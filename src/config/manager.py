import os
from pathlib import Path
from ..utils.logger import logger
from .defaults import default_config
from .utils import parse_config, validate_config
from .mixin import GetConfigMixin, SetConfigMixin, SaveConfigMixin
from .loader import config_loader
from PyQt6.QtCore import QObject, pyqtSignal


class ConfigManager(QObject, GetConfigMixin, SetConfigMixin, SaveConfigMixin):
    config_loaded = pyqtSignal()
    
    def __init__(self, filename: str = 'default'):
        super().__init__()
        self._path = Path('Settings', 'Configs', f'{filename}.txt')
        self._data = {}
        self.load(filename)
    
    def create(self, filename: str):
        if (self._path.parent / f'{filename}.txt').exists():
            return
        
        self._path = self._path.parent / f'{filename}.txt'
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self.save()
        logger.info(f'Created config: {filename}')
        self.load(filename)
    
    def load(self, filename: str):
        logger.info(f'Initializing config: {filename}')
        self._path = Path('Settings', 'Configs', f'{filename}.txt')
        self._path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self._path, 'r', encoding='utf-8', errors='ignore') as f:
                parsed_config = parse_config(f.read())
                self._data = validate_config(parsed_config, default_config())
            self.save()
        except FileNotFoundError:
            logger.warning(f'Config not found. Creating...')
            open(self._path, 'w').close()
        finally:
            logger.info(f'Config initialized: {self._path.stem}')
            self.config_loaded.emit()
        
    def set(self, key, value, *, sep='>'):
        super().set(key, value, sep=sep)
        if config_loader.get('Saver>Auto Save Changes', default=False):
            self.save()
        
    def reset(self, filename: str):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        open(self._path.parent / f'{filename}.txt', 'w').close()
        if self._path.stem == filename:
            self.load(filename)
            
    def delete(self, filename: str):
        if self._path.exists():
            os.remove(self._path.parent / f'{filename}.txt')
            if self._path.stem == filename:
                self.load('default')
                
    @property
    def name(self):
        return self._path.stem
    
    
config = ConfigManager(config_loader.get('Loader>Config On Launch', default='default'))