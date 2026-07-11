from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models import BaseModel

if TYPE_CHECKING:
    from src.db.models import (
        Badge, Gamepass, Product,
        CookieCheckerResult,
    )


class Place(BaseModel):
    __tablename__ = "places"

    place_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(128))
    visits: Mapped[int | None] = mapped_column(Integer)
    
    badges: Mapped[list["Badge"]] = relationship(back_populates="place")
    gamepasses: Mapped[list["Gamepass"]] = relationship(back_populates="place")
    products: Mapped[list["Product"]] = relationship(back_populates="place")

    owned_records: Mapped[list["PlaceOwned"]] = relationship(back_populates="place")
    played_records: Mapped[list["PlacePlayed"]] = relationship(back_populates="place")
    favorited_records: Mapped[list["PlaceFavorited"]] = relationship(back_populates="place")


class PlaceOwned(BaseModel):
    __tablename__ = "places_owned"

    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.place_id"), index=True)

    result: Mapped["CookieCheckerResult"] = relationship(back_populates="places_owned")

    place: Mapped["Place"] = relationship(back_populates="owned_records")


class PlacePlayed(BaseModel):
    __tablename__ = "places_played"

    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.place_id"), index=True)
    minutes_played: Mapped[int | None] = mapped_column(Integer)

    result: Mapped["CookieCheckerResult"] = relationship(back_populates="places_played")

    place: Mapped["Place"] = relationship(back_populates="played_records")


class PlaceFavorited(BaseModel):
    __tablename__ = "places_favorited"

    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.place_id"), index=True)

    result: Mapped["CookieCheckerResult"] = relationship(back_populates="places_favorited")

    place: Mapped["Place"] = relationship(back_populates="favorited_records")
