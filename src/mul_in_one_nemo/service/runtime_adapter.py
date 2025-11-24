"""Runtime adapter abstractions."""

from __future__ import annotations

import asyncio
import contextlib
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import replace
from typing import AsyncIterator, Dict

from mul_in_one_nemo.api_config import apply_api_bindings
from mul_in_one_nemo.config import Settings
from mul_in_one_nemo.persona import Persona, PersonaSettings, load_personas
from mul_in_one_nemo.runtime import MultiAgentRuntime
from mul_in_one_nemo.service.models import SessionMessage, SessionRecord
from mul_in_one_nemo.service.repositories import (
    PersonaDataRepository,
    SQLAlchemyPersonaRepository,
)


class RuntimeAdapter(ABC):
    """Adapter that bridges SessionService with runtime execution."""

    @abstractmethod
    async def invoke_stream(self, session: SessionRecord, message: SessionMessage) -> AsyncIterator[str]: ...


class StubRuntimeAdapter(RuntimeAdapter):
    """Simple runtime adapter used for tests and local development."""

    async def invoke_stream(self, session: SessionRecord, message: SessionMessage) -> AsyncIterator[str]:
        async def _generator() -> AsyncIterator[str]:
            await asyncio.sleep(0)
            prefix = message.sender or "user"
            yield f"{prefix}:{message.content}"

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

    async def invoke_stream(self, session: SessionRecord, message: SessionMessage) -> AsyncIterator[str]:
        tenant_id = session.tenant_id or "default"
        runtime = await self._ensure_runtime(tenant_id)
        persona_settings = self._persona_cache.get(tenant_id) or await self._load_persona_settings(tenant_id)
        persona = self._select_persona(message, persona_settings.personas)
        payload = {
            "session_id": session.id,
            "tenant_id": session.tenant_id,
            "user_message": message.content,
            "history": message.history or [],
            "target_personas": message.target_personas or [],
        }

        async def _generator() -> AsyncIterator[str]:
            async for chunk in runtime.invoke_stream(persona.name, payload):
                if isinstance(chunk, str):
                    yield chunk
                elif hasattr(chunk, "response"):
                    yield getattr(chunk, "response")  # type: ignore[no-any-return]
                else:
                    yield str(chunk)

        return _generator()

    @staticmethod
    def _select_persona(message: SessionMessage, personas: list[Persona]) -> Persona:
        if not personas:
            raise RuntimeError("No personas configured for runtime")

        if message.target_personas:
            mapping = {p.name.lower(): p for p in personas}
            handle_map = {p.handle.lower(): p for p in personas}
            for target in message.target_personas:
                key = target.lower()
                if key in mapping:
                    return mapping[key]
                if key in handle_map:
                    return handle_map[key]

        return personas[0]
