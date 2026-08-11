from __future__ import annotations

import typing as t

from src.app.types import AppServices

if t.TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication


def bootstrap(_app: QApplication) -> AppServices:
    import src.app.context as ctx
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
    
    # Theme
    from src.ui.theme.manager import ThemeManager
    services.theme = ThemeManager(services.config)
    
    # UI
    from src.ui.windows import MainWindow
    services.window = MainWindow(services.config)
    
    # Popup
    from src.ui.popup.manager import PopupManager
    services.popup = PopupManager(services.window.overlay)
    
    # from src.ui.theme.animation.manager import AnimationManager
    # animation_manager = AnimationManager(services.window, services.config) # TODO: refactor lighter (pls)
    # services.theme.themeLoaded.connect(animation_manager.load)
    
    services.theme.set_window(services.window)
    services.theme.load()
    
    # Other
    # from src.services.discord import DiscordRPC # TODO: fix | broken after remove PageState
    # services.discord_rpc = DiscordRPC(services.config)
    # app.aboutToQuit.connect(services.discord_rpc.shutdown)

    # object tree dumper
    from src.utils.debug import dump_object_tree
    dump_object_tree(services.window)

    return services
