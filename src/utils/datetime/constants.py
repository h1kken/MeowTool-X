from datetime import date


DATE_FORMAT = '%d.%m.%Y'
DATE_TIME_FORMAT = '%d.%m.%Y %H:%M:%S'

DATETIME_EPOCH_THRESHOLD_MS = 1_000_000_000_000
DATETIME_TIME_ANCHOR_DATE = date(1900, 1, 1)


__all__ = [name for name in globals() if name.isupper()]
