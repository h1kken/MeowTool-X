import typing as t

import tempfile
from pathlib import Path

import zipfile
import rarfile
import tarfile
import py7zr
import zstandard as zstd
import lz4.frame as lz4f
import bz2
import gzip
import lzma

from src.utils.bytes import ReadableBinaryStream

from .protocols import RarFileProtocol
from .constants import ARCHIVE_EXTENSIONS, ARCHIVE_EXTENSION_GROUPS, ARCHIVE_SIGNATURE_GROUPS, ARCHIVE_TAR_USTAR_OFFSET, ARCHIVE_TAR_USTAR_SIGNATURE
from .types import ArchiveKind

from ..filesystem import FS
from ..logging import logger

type ArchiveStreamCallback = t.Callable[[ReadableBinaryStream, str], None]


class Archive:
    _CHUNK_SIZE = 10*1024*1024
    
    @staticmethod
    def decompressed_name(path: Path) -> str:
        if path.name.lower().endswith(('.tzst', '.tlz4', '.tlzma')):
            return f'{path.stem}.tar'
        return path.stem
    
    @staticmethod
    def suffix_from_name(name: str) -> str:
        low = name.lower()
        for extension in ARCHIVE_EXTENSIONS:
            if low.endswith(extension):
                return extension
        return Path(name).suffix

    @staticmethod
    def detect_kind(path: Path, *, name_hint: str | None = None) -> str | None:
        by_name = Archive.kind_from_name(name_hint or path.name)
        if by_name is not None:
            return by_name

        by_signature = Archive.kind_from_signature(FS.read_file_head(path))
        if by_signature is not None:
            return by_signature

        if Archive.is_tar(path):
            return 'tar'

        return None

    @staticmethod
    def kind_from_name(name: str) -> ArchiveKind | None:
        low = name.lower()
        for kind, extensions in ARCHIVE_EXTENSION_GROUPS:
            if low.endswith(extensions):
                return kind
        return None

    @staticmethod
    def kind_from_signature(head: bytes) -> ArchiveKind | None:
        if not head:
            return None
        for kind, signatures in ARCHIVE_SIGNATURE_GROUPS:
            if any(head.startswith(signature) for signature in signatures):
                return kind
        return None

    @staticmethod
    def is_tar(path: Path) -> bool:
        try:
            with open(path, 'rb') as f:
                f.seek(ARCHIVE_TAR_USTAR_OFFSET)
                return f.read(len(ARCHIVE_TAR_USTAR_SIGNATURE)) == ARCHIVE_TAR_USTAR_SIGNATURE
        except OSError:
            return False

    # processors
    @staticmethod
    def process_zip(path: Path, *, callback: ArchiveStreamCallback) -> None:
        with zipfile.ZipFile(path) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue

                try:
                    with zf.open(info, 'r') as stream:
                        callback(stream, info.filename)
                except (OSError, ValueError, EOFError, zipfile.BadZipFile, RuntimeError) as e:
                    logger.debug(f'Zip parse fail {info.filename}: {e}')

    @staticmethod
    def process_rar(path: Path, *, callback: ArchiveStreamCallback) -> None:
        with rarfile.RarFile(path) as rf:
            rf = t.cast(RarFileProtocol, rf)
            
            for info in rf.infolist():
                if not info.is_file():
                    continue

                try:
                    with rf.open(info, 'r') as stream:
                        callback(stream, info.filename)
                except Exception as e:
                    logger.debug(f'Rar parse fail {info.filename}: {e}')
    
    @staticmethod
    def process_tar(path: Path, *, callback: ArchiveStreamCallback) -> None:
        with tarfile.open(path, 'r:*') as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue

                try:
                    stream = tf.extractfile(member)
                except (OSError, ValueError, EOFError, tarfile.TarError) as e:
                    logger.debug(f'Tar open fail {member.name}: {e}')
                    continue
                
                if stream is None:
                    continue

                try:
                    with stream:
                        callback(stream, member.name)
                except (OSError, ValueError, EOFError, tarfile.TarError) as e:
                    logger.debug(f'Tar parse fail {member.name}: {e}')
    
    @staticmethod
    def process_7z(path: Path, *, callback: ArchiveStreamCallback) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            
            with py7zr.SevenZipFile(path, 'r') as archive:
                archive.extractall(path=root)

            for extracted in root.rglob('*'):
                if not extracted.is_file():
                    continue

                try:
                    with extracted.open('rb') as stream:
                        callback(stream, extracted.name)
                except (OSError, ValueError, UnicodeError) as e:
                    logger.debug(f'7z parse fail {extracted}: {e}')
    
    @staticmethod
    def process_gz(path: Path, *, name: str, callback: ArchiveStreamCallback) -> None:
        with gzip.open(path, 'rb') as stream:
            callback(stream, name)
    
    @staticmethod
    def process_bz2(path: Path, *, name: str, callback: ArchiveStreamCallback) -> None:
        with bz2.open(path, 'rb') as stream:
            callback(stream, name)
    
    @staticmethod
    def process_xz(path: Path, *, name: str, callback: ArchiveStreamCallback) -> None:
        with lzma.open(path, 'rb') as stream:
            callback(stream, name)
    
    @staticmethod
    def process_zst(path: Path, *, name: str, callback: ArchiveStreamCallback) -> None:
        with open(path, 'rb') as fh:
            with zstd.ZstdDecompressor().stream_reader(fh) as stream:
                callback(stream, name)
    
    @staticmethod
    def process_lz4(path: Path, *, name: str, callback: ArchiveStreamCallback) -> None:
        lz4f_mod = t.cast(t.Any, lz4f)
        with lz4f_mod.open(path, 'rb') as stream:
            callback(stream, name)
