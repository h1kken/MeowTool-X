import os
import json
from pathlib import Path
from ..utils.logger import logger
from .defaults import default_config
from .validators import validate_config
from .mixin import GetConfigMixin, SetConfigMixin, SaveConfigMixin
from .loader import config_loader
from PyQt6.QtCore import QObject, pyqtSignal


class ConfigManager(QObject, GetConfigMixin, SetConfigMixin, SaveConfigMixin):
    config_loaded = pyqtSignal()
    
    def __init__(self, filename: str = 'default'):
        super().__init__()
        self._path = Path('Settings', 'Configs', f'{filename}.json')
        self._data = {}
        self.load(filename)
    
    def create(self, filename: str):
        if (self._path.parent / f'{filename}.json').exists():
            return
        
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path.parent / f'{filename}.json', 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        logger.info(f'Created config: {filename}')
        self.load(filename)
    
    def load(self, filename: str):
        logger.info(f'Initializing config: {filename}')
        self._path = Path('Settings', 'Configs', f'{filename}.json')
        self._path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self._path, 'r', encoding='utf-8', errors='ignore') as f:
                self._data = validate_config(json.load(f), default_config())
            self.save()
        except (FileNotFoundError, json.JSONDecodeError):
            logger.exception(f'Config can\'t be initialized. Using default settings...')
            self._path = self._path.parent / 'default.json'
            self._data = {} # default_config()
            with open(self._path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        finally:
            logger.info(f'Config initialized')
            self.config_loaded.emit()
        
    def set(self, key, value, *, sep='.'):
        super().set(key, value, sep=sep)
        if config_loader.get('Saver.Auto_Save', default=False):
            self.save()
        
    def reset(self, filename: str):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path.parent / f'{filename}.json', 'w', encoding='utf-8') as f:
            json.dump({}, f, indent=2, ensure_ascii=False)
            
    def delete(self, filename: str):
        if self._path.exists():
            os.remove(self._path.parent / f'{filename}.json')
            if self._path.stem == filename:
                self.load('default')
                
    @property
    def name(self):
        return self._path.stem
    
    
config = ConfigManager(config_loader.get('Loader.Load_On_Launch', default='default'))