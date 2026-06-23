from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import RunBoundModel
from src.db.types import JsonValue


# TODO: columns
class CookieCheckerResult(RunBoundModel):
    __tablename__ = "cookie_checker_results"

    cookie: Mapped[str] = mapped_column(Text)
    is_valid: Mapped[bool | None] = mapped_column(Boolean)
    user_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    name: Mapped[str | None] = mapped_column(String(128))
    display_name: Mapped[str | None] = mapped_column(String(128))
    robux: Mapped[int | None] = mapped_column(Integer)
    country_code: Mapped[str | None] = mapped_column(String(8))
    payload_json: Mapped[JsonValue | None] = mapped_column(JSON)


__all__ = ("CookieCheckerResult",)
