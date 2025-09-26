from datetime import datetime

def current_date(*, output_format: str) -> str:
    return datetime.now().strftime(output_format)

def current_time_in_ms() -> int:
    return int((datetime.now() - datetime(1970, 1, 1)).total_seconds() * 1000)

DATE_FORMATS = [
    '%Y-%m-%dT%H:%M:%S.%fZ',
    '%Y-%m-%dT%H:%M:%SZ'
]

def convert_date(input_date: str, output_format: str) -> str:
    for date_format in DATE_FORMATS:
        try:
            date_formatted = datetime.strptime(input_date, date_format)
            return date_formatted.strftime(output_format)
        except ValueError:
            ...