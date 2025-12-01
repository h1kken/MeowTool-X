from sqlalchemy import Column, Integer, String, Boolean, JSON, Index
from sqlalchemy.orm import DeclarativeBase


class BaseCookieChecker(DeclarativeBase):
    ...


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
    p_cookie                    = Column(String, nullable=False)

    def __repr__(self) -> str:
        return f'<Account[{self.id}]: {self.p_id} | {self.p_display_name} (@{self.p_name}) | {self.p_valid}>'

Index('idx_p_id', Account.p_id)
Index('idx_p_name', Account.p_name)