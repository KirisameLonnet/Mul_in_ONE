"""Repository interfaces and implementations for backend services."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional

from cryptography.fernet import Fernet
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from mul_in_one_nemo.db import get_session_factory
from mul_in_one_nemo.db.models import APIProfile as APIProfileRow
from mul_in_one_nemo.db.models import Persona as PersonaRow
from mul_in_one_nemo.db.models import Session as SessionRow
from mul_in_one_nemo.db.models import SessionMessage as SessionMessageRow
from mul_in_one_nemo.db.models import Tenant as TenantRow
from mul_in_one_nemo.db.models import User as UserRow
from mul_in_one_nemo.persona import Persona, PersonaAPIConfig, PersonaSettings
from mul_in_one_nemo.service.models import (
    APIProfileRecord,
    MessageRecord,
    PersonaRecord,
    SessionRecord,
)


logger = logging.getLogger(__name__)


class SessionRepository(ABC):
    """Abstract repository responsible for session persistence."""

    @abstractmethod
    async def create(self, tenant_id: str, user_id: str,
                     *, user_persona: str | None = None,
                     initial_persona_ids: List[int] = []) -> SessionRecord: ...

    @abstractmethod
    async def get(self, session_id: str) -> Optional[SessionRecord]: ...

    @abstractmethod
    async def list_sessions(self, tenant_id: str, user_id: str) -> List[SessionRecord]: ...

    @abstractmethod
    async def add_message(self, session_id: str, sender: str, content: str) -> MessageRecord: ...

    @abstractmethod
    async def list_messages(self, session_id: str, limit: int = 50) -> List[MessageRecord]: ...

    @abstractmethod
    async def update_user_persona(self, session_id: str, user_persona: str | None) -> SessionRecord: ...

    @abstractmethod
    async def update_session_participants(self, session_id: str, persona_ids: List[int]) -> SessionRecord: ...

    @abstractmethod
    async def update_session_metadata(
        self,
        session_id: str,
        *,
        title: str | None = None,
        user_display_name: str | None = None,
        user_handle: str | None = None,
        user_persona: str | None = None,
    ) -> SessionRecord: ...


class BaseSQLAlchemyRepository:
    """Shared helpers for repositories backed by SQLAlchemy async sessions."""

    def __init__(self, session_factory: async_sessionmaker | None = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    @asynccontextmanager
    async def _session_scope(self):
        session: AsyncSession = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            logger.exception("Database transaction failed; rolling back")
            await session.rollback()
            raise
        finally:
            await session.close()

    async def _get_or_create_tenant(self, db: AsyncSession, tenant_name: str) -> TenantRow:
        stmt = select(TenantRow).where(TenantRow.name == tenant_name)
        tenant = (await db.execute(stmt)).scalar_one_or_none()
        if tenant:
            return tenant
        tenant = TenantRow(name=tenant_name)
        db.add(tenant)
        await db.flush()
        return tenant

    async def _get_tenant(self, db: AsyncSession, tenant_name: str) -> TenantRow:
        stmt = select(TenantRow).where(TenantRow.name == tenant_name)
        tenant = (await db.execute(stmt)).scalar_one_or_none()
        if tenant is None:
            raise ValueError("Tenant not found")
        return tenant


class InMemorySessionRepository(SessionRepository):
    """In-memory session store with async locks for concurrency safety."""

    def __init__(self) -> None:
        self._records: Dict[str, SessionRecord] = {}
        self._messages: Dict[str, Deque[MessageRecord]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def create(self, tenant_id: str, user_id: str,
                     *, user_persona: str | None = None,
                     initial_persona_ids: List[int] = []) -> SessionRecord:
        async with self._lock:
            session_id = f"sess_{tenant_id}_{uuid.uuid4().hex[:8]}"
            participants = []
            if initial_persona_ids:
                for pid in initial_persona_ids:
                    participants.append(
                        PersonaRecord(
                            id=pid,
                            tenant_id=tenant_id,
                            name=f"persona_{pid}",
                            handle=f"persona_{pid}",
                            prompt="",
                            tone="",
                            proactivity=0.0,
                            memory_window=0,
                            max_agents_per_turn=0,
                            is_default=False,
                        )
                    )

            record = SessionRecord(
                id=session_id,
                tenant_id=tenant_id,
                user_id=user_id,
                created_at=datetime.now(timezone.utc),
                user_persona=user_persona,
                participants=participants or None,
            )
            self._records[session_id] = record
            return record

    async def get(self, session_id: str) -> Optional[SessionRecord]:
        async with self._lock:
            return self._records.get(session_id)

    async def list_sessions(self, tenant_id: str, user_id: str) -> List[SessionRecord]:
        async with self._lock:
            return [
                r for r in self._records.values() 
                if r.tenant_id == tenant_id and r.user_id == user_id
            ]

    async def add_message(self, session_id: str, sender: str, content: str) -> MessageRecord:
        async with self._lock:
            message_id = f"msg_{uuid.uuid4().hex[:8]}"
            record = MessageRecord(
                id=message_id,
                session_id=session_id,
                sender=sender,
                content=content,
                created_at=datetime.now(timezone.utc),
            )
            self._messages[session_id].append(record)
            # Limit stored history to avoid unbounded growth
            if len(self._messages[session_id]) > 200:
                self._messages[session_id].popleft()
            return record

    async def list_messages(self, session_id: str, limit: int = 50) -> List[MessageRecord]:
        async with self._lock:
            history = list(self._messages.get(session_id, ()))
            return history[-limit:]

    async def update_user_persona(self, session_id: str, user_persona: str | None) -> SessionRecord:
        async with self._lock:
            record = self._records.get(session_id)
            if record is None:
                raise ValueError("Session not found")
            updated = SessionRecord(
                id=record.id,
                tenant_id=record.tenant_id,
                user_id=record.user_id,
                created_at=record.created_at,
                user_persona=user_persona,
                participants=record.participants,
            )
            self._records[session_id] = updated
            return updated

    async def update_session_participants(self, session_id: str, persona_ids: List[int]) -> SessionRecord:
        async with self._lock:
            record = self._records.get(session_id)
            if record is None:
                raise ValueError("Session not found")
            participants = []
            for pid in persona_ids:
                participants.append(
                    PersonaRecord(
                        id=pid,
                        tenant_id=record.tenant_id,
                        name=f"persona_{pid}",
                        handle=f"persona_{pid}",
                        prompt="",
                        tone="",
                        proactivity=0.0,
                        memory_window=0,
                        max_agents_per_turn=0,
                        is_default=False,
                    )
                )

            updated = SessionRecord(
                id=record.id,
                tenant_id=record.tenant_id,
                user_id=record.user_id,
                created_at=record.created_at,
                user_persona=record.user_persona,
                participants=participants,
            )
            self._records[session_id] = updated
            return updated

    async def update_session_metadata(
        self,
        session_id: str,
        *,
        title: str | None = None,
        user_display_name: str | None = None,
        user_handle: str | None = None,
        user_persona: str | None = None,
    ) -> SessionRecord:
        async with self._lock:
            record = self._records.get(session_id)
            if record is None:
                raise ValueError("Session not found")
            updated = SessionRecord(
                id=record.id,
                tenant_id=record.tenant_id,
                user_id=record.user_id,
                created_at=record.created_at,
                user_persona=user_persona if user_persona is not None else record.user_persona,
                participants=record.participants,
                title=title if title is not None else getattr(record, "title", None),
                user_display_name=(user_display_name if user_display_name is not None else getattr(record, "user_display_name", None)),
                user_handle=(user_handle if user_handle is not None else getattr(record, "user_handle", None)),
            )
            self._records[session_id] = updated
            return updated


class PersonaDataRepository(ABC):
    """Repository responsible for persona and API profile persistence."""

    @abstractmethod
    async def get_api_profile(self, tenant_id: str, profile_id: int) -> APIProfileRecord | None: ...

    @abstractmethod
    async def create_api_profile(
        self,
        tenant_id: str,
        name: str,
        base_url: str,
        model: str,
        api_key: str,
        temperature: float | None = None,
        is_embedding_model: bool = False,
        embedding_dim: int | None = None,  # Maximum dimension supported by the model
    ) -> APIProfileRecord:
        ...

    @abstractmethod
    async def list_api_profiles(self, tenant_id: str) -> List[APIProfileRecord]: ...

    @abstractmethod
    async def update_api_profile(
        self,
        tenant_id: str,
        profile_id: int,
        *,
        name: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        temperature: float | None = None,
        is_embedding_model: bool | None = None,
        embedding_dim: int | None = None,
    ) -> APIProfileRecord:
        ...

    @abstractmethod
    async def delete_api_profile(self, tenant_id: str, profile_id: int) -> None: ...

    @abstractmethod
    async def get_persona(self, tenant_id: str, persona_id: int) -> PersonaRecord | None: ...

    @abstractmethod
    async def create_persona(
        self,
        tenant_id: str,
        name: str,
        prompt: str,
        handle: str | None,
        tone: str,
        proactivity: float,
        memory_window: int,
        max_agents_per_turn: int,
        api_profile_id: int | None,
        is_default: bool,
        background: str | None = None,
    ) -> PersonaRecord:
        ...

    @abstractmethod
    async def list_personas(self, tenant_id: str) -> List[PersonaRecord]: ...

    @abstractmethod
    async def update_persona(
        self,
        tenant_id: str,
        persona_id: int,
        *,
        name: str | None = None,
        prompt: str | None = None,
        handle: str | None = None,
        tone: str | None = None,
        proactivity: float | None = None,
        memory_window: int | None = None,
        max_agents_per_turn: int | None = None,
        api_profile_id: int | None = None,
        is_default: bool | None = None,
        background: str | None = None,
    ) -> PersonaRecord:
        ...

    @abstractmethod
    async def delete_persona(self, tenant_id: str, persona_id: int) -> None: ...

    @abstractmethod
    async def load_persona_settings(self, tenant_id: str) -> PersonaSettings: ...

    @abstractmethod
    async def get_tenant_embedding_config(self, tenant_id: str) -> dict: ...

    @abstractmethod
    async def update_tenant_embedding_config(self, tenant_id: str, api_profile_id: int | None) -> dict: ...

    @abstractmethod
    async def get_embedding_api_config_for_tenant(self, tenant_id: str) -> dict | None: ...


class SQLAlchemySessionRepository(SessionRepository, BaseSQLAlchemyRepository):
    """Persistence-backed repository that stores sessions inside Postgres."""

    def __init__(self, session_factory: async_sessionmaker | None = None,
                 persona_data_repository: PersonaDataRepository | None = None) -> None:
        BaseSQLAlchemyRepository.__init__(self, session_factory=session_factory)
        self._persona_data_repository = persona_data_repository


    async def create(self, tenant_id: str, user_id: str,
                     *, user_persona: str | None = None,
                     initial_persona_ids: List[int] = []) -> SessionRecord:
        async with self._session_scope() as db:
            logger.info(
                "Creating session (tenant=%s user=%s personas=%s)",
                tenant_id,
                user_id,
                initial_persona_ids,
            )
            tenant = await self._get_or_create_tenant(db, tenant_id)
            user = await self._get_or_create_user(db, tenant, user_id)
            
            initial_participants = []
            if initial_persona_ids:
                stmt = select(PersonaRow).where(PersonaRow.id.in_(initial_persona_ids))
                initial_participants = list((await db.execute(stmt)).scalars())
                if len(initial_participants) != len(initial_persona_ids):
                    raise ValueError("One or more initial personas not found")

            session_row = SessionRow(
                id=self._generate_session_id(tenant_id),
                tenant_id=tenant.id,
                user_id=user.id,
                status="active",
                user_persona=user_persona,
                participants=initial_participants, # Set initial participants
            )
            db.add(session_row)
            await db.flush()
            logger.info("Session created: %s", session_row.id)
            return self._to_session_record(session_row, tenant.name, user.email, session_row.participants)

    async def get(self, session_id: str) -> Optional[SessionRecord]:
        async with self._session_scope() as db:
            stmt = (
                select(SessionRow, TenantRow.name, UserRow.email)
                .join(TenantRow, SessionRow.tenant_id == TenantRow.id)
                .join(UserRow, SessionRow.user_id == UserRow.id)
                .where(SessionRow.id == session_id)
                .options(selectinload(SessionRow.participants))
            )
            result = await db.execute(stmt)
            row = result.first()
            if row is None:
                logger.info("Session not found: %s", session_id)
                return None
            session_row, tenant_name, user_email = row
            return self._to_session_record(session_row, tenant_name, user_email, session_row.participants)

    async def list_sessions(self, tenant_id: str, user_id: str) -> List[SessionRecord]:
        async with self._session_scope() as db:
            logger.info("Listing sessions for tenant=%s user=%s", tenant_id, user_id)
            try:
                stmt = (
                    select(SessionRow, TenantRow.name, UserRow.email)
                    .join(TenantRow, SessionRow.tenant_id == TenantRow.id)
                    .join(UserRow, SessionRow.user_id == UserRow.id)
                    .where(TenantRow.name == tenant_id, UserRow.email == user_id)
                    .order_by(SessionRow.created_at.desc())
                    .options(selectinload(SessionRow.participants))
                )
                rows = await db.execute(stmt)
                results = rows.all()
                logger.info("list_sessions returned %s rows", len(results))
                return [
                    self._to_session_record(session_row, tenant_name, user_email, session_row.participants)
                    for session_row, tenant_name, user_email in results
                ]
            except Exception:
                logger.exception("Failed to list sessions for tenant=%s user=%s", tenant_id, user_id)
                raise


    async def add_message(self, session_id: str, sender: str, content: str) -> MessageRecord:
        async with self._session_scope() as db:
            message_row = SessionMessageRow(
                id=self._generate_message_id(),
                session_id=session_id,
                sender_type=self._resolve_sender_type(sender),
                sender_name=sender,
                content=content,
            )
            db.add(message_row)
            await db.flush()
            logger.info(
                "Message stored session=%s sender=%s message_id=%s",
                session_id,
                sender,
                message_row.id,
            )
            return self._to_message_record(message_row)

    async def list_messages(self, session_id: str, limit: int = 50) -> List[MessageRecord]:
        async with self._session_scope() as db:
            stmt = (
                select(SessionMessageRow)
                .where(SessionMessageRow.session_id == session_id)
                .order_by(SessionMessageRow.created_at.desc())
                .limit(limit)
            )
            rows = list((await db.execute(stmt)).scalars())
            logger.info("Fetched %s messages for session=%s", len(rows), session_id)
            return [self._to_message_record(row) for row in reversed(rows)]

    async def update_user_persona(self, session_id: str, user_persona: str | None) -> SessionRecord:
        async with self._session_scope() as db:
            stmt = (
                select(SessionRow, TenantRow.name, UserRow.email)
                .join(TenantRow, SessionRow.tenant_id == TenantRow.id)
                .join(UserRow, SessionRow.user_id == UserRow.id)
                .where(SessionRow.id == session_id)
            )
            result = await db.execute(stmt)
            row = result.first()
            if row is None:
                raise ValueError("Session not found")
            session_row, tenant_name, user_email = row
            session_row.user_persona = user_persona
            db.add(session_row)
            await db.flush()
            logger.info("Updated user_persona for session=%s", session_id)
            return self._to_session_record(session_row, tenant_name, user_email, session_row.participants)

    async def update_session_participants(self, session_id: str, persona_ids: List[int]) -> SessionRecord:
        async with self._session_scope() as db:
            stmt = (
                select(SessionRow, TenantRow.name, UserRow.email)
                .join(TenantRow, SessionRow.tenant_id == TenantRow.id)
                .join(UserRow, SessionRow.user_id == UserRow.id)
                .where(SessionRow.id == session_id)
                .options(selectinload(SessionRow.participants))
            )
            result = await db.execute(stmt)
            row = result.first()
            if row is None:
                raise ValueError("Session not found")
            session_row, tenant_name, user_email = row

            unique_ids: List[int] = []
            seen: set[int] = set()
            for pid in persona_ids:
                if pid not in seen:
                    unique_ids.append(pid)
                    seen.add(pid)

            participants: List[PersonaRow] = []
            if unique_ids:
                logger.info(
                    "Updating session participants session=%s personas=%s",
                    session_id,
                    unique_ids,
                )
                persona_stmt = (
                    select(PersonaRow)
                    .where(
                        PersonaRow.id.in_(unique_ids),
                        PersonaRow.tenant_id == session_row.tenant_id,
                    )
                )
                persona_rows = list((await db.execute(persona_stmt)).scalars())
                if len(persona_rows) != len(unique_ids):
                    raise ValueError("One or more personas not found")
                persona_map = {persona.id: persona for persona in persona_rows}
                participants = [persona_map[pid] for pid in unique_ids]

            session_row.participants = participants
            db.add(session_row)
            await db.flush()
            logger.info("Session participants updated session=%s count=%s", session_id, len(participants))
            return self._to_session_record(session_row, tenant_name, user_email, participants)

    async def update_session_metadata(
        self,
        session_id: str,
        *,
        title: str | None = None,
        user_display_name: str | None = None,
        user_handle: str | None = None,
        user_persona: str | None = None,
    ) -> SessionRecord:
        async with self._session_scope() as db:
            stmt = (
                select(SessionRow, TenantRow.name, UserRow.email)
                .join(TenantRow, SessionRow.tenant_id == TenantRow.id)
                .join(UserRow, SessionRow.user_id == UserRow.id)
                .where(SessionRow.id == session_id)
                .options(selectinload(SessionRow.participants))
            )
            result = await db.execute(stmt)
            row = result.first()
            if row is None:
                raise ValueError("Session not found")
            session_row, tenant_name, user_email = row
            if title is not None:
                session_row.title = title
            if user_display_name is not None:
                session_row.user_display_name = user_display_name
            if user_handle is not None:
                session_row.user_handle = user_handle
            if user_persona is not None:
                session_row.user_persona = user_persona
            db.add(session_row)
            await db.flush()
            return self._to_session_record(session_row, tenant_name, user_email, session_row.participants)

    @staticmethod
    def _generate_session_id(tenant_id: str) -> str:
        return f"sess_{tenant_id}_{uuid.uuid4().hex[:8]}"

    @staticmethod
    def _generate_message_id() -> str:
        return f"msg_{uuid.uuid4().hex[:8]}"

    async def _get_or_create_user(self, db: AsyncSession, tenant: TenantRow, user_key: str) -> UserRow:
        stmt = select(UserRow).where(UserRow.email == user_key)
        user = (await db.execute(stmt)).scalar_one_or_none()
        if user:
            return user
        user = UserRow(tenant_id=tenant.id, email=user_key)
        db.add(user)
        await db.flush()
        return user

    @staticmethod
    def _resolve_sender_type(sender: str) -> str:
        normalized = sender.strip().lower()
        return "user" if normalized in {"user", "tenant", "human"} else "agent"

    def _to_session_record(
        self,
        row: SessionRow,
        tenant_name: str,
        user_email: str,
        participants_rows: List[PersonaRow] | None = None,
    ) -> SessionRecord:
        participants = participants_rows if participants_rows is not None else list(row.participants)
        return SessionRecord(
            id=row.id,
            tenant_id=tenant_name,
            user_id=user_email,
            created_at=self._normalize_dt(row.created_at),
            user_persona=row.user_persona,
            participants=[SQLAlchemyPersonaRepository._to_persona_record(p, tenant_name, None) for p in participants],
            title=getattr(row, "title", None),
            user_display_name=getattr(row, "user_display_name", None),
            user_handle=getattr(row, "user_handle", None),
        )

    def _to_message_record(self, row: SessionMessageRow) -> MessageRecord:
        return MessageRecord(
            id=row.id,
            session_id=row.session_id,
            sender=row.sender_name,
            content=row.content,
            created_at=self._normalize_dt(row.created_at),
        )

    @staticmethod
    def _normalize_dt(value: datetime | None) -> datetime:
        if value is None:
            return datetime.now(timezone.utc)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class SQLAlchemyPersonaRepository(PersonaDataRepository, BaseSQLAlchemyRepository):
    """Repository that manages API profiles and personas inside the database."""

    def __init__(
        self,
        session_factory: async_sessionmaker | None = None,
        *,
        encryption_key: str | None = None,
        default_memory_window: int,
        default_max_agents_per_turn: int,
        default_temperature: float,
    ) -> None:
        BaseSQLAlchemyRepository.__init__(self, session_factory=session_factory)
        self._fernet = self._build_cipher(encryption_key)
        self._default_memory_window = default_memory_window
        self._default_max_agents_per_turn = default_max_agents_per_turn
        self._default_temperature = default_temperature

    async def create_api_profile(
        self,
        tenant_id: str,
        name: str,
        base_url: str,
        model: str,
        api_key: str,
        temperature: float | None = None,
        is_embedding_model: bool = False,
        embedding_dim: int | None = None,
    ) -> APIProfileRecord:
        async with self._session_scope() as db:
            logger.info("Creating API profile '%s' for tenant=%s", name, tenant_id)
            tenant = await self._get_or_create_tenant(db, tenant_id)
            cipher = self._encrypt_api_key(api_key)
            profile = APIProfileRow(
                tenant_id=tenant.id,
                name=name,
                base_url=base_url,
                model=model,
                api_key_cipher=cipher,
                temperature=temperature if temperature is not None else self._default_temperature,
                is_embedding_model=is_embedding_model,
                embedding_dim=embedding_dim,
            )
            db.add(profile)
            await db.flush()
            logger.info("API profile created id=%s tenant=%s", profile.id, tenant_id)
            return self._to_api_profile_record(profile, tenant.name, decrypted_key=api_key)

    async def list_api_profiles(self, tenant_id: str) -> List[APIProfileRecord]:
        async with self._session_scope() as db:
            logger.info("Listing API profiles for tenant=%s", tenant_id)
            stmt = (
                select(APIProfileRow, TenantRow.name)
                .join(TenantRow, APIProfileRow.tenant_id == TenantRow.id)
                .where(TenantRow.name == tenant_id)
                .order_by(APIProfileRow.created_at.desc())
            )
            rows = await db.execute(stmt)
            records: List[APIProfileRecord] = []
            for profile, tenant_name in rows.all():
                records.append(self._to_api_profile_record(profile, tenant_name))
            return records

    async def get_api_profile(self, tenant_id: str, profile_id: int) -> APIProfileRecord | None:
        async with self._session_scope() as db:
            logger.info("Fetching API profile id=%s tenant=%s", profile_id, tenant_id)
            stmt = (
                select(APIProfileRow, TenantRow.name)
                .join(TenantRow, APIProfileRow.tenant_id == TenantRow.id)
                .where(TenantRow.name == tenant_id, APIProfileRow.id == profile_id)
            )
            result = await db.execute(stmt)
            row = result.first()
            if row is None:
                return None
            profile, tenant_name = row
            return self._to_api_profile_record(profile, tenant_name)

    async def get_api_profile_with_key(self, tenant_id: str, profile_id: int) -> dict | None:
        """Fetch API profile with decrypted key for internal use (e.g., health checks)."""
        async with self._session_scope() as db:
            logger.info("Fetching API profile with key id=%s tenant=%s", profile_id, tenant_id)
            stmt = (
                select(APIProfileRow, TenantRow.name)
                .join(TenantRow, APIProfileRow.tenant_id == TenantRow.id)
                .where(TenantRow.name == tenant_id, APIProfileRow.id == profile_id)
            )
            result = await db.execute(stmt)
            row = result.first()
            if row is None:
                return None
            profile, tenant_name = row
            return {
                "id": profile.id,
                "tenant_id": tenant_name,
                "name": profile.name,
                "base_url": profile.base_url,
                "model": profile.model,
                "temperature": profile.temperature,
                "api_key": self._decrypt_api_key(profile.api_key_cipher),
            }

    async def update_api_profile(
        self,
        tenant_id: str,
        profile_id: int,
        *,
        name: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        temperature: float | None = None,
        is_embedding_model: bool | None = None,
        embedding_dim: int | None = None,
    ) -> APIProfileRecord:
        async with self._session_scope() as db:
            logger.info("Updating API profile id=%s tenant=%s", profile_id, tenant_id)
            tenant = await self._get_tenant(db, tenant_id)
            profile = await self._assert_profile_owned(db, tenant.id, profile_id)
            if name is not None:
                profile.name = name
            if base_url is not None:
                profile.base_url = base_url
            if model is not None:
                profile.model = model
            if temperature is not None:
                profile.temperature = temperature
            if is_embedding_model is not None:
                profile.is_embedding_model = is_embedding_model
            if embedding_dim is not None:
                profile.embedding_dim = embedding_dim
            decrypted_key = None
            if api_key is not None:
                decrypted_key = api_key or None
                profile.api_key_cipher = self._encrypt_api_key(api_key)
            await db.flush()
            logger.info("API profile updated id=%s tenant=%s", profile.id, tenant_id)
            return self._to_api_profile_record(profile, tenant.name, decrypted_key=decrypted_key)

    async def delete_api_profile(self, tenant_id: str, profile_id: int) -> None:
        async with self._session_scope() as db:
            logger.info("Deleting API profile id=%s tenant=%s", profile_id, tenant_id)
            tenant = await self._get_tenant(db, tenant_id)
            profile = await self._assert_profile_owned(db, tenant.id, profile_id)
            await db.execute(
                update(PersonaRow)
                .where(PersonaRow.api_profile_id == profile.id)
                .values(api_profile_id=None)
            )
            await db.delete(profile)

    async def create_persona(
        self,
        tenant_id: str,
        name: str,
        prompt: str,
        handle: str | None,
        tone: str,
        proactivity: float,
        memory_window: int,
        max_agents_per_turn: int,
        api_profile_id: int | None,
        is_default: bool,
        background: str | None = None,
    ) -> PersonaRecord:
        async with self._session_scope() as db:
            logger.info("Creating persona '%s' for tenant=%s", name, tenant_id)
            tenant = await self._get_or_create_tenant(db, tenant_id)
            profile = None
            if api_profile_id is not None:
                profile = await self._assert_profile_owned(db, tenant.id, api_profile_id)
            normalized_handle = self._normalize_handle(handle, name)
            if is_default:
                await db.execute(
                    update(PersonaRow)
                    .where(PersonaRow.tenant_id == tenant.id)
                    .values(is_default=False)
                )
            persona = PersonaRow(
                tenant_id=tenant.id,
                name=name,
                handle=normalized_handle,
                prompt=prompt,
                tone=tone,
                proactivity=proactivity,
                memory_window=memory_window,
                max_agents_per_turn=max_agents_per_turn,
                api_profile_id=profile.id if profile else None,
                is_default=is_default,
                background=background,
            )
            db.add(persona)
            await db.flush()
            logger.info("Persona created id=%s tenant=%s", persona.id, tenant_id)
            return self._to_persona_record(persona, tenant.name, profile)

    async def list_personas(self, tenant_id: str) -> List[PersonaRecord]:
        async with self._session_scope() as db:
            logger.info("Listing personas for tenant=%s", tenant_id)
            stmt = (
                select(PersonaRow, TenantRow.name, APIProfileRow)
                .join(TenantRow, PersonaRow.tenant_id == TenantRow.id)
                .outerjoin(APIProfileRow, PersonaRow.api_profile_id == APIProfileRow.id)
                .where(TenantRow.name == tenant_id)
                .order_by(PersonaRow.id.asc())
            )
            rows = await db.execute(stmt)
            records: List[PersonaRecord] = []
            for persona, tenant_name, profile in rows.all():
                records.append(self._to_persona_record(persona, tenant_name, profile))
            return records

    async def get_persona_by_id(self, persona_id: int) -> PersonaRecord | None:
        """Fetch a persona by ID without requiring tenant_id (for internal use)."""
        async with self._session_scope() as db:
            logger.info("Fetching persona by id=%s", persona_id)
            stmt = (
                select(PersonaRow, TenantRow.name, APIProfileRow)
                .join(TenantRow, PersonaRow.tenant_id == TenantRow.id)
                .outerjoin(APIProfileRow, PersonaRow.api_profile_id == APIProfileRow.id)
                .where(PersonaRow.id == persona_id)
            )
            result = await db.execute(stmt)
            row = result.first()
            if row is None:
                return None
            persona, tenant_name, profile = row
            return self._to_persona_record(persona, tenant_name, profile)

    async def get_persona(self, tenant_id: str, persona_id: int) -> PersonaRecord | None:
        async with self._session_scope() as db:
            logger.info("Fetching persona id=%s tenant=%s", persona_id, tenant_id)
            stmt = (
                select(PersonaRow, TenantRow.name, APIProfileRow)
                .join(TenantRow, PersonaRow.tenant_id == TenantRow.id)
                .outerjoin(APIProfileRow, PersonaRow.api_profile_id == APIProfileRow.id)
                .where(TenantRow.name == tenant_id, PersonaRow.id == persona_id)
            )
            result = await db.execute(stmt)
            row = result.first()
            if row is None:
                return None
            persona, tenant_name, profile = row
            return self._to_persona_record(persona, tenant_name, profile)

    async def update_persona(
        self,
        tenant_id: str,
        persona_id: int,
        *,
        name: str | None = None,
        prompt: str | None = None,
        handle: str | None = None,
        tone: str | None = None,
        proactivity: float | None = None,
        memory_window: int | None = None,
        max_agents_per_turn: int | None = None,
        api_profile_id: int | None = None,
        is_default: bool | None = None,
        background: str | None = None,
    ) -> PersonaRecord:
        async with self._session_scope() as db:
            logger.info("Updating persona id=%s tenant=%s", persona_id, tenant_id)
            tenant = await self._get_tenant(db, tenant_id)
            persona = await self._assert_persona_owned(db, tenant.id, persona_id)
            profile_row = None
            if api_profile_id is not None:
                if api_profile_id > 0:
                    profile_row = await self._assert_profile_owned(db, tenant.id, api_profile_id)
                    persona.api_profile_id = profile_row.id
                else:
                    persona.api_profile_id = None
            elif persona.api_profile_id:
                profile_row = await db.get(APIProfileRow, persona.api_profile_id)
            if name is not None:
                persona.name = name
            if prompt is not None:
                persona.prompt = prompt
            if handle is not None:
                persona.handle = self._normalize_handle(handle, name or persona.name)
            if tone is not None:
                persona.tone = tone
            if proactivity is not None:
                persona.proactivity = proactivity
            if memory_window is not None:
                persona.memory_window = memory_window
            if max_agents_per_turn is not None:
                persona.max_agents_per_turn = max_agents_per_turn
            if is_default is not None:
                if is_default:
                    await db.execute(
                        update(PersonaRow)
                        .where(PersonaRow.tenant_id == tenant.id)
                        .values(is_default=False)
                    )
                persona.is_default = is_default
            if background is not None:
                persona.background = background
            await db.flush()
            logger.info("Persona updated id=%s tenant=%s", persona_id, tenant_id)
            if profile_row is None and persona.api_profile_id:
                profile_row = await db.get(APIProfileRow, persona.api_profile_id)
            return self._to_persona_record(persona, tenant.name, profile_row)

    async def delete_persona(self, tenant_id: str, persona_id: int) -> None:
        async with self._session_scope() as db:
            logger.info("Deleting persona id=%s tenant=%s", persona_id, tenant_id)
            tenant = await self._get_tenant(db, tenant_id)
            persona = await self._assert_persona_owned(db, tenant.id, persona_id)
            await db.delete(persona)

    async def load_persona_settings(self, tenant_id: str) -> PersonaSettings:
        async with self._session_scope() as db:
            logger.info("Loading persona settings for tenant=%s", tenant_id)
            stmt = (
                select(PersonaRow, APIProfileRow)
                .join(TenantRow, PersonaRow.tenant_id == TenantRow.id)
                .outerjoin(APIProfileRow, PersonaRow.api_profile_id == APIProfileRow.id)
                .where(TenantRow.name == tenant_id)
            )
            rows = await db.execute(stmt)
            items = rows.all()

        personas: List[Persona] = []
        memory_candidates: List[int] = []
        agent_candidates: List[int] = []
        for persona_row, api_row in items:
            persona = Persona(
                name=persona_row.name,
                handle=persona_row.handle,
                prompt=persona_row.prompt,
                tone=persona_row.tone,
                proactivity=persona_row.proactivity,
                id=persona_row.id, # Add this line
            )
            if api_row:
                persona.api = PersonaAPIConfig(
                    model=api_row.model,
                    base_url=api_row.base_url,
                    api_key=self._decrypt_api_key(api_row.api_key_cipher),
                    temperature=api_row.temperature,
                )
            personas.append(persona)
            if persona_row.memory_window:
                memory_candidates.append(persona_row.memory_window)
            if persona_row.max_agents_per_turn:
                agent_candidates.append(persona_row.max_agents_per_turn)

        memory_window = (
            max(memory_candidates) if memory_candidates else self._default_memory_window
        )
        max_agents_per_turn = (
            max(agent_candidates) if agent_candidates else self._default_max_agents_per_turn
        )
        return PersonaSettings(
            personas=personas,
            max_agents_per_turn=max_agents_per_turn,
            memory_window=memory_window,
        )

    async def get_persona_api_config(self, persona_id: int) -> dict | None:
        async with self._session_scope() as db:
            stmt = (
                select(APIProfileRow)
                .join(PersonaRow, PersonaRow.api_profile_id == APIProfileRow.id)
                .where(PersonaRow.id == persona_id)
            )
            row = (await db.execute(stmt)).scalar_one_or_none()
            if row is None:
                return None
            
            return {
                "model": row.model,
                "base_url": row.base_url,
                "api_key": self._decrypt_api_key(row.api_key_cipher),
                "temperature": row.temperature,
            }

    async def get_tenant_embedding_config(self, tenant_id: str) -> dict:
        """Get the tenant's global embedding API profile configuration"""
        async with self._session_scope() as db:
            logger.info("Fetching tenant embedding config for tenant=%s", tenant_id)
            tenant = await self._get_tenant(db, tenant_id)
            
            if tenant.embedding_api_profile_id is None:
                return {
                    "api_profile_id": None,
                    "api_profile_name": None,
                    "api_model": None,
                    "api_base_url": None,
                }
            
            profile = await db.get(APIProfileRow, tenant.embedding_api_profile_id)
            if profile is None:
                return {
                    "api_profile_id": None,
                    "api_profile_name": None,
                    "api_model": None,
                    "api_base_url": None,
                }
            
            return {
                "api_profile_id": profile.id,
                "api_profile_name": profile.name,
                "api_model": profile.model,
                "api_base_url": profile.base_url,
            }

    async def update_tenant_embedding_config(self, tenant_id: str, api_profile_id: int | None) -> dict:
        """Update the tenant's global embedding API profile configuration"""
        async with self._session_scope() as db:
            logger.info("Updating tenant embedding config tenant=%s profile_id=%s", tenant_id, api_profile_id)
            tenant = await self._get_tenant(db, tenant_id)
            
            # Validate the profile exists and belongs to this tenant if not None
            if api_profile_id is not None:
                profile = await self._assert_profile_owned(db, tenant.id, api_profile_id)
                tenant.embedding_api_profile_id = profile.id
            else:
                tenant.embedding_api_profile_id = None
            
            await db.flush()
            logger.info("Tenant embedding config updated tenant=%s", tenant_id)
            
            # Return the updated config
            return await self.get_tenant_embedding_config(tenant_id)

    async def get_embedding_api_config_for_tenant(self, tenant_id: str) -> dict | None:
        """Get the tenant's embedding API config with decrypted API key for actual use"""
        async with self._session_scope() as db:
            tenant = await self._get_tenant(db, tenant_id)
            
            if tenant.embedding_api_profile_id is None:
                return None
            
            profile = await db.get(APIProfileRow, tenant.embedding_api_profile_id)
            if profile is None:
                return None
            
            return {
                "model": profile.model,
                "base_url": profile.base_url,
                "api_key": self._decrypt_api_key(profile.api_key_cipher),
                "temperature": profile.temperature,
            }

    async def _assert_profile_owned(self, db: AsyncSession, tenant_db_id: int, profile_id: int) -> APIProfileRow:
        stmt = select(APIProfileRow).where(
            APIProfileRow.id == profile_id,
            APIProfileRow.tenant_id == tenant_db_id,
        )
        profile = (await db.execute(stmt)).scalar_one_or_none()
        if profile is None:
            raise ValueError("API profile does not belong to tenant")
        return profile

    async def _assert_persona_owned(self, db: AsyncSession, tenant_db_id: int, persona_id: int) -> PersonaRow:
        stmt = select(PersonaRow).where(
            PersonaRow.id == persona_id,
            PersonaRow.tenant_id == tenant_db_id,
        )
        persona = (await db.execute(stmt)).scalar_one_or_none()
        if persona is None:
            raise ValueError("Persona does not belong to tenant")
        return persona

    @staticmethod
    def _normalize_handle(handle: str | None, name: str) -> str:
        if handle:
            return handle
        return name.strip().lower().replace(" ", "_")

    def _to_api_profile_record(
        self,
        row: APIProfileRow,
        tenant_name: str,
        *,
        decrypted_key: str | None = None,
    ) -> APIProfileRecord:
        preview = self._mask_key(decrypted_key or self._decrypt_api_key(row.api_key_cipher))
        created_at = row.created_at or datetime.now(timezone.utc)
        return APIProfileRecord(
            id=row.id,
            tenant_id=tenant_name,
            name=row.name,
            base_url=row.base_url,
            model=row.model,
            temperature=row.temperature,
            created_at=created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc),
            api_key_preview=preview,
            is_embedding_model=getattr(row, 'is_embedding_model', False),
            embedding_dim=getattr(row, 'embedding_dim', None),
        )

    @staticmethod
    def _to_persona_record(
        row: PersonaRow,
        tenant_name: str,
        profile: APIProfileRow | None,
    ) -> PersonaRecord:
        return PersonaRecord(
            id=row.id,
            tenant_id=tenant_name,
            name=row.name,
            handle=row.handle,
            prompt=row.prompt,
            tone=row.tone,
            proactivity=row.proactivity,
            memory_window=row.memory_window,
            max_agents_per_turn=row.max_agents_per_turn,
            is_default=row.is_default,
            background=row.background,
            api_profile_id=profile.id if profile else None,
            api_profile_name=profile.name if profile else None,
            api_model=profile.model if profile else None,
            api_base_url=profile.base_url if profile else None,
            temperature=profile.temperature if profile else None,
        )

    def _encrypt_api_key(self, api_key: str) -> str:
        if not api_key:
            return ""
        if self._fernet is None:
            return api_key
        token = self._fernet.encrypt(api_key.encode("utf-8"))
        return token.decode("utf-8")

    def _decrypt_api_key(self, cipher_text: str | None) -> str | None:
        if not cipher_text:
            return None
        if self._fernet is None:
            return cipher_text
        try:
            return self._fernet.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
        except Exception:  # pragma: no cover - fallback to raw value
            return cipher_text

    @staticmethod
    def _mask_key(value: str | None) -> str | None:
        if not value:
            return None
        visible = value[-4:]
        return f"****{visible}"

    @staticmethod
    def _build_cipher(encryption_key: str | None) -> Fernet | None:
        if not encryption_key:
            return None
        digest = hashlib.sha256(encryption_key.encode("utf-8")).digest()
        derived = base64.urlsafe_b64encode(digest)
        return Fernet(derived)
