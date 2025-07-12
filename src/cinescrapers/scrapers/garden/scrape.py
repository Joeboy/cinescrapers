import datetime

import dateparser
from cinescrapers.types import ShowTime
from playwright.sync_api import sync_playwright
from rich import print


CINEMA_SHORTNAME = "Garden Cinema"
CINEMA_NAME = "The Garden Cinema"
CINEMA_SHORTCODE = "GD"
BASE_URL = "https://www.thegardencinema.co.uk"
URL = f"{BASE_URL}"


def scrape() -> list[ShowTime]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL)

        film_divs = page.locator(".films-list__by-title__film")
        showtimes = []
        for i in range(film_divs.count()):
            print(f"Film {1 + i} of {film_divs.count()} ({CINEMA_NAME})")

            fd = film_divs.nth(i)

            (link_e,) = fd.locator(".films-list__by-title__film-title > a").all()
            link = link_e.get_attribute("href")
            assert link
            title = link_e.evaluate(
                'el => el.firstChild && el.firstChild.nodeType === Node.TEXT_NODE ? el.firstChild.nodeValue.trim() : ""'
            ).strip()

            film_page = browser.new_page()
            film_page.goto(link)

            description = film_page.locator('meta[name="description"]').get_attribute(
                "content"
            )
            assert description
            img_src = film_page.locator('meta[property="og:image"]').get_attribute(
                "content"
            )

            screenings_e = film_page.locator(".film-detail__screenings").first
            screenings_es = screenings_e.locator(".screening-panel")
            for j in range(screenings_es.count()):
                screening_es = screenings_es.nth(j)
                date_e = screening_es.locator(".screening-panel__date-title")
                if date_e.count() == 1:
                    date_str = date_e.first.text_content()
                elif date_e.count() == 0:
                    # Just use the last date_str
                    pass

                # .first.text_content()
                assert date_str
                time_str = screening_es.locator(
                    ".screening-time a.screening"
                ).first.text_content()
                assert time_str
                date = dateparser.parse(date_str)
                assert date
                time = datetime.datetime.strptime(time_str, "%H:%M").time()
                date_time = datetime.datetime.combine(date, time)

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

    # print(showtimes)
    return showtimes
