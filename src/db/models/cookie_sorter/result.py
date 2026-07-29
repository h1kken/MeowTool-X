from __future__ import annotations

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import CookieSorterResultBase


class CookieSorterResult(CookieSorterResultBase):
    __tablename__ = 'results'

    cookies: Mapped[list[str]] = mapped_column(JSON)
