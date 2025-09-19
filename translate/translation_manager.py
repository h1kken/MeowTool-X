import json
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal
from utils.logger import logger


class TranslationManager(QObject):
    language_changed = pyqtSignal()

    def __init__(self, lang='en'):
        super().__init__()
        self.lang = lang
        self.translations = {}
        self.widgets = []
        self.load_language(lang)

    def load_language(self, lang: str):
        path = Path('translations', f'{lang}.json')
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            self.lang = lang
            self.language_changed.emit()
        else:
            logger.warning(f'Translate \'{lang}\' not found')

    def tr(self, key: str) -> str:
        return self.translations.get(key, key)


translator = TranslationManager()