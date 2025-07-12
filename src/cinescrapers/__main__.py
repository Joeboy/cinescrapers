import base64
import concurrent.futures
import datetime
import hashlib
import importlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Callable

import click
import humanize
import requests
from rich import print

from cinescrapers.cinema_details import CINEMAS
from cinescrapers.types import EnrichedShowTime, ShowTime
from cinescrapers.upload import get_s3_client, upload_file
from cinescrapers.utils import smart_square_thumbnail

IMAGES_CACHE = Path(__file__).parent / "scraped_images" / "source_images"
IMAGES_CACHE.mkdir(parents=True, exist_ok=True)
THUMBNAILS_FOLDER = Path(__file__).parent / "scraped_images" / "thumbnails"
THUMBNAILS_FOLDER.mkdir(parents=True, exist_ok=True)


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

    print("CINEMA DETAILS")
    print("-" * len("CINEMA DETAILS"))
    print()

    with_details = set(cinema_shortnames) & set(c.shortname for c in CINEMAS)
    missing_details = set(cinema_shortnames) - set(c.shortname for c in CINEMAS)

    print("Cinemas with details:")
    for shortname in sorted(with_details):
        print(f" - {shortname}")
    print()

    if missing_details:
        print("Cinemas with no details:")
        for shortname in missing_details:
            print(f" - {shortname}")
        print()
    else:
        print("No cinemas are missing details.")
    print()

    conn.close()


def get_hashed(s: str) -> str:
    digest = hashlib.sha256(s.encode("utf-8")).digest()
    b64 = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return b64[:32]  # Truncate to sensible length


def get_unique_identifier(st: ShowTime) -> str:
    """Build a unique identifier for a showtime"""
    return get_hashed(f"{st.cinema_shortname}-{st.title}-{st.datetime}")


def ensure_showtimes_table_exists():
    with sqlite3.connect("showtimes.db") as conn:
        cursor = conn.cursor()
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
                thumbnail TEXT,
                last_updated TEXT NOT NULL,
                scraper TEXT NOT NULL
            )
        """)


def get_thumbnail(showtime: ShowTime) -> str | None:
    """Grab a copy of the showtime's image and try to thumbnail it"""

    if showtime.image_src is None:
        return None
    if showtime.image_src.startswith("data:"):
        # Maybe we could do something with this, for now let's just skip it
        return None
    filename = get_hashed(showtime.image_src)
    filepath = IMAGES_CACHE / filename
    if not filepath.exists():
        response = requests.get(showtime.image_src)
        if not response.ok:
            print(
                f"Failed to fetch {showtime.image_src} for {showtime.title} ({showtime.cinema_shortname}) ({response.status_code})"
            )
            return None
        with filepath.open("wb") as f:
            f.write(response.content)
    thumbnail_filepath = THUMBNAILS_FOLDER / f"{filepath.stem}.jpg"
    if not thumbnail_filepath.exists():
        smart_square_thumbnail(filepath, thumbnail_filepath, 150)
    return thumbnail_filepath.name


def scrape_to_sqlite(scraper_name: str) -> None:
    """Run a scraper and insert the results into an sqlite db"""
    t = time.perf_counter()
    scraper = get_scraper(scraper_name)
    showtimes = scraper()
    elapsed = time.perf_counter() - t
    print(
        f"Scraped {len(showtimes)} showtimes in {elapsed:.2f} seconds ({scraper_name})."
    )

    now = datetime.datetime.now()
    enriched_showtimes = []
    for showtime in showtimes:
        thumbnail = get_thumbnail(showtime)
        if thumbnail is None:
            print(
                f"Failed to get thumbnail for {showtime.title} {showtime.image_src}, ({scraper_name})"
            )
        showtime.description = showtime.description[:210]
        enriched_showtimes.append(
            EnrichedShowTime(
                **showtime.model_dump(),
                last_updated=now,
                scraper=scraper_name,
                id=get_unique_identifier(showtime),
                thumbnail=thumbnail,
            )
        )

    rows = [s.model_dump(mode="json") for s in enriched_showtimes]

    ensure_showtimes_table_exists()
    with sqlite3.connect("showtimes.db") as conn:
        cursor = conn.cursor()
        query = """
            INSERT INTO showtimes (id, cinema_shortname, cinema_name, title, link, datetime, description, image_src, thumbnail, last_updated, scraper)
            VALUES (:id, :cinema_shortname, :cinema_name, :title, :link, :datetime, :description, :image_src, :thumbnail, :last_updated, :scraper)
            ON CONFLICT(id) DO UPDATE SET
                cinema_name = excluded.cinema_name,
                link = excluded.link,
                description = excluded.description,
                image_src = excluded.image_src,
                thumbnail = excluded.thumbnail,
                last_updated = excluded.last_updated,
                scraper = excluded.scraper

        """
        cursor.executemany(query, rows)


def grab_current_showtimes() -> list[dict[str, Any]]:
    this_morning = datetime.datetime.combine(
        datetime.datetime.now().date(), datetime.time.min
    )
    this_morning_str = this_morning.isoformat(timespec="seconds")
    three_months_time = this_morning + datetime.timedelta(days=90)
    three_months_time_str = three_months_time.isoformat(timespec="seconds")
    with sqlite3.connect("showtimes.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM showtimes
            WHERE datetime >= ?
            AND datetime <= ?
            ORDER BY datetime
        """,
            (this_morning_str, three_months_time_str),
        )
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        data = [dict(zip(columns, row)) for row in rows]

    return data


def export_json() -> None:
    """Dump the contents of the db to a json file"""

    current_showtimes = grab_current_showtimes()
    showtimes_file = Path(__file__).parent / "cinescrapers.json"
    with showtimes_file.open("w") as f:
        json.dump(current_showtimes, f)

    # Check cinema shortcodes are unique:
    assert len(set(c.shortcode for c in CINEMAS)) == len(CINEMAS)

    cinemas_data = [c.model_dump() for c in CINEMAS]
    cinemas_file = Path(__file__).parent / "cinemas.json"
    with cinemas_file.open("w") as f:
        json.dump(cinemas_data, f)


@click.group()
def cli():
    """CineScrapers CLI"""
    pass


@cli.command("export-json")
def export_json_cmd():
    """Dump database to JSON"""
    export_json()


@cli.command("list-scrapers")
def list_scrapers_cmd():
    """List available scrapers"""
    scrapers = get_scrapers()
    print("Available scrapers:\n")
    for scraper in scrapers:
        print(f" - {scraper}")
    print("\n")


@cli.command("stats")
def stats_cmd():
    """See some stats about the db"""
    print_stats()


@cli.command("refresh")
def refresh_cmd():
    """Refresh cinemas without recent updates"""
    max_staleness = datetime.timedelta(days=5)
    now = datetime.datetime.now()
    min_datetime = now - max_staleness
    ensure_showtimes_table_exists()
    conn = sqlite3.connect("showtimes.db")
    cursor = conn.cursor()
    scrapers_to_run = []
    for scraper in get_scrapers():
        if scraper == "rapidapi":
            # Bad / broken / unfinished scraper
            continue
        cursor.execute(
            "SELECT MAX(last_updated) FROM showtimes WHERE scraper = ?",
            (scraper,),
        )
        (latest_update_str,) = cursor.fetchone()
        if latest_update_str is None:
            scrapers_to_run.append(scraper)
        else:
            latest_update = datetime.datetime.fromisoformat(latest_update_str)
            if latest_update < min_datetime:
                scrapers_to_run.append(scraper)
    print(f"Running scrapers: {', '.join(scrapers_to_run)}")

    failed = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_scraper = {
            executor.submit(scrape_to_sqlite, scraper): scraper
            for scraper in scrapers_to_run
        }
        for future in concurrent.futures.as_completed(future_to_scraper):
            scraper = future_to_scraper[future]
            try:
                future.result()
            except Exception as e:
                print(f"[red]Error running scraper '{scraper}': {e}[/red]")
                import traceback

                traceback.print_exc()
                failed.append(scraper)
    print(f"Failed: {failed}")


@cli.command("upload")
def upload():
    # NOTE: These files are gzipped by default before uploading. To make that work,
    # on Chromium, I had to create a cloudflare rule to add the
    # "content-encoding: gzip" header.

    s3_client = get_s3_client()
    cinemas_json_path = Path(__file__).parent / "cinemas.json"
    cinescrapers_json_path = Path(__file__).parent / "cinescrapers.json"
    assert cinemas_json_path.exists()
    assert cinescrapers_json_path.exists()
    upload_file(
        s3_client,
        cinemas_json_path,
        cinemas_json_path.name,
    )
    upload_file(
        s3_client,
        cinescrapers_json_path,
        cinescrapers_json_path.name,
    )

    # One day, it might be better to only upload the thumbnails for
    # "current" showtimes, and to clear out old thumbnails. But this will
    # be OK for now I think.
    paginator = s3_client.get_paginator("list_objects_v2")
    existing_thumbnail_files = []
    for page in paginator.paginate(Bucket="cinescrapers", Prefix="thumbnails/"):
        for obj in page.get("Contents", []):
            existing_thumbnail_files.append(obj["Key"][len("thumbnails/") :])

    for path in THUMBNAILS_FOLDER.iterdir():
        if path.name in existing_thumbnail_files:
            print("skipping already-uploaded file")
        else:
            s3_key = f"thumbnails/{path.name}"
            upload_file(s3_client, path, s3_key)


@cli.command("scrape")
@click.argument("scraper")
def scrape_cmd(scraper):
    """Run scraper"""
    scrape_to_sqlite(scraper)


if __name__ == "__main__":
    cli()
