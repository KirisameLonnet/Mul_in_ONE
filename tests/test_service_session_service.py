"""SessionService behavior tests.

Test Timestamp: 2025-11-20T17:40:00+08:00
Coverage Scope: SessionService create/enqueue/stream with async runtime queue stub.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import importlib
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

_session_module = importlib.import_module("mul_in_one_nemo.service.session_service")
_models_module = importlib.import_module("mul_in_one_nemo.service.models")
_repositories_module = importlib.import_module("mul_in_one_nemo.service.repositories")
_runtime_module = importlib.import_module("mul_in_one_nemo.service.runtime_adapter")

SessionMessage = getattr(_models_module, "SessionMessage")
SessionService = getattr(_session_module, "SessionService")
InMemorySessionRepository = getattr(_repositories_module, "InMemorySessionRepository")
StubRuntimeAdapter = getattr(_runtime_module, "StubRuntimeAdapter")

TEST_TIMEOUT = 5
LOGGER = logging.getLogger("tests.session_service")


def test_create_and_stream_session():
    async def _scenario() -> None:
        repository = InMemorySessionRepository()
        service = SessionService(
            repository=repository,
            runtime_adapter=StubRuntimeAdapter(),
        )
        session_id = await service.create_session("tenant", "user")
        assert session_id.startswith("sess_tenant_")

        await service.enqueue_message(SessionMessage(session_id=session_id, content="hello", sender="user"))
        await service.enqueue_message(SessionMessage(session_id=session_id, content="world", sender="user"))

        collected: list[str] = []
        stream = await service.stream_responses(session_id)
        async for chunk in stream:
            collected.append(chunk)

            if len(collected) == 2:
                break

        await stream.aclose()

        assert collected == ["user:hello", "user:world"]

        messages = await repository.list_messages(session_id)
        senders = [message.sender for message in messages]
        contents = [message.content for message in messages]
        assert senders[:2] == ["user", "user"]
        assert senders[2:] == ["assistant", "assistant"]
        assert contents[:2] == ["hello", "world"]
        assert contents[2:] == ["user:hello", "user:world"]

    try:
        asyncio.run(asyncio.wait_for(_scenario(), timeout=TEST_TIMEOUT))
    except asyncio.TimeoutError as exc:  # pragma: no cover - debugging aid
        LOGGER.error("SessionService test timed out after %ss", TEST_TIMEOUT)
        raise AssertionError("SessionService did not produce responses in time") from exc
