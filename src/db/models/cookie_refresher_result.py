from __future__ import annotations

from sqlalchemy import Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.models import BaseModel


# TODO: columns
class CookieRefresherResult(BaseModel):
    __tablename__ = "cookie_refresher_results"

    input_cookie: Mapped[str] = mapped_column(Text)
    refreshed_cookie: Mapped[str | None] = mapped_column(Text)
    is_success: Mapped[bool | None] = mapped_column(Boolean, index=True)
    message: Mapped[str | None] = mapped_column(Text)


__all__ = ("CookieRefresherResult",)
