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
    repo = get_persona_repository()

    async def api_config_resolver(persona_id: int | None, use_embedding: bool = False) -> dict:
        if persona_id is None:
            raise ValueError("Persona ID required for API configuration resolution")
        
        if use_embedding:
            # Get persona record to extract username dynamically
            persona_record = await repo.get_persona_by_id(persona_id)
            if persona_record is None:
                raise ValueError(f"Persona {persona_id} not found")
            
            embedding_config = await repo.get_user_embedding_config(persona_record.username)
            if embedding_config.get("api_profile_id") is None:
                raise ValueError(
                    f"No embedding model configured for user {persona_record.username}. "
                    "Please configure an embedding API profile in Persona settings."
                )
            
            # get_persona_api_config_for_embedding will fetch and decrypt the key
            embedding_api_config = await repo.get_embedding_api_config_for_user(persona_record.username)
            if embedding_api_config is None:
                raise ValueError(f"Embedding API profile misconfigured for user {persona_record.username}")
            
            return embedding_api_config
        
        # Use persona's own API profile for LLM
        config = await repo.get_persona_api_config(persona_id)
        if config is None:
            raise ValueError(f"No API configuration found for persona {persona_id}")
        return config

    return RAGService(api_config_resolver=api_config_resolver)



