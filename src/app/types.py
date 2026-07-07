from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.config.loader import ConfigLoader
    from src.config.manager import Config
    from src.translation.manager import TranslationManager
    from src.theme.manager import ThemeManager
    from src.ui.windows.main_window import MainWindow
    from src.services.discord import DiscordRPC


@dataclass(slots=True)
class AppServices:
    config_loader: ConfigLoader
    config: Config
    translator: TranslationManager
    theme_manager: ThemeManager
    window: MainWindow
    discord_rpc: DiscordRPC