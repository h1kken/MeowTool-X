import json
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal
from utils.logger import logger


class TranslationManager(QObject):
    language_changed = pyqtSignal()

    def __init__(self, lang: str='en'):
        super().__init__()
        self.lang = lang
        self.translations = {}
        self.load_language(lang)

    def load_language(self, lang: str):
        logger.info(f'Initializing translation: {lang}')
        path = Path('Settings', 'Translates', f'{lang}.json')
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                self.translations = json.load(f)
            self.lang = lang
            self.language_changed.emit()
        except (FileNotFoundError, json.JSONDecodeError):
            logger.exception(f'Translation can\'t be initialized. Using default translate...')

    def tr(self, key: str) -> str:
        return self.translations.get(key, key)


translator = TranslationManager()