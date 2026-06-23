from __future__ import annotations

from sqlalchemy.orm import Session

from src.db.models import CookieCheckerResult
from src.db.repositories.base import RunBoundRepository


class CookieCheckerResultRepository(RunBoundRepository[CookieCheckerResult]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, CookieCheckerResult)


__all__ = ("CookieCheckerResultRepository",)
