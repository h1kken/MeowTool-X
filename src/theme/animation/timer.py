from __future__ import annotations

import typing as t

from PySide6.QtCore import QAbstractAnimation, QObject


def _clamp_progress(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class TimerAnimation(QAbstractAnimation):
    def __init__(
        self,
        duration: int,
        easing_fn: t.Callable[[float], float],
        on_start: t.Callable[[], None],
        on_update: t.Callable[[float], None],
        parent: QObject | None = None,
        *,
        restart_each_loop: bool = False,
    ):
        super().__init__(parent)
        self._duration = max(int(duration), 1)
        self._easing_fn = easing_fn
        self._on_start = on_start
        self._on_update = on_update
        self._started = False
        self._restart_each_loop = bool(restart_each_loop)
        self._active_loop = -1

    def duration(self) -> int:
        return self._duration

    def updateState(
        self,
        new_state: QAbstractAnimation.State,
        old_state: QAbstractAnimation.State,
    ) -> None:
        super().updateState(new_state, old_state)
        if new_state == QAbstractAnimation.State.Running:
            self._started = False
            self._active_loop = -1

    def updateCurrentTime(self, msec: int) -> None:
        current_loop = int(self.currentLoop())
        if (
            not self._started or
            (self._restart_each_loop and current_loop != self._active_loop)
        ):
            self._started = True
            self._active_loop = current_loop
            self._on_start()

        progress = _clamp_progress(msec / self._duration)
        self._on_update(_clamp_progress(self._easing_fn(progress)))

