"""SQLAlchemy models for Mul-in-One backend."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# Association table for the many-to-many relationship between sessions and personas
session_participants_table = Table(
    "session_participants",
    Base.metadata,
    Column("session_id", String, ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True),
    Column("persona_id", Integer, ForeignKey("personas.id", ondelete="CASCADE"), primary_key=True),
)


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(32), default="free")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    users: Mapped[list["User"]] = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_user_tenant_email"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")
    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="user", cascade="all, delete-orphan")


class APIProfile(Base):
    __tablename__ = "api_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(64))
    base_url: Mapped[str] = mapped_column(String(255))
    model: Mapped[str] = mapped_column(String(255))
    api_key_cipher: Mapped[str] = mapped_column(Text)
    temperature: Mapped[float] = mapped_column(default=0.4)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(128))
    handle: Mapped[str] = mapped_column(String(128))
    prompt: Mapped[str] = mapped_column(Text)
    tone: Mapped[str] = mapped_column(String(64), default="neutral")
    proactivity: Mapped[float] = mapped_column(default=0.5)
    memory_window: Mapped[int] = mapped_column(default=8)
    max_agents_per_turn: Mapped[int] = mapped_column(default=2)
    api_profile_id: Mapped[int | None] = mapped_column(ForeignKey("api_profiles.id"))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    sessions: Mapped[list["Session"]] = relationship(
        "Session", secondary=session_participants_table, back_populates="participants"
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_persona: Mapped[str | None] = mapped_column(Text, nullable=True)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="sessions")
    user: Mapped["User"] = relationship("User", back_populates="sessions")
    messages: Mapped[list["SessionMessage"]] = relationship(
        "SessionMessage", back_populates="session", cascade="all, delete-orphan"
    )
    participants: Mapped[list["Persona"]] = relationship(
        "Persona", secondary=session_participants_table, back_populates="sessions"
    )


class SessionMessage(Base):
    __tablename__ = "session_messages"

    id: Mapped[str] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"))
    sender_type: Mapped[str] = mapped_column(String(32))
    sender_name: Mapped[str] = mapped_column(String(128))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["Session"] = relationship("Session", back_populates="messages")