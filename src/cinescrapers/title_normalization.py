"""Code to attempt to get normalized movie titles for title matching, sorting etc"""

import re


TITLE_REGEXES = [
    r"^Bar Trash: (.*)$",
    r"^CAMP CLASSICS presents: (.*)$",
    r"^Carers & Babies: (.*)$",
    r"^Parent & Baby: (.*)$",
    r"^Parent & Baby Screening: (.*)$",
    r"^Relaxed Screening: (.*)$",
    r"^Senior Community Screening: (.*)$",
    r"^Seniors' Free Matinee: (.*)$",
    r"^Seniors' Paid Matinee: (.*)$",
    r"^Cine-real presents: (.*)$",
    r"^Classic Matinee: (.*)$",
    r"^(.*) \(\d\dth anniversary\)$",
    r"^Family Films: (.*)$",
    r"^Funeral Parade Presents '(.*)'$",
    r"^(.*) *Classics Presented in 35mm$",
    r"^Member exclusive: (.*)$",
    r"^Member Picks: (.*)$",
    r"^Members' Screening: (.*)$",
    r"^(.*)$",
]


def normalize_quotes(text: str) -> str:
    """Convert curly/special apostrophes and quotes to straight ones."""
    replacements = {
        ord("‘"): "'",
        ord("’"): "'",
        ord("‚"): "'",
        ord("‛"): "'",
        ord("“"): '"',
        ord("”"): '"',
        ord("„"): '"',
        ord("‟"): '"',
        ord("‹"): "'",
        ord("›"): "'",
        ord("«"): '"',
        ord("»"): '"',
    }
    return text.translate(replacements)


def normalize_title(title: str) -> str:
    title = title.strip().upper()
    title = normalize_quotes(title)
    title = re.sub(r"\s+", " ", title)

    for regex in TITLE_REGEXES:
        match = re.match(regex, title, re.I)
        if match:
            return match.group(1).strip()
    raise RuntimeError(
        "We shouldn't ever get here as the last regex should match anything."
    )
