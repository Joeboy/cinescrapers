from datetime import datetime
from zoneinfo import ZoneInfo
from cinescrapers.types import ShowTime
from cinescrapers.exceptions import ScrapingError
from playwright.sync_api import sync_playwright
from rich import print


CINEMA_NAME = "Barbican"
CINAME_SHORTNAME = "Barbican"
BASE_URL = "https://www.barbican.org.uk"


def scrape() -> list[ShowTime]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        showtimes = []

        page_no = 0
        while True:
            url = f"{BASE_URL}/whats-on?af[16]=16&page={page_no}"
            page.goto(url)

            if page.locator(".no-result-message").count() > 0 or page_no > 25:
                # No results on the page suggests we've scraped all
                # the pages already
                break

            film_divs = page.locator("article.listing--event")
            for i in range(film_divs.count()):
                print(
                    f"Page {1 + page_no}, Film {1 + i} of {film_divs.count()} ({CINEMA_NAME})"
                )

                fd = film_divs.nth(i)
                link_e = fd.locator("a.search-listing__link")
                link = link_e.get_attribute("href")
                link = f"{BASE_URL}{link}"
                picture = fd.locator("picture img").first
                img_src = picture.get_attribute("src")
                img_src = f"{BASE_URL}{img_src}"
                title_e = fd.locator("h2.listing-title")
                assert title_e.count() == 1
                title = title_e.text_content()
                assert title is not None
                desc_e = fd.locator("div.search-listing__intro")
                assert desc_e.count() == 1
                description = desc_e.text_content()
                assert description is not None
                description = description.strip()
                # print(f"{description=}")

                button = fd.locator("button.saved-event-button").first
                assert button.count() == 1
                event_id = button.get_attribute("data-saved-event-id")
                assert event_id is not None
                # print(f"{event_id=}")

                bookings_url = f"{BASE_URL}/whats-on/event/{event_id}/performances"
                # print(f"{bookings_url=}")

                bookings_page = browser.new_page()
                bookings_page.goto(bookings_url)
                time_elements = bookings_page.locator("time")
                for j in range(time_elements.count()):
                    time_element = time_elements.nth(j)
                    date_str = time_element.get_attribute("datetime")
                    # print(f"{date_str=}")
                    if date_str is None:
                        raise ScrapingError(
                            f"Could not get datetime from {bookings_url}"
                        )
                    date_and_time = datetime.fromisoformat(date_str)
                    date_and_time = date_and_time.astimezone(
                        ZoneInfo("Europe/London")
                    ).replace(tzinfo=None)

                    # print(f"{date_and_time=}")
                    showtime_data = ShowTime(
                        cinema_shortname=CINAME_SHORTNAME,
                        cinema_name=CINEMA_NAME,
                        title=title,
                        link=link,
                        datetime=date_and_time,
                        description=description,
                        image_src=img_src,
                    )
                    showtimes.append(showtime_data)

                bookings_page.close()

            page_no += 1

        # print(showtimes)

        page.close()
        browser.close()

    return showtimes
