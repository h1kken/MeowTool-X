import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from .date_utils import current_date


class Logger:
    def __init__(self, name: str, *, stream=False, level=logging.DEBUG):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        self._path = Path('Logs', f'{name} ({current_date('%d.%m.%Y %H.%M.%S')}).log')
        self._path.parent.mkdir(parents=True, exist_ok=True)
        
        if not self._logger.handlers:
            formatter = logging.Formatter('%(asctime)s > [%(name)s] > %(levelname)s | %(message)s')

            if stream:
                console_handler = logging.StreamHandler()
                console_handler.setLevel(logging.DEBUG)
                console_handler.setFormatter(formatter)
                self._logger.addHandler(console_handler)
            
            file_handler = RotatingFileHandler(
                filename=self._path,
                maxBytes=1024*1024*5,
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)
            self._logger.addHandler(file_handler)
            
        self._logger.info('Eared assistant is watching... :3')
    
    def debug(self, message: str = ''):
        self._logger.debug(message)
    
    def info(self, message: str = ''):
        self._logger.info(message)
    
    def warning(self, message: str = ''):
        self._logger.warning(message)
    
    def error(self, message: str = ''):
        self._logger.error(message)
    
    def exception(self, message: str = ''):
        self._logger.exception(message)


logger = Logger('MeowTool', stream=True)