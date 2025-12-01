"""Runtime adapter abstractions."""

from __future__ import annotations

import asyncio
import contextlib
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import replace
from typing import AsyncIterator, Dict, List
import logging

from mul_in_one_nemo.api_config import apply_api_bindings
from mul_in_one_nemo.config import Settings
from mul_in_one_nemo.memory import ConversationMemory
from mul_in_one_nemo.persona import Persona, PersonaSettings, load_personas
from mul_in_one_nemo.runtime import MultiAgentRuntime
from mul_in_one_nemo.scheduler import PersonaState, TurnScheduler
from mul_in_one_nemo.service.models import SessionMessage, SessionRecord
from mul_in_one_nemo.service.repositories import (
    PersonaDataRepository,
    SQLAlchemyPersonaRepository,
)
from mul_in_one_nemo.service.rag_context import set_rag_context, clear_rag_context

logger = logging.getLogger(__name__)


class RuntimeAdapter(ABC):
    """Adapter that bridges SessionService with runtime execution."""

    @abstractmethod
    async def invoke_stream(self, session: SessionRecord, message: SessionMessage) -> AsyncIterator[Dict]:
        ...


class StubRuntimeAdapter(RuntimeAdapter):
    """Simple runtime adapter used for tests and local development."""

    async def invoke_stream(self, session: SessionRecord, message: SessionMessage) -> AsyncIterator[Dict]:
        async def _generator() -> AsyncIterator[Dict]:
            await asyncio.sleep(0)
            target = (message.target_personas or ["assistant"])[0]
            sender = target or "assistant"
            content = f"{message.sender or 'user'}:{message.content}"
            yield {"event": "agent.start", "data": {"sender": sender}}
            yield {"event": "agent.chunk", "data": {"sender": sender, "content": content}}
            yield {"event": "agent.end", "data": {"sender": sender, "content": content}}

        return _generator()


class NemoRuntimeAdapter(RuntimeAdapter):
    """Runtime adapter that drives the real MultiAgentRuntime."""
    
    # Regex pattern to filter out special tokens from LLM output
    # Matches patterns like: <|pad|>, <|eos|>, <｜▁pad▁｜>, etc.
    # Common in Qwen models and other tokenizers
    _SPECIAL_TOKEN_PATTERN = re.compile(r'<[|｜][^|｜]*[|｜]>')

    def __init__(
        self,
        settings: Settings | None = None,
        persona_repository: PersonaDataRepository | None = None,
    ) -> None:
        self._settings = settings or Settings.from_env()
        self._persona_repository = persona_repository or SQLAlchemyPersonaRepository(
            encryption_key=self._settings.encryption_key or None,
            default_memory_window=self._settings.memory_window,
            default_max_agents_per_turn=self._settings.max_agents_per_turn,
            default_temperature=self._settings.temperature,
        )
        self._runtimes: Dict[str, MultiAgentRuntime] = {}
        self._persona_cache: Dict[str, PersonaSettings] = {}
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    @classmethod
    def _filter_special_tokens(cls, text: str) -> str:
        """Remove special tokens from LLM output.
        
        This filters out tokenizer artifacts like <|pad|>, <|eos|>, <｜▁pad▁｜>
        that some models (e.g., Qwen) may accidentally output in their responses.
        
        Args:
            text: Raw text from LLM that may contain special tokens
            
        Returns:
            Cleaned text with special tokens removed
        """
        return cls._SPECIAL_TOKEN_PATTERN.sub('', text)

    @staticmethod
    def _build_scheduler(personas: list[Persona], max_agents: int) -> TurnScheduler:
        states = [PersonaState(name=p.name, proactivity=p.proactivity) for p in personas]
        effective_max = len(personas) if max_agents <= 0 else max_agents
        return TurnScheduler(states, max_agents=effective_max)

    @staticmethod
    def _extract_tags(user_text: str, personas: list[Persona]) -> List[str]:
        """Extract mentioned persona names from user text, preserving order.

        Priority:
        1) Explicit @handle mentions (order preserved)
        2) Fallback substring match for handle/name (order by first occurrence)
        """
        text = user_text or ""
        lowered = text.lower()

        # Build lookup maps
        handle_to_name = {p.handle.lower(): p.name for p in personas}
        name_set = {p.name for p in personas}

        # 1) Parse explicit @mentions (Latin/CJK word-ish handles)
        # Capture sequences after @, allowing letters, numbers, _, -, and CJK
        mention_tokens = re.findall(r"@([\w\-\u4e00-\u9fff]+)", text)
        ordered_names: List[str] = []
        seen: set[str] = set()
        for token in mention_tokens:
            key = token.lower()
            if key in handle_to_name:
                name = handle_to_name[key]
                if name not in seen:
                    ordered_names.append(name)
                    seen.add(name)
            else:
                # Try direct name match (case-insensitive)
                for p in personas:
                    if p.name.lower() == key and p.name not in seen:
                        ordered_names.append(p.name)
                        seen.add(p.name)
                        break

        if ordered_names:
            return ordered_names

        # 2) Fallback: substring heuristic (keep order by first occurrence index)
        candidates: List[tuple[int, str]] = []
        for p in personas:
            idx = -1
            h = p.handle.lower()
            n = p.name.lower()
            if h and h in lowered:
                idx = lowered.find(h)
            elif n and n in lowered:
                idx = lowered.find(n)
            if idx >= 0:
                candidates.append((idx, p.name))
        candidates.sort(key=lambda x: x[0])
        return [name for _, name in candidates]

    async def _ensure_runtime(self, username: str) -> MultiAgentRuntime:
        runtime = self._runtimes.get(username)
        if runtime is not None:
            return runtime
        lock = self._locks[username]
        async with lock:
            runtime = self._runtimes.get(username)
            if runtime is not None:
                return runtime
            persona_settings = await self._load_persona_settings(username)
            resolved_settings = replace(
                self._settings,
                memory_window=persona_settings.memory_window or self._settings.memory_window,
                max_agents_per_turn=persona_settings.max_agents_per_turn or self._settings.max_agents_per_turn,
            )
            runtime = MultiAgentRuntime(resolved_settings, persona_settings.personas)
            await runtime.__aenter__()
            self._runtimes[username] = runtime
            self._persona_cache[username] = persona_settings
            return runtime

    async def _load_persona_settings(self, username: str) -> PersonaSettings:
        cached = self._persona_cache.get(username)
        if cached:
            return cached

        if self._persona_repository:
            settings = await self._persona_repository.load_persona_settings(username)
            if settings.personas:
                self._persona_cache[username] = settings
                return settings

        fallback = load_personas(self._settings.persona_file)
        if self._settings.api_configuration:
            apply_api_bindings(fallback.personas, self._settings.api_configuration)
        self._persona_cache[username] = fallback
        return fallback

    async def shutdown(self) -> None:
        for username, runtime in list(self._runtimes.items()):
            with contextlib.suppress(Exception):
                await runtime.__aexit__(None, None, None)
            self._runtimes.pop(username, None)
        self._persona_cache.clear()
        self._locks.clear()

    async def invoke_stream(self, session: SessionRecord, message: SessionMessage) -> AsyncIterator[Dict]:
        """Drives a multi-agent conversation turn, yielding structured events."""
        username = session.username or "default"
        runtime = await self._ensure_runtime(username)
        persona_settings = self._persona_cache[username]
        logger.info(f"RuntimeAdapter.invoke_stream called for user {username}, session {session.id}")
        logger.info(f"Persona settings loaded: {len(persona_settings.personas)} personas")

        # Set RAG context for this invocation (thread-safe via contextvars)
        # This allows RAG tools to access user/persona without LLM exposure
        # Context will be available to all async operations in this task
        # Note: We'll update persona_id per speaker during the conversation loop
        set_rag_context(username=username, persona_id=None)
        
        try:
            # Create a mapping from persona name to persona object for easy lookup
            persona_map = {p.name: p for p in persona_settings.personas}
        
            # Extract active participants (handles) from session.participants
            active_participants = []
            if session.participants:
                active_participants = [p.handle for p in session.participants]
            # Always include "user" as a participant
            if "user" not in active_participants and "用户" not in active_participants:
                active_participants.insert(0, "user")

            # 1. Initialize Memory for the entire turn
            memory = ConversationMemory()
            if message.history:
                for entry in message.history:
                    # 支持群聊式上下文，补全 recipient 字段
                    memory.add(
                        entry["sender"],
                        entry["content"],
                        entry.get("recipient")
                    )
            # 用户新消息，recipient 默认为 None（群聊）
            user_message_content = message.content
            memory.add(message.sender or "user", user_message_content, None)

            scheduler = self._build_scheduler(
                persona_settings.personas,
                (persona_settings.max_agents_per_turn or self._settings.max_agents_per_turn),
            )

            # 2. Set initial context for the turn
            context_tags = self._extract_tags(user_message_content, persona_settings.personas)
            user_selected_personas = None  # Track user's explicit selection
            if message.target_personas:
                # Map handle to name since target_personas contains handles (e.g., "Uika")
                # but context_tags and scheduler use persona names (e.g., "三角初华")
                handle_to_name = {p.handle: p.name for p in persona_settings.personas}
                user_selected_personas = []
                for target_handle in message.target_personas:
                    persona_name = handle_to_name.get(target_handle)
                    if persona_name:
                        if persona_name not in context_tags:
                            context_tags.append(persona_name)
                        user_selected_personas.append(persona_name)

            last_speaker = message.sender or "user"
            is_first_round = True
            num_personas = len(persona_settings.personas)
            # Use configurable max exchanges per user message
            max_exchanges = max(1, getattr(self._settings, "max_exchanges_per_turn", 8))
            logger.info(f"Starting conversation loop: context_tags={context_tags}, user_selected={user_selected_personas}")

            # 3. Start the conversation loop
            for exchange_round in range(max_exchanges):
                logger.info(f"Exchange round {exchange_round}: last_speaker={last_speaker}, is_first_round={is_first_round}")
                # If user explicitly selected personas, restrict conversation to only those personas
                if user_selected_personas:
                    speakers = scheduler.next_turn(
                        context_tags=context_tags if exchange_round == 0 else user_selected_personas,
                        last_speaker=last_speaker,
                        is_user_message=is_first_round,
                    )
                else:
                    speakers = scheduler.next_turn(
                        context_tags=context_tags if exchange_round == 0 else None,
                        last_speaker=last_speaker,
                        is_user_message=is_first_round,
                    )

                logger.info(f"Scheduler returned speakers: {speakers}")
                if not speakers:
                    logger.info("No speakers selected, breaking loop")
                    break
                
                # Skip if the only speaker is the same as last speaker (prevent self-conversation)
                if len(speakers) == 1 and speakers[0] == last_speaker and not is_first_round:
                    logger.info(f"Skipping self-conversation this round: {speakers[0]}")
                    # Try next round instead of terminating the conversation
                    continue

                for persona_name in speakers:
                    logger.info(f"Processing persona: {persona_name}")
                    yield {"event": "agent.start", "data": {"sender": persona_name}}

                    # Get persona_id for the current speaker
                    current_persona = persona_map.get(persona_name)
                    persona_id = current_persona.id if current_persona else None
                    
                    # Update RAG context with current persona's ID
                    # This makes it available to any RAG tool calls during this persona's turn
                    if persona_id:
                        set_rag_context(username=username, persona_id=persona_id)

                    # Construct payload with appropriate context
                    # In the first exchange round, ALL selected speakers respond to the user's original message
                    # In subsequent rounds, agents respond to the previous speaker
                    if exchange_round == 0:
                        # The first round: all agent(s) respond directly to the user's message
                        payload = {
                            "history": memory.as_payload(runtime.settings.memory_window, last_n=1),
                            "user_message": user_message_content,
                            "persona_id": persona_id, # Inject persona_id
                            "active_participants": active_participants, # Inject active participants
                            "user_display_name": getattr(session, "user_display_name", None),
                            "user_handle": getattr(session, "user_handle", None),
                            "user_persona": getattr(session, "user_persona", None),
                        }
                    else:
                        # Subsequent rounds: agents respond to the previous speaker in a more contextual way
                        # Skip if this persona is responding to themselves (shouldn't happen due to check above, but safety)
                        if persona_name == last_speaker:
                            continue
                        
                        # The full history is in memory, we frame the last message as an observation.
                        last_message = memory.get_last_message()
                        observed_message = f"你刚刚观察到 \"{last_speaker}\" 说: \"{last_message}\"。现在轮到你发言，你可以对此进行评论，或开启新话题。"
                        payload = {
                            "history": memory.as_payload(runtime.settings.memory_window, last_n=1),
                            "user_message": observed_message,
                            "persona_id": persona_id, # Inject persona_id
                            "active_participants": active_participants, # Inject active participants
                            "user_display_name": getattr(session, "user_display_name", None),
                            "user_handle": getattr(session, "user_handle", None),
                            "user_persona": getattr(session, "user_persona", None),
                        }

                    full_reply = ""
                    chunk_count = 0
                    try:
                        logger.info(f"Calling runtime.invoke_stream for {persona_name}")
                        logger.info(f"Payload: history_len={len(payload.get('history', []))}, user_message_preview={payload.get('user_message', '')[:100]}")
                        async for chunk in runtime.invoke_stream(persona_name, payload):
                            chunk_count += 1
                            if chunk_count <= 5:  # Log first 5 chunks
                                logger.info(f"Received chunk #{chunk_count} from {persona_name}: type={type(chunk)}, preview={repr(chunk)[:100]}")
                            text_chunk = ""
                            if isinstance(chunk, str):
                                text_chunk = chunk
                            elif hasattr(chunk, "response"):
                                text_chunk = getattr(chunk, "response")

                            if text_chunk:
                                before_filter = text_chunk
                                # Filter out special tokens that some LLMs (e.g., Qwen) may output
                                text_chunk = self._filter_special_tokens(text_chunk)
                                if before_filter != text_chunk:
                                    logger.info(f"Filtered special tokens: before={repr(before_filter[:50])}, after={repr(text_chunk[:50])}")
                                if text_chunk:  # Only yield if there's content after filtering
                                    yield {"event": "agent.chunk", "data": {"content": text_chunk}}
                                    full_reply += text_chunk
                                else:
                                    logger.warning(f"text_chunk was filtered to empty string from: {repr(before_filter[:100])}")
                            else:
                                if chunk_count <= 5:
                                    logger.info(f"No text_chunk extracted from chunk #{chunk_count}")
                        logger.info(f"Finished streaming from {persona_name}, received {chunk_count} chunks, reply length: {len(full_reply)}")
                    except Exception as e:
                        logger.error(f"Exception during runtime.invoke_stream for {persona_name}: {e}", exc_info=True)
                        error_message = f"[Error from {persona_name}: {e}]"
                        yield {"event": "agent.chunk", "data": {"content": error_message}}
                        full_reply = error_message

                    yield {"event": "agent.end", "data": {"sender": persona_name, "content": full_reply}}
                    # agent 回复 recipient 默认为 None（群聊），如需@可在此扩展
                    memory.add(persona_name, full_reply, None)
                    last_speaker = persona_name
                    context_tags.extend(self._extract_tags(full_reply, persona_settings.personas))
                
                # Mark first round complete after all speakers in this round have spoken
                is_first_round = False
        
        finally:
            # Clean up RAG context after invocation completes
            clear_rag_context()
