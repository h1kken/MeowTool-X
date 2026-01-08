from typing import Collection


def format_duration(
    ms: int,
    *,
    out_units: str | Collection[str] = 'all'
) -> dict[str, int]:
    s, ms = divmod(ms, 1000)
    m, s  = divmod(s,  60)
    h, m  = divmod(m,  60)
    d, h  = divmod(h,  24)
    
    units = {'d': d, 'h': h, 'm': m, 's': s, 'ms': ms}
    
    parts = {}
    for key in units.keys():
        if key in out_units or (isinstance(out_units, str) and 'all' == out_units.lower()):
            parts[key] = units[key]

    return parts