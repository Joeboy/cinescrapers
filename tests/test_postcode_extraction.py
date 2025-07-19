import pytest
from cinescrapers.utils import extract_uk_postcode


def test_extract_uk_postcode():
    """Test UK postcode extraction from various text formats."""

    # Valid postcodes with proper spacing
    assert extract_uk_postcode("Visit us at SW1A 1AA for tickets") == "SW1A 1AA"
    assert extract_uk_postcode("Located at M1 1AA in Manchester") == "M1 1AA"
    assert extract_uk_postcode("Address: B33 8TH Birmingham") == "B33 8TH"
    assert extract_uk_postcode("Come to E1 6AN London") == "E1 6AN"
    assert extract_uk_postcode("Our venue is at N1 9GU") == "N1 9GU"

    # Valid postcodes without spacing (should add space)
    assert extract_uk_postcode("Visit us at SW1A1AA for tickets") == "SW1A 1AA"
    assert extract_uk_postcode("Located at M11AA in Manchester") == "M1 1AA"
    assert extract_uk_postcode("Address: B338TH Birmingham") == "B33 8TH"
    assert extract_uk_postcode("Come to E16AN London") == "E1 6AN"
    assert extract_uk_postcode("Our venue is at N19GU") == "N1 9GU"

    # Special cases with R in district code
    assert extract_uk_postcode("Postcode: W1R 0AB") == "W1R 0AB"
    assert extract_uk_postcode("Located at W1R0AB") == "W1R 0AB"

    # Various London postcodes
    assert extract_uk_postcode("Central London WC2E 9RZ") == "WC2E 9RZ"
    assert extract_uk_postcode("East London E14 5AB") == "E14 5AB"
    assert extract_uk_postcode("South London SE1 9GF") == "SE1 9GF"
    assert extract_uk_postcode("West London W2 1HB") == "W2 1HB"
    assert extract_uk_postcode("North London NW1 5DA") == "NW1 5DA"

    # Mixed case input (should normalize to uppercase)
    assert extract_uk_postcode("visit us at sw1a 1aa") == "SW1A 1AA"
    assert extract_uk_postcode("Located at m1 1aa") == "M1 1AA"
    assert extract_uk_postcode("address: b338th birmingham") == "B33 8TH"

    # Postcodes in longer text
    assert (
        extract_uk_postcode(
            "The Electric Cinema is located at 191 Portobello Road, London W11 2ED. "
            "Join us for the latest films."
        )
        == "W11 2ED"
    )

    assert (
        extract_uk_postcode(
            "Phoenix Cinema, 52 High Road, East Finchley, London N2 9PJ. "
            "Independent cinema since 1910."
        )
        == "N2 9PJ"
    )

    # Postcodes with surrounding punctuation
    assert extract_uk_postcode("Address: (SW1A 1AA)") == "SW1A 1AA"
    assert extract_uk_postcode("Location: M1 1AA.") == "M1 1AA"
    assert extract_uk_postcode("Visit us at: B33 8TH!") == "B33 8TH"

    # Invalid postcodes should raise RuntimeError
    with pytest.raises(RuntimeError, match="No valid UK postcode found in the text"):
        extract_uk_postcode("No postcode here")
    with pytest.raises(RuntimeError, match="No valid UK postcode found in the text"):
        extract_uk_postcode("Invalid: 12345")
    with pytest.raises(RuntimeError, match="No valid UK postcode found in the text"):
        extract_uk_postcode("Wrong format: AA 123")
    with pytest.raises(RuntimeError, match="No valid UK postcode found in the text"):
        extract_uk_postcode("Too long: SW1A1 1AA")
    with pytest.raises(RuntimeError, match="No valid UK postcode found in the text"):
        extract_uk_postcode("Missing letters: SW1A 1A")
    with pytest.raises(RuntimeError, match="No valid UK postcode found in the text"):
        extract_uk_postcode("Missing numbers: SW1 A1A")

    # Empty or whitespace-only strings should raise RuntimeError
    with pytest.raises(RuntimeError, match="No valid UK postcode found in the text"):
        extract_uk_postcode("")
    with pytest.raises(RuntimeError, match="No valid UK postcode found in the text"):
        extract_uk_postcode("   ")
    with pytest.raises(RuntimeError, match="No valid UK postcode found in the text"):
        extract_uk_postcode("\n\t")

    # Edge cases with numbers that look like postcodes but aren't should raise RuntimeError
    with pytest.raises(RuntimeError, match="No valid UK postcode found in the text"):
        extract_uk_postcode("Phone: 020 1234 5678")
    with pytest.raises(RuntimeError, match="No valid UK postcode found in the text"):
        extract_uk_postcode("Price: £12 34p")

    # Multiple postcodes in text (should return first match)
    result = extract_uk_postcode("Visit SW1A 1AA or M1 1AA locations")
    assert result == "SW1A 1AA"

    # Real-world cinema descriptions
    assert (
        extract_uk_postcode("The Barbican Centre, Silk Street, London EC2Y 8DS")
        == "EC2Y 8DS"
    )

    assert (
        extract_uk_postcode("BFI Southbank, Belvedere Road, South Bank, London SE1 8XT")
        == "SE1 8XT"
    )

    assert (
        extract_uk_postcode("Prince Charles Cinema, 7 Leicester Place, London WC2H 7BY")
        == "WC2H 7BY"
    )


def test_extract_uk_postcode_comprehensive_formats():
    """Test various UK postcode formats comprehensively."""

    # Single letter area codes
    test_cases = [
        ("E1 6AN", "E1 6AN"),
        ("E16AN", "E1 6AN"),
        ("M1 1AA", "M1 1AA"),
        ("M11AA", "M1 1AA"),
        ("N1 9GU", "N1 9GU"),
        ("N19GU", "N1 9GU"),
    ]

    for input_text, expected in test_cases:
        assert extract_uk_postcode(f"Address: {input_text}") == expected

    # Double letter area codes
    test_cases = [
        ("SW1A 1AA", "SW1A 1AA"),
        ("SW1A1AA", "SW1A 1AA"),
        ("WC2E 9RZ", "WC2E 9RZ"),
        ("WC2E9RZ", "WC2E 9RZ"),
        ("EC2Y 8DS", "EC2Y 8DS"),
        ("EC2Y8DS", "EC2Y 8DS"),
    ]

    for input_text, expected in test_cases:
        assert extract_uk_postcode(f"Located at {input_text}") == expected

    # District codes with letters
    test_cases = [
        ("W1R 0AB", "W1R 0AB"),
        ("W1R0AB", "W1R 0AB"),
        ("SW1W 9SH", "SW1W 9SH"),
        ("SW1W9SH", "SW1W 9SH"),
    ]

    for input_text, expected in test_cases:
        assert extract_uk_postcode(f"Find us at {input_text}") == expected
