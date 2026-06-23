from __future__ import annotations

from sqlalchemy.orm import Session

from src.db.models import CookieSorterResult
from src.db.repositories.base import RunBoundRepository


class CookieSorterResultRepository(RunBoundRepository[CookieSorterResult]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, CookieSorterResult)


__all__ = ("CookieSorterResultRepository",)
