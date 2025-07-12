import re

import dateparser
from cinescrapers.types import ShowTime
from cinescrapers.exceptions import ScrapingError
from playwright.sync_api import sync_playwright
from rich import print


CINEMA_NAME = "Institute of Contemporary Arts"
CINEMA_SHORTNAME = "ICA"
CINEMA_SHORTCODE = "IC"
BASE_URL = "https://www.ica.art"
INDEX_URL = f"{BASE_URL}/films"

DATE_RE = re.compile(r".*(\d\d\.\d\d\.\d\d)$")


def scrape() -> list[ShowTime]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(INDEX_URL)

        showtimes = []
        film_divs = page.locator(".item.films")

        for i in range(film_divs.count()):
            print(f"Film {1 + i} of {film_divs.count()} ({CINEMA_NAME})")

            fd = film_divs.nth(i)

            a = fd.locator(":scope > a")
            assert a.count() == 1
            link = a.get_attribute("href")
            link = f"{BASE_URL}{link}"

            title_e = a.locator(".title-container .title").last
            assert title_e.count() == 1
            title = title_e.text_content()
            if title is None:
                raise ScrapingError("Failed to get title")

            img_e = a.locator("img").first
            if img_e.count() > 0:
                img_src = img_e.get_attribute("src")
                if img_src is None:
                    raise ScrapingError("Failed to get image src")
                if img_src.startswith("//"):
                    img_src = f"https:{img_src}"
            else:
                img_src = None
            description_e = a.locator("div.description").first
            description = description_e.inner_text()

            film_page = browser.new_page()
            film_page.goto(link)

            performances = film_page.locator("div.performance.future")
            for j in range(performances.count()):
                performance = performances.nth(j)
                date_e = performance.locator("div.date").first
                date_str = date_e.inner_text()
                time_e = performance.locator("div.time").first
                time_str = time_e.inner_text()
                date_and_time = f"{date_str} {time_str}"
                date_time = dateparser.parse(date_and_time)
                if date_time is None:
                    raise ScrapingError(f"Failed to parse date_time at {link}")

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

            film_page.close()

        page.close()
        browser.close()

    return showtimes
