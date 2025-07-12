import datetime
import re
import dateparser
from playwright.sync_api import sync_playwright
from rich import print

from cinescrapers.types import ShowTime

CINEMA_SHORTNAME = "Lumiere Romford"
CINEMA_NAME = "Lumiere Romford"
CINEMA_SHORTCODE = "LR"
BASE_URL = "https://www.lumiereromford.com"
URL = f"{BASE_URL}"

DATE_RE = re.compile(r".*/showtimes/(?P<date>20\d\d-[01]\d-[0123]\d)\?.*")


def scrape() -> list[ShowTime]:
    """One of the more annoying / challenging sites to scrape so far"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{BASE_URL}/available-to-book")

        # Seems like we have to do this for all the page content to load:
        page.keyboard.press("End")
        page.wait_for_load_state("networkidle")
        page.keyboard.press("End")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        showtimes = []

        movie_cards = page.locator(".movie-outer-wrapper")
        for i in range(movie_cards.count()):
            print(f"Movie {1 + i} of {movie_cards.count()} ({CINEMA_NAME})")
            movie_card = movie_cards.nth(i)

            # We have to get the description and showtimes from separate pages
            action_wrap_e = movie_card.locator(".action-wrap")
            assert action_wrap_e.count() == 1
            more_info_a = action_wrap_e.locator(":scope > a.is-secondary-small")
            assert more_info_a.count() == 1
            link = more_info_a.get_attribute("href")
            link = f"{BASE_URL}/{link}"
            assert link
            buy_tickets_a = action_wrap_e.locator(":scope > a.is-small")
            assert buy_tickets_a.count() == 1

            info_page = browser.new_page()
            info_page.goto(link)
            description_e = info_page.locator(".movie_description")
            assert description_e.count() == 1
            description = description_e.inner_text()
            title = info_page.locator("meta[property='og:title']").get_attribute(
                "content"
            )
            assert title
            image_src = info_page.locator("meta[property='og:image']").get_attribute(
                "content"
            )
            assert image_src
            info_page.close()

            buy_tickets_url = buy_tickets_a.get_attribute("href")
            buy_tickets_url = f"{BASE_URL}/{buy_tickets_url}"
            buy_tickets_page = browser.new_page()
            buy_tickets_page.goto(buy_tickets_url)
            buy_tickets_page.wait_for_load_state("networkidle")
            buy_tickets_page.wait_for_timeout(300)

            day_cards = buy_tickets_page.locator("a.day_card")
            assert day_cards.count() > 0
            for i in range(day_cards.count()):
                day_card = day_cards.nth(i)
                date_url = day_card.get_attribute("href")
                assert date_url
                m = DATE_RE.match(date_url)
                assert m
                date_str = m.group("date")
                date = datetime.datetime.strptime(date_str, "%Y-%m-%d")

                date_url = f"{BASE_URL}/{date_url}"
                date_page = browser.new_page()
                date_page.goto(date_url)

                showtime_es = buy_tickets_page.locator(".showtime")
                assert showtime_es.count() > 0
                for j in range(showtime_es.count()):
                    showtime_e = showtime_es.nth(j)
                    time_str = showtime_e.inner_text()
                    t = dateparser.parse(time_str)
                    assert t
                    date_time = datetime.datetime.combine(date.date(), t.time())
                    showtime_data = ShowTime(
                        cinema_shortcode=CINEMA_SHORTCODE,
                        title=title,
                        link=link,
                        datetime=date_time,
                        description=description,
                        image_src=image_src,
                    )
                    showtimes.append(showtime_data)

                date_page.close()

            buy_tickets_page.close()

        page.close()
        browser.close()

    return showtimes
