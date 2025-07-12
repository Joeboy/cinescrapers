import dateparser
from cinescrapers.types import ShowTime
from playwright.sync_api import sync_playwright
from rich import print


CINEMA_SHORTNAME = "Bertha DocHouse"
CINEMA_SHORTCODE = "BR"
CINEMA_NAME = "Bertha DocHouse"
BASE_URL = "https://dochouse.org"


def scrape() -> list[ShowTime]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        showtimes = []
        page_no = 1
        while page_no < 99:
            url = f"{BASE_URL}/whats-on/page/{page_no}/"
            print(f"Scraping {url}")

            page.goto(url)
            data_listing = page.locator("div[data-listing]")
            assert data_listing.count() == 1
            cards = data_listing.locator(".card")
            if cards.count() == 0:
                # Looks like we ran out of events
                break
            for i in range(cards.count()):
                card = cards.nth(i)
                img_a = card.locator("div.card-img > div.img-wrapper > a")
                assert img_a.count() == 1
                link = img_a.get_attribute("href")
                assert link

                film_page = browser.new_page()
                film_page.goto(link)
                title = film_page.locator('meta[property="og:title"]').get_attribute(
                    "content"
                )
                assert title
                if title.endswith(" - Bertha DocHouse"):
                    title = title[: -len(" - Bertha DocHouse")]
                description = film_page.locator(
                    'meta[property="og:description"]'
                ).get_attribute("content")
                assert description
                img_src = film_page.locator('meta[property="og:image"]').get_attribute(
                    "content"
                )
                assert img_src
                events_container = film_page.locator(".events-tablet")
                assert events_container.count() == 1
                event_date_es = events_container.locator("div.event-date")
                for j in range(event_date_es.count()):
                    event_date_e = event_date_es.nth(j)
                    date_e = event_date_e.locator(".date")

                    assert date_e.count() == 1
                    date_str = date_e.inner_text().strip()
                    time_e = event_date_e.locator(".time")
                    assert time_e.count() == 1
                    time_str = time_e.inner_text().strip()
                    date_time_str = f"{date_str} {time_str}"
                    date_time = dateparser.parse(date_time_str)
                    assert date_time
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
            page_no += 1

        page.close()
        browser.close()

    return showtimes
