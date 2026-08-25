import typing as t
import collections.abc as cabc


class RarInfoProtocol(t.Protocol):
    filename: str
    file_size: int
    compress_size: int
    def is_file(self) -> bool: ...


class RarFileProtocol(t.Protocol):
    def infolist(self) -> cabc.Sequence[RarInfoProtocol]: ...
    def open(self, name: RarInfoProtocol, mode: str = 'r', pwd: str | None = None) -> t.IO[bytes]: ...
