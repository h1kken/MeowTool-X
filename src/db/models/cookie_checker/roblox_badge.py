from __future__ import annotations

import typing as t

from sqlalchemy.orm import Mapped, relationship

from src.db.mixins import BaseMixin, RobloxBadgeMixin, ResultRobloxBadgeMixin

from .base import CookieCheckerBase

if t.TYPE_CHECKING:
    from . import CookieCheckerResult


class RobloxBadge(CookieCheckerBase, BaseMixin, RobloxBadgeMixin):
    __tablename__ = 'roblox_badges'


class RobloxBadgeOwned(CookieCheckerBase, BaseMixin, ResultRobloxBadgeMixin):
    __tablename__ = 'roblox_badges_owned'
    
    roblox_badge: Mapped['RobloxBadge'] = relationship()
    result: Mapped['CookieCheckerResult'] = relationship(back_populates='roblox_badges')
