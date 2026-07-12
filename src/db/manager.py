from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from sqlalchemy.orm import DeclarativeBase

from src.app.paths import (
    PATH_ROBLOX_COOKIE_CHECKER_DB,
    PATH_ROBLOX_COOKIE_SORTER_DB,
    PATH_ROBLOX_COOKIE_REFRESHER_DB,
)
from src.db.handler import DatabaseHandler


class DatabaseName(StrEnum):
    COOKIE_CHECKER = "cookie_checker"
    COOKIE_SORTER = "cookie_sorter"
    COOKIE_REFRESHER = "cookie_refresher"


@dataclass(frozen=True)
class DatabaseConfig:
    path: Path
    base: type[DeclarativeBase]


DATABASES: dict[DatabaseName, DatabaseConfig] = {
    DatabaseName.COOKIE_CHECKER: DatabaseConfig(
        path=PATH_ROBLOX_COOKIE_CHECKER_DB,
        base=CookieCheckerBase,
    ),
    DatabaseName.COOKIE_SORTER: DatabaseConfig(
        path=PATH_ROBLOX_COOKIE_SORTER_DB,
        base=CookieSorterBase,
    ),
    DatabaseName.COOKIE_REFRESHER: DatabaseConfig(
        path=PATH_ROBLOX_COOKIE_REFRESHER_DB,
        base=CookieRefresherBase,
    ),
}


class DatabaseManager:
    def __init__(self) -> None:
        self._handlers: dict[DatabaseName, DatabaseHandler] = {}

    def register(self, handler: DatabaseHandler) -> None:
        self._handlers[handler.name] = handler

    def get(self, name: DatabaseName) -> DatabaseHandler:
        return self._handlers[name]
    
    def create_all(self):
        for name, config in DATABASES.items():
            handler = DatabaseHandler(
                name=name,
                path=config.path,
                base=config.base,
            )

            handler.base.metadata.create_all()

            self._handlers[name] = handler