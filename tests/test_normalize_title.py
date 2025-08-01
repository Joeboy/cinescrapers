from cinescrapers.title_normalization import (
    normalize_title,
    normalize_accents,
    normalize_dashes,
)


def test_normalize_title():
    assert normalize_title("Bar Trash: Summer Nights") == "SUMMER NIGHTS"
    assert (
        normalize_title("CAMP CLASSICS presents: The Great Outdoors")
        == "THE GREAT OUTDOORS"
    )
    assert normalize_title("Parent & Baby: A Quiet Place") == "A QUIET PLACE"
    assert normalize_title("Senior Community Screening: The Notebook") == "THE NOTEBOOK"
    assert (
        normalize_title("Funeral Parade Presents 'The Last Picture Show'")
        == "THE LAST PICTURE SHOW"
    )
    assert normalize_title("Classic Matinee: Casablanca") == "CASABLANCA"
    assert normalize_title("Lilo & Stitch") == normalize_title("LILO AND STITCH")
    assert normalize_title("Barry Lyndon (50th Anniversary)") == "BARRY LYNDON"
    assert normalize_title("Barry Lyndon - 50th Anniversary") == "BARRY LYNDON"
    assert normalize_title("Members' Screening: Barry Lyndon - 50th Anniversary") == "BARRY LYNDON"


def test_normalize_accents():
    """Test that accented characters are converted to ASCII equivalents."""
    # Test common accented vowels
    assert normalize_accents("Amélie") == "Amelie"
    assert normalize_accents("Café") == "Cafe"
    assert normalize_accents("Naïve") == "Naive"
    assert normalize_accents("Résumé") == "Resume"
    assert normalize_accents("Crème brûlée") == "Creme brulee"

    # Test various accented characters (note: æ becomes 'ae', not just 'e')
    assert (
        normalize_accents("àáâãäåæçèéêëìíîïñòóôõöùúûüý")
        == "aaaaaaaeceeeeiiiinooooouuuuy"
    )

    # Test uppercase accented characters (note: Æ becomes 'AE')
    assert (
        normalize_accents("ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÑÒÓÔÕÖÙÚÛÜÝ")
        == "AAAAAAAECEEEEIIIINOOOOOUUUUY"
    )

    # Test mixed case
    assert normalize_accents("Señorita") == "Senorita"
    assert normalize_accents("Björk") == "Bjork"

    # Test ligatures
    assert normalize_accents("æon") == "aeon"
    assert normalize_accents("Æon") == "AEon"
    assert normalize_accents("œuvre") == "oeuvre"
    assert normalize_accents("Œuvre") == "OEuvre"
    assert normalize_accents("Straße") == "Strasse"

    # Test characters that shouldn't change
    assert normalize_accents("Hello World") == "Hello World"
    assert normalize_accents("123ABC") == "123ABC"


def test_normalize_dashes():
    """Test that various dash types are converted to regular hyphens."""
    # Test different dash types
    assert normalize_dashes("Spider–Man") == "Spider-Man"  # en-dash
    assert normalize_dashes("Spider—Man") == "Spider-Man"  # em-dash
    assert normalize_dashes("Spider―Man") == "Spider-Man"  # horizontal bar
    assert normalize_dashes("Spider‒Man") == "Spider-Man"  # figure dash
    assert normalize_dashes("Spider−Man") == "Spider-Man"  # minus sign

    # Test multiple dashes in one string
    assert (
        normalize_dashes("X–Men: Days of Future—Past") == "X-Men: Days of Future-Past"
    )

    # Test mixed dashes
    assert (
        normalize_dashes("Neo–Tokyo—2019―Future‒City−Life")
        == "Neo-Tokyo-2019-Future-City-Life"
    )

    # Test regular hyphens (should remain unchanged)
    assert normalize_dashes("Spider-Man") == "Spider-Man"
    assert normalize_dashes("Well-known") == "Well-known"

    # Test strings without dashes
    assert normalize_dashes("Hello World") == "Hello World"
    assert normalize_dashes("NoChange123") == "NoChange123"
