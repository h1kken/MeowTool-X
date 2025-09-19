import json
from pathlib import Path
from utils.logger import logger
from utils.helpers import get_nested, set_nested
from .config_manager import ConfigManager


class ConfigLoader:
    def __init__(self):
        self._path = Path('Settings', 'Configs', '.Loader.json')
        self._data = self.load()

    def _default_settings(self):
        return {
            'Loader': {
                'Config_On_Load': 'default'
            },
            'Saver': {
                'Auto_Save': False
            },
            'MeowTool': {
                'Username': '',
                'First_Launch': True
            }
        }

    def load(self) -> dict:
        try:
            if not self._path.exists():
                raise FileNotFoundError
            
            with open(self._path, 'r', encoding='utf-8') as f:
                return json.load(f)
            
        except (FileNotFoundError, json.JSONDecodeError):
            with open(self._path, 'w', encoding='utf-8') as f:
                json.dump(self._default_settings(), f, indent=2, ensure_ascii=False)

    def _load_config(self) -> ConfigManager:
        config_name = get_nested(self._data, 'Loader.Config_On_Load', default='default')
        return ConfigManager(config_name)
                
    def get(self, key, *, sep='.', default=None):
        return get_nested(self._data, key, sep=sep, default=default)
        
    def set(self, key, value, *, sep='.'):
        set_nested(self._data, key, value, sep=sep)
    

config_loader = ConfigLoader()
config = config_loader._load_config()