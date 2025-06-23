"""Abortive effort"""

import base64
import json
import os
from datetime import datetime
from pathlib import Path
import re
from time import sleep
from typing import Any

import requests
from playwright.sync_api import sync_playwright
from rich import print

from cinescrapers.exceptions import EmptyPage, ScrapingError, TooManyRequestsError
from cinescrapers.types import ShowTime

API_HOST = "film-chase1.p.rapidapi.com"
API_BASE_URL = f"https://{API_HOST}"

# For now, these are the cinemas we'll grab data for. ie. a few of the smaller,
# non-chain ones. Largely because we don't get many API requests on the free plan
CHAINS = [
    "kiln_theatre",
    # "prince_charles",
    "bfi",
    # "the_light",
    # "omniplex",
]
BOOKING_LINK_RE = re.compile(
    "^https://kilntheatre.com/whats-on/(?P<title_slug>[^/]+)/.*$"
)

# DATE_RE = re.compile(r".*(\d\d\.\d\d\.\d\d)$")


def encode_path(path: str) -> str:
    return base64.urlsafe_b64encode(path.encode("utf-8")).decode("ascii").rstrip("=")


def decode_path(encoded: str) -> str:
    padded = encoded + "=" * ((4 - len(encoded) % 4) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")


def call_api(endpoint: str, params: dict | None = None, use_cache: bool = True) -> Any:
    """Call an api endpoint. Sometime, I should extract the cacheing stuff for use with non-json."""

    rapidapi_api_key = os.getenv("RAPIDAPI_API_KEY")
    if not rapidapi_api_key:
        raise RuntimeError(
            "The RAPIDAPI_API_KEY environment variable needs to be set for this to work"
        )
    headers = {
        "x-rapidapi-host": "film-chase1.p.rapidapi.com",
        "x-rapidapi-key": rapidapi_api_key,
    }
    url = f"https://{API_HOST}{endpoint}"
    print(f"{url=}")
    print(f"{headers=}")

    req = requests.Request("GET", url, headers=headers, params=params)
    prepared = req.prepare()

    cache_dir = os.getenv("RAPIDAPI_CACHE_DIR")
    if use_cache and cache_dir:
        full_url: str = prepared.url  # type: ignore

        filename = f"{encode_path(full_url)}"
        filepath = Path(cache_dir) / filename
        print(f"{filepath=}")
        if filepath.exists():
            print(f"CACHE HIT for {full_url}")
            with open(filepath, "r") as f:
                data = json.load(f)
                if data == []:
                    raise EmptyPage
        else:
            print(f"CACHE MISS for {full_url}")
            sleep(5)  # RapidAPI is rate limited

            with requests.Session() as session:
                response = session.send(prepared)
                if response.ok:
                    content = response.content
                    with open(filepath, "wb") as f:
                        f.write(content)
                    data = json.loads(content)
                    if data == []:
                        raise EmptyPage
                else:
                    if response.status_code == 429:
                        raise TooManyRequestsError
                    print(f"{response=}")
                    print(dir(response))
                    raise RuntimeError(f"Got bad response from api: {endpoint}")
    else:
        sleep(5)  # RapidAPI is rate limited
        with requests.Session() as session:
            response = session.send(prepared)
        if response.ok:
            data = response.json()
            if data == []:
                raise EmptyPage
        else:
            if response.status_code == 429:
                raise TooManyRequestsError
            print(f"{response=}")
            print(dir(response))
            print(f"{response.status_code=}")
            print(endpoint)
            raise RuntimeError(f"Got bad response from api: {endpoint}")

    return data


def get_all_cinemas_from_api() -> list[dict[str, Any]]:
    """This seems to return something like 500-1000 records (and shouldn't take
    more than a handful of requests)"""
    page_no = 1
    cinemas = []
    while page_no < 999:
        try:
            cinemas.extend(call_api("/cinemas", params={"items": 100, "page": page_no}))
        except (TooManyRequestsError, EmptyPage):
            break
        page_no += 1
    return cinemas


def get_all_cinemas(use_local_file: bool = True) -> list[dict[str, Any]]:
    """Return a list of cinema data. Optionally try to load it from
    a local file (to save hits to the API)"""
    filepath = Path(__file__).parent / "cinemas.json"
    if use_local_file:
        if filepath.exists():
            print("Loading cinemas list from local file")
            with open(filepath) as f:
                cinemas = json.load(f)
    else:
        cinemas = get_all_cinemas_from_api()

    # with open(filepath, "w") as f:
    #     json.dump(cinemas, f)
    return cinemas


def is_in_london(lat: float, lon: float) -> bool:
    """Simple bounding box check for Londonishness"""
    return 51.2868 <= lat <= 51.6919 and -0.5103 <= lon <= 0.3340


def get_london_cinemas() -> list[dict[str, Any]]:
    all_cinemas = get_all_cinemas()
    print(f"Found {len(all_cinemas)} cinemas")
    cinemas = [c for c in all_cinemas if is_in_london(c["latitude"], c["longitude"])]
    print(f"Found {len(cinemas)} cinemas in London")

    distinct_chains = set(c["chain"] for c in cinemas)
    print("\nDISTINCT CHAINS:")
    for ch in distinct_chains:
        print(f"{ch}:")
        for c in cinemas:
            if c["chain"] == ch:
                print(c["name"])
        print()

    # Filter by our hardcoded list of chains:
    cinemas = [c for c in cinemas if c["chain"] in CHAINS]
    return cinemas


def process_kiln_listings(kiln_listings: list[dict]) -> list[ShowTime]:
    kiln_showtimes = []
    for kl in kiln_listings:
        m = BOOKING_LINK_RE.match(kl["booking_link"])
        if not m:
            raise RuntimeError(
                f"Booking link {kl['booking_link']} did not match expected format"
            )
        title = m.group("title_slug").replace("-", " ").title()
        print(f"{title=}")
        import dateparser

        date_time = dateparser.parse(kl["showing_at"])
        if date_time is None:
            raise ScrapingError("Could not parse showing_at")

        kiln_showtimes.append(
            ShowTime(
                cinema="Kiln Theatre",
                title=title,
                datetime=date_time,
                link=kl["booking_link"],
                description="No description",
                image_src="No image",
            )
        )
    return kiln_showtimes

def process_bfi_listings(bfi_listings: list[dict]) -> list[ShowTime]:
    bfi_showtimes = []
    for listing in bfi_listings:
        print(listing)

        xx
    return bfi_showtimes


def scrape() -> list[ShowTime]:
    cinemas = get_london_cinemas()
    print(cinemas)

    # Fetch all the listings for all the cinemas:
    listings = []
    for cinema in cinemas:
        print(cinema["name"])
        page_no = 1
        while page_no < 999:
            params = {
                "cinema_id": cinema["id"],
                "page": page_no,
                "items": 100,
            }
            try:
                listings.extend(call_api("/showtimes", params=params))
            except (TooManyRequestsError, EmptyPage) as e:
                print(e)
                print("breaking")
                break
            page_no += 1
    print(listings)
    print(len(listings))

    showtimes = []

    kiln_showtimes = process_kiln_listings([l for l in listings if l["chain"] == "kiln_theatre"])
    showtimes.extend(kiln_showtimes)
    bfi_showtimes = process_bfi_listings([l for l in listings if l["chain"] == "bfi"])
    showtimes.extend(bfi_showtimes)
    print(showtimes)

    return showtimes
    qq
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL)

        showtimes = []
        film_divs = page.locator("div.inner_block_3")
        for i in range(film_divs.count()):
            print(f"Film {1 + i} of {film_divs.count()} ({CINEMA_NAME})")

            fd = film_divs.nth(i)
            inner_block_l = fd.locator("div.inner_block_3_l")
            inner_block_r = fd.locator("div.inner_block_3_r")
            if inner_block_l.count() < 1 or inner_block_r.count() < 1:
                # This doesn't look like it's a film listing
                continue
            imgs = inner_block_l.locator("a > img")
            assert imgs.count() == 1
            img_src = imgs.get_attribute("src")
            img_src = f"{BASE_URL}{img_src}"

            header_container = inner_block_r.locator("h2 > a")
            assert header_container.count() == 1
            link = header_container.get_attribute("href")
            link = f"{BASE_URL}{link}"

            film_page = browser.new_page()
            film_page.goto(link)
            description = film_page.locator('meta[name="description"]').get_attribute(
                "content"
            )
            if description is None:
                raise ScrapingError(f"Could not get description from {link}")
            calender_table = film_page.locator("div.booking_calender table")
            if calender_table.count() == 0:
                print(f"Skipping {link} as there's no calendar on that page")
                continue
            calender_rows = calender_table.locator("tr#row")
            for j in range(calender_rows.count()):
                row = calender_rows.nth(j)
                cells = row.locator("td")
                assert cells.count() == 4
                title = cells.nth(0).text_content()
                if title is None:
                    raise ScrapingError(
                        f"Could not get title element from calendar at {link}"
                    )
                date_str = cells.nth(1).text_content()
                if date_str is None:
                    raise ScrapingError(f"Failed to read date at {link}")
                m = DATE_RE.match(date_str)
                if m is None:
                    raise ScrapingError(f"Failed to interpret date at {link}")
                date_str = m.group(1)
                time_str = cells.nth(2).text_content().strip()  # type: ignore
                date_and_time_str = f"{date_str} {time_str}"
                date_and_time = datetime.strptime(
                    date_and_time_str, "%d.%m.%y %I:%M %p"
                )

                showtime_data = ShowTime(
                    cinema=CINEMA_NAME,
                    title=title,
                    link=link,
                    datetime=date_and_time,
                    description=description,
                    image_src=img_src,
                )
                # print(showtime_data)
                showtimes.append(showtime_data)

            film_page.close()

        page.close()
        browser.close()

    return showtimes
