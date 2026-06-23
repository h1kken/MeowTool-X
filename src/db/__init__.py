from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

__all__ = (
    "Base",
    "BaseRepository",
    "CookieCheckerResultRepository",
    "CookieCheckerResult",
    "CookieRefresherResultRepository",
    "CookieRefresherResult",
    "CookieSorterResultRepository",
    "CookieSorterResult",
    "DatabaseFacade",
    "JsonScalar",
    "JsonValue",
    "RunBoundRepository",
    "RunBoundModel",
    "build_facade",
    "database_scope",
    "get_engine",
    "get_session_factory",
    "initialize_database",
    "load_models",
    "session_scope",
    "utc_now",
)

_EXPORT_MODULES: dict[str, str] = {
    "Base": "src.db.base",
    "RunBoundModel": "src.db.base",
    "utc_now": "src.db.base",
    "DatabaseFacade": "src.db.facade",
    "build_facade": "src.db.facade",
    "database_scope": "src.db.facade",
    "initialize_database": "src.db.init",
    "CookieCheckerResult": "src.db.models",
    "CookieRefresherResult": "src.db.models",
    "CookieSorterResult": "src.db.models",
    "load_models": "src.db.models",
    "BaseRepository": "src.db.repositories",
    "CookieCheckerResultRepository": "src.db.repositories",
    "CookieRefresherResultRepository": "src.db.repositories",
    "CookieSorterResultRepository": "src.db.repositories",
    "RunBoundRepository": "src.db.repositories",
    "get_engine": "src.db.session",
    "get_session_factory": "src.db.session",
    "session_scope": "src.db.session",
    "JsonScalar": "src.db.types",
    "JsonValue": "src.db.types",
}

if TYPE_CHECKING:
    from src.db.base import Base, RunBoundModel, utc_now
    from src.db.facade import DatabaseFacade, build_facade, database_scope
    from src.db.init import initialize_database
    from src.db.models import (
        CookieCheckerResult,
        CookieRefresherResult,
        CookieSorterResult,
        load_models,
    )
    from src.db.repositories import (
        BaseRepository,
        CookieCheckerResultRepository,
        CookieRefresherResultRepository,
        CookieSorterResultRepository,
        RunBoundRepository,
    )
    from src.db.session import get_engine, get_session_factory, session_scope
    from src.db.types import JsonScalar, JsonValue


def __getattr__(name: str) -> Any:
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name)
    return getattr(module, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
