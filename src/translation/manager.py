from __future__ import annotations

import typing as t

from pathlib import Path
from types import MappingProxyType

from PySide6.QtCore import QObject, Signal

from src.utils.logging import logger
from src.app.paths import PATH_DEFAULT_TRANSLATION, PATH_TRANSLATIONS_SRC, PATH_TRANSLATIONS_USER
from src.config.constants import CONFIG_COMMENT_SYMBOLS
from src.config import ConfigKey as CKey

if t.TYPE_CHECKING:
    from src.config import Config
    
    
class TranslationManager(QObject):
    languageChanged = Signal()

    def __init__(self, config: Config) -> None:
        super().__init__()
        self._config = config
        
        self._path = PATH_DEFAULT_TRANSLATION
        self._translations: dict[str, str] = {}

        self._config.configLoaded.connect(self.load)

    @property
    def name(self) -> str:
        return self._path.name
    
    @property
    def path(self) -> Path:
        return self._path
    
    @property
    def translations(self) -> MappingProxyType[str, str]:
        return MappingProxyType(self._translations)
    
    def load(self, name: str | None = None) -> None:        
        if name is None:
            name = str(self._config.get(CKey.GENERAL_LANGUAGE)).strip()
        
        try:
            path = self._resolve_translation(name)
            translations = self._parse_translations(path)
                
            if not translations:
                logger.warning('Translation file is empty. Using keys...')
        except (OSError, UnicodeError, ValueError, TypeError) as e:
            logger.warning(f'Translations can\'t be loaded. Error: {e}')
            return

        self._path = path
        self._translations = translations
        self.languageChanged.emit()

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

    def _resolve_translation(self, name: str) -> Path:
        for path in (
            PATH_TRANSLATIONS_USER / f'{name}.axis',
            PATH_TRANSLATIONS_SRC / f'{name}.axis',
        ):
            if path.is_file():
                return path
        return PATH_DEFAULT_TRANSLATION

    def _parse_translations(self, path: Path) -> dict[str, str]:
        translations: dict[str, str] = {}
        with path.open('r', encoding='utf-8', errors='ignore') as file:
            for line in file:
                line = line.strip()
                if (
                    not line
                    or line.startswith(CONFIG_COMMENT_SYMBOLS)
                    or '=' not in line
                ):
                    continue
                
                key, label = map(str.strip, line.split('=', 1))
                if not key:
                    continue
                    
                translations[key] = label
        return translations
    
