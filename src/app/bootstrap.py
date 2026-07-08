from __future__ import annotations

from typing import TYPE_CHECKING

import src.app.context as ctx
from src.app.types import AppServices
from src.utils.filesystem.file import create_start_paths
from src.config import (
    Config,
    ConfigLoader,
    ConfigKey as CKey,
    ConfigLoaderKey as CLKey
)
from src.translation.manager import TranslationManager
from src.ui.windows.main_window import MainWindow
from src.theme.manager import ThemeManager
from src.services.discord import DiscordRPC
from src.utils.logging import Logger
from src.app.paths import PATH_DEFAULT_CONFIG, PATH_DEFAULT_TRANSLATION

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication


def bootstrap(app: QApplication) -> None:
    services = ctx.services = AppServices()
    
    create_start_paths()
    
    services.logger = Logger()
    
    config_loader = ConfigLoader()

    services.config = Config(loader=config_loader)
    services.config.load(str(config_loader.get(CLKey.LOADER_CONFIG_ON_LOAD, default=PATH_DEFAULT_CONFIG.stem)).strip())

    # TODO: refactor lighter
    services.translator = TranslationManager()
    services.translator.load(str(services.config.get(CKey.GENERAL_LANGUAGE, default=PATH_DEFAULT_TRANSLATION.stem)).strip())
    
    # TODO: refactor lighter
    services.window = MainWindow(
        config=services.config,
    )
    services.window.build_pages()
    services.window.init_runtime_controllers()
    services.window.initialize_theme_manager()
    services.window.apply_startup_theme()
    
    # TODO: refactor lighter
    services.theme_manager = ThemeManager(
        root=services.window,
        config=services.config,
    )
    
    # TODO: refactor lighter
    services.discord_rpc = DiscordRPC(
        window=services.window,
        config=services.config,
    )
