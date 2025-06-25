from datetime import datetime
import json
import re
from cinescrapers.types import ShowTime
from cinescrapers.exceptions import ScrapingError
from playwright.sync_api import sync_playwright
from rich import print


CINEMA_SHORTNAME = "Castle"
CINEMA_NAME = "The Castle Cinema"
BASE_URL = "https://thecastlecinema.com"
LISTINGS_URL = f"{BASE_URL}/listings/film/"

# DATE_RE = re.compile(r".*(\d\d\.\d\d\.\d\d)$")


def scrape() -> list[ShowTime]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(LISTINGS_URL)

        showtimes = []
        film_divs = page.locator("div.programme-tile")
        for i in range(film_divs.count()):
            print(f"Film {1 + i} of {film_divs.count()} ({CINEMA_SHORTNAME})")

            fd = film_divs.nth(i)
            # print(fd.inner_html())
            link_e = fd.locator("div.tile-details > a").first
            assert link_e.count() == 1
            link = link_e.get_attribute("href")
            assert link is not None
            if not link.startswith("http"):
                link = f"{BASE_URL}{link}"
            print(f"{link=}")

            title_e = fd.locator("div.tile-details h1").first
            assert title_e.count() == 1
            title = title_e.text_content()
            assert title is not None
            print(f"{title=}")

            img_container = fd.locator("picture img").first
            assert img_container.count() == 1
            img_src = img_container.get_attribute("src")
            assert img_src is not None
            if not img_src.startswith("http"):
                img_src = f"{BASE_URL}{img_src}"
            print(f"{img_src=}")

            film_page = browser.new_page()
            film_page.goto(link)

            description = film_page.locator(".film-synopsis").first
            assert description.count() == 1
            description = description.text_content()
            assert description is not None
            description = description.strip()
            print(f"{description=}")

            json_scripts = film_page.locator('script[type="application/ld+json"]')

            if json_scripts.count() < 1:
                raise ScrapingError(f"Could not find JSON-LD script in {link}")

            for j in range(json_scripts.count()):
                script = json_scripts.nth(j)
                content = script.inner_text()
                data = json.loads(content)
                if isinstance(data, dict) and data.get("@type") == "ScreeningEvent":
                    # print(data)
                    date_time = datetime.fromisoformat(data["startDate"])
                    showtime_data = ShowTime(
                        cinema_shortname=CINEMA_SHORTNAME,
                        cinema_name=CINEMA_NAME,
                        title=title,
                        link=link,
                        datetime=date_time,
                        description=description,
                        image_src=img_src,
                    )
                    showtimes.append(showtime_data)
            film_page.close()

        browser.close()

    # print(showtimes, len(showtimes))
    return showtimes
