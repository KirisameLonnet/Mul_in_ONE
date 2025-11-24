"""Session service responsible for orchestrating runtime interactions."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Set

from mul_in_one_nemo.service.models import SessionMessage, SessionRecord
from mul_in_one_nemo.service.repositories import SessionRepository
from mul_in_one_nemo.service.runtime_adapter import RuntimeAdapter


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
        await self._request_queue.put(message)

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
        while True:
            message = await self._request_queue.get()
            agent_sender = self._resolve_agent_sender(message)
            response_id = self._generate_agent_message_id(agent_sender)
            await self._publish_event(
                SessionStreamEvent(
                    event="agent.start",
                    data={
                        "message_id": response_id,
                        "sender": agent_sender,
                        "session_id": self.record.id,
                        "timestamp": self._now_iso(),
                    },
                )
            )
            stream = await self.adapter.invoke_stream(self.record, message)
            buffer: List[str] = []
            async for chunk in stream:
                text = str(chunk)
                buffer.append(text)
                await self._publish_event(
                    SessionStreamEvent(
                        event="agent.chunk",
                        data={
                            "message_id": response_id,
                            "sender": agent_sender,
                            "content": text,
                        },
                    )
                )
            final_content = "".join(buffer)
            persisted_record = None
            if final_content:
                persisted_record = await self.repository.add_message(
                    self.record.id,
                    sender=agent_sender,
                    content=final_content,
                )
            end_payload = {
                "message_id": response_id,
                "sender": agent_sender,
                "content": final_content,
                "timestamp": self._now_iso(),
            }
            if persisted_record:
                end_payload["persisted_message_id"] = persisted_record.id
            await self._publish_event(
                SessionStreamEvent(
                    event="agent.end",
                    data=end_payload,
                )
            )

    async def _publish_event(self, event: SessionStreamEvent) -> None:
        if not self._subscriber_queues:
            return
        for queue in list(self._subscriber_queues):
            await queue.put(event)

    def _resolve_agent_sender(self, message: SessionMessage) -> str:
        if message.target_personas:
            for persona in message.target_personas:
                if persona:
                    return persona
        return "assistant"

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

    async def create_session(self, tenant_id: str, user_id: str) -> str:
        record = await self._repository.create(tenant_id, user_id)
        self._ensure_runtime(record)
        return record.id

    async def enqueue_message(self, message: SessionMessage) -> None:
        record = await self._repository.get(message.session_id)
        if record is None:
            raise SessionNotFoundError(message.session_id)
        await self._repository.add_message(message.session_id, sender=message.sender, content=message.content)
        history_records = await self._repository.list_messages(message.session_id, limit=self._history_limit)
        history_payload = [{"sender": r.sender, "content": r.content} for r in history_records]
        enriched_message = replace(message, history=history_payload)
        runtime = self._ensure_runtime(record)
        await runtime.enqueue(enriched_message)

    async def stream_responses(self, session_id: str) -> AsyncIterator[SessionStreamEvent]:
        record = await self._repository.get(session_id)
        if record is None:
            raise SessionNotFoundError(session_id)
        runtime = self._ensure_runtime(record)
        return runtime.subscribe()

    def _ensure_runtime(self, record: SessionRecord) -> SessionRuntime:
        runtime = self._runtimes.get(record.id)
        if runtime is None:
            runtime = SessionRuntime(record, self._runtime_adapter, self._repository, self._history_limit)
            self._runtimes[record.id] = runtime
        runtime.start()
        return runtime
