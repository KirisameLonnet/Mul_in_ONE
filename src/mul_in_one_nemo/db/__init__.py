"""Database utilities for Mul-in-One backend."""

from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from mul_in_one_nemo.config import Settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker | None = None


def get_engine(settings: Settings | None = None) -> AsyncEngine:
    global _engine
    if _engine is not None:
        return _engine
    resolved = settings or Settings.from_env()
    _engine = create_async_engine(resolved.database_url, future=True, echo=False)
    return _engine


def get_session_factory(settings: Settings | None = None) -> async_sessionmaker:
    global _session_factory
    if _session_factory is not None:
        return _session_factory
    engine = get_engine(settings)
    _session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return _session_factory


@asynccontextmanager
async def session_scope(settings: Settings | None = None):
    session_factory = get_session_factory(settings)
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
