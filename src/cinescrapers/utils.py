import base64
import datetime
import hashlib
import re

import dateparser

# Regular expression matching 1900-1999 or 2000-2029
RELEASE_YEAR_RE = re.compile(r"\b((19\d{2})|(20[0-2]\d))\b")


class DateParsingError(Exception):
    pass


def parse_date_without_year(date_str: str) -> datetime.datetime:
    """If eg. date_str eg. "February 12th" and it's now October, assume the
    date is next year"""
    now = datetime.datetime.now()
    date = dateparser.parse(date_str)
    if date is None:
        raise DateParsingError()
    if now.month > 6 and date.month < 3:
        date = date.replace(year=1 + now.year)
    return date


def extract_uk_postcode(text: str) -> str | None:
    """Extract UK postcode from text using regex."""
    # UK postcode regex pattern - matches formats like SW1A 1AA, M1 1AA, B33 8TH, etc.
    # Pattern explanation:
    # - [A-Z]{1,2}: 1-2 letters for area code
    # - [0-9R][0-9A-Z]?: 1-2 characters for district code
    # - \s?: optional space
    # - [0-9]: single digit
    # - [A-Z]{2}: exactly 2 letters
    uk_postcode_pattern = r"\b[A-Z]{1,2}[0-9R][0-9A-Z]?\s?[0-9][A-Z]{2}\b"

    match = re.search(uk_postcode_pattern, text.upper())
    if match:
        postcode = match.group(0)
        # Ensure proper spacing (add space if missing)
        if " " not in postcode:
            # Insert space before the last 3 characters
            postcode = postcode[:-3] + " " + postcode[-3:]
        return postcode
    raise RuntimeError("No valid UK postcode found in the text")


def get_hashed(s: str) -> str:
    digest = hashlib.sha256(s.encode("utf-8")).digest()
    b64 = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return b64[:32]  # Truncate to sensible length
