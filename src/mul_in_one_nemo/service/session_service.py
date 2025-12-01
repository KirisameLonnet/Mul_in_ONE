"""Session service responsible for orchestrating runtime interactions."""

from __future__ import annotations

import asyncio
import inspect
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Set
import logging

from mul_in_one_nemo.service.models import SessionMessage, SessionRecord
from mul_in_one_nemo.service.repositories import SessionRepository
from mul_in_one_nemo.service.runtime_adapter import RuntimeAdapter

logger = logging.getLogger(__name__)


class SessionNotFoundError(Exception):
    """Raised when a requested session cannot be located."""


@dataclass(frozen=True)
class SessionStreamEvent:
    """Structured event emitted to WebSocket subscribers."""

    event: str
    data: Dict[str, Any]


class SessionRuntime:
    """Processes queued messages for a session and broadcasts responses."""

    def __init__(
        self,
        record: SessionRecord,
        adapter: RuntimeAdapter,
        repository: SessionRepository,
        history_limit: int,
    ) -> None:
        self.record = record
        self.adapter = adapter
        self.repository = repository
        self.history_limit = history_limit
        self._request_queue: asyncio.Queue[SessionMessage] = asyncio.Queue()
        self._subscriber_queues: Set[asyncio.Queue[SessionStreamEvent]] = set()
        self._worker: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._worker is None or self._worker.done():
            self._worker = asyncio.create_task(self._worker_loop())

    async def stop(self) -> None:
        if self._worker:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:  # pragma: no cover - lifecycle guard
                pass
            self._worker = None

    async def enqueue(self, message: SessionMessage) -> None:
        logger.info(f"Enqueue called for session {self.record.id}")
        await self._request_queue.put(message)
        logger.info(f"Message enqueued for session {self.record.id}")

    def subscribe(self) -> AsyncIterator[SessionStreamEvent]:
        queue: asyncio.Queue[SessionStreamEvent] = asyncio.Queue()
        self._subscriber_queues.add(queue)

        async def _generator() -> AsyncIterator[SessionStreamEvent]:
            try:
                while True:
                    yield await queue.get()
            finally:
                self._subscriber_queues.discard(queue)

        return _generator()

    async def _worker_loop(self) -> None:
        logger.info(f"Worker loop started for session {self.record.id}")
        while True:
            logger.info(f"Worker waiting for message in session {self.record.id}")
            message = await self._request_queue.get()
            logger.info(f"Worker processing a message in session {self.record.id}")
            stream = self.adapter.invoke_stream(self.record, message)
            if inspect.isawaitable(stream):
                stream = await stream
            logger.info(f"Stream obtained, starting iteration")
            trackers: Dict[str, Dict[str, Any]] = {}
            try:
                async for raw_event in stream:
                    logger.debug(f"Worker received event: {raw_event}")
                    await self._handle_adapter_event(raw_event, trackers)
            except Exception as e:
                logger.error(f"Exception during stream iteration: {e}", exc_info=True)
                raise

            # Flush any trackers that did not receive an explicit agent.end
            for sender in list(trackers.keys()):
                tracker = trackers.pop(sender)
                final_content = "".join(tracker.get("buffer", []))
                payload = {
                    "message_id": tracker.get("id"),
                    "sender": sender,
                    "content": final_content,
                    "session_id": self.record.id,
                    "timestamp": self._now_iso(),
                }
                persisted_record = None
                if final_content:
                    persisted_record = await self.repository.add_message(
                        self.record.id,
                        sender=sender,
                        content=final_content,
                    )
                if persisted_record:
                    payload["persisted_message_id"] = persisted_record.id
                await self._publish_event(SessionStreamEvent(event="agent.end", data=payload))

    async def _handle_adapter_event(self, event: Any, trackers: Dict[str, Dict[str, Any]]) -> None:
        normalized = event if isinstance(event, dict) else {"event": "agent.chunk", "data": {"content": str(event)}}
        event_type = normalized.get("event") or "agent.chunk"
        data = dict(normalized.get("data") or {})
        sender = data.get("sender")

        if event_type in {"agent.start", "agent.chunk", "agent.end"} and sender:
            tracker = trackers.setdefault(
                sender,
                {
                    "id": self._generate_agent_message_id(sender),
                    "buffer": [],
                },
            )
            data.setdefault("message_id", tracker["id"])
            data.setdefault("session_id", self.record.id)

            if event_type == "agent.start":
                data.setdefault("timestamp", self._now_iso())
            elif event_type == "agent.chunk":
                content = str(data.get("content", ""))
                tracker["buffer"].append(content)
                data["content"] = content
            elif event_type == "agent.end":
                final_content = data.get("content") or "".join(tracker.get("buffer", []))
                data["content"] = final_content
                data.setdefault("timestamp", self._now_iso())
                persisted_record = None
                if final_content:
                    persisted_record = await self.repository.add_message(
                        self.record.id,
                        sender=sender,
                        content=final_content,
                    )
                if persisted_record:
                    data["persisted_message_id"] = persisted_record.id
                trackers.pop(sender, None)

        await self._publish_event(SessionStreamEvent(event=event_type, data=data))

    async def _publish_event(self, event: SessionStreamEvent) -> None:
        if not self._subscriber_queues:
            return
        for queue in list(self._subscriber_queues):
            await queue.put(event)

    @staticmethod
    def _generate_agent_message_id(sender: str) -> str:
        normalized = sender or "agent"
        safe_sender = "".join(ch if ch.isalnum() else "_" for ch in normalized.lower()).strip("_") or "agent"
        return f"{safe_sender}_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()


class SessionService:
    """Session orchestration entry point backed by repository and runtime adapter."""

    def __init__(
        self,
        repository: SessionRepository,
        runtime_adapter: RuntimeAdapter,
        history_limit: int = 50,
    ) -> None:
        self._repository = repository
        self._runtime_adapter = runtime_adapter
        self._runtimes: Dict[str, SessionRuntime] = {}
        self._history_limit = history_limit

    async def create_session(
        self,
        tenant_id: str,
        user_id: str,
        *,
        user_persona: str | None = None,
        initial_persona_ids: List[int] | None = None,
    ) -> str:
        record = await self._repository.create(
            tenant_id, user_id, user_persona=user_persona, initial_persona_ids=initial_persona_ids or []
        )
        self._ensure_runtime(record)
        return record.id

    async def enqueue_message(self, message: SessionMessage) -> None:
        record = await self._repository.get(message.session_id)
        if record is None:
            raise SessionNotFoundError(message.session_id)
        await self._repository.add_message(message.session_id, sender=message.sender, content=message.content)
        history_records = await self._repository.list_messages(message.session_id, limit=self._history_limit)
        history_payload = [{"sender": r.sender, "content": r.content} for r in history_records]
        if record.user_persona:
            history_payload.insert(0, {"sender": "user_persona", "content": record.user_persona})
        # Propagate current session participants to the runtime as target handles
        target_personas = None
        if record.participants:
            try:
                target_personas = [p.handle for p in record.participants if getattr(p, "handle", None)]
            except Exception:
                target_personas = None

        enriched_message = replace(
            message,
            history=history_payload,
            user_persona=record.user_persona,
            target_personas=target_personas,
        )
        runtime = self._ensure_runtime(record)
        preview = (message.content or "").strip()
        preview = preview[:80] + ("…" if len(preview) > 80 else "")
        logger.info(
            "enqueue_message: using runtime for session %s; pushing message preview=%s",
            record.id,
            preview,
        )
        await runtime.enqueue(enriched_message)
        logger.info(f"enqueue_message: message pushed to queue for session {record.id}")

    async def stream_responses(self, session_id: str) -> AsyncIterator[SessionStreamEvent]:
        record = await self._repository.get(session_id)
        if record is None:
            raise SessionNotFoundError(session_id)
        runtime = self._ensure_runtime(record)
        return runtime.subscribe()

    async def update_user_persona(self, session_id: str, user_persona: str | None) -> SessionRecord:
        try:
            record = await self._repository.update_user_persona(session_id, user_persona)
        except ValueError as exc:
            raise SessionNotFoundError(session_id) from exc
        self._ensure_runtime(record)
        return record

    async def update_session_participants(self, session_id: str, persona_ids: List[int]) -> SessionRecord:
        try:
            record = await self._repository.update_session_participants(session_id, persona_ids)
        except ValueError as exc:
            raise SessionNotFoundError(session_id) from exc
        self._ensure_runtime(record)
        return record

    async def update_session_metadata(
        self,
        session_id: str,
        *,
        title: str | None = None,
        user_display_name: str | None = None,
        user_handle: str | None = None,
        user_persona: str | None = None,
    ) -> SessionRecord:
        try:
            record = await self._repository.update_session_metadata(
                session_id,
                title=title,
                user_display_name=user_display_name,
                user_handle=user_handle,
                user_persona=user_persona,
            )
        except ValueError as exc:
            raise SessionNotFoundError(session_id) from exc
        self._ensure_runtime(record)
        return record

    def _ensure_runtime(self, record: SessionRecord) -> SessionRuntime:
        runtime = self._runtimes.get(record.id)
        if runtime is None:
            runtime = SessionRuntime(record, self._runtime_adapter, self._repository, self._history_limit)
            self._runtimes[record.id] = runtime
            logger.info(f"_ensure_runtime: created new runtime {id(runtime)} for session {record.id}")
        else:
            runtime.record = record
            logger.info(f"_ensure_runtime: reusing runtime {id(runtime)} for session {record.id}")
        runtime.start()
        logger.info(f"_ensure_runtime: runtime {id(runtime)} started; queue id {id(runtime._request_queue)}")
        return runtime
