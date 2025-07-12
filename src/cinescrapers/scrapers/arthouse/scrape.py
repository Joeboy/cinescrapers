import datetime

import dateparser
from cinescrapers.types import ShowTime
from playwright.sync_api import sync_playwright
from rich import print


CINEMA_SHORTNAME = "ArtHouse"
CINEMA_NAME = "ArtHouse Crouch End"
CINEMA_SHORTCODE = "AH"
BASE_URL = "https://www.arthousecrouchend.co.uk"
URL = f"{BASE_URL}/booking-now/"


def scrape() -> list[ShowTime]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL)

        showtimes = []
        film_divs = page.locator("div.performance")
        for i in range(film_divs.count()):
            print(f"Film {1 + i} of {film_divs.count()} ({CINEMA_NAME})")

            fd = film_divs.nth(i)
            # print(fd.inner_html())
            link_e = fd.locator("a[itemprop='url']")
            assert link_e.count() == 1
            link = link_e.get_attribute("href")
            assert link
            if not link.startswith("http"):
                link = f"{BASE_URL}{link}"
            # print(link)
            assert link
            title_e = fd.locator("div.show-title")
            assert title_e.count() == 1
            title = title_e.inner_text().strip()
            desc_e = fd.locator("div.synopsis")
            assert desc_e.count() == 1
            description = desc_e.inner_text()
            img_e = fd.locator(".thumb > img")
            assert img_e.count() == 1
            img_src = img_e.get_attribute("src")

            film_page = browser.new_page()
            film_page.goto(link)

            dates_e = film_page.locator("#dates")
            for j in range(dates_e.count()):
                date_e = dates_e.nth(j)
                date_str = date_e.inner_text().strip()
                if date_str.lower() == "today":
                    date = datetime.datetime.today().replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                else:
                    date = dateparser.parse(date_str)
                    assert date is not None

                times_container = date_e.locator(
                    'xpath=following-sibling::*[contains(@class, "times")][1]'
                )
                assert times_container.count() == 1
                time_es = times_container.locator("span.prog-times")
                for k in range(time_es.count()):
                    time_e = time_es.nth(k)

                    # Remove any extra stuff like "SUBTITLED":
                    time_str = time_e.evaluate(
                        'el => el.firstChild && el.firstChild.nodeType === Node.TEXT_NODE ? el.firstChild.nodeValue.trim() : ""'
                    ).strip()

                    assert time_str
                    time_str = time_str.strip()
                    time = datetime.datetime.strptime(time_str, "%H:%M").time()
                    combined_dt = datetime.datetime.combine(date.date(), time)

                    showtime_data = ShowTime(
                        cinema_shortcode=CINEMA_SHORTCODE,
                        title=title,
                        link=link,
                        datetime=combined_dt,
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
