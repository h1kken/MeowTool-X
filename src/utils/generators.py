import typing as t

T = t.TypeVar('T')


def chunked(seq: list[T], size: int) -> t.Generator[list[T], None, None]:
    for i in range(0, len(seq), size):
        yield seq[i:i + size]
