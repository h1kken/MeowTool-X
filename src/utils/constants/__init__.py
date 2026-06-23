from __future__ import annotations

from importlib import import_module
from typing import Any

_LEGACY_EXPORT_MODULES: tuple[str, ...] = (
    "src.utils.constants.app",
    "src.utils.constants.datetime",
    "src.utils.constants.log",
    "src.app.paths",
    "src.config.paths",
    "src.db.paths",
    "src.theme.paths",
    "src.translation.paths",
    "src.ui.paths",
    "src.services.roblox.paths",
    "src.utils.filesystem.constants",
    "src.services.roblox.archive_support",
)
_LEGACY_ALIAS_TARGETS: dict[str, tuple[str, str]] = {
    "DEFAULT_THEME": ("src.theme.paths", "PATH_DEFAULT_THEME"),
}
_export_cache: dict[str, tuple[str, str]] | None = None


def _export_map() -> dict[str, tuple[str, str]]:
    global _export_cache
    if _export_cache is not None:
        return _export_cache

    exports = dict(_LEGACY_ALIAS_TARGETS)
    for module_name in _LEGACY_EXPORT_MODULES:
        module = import_module(module_name)
        for export_name in getattr(module, "__all__", ()):
            exports.setdefault(export_name, (module_name, export_name))
    _export_cache = exports
    return exports


def __getattr__(name: str) -> Any:
    target = _export_map().get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    module = import_module(module_name)
    return getattr(module, attr_name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_export_map()))
