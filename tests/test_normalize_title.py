from cinescrapers.title_normalization import normalize_title


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
