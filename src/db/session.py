from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from src.db.paths import PATH_APP_DATABASE

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _configure_sqlite(dbapi_connection: sqlite3.Connection, _record: object) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def database_url() -> str:
    return f"sqlite:///{PATH_APP_DATABASE.as_posix()}"


def get_engine() -> Engine:
    global _engine

    if _engine is None:
        engine = create_engine(
            database_url(),
            future=True,
            echo=False,
        )
        event.listen(engine, "connect", _configure_sqlite)
        _engine = engine

    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory

    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            class_=Session,
            autoflush=False,
            expire_on_commit=False,
        )

    return _session_factory


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


__all__ = ("database_url", "get_engine", "get_session_factory", "session_scope")
