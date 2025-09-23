import json
from pathlib import Path
from ..utils.logger import logger
from .mixin import GetConfigMixin, SetConfigMixin, SaveConfigMixin
from .defaults import default_config_loader
from .validators import validate_config


class ConfigLoader(GetConfigMixin, SetConfigMixin, SaveConfigMixin):
    def __init__(self):
        logger.info('Intializing loader...')
        self._path = Path('Settings', 'Configs', '.Loader.json')
        self._path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self._path, 'r', encoding='utf-8', errors='ignore') as f:
                self._data = validate_config(json.load(f), default_config_loader())
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning('Loader can\'t be initialized. Using default settings...')
            self._data = default_config_loader()
            with open(self._path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        finally:
            logger.info('Loader initialized')
            
    def set(self, key, value, *, sep='.'):
        super().set(key, value, sep=sep)
        self.save()
            
config_loader = ConfigLoader()