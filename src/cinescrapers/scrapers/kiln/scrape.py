import re
from playwright.sync_api import sync_playwright

from cinescrapers.types import ShowTime
from cinescrapers.utils import parse_date_without_year
from rich import print

CINEMA_NAME = "The Kiln Theatre"
CINEMA_SHORTNAME = "Kiln Theatre"
BASE_URL = "https://kilntheatre.com"
LISTINGS_URL = f"{BASE_URL}/cinema-listings/"

TITLE_RE = re.compile(r"^(?P<title>.*) \([^\)]+\)$")


def scrape() -> list[ShowTime]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(LISTINGS_URL)

        # This site is slightly annoying. There's the film info, and the listings
        # info, but they're in different places. So let's grab what film info we
        # can, then later we'll associate it with the listings info
        film_divs = page.locator("div.c-film-listing > a")
        film_data = {}
        print(f"Pre-fetching film data ({CINEMA_NAME})")
        for i in range(film_divs.count()):
            fd = film_divs.nth(i)
            title_e = fd.locator(":scope > h5.c-film-listing__title")
            assert title_e.count() == 1
            title = title_e.inner_text().strip()
            img_e = fd.locator("img.c-film-listing__image")
            assert img_e.count() == 1
            img_src = img_e.get_attribute("src")
            link = fd.get_attribute("href")
            assert link

            film_page = browser.new_page()
            film_page.goto(link)
            desc_e = film_page.locator("section > div.max-width-wrap > div.c-col-txt")
            assert desc_e.count() == 1
            description = desc_e.inner_text()
            film_data[title] = {
                "title": title,
                "link": link,
                "image_src": img_src,
                "description": description,
            }

        def scrape_showtimes_for_page(page_no: int) -> list[ShowTime]:
            # Now back to the listings page, to get the dates
            booking_singles = page.locator("div.c-booking-single")
            showtimes_for_page = []
            for i in range(booking_singles.count()):
                print(f"Page {page_no}, date {1 + i} of {film_divs.count()} ({CINEMA_NAME})")
                date_div = booking_singles.nth(i)
                date_e = date_div.locator("div.c-film-booking__date")
                assert date_e.count() == 1
                date_str = date_e.inner_text()
                time_lis = date_div.locator("li")
                for j in range(time_lis.count()):
                    li = time_lis.nth(j)
                    title_e = li.locator("p.c-film-booking__title")
                    assert title_e.count() == 1
                    title = title_e.inner_text().strip()
                    # Remove the rating suffix, eg " (PG)""
                    m = TITLE_RE.match(title)
                    assert m
                    title = m.group("title")
                    time_e = li.locator(".c-film-booking__time")
                    assert time_e.count() == 1
                    time_str = time_e.inner_text()
                    date_time_str = f"{date_str} {time_str}"
                    date_time = parse_date_without_year(date_time_str)
                    # As of now, all the film_data is present. Maybe one day it won't be?
                    # Let's worry about that if / when it happens
                    showtime_data = film_data[title]
                    showtime_data |= {
                        "cinema_name": CINEMA_NAME,
                        "cinema_shortname": CINEMA_SHORTNAME,
                        "datetime": date_time,
                    }
                    showtime = ShowTime(**showtime_data)
                    showtime.title = showtime.title.title()
                    showtimes_for_page.append(showtime)
            return showtimes_for_page

        showtimes = []
        page_no = 1
        while 1:
            showtimes_for_page = scrape_showtimes_for_page(page_no)
            if not showtimes_for_page:
                break
            showtimes.extend(showtimes_for_page)

            # Click the "next page" button and wait for response:
            with page.expect_response("**/admin/wp-admin/admin-ajax.php"):
                page.click("i.fa.fa-chevron-right")
            page_no += 1

        page.close()
        browser.close()

    # print(showtimes)
    return showtimes
