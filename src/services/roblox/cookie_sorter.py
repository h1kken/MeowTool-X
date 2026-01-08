import re
import mmap
from pathlib import Path
from typing import Optional
from PySide6.QtCore import QObject, Signal
from src.utils.pyside6 import emit
from src.utils.datetime import current_date
from src.utils.filesystem import count_lines_in_file, create_folder, validate_filename
from src.utils.consts import ROBLOX_COOKIE_START, DATE_ROBLOX_COOKIE_SORTER_FORMAT
from src.utils.regex import ROBLOX_COOKIE_PATTERN, STRING_100_PLUS_SYMBOLS_PATTERN
from src.config.manager import config
from src.utils.logging import logger
from concurrent.futures import ThreadPoolExecutor
from threading import Lock


class RobloxCookieSorter(QObject):
    statement = Signal(str)
    progress = Signal(int)
    finished = Signal(dict)

    def __init__(self):
        super().__init__()
        self._config = config
        
        self._filename = validate_filename(self._config.get('Roblox>Cookie Sorter>Output Filename', default='output'))
        self._search_no_roblox_cookie_pattern = self._config.get('Roblox>Cookie Sorter>Search For 100 Plus Symbols Strings', default=False)
        self._symbols_between_warning_and_cookie = str(self._config.get('Roblox>General>Symbols Between Warning And Cookie', default='')).strip() if self._config.get('Roblox>General>Add Symbols Between Warning And Cookie', default=True) else ''
        
        self._base_path = Path('Roblox', 'Cookie Sorter')
        self._default_outputs_path = self._base_path / 'outputs'
        self._save_path = self._config.get('Roblox>Cookie Sorter>Save Path', default=self._default_outputs_path)
        
        self._counter_unique = 0
        self._counter_duplicate = 0
        self._counter_incorrect = 0
        
        self._cookie_set = set()
        self._cookie_set_length = 0
        
        self._max_workers = config.get('Roblox>Cookie Sorter>Threads', default=1)
        self._lock = Lock()
        
        self._date_of_sorting = current_date(DATE_ROBLOX_COOKIE_SORTER_FORMAT)
        self._is_running = True
        self._run()

    def _process_file(self, file_path: Path):
        unique_cookies_counter = 0
        unique_cookies_set = set()
        try:
            total_lines_in_file = count_lines_in_file(file_path)
            
            with open(file_path, 'rb') as f:
                if not total_lines_in_file:
                    return
                    
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    for line in iter(mm.readline, b''):
                        if not self._is_running:
                            return

                        line = line.decode('utf-8', errors='ignore')
                        cookie = self._process_line(line)
                        if cookie:
                            unique_cookies_set.add(cookie)
                            
            with self._lock:
                for cookie in unique_cookies_set:
                    if self._process_cookie(cookie):
                        unique_cookies_counter += 1
            
            logger.debug(f'{unique_cookies_counter}/{total_lines_in_file} unique cookies in {file_path}')
        except Exception as e:
            logger.exception(f'Error: {e}')

    def _process_line(self, line: str) -> Optional[str]:
        cookie = re.search(ROBLOX_COOKIE_PATTERN, line)
        if cookie:
            return cookie.group(0)
        
        if self._search_no_roblox_cookie_pattern:
            cookie = re.search(STRING_100_PLUS_SYMBOLS_PATTERN, line)
            if cookie:
                return f'{ROBLOX_COOKIE_START}{self._symbols_between_warning_and_cookie}{cookie.group(0)}'

    def _process_cookie(self, cookie: str) -> Optional[bool]:
        if not cookie:
            self._counter_incorrect += 1

        if cookie in self._cookie_set:
            self._counter_duplicate += 1
        else:
            self._counter_unique += 1
            self._cookie_set.add(cookie)
            return True

    def stop(self):
        self._is_running = False

    def _run(self):
        logger.info(f'Roblox Cookie Sorter started in {self._date_of_sorting}')
        
        file_paths = [
            path for path in list(self._base_path.rglob('*'))
            if not (path.is_dir() or self._default_outputs_path in path.parents)
        ]
        
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            executor.map(self._process_file, file_paths)

        if self._cookie_set:
            save_path = self._save_path / self._date_of_sorting
            create_folder(save_path)
            with open(save_path / f'{self._filename}.txt', 'a', encoding='utf-8') as f:
                f.write('\n'.join(self._cookie_set))

        emit(
            self.finished,
            {
                'unique': self._counter_unique,
                'duplicate': self._counter_duplicate,
                'incorrect': self._counter_incorrect
            }
        )