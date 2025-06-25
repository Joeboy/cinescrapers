from datetime import datetime
import re
from cinescrapers.types import ShowTime
from cinescrapers.exceptions import ScrapingError
from playwright.sync_api import sync_playwright
from rich import print


CINEMA_SHORTNAME = "Close-Up"
CINEMA_NAME = "Close-Up Film Centre"
BASE_URL = "https://www.closeupfilmcentre.com"
URL = f"{BASE_URL}/film_programmes/"

DATE_RE = re.compile(r".*(\d\d\.\d\d\.\d\d)$")


def scrape() -> list[ShowTime]:
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
                    cinema_shortname=CINEMA_SHORTNAME,
                    cinema_name=CINEMA_NAME,
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
