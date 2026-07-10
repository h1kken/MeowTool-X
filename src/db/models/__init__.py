from src.db.models.base import BaseModel, RunModel, ResultModel
from src.db.models.cookie_checker_result import CookieCheckerResult
from src.db.models.cookie_refresher_result import CookieRefresherResult
from src.db.models.cookie_sorter_result import CookieSorterResult


def load_models() -> None:
    _ = (
        BaseModel,
        RunModel,
        ResultModel,
        CookieCheckerResult,
        CookieRefresherResult,
        CookieSorterResult,
    )


__all__ = (
    "BaseModel",
    "RunModel",
    "ResultModel",
    "CookieCheckerResult",
    "CookieRefresherResult",
    "CookieSorterResult",
    "load_models",
)
