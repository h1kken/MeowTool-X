from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from src.app.paths import PATH_DEFAULT_TRANSLATION, PATH_TRANSLATIONS_USER
from src.config.constants import CONFIG_COMMENT_SYMBOLS
from src.utils.logging import logger


class TranslationManager(QObject):
    language_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._path: Path = PATH_DEFAULT_TRANSLATION
        self._translations: dict[str, str] = {}

    @property
    def path(self) -> Path: return self._path

    def load(self, filename: str) -> None:
        path = PATH_TRANSLATIONS_USER / f"{filename}.axis"
        if not path.is_file():
            return
        
        translations: dict[str, str] = {}
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as file:
                for line in file:
                    line = line.strip()
                    if line and not line.startswith(CONFIG_COMMENT_SYMBOLS) and "=" in line:
                        key, label = line.split("=", 1)
                        translations[key.strip()] = label.strip()
                        
            if not translations:
                logger.warning(f"translations not found, using keys...")
        except (OSError, UnicodeError, ValueError, TypeError) as e:
            logger.warning(f"translations can't be loaded, error: {e}")
            return

        self._path = path
        self._translations = translations
        self.language_changed.emit()

    def tr(
        self,
        key: str,
        disambiguation: str | None = None,
        n: int = -1,
        **kwargs: object,
    ) -> str:
        _ = (disambiguation, n)
        text = self._translations.get(key, key)
        if not kwargs:
            return text
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
