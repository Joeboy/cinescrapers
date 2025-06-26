from datetime import datetime
from cinescrapers.types import ShowTime
from playwright.sync_api import sync_playwright
from rich import print


CINEMA_SHORTNAME = "Rio"
CINEMA_NAME = "The Rio"
BASE_URL = "https://riocinema.org.uk"
URL = f"{BASE_URL}/Rio.dll/WhatsOn"


def scrape() -> list[ShowTime]:
    """Thank you, The Rio, for putting your listings in such a lovely format"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL)

        showtimes = []
        q = page.evaluate("Events")
        events = q["Events"]
        for event in events:
            # print(event)
            title = event["Title"]
            link = event["URL"]
            description = event["Synopsis"]
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
