type JsonScalar = None | bool | int | float | str
type JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]

__all__ = ("JsonScalar", "JsonValue")
