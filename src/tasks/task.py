from __future__ import annotations

import typing as t
import collections.abc as cabc

from uuid import UUID

from PySide6.QtCore import QObject, QRunnable, Signal


class TaskSignals(QObject):
    finished = Signal(object)
    result = Signal(object)
    error = Signal(object)


class Task(QRunnable):
    def __init__(self, task_id: UUID, function: cabc.Callable[..., t.Any], *args: t.Any, **kwargs: t.Any) -> None:
        super().__init__()
        
        self.task_id = task_id
        self.result: t.Any = None
        self.error: Exception | None = None
        
        self._function = function
        self._args = args
        self._kwargs = kwargs

        self.signals = TaskSignals()

    def run(self) -> None:
        try:
            self.result = self._function(*self._args, **self._kwargs)

        except Exception as e:
            self.error = e
            self.signals.error.emit(self)

        else:
            self.signals.result.emit(self)

        finally:
            self.signals.finished.emit(self)
