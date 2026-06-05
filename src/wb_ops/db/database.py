"""SQLite database configuration for the WB operations management system.

The project is designed to run directly on Windows during Phase 1. By default,
the SQLite database file is created under the repository's ``data`` directory.
Set ``SQLITE_DB_PATH`` in the environment to override the location.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "data" / "wb_ops.sqlite3"
DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{os.getenv('SQLITE_DB_PATH', DEFAULT_DB_PATH)}"


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""


def get_engine(database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine.

    SQLite needs ``check_same_thread=False`` when sessions may be used by a
    scheduler or dashboard thread in the same local Windows process.
    """

    url = database_url or DATABASE_URL
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, echo=False, future=True, connect_args=connect_args)


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@contextmanager
def get_db() -> Iterator[Session]:
    """Yield a database session and close it automatically."""

    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create_db_and_tables(database_engine: Engine | None = None) -> None:
    """Create all database tables declared in ``models.py``."""

    # Import models here so metadata is populated before create_all runs.
    from wb_ops.db import models  # noqa: F401

    bind = database_engine or engine
    if bind.url.get_backend_name() == "sqlite":
        db_path = bind.url.database
        if db_path and db_path != ":memory":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=bind)
