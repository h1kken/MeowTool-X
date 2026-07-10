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


class Gamepass(BaseModel):
    __tablename__ = "gamepasses"

    place_id: Mapped[int] = mapped_column(ForeignKey("places.place_id"), index=True)
    
    gamepass_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))

    owned_records: Mapped[list["GamepassOwned"]] = relationship(back_populates="gamepass")

    place: Mapped["Place"] = relationship(back_populates="gamepasses")


class GamepassOwned(BaseModel):
    __tablename__ = "gamepasses_owned"

    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
    
    gamepass_id: Mapped[int] = mapped_column(ForeignKey("gamepasses.id"), index=True)

    result: Mapped["CookieCheckerResult"] = relationship(back_populates="gamepasses")

    gamepass: Mapped["Gamepass"] = relationship(back_populates="owned_records")
