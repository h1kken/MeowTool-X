from typing import TypedDict


class _PageStateRequired(TypedDict):
    main: str


class PageState(_PageStateRequired, total=False):
    inner: tuple[str, ...]


__all__ = (
    "PageState",
)
