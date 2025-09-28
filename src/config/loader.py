from pathlib import Path
from ..utils.logger import logger
from .mixin import GetConfigMixin, SetConfigMixin, SaveConfigMixin
from .defaults import default_config_loader
from .utils import parse_config, validate_config


class ConfigLoader(GetConfigMixin, SetConfigMixin, SaveConfigMixin):
    def __init__(self):
        self._path = Path('Settings', 'Configs', '.Loader.txt')
        self._data = {}
        self._load()
        
    def _load(self):
        logger.info('Intializing loader...')
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self._path, 'r', encoding='utf-8', errors='ignore') as f:
                parsed_config = parse_config(f.read())
                self._data = validate_config(parsed_config, default_config_loader())
            self.save()
            logger.info('Loader initialized')
        except FileNotFoundError:
            logger.warning('Loader not found. Creating...')
            open(self._path, 'w').close()
            self._load()
        except Exception:
            logger.exception('Loader can\'t be initialized. Unknown error:')
            
    def set(self, key, value, *, sep='>'):
        super().set(key, value, sep=sep)
        self.save()
            
            
config_loader = ConfigLoader()