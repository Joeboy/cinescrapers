import html
from datetime import datetime
from cinescrapers.cinescrapers_types import ShowTime
from playwright.sync_api import sync_playwright
from rich import print


CINEMA_SHORTNAME = "Lexi"
CINEMA_NAME = "The Lexi"
CINEMA_SHORTCODE="LX"
BASE_URL = "https://thelexicinema.co.uk"
URL = f"{BASE_URL}/TheLexiCinema.dll/WhatsOn"


def scrape() -> list[ShowTime]:
    """Thank you, The Lexi, for putting your listings in such a lovely format"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL)

        showtimes = []
        q = page.evaluate("Events")
        events = q["Events"]
        for event in events:
            # print(event)
            title = html.unescape(event["Title"])
            link = event["URL"]
            description = html.unescape(event["Synopsis"])
            img_src = event["ImageURL"]
            performances = event["Performances"]
            for performance in performances:
                date_and_time_str = (
                    f"{performance['StartDate']} {performance['StartTime']}"
                )
                date_time = datetime.strptime(date_and_time_str, "%Y-%m-%d %H%M")

                showtime_data = ShowTime(
                    cinema_shortcode=CINEMA_SHORTCODE,
                    title=title,
                    link=link,
                    datetime=date_time,
                    description=description,
                    image_src=img_src,
                )
                # print(showtime_data)
                showtimes.append(showtime_data)

        page.close()
        browser.close()

    print(f"Scraped {len(showtimes)} showtimes")
    return showtimes
