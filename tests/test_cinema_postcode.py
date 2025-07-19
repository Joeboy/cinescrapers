import json
from cinescrapers.cinema_details import CINEMAS


def test_cinema_postcode_extraction():
    """Test that Cinema automatically extracts postcode from address using real data."""

    # Test a few specific cinemas from the real data
    ica = next(cinema for cinema in CINEMAS if cinema.shortcode == "IC")
    assert ica.postcode == "SW1Y 5AH"
    assert ica.address == "The Mall, London SW1Y 5AH"

    prince_charles = next(cinema for cinema in CINEMAS if cinema.shortcode == "PC")
    assert prince_charles.postcode == "WC2H 7BY"
    assert prince_charles.address == "7 Leicester Place, London WC2H 7BY"

    # Test that all cinemas with addresses have postcodes extracted
    for cinema in CINEMAS:
        if cinema.address:
            # All cinemas with addresses should have postcodes extracted
            assert cinema.postcode is not None, (
                f"Cinema {cinema.shortname} should have postcode extracted from address: {cinema.address}"
            )
            # Postcode should be a string with the right format
            assert isinstance(cinema.postcode, str)
            assert len(cinema.postcode) >= 5  # Minimum UK postcode length
        else:
            # Cinemas without addresses should have None postcode
            assert cinema.postcode is None


def test_cinema_serialization_includes_postcode():
    """Test that postcode is included when serializing Cinema to JSON using real data."""

    # Use the first cinema from real data
    cinema = CINEMAS[0]

    # Test model_dump (Pydantic v2 method)
    cinema_dict = cinema.model_dump()
    assert "postcode" in cinema_dict
    if cinema.address:
        assert cinema_dict["postcode"] is not None

    # Test JSON serialization
    cinema_json = cinema.model_dump_json()
    parsed_data = json.loads(cinema_json)
    assert parsed_data["postcode"]


def test_all_cinemas_postcode_extraction():
    """Test postcode extraction for all cinemas in the dataset."""

    postcodes_found = 0
    postcodes_missing = 0

    for cinema in CINEMAS:
        if cinema.address:
            if cinema.postcode:
                postcodes_found += 1
                print(
                    f"✓ {cinema.shortname}: {cinema.postcode} (from: {cinema.address})"
                )
            else:
                postcodes_missing += 1
                print(
                    f"✗ {cinema.shortname}: No postcode found in address: {cinema.address}"
                )
        else:
            print(f"- {cinema.shortname}: No address provided")

    print(f"\nSummary: {postcodes_found} postcodes found, {postcodes_missing} missing")

    # Most cinemas should have postcodes if they have addresses
    # This is a sanity check - if this fails, it might indicate issues with the regex
    if postcodes_found + postcodes_missing > 0:
        success_rate = postcodes_found / (postcodes_found + postcodes_missing)
        assert success_rate >= 0.8, (
            f"Only {success_rate:.1%} of cinemas with addresses had postcodes extracted"
        )
