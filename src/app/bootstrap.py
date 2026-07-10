from __future__ import annotations

from typing import TYPE_CHECKING

import src.app.context as ctx
from src.app.types import AppServices
from src.utils.logging import Logger
from src.utils.filesystem.file import create_start_paths
from src.config import ConfigLoader, Config
# db:
from src.translation.manager import TranslationManager
from src.ui.windows.main_window import MainWindow
from src.theme.manager import ThemeManager
from src.theme.animation.manager import AnimationManager
from src.services.discord import DiscordRPC

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication


def bootstrap(app: QApplication) -> None:
    services = ctx.services = AppServices()

    services.logger = Logger()
    
    create_start_paths()
    
    config_loader = ConfigLoader()

    services.config = Config(config_loader)
    services.config.load()

    # TODO: create db class & refactor lighter
    # services.database = Database()
    # services.database.load()

    services.translator = TranslationManager(services.config)
    services.translator.load()
    
    # TODO: refactor lighter
    services.window = MainWindow(services.config)
    services.window.build_pages()
    
    services.theme_manager = ThemeManager(services.window, services.config)
    
    # TODO: refactor lighter
    services.animation_manager = AnimationManager(services.window, services.config)
        
    # TODO: refactor lighter
    services.discord_rpc = DiscordRPC(services.window, services.config)
