from datetime import date, datetime, time, timezone

from src.utils.constants import (
    DATE_FORMAT,
    DATE_TIME_FORMAT,
    DATETIME_EPOCH_THRESHOLD_MS,
    DATETIME_TIME_ANCHOR_DATE,
    ROBLOX_DATE_FORMATS,
)
from src.utils.logging import logger


def current_date(output_format: str = DATE_FORMAT) -> str:
    return datetime.now().strftime(output_format)


def current_date_ms() -> int:
    return int((datetime.now() - datetime(1970, 1, 1)).total_seconds() * 1000)


def parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return datetime.combine(value, time.min)

    if isinstance(value, time):
        return datetime.combine(DATETIME_TIME_ANCHOR_DATE, value)

    if isinstance(value, (int, float)):
        timestamp = float(value)
        if abs(timestamp) >= DATETIME_EPOCH_THRESHOLD_MS:
            timestamp /= 1000.0
        try:
            return datetime.fromtimestamp(timestamp)
        except (OverflowError, OSError, ValueError):
            return None

    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    try:
        numeric = float(text)
        if abs(numeric) >= DATETIME_EPOCH_THRESHOLD_MS:
            numeric /= 1000.0
        return datetime.fromtimestamp(numeric)
    except ValueError:
        pass
    except (OverflowError, OSError):
        return None

    iso_candidate = text.replace('Z', '+00:00') if text.endswith('Z') else text
    try:
        return datetime.fromisoformat(iso_candidate)
    except ValueError:
        pass

    for date_format in ROBLOX_DATE_FORMATS:
        try:
            return datetime.strptime(text, date_format)
        except ValueError:
            pass

    return None


def convert_datetime(value: object, output_format: str = DATE_TIME_FORMAT) -> str | None:
    parsed = parse_datetime(value)
    if parsed is not None:
        return parsed.strftime(output_format)

    logger.warning(f'Can\'t convert datetime: {value}')


def timestamp_to_local_date(timestamp: int, output_format: str = DATE_FORMAT) -> str:
    return datetime.fromtimestamp(timestamp).strftime(output_format)


def timestamp_to_utc_date(timestamp: int, output_format: str = DATE_FORMAT) -> str:
    return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).strftime(output_format)

