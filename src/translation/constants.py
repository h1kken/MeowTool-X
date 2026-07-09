import locale


def _system_locale() -> str:
    candidates = (
        locale.getlocale()[0],
        locale.getlocale(locale.LC_CTYPE)[0],
    )

    for candidate in candidates:
        if not isinstance(candidate, str):
            continue

        text = candidate.strip().replace('-', '_')
        if not text or '_' not in text:
            continue

        language, region = text.split('_', 1)
        if language and region:
            return f'{language.lower()}_{region.upper()}'

    return 'en_US'


SYSTEM_LOCALE = _system_locale()
SYSTEM_LANGUAGE = SYSTEM_LOCALE.split('_', 1)[0].upper()


__all__ = [name for name in globals() if name.isupper()]
