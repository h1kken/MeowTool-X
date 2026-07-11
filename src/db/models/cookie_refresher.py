from __future__ import annotations

from sqlalchemy import Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.models import RunModel, ResultModel


class CookieRefresherRun(RunModel):
    __tablename__ = "runs"


class CookieRefresherResult(ResultModel):
    __tablename__ = "results"

    is_valid: Mapped[bool | None] = mapped_column(Boolean, index=True)
    
    input_cookie: Mapped[str] = mapped_column(Text)
    output_cookie: Mapped[str | None] = mapped_column(Text)


__all__ = (
    "CookieRefresherRun",
    "CookieRefresherResult",
)
