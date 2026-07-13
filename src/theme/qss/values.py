from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from PySide6.QtGui import QFontDatabase

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
_FONT_EXTENSIONS = {".otf", ".ttc", ".ttf", ".woff", ".woff2"}


def measure(value: Any) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return f"{value:g}px"
    if isinstance(value, str):
        text = value.strip()
        if text:
            try:
                return f"{float(text):g}px"
            except ValueError:
                pass
            return text
    return None


def box(value: Any) -> str | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return measure(value)
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
    values = [measure(part) for part in parts]
    return " ".join(cast(list[str], values)) if all(values) else None


def image(value: Any, theme_dir: Path) -> str | None:
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


def font_family(value: Any, theme_dir: Path) -> str | None:
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
