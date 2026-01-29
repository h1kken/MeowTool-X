from typing import Generator
from src.utils.types import T


def chunked(seq: list[T], size: int) -> Generator[list[T], None, None]:
    for i in range(0, len(seq), size):
        yield seq[i:i + size]
