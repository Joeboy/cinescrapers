from datetime import datetime
import re

import dateparser
from playwright.sync_api import sync_playwright, Browser
from rich import print

from cinescrapers.exceptions import ScrapingError
from cinescrapers.types import ShowTime
from cinescrapers.utils import parse_date_without_year

BASE_URL = "https://www.electriccinema.co.uk"
URL = f"{BASE_URL}/programme/list/"
TIME_RE = re.compile(r"(\d{1,2}:\d{2})")


def scrape_cinema(browser: Browser, cinema_name: str) -> list[ShowTime]:
    if cinema_name == "portobello":
        CINEMA_SHORTCODE = "EP"
    elif cinema_name == "white-city":
        CINEMA_SHORTCODE = "EW"
    else:
        raise ScrapingError(f"Unknown cinema name: {cinema_name}")
    url = f"{URL}{cinema_name.lower()}/"
    page = browser.new_page()
    page.goto(url)
    page.wait_for_load_state("networkidle")
    day_es = page.locator(".screening-day")
    assert day_es.count()
    showtimes = []
    for i in range(day_es.count()):
        print(f"Processing day {1 + i} of {day_es.count()} ({cinema_name})")
        day_e = day_es.nth(i)
        date_str = day_e.locator(".date-month").inner_text().strip()
        date = parse_date_without_year(date_str)
        assert date
        film_rows = day_e.locator(".film-listing__row")

        for i in range(film_rows.count()):
            film_row = film_rows.nth(i)
            # print(film_row.inner_html())
            title_e = film_row.locator(".film-listing__title")
            link_e = title_e.locator(":scope > a")
            assert link_e.count() == 1
            link = link_e.get_attribute("href")
            assert link
            if not link.startswith("http"):
                link = f"{BASE_URL}{link}"

            title = link_e.inner_text().strip()
            assert title

            image_e = film_row.locator("img.film-thumb")
            assert image_e.count() == 1
            image_src = image_e.get_attribute("src")
            assert image_src
            if not image_src.startswith("http"):
                image_src = f"{BASE_URL}{image_src}"

            # Go to the film page to get the synopsis:
            film_page = browser.new_page()
            film_page.goto(link)
            film_page.wait_for_load_state("networkidle")
            film_page.wait_for_selector(".film-info__synopsis")
            description_e = film_page.locator(".film-info__synopsis")
            # weirdly there seem to be two descriptions, one of them for
            # "The Fall Guy", and the other for the actual film
            assert description_e.count() == 2
            for j in range(description_e.count()):
                text = description_e.nth(j).inner_text().strip()
                if not text.startswith("Synopsis\nHe's a stuntman"):
                    description = text
                    break
            if description.startswith("Synopsis\n"):
                description = description[len("Synopsis\n") :]
            assert description
            film_page.close()

            screening_time_es = film_row.locator(".screening-time")
            for j in range(screening_time_es.count()):
                screening_time_e = screening_time_es.nth(j)
                assert screening_time_e.count() == 1
                time_str = screening_time_e.inner_text().strip()
                time_matches = TIME_RE.findall(time_str)
                assert len(time_matches) == 1
                (time_str,) = time_matches
                assert time_str
                parsed_time = dateparser.parse(time_str)
                assert parsed_time
                date_time = datetime.combine(date, parsed_time.time())

                showtime_data = ShowTime(
                    cinema_shortcode=CINEMA_SHORTCODE,
                    title=title,
                    link=link,
                    datetime=date_time,
                    description=description,
                    image_src=image_src,
                )
                showtimes.append(showtime_data)

    page.close()
    return showtimes


def scrape() -> list[ShowTime]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        showtimes = []
        showtimes.extend(scrape_cinema(browser, "portobello"))
        showtimes.extend(scrape_cinema(browser, "white-city"))
        browser.close()

    return showtimes
