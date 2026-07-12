from __future__ import annotations

import sqlite3
from collections.abc import Generator, Iterable, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import Engine, Table, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.sql.schema import MetaData

from src.app.paths import PATH_DATABASES

if TYPE_CHECKING:
    from src.db.facade import DatabaseFacade

DatabaseTarget = str | Path | None


def _configure_sqlite(dbapi_connection: sqlite3.Connection, _record: object) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _looks_like_path(value: str) -> bool:
    if value.lower().endswith((".db", ".sqlite", ".sqlite3")):
        return True

    if "/" in value or "\\" in value:
        return True

    return Path(value).drive != ""


class DatabaseHandle:
    def __init__(
        self,
        *,
        name: str,
        path: Path,
        echo: bool = False,
        autoflush: bool = False,
        expire_on_commit: bool = False,
    ) -> None:
        self._name = name
        self._path = path
        self._echo = echo
        self._autoflush = autoflush
        self._expire_on_commit = expire_on_commit
        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def path(self) -> Path:
        return self._path

    @property
    def url(self) -> str:
        return f"sqlite:///{self._path.as_posix()}"

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._path.parent.mkdir(parents=True, exist_ok=True)

            engine = create_engine(
                self.url,
                echo=self._echo,
                poolclass=NullPool,
            )
            event.listen(engine, "connect", _configure_sqlite)
            self._engine = engine

        return self._engine

    @property
    def session_factory(self) -> sessionmaker[Session]:
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                class_=Session,
                autoflush=self._autoflush,
                expire_on_commit=self._expire_on_commit,
            )

        return self._session_factory

    def session(self) -> Session:
        return self.session_factory()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        session = self.session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def facade_scope(self) -> Generator[DatabaseFacade, None, None]:
        from src.db.facade import build_facade

        with self.session_scope() as session:
            yield build_facade(session)

    def create_all(
        self,
        *,
        metadata: MetaData | None = None,
        models: Iterable[type[object]] = (),
        tables: Iterable[Table] = (),
    ) -> DatabaseHandle:
        self.engine
        self.session_factory
        collected_tables = self._collect_tables(models=models, tables=tables)
        if metadata is None and not collected_tables:
            return self

        if metadata is not None:
            metadata.create_all(self.engine)
            return self

        for current_metadata, current_tables in self._group_tables_by_metadata(collected_tables):
            current_metadata.create_all(self.engine, tables=current_tables)
        return self

    def dispose(self) -> None:
        if self._engine is not None:
            self._engine.dispose()

        self._engine = None
        self._session_factory = None

    @staticmethod
    def _collect_tables(
        *,
        models: Iterable[type[object]],
        tables: Iterable[Table],
    ) -> list[Table]:
        collected: list[Table] = []
        seen: set[int] = set()

        for table in tables:
            table_id = id(table)
            if table_id in seen:
                continue
            collected.append(table)
            seen.add(table_id)

        for model_type in models:
            table = getattr(model_type, "__table__", None)
            if not isinstance(table, Table):
                raise TypeError(f"{model_type!r} does not expose a mapped __table__")

            table_id = id(table)
            if table_id in seen:
                continue
            collected.append(table)
            seen.add(table_id)

        return collected

    @staticmethod
    def _group_tables_by_metadata(
        tables: Sequence[Table],
    ) -> list[tuple[MetaData, list[Table]]]:
        groups: list[tuple[MetaData, list[Table]]] = []

        for table in tables:
            table_metadata = table.metadata
            for current_metadata, current_tables in groups:
                if current_metadata is table_metadata:
                    current_tables.append(table)
                    break
            else:
                groups.append((table_metadata, [table]))

        return groups


class DatabaseManager:
    def __init__(
        self,
        *,
        echo: bool = False,
        autoflush: bool = False,
        expire_on_commit: bool = False,
    ) -> None:
        self._handles_by_name: dict[str, DatabaseHandle] = {}
        self._handles_by_path: dict[Path, DatabaseHandle] = {}
        # not used in this module
        self._echo = echo
        self._autoflush = autoflush
        self._expire_on_commit = expire_on_commit

    def register(self, name: str, path: str | Path | None = None) -> DatabaseHandle:
        resolved_path = self._resolve_named_path(name, path)
        handle = self._handles_by_path.get(resolved_path)

        if handle is None:
            handle = DatabaseHandle(
                name=name,
                path=resolved_path,
                echo=self._echo,
                autoflush=self._autoflush,
                expire_on_commit=self._expire_on_commit,
            )
            self._handles_by_path[resolved_path] = handle

        self._handles_by_name[name] = handle
        return handle

    def database(self, target: DatabaseTarget = None) -> DatabaseHandle:
        if target is None:
            return self.register(self._default_name)

        if isinstance(target, Path):
            return self._handle_for_path(target)

        if _looks_like_path(target):
            return self._handle_for_path(Path(target))

        return self.register(target)

    def engine(self, target: DatabaseTarget = None) -> Engine:
        return self.database(target).engine

    def session_factory(self, target: DatabaseTarget = None) -> sessionmaker[Session]:
        return self.database(target).session_factory

    def session(self, target: DatabaseTarget = None) -> Session:
        return self.database(target).session()

    @contextmanager
    def session_scope(self, target: DatabaseTarget = None) -> Generator[Session, None, None]:
        with self.database(target).session_scope() as session:
            yield session

    @contextmanager
    def facade_scope(self, target: DatabaseTarget = None) -> Generator[DatabaseFacade, None, None]:
        with self.database(target).facade_scope() as facade:
            yield facade

    def create_all(
        self,
        target: DatabaseTarget = None,
        *,
        metadata: MetaData | None = None,
        models: Iterable[type[object]] = (),
        tables: Iterable[Table] = (),
    ) -> DatabaseHandle:
        handle = self.database(target)
        handle.create_all(metadata=metadata, models=models, tables=tables)
        return handle

    def dispose(self, target: DatabaseTarget = None) -> None:
        self.database(target).dispose()

    def dispose_all(self) -> None:
        for handle in list(self._handles_by_path.values()):
            handle.dispose()

        self._handles_by_name.clear()
        self._handles_by_path.clear()

    def _handle_for_path(self, path: Path) -> DatabaseHandle:
        resolved_path = self._resolve_path(path)
        handle = self._handles_by_path.get(resolved_path)

        if handle is None:
            handle = DatabaseHandle(
                name=resolved_path.stem,
                path=resolved_path,
                echo=self._echo,
                autoflush=self._autoflush,
                expire_on_commit=self._expire_on_commit,
            )
            self._handles_by_path[resolved_path] = handle

        return handle

    def _resolve_named_path(self, name: str, path: str | Path | None) -> Path:
        if path is not None:
            return self._resolve_path(Path(path))

        filename = name if name.lower().endswith(".db") else f"{name}.db"
        return self._resolve_path(PATH_DATABASES / filename)

    @staticmethod
    def _resolve_path(path: Path) -> Path:
        return path.expanduser().resolve()


__all__ = ("DatabaseHandle", "DatabaseManager", "DatabaseTarget")
