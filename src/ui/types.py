import typing as t


class _PageStateRequired(t.TypedDict):
    main: str


class PageState(_PageStateRequired, total=False):
    inner: tuple[str, ...]


__all__ = (
    "PageState",
)
