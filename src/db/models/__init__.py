from src.db.models.cookie_checker_result import CookieCheckerResult
from src.db.models.cookie_refresher_result import CookieRefresherResult
from src.db.models.cookie_sorter_result import CookieSorterResult


def load_models() -> None:
    _ = (
        CookieCheckerResult,
        CookieRefresherResult,
        CookieSorterResult,
    )


__all__ = (
    "CookieCheckerResult",
    "CookieRefresherResult",
    "CookieSorterResult",
    "load_models",
)
