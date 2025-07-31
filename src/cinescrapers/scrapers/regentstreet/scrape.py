import re
from playwright.sync_api import sync_playwright
from rich import print

from cinescrapers.cinescrapers_types import ShowTime
from cinescrapers.utils import parse_date_without_year

CINEMA_SHORTNAME = "Regent Street"
CINEMA_NAME = "Regent Street Cinema"
CINEMA_SHORTCODE="RG"
BASE_URL = "https://www.regentstreetcinema.com"
URL = f"{BASE_URL}/now-playing"

HREF_RE = re.compile(r"href=\"([^\"]*)\"", re.I)
MOVIE_LINK_RE = re.compile(r"^https://www.regentstreetcinema.com/movie/.*$")


def scrape() -> list[ShowTime]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(java_script_enabled=False)
        page = context.new_page()
        page.goto(f"{URL}")

        html = page.locator("html").inner_html()
        hrefs = HREF_RE.findall(html)
        movie_hrefs = [h for h in hrefs if MOVIE_LINK_RE.match(h)]

        showtimes = []
        for i, link in enumerate(movie_hrefs):
            print(f"Film {1 + i} of {len(movie_hrefs)} ({CINEMA_SHORTNAME})")
            film_page = context.new_page()
            film_page.goto(link)

            showtimes_es = film_page.locator(
                '//h1[normalize-space(text())="Showtimes"]/following-sibling::h2'
            )
            if showtimes_es.count() == 0:
                # Sometimes we get pages with no showtimes
                continue

            title = film_page.locator("meta[property='og:title']").get_attribute(
                "content"
            )
            assert title
            description = film_page.locator(
                "meta[property='og:description']"
            ).get_attribute("content")
            assert description
            image_src = film_page.locator("meta[property='og:image']").get_attribute(
                "content"
            )
            assert image_src

            for i in range(showtimes_es.count()):
                date_time_str = showtimes_es.nth(i).text_content()
                assert date_time_str
                date_time = parse_date_without_year(date_time_str)

                showtime_data = ShowTime(
                    cinema_shortcode=CINEMA_SHORTCODE,
                    title=title,
                    link=link,
                    datetime=date_time,
                    description=description,
                    image_src=image_src,
                )
                showtimes.append(showtime_data)
            film_page.close()

        page.close()
        browser.close()

    return showtimes
