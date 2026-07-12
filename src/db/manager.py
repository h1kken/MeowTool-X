from src.app.paths import (
    PATH_ROBLOX_COOKIE_CHECKER_DB,
    PATH_ROBLOX_COOKIE_SORTER_DB,
    PATH_ROBLOX_COOKIE_REFRESHER_DB,
)
from src.db.names import DatabaseName
from src.db.config import DatabaseConfig
from src.db.handler import DatabaseHandler
from src.db.models import (
    CookieCheckerBase,
    CookieSorterBase,
    CookieRefresherBase,
)


class DatabaseManager:
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
    
    def __init__(self) -> None:
        self._handlers = {
            name: DatabaseHandler(
                name=name,
                path=config.path,
                base=config.base,
            )
            for name, config in self.DATABASES.items()
        }

    def get(self, name: DatabaseName) -> DatabaseHandler:
        return self._handlers[name]
