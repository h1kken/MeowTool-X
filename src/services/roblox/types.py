# TODO: it wont to be
import typing as t


type JsonDict = dict[str, t.Any]
type JsonList = list[JsonDict]
type PlaceDataMap = dict[str, dict[str, dict[int, str]]]
type NamedIdMap = dict[int, str]
type SessionEntry = dict[str, JsonDict | str | None]


__all__ = (
    'JsonDict',
    'JsonList',
    'NamedIdMap',
    'PlaceDataMap',
    'SessionEntry',
)
