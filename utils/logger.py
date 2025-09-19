import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

class Logger:
    def __init__(self, name: str, *, stream=False, level=logging.DEBUG):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        if not self.logger.handlers:
            formatter = logging.Formatter('%(asctime)s > [%(name)s] > %(levelname)s | %(message)s')

            if stream:
                console_handler = logging.StreamHandler()
                console_handler.setLevel(logging.DEBUG)
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)
            
            file_handler = RotatingFileHandler(
                filename=f'{name} ({datetime.now().strftime('%H.%M.%S %d.%m.%Y')}).log',
                maxBytes=1024*1024*5,
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(file_handler)
    
    def debug(self, message: str):
        self.logger.debug(message)
    
    def info(self, message: str):
        self.logger.info(message)
    
    def warning(self, message: str):
        self.logger.warning(message)
    
    def error(self, message: str):
        self.logger.error(message)
    
    def exception(self, message: str):
        self.logger.exception(message)


logger = Logger('MeowTool', stream=True)