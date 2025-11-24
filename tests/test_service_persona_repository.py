import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import asyncio
import importlib

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

_models_module = importlib.import_module("mul_in_one_nemo.db.models")
_repositories_module = importlib.import_module("mul_in_one_nemo.service.repositories")

Base = getattr(_models_module, "Base")
SQLAlchemyPersonaRepository = getattr(_repositories_module, "SQLAlchemyPersonaRepository")


def test_create_and_list_api_profiles() -> None:
    asyncio.run(_test_create_and_list_api_profiles())


async def _test_create_and_list_api_profiles() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = SQLAlchemyPersonaRepository(
        session_factory=session_factory,
        encryption_key="secret-key",
        default_memory_window=8,
        default_max_agents_per_turn=2,
        default_temperature=0.4,
    )

    created = await repo.create_api_profile(
        tenant_id="tenant-a",
        name="Primary",
        base_url="https://example.com/v1",
        model="model-x",
        api_key="sk-test-1234",
        temperature=0.7,
    )
    assert created.api_key_preview == "****1234"

    profiles = await repo.list_api_profiles("tenant-a")
    assert len(profiles) == 1
    assert profiles[0].name == "Primary"
    assert profiles[0].api_key_preview == "****1234"

    await engine.dispose()


def test_persona_crud_and_settings() -> None:
    asyncio.run(_test_persona_crud_and_settings())


async def _test_persona_crud_and_settings() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = SQLAlchemyPersonaRepository(
        session_factory=session_factory,
        encryption_key="secret-key",
        default_memory_window=8,
        default_max_agents_per_turn=2,
        default_temperature=0.4,
    )

    profile = await repo.create_api_profile(
        tenant_id="tenant-a",
        name="Primary",
        base_url="https://example.com/v1",
        model="model-x",
        api_key="sk-test-9999",
        temperature=0.6,
    )

    persona = await repo.create_persona(
        tenant_id="tenant-a",
        name="Helper",
        prompt="You are helpful",
        handle=None,
        tone="warm",
        proactivity=0.8,
        memory_window=10,
        max_agents_per_turn=3,
        api_profile_id=profile.id,
        is_default=True,
    )

    assert persona.handle == "helper"
    assert persona.api_profile_id == profile.id

    personas = await repo.list_personas("tenant-a")
    assert len(personas) == 1
    assert personas[0].is_default is True

    settings = await repo.load_persona_settings("tenant-a")
    assert settings.personas[0].name == "Helper"
    assert settings.personas[0].api is not None
    assert settings.personas[0].api.api_key == "sk-test-9999"

    await engine.dispose()


def test_create_persona_validates_api_profile() -> None:
    asyncio.run(_test_create_persona_validates_api_profile())


async def _test_create_persona_validates_api_profile() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = SQLAlchemyPersonaRepository(
        session_factory=session_factory,
        encryption_key="secret-key",
        default_memory_window=8,
        default_max_agents_per_turn=2,
        default_temperature=0.4,
    )

    other_profile = await repo.create_api_profile(
        tenant_id="tenant-b",
        name="Secondary",
        base_url="https://example.com/v1",
        model="model-y",
        api_key="sk-test-0000",
        temperature=None,
    )

    with pytest.raises(ValueError):
        await repo.create_persona(
            tenant_id="tenant-a",
            name="Helper",
            prompt="You are helpful",
            handle=None,
            tone="warm",
            proactivity=0.5,
            memory_window=8,
            max_agents_per_turn=2,
            api_profile_id=other_profile.id,
            is_default=False,
        )

    await engine.dispose()


def test_api_profile_update_and_delete() -> None:
    asyncio.run(_test_api_profile_update_and_delete())


async def _test_api_profile_update_and_delete() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = SQLAlchemyPersonaRepository(
        session_factory=session_factory,
        encryption_key="secret-key",
        default_memory_window=8,
        default_max_agents_per_turn=2,
        default_temperature=0.4,
    )

    profile = await repo.create_api_profile(
        tenant_id="tenant-z",
        name="Legacy",
        base_url="https://example.com/v1",
        model="model-old",
        api_key="sk-legacy-0001",
        temperature=0.3,
    )

    updated = await repo.update_api_profile(
        tenant_id="tenant-z",
        profile_id=profile.id,
        name="Primary",
        api_key="sk-new-0002",
        temperature=0.9,
    )
    assert updated.name == "Primary"
    assert updated.api_key_preview == "****0002"
    assert updated.temperature == 0.9

    await repo.delete_api_profile("tenant-z", profile.id)
    assert await repo.get_api_profile("tenant-z", profile.id) is None
    await engine.dispose()


def test_persona_update_and_delete() -> None:
    asyncio.run(_test_persona_update_and_delete())


async def _test_persona_update_and_delete() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = SQLAlchemyPersonaRepository(
        session_factory=session_factory,
        encryption_key="secret-key",
        default_memory_window=8,
        default_max_agents_per_turn=2,
        default_temperature=0.4,
    )

    profile = await repo.create_api_profile(
        tenant_id="tenant-y",
        name="Primary",
        base_url="https://example.com/v1",
        model="model-1",
        api_key="sk-test-1111",
        temperature=0.4,
    )
    persona = await repo.create_persona(
        tenant_id="tenant-y",
        name="Helper",
        prompt="Assist",
        handle="helper",
        tone="warm",
        proactivity=0.4,
        memory_window=8,
        max_agents_per_turn=2,
        api_profile_id=profile.id,
        is_default=False,
    )

    updated = await repo.update_persona(
        tenant_id="tenant-y",
        persona_id=persona.id,
        tone="excited",
        is_default=True,
    )
    assert updated.tone == "excited"
    assert updated.is_default is True

    await repo.delete_persona("tenant-y", persona.id)
    assert await repo.get_persona("tenant-y", persona.id) is None
    await engine.dispose()
