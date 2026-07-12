from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, relationship

from .base import CookieCheckerBase
from src.db.models.mixins import BaseMixin, RobloxBadgeMixin, ResultRobloxBadgeMixin

if TYPE_CHECKING:
    from . import CookieCheckerResult


class RobloxBadge(CookieCheckerBase, BaseMixin, RobloxBadgeMixin):
    __tablename__ = "roblox_badges"


class RobloxBadgeOwned(CookieCheckerBase, BaseMixin, ResultRobloxBadgeMixin):
    __tablename__ = "roblox_badges_owned"
    
    roblox_badge: Mapped["RobloxBadge"] = relationship()
    result: Mapped["CookieCheckerResult"] = relationship(back_populates="roblox_badges")
