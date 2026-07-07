from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from src.app.paths import (
    PATH_DEFAULT_TRANSLATION,
    PATH_TRANSLATIONS_SRC,
    PATH_TRANSLATIONS_USER,
)
from src.config.constants import CONFIG_COMMENT_SYMBOLS
from src.translation.constants import DEFAULT_LANGUAGE
from src.utils.logging import logger


def _normalize_translation_name(filename: str | None) -> str:
    normalized = Path(str(filename or '')).stem.strip().replace('-', '_')
    return normalized or DEFAULT_LANGUAGE


def resolve_translation(filename: str | None) -> Path:
    translation_name = _normalize_translation_name(filename)
    candidates = (
        PATH_TRANSLATIONS_USER / f'{translation_name}.axis',
        PATH_TRANSLATIONS_SRC / f'{translation_name}.axis',
    )

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return PATH_DEFAULT_TRANSLATION


class TranslationManager(QObject):
    language_changed = Signal()

    def __init__(self, filename: str | None = None, *, auto_load: bool = False) -> None:
        super().__init__()
        self._path: Path = PATH_DEFAULT_TRANSLATION
        self._translations: dict[str, str] = {}
        if auto_load or filename is not None:
            self.load(filename)

    @property
    def name(self) -> str:
        return self._path.stem

    def load(self, filename: str | None) -> None:
        language_path = resolve_translation(filename)
        logger.info(f'Initializing translation: requested({filename}), resolved({language_path.stem})')
        new_translations: dict[str, str] = {}

        if not language_path.is_file():
            self._path = language_path
            self._translations = {}
            logger.warning('Not found any translations. Using keys...')
            self.language_changed.emit()
            return
        
        try:
            with language_path.open('r', encoding='utf-8', errors='ignore') as file:
                for line in file:
                    line = line.strip()
                    if line and not line.startswith(CONFIG_COMMENT_SYMBOLS) and '=' in line:
                        key, label = line.split('=', 1)
                        new_translations[key.strip()] = label.strip()
                        
            if not new_translations:
                raise ValueError(f'No valid translations found in {language_path}')
        except (OSError, UnicodeError, ValueError, TypeError) as e:
            self._path = language_path
            self._translations = {}
            logger.warning(f'Translation can\'t be initialized. Error: {e}')
            self.language_changed.emit()
            return

        self._path = language_path
        self._translations = new_translations
        logger.info(f'Translation initialized: {self.name}')
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


_TRANSLATOR: TranslationManager | None = None


def set_translator(manager: TranslationManager) -> TranslationManager:
    global _TRANSLATOR
    _TRANSLATOR = manager
    return manager


def get_translator() -> TranslationManager:
    if _TRANSLATOR is None:
        raise RuntimeError('Translator is not initialized')
    return _TRANSLATOR
