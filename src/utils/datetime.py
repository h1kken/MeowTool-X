import collections.abc as cabc

from datetime import date, datetime, time, timezone

from src.services.roblox.constants import ROBLOX_DATE_FORMATS
from src.utils.logging import logger


class DateTime:
    _DATE_FORMAT_DEFAULT = '%d.%m.%Y'
    _DATETIME_FORMAT_DEFAULT = '%d.%m.%Y %H:%M:%S'
    _DATETIME_EPOCH_THRESHOLD_MS = 1_000_000_000_000
    _DATETIME_TIME_ANCHOR_DATE = date(1900, 1, 1)

    @staticmethod
    def current_datetime(utc: bool = False) -> datetime:
        return datetime.now(timezone.utc if utc else None)

    @staticmethod
    def utc_to_local_datetime(value: datetime) -> datetime:
        return value.astimezone()

    @staticmethod
    def timestamp_to_datetime(timestamp: int, utc: bool = False) -> datetime:
        return datetime.fromtimestamp(timestamp, timezone.utc if utc else None)

    # formaters
    @staticmethod
    def format_duration(ms: int, *, out_units: str | cabc.Collection[str] = 'all') -> dict[str, int]:
        s, ms = divmod(ms, 1000)
        m, s  = divmod(s,  60)
        h, m  = divmod(m,  60)
        d, h  = divmod(h,  24)

        units = {'d': d, 'h': h, 'm': m, 's': s, 'ms': ms}

        parts: dict[str, int] = {}
        for key in units.keys():
            if key in out_units or (isinstance(out_units, str) and 'all' == out_units.lower()):
                parts[key] = units[key]

        return parts

    # parsers
    @staticmethod
    def parse_datetime(value: object) -> datetime | None:
        if isinstance(value, datetime):
            return value

        if isinstance(value, date):
            return datetime.combine(value, time.min)

        if isinstance(value, time):
            return datetime.combine(DateTime._DATETIME_TIME_ANCHOR_DATE, value)

        if isinstance(value, (int, float)):
            timestamp = float(value)
            if abs(timestamp) >= DateTime._DATETIME_EPOCH_THRESHOLD_MS:
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
            if abs(numeric) >= DateTime._DATETIME_EPOCH_THRESHOLD_MS:
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

    # converters
    @staticmethod
    def convert_datetime(value: object, output_format: str = _DATETIME_FORMAT_DEFAULT) -> str | None:
        parsed = DateTime.parse_datetime(value)
        if parsed is not None:
            return parsed.strftime(output_format)

        logger.warning(f'Failed convert date: {value}')
