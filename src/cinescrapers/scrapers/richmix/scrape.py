from datetime import datetime

import dateparser
from cinescrapers.cinescrapers_types import ShowTime
from playwright.sync_api import sync_playwright
from rich import print


CINEMA_SHORTNAME = "Rich Mix"
CINEMA_NAME = "Rich Mix"
CINEMA_SHORTCODE = "RM"
BASE_URL = "https://richmix.org.uk"
URL = f"{BASE_URL}/whats-on/cinema/"


def scrape() -> list[ShowTime]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL)

        showtimes = []
        articles_section = page.locator("section#articles")
        assert articles_section.count() == 1
        film_divs = articles_section.locator("article")
        for i in range(film_divs.count()):
            print(f"Film {1 + i} of {film_divs.count()} ({CINEMA_NAME})")

            fd = film_divs.nth(i)
            img_a = fd.locator("div.post-image > a").first
            link = img_a.get_attribute("href")
            assert link
            img_e = img_a.locator("img").first
            img_src = img_e.get_attribute("src")

            film_page = browser.new_page()
            film_page.goto(link)

            title = film_page.locator('meta[property="og:title"]').get_attribute(
                "content"
            )
            assert title
            if title.endswith(" - Rich Mix"):
                title = title[: -len(" - Rich Mix")]
            description = film_page.locator(
                'meta[property="og:description"]'
            ).get_attribute("content")
            assert description

            dates_and_times_e = film_page.locator("div#dates-and-times")
            if dates_and_times_e.count() == 0:
                # I think it doesn't display the dates / times if the film
                # already started
                print(f"Skipping {link}")
                continue
            assert dates_and_times_e.count() == 1

            days_e = dates_and_times_e.locator("div.day")

            for j in range(days_e.count()):
                day_e = days_e.nth(j)
                weekday_e = day_e.locator("div.weekday, div.instance-date")
                assert weekday_e
                weekday_str = weekday_e.inner_text()
                date_as_datetime = dateparser.parse(weekday_str)
                assert date_as_datetime
                date = date_as_datetime.date()

                time_es = day_e.locator(".times > a.time")
                for k in range(time_es.count()):
                    time_e = time_es.nth(k)
                    time_str = time_e.inner_text()
                    time_as_datetime = dateparser.parse(time_str)
                    assert time_as_datetime
                    time = time_as_datetime.time()
                    date_time = datetime.combine(date, time)

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

        page.close()
        browser.close()

    return showtimes
