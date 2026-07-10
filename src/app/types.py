from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass, field


if TYPE_CHECKING:
    from src.config.manager import Config
    from src.translation.manager import TranslationManager
    from src.ui.windows.main_window import MainWindow
    from src.theme.manager import ThemeManager
    from src.theme.animation.manager import AnimationManager
    from src.services.discord import DiscordRPC
    from src.utils.logging import Logger


@dataclass(slots=True)
class AppServices:
    config: Config = field(init=False)
    translator: TranslationManager = field(init=False)
    window: MainWindow = field(init=False)
    theme_manager: ThemeManager = field(init=False)
    animation_manager: AnimationManager = field(init=False)
    discord_rpc: DiscordRPC = field(init=False)
    logger: Logger = field(init=False)
