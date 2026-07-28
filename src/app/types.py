from __future__ import annotations

import typing as t
from dataclasses import dataclass, field


if t.TYPE_CHECKING:
    from src.config.manager import Config
    from src.db.manager import DatabaseManager
    from src.translation.manager import TranslationManager
    from src.ui.windows.main_window import MainWindow
    from src.theme.manager import ThemeManager
    from src.services.discord import DiscordRPC


@dataclass(slots=True)
class AppServices:
    config: Config = field(init=False)
    database: DatabaseManager = field(init=False)
    translator: TranslationManager = field(init=False)
    window: MainWindow = field(init=False)
    theme_manager: ThemeManager = field(init=False)
    discord_rpc: DiscordRPC = field(init=False)
