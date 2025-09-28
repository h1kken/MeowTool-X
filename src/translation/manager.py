from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal
from ..config import config
from ..utils import logger, detect_system_locale


class TranslationManager(QObject):
    language_changed = pyqtSignal()

    def __init__(self, filename: str = None):
        super().__init__()
        self._translations = {}
        self.load_language(filename)

    def find_language_path(self, filename: str) -> Path:
        for path in (
            Path(__file__).parent / '..' / '..' / 'Settings' / 'Translates' / f'{filename}.axis',
            Path(__file__).parent / 'translations' / f'{filename}.axis'
        ):
            if path.exists():
                return path
            
        logger.warning('Translation not found. Using other...')
        return path.parent / f'{detect_system_locale()}.axis'

    def load_language(self, filename: str):
        logger.info(f'Initializing translation: {filename}')
        
        self._path = self.find_language_path(filename)
        config.set('General>Language', self._path.stem)
            
        try:
            with open(self._path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if not line or line.startswith('!') or line.startswith('#'):
                        continue
                    
                    if '=' in line:
                        key, label = line.split('=', 1)
                        self._translations[key.strip()] = label.strip()
            self.language_changed.emit()
            logger.info(f'Translation initialized: {self._path.stem}')
        except FileNotFoundError:
            logger.warning('Not found any translations. Using keys...')
        except Exception:
            logger.exception('Translation can\'t be initialized. Unknown error:')

    def create_language():
        ...

    def tr(self, key: str) -> str:
        return self._translations.get(key, key)


translator = TranslationManager(config.get('General>Language', default=detect_system_locale()))