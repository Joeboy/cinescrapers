import zoneinfo
from datetime import datetime

from playwright.sync_api import sync_playwright
from rich import print

from cinescrapers.cinescrapers_types import ShowTime

CINEMA_SHORTNAME = "Sands Films"
CINEMA_SHORTCODE = "SF"

URL = "https://www.sandsfilms.co.uk/cinema-club.html"
EVENT_URL_TEMPLATE = "https://sandsfilms.eventive.org/schedule/{}"


def scrape() -> list[ShowTime]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()

        captured = {}

        ctx.on(
            "response",
            lambda resp: (
                captured.setdefault("data", resp.json())
                if ("api.eventive.org/event_buckets/" in resp.url)
                and ("/events" in resp.url)
                else None
            ),
        )

        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(1000)
        browser.close()
        data = captured["data"]
        showtimes = []
        for i, event in enumerate(data["events"]):
            if event["is_virtual"]:
                print("Skipping virtual event")
                continue
            films = [f for f in event["films"] if f["type"] == "film"]
            if len(films) == 0:
                continue
            elif len(films) == 1:
                (film,) = films
            elif len(films) > 1:
                (film,) = [f for f in films if f["credits"]]

            title = film["name"]
            assert title
            imdb_id = film["imdb_id"]
            assert imdb_id
            link = EVENT_URL_TEMPLATE.format(event["id"])
            assert link
            description = film["description"]
            image_src = film["poster_image"]
            assert image_src

            date_time_str = event["start_time"]
            dt_utc = datetime.fromisoformat(date_time_str.replace("Z", "+00:00"))
            london_tz = zoneinfo.ZoneInfo("Europe/London")
            date_time = dt_utc.astimezone(london_tz).replace(tzinfo=None)

            showtime_data = ShowTime(
                cinema_shortcode=CINEMA_SHORTCODE,
                title=title,
                link=link,
                datetime=date_time,
                description=description,
                image_src=image_src,
                imdb_id=imdb_id,
            )
            showtimes.append(showtime_data)

        page.close()
        browser.close()

    return showtimes
