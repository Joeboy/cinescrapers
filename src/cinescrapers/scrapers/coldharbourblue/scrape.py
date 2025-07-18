from datetime import datetime
import json
from cinescrapers.types import ShowTime
from cinescrapers.exceptions import ScrapingError
from playwright.sync_api import sync_playwright
from rich import print


CINEMA_SHORTNAME = "Coldharbour Blue"
CINEMA_NAME = "Coldharbour Blue"
CINEMA_SHORTCODE = "CB"
BASE_URL = "https://www.coldharbourblue.com"
LISTINGS_URL = f"{BASE_URL}/about/"


def scrape() -> list[ShowTime]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(LISTINGS_URL)

        movies = page.locator("div.movie")
        showtimes = []
        assert movies.count()
        for i in range(movies.count()):
            print(f"Movie {1 + i} of {movies.count()} ({CINEMA_SHORTNAME})")
            movie = movies.nth(i)
            # print(movie.inner_html())
            link = movie.locator(".title-link").get_attribute("href")
            assert link
            if not link.startswith("http"):
                link = f"{BASE_URL}{link}"

            film_page = browser.new_page()
            film_page.goto(link)
            title = film_page.locator("meta[property='og:title']").get_attribute(
                "content"
            )
            assert title
            description = film_page.locator(
                "meta[property='og:description']"
            ).get_attribute("content")
            assert description
            img_src = film_page.locator("meta[property='og:image']").get_attribute(
                "content"
            )
            assert img_src
            if not img_src.startswith("http"):
                img_src = f"{BASE_URL}{img_src}"
            ld_json_script = film_page.locator('script[type="application/ld+json"]')
            assert ld_json_script.count() == 1
            content = ld_json_script.inner_text()
            data = json.loads(content)
            graph = data.get("@graph")
            if not graph:
                raise ScrapingError(f"Could not find @graph in {link}")
            # print(graph)
            for item in graph:
                if item["@type"] == "Event":
                    date_time = datetime.fromisoformat(item["startDate"]).replace(
                        tzinfo=None
                    )
                    showtime_data = ShowTime(
                        cinema_shortcode=CINEMA_SHORTCODE,
                        title=title,
                        link=link,
                        datetime=date_time,
                        description=description,
                        image_src=img_src,
                    )
                    showtimes.append(showtime_data)
            film_page.close()

        browser.close()

    return showtimes
