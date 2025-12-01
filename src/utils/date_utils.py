from datetime import datetime
from src.utils.consts import DATE_ROBLOX_FORMATS


def current_date(output_format: str) -> str:
    return datetime.now().strftime(output_format)

def current_time_in_ms() -> int:
    return int((datetime.now() - datetime(1970, 1, 1)).total_seconds() * 1000)

def convert_date(input_date: str, output_format: str) -> str:
    for date_format in DATE_ROBLOX_FORMATS:
        try:
            return datetime.strptime(input_date, date_format).strftime(output_format)
        except ValueError:
            ...