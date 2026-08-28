from __future__ import annotations

import typing as t

from abc import abstractmethod
from pathlib import Path

from PySide6.QtCore import QObject, Signal

if t.TYPE_CHECKING:
    from src.config import Config


class BaseWorker(QObject):
    runCreated = Signal(object)
    progress = Signal(dict)
    finished = Signal()

    def __init__(self, *, config: Config, data: list[str | Path]) -> None:
        super().__init__()
        self._config = config
        self._data = data

    @abstractmethod
    def run(self) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...

    @abstractmethod
    def pause(self, paused: bool) -> None:
        ...
