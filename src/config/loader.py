from pathlib import Path
from src.utils.logger import logger
from src.config.mixin import GetConfigMixin, SetConfigMixin, SaveConfigMixin
from src.config.defaults import default_config_loader
from src.config.utils import parse_config, validate_config
from src.utils.consts import PATH_CONFIGS
from src.utils.file_utils import create_folder


class ConfigLoader(GetConfigMixin, SetConfigMixin, SaveConfigMixin):
    def __init__(self) -> None:
        self._data = {}
        self._load()
        
    def _create(self) -> None:
        if self._path.exists(): return
        
        create_folder(PATH_CONFIGS)
        self._path.touch()
        logger.info('Loader created')
        self._load()
        
    def _load(self) -> None:
        logger.info('Intializing loader...')
        self._path = PATH_CONFIGS / '.Loader.txt'
        
        try:
            with open(self._path, 'r', encoding='utf-8', errors='ignore') as f:
                parsed_config_loader = parse_config(f.read())
                
            self._data = validate_config(parsed_config_loader, default_config_loader())
            self.save()
            logger.info('Loader initialized')
        except FileNotFoundError:
            logger.warning('Loader not found. Creating...')
            self._create()
        except Exception:
            logger.exception('Loader can\'t be initialized. Unknown error:')
            
    def set(self, key, value, *, sep='>') -> None:
        super().set(key, value, sep=sep)
        self.save()
            
            
config_loader = ConfigLoader()