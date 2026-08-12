from __future__ import annotations

import typing as t
import collections.abc as cabc

from dataclasses import dataclass


@dataclass(slots=True)
class AnimationSpec:
    action: str
    property_key: str
    css_property: str
    kind: str
    duration: int
    loop_count: int
    easing: cabc.Callable[[float], float]
    start: t.Any
    end: t.Any
    options: dict[str, t.Any] | None = None

