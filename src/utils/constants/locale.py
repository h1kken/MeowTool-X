import ctypes
import locale
import os


def _normalize_locale_name(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    text = text.split('.', 1)[0].split('@', 1)[0].replace('-', '_')
    return text or None


def _windows_locale_name() -> str | None:
    if os.name != 'nt':
        return None

    try:
        buffer = ctypes.create_unicode_buffer(85)
        length = ctypes.windll.kernel32.GetUserDefaultLocaleName(buffer, len(buffer))
        if length > 0:
            return _normalize_locale_name(buffer.value)
    except Exception:
        return None

    return None


def _resolve_system_locale() -> str:
    candidates = [
        _windows_locale_name(),
        _normalize_locale_name(locale.getlocale()[0]),
        _normalize_locale_name(locale.getlocale(locale.LC_CTYPE)[0]),
    ]

    for candidate in candidates:
        if candidate:
            return candidate

    return 'en_US'


def _resolve_system_language(locale_name: str) -> str:
    if not locale_name:
        return 'EN'
    return locale_name.split('_', 1)[0].upper()


SYSTEM_LOCALE = _resolve_system_locale()
SYSTEM_LANGUAGE = _resolve_system_language(SYSTEM_LOCALE)
LANGUAGE_LOCALE_DEFAULTS = {
    'en': 'en_US',
    'ru': 'ru_RU',
}
DEFAULT_FALLBACK_LOCALE = 'en_US'


__all__ = [name for name in globals() if name.isupper()]
