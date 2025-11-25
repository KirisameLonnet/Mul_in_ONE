"""Shared FastAPI dependencies."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from mul_in_one_nemo.config import Settings
from mul_in_one_nemo.service.rag_service import RAGService
from mul_in_one_nemo.service.repositories import (
    InMemorySessionRepository,
    PersonaDataRepository,
    SQLAlchemyPersonaRepository,
    SQLAlchemySessionRepository,
    SessionRepository,
)
from mul_in_one_nemo.service.runtime_adapter import (
    NemoRuntimeAdapter,
    RuntimeAdapter,
    StubRuntimeAdapter,
)
from mul_in_one_nemo.service.session_service import SessionService


@lru_cache
def get_session_repository() -> SessionRepository:
    """Return the process-wide session repository implementation."""
    backend = os.environ.get("MUL_IN_ONE_SESSION_REPO", "db").strip().lower()
    if backend == "db":
        return SQLAlchemySessionRepository()
    return InMemorySessionRepository()


@lru_cache
def get_runtime_adapter() -> RuntimeAdapter:
    """Return the runtime adapter used to execute persona sessions."""
    mode = os.environ.get("MUL_IN_ONE_RUNTIME_MODE", "nemo").strip().lower()
    persona_repo = get_persona_repository()
    if mode == "nemo":
        return NemoRuntimeAdapter(persona_repository=persona_repo)
    return StubRuntimeAdapter()


@lru_cache
def get_session_service() -> SessionService:
    """Singleton-style accessor for SessionService."""
    return SessionService(
        repository=get_session_repository(),
        runtime_adapter=get_runtime_adapter(),
    )


@lru_cache
def get_persona_repository() -> PersonaDataRepository:
    """Provide repository used by persona/API profile APIs and runtime."""
    settings = Settings.from_env()
    return SQLAlchemyPersonaRepository(
        encryption_key=settings.encryption_key or None,
        default_memory_window=settings.memory_window,
        default_max_agents_per_turn=settings.max_agents_per_turn,
        default_temperature=settings.temperature,
    )


@lru_cache
def get_rag_service() -> RAGService:
    """Provide a singleton instance of the RAGService."""
    return RAGService()
