from __future__ import annotations

import typing as t

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import CookieCheckerBase
from src.db.models.mixins import BaseMixin, GamepassMixin, ResultGamepassMixin

if t.TYPE_CHECKING:
    from . import CookieCheckerResult, Place


class Gamepass(CookieCheckerBase, BaseMixin, GamepassMixin):
    __tablename__ = "gamepasses"

    place_ref_id: Mapped[int] = mapped_column(ForeignKey("places.id"), index=True)
    place: Mapped["Place"] = relationship(back_populates="gamepasses")


class GamepassOwned(CookieCheckerBase, BaseMixin, ResultGamepassMixin):
    __tablename__ = "gamepasses_owned"

    gamepass: Mapped["Gamepass"] = relationship()
    result: Mapped["CookieCheckerResult"] = relationship(back_populates="gamepasses")
