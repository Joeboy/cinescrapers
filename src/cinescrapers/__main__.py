import concurrent.futures
import datetime
import importlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Callable

import click
import humanize
import requests
from rich import print

from cinescrapers.cinema_details import CINEMAS
from cinescrapers.cinemap import generate_cinema_map
from cinescrapers.cinescrapers_types import EnrichedShowTime, ShowTime
from cinescrapers.film_identification import get_best_tmdb_match
from cinescrapers.indexnow import submit_to_indexnow
from cinescrapers.thumbnailing import smart_square_thumbnail
from cinescrapers.title_normalization import normalize_title
from cinescrapers.upload import get_s3_client, upload_file
from cinescrapers.utils import get_hashed

IMAGES_CACHE = Path(__file__).parent / "scraped_images" / "source_images"
IMAGES_CACHE.mkdir(parents=True, exist_ok=True)
THUMBNAILS_FOLDER = Path(__file__).parent / "scraped_images" / "thumbnails"
THUMBNAILS_FOLDER.mkdir(parents=True, exist_ok=True)
TMDB_ID_CACHE = Path(__file__).parent / "tmdb_id_cache.json"
if not TMDB_ID_CACHE.exists():
    # Create the cache file if it doesn't exist
    TMDB_ID_CACHE.write_text("{}")

# How long since the last update before we need to refresh a cinema's listings
MAX_STALENESS = datetime.timedelta(days=5)


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
    now = datetime.datetime.now()
    if now.month == 12:
        one_months_time = now.replace(year=now.year + 1, month=1)
    else:
        one_months_time = now.replace(month=now.month + 1)
    one_month_num_days = (one_months_time - now).days

    with sqlite3.connect("showtimes.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM showtimes")
        showtimes_total_count = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM showtimes WHERE datetime <= ?", (one_months_time,)
        )
        showtimes_month_count = cursor.fetchone()[0]

        # Calculate average films per day by grouping by date
        cursor.execute(
            """
            SELECT DATE(datetime) as show_date, COUNT(DISTINCT norm_title) as daily_films
            FROM showtimes
            WHERE datetime <= ? AND datetime >= ?
            GROUP BY DATE(datetime)
        """,
            (one_months_time, now),
        )
        daily_film_counts = cursor.fetchall()

        if daily_film_counts:
            avg_films_per_day = sum(count for _, count in daily_film_counts) // len(
                daily_film_counts
            )
        else:
            avg_films_per_day = 0

        # Total film count for the next month:
        cursor.execute(
            """
            SELECT COUNT(DISTINCT norm_title) FROM showtimes
            WHERE datetime >= ? AND datetime < ?
        """,
            (now, one_months_time),
        )
        total_titles_next_month = cursor.fetchone()[0]

        cursor.execute("SELECT DISTINCT cinema_shortcode FROM showtimes")
        cinema_shortcodes = [c for (c,) in cursor.fetchall()]

        print(f"Total showtimes in db: {showtimes_total_count}")
        print(f"Showtimes for the next month: {showtimes_month_count}")
        print(
            f"Average number of showtimes per day for the next month: {showtimes_month_count // one_month_num_days}"
        )
        print(
            f"Average number of films showing per day for the next month: {avg_films_per_day}"
        )
        print(f"Distinct cinemas: {len(cinema_shortcodes)}")
        print()

        tweet_text = (
            f"Welcome to {datetime.datetime.now().strftime('%B!')}! "
            f"The filmhose.uk database has {showtimes_month_count} showtimes for this month,"
            f" averaging about {showtimes_month_count // one_month_num_days} showtimes per day. "
            f"That's {total_titles_next_month} titles, an average of "
            f"{avg_films_per_day} different films per day, across {len(cinema_shortcodes)} cinemas."
        )
        print(tweet_text)

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

        with_details = set(cinema_shortcodes) & set(c.shortcode for c in CINEMAS)
        missing_details = set(cinema_shortcodes) - set(c.shortcode for c in CINEMAS)

        print("Cinemas with details:")
        for shortcode in sorted(with_details):
            print(f" - {shortcode}")
        print()

        if missing_details:
            print("Cinemas with no details:")
            for shortcode in missing_details:
                print(f" - {shortcode}")
            print()
        else:
            print("No cinemas are missing details.")
        print()


def get_unique_identifier(st: ShowTime) -> str:
    """Build a unique identifier for a showtime"""
    return get_hashed(f"{st.cinema_shortcode}-{st.title}-{st.datetime}")


def ensure_showtimes_table_exists():
    with sqlite3.connect("showtimes.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS showtimes (
                id TEXT PRIMARY KEY,
                cinema_shortcode TEXT NOT NULL,
                title TEXT NOT NULL,
                norm_title TEXT,
                datetime TEXT NOT NULL,
                link TEXT NOT NULL,
                description TEXT,
                image_src TEXT,
                thumbnail TEXT,
                release_year INTEGER,
                last_updated TEXT NOT NULL,
                scraper TEXT NOT NULL,
                tmdb_id INTEGER
            )
        """
        )


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
        # Add headers to mimic a browser request
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            ),
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        # Add referer header if the image is from the same domain as the showtime link
        try:
            from urllib.parse import urlparse

            image_domain = urlparse(showtime.image_src).netloc
            link_domain = urlparse(showtime.link).netloc
            if image_domain == link_domain:
                headers["Referer"] = showtime.link
        except Exception:
            pass

        response = requests.get(showtime.image_src, headers=headers, timeout=10)
        if not response.ok:
            print(
                f"Failed to fetch '{showtime.image_src}' for {showtime.title} ({showtime.cinema_shortcode}) ({response.status_code})"
            )
            return None

        # Check if the response content is actually an image by examining the file signature
        content = response.content
        if len(content) < 8:
            print(
                f"Response too short to be an image for '{showtime.image_src}' for {showtime.title} ({showtime.cinema_shortcode})"
            )
            return None

        # Check common image file signatures (magic numbers)
        image_signatures = [
            b"\xff\xd8\xff",  # JPEG
            b"\x89PNG\r\n\x1a\n",  # PNG
            b"GIF87a",  # GIF87a
            b"GIF89a",  # GIF89a
            b"RIFF",  # WebP (starts with RIFF, followed by WEBP later)
            b"\x00\x00\x01\x00",  # ICO
            b"BM",  # BMP
        ]

        is_image = any(content.startswith(sig) for sig in image_signatures)
        # Special case for WebP which has RIFF header but needs to check for WEBP signature too
        if content.startswith(b"RIFF") and len(content) >= 12:
            is_image = content[8:12] == b"WEBP"

        if not is_image:
            content_type = response.headers.get("content-type", "unknown")
            print(
                f"Response is not an image (content-type: {content_type}, no image signature found) for '{showtime.image_src}' for {showtime.title} ({showtime.cinema_shortcode})"
            )
            return None

        with filepath.open("wb") as f:
            f.write(content)
    thumbnail_filepath = THUMBNAILS_FOLDER / f"{filepath.stem}.jpg"
    if not thumbnail_filepath.exists():
        smart_square_thumbnail(filepath, thumbnail_filepath, 150)
    return thumbnail_filepath.stem


def scrape_to_sqlite(scraper_name: str) -> None:
    """Run a scraper and insert the results into an sqlite db"""
    t = time.perf_counter()
    scraper = get_scraper(scraper_name)
    showtimes = scraper()
    elapsed = time.perf_counter() - t
    print(
        f"Scraped {len(showtimes)} showtimes in {humanize.naturaldelta(elapsed)} ({scraper_name})."
    )

    now = datetime.datetime.now()
    enriched_showtimes = []
    for showtime in showtimes:
        thumbnail = get_thumbnail(showtime)
        if thumbnail is None:
            print(
                f"Failed to get thumbnail for {showtime.title} {showtime.image_src}, ({scraper_name})"
            )
        if showtime.title == showtime.title.upper():
            # If title is all caps, that probably means the cinema capilized it, and
            # it's be better to have it in title case. Unfortunately still misses things
            # like "THE GODFATHER (40th ANNIVERSARY)"
            showtime.title = showtime.title.title()
        enriched_showtimes.append(
            EnrichedShowTime(
                **showtime.model_dump(),
                norm_title=normalize_title(showtime.title),
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
            INSERT INTO showtimes (id, cinema_shortcode, title, norm_title, link, datetime, description, image_src, thumbnail, release_year, last_updated, scraper)
            VALUES (:id, :cinema_shortcode, :title, :norm_title, :link, :datetime, :description, :image_src, :thumbnail, :release_year, :last_updated, :scraper)
            ON CONFLICT(id) DO UPDATE SET
                link = excluded.link,
                norm_title = excluded.norm_title,
                description = excluded.description,
                image_src = excluded.image_src,
                thumbnail = excluded.thumbnail,
                release_year = excluded.release_year,
                last_updated = excluded.last_updated,
                scraper = excluded.scraper

        """
        cursor.executemany(query, rows)


def grab_current_showtimes() -> list[EnrichedShowTime]:
    this_morning = datetime.datetime.combine(
        datetime.datetime.now().date(), datetime.time.min
    )
    this_morning_str = this_morning.isoformat(timespec="seconds")
    three_months_time = this_morning + datetime.timedelta(days=90)
    three_months_time_str = three_months_time.isoformat(timespec="seconds")
    with sqlite3.connect("showtimes.db") as conn:
        conn.row_factory = sqlite3.Row
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
        return [EnrichedShowTime(**row) for row in cursor.fetchall()]


def export_json() -> None:
    """Dump the contents of the db to a json file"""

    cinema_shortcodes = [c.shortcode for c in CINEMAS]
    # Check cinema shortcodes are unique:
    assert len(set(cinema_shortcodes)) == len(CINEMAS)

    cinemas_data = [c.model_dump() for c in CINEMAS]
    cinemas_file = Path(__file__).parent / "cinemas.json"
    with cinemas_file.open("w") as f:
        json.dump(cinemas_data, f)

    current_showtimes = grab_current_showtimes()
    # Check each showtime has a valid cinema shortcode:
    showtimes_json = []
    for showtime in current_showtimes:
        assert showtime.cinema_shortcode in cinema_shortcodes
        showtime.description = showtime.description[:210]
        showtimes_json.append(showtime.model_dump(mode="json"))

    showtimes_file = Path(__file__).parent / "cinescrapers.json"
    with showtimes_file.open("w") as f:
        json.dump(showtimes_json, f)


@click.group()
def cli():
    """CineScrapers CLI"""
    pass


@cli.command("export-json")
def export_json_cmd():
    """Dump database to JSON"""
    export_json()


@cli.command("grab_tmdb_ids")
def grab_tmdb_ids_cmd():
    """Grab TMDB IDs for all showtimes"""
    t1 = time.perf_counter()
    tmdb_id_cache = json.loads(TMDB_ID_CACHE.read_text())
    with sqlite3.connect("showtimes.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM showtimes")
        rows = cursor.fetchall()
        num_showtimes = len(rows)
        for i, row in enumerate(rows):
            print(f"{i} of {num_showtimes}, {row['title']}")
            showtime = EnrichedShowTime(**row)

            # I think we can assume that movie listings with the same
            # norm_title, description and image are pretty definitely for the
            # same movie
            movie_id_str = (
                f"{showtime.norm_title}-{showtime.description}-{showtime.image_src}"
            )
            movie_hash = get_hashed(movie_id_str)
            print(f"{showtime.norm_title} -> {movie_hash}")

            if showtime.tmdb_id:
                print("Skipping, db already has TMDB ID")
                # The tmdb_id for this db row is already in the db
                continue
            if movie_hash in tmdb_id_cache.keys():
                print(f"'{showtime.norm_title}' Found in file cache")
                showtime_tmdb_id = tmdb_id_cache[movie_hash]
            else:
                print(
                    f"'{showtime.norm_title}' Not found in file cache, searching TMDB"
                )
                best_match = get_best_tmdb_match(showtime, IMAGES_CACHE)
                if best_match:
                    showtime_tmdb_id = best_match["id"]
                else:
                    showtime_tmdb_id = None
            if showtime_tmdb_id:
                print(f"Found TMDB ID: {showtime_tmdb_id} for {showtime.norm_title}")
                cursor.execute(
                    "UPDATE showtimes SET tmdb_id = ? WHERE id = ?",
                    (showtime_tmdb_id, showtime.id),
                )
                tmdb_id_cache[movie_hash] = showtime_tmdb_id

            if not i % 100:
                cursor.connection.commit()
                print("writing file cache")
                TMDB_ID_CACHE.write_text(json.dumps(tmdb_id_cache, indent=2))

        TMDB_ID_CACHE.write_text(json.dumps(tmdb_id_cache, indent=2))
        cursor.connection.commit()
    print(
        f"Updated TMDB IDs for all showtimes in {humanize.naturaldelta(time.perf_counter() - t1)}."
    )


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


@cli.command("list-films")
def list_films_cmd():
    """List all films in the database"""
    with sqlite3.connect("showtimes.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM showtimes ORDER BY title")
        results = cursor.fetchall()
    titles = sorted(set(normalize_title(title) for (title,) in results))
    for title in titles:
        print(title)


@cli.command("refresh")
@click.option(
    "--scrape-all", "-a", is_flag=True, help="Run all scrapers, even if not stale"
)
def refresh_cmd(scrape_all: bool = False):
    """Refresh cinemas without recent updates"""
    t = time.perf_counter()
    now = datetime.datetime.now()
    min_datetime = now - MAX_STALENESS
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
            if latest_update < min_datetime or scrape_all:
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
    if failed:
        print(f"Failed: {failed}")
    else:
        print("No failures.")
    elapsed = time.perf_counter() - t
    print(f"Completed in {humanize.naturaldelta(elapsed)}.")


@cli.command("upload")
def upload():
    # NOTE: These files are gzipped by default before uploading. To make that work,
    # on Chromium, I had to create a cloudflare rule to add the
    # "content-encoding: gzip" header.

    s3_client = get_s3_client()
    cinemas_json_path = Path(__file__).parent / "cinemas.json"
    cinescrapers_json_path = Path(__file__).parent / "cinescrapers.json"
    sitemap_xml_path = Path(__file__).parent / "sitemap.xml"
    map_html_path = Path(__file__).parent / "cinema_map.html"
    generate_cinema_map()
    generate_sitemap()
    assert cinemas_json_path.exists()
    assert cinescrapers_json_path.exists()
    assert sitemap_xml_path.exists()
    assert map_html_path.exists()

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
    upload_file(
        s3_client,
        sitemap_xml_path,
        sitemap_xml_path.name,
    )
    upload_file(
        s3_client,
        map_html_path,
        map_html_path.name,
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


@cli.command("generate-map")
def generate_map_cmd():
    """Generate an interactive map of all cinemas"""
    generate_cinema_map()


def generate_sitemap():
    """Generate a sitemap.xml file"""
    output_path = Path(__file__).parent / "sitemap.xml"
    template_path = Path(__file__).parent / "sitemap.xml.template"
    template = template_path.read_text()

    cinema_page_sitemaps = "\n".join(
        f"""
    <url>
        <loc>https://filmhose.uk/cinemas/{cinema.shortname}</loc>
        <lastmod><!-- TODAY --></lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.6</priority>
    </url>

    <url>
        <loc>https://filmhose.uk/cinema-listings/{cinema.shortcode}</loc>
        <lastmod><!-- TODAY --></lastmod>
        <changefreq>daily</changefreq>
        <priority>0.6</priority>
    </url>
"""
        for cinema in CINEMAS
    )
    sitemap_content = template.replace("<!-- CINEMA PAGES -->", cinema_page_sitemaps)
    sitemap_content = template.replace(
        "<!-- CINEMA PAGES -->", cinema_page_sitemaps
    ).replace("<!-- TODAY -->", datetime.datetime.now().date().isoformat())
    output_path.write_text(sitemap_content)
    print(f"Sitemap generated at {output_path}")


@cli.command("generate-sitemap")
def generate_sitemap_cmd():
    generate_sitemap()


@cli.command("submit-indexnow")
def submit_indexnow_cmd():
    """Submit URLs to IndexNow"""
    submit_to_indexnow(f"https://filmhose.uk/")
    submit_to_indexnow(f"https://filmhose.uk/cinemas")
    for cinema in CINEMAS:
        submit_to_indexnow(f"https://filmhose.uk/cinemas/{cinema.shortname}")
        submit_to_indexnow(f"https://filmhose.uk/cinema-listings/{cinema.shortcode}")


@cli.command("scrape")
@click.argument("scraper")
def scrape_cmd(scraper):
    """Run scraper"""
    scrape_to_sqlite(scraper)


if __name__ == "__main__":
    cli()
