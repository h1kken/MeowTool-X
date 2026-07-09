from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

import src.app.context as ctx
logger = ctx.services.logger
from src.app.paths import PATH_DEFAULT_TRANSLATION, PATH_TRANSLATIONS_SRC, PATH_TRANSLATIONS_USER
from src.config.constants import CONFIG_COMMENT_SYMBOLS


class TranslationManager(QObject):
    language_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._path = PATH_DEFAULT_TRANSLATION
        self._translations: dict[str, str] = {}

    @property
    def path(self) -> Path: return self._path

    def load(self, filename: str) -> None:        
        try:
            path = self.resolve_translation(filename)
            translations = self._parse_translations(path)
                        
            if not translations:
                logger.warning("Translation file is empty. Using keys...")
        except (OSError, UnicodeError, ValueError, TypeError) as e:
            logger.warning(f"Translations can't be loaded. Error: {e}")
            return

        self._path = path
        self._translations = translations
        self.language_changed.emit()

    def resolve_translation(self, filename: str) -> Path:
        for path in (
            PATH_TRANSLATIONS_USER / f"{filename}.axis",
            PATH_TRANSLATIONS_SRC / f"{filename}.axis",
        ):
            if path.is_file():
                return path
        return PATH_DEFAULT_TRANSLATION

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

    def _parse_translations(self, path: Path) -> dict[str, str]:
        translations: dict[str, str] = {}
        with path.open("r", encoding="utf-8", errors="ignore") as file:
            for line in file:
                line = line.strip()
                if (
                    not line
                    or line.startswith(CONFIG_COMMENT_SYMBOLS)
                    or "=" not in line
                ):
                    continue
                
                key, label = map(str.strip, line.split("=", 1))
                if not key:
                    continue
                    
                translations[key] = label
        return translations
    