from typing import Any, Type, Generator
from contextlib import contextmanager
from sqlalchemy import create_engine, select, exists
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase


class Database:
    def __init__(self, db_path: str, echo: bool = False):
        self._engine = create_engine(
            db_path,
            connect_args={'check_same_thread': False},
            echo=echo
        )
        self._sessionmaker = sessionmaker(self._engine, autoflush=False, autocommit=False)

    def create_tables(self, base: DeclarativeBase) -> None:
        base.metadata.create_all(self._engine)
    
    def create_session(self) -> Session:
        return self._sessionmaker()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        _session: Session = self._sessionmaker()
        try:
            yield _session
            _session.commit()
        except Exception:
            _session.rollback()
            raise
        finally:
            _session.close()
            
    def record_exists(self, session: Session, model: Type, **filters: Any) -> bool:
        conditions = [getattr(model, key) == value for key, value in filters.items()]
        selection = select(exists().where(*conditions))
        return session.execute(selection).scalar()