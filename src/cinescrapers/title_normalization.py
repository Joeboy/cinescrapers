"""Code to attempt to get normalized movie titles for title matching, sorting etc"""

import re
import unicodedata


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
    r"^(.*) *- *The Chiswick Cinema$",
    r"^Member exclusive: (.*)$",
    r"^Member Picks: (.*)$",
    r"^Members' Screening: (.*)$",
    r"^Outdoor Cinema: (.*)$",
    r"^Phoenix Classics: *(.*)$",
    r"^(.*)$",
]

AMP_REGEX = re.compile(r" & ")
PUNC_REGEX = re.compile(r"[\.\!,:-]")


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


def normalize_dashes(text: str) -> str:
    """Convert various types of dashes to regular hyphens."""
    replacements = {
        ord("–"): "-",  # en-dash
        ord("—"): "-",  # em-dash
        ord("―"): "-",  # horizontal bar
        ord("‒"): "-",  # figure dash
        ord("−"): "-",  # minus sign
    }
    return text.translate(replacements)


def normalize_accents(text: str) -> str:
    """Convert accented characters to their ASCII equivalents."""
    # First handle common ligatures that NFD doesn't decompose
    ligature_replacements = {
        "æ": "ae",
        "Æ": "AE",
        "œ": "oe",
        "Œ": "OE",
        "ß": "ss",
        "ẞ": "SS",
    }

    for ligature, replacement in ligature_replacements.items():
        text = text.replace(ligature, replacement)

    # Normalize to NFD (decomposed form) to separate base characters from combining marks
    nfd = unicodedata.normalize("NFD", text)
    # Filter out combining characters (accents, diacritics)
    ascii_text = "".join(char for char in nfd if unicodedata.category(char) != "Mn")
    return ascii_text


def normalize_title(title: str) -> str:
    title = title.strip().upper()
    title = normalize_quotes(title)
    title = normalize_dashes(title)
    title = normalize_accents(title)

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
