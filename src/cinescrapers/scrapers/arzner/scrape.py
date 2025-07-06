import html
from datetime import datetime
from cinescrapers.types import ShowTime
from playwright.sync_api import sync_playwright
from rich import print


CINEMA_SHORTNAME = "Arzner"
CINEMA_NAME = "The Arzner"
BASE_URL = "https://thearzner.com"
URL = f"{BASE_URL}/TheArzner.dll/WhatsOn"


def scrape() -> list[ShowTime]:
    """Thank you, The Arzner, for putting your listings in such a lovely format"""
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
                    cinema_shortname=CINEMA_SHORTNAME,
                    cinema_name=CINEMA_NAME,
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
