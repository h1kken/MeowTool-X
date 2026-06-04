from __future__ import annotations

import hashlib
import re
import threading
import urllib.parse
import urllib.request
from copy import deepcopy
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QWidget

from src.theme.colors import normalize_color, normalize_color_or_raw, to_qcolor
from src.theme.qss.normalizer import StyleNormalizer
from src.utils.constants import GRADIENT_DIRECTIONS, PATH_FONTS, ROOT, SUPPORTED_BG_MEDIA_EXTENSIONS

_FONT_SOURCE_PATTERN = re.compile(r'^url\((?P<value>.+)\)$', re.IGNORECASE)
_FONT_CSS_URL_PATTERN = re.compile(r'url\((?P<value>[^)]+)\)', re.IGNORECASE)
_SUPPORTED_FONT_EXTENSIONS = {'.ttf', '.otf', '.ttc', '.woff', '.woff2'}


class _FontDownloadNotifier(QObject):
    font_ready = Signal(str)


class QssBuilder(StyleNormalizer):
    def __init__(self, theme_base_dir: Path | None = None) -> None:
        self._theme_base_dir = theme_base_dir
        self._font_family_cache: dict[str, str] = {}
        self._pending_font_downloads: set[str] = set()
        self._font_download_lock = threading.Lock()
        self._font_notifier = _FontDownloadNotifier()

    @property
    def font_ready(self):
        return self._font_notifier.font_ready

    def set_theme_base_dir(self, theme_base_dir: Path | None) -> None:
        self._theme_base_dir = theme_base_dir

    def build(
        self,
        obj_name: str,
        styles: dict[str, Any],
        selector: str = '#',
        *,
        widgets: list[QWidget] | None = None,
        root_widget: QWidget | None = None,
    ) -> str:
        if not isinstance(styles, dict):
            return ''

        widgets = widgets or []
        if isinstance(obj_name, str) and obj_name != '*' and ('*' in obj_name or obj_name.startswith('MT')):
            return self._build_widget_specific_qss(obj_name, styles, widgets)

        if self.contains_resolvable_radius(styles):
            resolved_qss = self._build_widget_specific_qss(obj_name, styles, widgets)
            if resolved_qss:
                return resolved_qss

            sample_widget = next(iter(widgets), root_widget)
            if isinstance(sample_widget, QWidget):
                styles = self.resolve_relative_styles(styles, sample_widget)

        return self._build_qss_block(obj_name, styles, selector)

    def build_rules(self, data: Any) -> list[str]:
        if not isinstance(data, dict):
            return []

        rules: list[str] = []

        bg_data = data.get('background') if isinstance(data.get('background'), dict) else {}
        if isinstance(bg_data, dict):
            if (bg_color := self.build_background_color(bg_data.get('color'))):
                rules.append(bg_color)
            if (bg_image := self.build_background_image(bg_data.get('image'))):
                rules.append(bg_image)

        if isinstance((media_data := data.get('media')), dict):
            source = media_data.get('source')
            if isinstance(source, str) and source.strip():
                resolved_source = self.resolve_media_source(source)
                if (media_bg_image := self.build_background_image(resolved_source)):
                    rules.append(media_bg_image)

        if isinstance((text_data := data.get('text')), dict):
            if (text_color := text_data.get('color')):
                rules.append(f'color: {normalize_color_or_raw(text_color)};')
            if isinstance((font_data := text_data.get('font')), dict):
                if (family := font_data.get('family')):
                    if (resolved_family := self.resolve_font_family(str(family))):
                        rules.append(f'font-family: {resolved_family};')
                if (size := self.normalize_measure(font_data.get('size'))):
                    rules.append(f'font-size: {size};')
                if (weight := font_data.get('weight')):
                    rules.append(f'font-weight: {weight};')
                if (style := font_data.get('style')):
                    rules.append(f'font-style: {style};')

        if (qss_rules := self.build_qss_passthrough_rules(data.get('qss'))):
            rules.extend(qss_rules)

        if isinstance((border_data := data.get('border')), dict):
            border_rules = self.build_border_rules(border_data)
            rules.extend(border_rules)
            radius_value = border_data.get('radius', bg_data.get('radius') if isinstance(bg_data, dict) else None)
            if (radius_rule := self.build_border_radius_rule(radius_value)):
                if not border_rules:
                    rules.append('border: none;')
                rules.append(radius_rule)
        elif isinstance(bg_data, dict) and (radius_rule := self.build_border_radius_rule(bg_data.get('radius'))):
            rules.append('border: none;')
            rules.append(radius_rule)

        rules.extend(self.build_padding_rules(data))

        return rules

    def build_background_color(self, data: Any) -> str | None:
        if data is None:
            return None
        if isinstance(data, str):
            return f'background-color: {normalize_color_or_raw(data)};'
        if isinstance(data, dict) and (gradient := self.build_gradient(data)):
            return f'background: {gradient};'
        return None

    def build_background_image(self, data: Any) -> str | None:
        if not isinstance(data, str):
            return None

        if not (value := data.strip()):
            return None

        if value.startswith('url('):
            return f'background-image: {value};'

        raw_path = Path(value.split('?', 1)[0].split('#', 1)[0])
        if raw_path.suffix.lower() in SUPPORTED_BG_MEDIA_EXTENSIONS:
            normalized = value.replace('\\', '/')
            return f'background-image: url("{normalized}");'

        return f'background-image: {value};'

    def build_gradient(self, data: dict[str, Any]) -> str | None:
        if not isinstance(data, dict):
            return None

        if not (stops := self.parse_gradient_stops(data.get('stops'))):
            return None

        stop_text = ', '.join(f'stop:{pos} {color}' for pos, color in stops)
        match data.get('type', 'linear'):
            case 'linear':
                direction = data.get('direction', 'vertical')
                x1, y1, x2, y2 = GRADIENT_DIRECTIONS.get(direction, (0, 0, 0, 1))
                return f'qlineargradient(x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}, {stop_text})'
            case 'radial':
                cx, cy = data.get('center', (0.5, 0.5))
                radius = data.get('radius', 0.5)
                return f'qradialgradient(cx:{cx}, cy:{cy}, radius:{radius}, {stop_text})'
        return None

    def parse_gradient_stops(self, data: Any) -> list[tuple[float, str]]:
        if not isinstance(data, (list, tuple)):
            return []

        stops: list[tuple[float, str]] = []
        for stop in data:
            pos: Any = None
            color: Any = None

            if isinstance(stop, dict):
                pos = stop.get('pos', stop.get('position'))
                color = stop.get('color')
            elif isinstance(stop, (list, tuple)) and len(stop) >= 2:
                pos, color = stop[0:2]
            else:
                continue

            if color is None:
                continue

            try:
                pos_value = float(pos)
            except (TypeError, ValueError):
                continue

            resolved = to_qcolor(color)
            if resolved is None:
                continue

            normalized = normalize_color(resolved)
            if normalized is None:
                continue

            stops.append((pos_value, normalized))

        return stops

    def build_border(self, data: dict[str, Any]) -> str | None:
        rules = self.build_border_rules(data)
        return '\n'.join(rules) if rules else None

    def build_border_rules(self, data: dict[str, Any]) -> list[str]:
        if not isinstance(data, dict):
            return []

        rules: list[str] = []
        width = self.normalize_measure(data.get('width')) or ''
        style = str(data.get('style', '')).strip()
        color = normalize_color_or_raw(data.get('color', '')) if str(data.get('color', '')).strip() else ''
        if all((width, style, color)):
            rules.append(f'border: {width} {style} {color};')
        else:
            if width:
                rules.append(f'border-width: {width};')
            if style:
                rules.append(f'border-style: {style};')
            if color:
                rules.append(f'border-color: {color};')

        for side in ('top', 'right', 'bottom', 'left'):
            side_rules = self.build_border_side_rules(side, data)
            rules.extend(side_rules)

        return rules

    def build_border_side_rules(self, side: str, data: dict[str, Any]) -> list[str]:
        raw_side_data = data.get(side)
        if isinstance(raw_side_data, str):
            return [f'border-{side}: {raw_side_data.strip().rstrip(";")};'] if raw_side_data.strip() else []
        side_data = raw_side_data if isinstance(raw_side_data, dict) else {}

        width = self.normalize_measure(side_data.get('width', data.get(f'{side}_width', ''))) or ''
        style = str(side_data.get('style', data.get(f'{side}_style', ''))).strip()
        color_value = side_data.get('color', data.get(f'{side}_color', ''))
        color = normalize_color_or_raw(color_value) if str(color_value).strip() else ''

        if not any((width, style, color)):
            return []

        if all((width, style, color)):
            return [f'border-{side}: {width} {style} {color};']

        rules: list[str] = []
        if width:
            rules.append(f'border-{side}-width: {width};')
        if style:
            rules.append(f'border-{side}-style: {style};')
        if color:
            rules.append(f'border-{side}-color: {color};')
        return rules

    def build_border_radius_rule(self, data: Any) -> str | None:
        radius = self.normalize_measure(data)
        if not isinstance(radius, str) or not radius.strip():
            return None
        return f'border-radius: {radius.strip()};'

    def build_padding_rules(self, data: Any) -> list[str]:
        if isinstance(data, dict):
            box = self.normalize_box(data.get('padding'))
            side_values = {
                side: self.normalize_measure(data.get(f'padding-{side}', data.get(f'padding_{side}')))
                for side in ('top', 'right', 'bottom', 'left')
            }
        else:
            box = self.normalize_box(data)
            side_values = {side: None for side in ('top', 'right', 'bottom', 'left')}

        rules: list[str] = []
        if box is not None:
            left, top, right, bottom = box
            if left == right == top == bottom:
                rules.append(f'padding: {top}px;')
            else:
                rules.append(f'padding: {top}px {right}px {bottom}px {left}px;')

        for side, value in side_values.items():
            if isinstance(value, str) and value.strip():
                rules.append(f'padding-{side}: {value};')

        return rules

    def build_padding_rule(self, data: Any) -> str | None:
        rules = self.build_padding_rules(data)
        return rules[-1] if rules else None

    def build_qss_passthrough_rules(self, data: Any) -> list[str]:
        if isinstance(data, str):
            text = data.strip()
            if not text:
                return []
            return [text if text.endswith(';') else f'{text};']

        if not isinstance(data, dict):
            return []

        rules: list[str] = []
        for key, value in data.items():
            if not isinstance(key, str) or value is None:
                continue
            name = key.strip()
            text = str(value).strip()
            if name and text:
                rules.append(f'{name}: {text};')
        return rules

    def parse_measure(self, data: Any) -> float | None:
        if isinstance(data, bool):
            return None
        if isinstance(data, (int, float)):
            return float(data)
        if isinstance(data, str):
            value = data.strip().lower()
            if not value or value.endswith('%'):
                return None
            if value.endswith('px'):
                value = value[:-2].strip()
            try:
                return float(value)
            except ValueError:
                return None
        return None

    def contains_resolvable_radius(self, data: Any) -> bool:
        if not isinstance(data, dict):
            return False

        if isinstance((border := data.get('border')), dict):
            if self._radius_needs_widget_resolution(border.get('radius')):
                return True

        if isinstance((background := data.get('background')), dict):
            if self._radius_needs_widget_resolution(background.get('radius')):
                return True

        for value in data.values():
            if isinstance(value, dict) and self.contains_resolvable_radius(value):
                return True
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and self.contains_resolvable_radius(item):
                        return True
        return False

    def contains_percent_radius(self, data: Any) -> bool:
        return self.contains_resolvable_radius(data)

    def resolve_relative_styles(self, data: Any, widget: QWidget) -> Any:
        if isinstance(data, dict):
            resolved: dict[str, Any] = {}
            for key, value in data.items():
                if key in {'background', 'border'} and isinstance(value, dict):
                    resolved[key] = self._resolve_radius_styles(value, widget)
                else:
                    resolved[key] = self.resolve_relative_styles(value, widget)
            return resolved

        if isinstance(data, list):
            return [self.resolve_relative_styles(value, widget) for value in data]

        return deepcopy(data)

    def resolve_media_source(self, source: str) -> str:
        value = source.strip()
        if not value:
            return ''

        raw = Path(value).expanduser()
        candidates: list[Path] = [raw]
        if not raw.is_absolute():
            if self._theme_base_dir is not None:
                candidates.insert(0, self._theme_base_dir / raw)
            candidates.append(ROOT / raw)
            candidates.append(ROOT / 'src' / raw)

        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return str(candidate)

        return value

    def resolve_font_family(self, family: str) -> str:
        value = str(family or '').strip()
        if not value:
            return ''

        if not self._looks_like_font_source(value):
            return value

        cache_key = value
        if cache_key in self._font_family_cache:
            return self._font_family_cache[cache_key]

        if self._is_remote_font_source(value) and self._cached_remote_font_path(self._unwrap_url_value(value)) is None:
            self._queue_remote_font_download(value)
            return ''

        loaded_family = self._load_font_family(value)
        if loaded_family:
            self._font_family_cache[cache_key] = loaded_family
        return loaded_family

    def _is_remote_font_source(self, value: str) -> bool:
        parsed = urllib.parse.urlparse(self._unwrap_url_value(value))
        return parsed.scheme in {'http', 'https'}

    def _looks_like_font_source(self, value: str) -> bool:
        source = self._unwrap_url_value(value)
        parsed = urllib.parse.urlparse(source)
        if parsed.scheme in {'http', 'https', 'file'}:
            return True

        suffix = Path(source.split('?', 1)[0].split('#', 1)[0]).suffix.lower()
        return suffix in _SUPPORTED_FONT_EXTENSIONS

    def _load_font_family(self, source: str) -> str:
        source = self._unwrap_url_value(source)
        if not source:
            return ''

        font_path = self._resolve_font_source_path(source)
        if font_path is None:
            return ''

        font_id = QFontDatabase.addApplicationFont(str(font_path))
        if font_id < 0:
            return ''

        families = QFontDatabase.applicationFontFamilies(font_id)
        return self._quote_font_family(families[0]) if families else ''

    def _resolve_font_source_path(self, source: str) -> Path | None:
        parsed = urllib.parse.urlparse(source)
        if parsed.scheme in {'http', 'https'}:
            return self._download_remote_font(source)

        if parsed.scheme == 'file':
            local_path = Path(urllib.request.url2pathname(parsed.path))
            return local_path if local_path.exists() and local_path.is_file() else None

        raw = Path(source).expanduser()
        candidates: list[Path] = [raw]
        if not raw.is_absolute():
            if self._theme_base_dir is not None:
                candidates.insert(0, self._theme_base_dir / raw)
            candidates.append(ROOT / raw)

        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate
        return None

    def _download_remote_font(self, url: str) -> Path | None:
        return self._resolve_remote_font_path(url, download=True)

    def _cached_remote_font_path(self, url: str) -> Path | None:
        return self._resolve_remote_font_path(url, download=False)

    def _resolve_remote_font_path(self, url: str, *, download: bool) -> Path | None:
        PATH_FONTS.mkdir(parents=True, exist_ok=True)
        parsed = urllib.parse.urlparse(url)
        suffix = Path(parsed.path).suffix.lower()

        if suffix in _SUPPORTED_FONT_EXTENSIONS:
            return self._url_cache_path(url, suffix, download=download)

        css_path = self._url_cache_path(url, '.css', download=download)
        if css_path is None:
            return None

        css_text = css_path.read_text(encoding='utf-8', errors='ignore')
        font_url = self._extract_font_url_from_css(css_text, base_url=url)
        if not font_url:
            return None

        font_suffix = Path(urllib.parse.urlparse(font_url).path).suffix.lower()
        if font_suffix not in _SUPPORTED_FONT_EXTENSIONS:
            font_suffix = '.woff2'
        return self._url_cache_path(font_url, font_suffix, download=download)

    def _url_cache_path(self, url: str, suffix: str, *, download: bool) -> Path | None:
        target = self._cached_url_path(url, suffix)
        if target.exists() and target.is_file():
            return target
        if not download:
            return None
        return self._download_url_to_cache(url, suffix)

    def _download_url_to_cache(self, url: str, suffix: str) -> Path | None:
        target = self._cached_url_path(url, suffix)
        if target.exists() and target.is_file():
            return target

        request = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0'},
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                target.write_bytes(response.read())
        except OSError:
            return None
        return target

    def _cached_url_path(self, url: str, suffix: str) -> Path:
        filename = hashlib.sha256(url.encode('utf-8')).hexdigest() + suffix
        return PATH_FONTS / filename

    def _queue_remote_font_download(self, source: str) -> None:
        url = self._unwrap_url_value(source)
        if not url:
            return

        with self._font_download_lock:
            if url in self._pending_font_downloads:
                return
            self._pending_font_downloads.add(url)

        def worker() -> None:
            try:
                path = self._download_remote_font(url)
                if path is not None:
                    self._font_notifier.font_ready.emit(url)
            finally:
                with self._font_download_lock:
                    self._pending_font_downloads.discard(url)

        thread = threading.Thread(target=worker, name='ThemeFontDownloader', daemon=True)
        thread.start()

    def _extract_font_url_from_css(self, css_text: str, *, base_url: str) -> str:
        matches = [self._strip_quotes(match.group('value')) for match in _FONT_CSS_URL_PATTERN.finditer(css_text)]
        if not matches:
            return ''

        preferred = next(
            (
                value for value in matches
                if Path(urllib.parse.urlparse(value).path).suffix.lower() in _SUPPORTED_FONT_EXTENSIONS
            ),
            matches[0],
        )
        return urllib.parse.urljoin(base_url, preferred)

    def _unwrap_url_value(self, value: str) -> str:
        text = value.strip()
        if match := _FONT_SOURCE_PATTERN.match(text):
            text = match.group('value').strip()
        return self._strip_quotes(text)

    def _strip_quotes(self, value: str) -> str:
        text = value.strip()
        if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
            return text[1:-1]
        return text

    def _quote_font_family(self, family: str) -> str:
        text = str(family or '').strip()
        if not text:
            return ''
        escaped = text.replace('"', '\\"')
        return f'"{escaped}"'

    def _build_qss_block(self, obj_name: str, styles: dict[str, Any], selector: str = '#') -> str:
        target_selector = f'{selector}{obj_name}'
        qss: list[str] = []

        if (base_rules := self.build_rules(styles)):
            qss.append(f'{target_selector} {{\n ' + '\n  '.join(base_rules) + '\n}')

        return '\n'.join(qss)

    def _build_widget_specific_qss(self, qss_target: str, styles: dict[str, Any], widgets: list[QWidget]) -> str:
        qss_parts: list[str] = []
        for widget in widgets:
            if not (selector := self._widget_selector(qss_target, widget)):
                continue
            resolved_styles = self.resolve_relative_styles(styles, widget)
            qss_parts.append(self._build_qss_block(selector, resolved_styles, selector=''))
        return '\n'.join(qss_parts)

    def _widget_selector(self, qss_target: str, widget: QWidget) -> str | None:
        if not isinstance(qss_target, str):
            return None

        object_name = widget.objectName().strip()
        if not object_name:
            return None

        if '[' in qss_target and qss_target.endswith(']'):
            return f'#{object_name}{qss_target[qss_target.index("["):]}'
        return f'#{object_name}'

    def _resolve_radius_styles(self, data: dict[str, Any], widget: QWidget) -> dict[str, Any]:
        resolved = deepcopy(data)
        radius = resolved.get('radius')
        if (radius_value := self._resolve_radius(radius, widget)) is not None:
            resolved['radius'] = radius_value
        return resolved

    def _radius_needs_widget_resolution(self, value: Any) -> bool:
        if isinstance(value, bool) or value is None:
            return False
        if isinstance(value, (int, float)):
            return True
        if not isinstance(value, str):
            return False
        text = value.strip()
        return bool(text) and (text.endswith('%') or self.parse_measure(text) is not None)

    def _resolve_radius(self, value: Any, widget: QWidget) -> str | None:
        base_size = self._radius_base_size(widget)
        if base_size <= 0:
            return None

        radius_px: float | None = None
        if isinstance(value, str) and value.strip().endswith('%'):
            try:
                percent = float(value.strip()[:-1].strip())
            except ValueError:
                return None
            radius_px = (base_size * percent) / 100.0
        else:
            radius_px = self.parse_measure(value)

        if radius_px is None:
            return None

        max_radius = self._safe_background_radius(float(base_size))
        resolved = max(0.0, min(float(radius_px), max_radius))
        return f'{resolved:g}px'

    def _safe_background_radius(self, base_size: float) -> float:
        max_radius = max(0.0, base_size / 2.0)
        if max_radius <= 1.0:
            return max_radius
        return max(0.0, max_radius - 1.0)

    def _radius_base_size(self, widget: QWidget) -> int:
        sizes: list[int] = []

        current = widget.size()
        current_width = int(current.width())
        current_height = int(current.height())
        if current_width > 1 and current_height > 1:
            current_base = min(current_width, current_height)
            # Qt widgets can report a temporary 640x480 size before the layout
            # pass. That value must not drive pill radii like 999px.
            if (current_width, current_height) != (640, 480):
                sizes.append(current_base)

        hint = widget.sizeHint()
        hint_width = int(hint.width())
        hint_height = int(hint.height())
        if hint_width > 1 and hint_height > 1:
            sizes.append(min(hint_width, hint_height))

        minimum_hint = widget.minimumSizeHint()
        min_hint_width = int(minimum_hint.width())
        min_hint_height = int(minimum_hint.height())
        if min_hint_width > 1 and min_hint_height > 1:
            sizes.append(min(min_hint_width, min_hint_height))

        if sizes:
            return min(sizes)

        minimum = widget.minimumSize()
        min_width = int(minimum.width())
        min_height = int(minimum.height())
        if min_width > 1 and min_height > 1:
            return min(min_width, min_height)

        if current_width > 0 and current_height > 0:
            return min(current_width, current_height)
        return 0
