from __future__ import annotations

from sqlalchemy import Boolean, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import RunBoundModel
from src.db.types import JsonValue


# TODO: columns
class CookieRefresherResult(RunBoundModel):
    __tablename__ = "cookie_refresher_results"

    input_cookie: Mapped[str] = mapped_column(Text)
    refreshed_cookie: Mapped[str | None] = mapped_column(Text)
    is_success: Mapped[bool | None] = mapped_column(Boolean, index=True)
    message: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[JsonValue | None] = mapped_column(JSON)


__all__ = ("CookieRefresherResult",)
