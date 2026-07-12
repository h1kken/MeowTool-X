from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from src.utils.filesystem import FS


class DatabaseHandler:
    def __init__(
        self,
        name: str,
        path: Path,
        base: type[DeclarativeBase],
        *,
        echo: bool = False,
        autoflush: bool = False,
        expire_on_commit: bool = False,
    ) -> None:
        self.name = name
        self.path = path
        self.base = base
        
        self._echo = echo
        self._autoflush = autoflush
        self._expire_on_commit = expire_on_commit
        
        self.engine = create_engine(
            f"sqlite:///{path.as_posix()}",
            echo=False,
        )

        self._session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

    def ensure_initialized(self) -> None:
        FS.ensure_dir(self.path)
        self.base.metadata.create_all(self.engine)

    def session(self) -> Session:
        self.ensure_initialized()
        return self._session_factory()