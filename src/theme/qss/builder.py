from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, cast

from PySide6.QtWidgets import QWidget

from src.theme.qss.rules import build_rules
from src.theme.qss.targets import (
    normalize_qss_target,
    parse_qss_target,
    parse_selector_chain,
    resolve_target_widgets,
)
from src.theme.schema.access import theme_map
from src.theme.schema.payload import normalize_theme_payload
from src.theme.schema.types import ThemeMap


class QssBuilder:
    def __init__(self, root: QWidget) -> None:
        self._root = root

    def build(self, payload: ThemeMap, *, theme_dir: Path) -> str:
        theme = normalize_theme_payload(payload, include_animations=False)
        widgets = cast(dict[str, ThemeMap], theme_map(theme.get("widgets")) or {})
        blocks: list[str] = []

        for target, styles in sorted(widgets.items(), key=self._sort_key):
            blocks.extend(self._build_target(target, styles, theme_dir))

        return "\n\n".join(blocks)

    def _build_target(
        self,
        target: str,
        styles: ThemeMap,
        theme_dir: Path,
    ) -> list[str]:
        if not self._needs_concrete_widgets(target, styles):
            return self._build_blocks((self._selector(target),), styles, theme_dir)

        blocks: list[str] = []
        for widget in resolve_target_widgets(self._root, target, include_window=True):
            name = widget.objectName().strip()
            if not name:
                continue
            resolved = self._resolve_percent_radius(styles, widget)
            blocks.extend(self._build_blocks((f"#{name}",), resolved, theme_dir))
        return blocks

    def _build_blocks(
        self,
        selectors: tuple[str, ...],
        styles: ThemeMap,
        theme_dir: Path,
    ) -> list[str]:
        rules = build_rules(styles, theme_dir)
        if not rules:
            return []

        body = "\n  ".join(rules)
        return [f"{selector} {{\n  {body}\n}}" for selector in selectors if selector]

    def _selector(self, target: str) -> str:
        normalized = normalize_qss_target(target)
        if normalized.startswith(("*", "MT")):
            return normalized
        return f"#{normalized}"

    def _needs_concrete_widgets(self, target: str, styles: ThemeMap) -> bool:
        parsed = parse_qss_target(target)
        base = parsed[0] if parsed else target
        return (
            parse_selector_chain(target) is not None
            or (base != "*" and any(token in base for token in ("*", "?")))
            or self._has_percent_radius(styles)
        )

    def _has_percent_radius(self, styles: ThemeMap) -> bool:
        for section in ("background", "border"):
            data = theme_map(styles.get(section))
            radius = None if data is None else data.get("radius")
            if isinstance(radius, str) and radius.strip().endswith("%"):
                return True
        return False

    def _resolve_percent_radius(
        self,
        styles: ThemeMap,
        widget: QWidget,
    ) -> ThemeMap:
        resolved = deepcopy(styles)
        base_size = self._radius_base_size(widget)
        if base_size <= 0:
            return resolved

        for section in ("background", "border"):
            data = theme_map(resolved.get(section))
            if data is None:
                continue
            radius = data.get("radius")
            if not isinstance(radius, str) or not radius.strip().endswith("%"):
                continue
            try:
                percent = float(radius.strip()[:-1])
            except ValueError:
                continue
            value = min(max(base_size * percent / 100.0, 0.0), base_size / 2.0)
            data["radius"] = f"{value:g}px"
        return resolved

    def _radius_base_size(self, widget: QWidget) -> int:
        candidates = (
            widget.size(),
            widget.sizeHint(),
            widget.minimumSizeHint(),
            widget.minimumSize(),
        )
        sizes = [
            min(size.width(), size.height())
            for size in candidates
            if size.width() > 1 and size.height() > 1
        ]
        return min(sizes) if sizes else 0

    def _sort_key(self, item: tuple[str, Any]) -> tuple[int, int]:
        target, _styles = item
        if target == "*":
            return 0, 0
        if parse_selector_chain(target) is not None:
            return 3, 0
        parsed = parse_qss_target(target)
        base, properties = parsed if parsed else (target, [])
        if base.startswith("MT"):
            return 1, len(properties)
        return 2, len(properties)
