from .base import BaseModel, RunModel, ResultModel

from .cookie import Cookie
from .account import Account
from .card import Card
from .session import Session
from .email import Email
from .badge import Badge, BadgeOwned
from .bundle import Bundle, BundleOwned
from .gamepass import Gamepass, GamepassOwned
from .group import Group, GroupOwned
from .place import Place, PlaceOwned, PlacePlayed, PlaceFavorited
from .product import Product, ProductOwned
from .roblox_badge import RobloxBadge, RobloxBadgeOwned

from .cookie_checker import CookieCheckerRun, CookieCheckerResult

from .cookie_refresher import CookieRefresherRun, CookieRefresherResult

from .cookie_sorter import CookieSorterRun, CookieSorterResult

from .transaction import Transaction

from .transaction_analysis import TransactionAnalysisRun, TransactionAnalysisResult


def load_models() -> None:
    _ = (
        BaseModel,
        RunModel,
        ResultModel,

        Cookie,

        Account,
        
        Card,
        Session,
        Email,
        
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
        
        CookieCheckerRun,
        CookieCheckerResult,

        CookieRefresherRun,
        CookieRefresherResult,

        CookieSorterRun,
        CookieSorterResult,
        
        Transaction,
        
        TransactionAnalysisRun,
        TransactionAnalysisResult,
    )


__all__ = (
    "BaseModel",
    "RunModel",
    "ResultModel",

    "Cookie",

    "Account",

    "Card",
    "Session",
    "Email",

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
    
    "CookieCheckerRun",
    "CookieCheckerResult",

    "CookieRefresherRun",
    "CookieRefresherResult",
    
    "CookieSorterRun",
    "CookieSorterResult",
    
    "Transaction",
    
    "TransactionAnalysisRun",
    "TransactionAnalysisResult",

    "load_models",
)