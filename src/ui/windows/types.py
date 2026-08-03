from __future__ import annotations

import typing as t

from dataclasses import dataclass

if t.TYPE_CHECKING:
    from src.ui.pages.base import BasePage


@dataclass(frozen=True)
class PageSpec:
    page_class: type[BasePage]
    tr_key: str
    obj_name: str
    icon: str | None = None
    has_page_controller: bool = False


__all__ = (
    'PageSpec',
)
