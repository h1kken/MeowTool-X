import re
from typing import Optional, Callable
from PySide6.QtCore import Signal
from src.utils.logging import logger
from src.utils.regex import SIGNAL_NAME_PATTERN


def connect(signal: Signal, *, func: Optional[Callable] = None):
    match = re.search(SIGNAL_NAME_PATTERN, str(signal))
    signal_name = match.group(1) if match else 'Unknown Signal'
    func_name = getattr(func, '__qualname__', repr(func))
    logger.debug(f'Connecting \'{signal_name}\' to \'{func_name}\'')
    signal.connect(func)


def emit(signal: Signal, *args):
    match = re.search(SIGNAL_NAME_PATTERN, str(signal))
    signal_name = match.group(1) if match else 'Unknown Signal'
    logger.debug(f'Emitting \'{signal_name}\'. Args: {args}')
    signal.emit(*args)
