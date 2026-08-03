from __future__ import annotations

import typing as t

import src.app.context as ctx
from src.app.types import AppServices

if t.TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication


def bootstrap(app: QApplication) -> AppServices:
    services = ctx.services = AppServices()
    
    # Filesystem
    from src.utils.filesystem.file import create_start_paths
    create_start_paths()
    
    # Config
    from src.config import ConfigLoader, Config
    services.config = Config(ConfigLoader())
    services.config.load()

    # Database
    from src.db.manager import DatabaseManager
    services.database = DatabaseManager()

    # Translation
    from src.translation.manager import TranslationManager
    services.translator = TranslationManager(services.config)
    services.translator.load()
    
    # UI
    from src.ui.windows import MainWindow
    services.window = MainWindow(services.config) # TODO: refactor lighter (inner pages) + change generations of all object names, do it with some logic
    
    # Theme
    from src.theme.manager import ThemeManager
    services.theme_manager = ThemeManager(services.window, services.config) # TODO: refactor lighter | do strict format, no many variants of one parameter
    
    from src.theme.animation.manager import AnimationManager
    animation_manager = AnimationManager(services.window, services.config) # TODO: refactor lighter (pls)
    services.theme_manager.themeLoaded.connect(animation_manager.load)
    
    services.theme_manager.load()
    
    # Other
    from src.services.discord import DiscordRPC # TODO: fix | broken after remove PageState
    services.discord_rpc = DiscordRPC(services.window, services.config)
    app.aboutToQuit.connect(services.discord_rpc.shutdown)

    return services
