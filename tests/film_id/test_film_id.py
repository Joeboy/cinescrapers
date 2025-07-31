import sqlite3
from pathlib import Path
import time

import pytest
from rich import print

from cinescrapers.film_identification import get_best_tmdb_match

TESTDATA_ROOT = Path(__file__).parent / "test_data"
DB_PATH = TESTDATA_ROOT / "showtimes.db"
IMAGES_CACHE = TESTDATA_ROOT / "source_images"


@pytest.fixture
def showtimes_data():
    """Fixture to provide a connection to the test database."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT distinct title, norm_title, description, thumbnail FROM showtimes LIMIT 100"
        )
        yield [dict(row) for row in cursor.fetchall()]


def test_film_id(showtimes_data):
    """None of this is actually used and this isn't really a test"""

    num_matches = 0
    for showtime_result in showtimes_data:
        print("-" * 80)
        print(showtime_result)
        match = get_best_tmdb_match(showtime_result, IMAGES_CACHE)
        if match:
            num_matches += 1
            print("MATCH:")
            print(match)
        else:
            print("NO MATCH")
        time.sleep(0.1)

    print(f"Total matches found: {num_matches} out of {len(showtimes_data)}")
