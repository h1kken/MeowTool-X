from src.db.models.base import BaseModel, RunModel, ResultModel

# checker
from src.db.models.account import Account
from src.db.models.badges import Badge, BadgeOwned
from src.db.models.bundles import Bundle, BundleOwned
from src.db.models.gamepasses import Gamepass, GamepassOwned
from src.db.models.groups import Group, GroupOwned
from src.db.models.places import Place, PlaceOwned, PlacePlayed, PlaceFavorited
from src.db.models.products import Product, ProductOwned
from src.db.models.roblox_badges import RobloxBadge, RobloxBadgeOwned
from src.db.models.cookie_checker import (
    CookieCheckerResult,
    Card,
    Session,
    Email,
)

# refresher
from src.db.models.cookie_refresher_result import CookieRefresherResult

# sorter
from src.db.models.cookie_sorter_result import CookieSorterResult


def load_models() -> None:
    _ = (
        BaseModel,
        RunModel,
        ResultModel,

        Account,
        
        Badge,
        BadgeOwned,

        Bundle,
        BundleOwned,

        Gamepass,
        GamepassOwned,
        
        Group,
        GroupOwned,

        Place,
        PlaceOwned,
        PlacePlayed,
        PlaceFavorited,

        Product,
        ProductOwned,

        RobloxBadge,
        RobloxBadgeOwned,
        
        Card,
        Session,
        Email,
        CookieCheckerResult,

        CookieRefresherResult,
        CookieSorterResult,
    )


__all__ = (
    "BaseModel",
    "RunModel",
    "ResultModel",

    "Account",

    "Badge",
    "BadgeOwned",

    "Bundle",
    "BundleOwned",

    "Gamepass",
    "GamepassOwned",

    "Group",
    "GroupOwned",

    "Place",
    "PlaceOwned",
    "PlacePlayed",
    "PlaceFavorited",

    "Product",
    "ProductOwned",

    "RobloxBadge",
    "RobloxBadgeOwned",

    "Card",
    "Session",
    "Email",
    "CookieCheckerResult",

    "CookieRefresherResult",
    "CookieSorterResult",

    "load_models",
)