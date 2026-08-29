"""SQLAlchemy engine and session management."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from darwin.config import Settings, get_settings


def get_engine(settings: Settings | None = None) -> Engine:
    """Create a SQLAlchemy engine from application settings."""

    resolved_settings = settings or get_settings()
    return create_engine(resolved_settings.database_url, pool_pre_ping=True)


def get_session_factory(settings: Settings | None = None) -> sessionmaker[Session]:
    """Create a configured SQLAlchemy session factory."""

    return sessionmaker(bind=get_engine(settings), autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope(settings: Settings | None = None) -> Iterator[Session]:
    """Provide a transactional scope around a sequence of operations."""

    session = get_session_factory(settings)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
