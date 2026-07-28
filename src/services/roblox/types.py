import typing as t

type JsonDict = dict[str, t.Any]
type JsonList = list[JsonDict]
type PlaceDataMap = dict[str, dict[str, dict[int, str]]]
type NamedIdMap = dict[int, str]
type SessionEntry = dict[str, JsonDict | str | None]


class ReadableBinaryStream(t.Protocol):
    def read(self, size: int = -1, /) -> bytes: ...

__all__ = (
    "JsonDict",
    "JsonList",
    "NamedIdMap",
    "PlaceDataMap",
    "ReadableBinaryStream",
    "SessionEntry",
)
