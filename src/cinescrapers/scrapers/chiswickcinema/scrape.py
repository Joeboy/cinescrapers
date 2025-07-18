from playwright.sync_api import sync_playwright
from rich import print

from cinescrapers.types import ShowTime
from cinescrapers.utils import parse_date_without_year

CINEMA_SHORTCODE = "CC"
BASE_URL = "https://www.chiswickcinema.co.uk"
URL = f"{BASE_URL}/whats-on/"


def scrape() -> list[ShowTime]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL)
        showtimes = []

        film_es = page.locator(".whats-on__films__film")
        assert film_es.count()
        for i in range(film_es.count()):
            print(f"Film {1 + i} of {film_es.count()} ({CINEMA_SHORTCODE})")
            film_e = film_es.nth(i)

            link_e = film_e.locator(":scope > a")
            assert link_e.count() == 1
            link = link_e.get_attribute("href")
            assert link

            img_e = link_e.locator(":scope > img")
            assert img_e.count() == 1
            image_src = img_e.get_attribute("src")
            assert image_src
            if not image_src.startswith("http"):
                image_src = f"{BASE_URL}{image_src}"

            film_page = browser.new_page()
            film_page.goto(link)
            title = film_page.locator("meta[property='og:title']").get_attribute(
                "content"
            )
            assert title
            if title.endswith(" – The Chiswick Cinema"):
                title = title[: -len(" – The Chiswick Cinema")]

            description_e = film_page.locator(".film-details__synopsis")
            assert description_e.count() == 1
            description = description_e.text_content()
            assert description

            book_tickets_schedule = film_page.locator(
                ".film-details__book-tickets__schedule"
            )
            assert book_tickets_schedule.count() == 1

            # Parse each day's showtimes
            day_elements = book_tickets_schedule.locator(
                ".film-details__book-tickets__schedule__day"
            )
            for day_idx in range(day_elements.count()):
                day_element = day_elements.nth(day_idx)

                # Get the date label (e.g., "Fri 18 Jul")
                date_label = day_element.locator(
                    ".film-details__book-tickets__schedule__day__label"
                ).text_content()
                assert date_label

                parsed_date = parse_date_without_year(date_label)

                # Get all time links for this day
                time_links = day_element.locator("a.book__link")
                for time_idx in range(time_links.count()):
                    time_link = time_links.nth(time_idx)
                    time_str = time_link.get_attribute("data-time")
                    assert time_str

                    # Parse time and combine with date
                    time_parts = time_str.split(":")
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])

                    showtime_datetime = parsed_date.replace(hour=hour, minute=minute)

                    showtime_data = ShowTime(
                        cinema_shortcode=CINEMA_SHORTCODE,
                        title=title,
                        link=link,
                        datetime=showtime_datetime,
                        description=description,
                        image_src=image_src,
                    )
                    showtimes.append(showtime_data)

            film_page.close()

        page.close()
        browser.close()

    return showtimes
