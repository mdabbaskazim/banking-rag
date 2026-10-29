"""Database session and engine management.

Complies with ARCHITECTURE.md Section 8, 9 & 12:
- Connection pool pre-ping to handle Neon scale-to-zero cold starts.
- Clean session life cycle and disposal.
- Configurable URL for testing and migrations.
"""

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from bankrag.core.config import Settings, get_settings


def normalize_database_url(url: str) -> str:
    """Ensure database URL is properly formatted for SQLAlchemy with psycopg driver."""
    if not url:
        return "sqlite:///:memory:"
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def get_engine(settings: Settings | None = None, **kwargs: Any) -> Engine:
    """Create an Engine with pool_pre_ping enabled for Neon cold starts."""
    current_settings = settings or get_settings()
    url = normalize_database_url(current_settings.database_url)

    engine_kwargs: dict[str, Any] = {
        "pool_pre_ping": True,
        **kwargs,
    }

    # Set connection timeout for PostgreSQL
    if "postgresql" in url:
        engine_kwargs["connect_args"] = {"connect_timeout": 10}

    return create_engine(url, **engine_kwargs)


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Return a sessionmaker bound to the engine."""
    eng = engine or get_engine()
    return sessionmaker(bind=eng, expire_on_commit=False)


def get_db_session() -> Generator[Session, None, None]:
    """Dependency for yielding a database session."""
    factory = get_session_factory()
    with factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
