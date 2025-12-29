from pathlib import Path
from PySide6.QtCore import QObject, Signal
from src.config.manager import config
from src.utils.pyside6 import emit
from src.utils.logger import logger
from src.utils.consts import (
    PATH_TRANSLATIONS_USER,
    PATH_TRANSLATIONS_SOURCE,
    SYSTEM_LOCALE,
    CONFIG_COMMENT_SYMBOLS
)
from src.utils.file import create_folder, copy_file


class TranslationManager(QObject):
    language_changed = Signal()

    def __init__(self, filename: str = None):
        super().__init__()
        self._path = None
        self._translations = {}
        self.load_language(filename)

    @property
    def name(self):
        return self._path.stem

    def _find_language_path(self, filename: str) -> Path:
        for path in (
            PATH_TRANSLATIONS_USER / f'{filename}.axis',
            PATH_TRANSLATIONS_SOURCE / f'{filename}.axis'
        ):
            if path.exists():
                self._path = path
                return path
            
        logger.warning(f'Translation not found. Using default: {SYSTEM_LOCALE}')
        # config.set('General>Language', SYSTEM_LOCALE)
        return PATH_TRANSLATIONS_SOURCE / f'{SYSTEM_LOCALE.lower()}.axis'

    def load_language(self, filename: str) -> None:
        logger.info(f'Initializing translation: {filename}')
        self._path = self._find_language_path(filename)
        
        try:
            with open(self._path, 'r', encoding='utf-8', errors='ignore') as file:
                for line in file:
                    if line and line[0] not in CONFIG_COMMENT_SYMBOLS and '=' in line:
                        key, label = line.split('=', 1)
                        self._translations[key.strip()] = label.strip()
            emit(self.language_changed)
            logger.info(f'Translation initialized: {self.name}')
        except FileNotFoundError:
            logger.warning('Not found any translations. Using keys...')
        except Exception as e:
            logger.exception(f'Translation can\'t be initialized. Error: {e}')

    def create_my_own_language(self, to_language: str, from_language: str) -> None:
        new_path = PATH_TRANSLATIONS_USER / f'{to_language}.axis'
        if new_path.exists():
            return

        old_path = PATH_TRANSLATIONS_SOURCE / f'{from_language}.axis'
        if not old_path.exists():
            return
        
        create_folder(PATH_TRANSLATIONS_USER)
        copy_file(old_path, new_path)

    def tr(self, key: str) -> str:
        return self._translations.get(key, key)


translator = TranslationManager(config.get('General>Language', default=SYSTEM_LOCALE))