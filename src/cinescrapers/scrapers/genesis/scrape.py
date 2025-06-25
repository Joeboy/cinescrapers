import re

import dateparser
from cinescrapers.types import ShowTime
from cinescrapers.exceptions import ScrapingError
from playwright.sync_api import sync_playwright
from rich import print


CINEMA_SHORTNAME = "Genesis"
CINEMA_NAME = "The Genesis Cinema"
BASE_URL = "https://www.genesiscinema.co.uk"
URL = f"{BASE_URL}/whatson/all"


def scrape() -> list[ShowTime]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL)

        showtimes = []
        film_divs = page.locator("div.grid.grid-cols-10.gap-4.gap-y-5.my-5.mx-2")
        for i in range(film_divs.count()):
            print(f"Film {1 + i} of {film_divs.count()} ({CINEMA_NAME})")

            fd = film_divs.nth(i)
            # print(fd.inner_html())
            img_e = fd.locator(":scope> div > img")
            assert img_e.count() == 1
            img_src = img_e.get_attribute("src")
            assert img_src is not None
            if not img_src.startswith("http"):
                img_src = f"{BASE_URL}{img_src}"
            title_e = fd.locator("h1")
            assert title_e.count() == 1
            link_e = title_e.locator("a")
            assert link_e.count() == 1
            link = link_e.get_attribute("href")
            if link is None:
                raise ScrapingError("Failed to get link from film div")
            if not link.startswith("http"):
                link = f"{BASE_URL}{link}"
            title = link_e.text_content()
            assert title
            title = title.strip()
            assert title
            film_page = browser.new_page()
            film_page.goto(link)
            container = film_page.locator("div.grid.grid-cols-3.gap-4")
            assert container.count() == 1
            description_div = container.locator("div").last
            assert description_div.count() == 1
            description = description_div.text_content()
            assert description is not None
            description = description.strip()
            film_page.close()

            # Grab the dates and times a bit laboriously
            # from the original page:
            md_blocks = fd.locator("div.hidden[class*='md:block']")

            showtime_rows = md_blocks.locator(":scope > div")
            for j in range(showtime_rows.count()):
                showtime_row = showtime_rows.nth(j)
                date_str = showtime_row.inner_text().splitlines()[0]
                time_es = showtime_row.locator("span")
                for k in range(time_es.count()):
                    time_e = time_es.nth(k)
                    # print(f"{time_e.inner_text()}")
                    time_str = time_e.inner_text().strip()
                    if re.match(r"^\d\d:\d\d", time_str):
                        date_and_time_str = f"{date_str} {time_str}"
                        date_time = dateparser.parse(date_and_time_str)
                        if date_time is None:
                            raise ScrapingError("Failed to interpret date / time")

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

    # print(showtimes)
    return showtimes
