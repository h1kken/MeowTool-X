from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal
from ..config import config
from ..utils import logger, detect_system_locale


class TranslationManager(QObject):
    language_changed = pyqtSignal()

    def __init__(self, filename: str='en'):
        super().__init__()
        self.translations = {}
        self.load_language(filename)

    def load_language(self, filename: str):
        logger.info(f'[Translation] Initializing: {filename}')
        path = Path(__file__).parent / 'Settings' / 'Translates' / f'{filename}.axis'
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if not line or line.startswith('!') or line.startswith('#'):
                        continue
                    
                    if '=' in line:
                        key, label = line.split('=', 1)
                        self.translations[key.strip()] = label.strip()
            self.language_changed.emit()
            logger.info(f'[Translation] Initialized: {filename}')
        except FileNotFoundError:
            logger.exception('[Translation] File not found')
        except Exception:
            logger.exception('[Translation] Unknown error')

    def tr(self, key: str) -> str:
        return self.translations.get(key, key)


translator = TranslationManager(config.get('General>Language', default=detect_system_locale()))