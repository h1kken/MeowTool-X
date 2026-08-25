import typing as t


type JsonObject = dict[str, object]

type DataScalar = None | bool | int | float | str
type DataValue = (
    DataScalar
    | list['DataValue']
    | tuple['DataValue', ...]
    | dict[str, 'DataValue']
)
DataMap: t.TypeAlias = dict[str, DataValue]
