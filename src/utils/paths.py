from pathlib import Path
from typing import Optional
from src.utils.logger import logger
from src.utils.consts import PATH_FISHSTRAP, PATH_BLOXSTRAP, PATH_ROBLOXPLAYERBETA
from src.utils.regex import ROBLOX_VERSION_PATH_PATTERN


def detect_roblox_path() -> Optional[Path]:
    if PATH_FISHSTRAP.exists(): return PATH_FISHSTRAP
    if PATH_BLOXSTRAP.exists(): return PATH_BLOXSTRAP

    if PATH_ROBLOXPLAYERBETA.exists():
        paths = sorted(
            list(PATH_ROBLOXPLAYERBETA.iterdir()),
            key=lambda e: e.stat().st_mtime,
            reverse=True
        )
        for path in paths:
            if ROBLOX_VERSION_PATH_PATTERN.search(str(path)):
                return path
    logger.warning('Can\'t detect Roblox installation path')