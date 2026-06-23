from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.db.repositories import (
    CookieCheckerResultRepository,
    CookieRefresherResultRepository,
    CookieSorterResultRepository,
)
from src.db.session import session_scope


@dataclass(slots=True)
class DatabaseFacade:
    session: Session
    checker_results: CookieCheckerResultRepository
    sorter_results: CookieSorterResultRepository
    refresher_results: CookieRefresherResultRepository


def build_facade(session: Session) -> DatabaseFacade:
    return DatabaseFacade(
        session=session,
        checker_results=CookieCheckerResultRepository(session),
        sorter_results=CookieSorterResultRepository(session),
        refresher_results=CookieRefresherResultRepository(session),
    )


@contextmanager
def database_scope() -> Generator[DatabaseFacade, None, None]:
    with session_scope() as session:
        yield build_facade(session)


__all__ = ("DatabaseFacade", "build_facade", "database_scope")
