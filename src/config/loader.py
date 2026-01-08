from src.utils.logging import logger
from src.config.mixin import GetConfigMixin, SetConfigMixin, SaveConfigMixin
from src.config.defaults import default_config_loader
from src.config.utils import parse_config, validate_config
from src.utils.consts import PATH_CONFIGS
from src.utils.filesystem import create_folder, create_file


class ConfigLoader(GetConfigMixin, SetConfigMixin, SaveConfigMixin):
    def __init__(self) -> None:
        self._path = None
        self._data = {}
        self._load()
        
    def _create_loader(self) -> None:
        if self._path.exists():
            return
        
        create_folder(PATH_CONFIGS)
        create_file(self._path)
        logger.info('Loader created')
        self._load()
        
    def _load(self) -> None:
        logger.info('Initializing loader...')
        self._path = PATH_CONFIGS / '.Loader.txt'
        
        try:
            with open(self._path, 'r', encoding='utf-8', errors='ignore') as f:
                parsed_config_loader = parse_config(f.read())
                
            self._data = validate_config(parsed_config_loader, default_config_loader())
            self.save()
            logger.info('Loader initialized')
        except FileNotFoundError:
            logger.warning('Loader not found. Creating...')
            self._create_loader()
        except Exception as e:
            logger.exception(f'Loader can\'t be initialized. Error: {e}')
            
    def set(self, key, value, *, sep='>') -> None:
        super().set(key, value, sep=sep)
        self.save()
            
            
config_loader = ConfigLoader()