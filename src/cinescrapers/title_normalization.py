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
    r"^Cinematix Escapes Presents: (.*)$",
    r"^Classic Matinee: (.*)$",
    r"^(.*) *\+ intro by .*$",
    r"^(.*) *\+ introduction by .*$",
    r"^(.*) *plus intro by .*$",
    r"^(.*) *with intro by .*$",
    r"^(.*) *\+ pre-recorded intro by .*$",
    r"^(.*) *\+ Panel discussion\b.*$",
    r"^(.*) *plus Panel discussion\b.*$",
    r"^(.*) *\+ Q&A\b.*$",
    r"^(.*) *plus Q&A\b.*$",
    r"^(.*) *\+ recorded Q&A\b.*$",
    r"^(.*) *plus recorded Q&A\b.*$",
    r"^(.*) *\+ director Q&A\b.*$",
    r"^(.*) *plus director Q&A\b.*$",
    r"^(.*) \(\d\dth anniversary\)$",
    r"^(.*) *- *\d\dth anniversary$",
    r"^(.*) *\(Subtitled\) *$",
    r"^Family Films: (.*)$",
    r"^Funeral Parade Presents '(.*)'$",
    r"^(.*) *Classics Presented in 35mm$",
    r"^Member exclusive: (.*)$",
    r"^Member Picks: (.*)$",
    r"^Members' Screening: (.*)$",
    r"^Outdoor Cinema: (.*)$",
    r"^Phoenix Classics: *(.*)$",
    r"^(.*)$",
]

AMP_REGEX = re.compile(r" & ")
PUNC_REGEX = re.compile(r"[:-]")


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

    for regex in TITLE_REGEXES:
        match = re.match(regex, title, re.I)
        if match:
            title = match.group(1)
            title = PUNC_REGEX.sub(" ", title)
            title = AMP_REGEX.sub(" AND ", title)
            title = re.sub(r"\s+", " ", title)
            title = title.strip()
            assert title
            return title
    raise RuntimeError(
        "We shouldn't ever get here as the last regex should match anything."
    )
