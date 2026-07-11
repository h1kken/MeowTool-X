from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models import BaseModel

if TYPE_CHECKING:
    from src.db.models import CookieCheckerResult


class RobloxBadge(BaseModel):
    __tablename__ = "roblox_badges"
    
    roblox_badge_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(16))

    owned_records: Mapped[list["RobloxBadgeOwned"]] = relationship(back_populates="roblox_badge")


class RobloxBadgeOwned(BaseModel):
    __tablename__ = "roblox_badges_owned"
    
    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
    result: Mapped["CookieCheckerResult"] = relationship(back_populates="roblox_badges")

    roblox_badge_id: Mapped[int] = mapped_column(ForeignKey("roblox_badges.badge_id"), index=True)
    roblox_badge: Mapped["RobloxBadge"] = relationship(back_populates="owned_records")
