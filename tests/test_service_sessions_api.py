"""Tests for session API skeleton.

Test Timestamp: 2025-11-20T17:40:00+08:00
Coverage Scope: FastAPI session endpoints & WebSocket stream smoke tests.
"""

from __future__ import annotations

import importlib
import logging
import sys
import threading
from pathlib import Path

from fastapi.testclient import TestClient

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

service_module = importlib.import_module("mul_in_one_nemo.service")
dependencies_module = importlib.import_module("mul_in_one_nemo.service.dependencies")
create_app = service_module.create_app
get_session_service = getattr(dependencies_module, "get_session_service")

TEST_TIMEOUT = 5
LOGGER = logging.getLogger("tests.sessions_api")

def _client() -> TestClient:
    if hasattr(get_session_service, "cache_clear"):
        get_session_service.cache_clear()
    app = create_app()
    return TestClient(app)

def _receive_json_with_timeout(ws, timeout: float):
    result: dict[str, object] = {}
    error: list[BaseException] = []

    def _target() -> None:
        try:
            result["event"] = ws.receive_json()
        except BaseException as exc:  # pragma: no cover - diagnostics
            error.append(exc)

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise AssertionError(f"WebSocket receive timed out after {timeout}s")
    if error:
        raise error[0]
    return result["event"]


def test_create_session_endpoint():
    client = _client()
    resp = client.post("/api/sessions", params={"tenant_id": "t1", "user_id": "u1"})
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["session_id"].startswith("sess_t1_")


def test_enqueue_message_endpoint():
    client = _client()
    session_id = client.post("/api/sessions", params={"tenant_id": "t1", "user_id": "u1"}).json()["session_id"]
    resp = client.post(f"/api/sessions/{session_id}/messages", params={"content": "hi"})
    assert resp.status_code == 202
    assert resp.json()["status"] == "queued"


def test_websocket_stream_receives_chunks():
    client = _client()
    session_id = client.post("/api/sessions", params={"tenant_id": "t1", "user_id": "u1"}).json()["session_id"]

    with client.websocket_connect(f"/api/ws/sessions/{session_id}") as ws:
        LOGGER.info("Waiting for websocket chunk for session %s", session_id)
        client.post(f"/api/sessions/{session_id}/messages", params={"content": "hola"})
        start_event = _receive_json_with_timeout(ws, TEST_TIMEOUT)
        assert start_event["event"] == "agent.start"
        chunk_event = _receive_json_with_timeout(ws, TEST_TIMEOUT)
        assert chunk_event["event"] == "agent.chunk"
        end_event = _receive_json_with_timeout(ws, TEST_TIMEOUT)
        assert end_event["event"] == "agent.end"

        assert chunk_event["data"]["content"].endswith("hola")
        assert end_event["data"]["content"].endswith("hola")

        msg_id = start_event["data"].get("message_id")
        assert msg_id
        assert chunk_event["data"]["message_id"] == msg_id
        assert end_event["data"]["message_id"] == msg_id
