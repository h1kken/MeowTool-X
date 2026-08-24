from __future__ import annotations

import typing as t

from dataclasses import dataclass

from src.translation import TranslationKey as TrKey

if t.TYPE_CHECKING:
    from src.ui.pages.base import BasePage
    from src.services.base_worker import BaseWorker


@dataclass(frozen=True)
class PageSpec:
    page_class: type[BasePage]
    worker_class: type[BaseWorker] | None = None
    tr: TrKey = TrKey()
    obj_name: str = ''
    icon_path: str | None = None
    has_page_controller: bool = False
