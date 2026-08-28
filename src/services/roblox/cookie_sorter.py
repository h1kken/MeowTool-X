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
import hashlib

import src.app.context as ctx
from src.config import ConfigKey as CKey
from src.db.commands import CreateModelCommand, InsertCommand, UpdateModelCommand
from src.db.models.cookie_sorter import CookieSorterRun, CookieSorterResult
from src.db.names import DatabaseName
from src.db.writer import DatabaseWriter
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
    PROGRESS_LOOP_INTERVAL = 0.20
    
    RUN_CREATING_TIME_LIMIT = 5
    
    def __init__(
        self,
        *,
        config: Config,
        data: list[str | Path],
    ) -> None:
        super().__init__(config=config, data=data)
        self._db = ctx.services.database

        # settings
        self._threads = self._config.get(CKey.ROBLOX_COOKIE_SORTER_THREADS, int)

        # prepare
        self._date_of_sorting = DateTime.current_datetime(utc=True)
        
        self._lock = threading.Lock()
        self._valid_counter = 0
        self._duplicate_counter = 0
        self._invalid_counter = 0
        
        self._db_handler = self._db.get(DatabaseName.COOKIE_SORTER)
        self._db_writer = DatabaseWriter(self._db_handler, CookieSorterResult, self._on_batch_written)
        self._db_writer_thread = threading.Thread(target=self._db_writer.run, name='cookie-sorter-db-writer', daemon=False)

        self._executor = ThreadPoolExecutor(max_workers=self._threads, thread_name_prefix='cookie-sorter')

        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()

        self._progress_loop_thread = threading.Thread(target=self._progress_loop, name='cookie-sorter-progress-loop', daemon=False)
        self._progress_loop_stop_event = threading.Event()

        self._run_created_event = threading.Event()

    def _on_batch_written(self, counters: dict[str, int]) -> None:
        with self._lock:
            self._add_valid(counters['inserted'])
            self._add_duplicate(counters['duplicate'])

    def _get_progress(self) -> dict[str, int]:
        with self._lock:
            return {
                'valid': self._valid_counter,
                'duplicate': self._duplicate_counter,
                'invalid': self._invalid_counter,
            }

    def _progress_loop(self) -> None:
        while not self._progress_loop_stop_event.wait(self.PROGRESS_LOOP_INTERVAL):
            self.progress.emit(self._get_progress())
        self.progress.emit(self._get_progress())
    
    def _on_run_created(self, run: CookieSorterRun) -> None:
        self._run = run
        self.runCreated.emit(run)
        self._run_created_event.set()

    def run(self) -> None:
        logger.info(f'Roblox Cookie Sorter started in {DateTime.convert_datetime(DateTime.utc_to_local_datetime(self._date_of_sorting))}')
        
        self._start_run()

        try:
            # work
            for data in self._data:
                if self._stop_event.is_set():
                    break
                
                self._executor.submit(self._process_data, data)
                
            self._executor.shutdown()
            
            # finish
            date_of_finished = DateTime.current_datetime(utc=True)            
            
            # update run record
            self._db_writer.put(
                UpdateModelCommand(
                    model=CookieSorterRun,
                    id=self._run.id,
                    values={
                        'finished_at': date_of_finished,
                        'status': 'completed' if not self._stop_event.is_set() else 'stopped',
                        'valid_count': self._valid_counter,
                        'duplicate_count': self._duplicate_counter,
                        'invalid_count': self._invalid_counter,
                    },
                )
            )
            
            self.finished.emit()
            logger.info(f'Roblox Cookie Sorter finished in {DateTime.convert_datetime(DateTime.utc_to_local_datetime(date_of_finished))}')
        finally:
            self._finish_run()
    
    # run actions
    def _start_run(self) -> None:
        self._db_writer_thread.start()
        
        # create run record
        self._db_writer.put(
            CreateModelCommand(
                model=CookieSorterRun,
                values={
                    'started_at': self._date_of_sorting,
                    'status': 'stopped', # should be 'processing' maybe... but im too lazy to process it after closing the program
                    'data': [str(item) for item in self._data],
                },
                callback=self._on_run_created,
            )
        )
        
        if not self._run_created_event.wait(timeout=self.RUN_CREATING_TIME_LIMIT):
            raise TimeoutError(f'Run creation timed out after {self.RUN_CREATING_TIME_LIMIT}s')

        self._progress_loop_thread.start()
    
    def _finish_run(self) -> None:
        self._db_writer.stop()
        self._db_writer_thread.join()
        
        self._progress_loop_stop_event.set()
        self._progress_loop_thread.join()

    # ui actions
    def stop(self) -> None:
        self._stop_event.set()
        self._pause_event.set()
        self._executor.shutdown(wait=False, cancel_futures=True)

    def pause(self, paused: bool) -> None:
        if paused:
            self._pause_event.clear()
        else:
            self._pause_event.set()

    # increments
    def _add_valid(self, i: int = 1) -> None:
        if i <= 0:
            return
        self._valid_counter += i

    def _add_duplicate(self, i: int = 1) -> None:
        if i <= 0:
            return
        self._duplicate_counter += i

    def _add_incorrect(self, i: int = 1) -> None:
        if i <= 0:
            return
        with self._lock:
            self._invalid_counter += i

    # processors
    def _process_data(self, item: str | Path) -> None:
        thread = threading.current_thread() # TODO
        
        if isinstance(item, str):
            self._process_text(item)
        else:
            self._process_file(item)
    
    def _process_file(self, path: Path) -> None:
        try:
            if not self._extract_from_archive(path):
                self._extract_from_file(path)
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
                        InsertCommand(
                            run_id=self._run.id,
                            values={
                                'run_ref_id': self._run.id,
                                'cookie': cookie,
                                'cookie_hash': hashlib.sha256(cookie.encode()).digest(),
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
