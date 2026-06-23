from pathlib import Path

from src.services.roblox.paths import PATH_BLOXSTRAP, PATH_FISHSTRAP, PATH_ROBLOXPLAYERBETA
from src.services.roblox.regexes import ROBLOX_VERSION_PATH_PATTERN
from src.utils.logging import logger


def detect_roblox_path() -> Path | None:
    if PATH_FISHSTRAP.exists():
        return PATH_FISHSTRAP
    if PATH_BLOXSTRAP.exists():
        return PATH_BLOXSTRAP

    if PATH_ROBLOXPLAYERBETA.exists():
        paths = sorted(
            list(PATH_ROBLOXPLAYERBETA.iterdir()),
            key=lambda entry: entry.stat().st_mtime,
            reverse=True,
        )
        for path in paths:
            if ROBLOX_VERSION_PATH_PATTERN.search(str(path)):
                return path

    logger.warning('Can\'t detect Roblox installation path')
    return None
