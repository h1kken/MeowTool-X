from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from src.config.manager import Config
    from src.translation.manager import TranslationManager
    from src.theme.manager import ThemeManager
    from src.ui.windows.main_window import MainWindow
    from src.services.discord import DiscordRPC


@dataclass(slots=True)
class AppServices:
    config: Config
    translator: TranslationManager
    window: MainWindow
    theme_manager: ThemeManager
    discord_rpc: DiscordRPC
