import datetime
import dateparser


class DateParsingError(Exception):
    pass


def parse_date_without_year(date_str: str) -> datetime.datetime | None:
    """If eg. date_str eg. "February 12th" and it's now October, assume the
    date is next year"""
    now = datetime.datetime.now()
    date = dateparser.parse(date_str)
    if date is None:
        raise DateParsingError()
    if now.month > 6 and date.month < 3:
        date = date.replace(year=1 + now.year)
    return date
