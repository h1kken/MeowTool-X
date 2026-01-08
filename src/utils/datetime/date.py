from typing import Optional
from datetime import datetime, timezone
from src.utils.logging import logger
from src.utils.consts import DATE_FORMAT, ROBLOX_DATE_FORMATS


def current_date(output_format: str = DATE_FORMAT) -> str:
    return datetime.now().strftime(output_format)


def current_date_timestamp() -> int:
    return int((datetime.now() - datetime(1970, 1, 1)).total_seconds() * 1000)


def convert_date(input_date: str, output_format: str = DATE_FORMAT) -> Optional[str]:
    for date_format in ROBLOX_DATE_FORMATS:
        try:
            return datetime.strptime(input_date, date_format).strftime(output_format)
        except ValueError:
            ...
    logger.warning(f'Can\'t convert date: {input_date}')


def timestamp_to_local_date(timestamp: int, output_format: str = DATE_FORMAT) -> str:
    return datetime.fromtimestamp(timestamp).strftime(output_format)


def timestamp_to_utc_date(timestamp: int, output_format: str = DATE_FORMAT) -> str:
    return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).strftime(output_format)
