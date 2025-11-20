import os
from src.config.defaults import default_config
from src.config.utils import parse_config, validate_config
from src.config.mixin import GetConfigMixin, SetConfigMixin, SaveConfigMixin
from PyQt6.QtCore import QObject, pyqtSignal
from src.config.loader import config_loader
from src.utils.logger import logger
from src.utils.consts import PATH_CONFIGS
from src.utils.file_utils import create_folder, delete_file


class Config(QObject, GetConfigMixin, SetConfigMixin, SaveConfigMixin):
    config_loaded = pyqtSignal()
    
    def __init__(self, filename: str = 'default'):
        super().__init__()
        self._path = None
        self._data = {}
        self.load(filename)
        
    @property
    def name(self):
        return self._path.stem
    
    def create(self, filename: str):
        path = PATH_CONFIGS / f'{filename}.txt'
        if path.exists(): return
        
        create_folder(PATH_CONFIGS)
        path.touch()
        logger.info(f'Created config: {filename}')
        self.load(filename)
    
    def load(self, filename: str):
        logger.info(f'Initializing config: {filename}')
        self._path = PATH_CONFIGS / f'{filename}.txt'
        
        try:
            with open(self._path, 'r', encoding='utf-8', errors='ignore') as f:
                parsed_config = parse_config(f.read())
                
            self._data = validate_config(parsed_config, default_config())
            self.save()
            logger.info(f'Config initialized: {filename}')
            self.config_loaded.emit()
        except FileNotFoundError:
            logger.warning(f'Config not found. Creating...')
            self.create(filename)
        except Exception:
            logger.exception('Config can\'t be initialized. Unknown error:')
        
    def set(self, key, value, *, sep='>', force_save: bool = False):
        super().set(key, value, sep=sep)
        if config_loader.get('Saver>Auto Save Changes', default=False) or force_save:
            self.save()
        
    def reset(self, filename: str):
        path = PATH_CONFIGS / f'{filename}.txt'
        if not path.exists(): return
        
        create_folder(PATH_CONFIGS)
        open(path, 'w').close()
        if self._path.stem == filename:
            self.load(filename)
            
    def delete(self, filename: str):
        path = PATH_CONFIGS / f'{filename}.txt'
        if path.exists():
            delete_file(path)
            if path.stem == filename:
                self.load('default')
    
    
config = Config(config_loader.get('Loader>Config On Launch', default='default'))