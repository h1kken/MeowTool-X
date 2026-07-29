from fnmatch import fnmatchcase
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

_TARGET_PATTERN = re.compile(
    r'(?P<base>[a-zA-Z_*][\w*]*)'
    r'(?P<props>(?:\[\s*\w+\s*=\s*(?:"(?:\\.|[^"])*"|\'(?:\\.|[^\'])*\'|[^\]]+)\s*\])*)'
)
_TARGET_PROPERTY_PATTERN = re.compile(
    r'\[\s*(?P<key>\w+)\s*=\s*(?P<value>"(?:\\.|[^"])*"|\'(?:\\.|[^\'])*\'|[^\]]+)\s*\]'
)

_CLASS_TARGET_FAMILIES: dict[str, tuple[str, ...]] = {}


def _strip_quotes(value: str) -> str:
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        quote = text[0]
        text = text[1:-1]
        text = text.replace(f'\\{quote}', quote).replace('\\\\', '\\')
    return text


def _is_wildcard_target(text: str) -> bool:
    return '*' in text


def _widget_class_matches(widget: QWidget, target: str) -> bool:
    family_names = _CLASS_TARGET_FAMILIES.get(target, (target,))
    return any(cls.__name__ in family_names for cls in type(widget).mro())


def _widget_class_wildcard_matches(widget: QWidget, target: str) -> bool:
    return any(fnmatchcase(cls.__name__, target) for cls in type(widget).mro())


def parse_qss_target(target: str) -> tuple[str, list[tuple[str, str]]] | None:
    text = target.strip()
    if not text:
        return None

    match = _TARGET_PATTERN.fullmatch(text)
    if not match:
        return None

    base = str(match.group('base')).strip()
    props_text = str(match.group('props') or '').strip()
    properties: list[tuple[str, str]] = []

    if props_text:
        for prop_match in _TARGET_PROPERTY_PATTERN.finditer(props_text):
            key = str(prop_match.group('key')).strip()
            value = _strip_quotes(str(prop_match.group('value')))
            properties.append((key, value))

    return base, properties


def normalize_qss_target(target: str) -> str:
    parsed = parse_qss_target(target)
    if parsed:
        obj_name, properties = parsed
        if not properties:
            return obj_name

        prop_chunks: list[str] = []
        for key, value in properties:
            escaped = value.replace('\\', '\\\\').replace('"', '\\"')
            prop_chunks.append(f'[{key}="{escaped}"]')
        return f'{obj_name}{''.join(prop_chunks)}'
    return target


def find_target_widgets(root: QWidget, target: str) -> list[QWidget]:
    if target == '*':
        return [root, *root.findChildren(QWidget)]

    if target.startswith('#'):
        target = target[1:]

    chain = parse_selector_chain(target)
    if chain and len(chain) > 1:
        return _find_widgets_by_selector_chain(root, chain)

    parsed = parse_qss_target(target)
    if parsed:
        obj_name, properties = parsed
        if not properties:
            return _find_widgets(root, obj_name)

        widgets = _find_widgets(root, obj_name)
        return [
            widget for widget in widgets
            if all(str(widget.property(key)) == expected for key, expected in properties)
        ]

    return _find_widgets(root, str(target))


def resolve_target_widgets(root: QWidget, target: str, *, include_window: bool = False) -> list[QWidget]:
    widgets = find_target_widgets(root, target)
    if include_window:
        root_window = root.window()
        if root_window is not root:
            widgets.extend(find_target_widgets(root_window, target))
    return _dedupe_widgets(widgets)


def _find_widgets(root: QWidget, obj_name: str) -> list[QWidget]:
    widgets: list[QWidget] = []

    if _is_wildcard_target(obj_name):
        if obj_name.startswith('MT'):
            if _widget_class_wildcard_matches(root, obj_name):
                widgets.append(root)
            widgets.extend(
                widget
                for widget in root.findChildren(QWidget)
                if _widget_class_wildcard_matches(widget, obj_name)
            )
            return _dedupe_widgets(widgets)

        if fnmatchcase(root.objectName(), obj_name):
            widgets.append(root)
        widgets.extend(
            widget
            for widget in root.findChildren(QWidget)
            if fnmatchcase(widget.objectName(), obj_name)
        )
        return _dedupe_widgets(widgets)

    if obj_name.startswith('MT'):
        if _widget_class_matches(root, obj_name):
            widgets.append(root)
        widgets.extend(widget for widget in root.findChildren(QWidget) if _widget_class_matches(widget, obj_name))
        return _dedupe_widgets(widgets)

    if root.objectName() == obj_name:
        widgets.append(root)
    widgets.extend(root.findChildren(QWidget, obj_name))
    return _dedupe_widgets(widgets)


def parse_selector_chain(target: str) -> list[tuple[str, str]] | None:
    text = target.strip()
    if not text:
        return None

    segments: list[tuple[str, str]] = []
    current: list[str] = []
    bracket_depth = 0
    quote_char = ''
    next_relation = ''
    has_combinator = False
    index = 0

    def flush_segment() -> None:
        nonlocal next_relation
        segment_text = ''.join(current).strip()
        current.clear()
        if not segment_text:
            return
        segments.append((next_relation, segment_text))
        next_relation = ''

    while index < len(text):
        char = text[index]

        if quote_char:
            current.append(char)
            if char == quote_char and (index == 0 or text[index - 1] != '\\'):
                quote_char = ''
            index += 1
            continue

        if char in {'"', "'"}:
            quote_char = char
            current.append(char)
            index += 1
            continue

        if char == '[':
            bracket_depth += 1
            current.append(char)
            index += 1
            continue

        if char == ']':
            bracket_depth = max(0, bracket_depth - 1)
            current.append(char)
            index += 1
            continue

        if bracket_depth == 0 and char == '>':
            flush_segment()
            next_relation = '>'
            has_combinator = True
            index += 1
            continue

        if bracket_depth == 0 and char.isspace():
            flush_segment()
            while index < len(text) and text[index].isspace():
                index += 1
            if index < len(text) and text[index] == '>':
                continue
            if segments and not next_relation:
                next_relation = ' '
                has_combinator = True
            continue

        current.append(char)
        index += 1

    flush_segment()

    if not has_combinator or len(segments) < 2:
        return None

    if any(parse_qss_target(segment) is None for _, segment in segments):
        return None

    return segments


def _find_widgets_by_selector_chain(root: QWidget, chain: list[tuple[str, str]]) -> list[QWidget]:
    if not chain:
        return []

    _, first_segment = chain[0]
    current_widgets = _find_widgets_matching_selector(root, first_segment, include_root=True)

    for relation, segment in chain[1:]:
        next_widgets: list[QWidget] = []
        for parent_widget in current_widgets:
            if relation == '>':
                candidates = [
                    child
                    for child in parent_widget.children()
                    if isinstance(child, QWidget)
                ]
            else:
                candidates = parent_widget.findChildren(
                    QWidget,
                    options=Qt.FindChildOption.FindChildrenRecursively,
                )

            next_widgets.extend(
                widget
                for widget in candidates
                if _widget_matches_selector(widget, segment)
            )
        current_widgets = _dedupe_widgets(next_widgets)
        if not current_widgets:
            break

    return current_widgets


def _find_widgets_matching_selector(root: QWidget, selector: str, *, include_root: bool) -> list[QWidget]:
    widgets = _find_widgets(root, selector_base(selector))
    if include_root and _widget_matches_selector(root, selector) and root not in widgets:
        widgets.insert(0, root)
    return [
        widget for widget in widgets
        if _widget_matches_selector(widget, selector)
    ]


def _widget_matches_selector(widget: QWidget, selector: str) -> bool:
    parsed = parse_qss_target(selector)
    if not parsed:
        return False

    base, properties = parsed
    if not _widget_matches_base(widget, base):
        return False

    return all(str(widget.property(key)) == expected for key, expected in properties)


def _widget_matches_base(widget: QWidget, base: str) -> bool:
    if base == '*':
        return True

    if _is_wildcard_target(base):
        if base.startswith('MT'):
            return _widget_class_wildcard_matches(widget, base)
        return fnmatchcase(widget.objectName(), base)

    if base.startswith('MT'):
        return _widget_class_matches(widget, base)

    return widget.objectName() == base


def selector_base(selector: str) -> str:
    parsed = parse_qss_target(selector)
    return parsed[0] if parsed else selector


def _dedupe_widgets(widgets: list[QWidget]) -> list[QWidget]:
    deduped: list[QWidget] = []
    seen: set[int] = set()
    for widget in widgets:
        widget_id = id(widget)
        if widget_id in seen:
            continue
        seen.add(widget_id)
        deduped.append(widget)
    return deduped
