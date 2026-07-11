from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models import BaseModel

if TYPE_CHECKING:
    from src.db.models import (
        Place,
        CookieCheckerResult,
    )


class Badge(BaseModel):
    __tablename__ = "badges"
    
    badge_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))

    place_id: Mapped[int] = mapped_column(ForeignKey("places.place_id"), index=True)
    place: Mapped["Place"] = relationship(back_populates="badges")

    owned_records: Mapped[list["BadgeOwned"]] = relationship(back_populates="badge")


class BadgeOwned(BaseModel):
    __tablename__ = "badges_owned"

    badge_id: Mapped[int] = mapped_column(ForeignKey("badges.id"), index=True)
    badge: Mapped["Badge"] = relationship(back_populates="owned_records")

    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
    result: Mapped["CookieCheckerResult"] = relationship(back_populates="badges")
