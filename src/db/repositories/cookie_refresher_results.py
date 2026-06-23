from __future__ import annotations

from sqlalchemy.orm import Session

from src.db.models import CookieRefresherResult
from src.db.repositories.base import RunBoundRepository


class CookieRefresherResultRepository(RunBoundRepository[CookieRefresherResult]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, CookieRefresherResult)


__all__ = ("CookieRefresherResultRepository",)
