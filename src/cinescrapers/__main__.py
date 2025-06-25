import argparse
import base64
import datetime
import gzip
import hashlib
import importlib
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Callable

import humanize
from rich import print

from cinescrapers.cinema_details import CINEMAS
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


def print_stats() -> None:
    """Print some stats about the database."""
    conn = sqlite3.connect("showtimes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM showtimes")
    count = cursor.fetchone()[0]
    cursor.execute("SELECT DISTINCT cinema_shortname FROM showtimes")
    cinema_shortnames = [c for (c,) in cursor.fetchall()]

    print(f"Total showtimes: {count}")
    print(f"Distinct cinemas: {len(cinema_shortnames)}")
    print()

    for scraper in get_scrapers():
        cursor.execute(
            "SELECT COUNT(*), MAX(last_updated) FROM showtimes WHERE scraper = ?",
            (scraper,),
        )
        scraper_count, latest_update = cursor.fetchone()
        if latest_update:
            latest_update = datetime.datetime.fromisoformat(latest_update)
        print(scraper)
        print("-" * len(scraper))

        print(f"Showtimes: {scraper_count}")
        if latest_update is None:
            print("No updates found")
        else:
            elapsed = datetime.datetime.now() - latest_update
            print(f"Last updated: {humanize.naturaltime(elapsed)} ago")
        print()

    conn.close()


def get_unique_identifier(st: ShowTime) -> str:
    """Build a unique identifier for a showtime"""
    s = f"{st.cinema_shortname}-{st.title}-{st.datetime}"
    digest = hashlib.sha256(s.encode("utf-8")).digest()
    b64 = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return b64[:32]  # Truncate to sensible length


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
            id TEXT PRIMARY KEY,
            cinema_shortname TEXT NOT NULL,
            cinema_name TEXT NOT NULL,
            title TEXT NOT NULL,
            datetime TEXT NOT NULL,
            link TEXT NOT NULL,
            description TEXT,
            image_src TEXT,
            last_updated TEXT NOT NULL,
            scraper TEXT NOT NULL
        )
    """)
    query = """
        INSERT INTO showtimes (id, cinema_shortname, cinema_name, title, link, datetime, description, image_src, last_updated, scraper)
        VALUES (:id, :cinema_shortname, :cinema_name, :title, :link, :datetime, :description, :image_src, :last_updated, :scraper)
        ON CONFLICT(id) DO UPDATE SET
            cinema_name = excluded.cinema_name,
            link = excluded.link,
            description = excluded.description,
            image_src = excluded.image_src,
            last_updated = excluded.last_updated,
            scraper = excluded.scraper

    """

    now = datetime.datetime.now()
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
    now_str = datetime.datetime.now().isoformat(timespec="seconds")
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

    dest_file = Path(__file__).parent / "cinescrapers.json"

    # In order for the gzip file to work on Chromium I had to set up
    # a cloudflare rule to write the content-encoding: gzip header.
    # Without that, for some reason cloudflare sets it as "gzip,aws-chunked",
    # which doesn't work on Chromium
    with gzip.open(dest_file, "wt", encoding="utf-8") as f:
        json.dump(data, f)

    # with open(dest_file, "w") as f:
    #     json.dump(data, f)

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
    parser.add_argument(
        "--stats", action="store_true", help="See some stats about the db"
    )
    parser.add_argument("scraper", nargs="?", help="Run scraper")

    args = parser.parse_args()
    chosen = sum(
        bool(x) for x in [args.dump_json, args.list_scrapers, args.stats, args.scraper]
    )
    if chosen > 1:
        parser.error(
            "Arguments --dump-json, --list-scrapers, --stats and scraper are mutually exclusive."
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
    elif args.stats:
        print_stats()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
