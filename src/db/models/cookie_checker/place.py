from __future__ import annotations

import typing as t

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import CookieCheckerBase
from src.db.models.mixins import BaseMixin, PlaceMixin, ResultPlaceMixin

if t.TYPE_CHECKING:
    from . import CookieCheckerResult, Badge, Gamepass, Product


class Place(CookieCheckerBase, BaseMixin, PlaceMixin):
    __tablename__ = 'places'

    extended: Mapped['PlaceExtended | None'] = relationship(back_populates='place', uselist=False)


class PlaceExtended(CookieCheckerBase, BaseMixin):
    __tablename__ = 'places_extended'

    place_ref_id: Mapped[int] = mapped_column(ForeignKey('places.id'), unique=True)
    place: Mapped['Place'] = relationship(back_populates='extended')
    
    visits: Mapped[int | None] = mapped_column(Integer)
    
    badges: Mapped[list['Badge']] = relationship(back_populates='place')
    gamepasses: Mapped[list['Gamepass']] = relationship(back_populates='place')
    products: Mapped[list['Product']] = relationship(back_populates='place')


class PlaceOwned(CookieCheckerBase, BaseMixin, ResultPlaceMixin):
    __tablename__ = 'places_owned'

    place: Mapped['Place'] = relationship()
    result: Mapped['CookieCheckerResult'] = relationship(back_populates='places_owned')


class PlacePlayed(CookieCheckerBase, BaseMixin, ResultPlaceMixin):
    __tablename__ = 'places_played'

    minutes_played: Mapped[int | None] = mapped_column(Integer)
    
    place: Mapped['Place'] = relationship()
    result: Mapped['CookieCheckerResult'] = relationship(back_populates='places_played')


class PlaceFavorited(CookieCheckerBase, BaseMixin, ResultPlaceMixin):
    __tablename__ = 'places_favorited'

    place: Mapped['Place'] = relationship()
    result: Mapped['CookieCheckerResult'] = relationship(back_populates='places_favorited')
