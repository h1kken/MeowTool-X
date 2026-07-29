from __future__ import annotations

import typing as t

import src.app.context as ctx
from src.app.types import AppServices

if t.TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication


def bootstrap(app: QApplication) -> AppServices:
    services = ctx.services = AppServices()
    
    from src.utils.filesystem.file import create_start_paths
    create_start_paths()
    
    from src.config import ConfigLoader, Config
    config_loader = ConfigLoader()

    services.config = Config(config_loader)
    services.config.load()

    from src.db.manager import DatabaseManager
    services.database = DatabaseManager()

    from src.translation.manager import TranslationManager
    services.translator = TranslationManager(services.config)
    services.translator.load()
    
    # TODO: change generations of all object names, do it with some logic
    # TODO: refactor lighter (inner pages)
    from src.ui.windows.main_window import MainWindow
    services.window = MainWindow(services.config)
    
    # TODO: refactor lighter | do strict format, no many variants of one parameter
    from src.theme.manager import ThemeManager
    services.theme_manager = ThemeManager(services.window, services.config)
    
    # TODO: refactor lighter (pls)
    from src.theme.animation.manager import AnimationManager
    animation_manager = AnimationManager(services.window, services.config)
    services.theme_manager.theme_loaded.connect(animation_manager.load)
    
    services.theme_manager.load()
    
    from src.services.discord import DiscordRPC
    services.discord_rpc = DiscordRPC(services.window, services.config)
    app.aboutToQuit.connect(services.discord_rpc.shutdown)

    return services
