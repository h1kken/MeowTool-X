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

    extended: Mapped["PlaceExtended | None"] = relationship(back_populates="place", uselist=False)


class PlaceExtended(BaseModel):
    __tablename__ = "places_extended"
    
    place_id: Mapped[int] = mapped_column(ForeignKey("places.place_id"), unique=True)
    place: Mapped["Place"] = relationship(back_populates="extended")
    
    visits: Mapped[int | None] = mapped_column(Integer)
    
    badges: Mapped[list["Badge"]] = relationship(back_populates="place")
    gamepasses: Mapped[list["Gamepass"]] = relationship(back_populates="place")
    products: Mapped[list["Product"]] = relationship(back_populates="place")

    owned_records: Mapped[list["PlaceOwned"]] = relationship(back_populates="place")
    played_records: Mapped[list["PlacePlayed"]] = relationship(back_populates="place")
    favorited_records: Mapped[list["PlaceFavorited"]] = relationship(back_populates="place")


class PlaceOwned(BaseModel):
    __tablename__ = "places_owned"

    place_id: Mapped[int] = mapped_column(ForeignKey("places.place_id"), index=True)
    place: Mapped["Place"] = relationship(back_populates="owned_records")

    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
    result: Mapped["CookieCheckerResult"] = relationship(back_populates="places_owned")


class PlacePlayed(BaseModel):
    __tablename__ = "places_played"

    place_id: Mapped[int] = mapped_column(ForeignKey("places.place_id"), index=True)
    place: Mapped["Place"] = relationship(back_populates="played_records")
    
    minutes_played: Mapped[int | None] = mapped_column(Integer)

    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
    result: Mapped["CookieCheckerResult"] = relationship(back_populates="places_played")


class PlaceFavorited(BaseModel):
    __tablename__ = "places_favorited"

    place_id: Mapped[int] = mapped_column(ForeignKey("places.place_id"), index=True)
    place: Mapped["Place"] = relationship(back_populates="favorited_records")

    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
    result: Mapped["CookieCheckerResult"] = relationship(back_populates="places_favorited")
