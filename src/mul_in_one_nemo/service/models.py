"""Data models shared between service layers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class APIProfileRecord:
    id: int
    tenant_id: str
    name: str
    base_url: str
    model: str
    temperature: float
    created_at: datetime
    api_key_preview: str | None = None
    is_embedding_model: bool = False
    embedding_dim: int | None = None


@dataclass(frozen=True)
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
    background: str | None = None
    api_profile_id: int | None = None
    api_profile_name: str | None = None
    api_model: str | None = None
    api_base_url: str | None = None
    temperature: float | None = None


@dataclass(frozen=True)
class SessionRecord:
    id: str
    tenant_id: str
    user_id: str
    created_at: datetime
    user_persona: str | None = None
    participants: list[PersonaRecord] | None = None
    # Editable session metadata
    title: str | None = None
    user_display_name: str | None = None
    user_handle: str | None = None


@dataclass(frozen=True)
class SessionMessage:
    session_id: str
    sender: str
    content: str
    history: list[dict[str, str]] | None = None
    target_personas: list[str] | None = None
    user_persona: str | None = None


@dataclass(frozen=True)
class MessageRecord:
    id: str
    session_id: str
    sender: str
    content: str
    created_at: datetime
    background: str | None = None
