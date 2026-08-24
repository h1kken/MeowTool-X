from __future__ import annotations

import typing as t
import collections.abc as cabc

import py7zr
import zstandard as zstd
import lz4.frame as lz4f
import bz2
import gzip
import lzma
import mmap
import shutil
import tarfile
import tempfile
import zipfile
import rarfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock

from src.app.paths import PATH_ROBLOX_COOKIE_SORTER_DB
from src.db.models.cookie_sorter.base import CookieSorterBase
from src.db.models.cookie_sorter.result import CookieSorterResult
from src.db.names import DatabaseName
from src.db.handler import DatabaseHandler
from src.db.writer import DatabaseWriter
from src.services.base_worker import BaseWorker
from src.utils.archive import Archive
from src.utils.archive.constants import ARCHIVE_STREAM_COPY_CHUNK_BYTES
from src.services.roblox.constants import DATE_ROBLOX_COOKIE_SORTER_FORMAT, ROBLOX_COOKIE_START
from src.services.roblox.regexes import ROBLOX_COOKIE_PATTERN_BYTES, STRING_100_PLUS_SYMBOLS_PATTERN_BYTES
from src.services.roblox.types import ReadableBinaryStream
from src.utils.archive.archive import Archive
from src.utils.datetime import current_date
from src.utils.logging import logger
from src.config import ConfigKey as CKey

if t.TYPE_CHECKING:
    from src.config import Config


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

        # Settings
        self._threads = self._config.get(CKey.ROBLOX_COOKIE_SORTER_THREADS, int)

        # Prepare
        self._date_of_sorting = current_date(DATE_ROBLOX_COOKIE_SORTER_FORMAT)
        
        self._lock = Lock()
        self._unique_counter = 0
        self._duplicate_counter = 0
        self._incorrect_counter = 0
        
        self._db_handler = DatabaseHandler(DatabaseName.COOKIE_SORTER, PATH_ROBLOX_COOKIE_SORTER_DB, CookieSorterBase)
        self._db_writer = DatabaseWriter(self._db_handler, CookieSorterResult, self._on_duplicates)

        self._is_running = True

    def _on_duplicates(self, num: int) -> None:
        ...

    def run(self) -> None:
        logger.info(f'Roblox Cookie Sorter started in {self._date_of_sorting}')

        db_writer_thread = threading.Thread(target=self._db_writer.run, name='cookie-sorter-db-writer', daemon=False)
        db_writer_thread.start()

        if self._is_running:
            with ThreadPoolExecutor(max_workers=self._threads) as executor:
                for _ in executor.map(self._process_data, self._data):
                    pass

        self._db_writer.stop()
        db_writer_thread.join()

        self.finished.emit(
            {
                'unique': self._unique_counter,
                'duplicate': self._duplicate_counter,
                'incorrect': self._incorrect_counter,
            }
        )

    def stop(self) -> None:
        self._is_running = False

    # increments
    def _add_unique(self, num: int = 1) -> None:
        if num <= 0:
            return
        with self._lock:
            self._unique_counter += num

    def _add_duplicate(self, num: int = 1) -> None:
        if num <= 0:
            return
        with self._lock:
            self._duplicate_counter += num

    def _add_incorrect(self, num: int = 1) -> None:
        if num <= 0:
            return
        with self._lock:
            self._incorrect_counter += num

    # extractors
    def _decode_token(self, raw: bytes) -> str | None:
        if not raw:
            self._add_incorrect()
            return

        token = raw.decode(encoding='utf-8', errors='ignore').strip().rstrip(';')
        if token:
            return token
        
        self._add_incorrect()

    def _iter_lines(self, data: bytes | mmap.mmap) -> cabc.Iterator[bytes]:
        start = 0
        data_len = len(data)
        while start < data_len:
            end = data.find(b'\n', start)
            if end == -1:
                line = data[start:data_len]
                start = data_len
            else:
                line = data[start:end]
                start = end + 1

            if line.endswith(b'\r'):
                line = line[:-1]
            yield line

    def _extract_cookies_from_bytes(self, data: bytes | mmap.mmap) -> tuple[set[str], int]:
        cookies: set[str] = set()
        total_found = 0

        for line in self._iter_lines(data):
            found_in_line = False

            try:
                for match in ROBLOX_COOKIE_PATTERN_BYTES.finditer(line):
                    found_in_line = True
                    cookie = self._decode_token(match.group(0))
                    if cookie:
                        cookies.add(cookie)
                        total_found += 1

            except (TypeError, ValueError):
                self._add_incorrect()
                continue

            if not found_in_line:
                self._add_incorrect()

        return cookies, total_found

    def _extract_cookies_from_regular_file(self, file_path: Path) -> tuple[set[str], int]:
        with open(file_path, 'rb') as f:
            if f.seek(0, 2) == 0:
                return set(), 0
            f.seek(0)

            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                return self._extract_cookies_from_bytes(mm)

    def _extract_from_stream(self, stream: ReadableBinaryStream, *, name: str, depth: int) -> tuple[set[str], int]:
        suffix = Archive.suffix_from_name(name) or '.bin'
        tmp_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                shutil.copyfileobj(stream, tmp, length=ARCHIVE_STREAM_COPY_CHUNK_BYTES)
                tmp_path = Path(tmp.name)

            nested = self._extract_from_archive(tmp_path, depth=depth, name_hint=name)
            if nested is not None:
                return nested

            return self._extract_cookies_from_regular_file(tmp_path)
        finally:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)

    def _extract_from_zip(self, zip_file: zipfile.ZipFile, *, depth: int) -> tuple[set[str], int]:
        cookies: set[str] = set()
        total_found = 0
        for info in zip_file.infolist():
            if not self._is_running:
                break
            if info.is_dir():
                continue
            try:
                with zip_file.open(info, 'r') as stream:
                    nested_cookies, nested_total_found = self._extract_from_stream(stream, name=info.filename, depth=depth + 1)
                    cookies.update(nested_cookies)
                    total_found += nested_total_found
            except (OSError, ValueError, EOFError, zipfile.BadZipFile, RuntimeError) as e:
                logger.debug(f'Zip entry parse fallback for {info.filename}: {e}')
                continue

        return cookies, total_found

    def _extract_from_tar(self, tar: tarfile.TarFile, *, depth: int) -> tuple[set[str], int]:
        cookies: set[str] = set()
        total_found = 0
        for member in tar.getmembers():
            if not self._is_running:
                break
            if not member.isfile():
                continue

            try:
                stream = tar.extractfile(member)
            except (OSError, ValueError, EOFError, tarfile.TarError) as e:
                logger.debug(f'Tar entry open fallback for {member.name}: {e}')
                continue
            if stream is None:
                continue

            try:
                with stream:
                    nested_cookies, nested_total_found = self._extract_from_stream(stream, name=member.name, depth=depth + 1)
                    cookies.update(nested_cookies)
                    total_found += nested_total_found
            except (OSError, ValueError, EOFError, tarfile.TarError) as e:
                logger.debug(f'Tar entry parse fallback for {member.name}: {e}')
                continue

        return cookies, total_found

    def _extract_from_rar(self, archive: rarfile.RarFile, *, depth: int) -> tuple[set[str], int]:
        cookies: set[str] = set()
        total_found = 0
        for info in t.cast(list[t.Any], archive.infolist()):
            if not self._is_running:
                break

            is_dir = False
            if hasattr(info, 'is_dir'):
                is_dir = bool(info.is_dir())
            elif hasattr(info, 'isdir'):
                attr = getattr(info, 'isdir')
                is_dir = bool(attr() if callable(attr) else attr)
            if is_dir:
                continue

            entry_name = str(getattr(info, 'filename', None) or getattr(info, 'name', '') or '')
            try:
                archive_mod = t.cast(t.Any, archive)
                with archive_mod.open(info, 'r') as stream:
                    nested_cookies, nested_total_found = self._extract_from_stream(stream, name=entry_name, depth=depth + 1)
                    cookies.update(nested_cookies)
                    total_found += nested_total_found
            except Exception as e:
                logger.debug(f'RAR entry parse fallback for {entry_name}: {e}')
                continue

        return cookies, total_found

    def _extract_from_7z(self, path: Path, *, depth: int) -> tuple[set[str], int]:
        cookies: set[str] = set()
        total_found = 0
        with tempfile.TemporaryDirectory() as temp_dir:
            with py7zr.SevenZipFile(path, mode='r') as archive:
                archive.extractall(path=temp_dir)

            root = Path(temp_dir)
            for extracted in root.rglob('*'):
                if not self._is_running:
                    break
                if not extracted.is_file():
                    continue

                try:
                    nested = self._extract_from_archive(extracted, depth=depth + 1)
                    if nested is not None:
                        nested_cookies, nested_total_found = nested
                        cookies.update(nested_cookies)
                        total_found += nested_total_found
                    else:
                        file_cookies, file_total_found = self._extract_cookies_from_regular_file(extracted)
                        cookies.update(file_cookies)
                        total_found += file_total_found
                except (OSError, ValueError, UnicodeError) as e:
                    logger.debug(f'7z nested entry fallback for {extracted}: {e}')
                    continue

        return cookies, total_found

    def _decompressed_name(self, path: Path) -> str:
        if path.name.lower().endswith(('.tzst', '.tlz4', '.tlzma')):
            return f'{path.stem}.tar'
        return path.stem

    def _extract_from_single_compressed_path(self, path: Path, *, depth: int, kind: str | None = None) -> tuple[set[str], int] | None:
        compression_kind = kind or Archive.detect_kind(path)
        if compression_kind is None:
            return None
        
        out_name = self._decompressed_name(path)
        
        match compression_kind:
            case 'gz':
                with gzip.open(path, 'rb') as stream:
                    return self._extract_from_stream(stream, name=out_name, depth=depth + 1)

            case 'bz2':
                with bz2.open(path, 'rb') as stream:
                    return self._extract_from_stream(stream, name=out_name, depth=depth + 1)

            case 'xz':
                with lzma.open(path, 'rb') as stream:
                    return self._extract_from_stream(stream, name=out_name, depth=depth + 1)

            case 'zst':
                with open(path, 'rb') as fh:
                    with zstd.ZstdDecompressor().stream_reader(fh) as stream:
                        return self._extract_from_stream(stream, name=out_name, depth=depth + 1)

            case 'lz4':
                lz4f_mod = t.cast(t.Any, lz4f)
                with lz4f_mod.open(path, mode='rb') as stream:
                    return self._extract_from_stream(stream, name=out_name, depth=depth + 1)

            case _:
                return None

    def _extract_from_archive(self, path: Path, *, depth: int, name_hint: str | None = None) -> tuple[set[str], int] | None:
        kind = Archive.detect_kind(path, name_hint=name_hint)
        if kind is None:
            return

        try:
            match kind:
                
                case 'zip':
                    with zipfile.ZipFile(path) as zf:
                        return self._extract_from_zip(zf, depth=depth)

                case 'tar':
                    with tarfile.open(path, 'r:*') as tf:
                        return self._extract_from_tar(tf, depth=depth)

                case '7z':
                    return self._extract_from_7z(path, depth=depth)

                case 'rar':
                    with rarfile.RarFile(path) as archive:
                        return self._extract_from_rar(archive, depth=depth)

                case _:
                    payload_cookies = self._extract_from_single_compressed_path(path, depth=depth, kind=kind)
                    if payload_cookies is not None:
                        return payload_cookies

        except (OSError, ValueError, EOFError, zipfile.BadZipFile, tarfile.TarError, lzma.LZMAError, RuntimeError) as e:
            logger.debug(f'Archive parse fallback for {path}: {e}')

    def _process_data(self, data: list[str | Path]) -> None:
        for item in data:
            if isinstance(item, str):
                self._process_text(item)
            else:
                self._process_file(item)
        
    def _process_file(self, file_path: Path) -> None:
        try:
            archive_cookies = self._extract_from_archive(file_path, depth=0)
            if archive_cookies is None:
                cookies, total_found = self._extract_cookies_from_regular_file(file_path)
            else:
                cookies, total_found = archive_cookies

            unique_cookies_counter = self._merge_cookies(cookies, total_found=total_found)
            logger.debug(f'{unique_cookies_counter} unique cookies in {file_path}')
        except (OSError, ValueError, UnicodeError) as e:
            self._add_incorrect()
            logger.exception(f'Error: {e}')

    def _process_text(self, text: str) -> None:
        if not self._is_running:
            return
        
        try:
            cookies, total_found = self._extract_cookies_from_bytes(text.encode('utf-8', errors='ignore'))
            self._merge_cookies(cookies, total_found=total_found)
        except (OSError, ValueError, UnicodeError):
            self._add_incorrect()

    def _merge_cookies(self, cookies: set[str], *, total_found: int) -> int:
        if not cookies and total_found <= 0:
            return 0

        with self._lock:
            new_cookies = cookies - self._cookie_set
            unique_cookies_counter = len(new_cookies)
            duplicate_counter = max(0, total_found - unique_cookies_counter)

            self._cookie_set.update(new_cookies)
            self._counter_unique += unique_cookies_counter
            self._counter_duplicate += duplicate_counter

            return unique_cookies_counter
