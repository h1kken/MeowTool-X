from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import CookieCheckerBase
from src.db.models.mixins import BaseMixin, SessionMixin

if TYPE_CHECKING:
    from . import CookieCheckerResult


class Session(CookieCheckerBase, BaseMixin, SessionMixin):
    __tablename__ = "sessions"

    result_ref_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
    result: Mapped["CookieCheckerResult"] = relationship(back_populates="sessions")
