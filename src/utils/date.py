from datetime import datetime
from src.utils.logger import logger
from src.utils.consts import ROBLOX_DATE_FORMATS


def current_date(output_format: str) -> str:
    return datetime.now().strftime(output_format)

def current_time_in_ms() -> int:
    return int((datetime.now() - datetime(1970, 1, 1)).total_seconds() * 1000)

def convert_date(input_date: str, output_format: str) -> str:
    for date_format in ROBLOX_DATE_FORMATS:
        try:
            return datetime.strptime(input_date, date_format).strftime(output_format)
        except ValueError:
            ...
    logger.warning(f'Can\'t convert date: {input_date}')
