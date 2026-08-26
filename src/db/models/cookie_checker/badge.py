from __future__ import annotations

import typing as t

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.mixins import BaseMixin, BadgeMixin, ResultBadgeMixin

from .base import CookieCheckerBase

if t.TYPE_CHECKING:
    from . import CookieCheckerResult, Place


class Badge(CookieCheckerBase, BaseMixin, BadgeMixin):
    __tablename__ = 'badges'

    place_ref_id: Mapped[int] = mapped_column(ForeignKey('places.id'), index=True)
    place: Mapped['Place'] = relationship(back_populates='badges')


class BadgeOwned(CookieCheckerBase, BaseMixin, ResultBadgeMixin):
    __tablename__ = 'badges_owned'

    badge: Mapped['Badge'] = relationship()
    result: Mapped['CookieCheckerResult'] = relationship(back_populates='badges')
