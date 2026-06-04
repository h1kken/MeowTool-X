from typing import Callable


class StartupProgressTracker:
    def __init__(
        self,
        callback: Callable[..., None] | None,
        stages: list[tuple[str, float]],
    ) -> None:
        self._callback = callback
        self._weights: dict[str, float] = {}
        self._offsets: dict[str, float] = {}
        self._last_value = 0.0

        total = 0.0
        for key, weight in stages:
            normalized = max(0.0, float(weight))
            self._offsets[key] = total
            self._weights[key] = normalized
            total += normalized

        self.total = max(1.0, total)

    def update(
        self,
        key: str,
        progress: float,
        stage: str,
        counter_text: str | None = None,
    ) -> None:
        if not callable(self._callback):
            return

        weight = self._weights.get(key, 0.0)
        offset = self._offsets.get(key, 0.0)
        clamped = max(0.0, min(1.0, float(progress)))
        current = offset + (weight * clamped)
        current = max(self._last_value, min(self.total, current))
        self._last_value = current
        self._callback(current, self.total, stage, counter_text)

    def complete(self, key: str, stage: str, counter_text: str | None = None) -> None:
        self.update(key, 1.0, stage, counter_text)
