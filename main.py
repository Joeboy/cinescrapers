import sqlite3
import sys
import time
from pathlib import Path
import importlib
from typing import Callable
from datetime import datetime

sys.path.append(str(Path(__file__).parent / "src"))


def get_scrapers() -> list[str]:
    """Get a list of available scraper names."""
    scrapers_dir = Path(__file__).parent / "src" / "cinescrapers" / "scrapers"
    possible_scrapers = [
        folder.name
        for folder in scrapers_dir.iterdir()
        if folder.is_dir() and (folder / "scrape.py").is_file()
    ]
    scrapers = []
    for possible_scraper in possible_scrapers:
        module_path = f"cinescrapers.scrapers.{possible_scraper}.scrape"
        try:
            importlib.import_module(module_path)
        except ImportError as e:
            print(f"Failed to import {possible_scraper}: {e}")
        else:
            scrapers.append(possible_scraper)
    return scrapers


def get_scraper(scraper_name: str) -> Callable:
    """Get the callable for a given scraper name."""
    module_path = f"cinescrapers.scrapers.{scraper_name}.scrape"
    try:
        scrape = importlib.import_module(module_path).scrape
    except ImportError:
        print(f"Error importing scraper '{scraper_name}'")
        raise
    return scrape


def serialize_record(record: dict) -> dict:
    """Convert datetimes to strings (otherwise sqlite complains)"""
    return {
        key: value.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(value, datetime)
        else value
        for key, value in record.items()
    }


def scrape_to_sqlite(scraper: Callable) -> None:
    t = time.perf_counter()
    showtimes = scraper()
    elapsed = time.perf_counter() - t
    print(f"Scraped {len(showtimes)} showtimes in {elapsed:.2f} seconds.")

    conn = sqlite3.connect("showtimes.db")
    cursor = conn.cursor()
    # TODO: Probably ought to figure out some migration system
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS showtimes (
            cinema TEXT,
            title TEXT,
            link TEXT,
            datetime TEXT,
            description TEXT,
            image_src TEXT,
            UNIQUE(cinema, title, datetime) ON CONFLICT REPLACE
        )
    """)
    query = """
        INSERT INTO showtimes (cinema, title, link, datetime, description, image_src)
        VALUES (:cinema, :title, :link, :datetime, :description, :image_src)
    """

    showtimes = [serialize_record(showtime) for showtime in showtimes]
    cursor.executemany(query, showtimes)
    conn.commit()
    conn.close()


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python main.py <scraper_name>\n")
        scrapers = get_scrapers()
        print("Available scrapers:\n")
        for scraper in scrapers:
            print(f" - {scraper}")
        print("\n")
        sys.exit(1)

    scraper_name = sys.argv[1]
    scraper = get_scraper(scraper_name)
    scrape_to_sqlite(scraper)


if __name__ == "__main__":
    main()
