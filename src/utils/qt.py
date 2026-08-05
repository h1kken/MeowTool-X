def build_object_name(parts: tuple[str, ...]) -> str:
    _parts = [part.strip() for part in parts]
    return '_'.join(_parts) if all(_parts) else ''
