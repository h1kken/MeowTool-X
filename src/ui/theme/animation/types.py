from __future__ import annotations

from dataclasses import dataclass
import typing as t


@dataclass(slots=True)
class AnimationSpec:
    action: str
    property_key: str
    css_property: str
    kind: str
    duration: int
    loop_count: int
    easing: t.Callable[[float], float]
    start: t.Any
    end: t.Any
    options: dict[str, t.Any] | None = None

