from typing import TYPE_CHECKING

from src.config.constants import CONFIG_DEFAULT_NAME
from src.config.manager import Config
from src.config.loader import ConfigLoader
from src.config.enums import (
    ConfigKey as CKey,
    ConfigLoaderKey as CLKey,
)
from src.translation.constants import DEFAULT_LANGUAGE
from src.translation.manager import TranslationManager, set_translator
from src.ui.windows.main_window import MainWindow
from src.services.discord import DiscordRPC
from src.app.types import AppServices

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication


def bootstrap_app(app: QApplication) -> AppServices:
    _ = app
    config_loader = ConfigLoader()

    config = Config(config_loader)
    config.load(
        str(config_loader.get(CLKey.LOADER_CONFIG_ON_LOAD, default=CONFIG_DEFAULT_NAME)).strip()
        or CONFIG_DEFAULT_NAME
    )

    translator = set_translator(TranslationManager())
    translator.load(
        str(config.get(CKey.GENERAL_LANGUAGE, default=DEFAULT_LANGUAGE)).strip()
        or DEFAULT_LANGUAGE
    )

    window = MainWindow(
        config_loader=config_loader,
        config=config,
        translator=translator,
    )
    window.build_pages()
    window.init_runtime_controllers()
    window.initialize_theme_manager()
    window.apply_startup_theme()
    
    discord_rpc = DiscordRPC(window, config)

    return AppServices(
        config_loader=config_loader,
        config=config,
        translator=translator,
        theme_manager=window.theme_manager,
        window=window,
        discord_rpc=discord_rpc,
    )
