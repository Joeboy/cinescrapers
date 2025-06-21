import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path
import importlib
from typing import Callable
from datetime import datetime
from cinescrapers.types import EnrichedShowTime, ShowTime


def get_scrapers() -> list[str]:
    """Get a list of available scraper names."""
    scrapers_dir = Path(__file__).parent / "scrapers"
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


def get_unique_identifier(st: ShowTime) -> str:
    s = f"{st.cinema}-{st.title}-{st.datetime}"
    return s


def scrape_to_sqlite(scraper_name: str) -> None:
    """Run a scraper and insert the results into an sqlite db"""
    t = time.perf_counter()
    scraper = get_scraper(scraper_name)
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
            last_updated TEXT,
            scraper TEXT,
            UNIQUE(cinema, title, datetime) ON CONFLICT REPLACE
        )
    """)
    query = """
        INSERT INTO showtimes (cinema, title, link, datetime, description, image_src, last_updated, scraper)
        VALUES (:cinema, :title, :link, :datetime, :description, :image_src, :last_updated, :scraper)
    """

    now = datetime.now()
    enriched_showtimes = [
        EnrichedShowTime(
            **s.model_dump(),
            last_updated=now,
            scraper=scraper_name,
            id=get_unique_identifier(s),
        )
        for s in showtimes
    ]

    rows = [s.model_dump(mode="json") for s in enriched_showtimes]
    cursor.executemany(query, rows)
    conn.commit()
    conn.close()


def dump_to_json() -> None:
    """Dump the contents of the db to a json file"""
    now_str = datetime.now().isoformat(timespec="seconds")
    conn = sqlite3.connect("showtimes.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM showtimes
        WHERE datetime >= ?
        ORDER BY datetime
    """,
        (now_str,),
    )
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()

    data = [dict(zip(columns, row)) for row in rows]

    dest_file = Path(__file__).parent / "showtimes.json"
    with open(dest_file, "w") as f:
        json.dump(data, f)
    conn.commit()
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="CineScrapers CLI")
    parser.add_argument(
        "--dump-json", action="store_true", help="Dump database to JSON"
    )
    parser.add_argument(
        "--list-scrapers", action="store_true", help="List available scrapers"
    )
    parser.add_argument("scraper", nargs="?", help="Run scraper")

    args = parser.parse_args()
    chosen = sum(bool(x) for x in [args.dump_json, args.list_scrapers, args.scraper])
    if chosen > 1:
        parser.error(
            "Arguments --dump-json, --list-scrapers, and scraper are mutually exclusive."
        )

    if args.scraper:
        scrape_to_sqlite(args.scraper)
    elif args.dump_json:
        dump_to_json()
    elif args.list_scrapers:
        scrapers = get_scrapers()
        print("Available scrapers:\n")
        for scraper in scrapers:
            print(f" - {scraper}")
        print("\n")
        sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
