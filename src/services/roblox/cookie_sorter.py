from __future__ import annotations

import typing as t
import collections.abc as cabc

import bz2
import gzip
import lzma
import mmap
import os
import shutil
import tarfile
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock

from PySide6.QtCore import QObject, Signal

from src.services.roblox import archive_support
from src.services.roblox.constants import DATE_ROBLOX_COOKIE_SORTER_FORMAT, ROBLOX_COOKIE_START
from src.services.roblox.regexes import ROBLOX_COOKIE_PATTERN_BYTES, STRING_100_PLUS_SYMBOLS_PATTERN_BYTES
from src.services.roblox.types import ReadableBinaryStream
from src.utils.datetime import current_date
from src.utils.filesystem import FS, validate_filename
from src.utils.logging import logger

if t.TYPE_CHECKING:
    from src.config import Config

try:
    import py7zr
except ImportError:
    py7zr = None

try:
    import rarfile
except ImportError:
    rarfile = None

try:
    import zstandard as zstd
except ImportError:
    zstd = None

try:
    import lz4.frame as lz4f
except ImportError:
    lz4f = None

if t.TYPE_CHECKING:
    from rarfile import RarFile
    RarFileType: t.TypeAlias = RarFile
else:
    RarFileType: t.TypeAlias = t.Any
class RobloxCookieSorter(QObject):
    statement = Signal(str)
    progress = Signal(int)
    finished = Signal(dict)
    _DEFAULT_SORTER_WORKERS = min(8, max(2, os.cpu_count() or 2))

    def __init__(
        self,
        config: Config,
        *,
        input_paths: list[Path] | None = None,
        text_chunks: list[str] | None = None,
        use_default_folder: bool = True,
    ) -> None:
        super().__init__()
        self._config = config

        # Settings
        output_filename = str(self._config.get('Roblox>Cookie Sorter>Output Filename')).strip()
        self._filename = validate_filename(output_filename if output_filename else 'output')
        
        self._search_no_roblox_cookie_pattern = bool(self._config.get('Roblox>Cookie Sorter>Search For 100 Plus Symbols Strings'))
        self._symbols_between_warning_and_cookie = str(self._config.get('Roblox>General>Symbols Between Warning And Cookie')).strip() if self._config.get('Roblox>General>Add Symbols Between Warning And Cookie') else ''

        self._base_path = Path('Roblox', 'Cookie Sorter')
        self._default_outputs_path = self._base_path / 'outputs'
        raw_save_path = self._config.get('Roblox>Cookie Sorter>Save Path')
        self._save_path = Path(raw_save_path) if isinstance(raw_save_path, (str, Path)) else self._default_outputs_path
        self._input_paths = [Path(path) for path in (input_paths or [])]
        self._text_chunks = [chunk for chunk in (text_chunks or []) if chunk.strip()]
        self._use_default_folder = use_default_folder

        self._counter_unique = 0
        self._counter_duplicate = 0
        self._counter_incorrect = 0

        self._cookie_set: set[str] = set()
        raw_workers = t.cast(object, self._config.get('Roblox>Cookie Sorter>Threads'))
        if raw_workers is None:
            raw_workers = t.cast(object, self._config.get('Roblox>Cookie Sorter>Main Threads'))
        if isinstance(raw_workers, tuple):
            tuple_workers = t.cast(tuple[object, ...], raw_workers)
            raw_workers = tuple_workers[0] if tuple_workers else self._DEFAULT_SORTER_WORKERS
        try:
            self._max_workers = max(1, int(raw_workers if isinstance(raw_workers, (int, float, str)) else self._DEFAULT_SORTER_WORKERS))
        except (TypeError, ValueError):
            self._max_workers = self._DEFAULT_SORTER_WORKERS
        self._lock = Lock()
        self._missing_backend_warnings: set[str] = set()

        self._date_of_sorting = current_date(DATE_ROBLOX_COOKIE_SORTER_FORMAT)
        self._is_running = True

    def _add_incorrect(self, count: int = 1) -> None:
        if count <= 0:
            return
        with self._lock:
            self._counter_incorrect += count

    def _path_key(self, path: Path) -> str:
        try:
            return str(path.resolve()).lower()
        except OSError:
            return str(path.absolute()).lower()

    def _read_file_head(self, path: Path, size: int = 8) -> bytes:
        try:
            with open(path, 'rb') as f:
                return f.read(size)
        except OSError:
            return b''

    def _looks_like_tar_file(self, path: Path) -> bool:
        try:
            with open(path, 'rb') as f:
                f.seek(archive_support.ARCHIVE_TAR_USTAR_OFFSET)
                return f.read(len(archive_support.ARCHIVE_TAR_USTAR_SIGNATURE)) == archive_support.ARCHIVE_TAR_USTAR_SIGNATURE
        except OSError:
            return False

    def _detect_archive_kind(self, path: Path, *, name_hint: str | None = None) -> str | None:
        by_name = archive_support.archive_kind_from_name(name_hint or path.name)
        if by_name is not None:
            return by_name

        by_signature = archive_support.archive_kind_from_signature(self._read_file_head(path))
        if by_signature is not None:
            return by_signature

        if self._looks_like_tar_file(path):
            return 'tar'
        return None

    def _warn_missing_backend(self, backend: str) -> None:
        if backend in self._missing_backend_warnings:
            return
        self._missing_backend_warnings.add(backend)
        logger.warning(f'Missing optional backend for archive format: {backend}')

    def _is_supported_input_file(self, path: Path) -> bool:
        if not path.is_file():
            return False
        if self._default_outputs_path in path.parents:
            return False
        return True

    def _iter_files_from_directory(self, directory: Path) -> cabc.Iterator[Path]:
        for path in directory.rglob('*'):
            if self._is_supported_input_file(path):
                yield path

    def _collect_input_files(self) -> list[Path]:
        files: list[Path] = []

        if self._use_default_folder and self._base_path.exists():
            files.extend(self._iter_files_from_directory(self._base_path))

        for path in self._input_paths:
            if not path.exists():
                continue
            if path.is_file() and self._is_supported_input_file(path):
                files.append(path)
                continue
            if path.is_dir():
                files.extend(self._iter_files_from_directory(path))

        deduped: list[Path] = []
        seen: set[str] = set()
        for path in files:
            key = self._path_key(path)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(path)
        return deduped

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

                if self._search_no_roblox_cookie_pattern and not found_in_line:
                    for match in STRING_100_PLUS_SYMBOLS_PATTERN_BYTES.finditer(line):
                        found_in_line = True
                        cookie = self._decode_token(match.group(0))
                        if cookie:
                            cookies.add(f'{ROBLOX_COOKIE_START}{self._symbols_between_warning_and_cookie}{cookie}')
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
        suffix = archive_support.archive_suffix_for_name(name) or '.bin'
        tmp_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                shutil.copyfileobj(t.cast(t.Any, stream), tmp, length=archive_support.ARCHIVE_STREAM_COPY_CHUNK_BYTES)
                tmp_path = Path(tmp.name)

            nested = self._extract_archive_file(tmp_path, depth=depth, name_hint=name)
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

    def _extract_from_rar(self, archive: RarFileType, *, depth: int) -> tuple[set[str], int]:
        cookies: set[str] = set()
        total_found = 0
        archive_any = t.cast(t.Any, archive)
        for info in t.cast(list[t.Any], archive_any.infolist()):
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
                with archive_any.open(info, 'r') as stream:
                    nested_cookies, nested_total_found = self._extract_from_stream(stream, name=entry_name, depth=depth + 1)
                    cookies.update(nested_cookies)
                    total_found += nested_total_found
            except Exception as e:
                logger.debug(f'RAR entry parse fallback for {entry_name}: {e}')
                continue

        return cookies, total_found

    def _extract_from_7z_file(self, path: Path, *, depth: int) -> tuple[set[str], int]:
        cookies: set[str] = set()
        total_found = 0
        archive_mod = t.cast(t.Any, py7zr)
        with tempfile.TemporaryDirectory() as temp_dir:
            with archive_mod.SevenZipFile(path, mode='r') as archive:
                archive.extractall(path=temp_dir)

            root = Path(temp_dir)
            for extracted in root.rglob('*'):
                if not self._is_running:
                    break
                if not extracted.is_file():
                    continue

                try:
                    nested = self._extract_archive_file(extracted, depth=depth + 1, name_hint=extracted.name)
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
        compression_kind = kind or self._detect_archive_kind(path)
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
                if zstd is None:
                    self._warn_missing_backend('zstandard')
                    return None
                zstd_mod = t.cast(t.Any, zstd)
                with open(path, 'rb') as fh:
                    dctx = zstd_mod.ZstdDecompressor()
                    with dctx.stream_reader(fh) as stream:
                        return self._extract_from_stream(stream, name=out_name, depth=depth + 1)
            case 'lz4':
                if lz4f is None:
                    self._warn_missing_backend('lz4')
                    return None
                lz4f_mod = t.cast(t.Any, lz4f)
                with lz4f_mod.open(path, mode='rb') as stream:
                    return self._extract_from_stream(stream, name=out_name, depth=depth + 1)
            case _:
                return None

    def _extract_archive_file(self, path: Path, *, depth: int, name_hint: str | None = None) -> tuple[set[str], int] | None:
        kind = self._detect_archive_kind(path, name_hint=name_hint)
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
                    if py7zr is None:
                        self._warn_missing_backend('py7zr')
                        return None
                    return self._extract_from_7z_file(path, depth=depth)
                case 'rar':
                    if rarfile is None:
                        self._warn_missing_backend('rarfile')
                        return None
                    rarfile_mod = t.cast(t.Any, rarfile)
                    with rarfile_mod.RarFile(path) as archive:
                        return self._extract_from_rar(archive, depth=depth)
                case _:
                    payload_cookies = self._extract_from_single_compressed_path(path, depth=depth, kind=kind)
                    if payload_cookies is not None:
                        return payload_cookies

        except (OSError, ValueError, EOFError, zipfile.BadZipFile, tarfile.TarError, lzma.LZMAError, RuntimeError) as e:
            logger.debug(f'Archive parse fallback for {path}: {e}')

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

    def _process_file(self, file_path: Path) -> None:
        try:
            archive_cookies = self._extract_archive_file(file_path, depth=0)
            if archive_cookies is None:
                cookies, total_found = self._extract_cookies_from_regular_file(file_path)
            else:
                cookies, total_found = archive_cookies

            unique_cookies_counter = self._merge_cookies(cookies, total_found=total_found)
            logger.debug(f'{unique_cookies_counter} unique cookies in {file_path}')
        except (OSError, ValueError, UnicodeError) as e:
            self._add_incorrect()
            logger.exception(f'Error: {e}')

    def _process_text_chunks(self) -> None:
        for chunk in self._text_chunks:
            if not self._is_running:
                return
            try:
                cookies, total_found = self._extract_cookies_from_bytes(chunk.encode('utf-8', errors='ignore'))
                self._merge_cookies(cookies, total_found=total_found)
            except (OSError, ValueError, UnicodeError):
                self._add_incorrect()

    def stop(self) -> None:
        self._is_running = False

    def run(self) -> None:
        logger.info(f'Roblox Cookie Sorter started in {self._date_of_sorting}')

        file_paths = self._collect_input_files()
        logger.info(f'Roblox Cookie Sorter workload: files={len(file_paths)}, text_blocks={len(self._text_chunks)}, workers={self._max_workers}')

        self._process_text_chunks()

        if self._is_running and file_paths:
            with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                for _ in executor.map(self._process_file, file_paths):
                    pass

        if self._cookie_set:
            save_path = self._save_path / self._date_of_sorting
            FS.ensure_dir(save_path)
            with open(save_path / f'{self._filename}.txt', 'a', encoding='utf-8') as f:
                f.write('\n'.join(self._cookie_set))

        self.finished.emit(
            {
                'unique': self._counter_unique,
                'duplicate': self._counter_duplicate,
                'incorrect': self._counter_incorrect,
                'sources': {
                    'files': len(file_paths),
                    'text_blocks': len(self._text_chunks),
                    'use_default_folder': self._use_default_folder,
                },
            }
        )
