from __future__ import annotations

from enum import Enum

# import rarfile
import zipfile

from .protocols import RarFileProtocol


class ArchiveStatus(Enum):
    GOOD = 'good'
    BAD = 'bad'


class ArchiveAnalyzer:
    def __init__(
        self,
        *,
        max_uncompressed_size: int,
        max_compression_ratio: float,
    ) -> None:
        self._max_uncompressed_size = max_uncompressed_size
        self._max_compression_ratio = max_compression_ratio

    def analyze_zip(self, archive: zipfile.ZipFile) -> ArchiveStatus:
        compressed_size = 0
        uncompressed_size = 0
        file_count = 0
        max_file_size = 0

        for info in archive.infolist():
            if info.is_dir():
                continue

            compressed_size += info.compress_size
            uncompressed_size += info.file_size
            file_count += 1
            max_file_size = max(max_file_size, info.file_size)

            if uncompressed_size > self._max_uncompressed_size:
                return ArchiveStatus.BAD

            if compressed_size and (uncompressed_size / compressed_size) > self._max_compression_ratio:
                return ArchiveStatus.BAD

        return ArchiveStatus.GOOD

    def analyze_rar(self, archive: RarFileProtocol) -> ArchiveStatus:
        compressed_size = 0
        uncompressed_size = 0
        file_count = 0
        max_file_size = 0

        for info in archive.infolist():
            if not info.is_file():
                continue

            compressed_size += info.compress_size or 0
            uncompressed_size += info.file_size
            file_count += 1
            max_file_size = max(max_file_size, info.file_size)

            if uncompressed_size > self._max_uncompressed_size:
                return ArchiveStatus.BAD

            if compressed_size and (uncompressed_size / compressed_size) > self._max_compression_ratio:
                return ArchiveStatus.BAD

        return ArchiveStatus.GOOD

    # TODO
    def analyze_7zip(self) -> ArchiveStatus:
        ...
