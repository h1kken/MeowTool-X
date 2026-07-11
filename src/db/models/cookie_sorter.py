from __future__ import annotations

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.db.models import RunModel, ResultModel


class CookieSorterRun(RunModel):
    __tablename__ = "runs"


class CookieSorterResult(ResultModel):
    __tablename__ = "results"

    cookies: Mapped[list[str]] = mapped_column(JSON)


__all__ = (
    "CookieRefresherRun",
    "CookieSorterResult",
)
