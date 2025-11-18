import shutil
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal
from src.config.manager import config
from src.utils.logger import logger
from src.utils.other_utils import detect_system_locale
from src.utils.paths_utils import ROOT

class TranslationManager(QObject):
    language_changed = pyqtSignal()

    def __init__(self, filename: str = None):
        super().__init__()
        self._path = None
        self._translations = {}
        self.load_language(filename)

    def find_language_path(self, filename: str) -> Path:
        for path in (
            ROOT / 'Settings' / 'Translations' / f'{filename}.axis',
            ROOT / 'src' / 'translation' / 'translations' / f'{filename}.axis'
        ):
            if path.exists():
                return path
            
        logger.warning('Translation not found. Using other...')
        lang = detect_system_locale()
        config.set('General>Language', lang)
        return path.parent / f'{lang.lower()}.axis'

    def load_language(self, filename: str):
        logger.info(f'Initializing translation: {filename}')
        
        self._path = self.find_language_path(filename)
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

    def create_my_own_language(self, to_lang: str, from_lang: str) -> None:
        new_lang = ROOT / 'Settings' / 'Translations' / f'{to_lang}.axis'
        if new_lang.exists():
            return
        
        old_lang =  ROOT / 'src' / 'translation' / 'translations' / f'{from_lang}.axis'
        if not old_lang.exists():
            return
        
        new_lang.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(str(old_lang), str(new_lang))

    def tr(self, key: str) -> str:
        return self._translations.get(key, key)


translator = TranslationManager(config.get('General>Language', default=detect_system_locale()))