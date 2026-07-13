from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from src.theme.colors import normalize_color
from src.theme.qss.values import box, font_family, image, measure
from src.theme.schema.access import theme_map
from src.theme.schema.types import ThemeMap

type RuleBuilder = Callable[[ThemeMap, Path], list[str]]


def background_rules(styles: ThemeMap, theme_dir: Path) -> list[str]:
    background = theme_map(styles.get("background")) or {}
    media = theme_map(styles.get("media")) or {}
    rules: list[str] = []

    color = background.get("color")
    if isinstance(color, str) and color.strip():
        rules.append(f"background-color: {normalize_color(color, fallback_raw=True)};")
    value = image(background.get("image"), theme_dir)
    if value:
        rules.append(f"background-image: {value};")
    value = image(media.get("source"), theme_dir)
    if value:
        rules.append(f"background-image: {value};")
    return rules


def text_rules(styles: ThemeMap, theme_dir: Path) -> list[str]:
    text = theme_map(styles.get("text")) or {}
    font = theme_map(text.get("font")) or {}
    rules: list[str] = []

    color = text.get("color")
    if isinstance(color, str) and color.strip():
        rules.append(f"color: {normalize_color(color, fallback_raw=True)};")
    family = font_family(font.get("family"), theme_dir)
    if family:
        rules.append(f"font-family: {family};")
    size = measure(font.get("size"))
    if size:
        rules.append(f"font-size: {size};")
    for key in ("weight", "style"):
        value = str(font.get(key, "")).strip()
        if value:
            rules.append(f"font-{key}: {value};")
    return rules


def border_rules(styles: ThemeMap, _theme_dir: Path) -> list[str]:
    background = theme_map(styles.get("background")) or {}
    border = theme_map(styles.get("border"))
    rules: list[str] = []

    if border is not None:
        width = measure(border.get("width")) or ""
        style = str(border.get("style", "")).strip()
        color = _color(border.get("color"))
        if width and style and color:
            rules.append(f"border: {width} {style} {color};")
        else:
            rules.extend(_partial_border_rules("border", width, style, color))

        for side in ("top", "right", "bottom", "left"):
            rules.extend(_border_side_rules(side, border))

        radius = border.get("radius", background.get("radius"))
    else:
        radius = background.get("radius")

    radius_value = measure(radius)
    if radius_value:
        if not rules:
            rules.append("border: none;")
        rules.append(f"border-radius: {radius_value};")
    elif border is None and _has_background(styles):
        rules.append("border: none;")
    return rules


def padding_rules(styles: ThemeMap, _theme_dir: Path) -> list[str]:
    rules: list[str] = []
    value = box(styles.get("padding"))
    if value:
        rules.append(f"padding: {value};")

    for side in ("top", "right", "bottom", "left"):
        value = measure(
            styles.get(f"padding-{side}", styles.get(f"padding_{side}"))
        )
        if value:
            rules.append(f"padding-{side}: {value};")
    return rules


def passthrough_rules(styles: ThemeMap, _theme_dir: Path) -> list[str]:
    raw = styles.get("qss")
    if isinstance(raw, str):
        value = raw.strip()
        return [value if value.endswith(";") else f"{value};"] if value else []

    data = theme_map(raw)
    if data is None:
        return []
    rules: list[str] = []
    for raw_key, raw_value in data.items():
        key = str(raw_key).strip()
        value = "" if raw_value is None else str(raw_value).strip()
        if key and value:
            rules.append(f"{key}: {value};")
    return rules


RULE_BUILDERS: tuple[RuleBuilder, ...] = (
    background_rules,
    text_rules,
    border_rules,
    padding_rules,
    passthrough_rules,
)


def build_rules(styles: ThemeMap, theme_dir: Path) -> list[str]:
    return [
        rule
        for builder in RULE_BUILDERS
        for rule in builder(styles, theme_dir)
    ]


def _border_side_rules(side: str, border: ThemeMap) -> list[str]:
    raw = border.get(side)
    if isinstance(raw, str):
        value = raw.strip().rstrip(";")
        return [f"border-{side}: {value};"] if value else []

    data = theme_map(raw) or {}
    width = measure(data.get("width", border.get(f"{side}_width"))) or ""
    style = str(data.get("style", border.get(f"{side}_style", ""))).strip()
    color = _color(data.get("color", border.get(f"{side}_color")))
    if width and style and color:
        return [f"border-{side}: {width} {style} {color};"]
    return _partial_border_rules(f"border-{side}", width, style, color)


def _partial_border_rules(
    prefix: str,
    width: str,
    style: str,
    color: str,
) -> list[str]:
    values = (("width", width), ("style", style), ("color", color))
    return [f"{prefix}-{name}: {value};" for name, value in values if value]


def _color(value: Any) -> str:
    text = str(value or "").strip()
    return normalize_color(text, fallback_raw=True) if text else ""


def _has_background(styles: ThemeMap) -> bool:
    background = theme_map(styles.get("background")) or {}
    media = theme_map(styles.get("media")) or {}
    return any(background.get(key) for key in ("color", "image")) or bool(
        media.get("source")
    )
