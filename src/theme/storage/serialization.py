from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

_INDENT = '  '
_ANIMATION_EVENT_KEYS = {'on', 'action', 'state', 'event'}
_EOF_COMMENT_ANCHOR = ('__eof__', 0)
_LINE_COMMENT_PATTERN = re.compile(r'//|/\*')


@dataclass(slots=True)
class _CommentBundle:
    leading: list[str] = field(default_factory=list)
    inline: str = ''


def format_theme_json(payload: Any, *, existing_text: str | None = None) -> str:
    text = f'{_serialize_theme_value(compact_theme_payload(payload))}\n'
    if not isinstance(existing_text, str) or not existing_text.strip():
        return text
    return preserve_json5_comments(existing_text, text)


def preserve_json5_comments(source_text: str, target_text: str) -> str:
    comments = _collect_json5_comments(source_text)
    if not comments:
        return target_text

    counts: dict[str, int] = {}
    output: list[str] = []
    for line in target_text.splitlines():
        code, _comment = _split_code_comment(line)
        anchor = _normalize_comment_anchor(code)
        bundle = None
        if anchor:
            occurrence = counts.get(anchor, 0)
            counts[anchor] = occurrence + 1
            bundle = comments.get((anchor, occurrence))

        if bundle is not None:
            indent = line[:len(line) - len(line.lstrip())]
            output.extend(_reindent_comment_line(item, indent) for item in bundle.leading)
            if bundle.inline and not _comment:
                line = f'{line.rstrip()} {bundle.inline.strip()}'
        output.append(line)

    if eof_bundle := comments.get(_EOF_COMMENT_ANCHOR):
        output.extend(eof_bundle.leading)

    return '\n'.join(output).rstrip() + '\n'


def compact_theme_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        compacted: dict[str, Any] = {}
        for key, value in payload.items():
            if key == 'animations':
                compacted[key] = compact_animations(value)
            else:
                compacted[key] = compact_theme_payload(value)
        return compacted

    if isinstance(payload, list):
        return [compact_theme_payload(item) for item in payload]

    return deepcopy(payload)


def compact_animations(raw: Any) -> Any:
    if not isinstance(raw, list):
        return compact_theme_payload(raw)

    grouped: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for item in raw:
        if not isinstance(item, dict):
            order_key = f'__raw__:{len(order)}'
            grouped[order_key] = {'events': [], 'payload': compact_theme_payload(item)}
            order.append(order_key)
            continue

        payload = {
            key: compact_theme_payload(value)
            for key, value in item.items()
            if key not in _ANIMATION_EVENT_KEYS
        }
        events = _animation_events(item)
        grouping_key = _stable_json_key(payload)
        if grouping_key not in grouped:
            grouped[grouping_key] = {'events': [], 'payload': payload}
            order.append(grouping_key)

        for event in events:
            if event not in grouped[grouping_key]['events']:
                grouped[grouping_key]['events'].append(event)

    compacted: list[Any] = []
    for key in order:
        item = grouped[key]
        payload = item['payload']
        if not isinstance(payload, dict):
            compacted.append(payload)
            continue

        events = item['events']
        if events:
            output = {'on': events[0] if len(events) == 1 else events}
            output.update(payload)
            compacted.append(output)
        else:
            compacted.append(payload)
    return compacted


def _animation_events(item: dict[str, Any]) -> list[str]:
    events: list[str] = []
    for key in ('on', 'action', 'state', 'event'):
        if key not in item:
            continue

        raw = item.get(key)
        if isinstance(raw, str):
            values = [raw]
        elif isinstance(raw, (list, tuple, set)):
            values = list(raw)
        else:
            values = [raw]

        for value in values:
            text = str(value).strip()
            if text and text not in events:
                events.append(text)

    return events


def _stable_json_key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _serialize_theme_value(value: Any, *, level: int = 0, parent_key: str | None = None) -> str:
    match value:
        case dict():
            if not value:
                return '{}'

            child_indent = _INDENT * (level + 1)
            lines: list[str] = []
            for key, child in value.items():
                encoded_key = json.dumps(str(key), ensure_ascii=False)
                encoded_child = _serialize_theme_value(child, level=level + 1, parent_key=str(key))
                lines.append(f'{child_indent}{encoded_key}: {encoded_child}')
            closing_indent = _INDENT * level
            return '{\n' + ',\n'.join(lines) + f'\n{closing_indent}' + '}'

        case list():
            if not value:
                return '[]'

            child_indent = _INDENT * (level + 1)
            closing_indent = _INDENT * level
            lines: list[str] = []
            for child in value:
                if parent_key == 'stops':
                    encoded_child = _serialize_stop_inline(child)
                else:
                    encoded_child = _serialize_theme_value(child, level=level + 1)
                lines.append(f'{child_indent}{encoded_child}')
            return '[\n' + ',\n'.join(lines) + f'\n{closing_indent}' + ']'

        case _:
            return json.dumps(value, ensure_ascii=False)


def _serialize_stop_inline(value: Any) -> str:
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False, separators=(', ', ': '))
    if isinstance(value, tuple):
        return json.dumps(list(value), ensure_ascii=False, separators=(', ', ': '))
    return _serialize_theme_value(value)


def _collect_json5_comments(text: str) -> dict[tuple[str, int], _CommentBundle]:
    comments: dict[tuple[str, int], _CommentBundle] = {}
    counts: dict[str, int] = {}
    pending: list[str] = []
    in_block = False

    for line in text.splitlines():
        stripped = line.strip()
        if in_block:
            pending.append(line)
            if '*/' in stripped:
                in_block = False
            continue

        if stripped.startswith('/*'):
            pending.append(line)
            in_block = '*/' not in stripped
            continue

        if stripped.startswith('//'):
            pending.append(line)
            continue

        if not stripped:
            if pending:
                pending.append(line)
            continue

        code, inline_comment = _split_code_comment(line)
        anchor = _normalize_comment_anchor(code)
        if not anchor:
            if inline_comment:
                pending.append(inline_comment)
            continue

        occurrence = counts.get(anchor, 0)
        counts[anchor] = occurrence + 1
        if pending or inline_comment:
            bundle = comments.setdefault((anchor, occurrence), _CommentBundle())
            bundle.leading.extend(pending)
            if inline_comment:
                bundle.inline = inline_comment
            pending = []

    if pending:
        comments[_EOF_COMMENT_ANCHOR] = _CommentBundle(leading=pending)
    return comments


def _split_code_comment(line: str) -> tuple[str, str]:
    in_string = False
    quote = ''
    escaped = False

    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue

        if char == '\\' and in_string:
            escaped = True
            continue

        if char in {'"', "'"}:
            if not in_string:
                in_string = True
                quote = char
            elif quote == char:
                in_string = False
                quote = ''
            continue

        if in_string:
            continue

        if line.startswith('//', index) or line.startswith('/*', index):
            return line[:index].rstrip(), line[index:].rstrip()

    return line.rstrip(), ''


def _normalize_comment_anchor(code: str) -> str:
    text = code.strip()
    if not text:
        return ''
    text = text.removesuffix(',').strip()
    if match := re.match(r'^((?:"(?:\\.|[^"])*"|\'(?:\\.|[^\'])*\'|[A-Za-z_$][\w$-]*)\s*:)', text):
        return re.sub(r'\s+', ' ', match.group(1).strip())
    return re.sub(r'\s+', ' ', text)


def _reindent_comment_line(line: str, indent: str) -> str:
    stripped = line.lstrip()
    return f'{indent}{stripped}' if stripped else line
