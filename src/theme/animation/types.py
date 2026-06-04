from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(slots=True)
class AnimationSpec:
    action: str
    property_key: str
    css_property: str
    kind: str
    duration: int
    loop_count: int
    easing: Callable[[float], float]
    start: Any
    end: Any
    options: dict[str, Any] | None = None

