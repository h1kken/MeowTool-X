from typing import Generator, TypeVar

T = TypeVar('T')


def chunked(seq: list[T], size: int) -> Generator[list[T], None, None]:
    for i in range(0, len(seq), size):
        yield seq[i:i + size]
