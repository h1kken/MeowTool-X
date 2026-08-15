from __future__ import annotations

import typing as t
import collections.abc as cabc

from PySide6.QtCore import QThreadPool

from .task import Task


class TaskRunner:
    def __init__(self) -> None:
        self._pool = QThreadPool.globalInstance()

    def run(self, function: cabc.Callable[..., t.Any], *args: t.Any, **kwargs: t.Any) -> Task:
        task = Task(function, *args, **kwargs)
        self._pool.start(task)
        return task
