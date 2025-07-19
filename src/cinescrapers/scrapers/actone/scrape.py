import re

from playwright.sync_api import sync_playwright
from rich import print

from cinescrapers.types import ShowTime
from cinescrapers.utils import parse_date_without_year

CINEMA_SHORTNAME = "ActOne"
CINEMA_NAME = "ActOne Cinema"
CINEMA_SHORTCODE = "AC"
BASE_URL = "https://www.actonecinema.co.uk"
LISTINGS_URL = f"{BASE_URL}/whats-on"
MOVIE_HREF = re.compile(r"^https://www\.actonecinema\.co\.uk\/movie/.*$")


def scrape() -> list[ShowTime]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(java_script_enabled=False)
        page = context.new_page()
        page.goto(LISTINGS_URL)

        hrefs = page.locator("a")
        movie_hrefs = []
        for i in range(hrefs.count()):
            href = hrefs.nth(i).get_attribute("href")
            if href and MOVIE_HREF.match(href):
                movie_hrefs.append(href)
        assert movie_hrefs, "No movie links found on the page"

        showtimes = []
        for i, link in enumerate(movie_hrefs):
            print(f"Movie {1 + i} of {len(movie_hrefs)} ({CINEMA_SHORTNAME})")
            film_page = context.new_page()
            film_page.goto(link)

            title = film_page.locator("meta[property='og:title']").get_attribute(
                "content"
            )
            assert title, "Failed to get movie title"
            description = film_page.locator(
                "meta[property='og:description']"
            ).get_attribute("content")
            assert description, "Failed to get movie description"
            img_src = film_page.locator("meta[property='og:image']").get_attribute(
                "content"
            )
            assert img_src, "Failed to get movie image source"

            date_time_es = film_page.locator("h2 > a")
            for j in range(date_time_es.count()):
                date_time_e = date_time_es.nth(j)
                date_time_str = date_time_e.text_content()
                assert date_time_str
                date_time = parse_date_without_year(date_time_str.strip())

                showtime_data = ShowTime(
                    cinema_shortcode=CINEMA_SHORTCODE,
                    title=title,
                    link=link,
                    datetime=date_time,
                    description=description,
                    image_src=img_src,
                )
                showtimes.append(showtime_data)
                # print(showtime_data)

            film_page.close()

        browser.close()

    return showtimes
