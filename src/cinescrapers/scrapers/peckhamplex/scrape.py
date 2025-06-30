from datetime import datetime

from cinescrapers.types import ShowTime
from playwright.sync_api import sync_playwright

# ── site-specific values (replace) ─────────────────────────────────────────────
BASE_URL = "https://www.peckhamplex.london/"
CINEMA_NAME = "Peckhamplex"
CINEMA_SHORTNAME = "Peckhamplex"

LINK_SELECTOR = ".book-now a"
TITLE_SELECTOR = ".page-title"

DATE_TIMES_SELECTOR = "time"

IMAGE_SELECTOR = ".poster img"
DESCRIPTION_SELECTOR = 'p[itemprop="description"]'


def scrape() -> list[ShowTime]:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        showtimes: list[ShowTime] = []

        url = f"{BASE_URL}films/out-now"
        page.goto(url)

        films = page.locator(LINK_SELECTOR)

        film_count = films.count()
        for idx in range(film_count):
            film = films.nth(idx)

            link = film.get_attribute("href") or ""

            detail_page = browser.new_page()
            detail_page.goto(link)

            title = detail_page.locator(TITLE_SELECTOR).text_content()
            assert title

            print(f"Film {1 + idx} of {films.count()} ({CINEMA_NAME}) - {title}")

            image = detail_page.locator(IMAGE_SELECTOR).get_attribute("src") or ""

            description = detail_page.locator(DESCRIPTION_SELECTOR).text_content() or ""

            times = detail_page.locator(DATE_TIMES_SELECTOR)

            for j in range(times.count()):
                time = times.nth(j)
                date_time_str = time.get_attribute("datetime")
                assert date_time_str

                showtimes.append(
                    ShowTime(
                        cinema_shortname=CINEMA_SHORTNAME,
                        cinema_name=CINEMA_NAME,
                        title=title,
                        link=f"{link}",
                        datetime=datetime.fromisoformat(date_time_str),
                        description=description,
                        image_src=f"{BASE_URL}{image}",
                    )
                )
            detail_page.close()

        page.close()
        browser.close()

    return showtimes
