import asyncio
import sys
from pathlib import Path

import importlib
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

_service_app = importlib.import_module("mul_in_one_nemo.service.app")
_dependencies_module = importlib.import_module("mul_in_one_nemo.service.dependencies")
_models_module = importlib.import_module("mul_in_one_nemo.db.models")
_repositories_module = importlib.import_module("mul_in_one_nemo.service.repositories")

create_app = getattr(_service_app, "create_app")
get_persona_repository = getattr(_dependencies_module, "get_persona_repository")
Base = getattr(_models_module, "Base")
SQLAlchemyPersonaRepository = getattr(_repositories_module, "SQLAlchemyPersonaRepository")


@pytest.fixture
def persona_test_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)

    async def _prepare() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_prepare())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    repository = SQLAlchemyPersonaRepository(
        session_factory=session_factory,
        encryption_key="secret-key",
        default_memory_window=8,
        default_max_agents_per_turn=2,
        default_temperature=0.4,
    )

    app = create_app()
    app.dependency_overrides[get_persona_repository] = lambda: repository
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())


def test_create_and_list_api_profile(persona_test_client: TestClient) -> None:
    payload = {
        "tenant_id": "tenant-a",
        "name": "Primary",
        "base_url": "https://example.com/v1",
        "model": "model-x",
        "api_key": "sk-test-1234",
        "temperature": 0.7,
    }
    response = persona_test_client.post("/api/api-profiles", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["api_key_preview"] == "****1234"

    list_resp = persona_test_client.get("/api/api-profiles", params={"tenant_id": "tenant-a"})
    assert list_resp.status_code == 200
    profiles = list_resp.json()
    assert len(profiles) == 1
    assert profiles[0]["name"] == "Primary"


def test_create_and_list_personas(persona_test_client: TestClient) -> None:
    profile_payload = {
        "tenant_id": "tenant-a",
        "name": "Primary",
        "base_url": "https://example.com/v1",
        "model": "model-x",
        "api_key": "sk-test-9999",
        "temperature": 0.6,
    }
    profile = persona_test_client.post("/api/api-profiles", json=profile_payload).json()

    persona_payload = {
        "tenant_id": "tenant-a",
        "name": "Helper",
        "prompt": "You are helpful",
        "tone": "warm",
        "proactivity": 0.7,
        "memory_window": 12,
        "max_agents_per_turn": 3,
        "api_profile_id": profile["id"],
        "is_default": True,
    }
    persona_resp = persona_test_client.post("/api/personas", json=persona_payload)
    assert persona_resp.status_code == 201
    persona = persona_resp.json()
    assert persona["api_profile_name"] == "Primary"

    list_resp = persona_test_client.get("/api/personas", params={"tenant_id": "tenant-a"})
    assert list_resp.status_code == 200
    personas = list_resp.json()
    assert len(personas) == 1
    assert personas[0]["name"] == "Helper"


def test_validate_api_profile_tenant(persona_test_client: TestClient) -> None:
    persona_test_client.post(
        "/api/api-profiles",
        json={
            "tenant_id": "tenant-b",
            "name": "Secondary",
            "base_url": "https://example.com/v1",
            "model": "model-y",
            "api_key": "sk-test-0000",
        },
    )

    persona_payload = {
        "tenant_id": "tenant-a",
        "name": "Helper",
        "prompt": "You are helpful",
        "api_profile_id": 1,
    }
    response = persona_test_client.post("/api/personas", json=persona_payload)
    assert response.status_code == 400


def test_update_and_delete_api_profile(persona_test_client: TestClient) -> None:
    profile = persona_test_client.post(
        "/api/api-profiles",
        json={
            "tenant_id": "tenant-a",
            "name": "Primary",
            "base_url": "https://example.com/v1",
            "model": "model-x",
            "api_key": "sk-test-1234",
        },
    ).json()

    update_resp = persona_test_client.patch(
        f"/api/api-profiles/{profile['id']}",
        params={"tenant_id": "tenant-a"},
        json={"name": "Renamed", "temperature": 0.8},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Renamed"

    delete_resp = persona_test_client.delete(
        f"/api/api-profiles/{profile['id']}", params={"tenant_id": "tenant-a"}
    )
    assert delete_resp.status_code == 204

    get_resp = persona_test_client.get(
        f"/api/api-profiles/{profile['id']}", params={"tenant_id": "tenant-a"}
    )
    assert get_resp.status_code == 404


def test_update_and_delete_persona(persona_test_client: TestClient) -> None:
    profile = persona_test_client.post(
        "/api/api-profiles",
        json={
            "tenant_id": "tenant-a",
            "name": "Primary",
            "base_url": "https://example.com/v1",
            "model": "model-x",
            "api_key": "sk-test-1234",
        },
    ).json()

    persona = persona_test_client.post(
        "/api/personas",
        json={
            "tenant_id": "tenant-a",
            "name": "Helper",
            "prompt": "Assist",
            "api_profile_id": profile["id"],
            "is_default": False,
        },
    ).json()

    update_resp = persona_test_client.patch(
        f"/api/personas/{persona['id']}",
        params={"tenant_id": "tenant-a"},
        json={"tone": "excited", "is_default": True},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["tone"] == "excited"
    assert data["is_default"] is True

    delete_resp = persona_test_client.delete(
        f"/api/personas/{persona['id']}", params={"tenant_id": "tenant-a"}
    )
    assert delete_resp.status_code == 204

    get_resp = persona_test_client.get(
        f"/api/personas/{persona['id']}", params={"tenant_id": "tenant-a"}
    )
    assert get_resp.status_code == 404