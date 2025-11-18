from pathlib import Path
import sys

def get_root() -> Path:
    if getattr(sys, '_MEIPASS', None):
        return Path(sys._MEIPASS).resolve()

    return Path(__file__).resolve().parent

ROOT = get_root()