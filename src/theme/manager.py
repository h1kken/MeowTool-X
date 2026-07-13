from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget

from src.theme.qss.builder import QssBuilder
from src.theme.storage.loader import load_theme

if TYPE_CHECKING:
    from src.config.manager import Config


class ThemeManager:
    def __init__(self, window: QWidget, config: Config) -> None:
        self._window = window
        self._config = config
        self._builder = QssBuilder(window)

    def load(self, name: str | None = None) -> Path | None:
        loaded = load_theme(self._config, name)
        if loaded is None:
            return None

        path, payload = loaded
        self._window.setStyleSheet(
            self._builder.build(payload, theme_dir=path.parent)
        )
        return path
