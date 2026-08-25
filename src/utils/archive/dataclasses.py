from dataclasses import dataclass


@dataclass(slots=True)
class ArchiveStats:
    compressed_size: int
    uncompressed_size: int
    file_count: int
    max_file_size: int

    @property
    def compression_ratio(self) -> float:
        if self.compressed_size == 0:
            return 0.0
        return self.uncompressed_size / self.compressed_size
