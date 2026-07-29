from __future__ import annotations

from sqlalchemy import Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import CookieRefresherResultBase


class CookieRefresherResult(CookieRefresherResultBase):
    __tablename__ = 'results'

    is_valid: Mapped[bool | None] = mapped_column(Boolean, index=True)
    
    input_cookie: Mapped[str] = mapped_column(Text)
    output_cookie: Mapped[str | None] = mapped_column(Text)
