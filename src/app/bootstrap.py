from __future__ import annotations

from typing import TYPE_CHECKING

from src.utils.filesystem.file import create_start_paths
from src.config import (
    Config,
    ConfigLoader,
    ConfigKey as CKey,
    ConfigLoaderKey as CLKey
)
from src.theme.manager import ThemeManager
from src.translation.manager import TranslationManager
from src.ui.windows.main_window import MainWindow
from src.services.discord import DiscordRPC
from src.app.paths import PATH_DEFAULT_CONFIG, PATH_DEFAULT_TRANSLATION
from src.app.types import AppServices

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication


def bootstrap(app: QApplication) -> AppServices:
    create_start_paths()
    
    config_loader = ConfigLoader()

    config = Config(config_loader)
    config.load(str(config_loader.get(CLKey.LOADER_CONFIG_ON_LOAD, default=PATH_DEFAULT_CONFIG.stem)).strip())

    translator = TranslationManager()
    translator.load(str(config.get(CKey.GENERAL_LANGUAGE, default=PATH_DEFAULT_TRANSLATION.stem)).strip())
    
    window = MainWindow(
        config=config,
        translator=translator,
    )
    window.build_pages()
    window.init_runtime_controllers()
    window.initialize_theme_manager()
    window.apply_startup_theme()
    
    theme_manager = ThemeManager(window, config)
    
    discord_rpc = DiscordRPC(window, config)

    return AppServices(
        config=config,
        translator=translator,
        window=window,
        theme_manager=theme_manager,
        discord_rpc=discord_rpc,
    )
