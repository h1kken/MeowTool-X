from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, BigInteger, Boolean, Integer, JSON, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models import BaseModel, RunModel, ResultModel


class CookieCheckerRun(RunModel):
    __tablename__ = "runs"


class GroupOwned(BaseModel):
    __tablename__ = "groups_owned"

    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)

    group_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(128))
    members_count: Mapped[int | None] = mapped_column(Integer)
    robux_pending: Mapped[int | None] = mapped_column(BigInteger)
    robux_funds: Mapped[int | None] = mapped_column(BigInteger)

    result: Mapped["CookieCheckerResult"] = relationship(back_populates="groups_owned")


class Place(BaseModel):
    __tablename__ = "places"

    place_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(128))


class PlaceOwned(BaseModel):
    __tablename__ = "places_owned"

    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.place_id"), index=True)
    visits: Mapped[int | None] = mapped_column(Integer) # idk why it here

    place: Mapped["Place"] = relationship()


class CookieCheckerResult(ResultModel):
    __tablename__ = "results"

    is_valid: Mapped[bool] = mapped_column(Boolean)
    
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    name: Mapped[str | None] = mapped_column(String(128))
    display_name: Mapped[str | None] = mapped_column(String(128))
    country_code: Mapped[str | None] = mapped_column(String(2))
    registration_date: Mapped[datetime | None] = mapped_column(DateTime)

    robux: Mapped[int | None] = mapped_column(BigInteger)
    billing: Mapped[int | None] = mapped_column(BigInteger)
    pending: Mapped[int | None] = mapped_column(BigInteger)
    donate_period: Mapped[str | None] = mapped_column(String(5))
    donate_period_amount: Mapped[int | None] = mapped_column(BigInteger)
    donate_all_time: Mapped[int | None] = mapped_column(BigInteger)
    rap: Mapped[int | None] = mapped_column(BigInteger)
    сard
    premium: Mapped[bool | None] = mapped_column(Boolean)
    gamepasses
    custom_gamepasses
    badges
    favorite_places
    places_weekly_playtime
    bundles
    sessions: 
    has_email: Mapped[bool | None] = mapped_column(Boolean)
    has_phone: Mapped[bool | None] = mapped_column(Boolean)
    has_2fa: Mapped[bool | None] = mapped_column(Boolean)
    has_pin: Mapped[bool | None] = mapped_column(Boolean)
    groups_owned: Mapped[list["GroupOwned"] | None] = relationship(back_populates="result")
    places_owned: Mapped[list["PlaceOwned"] | None] = relationship()
    age_group: Mapped[str | None] = mapped_column(String(3))
    is_verified_age: Mapped[bool | None] = mapped_column(Boolean)
    is_verified_voice: Mapped[bool | None] = mapped_column(Boolean)
    friends: Mapped[int | None] = mapped_column(Integer)
    followers: Mapped[int | None] = mapped_column(Integer)
    followings: Mapped[int | None] = mapped_column(Integer)
    roblox_badges
    
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    
    cookie: Mapped[str] = mapped_column(Text)



__all__ = ("CookieCheckerResult",)
