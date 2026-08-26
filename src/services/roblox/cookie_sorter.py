from __future__ import annotations

import typing as t

import mmap
import shutil
import tarfile
import tempfile
import zipfile
import lzma
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import src.app.context as ctx
from src.db.commands.create import CreateModelCommand
from src.db.models.cookie_sorter.run import CookieSorterRun
db = ctx.services.database
from src.config import ConfigKey as CKey
from src.db.models.cookie_sorter import CookieSorterResult
from src.db.names import DatabaseName
from src.db.writer import DatabaseWriter
from src.db.commands import UpdateModelCommand
from src.services.base_worker import BaseWorker
from src.services.roblox.regexes import ROBLOX_COOKIE_PATTERN_BYTES
from src.utils.archive.constants import ARCHIVE_STREAM_COPY_CHUNK_BYTES
from src.utils.logging import logger
from src.utils.datetime import DateTime
from src.utils.archive import Archive
from src.utils.bytes import Bytes
from src.utils.string import String
from src.utils.filesystem.file import FS

if t.TYPE_CHECKING:
    from src.config import Config
    from src.utils.bytes import ReadableBinaryStream


class RobloxCookieSorter(BaseWorker):
    def __init__(
        self,
        *,
        config: Config,
        data: list[str | Path],
    ) -> None:
        super().__init__()
        self._config = config
        self._data = data

        # settings
        self._threads = self._config.get(CKey.ROBLOX_COOKIE_SORTER_THREADS, int)

        # prepare
        self._date_of_sorting = DateTime.current_utc_date()
        
        self._lock = threading.Lock()
        self._unique_counter = 0
        self._duplicate_counter = 0
        self._incorrect_counter = 0
        
        self._db_handler = db.get(DatabaseName.COOKIE_SORTER)
        self._db_writer = DatabaseWriter(self._db_handler, CookieSorterResult, self._on_duplicates)
        self._db_writer_thread = threading.Thread(target=self._db_writer.run, name='cookie-sorter-db-writer', daemon=False)

        self._executor = ThreadPoolExecutor(max_workers=self._threads)

        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()

    def _on_duplicates(self, i: int) -> None:
        self._duplicate_counter += i
    
    def _on_run_create(self, run: CookieSorterRun) -> None:
        self._run = run
        self.run_created.emit(run)

    def run(self) -> None:
        logger.info(f'Roblox Cookie Sorter started in {self._date_of_sorting}')
        
        self._db_writer_thread.start()
        
        # create run record
        self._db_writer.put(
            CreateModelCommand(
                model=CookieSorterRun,
                values={
                    'started_at': self._date_of_sorting,
                    'status': 'abandoned',
                    'data': [str(item) for item in self._data],
                },
                callback=self._on_run_create,
            )
        )

        try:
            for data in self._data:
                if self._stop_event.is_set():
                    break
                
                self._executor.submit(self._process_data, data)
                
            self._executor.shutdown()
            
            # update run record
            self._db_writer.put(
                UpdateModelCommand(
                    model=CookieSorterRun,
                    id=self._run.id,
                    values={
                        'finished_at': DateTime.current_utc_date(),
                        'status': 'finished' if not self._stop_event.is_set() else 'abandoned',
                        'unique_count': self._unique_counter,
                        'duplicate_count': self._duplicate_counter,
                        'incorrect_count': self._incorrect_counter,
                    },
                )
            )
        finally:
            self._db_writer.stop()
            self._db_writer_thread.join()

    # actions
    def stop(self) -> None:
        self._stop_event.set()
        self._pause_event.set()
        self._executor.shutdown(wait=False, cancel_futures=True)

    def pause(self) -> None:
        self._pause_event.clear()

    def unpause(self) -> None:
        self._pause_event.set()

    # increments
    def _add_unique(self, i: int = 1) -> None:
        if i <= 0:
            return
        with self._lock:
            self._unique_counter += i

    def _add_duplicate(self, i: int = 1) -> None:
        if i <= 0:
            return
        with self._lock:
            self._duplicate_counter += i

    def _add_incorrect(self, i: int = 1) -> None:
        if i <= 0:
            return
        with self._lock:
            self._incorrect_counter += i

    # processors
    def _process_data(self, item: str | Path) -> None:
        if isinstance(item, str):
            self._process_text(item)
        else:
            self._process_file(item)
    
    def _process_file(self, file_path: Path) -> None:
        try:
            if not self._extract_from_archive(file_path):
                self._extract_from_file(file_path)
        except (OSError, ValueError, UnicodeError):
            self._add_incorrect()

    def _process_text(self, text: str) -> None:
        try:
            self._extract_from_bytes(text.encode(errors='ignore'))
        except (OSError, ValueError, UnicodeError):
            self._add_incorrect()

    # extractors
    def _extract_from_bytes(self, data: bytes | mmap.mmap) -> None:
        for line in Bytes.iter_lines(data):
            self._pause_event.wait()
            if self._stop_event.is_set():
                return
            
            try:
                for match in ROBLOX_COOKIE_PATTERN_BYTES.finditer(line):
                    cookie = String.decode_token(match.group(0))
                    if cookie is not None:
                        cookie = cookie.rstrip(';')
                    
                    if not cookie:
                        self._add_incorrect()
                        continue
                    
                    self._db_writer.put(
                        CreateModelCommand(
                            model=CookieSorterResult,
                            values={
                                'run_ref_id': self._run.id,
                                'cookie': cookie,
                            }
                        )
                    )
            except (TypeError, ValueError):
                self._add_incorrect()

    def _extract_from_stream(self, stream: ReadableBinaryStream, name: str) -> None:
        self._pause_event.wait()
        if self._stop_event.is_set():
            return
        
        suffix = Archive.suffix_from_name(name) or '.bin'
        temp_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
                shutil.copyfileobj(stream, temp_file, length=ARCHIVE_STREAM_COPY_CHUNK_BYTES)
                temp_path = Path(temp_file.name)

            if not self._extract_from_archive(temp_path, name_hint=name):
                self._extract_from_file(temp_path)
        finally:
            if temp_path is not None:
                FS.delete_file(temp_path)

    def _extract_from_file(self, path: Path) -> None:
        self._pause_event.wait()
        if self._stop_event.is_set():
            return
        
        with open(path, 'rb') as f:
            if f.seek(0, 2) == 0:
                self._add_incorrect()
                return

            f.seek(0)
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                self._extract_from_bytes(mm)

    def _extract_from_compressed_file(self, path: Path, *, kind: str | None = None) -> tuple[set[str], int] | None:
        self._pause_event.wait()
        if self._stop_event.is_set():
            return
        
        compression_kind = kind or Archive.detect_kind(path)
        if compression_kind is None:
            return
        
        name = Archive.decompressed_name(path)
        
        match compression_kind:
            case 'gz':
                Archive.process_gz(path, name=name, callback=self._extract_from_stream)
            case 'bz2':
                Archive.process_bz2(path, name=name, callback=self._extract_from_stream)
            case 'xz':
                Archive.process_xz(path, name=name, callback=self._extract_from_stream)
            case 'zst':
                Archive.process_zst(path, name=name, callback=self._extract_from_stream)
            case 'lz4':
                Archive.process_lz4(path, name=name, callback=self._extract_from_stream)
            case _:
                return

    def _extract_from_archive(self, path: Path, *, name_hint: str | None = None) -> bool:
        self._pause_event.wait()
        if self._stop_event.is_set():
            return True
        
        kind = Archive.detect_kind(path, name_hint=name_hint)
        if kind is None:
            return False

        try:
            match kind:
                case 'zip':
                    Archive.process_zip(path, callback=self._extract_from_stream)
                case 'rar':
                    Archive.process_rar(path, callback=self._extract_from_stream)
                case 'tar':
                    Archive.process_tar(path, callback=self._extract_from_stream)
                case '7z':
                    Archive.process_7z(path, callback=self._extract_from_stream)
                case _:
                    self._extract_from_compressed_file(path, kind=kind)

            return True
        except (OSError, ValueError, EOFError, zipfile.BadZipFile, tarfile.TarError, lzma.LZMAError, RuntimeError) as e:
            logger.debug(f'Archive parse fail {path}: {e}')
            return True
