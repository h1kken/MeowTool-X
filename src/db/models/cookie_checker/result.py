from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, BigInteger, Boolean, Integer, JSON, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import CookieCheckerResultBase

if TYPE_CHECKING:
    from . import (
        Cookie, Account, Card,
        Session, Email, BadgeOwned,
        GamepassOwned, ProductOwned, PlaceFavorited,
        PlacePlayed, PlaceOwned, BundleOwned,
        GroupOwned, RobloxBadgeOwned,
    )


class CookieCheckerResult(CookieCheckerResultBase):
    __tablename__ = "results"

    is_valid: Mapped[bool] = mapped_column(Boolean)
    
    account_ref_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), index=True)
    account: Mapped["Account | None"] = relationship()
    
    country_code: Mapped[str | None] = mapped_column(String(2))
    registration_date: Mapped[datetime | None] = mapped_column(DateTime)

    robux: Mapped[int | None] = mapped_column(BigInteger)
    billing: Mapped[int | None] = mapped_column(BigInteger)
    pending: Mapped[int | None] = mapped_column(BigInteger)
    donate_period: Mapped[str | None] = mapped_column(String(5))
    donate_period_amount: Mapped[int | None] = mapped_column(BigInteger)
    donate_all_time: Mapped[int | None] = mapped_column(BigInteger)
    rap: Mapped[int | None] = mapped_column(BigInteger)
    
    is_card_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    card: Mapped[list["Card"] | None] = relationship(back_populates="result")
    
    has_premium: Mapped[bool | None] = mapped_column(Boolean)
    
    is_badges_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    badges: Mapped[list["BadgeOwned"]] = relationship(back_populates="result")

    is_gamepasses_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    gamepasses: Mapped[list["GamepassOwned"]] = relationship(back_populates="result")

    is_products_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    products: Mapped[list["ProductOwned"]] = relationship(back_populates="result")

    is_places_favorited_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    places_favorited: Mapped[list["PlaceFavorited"]] = relationship(back_populates="result")

    is_places_played_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    places_played: Mapped[list["PlacePlayed"]] = relationship(back_populates="result")

    is_places_owned_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    places_owned: Mapped[list["PlaceOwned"]] = relationship(back_populates="result")

    is_bundles_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    bundles: Mapped[list["BundleOwned"]] = relationship(back_populates="result")

    sessions: Mapped[list["Session"]] = relationship(back_populates="result")
    email: Mapped["Email | None"] = relationship(back_populates="result", uselist=False)
    has_phone: Mapped[bool | None] = mapped_column(Boolean)
    has_2fa: Mapped[bool | None] = mapped_column(Boolean)
    has_pin: Mapped[bool | None] = mapped_column(Boolean)
    
    is_groups_owned_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    groups_owned: Mapped[list["GroupOwned"]] = relationship(back_populates="result")

    age_group: Mapped[str | None] = mapped_column(String(3))
    is_verified_age: Mapped[bool | None] = mapped_column(Boolean)
    is_verified_voice: Mapped[bool | None] = mapped_column(Boolean)
    friends: Mapped[int | None] = mapped_column(Integer)
    followers: Mapped[int | None] = mapped_column(Integer)
    followings: Mapped[int | None] = mapped_column(Integer)
    
    is_roblox_badges_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    roblox_badges: Mapped[list["RobloxBadgeOwned"]] = relationship(back_populates="result")
    
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    
    cookie_ref_id: Mapped[int] = mapped_column(ForeignKey("cookies.id"))
    cookie: Mapped["Cookie"] = relationship(back_populates="cookie")
