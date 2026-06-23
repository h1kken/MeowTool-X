from pathlib import Path

from PySide6.QtCore import QObject, Signal

from src.config.constants import CONFIG_COMMENT_SYMBOLS
from src.translation.constants import (
    DEFAULT_FALLBACK_LOCALE,
    LANGUAGE_LOCALE_DEFAULTS,
    SYSTEM_LANGUAGE,
    SYSTEM_LOCALE,
)
from src.translation.paths import PATH_TRANSLATIONS_SOURCE, PATH_TRANSLATIONS_USER
from src.utils.filesystem import FS
from src.utils.logging import logger


class TranslationManager(QObject):
    language_changed = Signal()

    def __init__(self, filename: str | None = None) -> None:
        super().__init__()
        self._path: Path | None = None
        self._translations: dict[str, str] = {}
        self.load_language(filename)

    @property
    def name(self) -> str:
        return self._path.stem if self._path is not None else ''

    @staticmethod
    def _normalize_language_name(value: str | None) -> str | None:
        if not isinstance(value, str):
            return None

        text = value.strip()
        if not text:
            return None

        text = text.split('.', 1)[0].replace('-', '_')
        if '_' in text:
            language, region = text.split('_', 1)
            if language and region:
                return f'{language.lower()}_{region.upper()}'

        if len(text) == 2 and text.isalpha():
            return text.lower()

        return text

    @staticmethod
    def _language_family(name: str | None) -> str | None:
        if not name:
            return None
        return name.split('_', 1)[0].lower()

    def _available_translation_paths(self) -> dict[str, Path]:
        available: dict[str, Path] = {}
        for root in (PATH_TRANSLATIONS_SOURCE, PATH_TRANSLATIONS_USER):
            if not root.exists():
                continue
            for path in root.glob('*.axis'):
                if not path.is_file():
                    continue
                normalized = self._normalize_language_name(path.stem)
                if normalized is None:
                    continue
                available[normalized] = path
        return available

    def _build_language_candidates(self, filename: str | None, available: dict[str, Path]) -> list[str]:
        requested = self._normalize_language_name(filename)
        system_locale = self._normalize_language_name(SYSTEM_LOCALE)
        system_language = self._normalize_language_name(SYSTEM_LANGUAGE)

        candidates: list[str] = []

        def add(value: str | None) -> None:
            if value and value not in candidates:
                candidates.append(value)

        def add_family_variants(value: str | None) -> None:
            family = self._language_family(value)
            if not family:
                return

            preferred_locale = LANGUAGE_LOCALE_DEFAULTS.get(family)
            add(preferred_locale)

            for key in sorted(available):
                if key == family:
                    continue
                if self._language_family(key) == family:
                    add(key)

            add(family)

        add(requested)
        if requested and '_' in requested:
            add(self._language_family(requested))
        else:
            add_family_variants(requested)

        add(system_locale)
        add_family_variants(system_locale)
        add(system_language)
        add_family_variants(system_language)

        add(DEFAULT_FALLBACK_LOCALE)
        add_family_variants(DEFAULT_FALLBACK_LOCALE)
        add('en')

        return candidates

    def _find_language_path(self, filename: str | None) -> Path | None:
        available = self._available_translation_paths()
        for candidate in self._build_language_candidates(filename, available):
            path = available.get(candidate)
            if path is not None:
                return path

        logger.warning(f'Translation not found. Using keys only: requested={filename}')
        return None

    def load_language(self, filename: str | None) -> None:
        language_path = self._find_language_path(filename)
        resolved_name = language_path.stem if language_path is not None else '-'
        logger.info(f'Initializing translation: requested({filename}), resolved({resolved_name})')
        new_translations: dict[str, str] = {}

        if language_path is None or not language_path.is_file():
            self._path = language_path
            self._translations = {}
            logger.warning('Not found any translations. Using keys...')
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
             
            self._path = language_path
            self._translations = new_translations
            self.language_changed.emit()
            logger.info(f'Translation initialized: {self.name}')
        except FileNotFoundError:
            self._path = language_path
            self._translations = {}
            logger.warning('Not found any translations. Using keys...')
        except (OSError, UnicodeError, ValueError, TypeError) as e:
            self._path = language_path
            self._translations = {}
            logger.warning(f'Translation can\'t be initialized. Error: {e}')

    def create_language(self, to_language: str, from_language: str) -> None:
        new_path = PATH_TRANSLATIONS_USER / f'{to_language}.axis'
        if new_path.exists():
            return
        old_path = self._find_language_path(from_language)
        if old_path is None or not old_path.exists():
            return
        FS.ensure_dir(PATH_TRANSLATIONS_USER)
        FS.copy_file(old_path, new_path)

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


translator = TranslationManager(SYSTEM_LOCALE)
