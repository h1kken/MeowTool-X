from __future__ import annotations

import json
from typing import Iterable

from sqlalchemy import JSON, Boolean, Column, Integer, String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator


class BaseCookieChecker(DeclarativeBase):
    pass


class StringSetJSON(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return '[]'
        if isinstance(value, str):
            return json.dumps([value], ensure_ascii=False)
        if isinstance(value, (set, list, tuple)):
            normalized = sorted({str(item) for item in value if item})
            return json.dumps(normalized, ensure_ascii=False)
        raise TypeError(f'Unsupported value for StringSetJSON: {type(value)!r}')

    def process_result_value(self, value, dialect):
        if value is None:
            return set()
        if isinstance(value, (list, tuple, set)):
            return {str(item) for item in value if item}

        raw = str(value).strip()
        if not raw:
            return set()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {raw}

        if isinstance(parsed, str):
            return {parsed}
        if isinstance(parsed, (list, tuple, set)):
            return {str(item) for item in parsed if item}
        return set()


class Account(BaseCookieChecker):
    __tablename__ = 'accounts'
    
    id                          = Column(Integer, primary_key=True)
    # account keys
    p_valid                     = Column(Boolean)
    p_country_registration      = Column(String)
    p_id                        = Column(String, index=True)
    p_name                      = Column(String, index=True)
    p_display_name              = Column(String)
    p_registration_date_dmy     = Column(String)
    p_registration_date_in_days = Column(Integer)
    p_robux                     = Column(Integer)
    p_billing                   = Column(Integer)
    p_pending                   = Column(Integer)
    p_donate_1_year             = Column(Integer)
    p_donate_all_time           = Column(Integer)
    p_rap                       = Column(Integer)
    p_cards                     = Column(JSON, default=dict)
    p_premium                   = Column(Boolean)
    p_gamepasses                = Column(JSON, default=dict)
    p_custom_gamepasses         = Column(JSON, default=dict)
    p_badges                    = Column(JSON, default=dict)
    p_favorite_places           = Column(JSON, default=dict)
    p_places_weekly_playtime    = Column(JSON, default=dict)
    p_bundles                   = Column(JSON, default=dict)
    p_inventory_privacy         = Column(String)
    p_trade_privacy             = Column(String)
    p_can_trade                 = Column(Boolean)
    p_sessions                  = Column(JSON, default=dict)
    p_email                     = Column(JSON, default=dict)
    p_phone                     = Column(Boolean)
    p_twofa                     = Column(Boolean)
    p_pin                       = Column(Boolean)
    p_groups_owned              = Column(JSON, default=dict)
    p_groups_members            = Column(Integer)
    p_groups_pending            = Column(Integer)
    p_groups_funds              = Column(Integer)
    p_place_visits              = Column(Integer)
    p_age_group                 = Column(JSON, default=dict)
    p_verified_age              = Column(Boolean)
    p_verified_voice            = Column(Boolean)
    p_friends                   = Column(Integer)
    p_followers                 = Column(Integer)
    p_followings                = Column(Integer)
    p_roblox_badges             = Column(JSON, default=dict)
    p_cookie                    = Column(StringSetJSON, default=set, nullable=False)

    def cookies(self) -> set[str]:
        value = self.p_cookie
        if isinstance(value, set):
            return set(value)
        if isinstance(value, str):
            return {value}
        if isinstance(value, (list, tuple)):
            return {str(item) for item in value if item}
        return set()

    def set_cookies(self, cookies: Iterable[str] | None) -> set[str]:
        normalized = {
            str(cookie).strip()
                for cookie in (cookies or [])
                    if str(cookie).strip()
        }
        self.p_cookie = normalized
        return normalized

    def add_cookie(self, cookie: str) -> bool:
        cookie = str(cookie).strip()
        if not cookie:
            return False

        current = self.cookies()
        before = len(current)
        current.add(cookie)
        self.p_cookie = current
        return len(current) > before

    def merge_cookies(self, cookies: Iterable[str] | None) -> int:
        if not cookies:
            return 0

        current = self.cookies()
        before = len(current)
        current.update(str(cookie).strip() for cookie in cookies if str(cookie).strip())
        self.p_cookie = current
        return len(current) - before

    def __repr__(self) -> str:
        return f'<Account[{self.id}]: {self.p_id} | {self.p_display_name} (@{self.p_name}) | {self.p_valid} | cookies={len(self.cookies())}>'
