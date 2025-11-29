"""Runtime adapter abstractions."""

from __future__ import annotations

import asyncio
import contextlib
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import replace
from typing import AsyncIterator, Dict, List

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

    @staticmethod
    def _build_scheduler(personas: list[Persona], max_agents: int) -> TurnScheduler:
        states = [PersonaState(name=p.name, proactivity=p.proactivity) for p in personas]
        effective_max = len(personas) if max_agents <= 0 else max_agents
        return TurnScheduler(states, max_agents=effective_max)

    @staticmethod
    def _extract_tags(user_text: str, personas: list[Persona]) -> List[str]:
        lowered = user_text.lower()
        tags = []
        for persona in personas:
            handle = persona.handle.lower()
            if persona.name.lower() in lowered or handle in lowered:
                tags.append(persona.name)
        return tags

    async def _ensure_runtime(self, tenant_id: str) -> MultiAgentRuntime:
        runtime = self._runtimes.get(tenant_id)
        if runtime is not None:
            return runtime
        lock = self._locks[tenant_id]
        async with lock:
            runtime = self._runtimes.get(tenant_id)
            if runtime is not None:
                return runtime
            persona_settings = await self._load_persona_settings(tenant_id)
            resolved_settings = replace(
                self._settings,
                memory_window=persona_settings.memory_window or self._settings.memory_window,
                max_agents_per_turn=persona_settings.max_agents_per_turn or self._settings.max_agents_per_turn,
            )
            runtime = MultiAgentRuntime(resolved_settings, persona_settings.personas)
            await runtime.__aenter__()
            self._runtimes[tenant_id] = runtime
            self._persona_cache[tenant_id] = persona_settings
            return runtime

    async def _load_persona_settings(self, tenant_id: str) -> PersonaSettings:
        cached = self._persona_cache.get(tenant_id)
        if cached:
            return cached

        if self._persona_repository:
            settings = await self._persona_repository.load_persona_settings(tenant_id)
            if settings.personas:
                self._persona_cache[tenant_id] = settings
                return settings

        fallback = load_personas(self._settings.persona_file)
        if self._settings.api_configuration:
            apply_api_bindings(fallback.personas, self._settings.api_configuration)
        self._persona_cache[tenant_id] = fallback
        return fallback

    async def shutdown(self) -> None:
        for tenant_id, runtime in list(self._runtimes.items()):
            with contextlib.suppress(Exception):
                await runtime.__aexit__(None, None, None)
            self._runtimes.pop(tenant_id, None)
        self._persona_cache.clear()
        self._locks.clear()

    async def invoke_stream(self, session: SessionRecord, message: SessionMessage) -> AsyncIterator[Dict]:
        """Drives a multi-agent conversation turn, yielding structured events."""
        tenant_id = session.tenant_id or "default"
        runtime = await self._ensure_runtime(tenant_id)
        persona_settings = self._persona_cache[tenant_id]

        # Set RAG context for this invocation (thread-safe via contextvars)
        # This allows RAG tools to access tenant/persona without LLM exposure
        # Context will be available to all async operations in this task
        # Note: We'll update persona_id per speaker during the conversation loop
        set_rag_context(tenant_id=tenant_id, persona_id=None)
        
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
            max_exchanges = 3  # Allow natural conversation flow

            # 3. Start the conversation loop
            for exchange_round in range(max_exchanges):
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

                if not speakers:
                    break
                
                # Skip if the only speaker is the same as last speaker (prevent self-conversation)
                if len(speakers) == 1 and speakers[0] == last_speaker and not is_first_round:
                    break

                for persona_name in speakers:
                    yield {"event": "agent.start", "data": {"sender": persona_name}}

                    # Get persona_id for the current speaker
                    current_persona = persona_map.get(persona_name)
                    persona_id = current_persona.id if current_persona else None
                    
                    # Update RAG context with current persona's ID
                    # This makes it available to any RAG tool calls during this persona's turn
                    if persona_id:
                        set_rag_context(tenant_id=tenant_id, persona_id=persona_id)

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
                        }

                    full_reply = ""
                    try:
                        async for chunk in runtime.invoke_stream(persona_name, payload):
                            text_chunk = ""
                            if isinstance(chunk, str):
                                text_chunk = chunk
                            elif hasattr(chunk, "response"):
                                text_chunk = getattr(chunk, "response")

                            if text_chunk:
                                yield {"event": "agent.chunk", "data": {"content": text_chunk}}
                                full_reply += text_chunk
                    except Exception as e:
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
