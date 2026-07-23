from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from PySide6.QtGui import QFontDatabase

from src.theme.colors import normalize_color
from src.theme.parser import ThemeMap
from src.utils.conversion import as_dict

_IMAGE_EXTENSIONS = {
    ".bmp",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".png",
    ".svg",
    ".webp",
}
_FONT_EXTENSIONS = {
    ".otf",
    ".ttc",
    ".ttf",
    ".woff",
    ".woff2",
}


def _measure(value: Any) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return f"{value:g}px"
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None
    try:
        return f"{float(text):g}px"
    except ValueError:
        return text


def _box(value: Any) -> str | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _measure(value)
    if isinstance(value, str):
        parts: list[Any] = value.replace(",", " ").split()
    elif isinstance(value, (list, tuple)):
        parts = list(cast(list[Any] | tuple[Any, ...], value))
    elif isinstance(value, dict):
        data = cast(dict[str, Any], value)
        parts = [data.get(side) for side in ("top", "right", "bottom", "left")]
    else:
        return None

    if not 1 <= len(parts) <= 4:
        return None
    values = [_measure(part) for part in parts]
    return " ".join(cast(list[str], values)) if all(values) else None


def _image(value: Any, theme_dir: Path) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.startswith("url("):
        return text

    path = _resolve_file(text, theme_dir)
    source = str(path or text).replace("\\", "/")
    suffix = Path(text.split("?", 1)[0].split("#", 1)[0]).suffix.lower()
    return f'url("{source}")' if suffix in _IMAGE_EXTENSIONS else text


def _font_family(value: Any, theme_dir: Path) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    source = text.removeprefix("url(").removesuffix(")").strip(" \"'")
    if Path(source).suffix.lower() not in _FONT_EXTENSIONS:
        return text

    path = _resolve_file(source, theme_dir)
    if path is None:
        return None
    font_id = QFontDatabase.addApplicationFont(str(path))
    families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
    if not families:
        return None
    escaped = families[0].replace('"', '\\"')
    return f'"{escaped}"'


def _resolve_file(value: str, theme_dir: Path) -> Path | None:
    path = Path(value).expanduser()
    candidates = (path,) if path.is_absolute() else (theme_dir / path, path)
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def background_rules(styles: ThemeMap, theme_dir: Path) -> list[str]:
    background = as_dict(styles.get("background")) or {}
    media = as_dict(styles.get("media")) or {}
    rules: list[str] = []

    color = background.get("color")
    if isinstance(color, str) and color.strip():
        rules.append(f"background-color: {normalize_color(color, fallback_raw=True)};")
    value = _image(background.get("image"), theme_dir)
    if value:
        rules.append(f"background-image: {value};")
    value = _image(media.get("source"), theme_dir)
    if value:
        rules.append(f"background-image: {value};")
    return rules


def text_rules(styles: ThemeMap, theme_dir: Path) -> list[str]:
    text = as_dict(styles.get("text")) or {}
    font = as_dict(text.get("font")) or {}
    rules: list[str] = []

    color = text.get("color")
    if isinstance(color, str) and color.strip():
        rules.append(f"color: {normalize_color(color, fallback_raw=True)};")
    family = _font_family(font.get("family"), theme_dir)
    if family:
        rules.append(f"font-family: {family};")
    size = _measure(font.get("size"))
    if size:
        rules.append(f"font-size: {size};")
    for key in ("weight", "style"):
        value = str(font.get(key, "")).strip()
        if value:
            rules.append(f"font-{key}: {value};")
    return rules


def border_rules(styles: ThemeMap, _theme_dir: Path) -> list[str]:
    background = as_dict(styles.get("background")) or {}
    border = as_dict(styles.get("border"))
    rules: list[str] = []

    if border is not None:
        width = _measure(border.get("width")) or ""
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

    radius_value = _measure(radius)
    if radius_value:
        if not rules:
            rules.append("border: none;")
        rules.append(f"border-radius: {radius_value};")
    elif border is None and _has_background(styles):
        rules.append("border: none;")
    return rules


def padding_rules(styles: ThemeMap, _theme_dir: Path) -> list[str]:
    content = as_dict(styles.get("content")) or {}
    rules: list[str] = []
    value = _box(styles.get("padding", content.get("padding")))
    if value:
        rules.append(f"padding: {value};")

    for side in ("top", "right", "bottom", "left"):
        value = _measure(
            styles.get(
                f"padding-{side}",
                styles.get(
                    f"padding_{side}",
                    content.get(
                        f"padding-{side}",
                        content.get(f"padding_{side}"),
                    ),
                ),
            )
        )
        if value:
            rules.append(f"padding-{side}: {value};")
    return rules


def margin_rules(styles: ThemeMap, _theme_dir: Path) -> list[str]:
    content = as_dict(styles.get("content")) or {}
    rules: list[str] = []
    value = _box(styles.get("margin", content.get("margin")))
    if value:
        rules.append(f"margin: {value};")

    for side in ("top", "right", "bottom", "left"):
        value = _measure(
            styles.get(
                f"margin-{side}",
                styles.get(
                    f"margin_{side}",
                    content.get(
                        f"margin-{side}",
                        content.get(f"margin_{side}"),
                    ),
                ),
            )
        )
        if value:
            rules.append(f"margin-{side}: {value};")
    return rules


def passthrough_rules(styles: ThemeMap, _theme_dir: Path) -> list[str]:
    raw = styles.get("qss")
    if isinstance(raw, str):
        value = raw.strip()
        return [value if value.endswith(";") else f"{value};"] if value else []

    data = as_dict(raw)
    if data is None:
        return []
    rules: list[str] = []
    for raw_key, raw_value in data.items():
        key = str(raw_key).strip()
        value = "" if raw_value is None else str(raw_value).strip()
        if key and value:
            rules.append(f"{key}: {value};")
    return rules


def build_rules(styles: ThemeMap, theme_dir: Path) -> list[str]:
    rules: list[str] = []
    for builder in (
        background_rules,
        text_rules,
        border_rules,
        margin_rules,
        padding_rules,
        passthrough_rules,
    ):
        rules.extend(builder(styles, theme_dir))
    return rules


def _border_side_rules(side: str, border: ThemeMap) -> list[str]:
    raw = border.get(side)
    if isinstance(raw, str):
        value = raw.strip().rstrip(";")
        return [f"border-{side}: {value};"] if value else []

    data = as_dict(raw) or {}
    width = _measure(data.get("width", border.get(f"{side}_width"))) or ""
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
    background = as_dict(styles.get("background")) or {}
    media = as_dict(styles.get("media")) or {}
    return any(background.get(key) for key in ("color", "image")) or bool(
        media.get("source")
    )
