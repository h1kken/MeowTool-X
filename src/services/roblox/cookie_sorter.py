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
from typing import TYPE_CHECKING, Any, Iterator, TypeAlias

from PySide6.QtCore import QObject, Signal

import src.utils.constants.archive as archive_constants
from src.config.manager import config
from src.utils.constants import DATE_ROBLOX_COOKIE_SORTER_FORMAT, ROBLOX_COOKIE_START
from src.utils.datetime import current_date
from src.utils.filesystem import FS, validate_filename
from src.utils.logging import logger
from src.utils.regexes import (
    ROBLOX_COOKIE_PATTERN_BYTES,
    STRING_100_PLUS_SYMBOLS_PATTERN_BYTES,
)

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

if TYPE_CHECKING:
    from rarfile import RarFile
    RarFileType: TypeAlias = RarFile
else:
    RarFileType: TypeAlias = Any


class RobloxCookieSorter(QObject):
    statement = Signal(str)
    progress = Signal(int)
    finished = Signal(dict)
    _DEFAULT_SORTER_WORKERS = min(8, max(2, os.cpu_count() or 2))

    def __init__(
        self,
        *,
        input_paths: list[Path] | None = None,
        text_chunks: list[str] | None = None,
        use_default_folder: bool = True,
    ):
        super().__init__()
        self._config = config

        # Settings
        self._filename = validate_filename(self._config.get('Roblox>Cookie Sorter>Output Filename', default='output'))
        self._search_no_roblox_cookie_pattern = self._config.get('Roblox>Cookie Sorter>Search For 100 Plus Symbols Strings', default=False)
        self._symbols_between_warning_and_cookie = str(
            self._config.get('Roblox>General>Symbols Between Warning And Cookie', default='')
        ).strip() if self._config.get('Roblox>General>Add Symbols Between Warning And Cookie', default=False) else ''

        self._base_path = Path('Roblox', 'Cookie Sorter')
        self._default_outputs_path = self._base_path / 'outputs'
        self._save_path = Path(self._config.get('Roblox>Cookie Sorter>Save Path', default=self._default_outputs_path))
        self._input_paths = [Path(path) for path in (input_paths or [])]
        self._text_chunks = [chunk for chunk in (text_chunks or []) if isinstance(chunk, str) and chunk.strip()]
        self._use_default_folder = bool(use_default_folder)

        self._counter_unique = 0
        self._counter_duplicate = 0
        self._counter_incorrect = 0

        self._cookie_set: set[str] = set()
        raw_workers = config.get('Roblox>Cookie Sorter>Threads', default=None)
        if raw_workers is None:
            raw_workers = config.get('Roblox>Cookie Sorter>Main Threads', default=self._DEFAULT_SORTER_WORKERS)
        if isinstance(raw_workers, tuple):
            raw_workers = raw_workers[0] if raw_workers else self._DEFAULT_SORTER_WORKERS
        try:
            self._max_workers = max(1, int(raw_workers))
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

    def _is_archive_name(self, name: str) -> bool:
        return name.lower().endswith(archive_constants.ARCHIVE_EXTENSIONS)

    def _archive_kind_from_name(self, name: str) -> str | None:
        low = name.lower()
        if low.endswith(archive_constants.ARCHIVE_TAR_EXTENSIONS):
            return 'tar'
        if low.endswith(archive_constants.ARCHIVE_ZIP_CONTAINER_EXTENSIONS):
            return 'zip'
        if low.endswith(archive_constants.ARCHIVE_7Z_EXTENSIONS):
            return '7z'
        if low.endswith(archive_constants.ARCHIVE_RAR_EXTENSIONS):
            return 'rar'
        if low.endswith(archive_constants.ARCHIVE_GZIP_EXTENSIONS):
            return 'gz'
        if low.endswith(archive_constants.ARCHIVE_BZIP2_EXTENSIONS):
            return 'bz2'
        if low.endswith(archive_constants.ARCHIVE_XZ_EXTENSIONS):
            return 'xz'
        if low.endswith(archive_constants.ARCHIVE_ZST_EXTENSIONS):
            return 'zst'
        if low.endswith(archive_constants.ARCHIVE_LZ4_EXTENSIONS):
            return 'lz4'
        return None

    def _read_file_head(self, path: Path, size: int = 8) -> bytes:
        try:
            with open(path, 'rb') as f:
                return f.read(size)
        except OSError:
            return b''

    def _looks_like_tar_file(self, path: Path) -> bool:
        try:
            with open(path, 'rb') as f:
                f.seek(archive_constants.ARCHIVE_TAR_USTAR_OFFSET)
                return f.read(len(archive_constants.ARCHIVE_TAR_USTAR_SIGNATURE)) == archive_constants.ARCHIVE_TAR_USTAR_SIGNATURE
        except OSError:
            return False

    def _detect_archive_kind(self, path: Path, *, name_hint: str | None = None) -> str | None:
        by_name = self._archive_kind_from_name(name_hint or path.name)
        if by_name is not None:
            return by_name

        head = self._read_file_head(path)
        if not head:
            return None

        if any(head.startswith(sig) for sig in archive_constants.ARCHIVE_ZIP_SIGNATURES):
            return 'zip'
        if head.startswith(archive_constants.ARCHIVE_7Z_SIGNATURE):
            return '7z'
        if head.startswith(archive_constants.ARCHIVE_RAR4_SIGNATURE) or head.startswith(archive_constants.ARCHIVE_RAR5_SIGNATURE):
            return 'rar'
        if head.startswith(archive_constants.ARCHIVE_GZIP_SIGNATURE):
            return 'gz'
        if head.startswith(archive_constants.ARCHIVE_BZIP2_SIGNATURE):
            return 'bz2'
        if head.startswith(archive_constants.ARCHIVE_XZ_SIGNATURE):
            return 'xz'
        if head.startswith(archive_constants.ARCHIVE_ZSTD_SIGNATURE):
            return 'zst'
        if any(head.startswith(sig) for sig in archive_constants.ARCHIVE_LZ4_SIGNATURES):
            return 'lz4'
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

    def _iter_files_from_directory(self, directory: Path):
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

    def _archive_suffix_for_name(self, name: str) -> str:
        low = name.lower()
        for ext in sorted(archive_constants.ARCHIVE_EXTENSIONS, key=len, reverse=True):
            if low.endswith(ext):
                return ext
        return Path(name).suffix

    def _decode_token(self, raw: bytes) -> str | None:
        if not raw:
            self._add_incorrect()
            return

        token = raw.decode(encoding='utf-8', errors='ignore').strip().rstrip(';')
        if token:
            return token
        self._add_incorrect()

    def _iter_lines(self, data: bytes | mmap.mmap) -> Iterator[bytes]:
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

    def _extract_from_stream(self, stream, *, name: str, depth: int) -> tuple[set[str], int]:
        suffix = self._archive_suffix_for_name(name) or '.bin'
        tmp_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                shutil.copyfileobj(stream, tmp, length=archive_constants.ARCHIVE_STREAM_COPY_CHUNK_BYTES)
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
        for info in archive.infolist():
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
                with archive.open(info, 'r') as stream:
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
                    return
                with open(path, 'rb') as fh:
                    dctx = zstd.ZstdDecompressor()
                    with dctx.stream_reader(fh) as stream:
                        return self._extract_from_stream(stream, name=out_name, depth=depth + 1)
            case 'lz4':
                if lz4f is None:
                    self._warn_missing_backend('lz4')
                    return
                with lz4f.open(path, mode='rb') as stream:
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
                        return
                    return self._extract_from_7z_file(path, depth=depth)
                case 'rar':
                    if rarfile is None:
                        self._warn_missing_backend('rarfile')
                        return
                    with rarfile.RarFile(path) as archive:
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

    def _process_file(self, file_path: Path):
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

    def stop(self):
        self._is_running = False

    def run(self):
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
            FS.create_folder(save_path)
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
