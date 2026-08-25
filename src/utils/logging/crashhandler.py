import faulthandler

from pathlib import Path


def setup_crash_handler(path: Path) -> None:
    file = open(path / 'crash.log', 'a', encoding='utf-8')
    faulthandler.enable(file)
