from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Type

from sqlalchemy import create_engine, event, exists, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Database:
    def __init__(self, db_path: str, *, echo: bool = False):
        self._db_url = self._normalize_url(db_path)
        self._engine = create_engine(
            self._db_url,
            connect_args=self._connect_args(self._db_url),
            echo=echo,
            future=True,
            pool_pre_ping=True,
        )
        if self._is_sqlite_url(self._db_url):
            event.listen(self._engine, 'connect', self._on_sqlite_connect)

        self._sessionmaker = sessionmaker(
            bind=self._engine,
            autoflush=False,
            expire_on_commit=False,
            future=True,
        )

    @staticmethod
    def _normalize_url(db_path: str) -> str:
        if '://' in db_path:
            return db_path
        return f"sqlite:///{Path(db_path).resolve().as_posix()}"

    @staticmethod
    def _is_sqlite_url(url: str) -> bool:
        return url.startswith('sqlite')

    @staticmethod
    def _connect_args(url: str) -> dict[str, Any]:
        if url.startswith('sqlite'):
            return {'check_same_thread': False}
        return {}

    @staticmethod
    def _on_sqlite_connect(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute('PRAGMA foreign_keys=ON;')
            cursor.execute('PRAGMA journal_mode=WAL;')
            cursor.execute('PRAGMA synchronous=NORMAL;')
            cursor.execute('PRAGMA busy_timeout=5000;')
            cursor.execute('PRAGMA temp_store=MEMORY;')
        finally:
            cursor.close()

    @property
    def engine(self) -> Engine:
        return self._engine

    def create_tables(self, *bases: Type[DeclarativeBase]) -> None:
        for base in bases:
            base.metadata.create_all(self._engine)

    def drop_tables(self, *bases: Type[DeclarativeBase]) -> None:
        for base in bases:
            base.metadata.drop_all(self._engine)

    def create_session(self) -> Session:
        return self._sessionmaker()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        session: Session = self._sessionmaker()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def record_exists(self, session: Session, model: Type, **filters: Any) -> bool:
        conditions = []
        for key, value in filters.items():
            if not hasattr(model, key):
                raise AttributeError(f'{model.__name__} has no column "{key}"')
            conditions.append(getattr(model, key) == value)

        if conditions:
            stmt = select(exists(select(1).select_from(model).where(*conditions)))
        else:
            stmt = select(exists(select(1).select_from(model)))
        return bool(session.execute(stmt).scalar())

    def dispose(self) -> None:
        self._engine.dispose()

