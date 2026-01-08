import re
from src.utils.logging import logger
from src.utils.regex import SIGNAL_NAME_PATTERN


def emit(signal, *args):
    match = re.search(SIGNAL_NAME_PATTERN, str(signal))
    logger_method, signal_name = [logger.debug, match.group(1)] if match else [logger.warning, 'Unknown Signal']
    logger_method(f'Emitting \'{signal_name}\'. Args: {args}')
    signal.emit(*args)