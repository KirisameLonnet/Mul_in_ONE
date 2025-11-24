"""Repository interfaces and implementations for backend services."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional

from cryptography.fernet import Fernet
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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


class SessionRepository(ABC):
    """Abstract repository responsible for session persistence."""

    @abstractmethod
    async def create(self, tenant_id: str, user_id: str) -> SessionRecord: ...

    @abstractmethod
    async def get(self, session_id: str) -> Optional[SessionRecord]: ...

    @abstractmethod
    async def list_sessions(self, tenant_id: str, user_id: str) -> List[SessionRecord]: ...

    @abstractmethod
    async def add_message(self, session_id: str, sender: str, content: str) -> MessageRecord: ...

    @abstractmethod
    async def list_messages(self, session_id: str, limit: int = 50) -> List[MessageRecord]: ...


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

    async def create(self, tenant_id: str, user_id: str) -> SessionRecord:
        async with self._lock:
            session_id = f"sess_{tenant_id}_{uuid.uuid4().hex[:8]}"
            record = SessionRecord(id=session_id, tenant_id=tenant_id, user_id=user_id)
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
            record = MessageRecord(id=message_id, session_id=session_id, sender=sender, content=content)
            self._messages[session_id].append(record)
            # Limit stored history to avoid unbounded growth
            if len(self._messages[session_id]) > 200:
                self._messages[session_id].popleft()
            return record

    async def list_messages(self, session_id: str, limit: int = 50) -> List[MessageRecord]:
        async with self._lock:
            history = list(self._messages.get(session_id, ()))
            return history[-limit:]


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
    ) -> PersonaRecord:
        ...

    @abstractmethod
    async def delete_persona(self, tenant_id: str, persona_id: int) -> None: ...

    @abstractmethod
    async def load_persona_settings(self, tenant_id: str) -> PersonaSettings: ...


class SQLAlchemySessionRepository(SessionRepository, BaseSQLAlchemyRepository):
    """Persistence-backed repository that stores sessions inside Postgres."""

    def __init__(self, session_factory: async_sessionmaker | None = None) -> None:
        BaseSQLAlchemyRepository.__init__(self, session_factory=session_factory)

    async def create(self, tenant_id: str, user_id: str) -> SessionRecord:
        async with self._session_scope() as db:
            tenant = await self._get_or_create_tenant(db, tenant_id)
            user = await self._get_or_create_user(db, tenant, user_id)
            session_row = SessionRow(
                id=self._generate_session_id(tenant_id),
                tenant_id=tenant.id,
                user_id=user.id,
                status="active",
            )
            db.add(session_row)
            await db.flush()
            return self._to_session_record(session_row, tenant.name, user.email)

    async def get(self, session_id: str) -> Optional[SessionRecord]:
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
                return None
            session_row, tenant_name, user_email = row
            return self._to_session_record(session_row, tenant_name, user_email)

    async def list_sessions(self, tenant_id: str, user_id: str) -> List[SessionRecord]:
        print("\n[DEBUG] Entering list_sessions method.")
        print(f"[DEBUG] tenant_id = {tenant_id}, user_id = {user_id}")
        async with self._session_scope() as db:
            try:
                stmt = (
                    select(SessionRow, TenantRow.name, UserRow.email)
                    .join(TenantRow, SessionRow.tenant_id == TenantRow.id)
                    .join(UserRow, SessionRow.user_id == UserRow.id)
                    .where(TenantRow.name == tenant_id, UserRow.email == user_id)
                    .order_by(SessionRow.created_at.desc())
                )
                print(f"[DEBUG] Executing SQLAlchemy statement...")
                rows = await db.execute(stmt)
                
                results = rows.all()
                print(f"[DEBUG] Query executed. Found {len(results)} rows.")

                processed_records = []
                for i, (session_row, tenant_name, user_email) in enumerate(results):
                    print(f"[DEBUG] Processing row {i}: session_id={session_row.id}, tenant_name={tenant_name}, user_email={user_email}")
                    record = self._to_session_record(session_row, tenant_name, user_email)
                    processed_records.append(record)
                
                print("[DEBUG] Finished processing all rows. Returning records.")
                return processed_records
            except Exception as e:
                print(f"[DEBUG] An exception occurred inside list_sessions: {e}")
                import traceback
                traceback.print_exc()
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
            return [self._to_message_record(row) for row in reversed(rows)]

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

    def _to_session_record(self, row: SessionRow, tenant_name: str, user_email: str) -> SessionRecord:
        return SessionRecord(
            id=row.id,
            tenant_id=tenant_name,
            user_id=user_email,
            created_at=self._normalize_dt(row.created_at),
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
    ) -> APIProfileRecord:
        async with self._session_scope() as db:
            tenant = await self._get_or_create_tenant(db, tenant_id)
            cipher = self._encrypt_api_key(api_key)
            profile = APIProfileRow(
                tenant_id=tenant.id,
                name=name,
                base_url=base_url,
                model=model,
                api_key_cipher=cipher,
                temperature=temperature if temperature is not None else self._default_temperature,
            )
            db.add(profile)
            await db.flush()
            return self._to_api_profile_record(profile, tenant.name, decrypted_key=api_key)

    async def list_api_profiles(self, tenant_id: str) -> List[APIProfileRecord]:
        async with self._session_scope() as db:
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
    ) -> APIProfileRecord:
        async with self._session_scope() as db:
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
            decrypted_key = None
            if api_key is not None:
                decrypted_key = api_key or None
                profile.api_key_cipher = self._encrypt_api_key(api_key)
            await db.flush()
            return self._to_api_profile_record(profile, tenant.name, decrypted_key=decrypted_key)

    async def delete_api_profile(self, tenant_id: str, profile_id: int) -> None:
        async with self._session_scope() as db:
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
    ) -> PersonaRecord:
        async with self._session_scope() as db:
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
            )
            db.add(persona)
            await db.flush()
            return self._to_persona_record(persona, tenant.name, profile)

    async def list_personas(self, tenant_id: str) -> List[PersonaRecord]:
        async with self._session_scope() as db:
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

    async def get_persona(self, tenant_id: str, persona_id: int) -> PersonaRecord | None:
        async with self._session_scope() as db:
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
    ) -> PersonaRecord:
        async with self._session_scope() as db:
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
            await db.flush()
            if profile_row is None and persona.api_profile_id:
                profile_row = await db.get(APIProfileRow, persona.api_profile_id)
            return self._to_persona_record(persona, tenant.name, profile_row)

    async def delete_persona(self, tenant_id: str, persona_id: int) -> None:
        async with self._session_scope() as db:
            tenant = await self._get_tenant(db, tenant_id)
            persona = await self._assert_persona_owned(db, tenant.id, persona_id)
            await db.delete(persona)

    async def load_persona_settings(self, tenant_id: str) -> PersonaSettings:
        async with self._session_scope() as db:
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
        )

    def _to_persona_record(
        self,
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
