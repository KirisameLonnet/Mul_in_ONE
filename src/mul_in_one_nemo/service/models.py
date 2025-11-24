"""Domain models for the service layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    user_id: str
    roles: tuple[str, ...] = ()


@dataclass
class SessionRecord:
    id: str
    tenant_id: str
    user_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SessionMessage:
    session_id: str
    content: str
    sender: str
    target_personas: Optional[list[str]] = None
    history: Optional[list[dict[str, str]]] = None


@dataclass
class MessageRecord:
    id: str
    session_id: str
    sender: str
    content: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class APIProfileRecord:
    id: int
    tenant_id: str
    name: str
    base_url: str
    model: str
    temperature: float | None
    created_at: datetime
    api_key_preview: str | None = None


@dataclass
class PersonaRecord:
    id: int
    tenant_id: str
    name: str
    handle: str
    prompt: str
    tone: str
    proactivity: float
    memory_window: int
    max_agents_per_turn: int
    is_default: bool
    api_profile_id: int | None = None
    api_profile_name: str | None = None
    api_model: str | None = None
    api_base_url: str | None = None
    temperature: float | None = None
