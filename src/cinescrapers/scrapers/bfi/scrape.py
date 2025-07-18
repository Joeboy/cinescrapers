import dateparser
from playwright.sync_api import Error as PlayWrightError
from playwright.sync_api import sync_playwright
from pyvirtualdisplay.display import Display
from rich import print

from cinescrapers.exceptions import ScrapingError
from cinescrapers.types import ShowTime

CINEMA_SHORTCODE = "BF"
INDEX_URL = "https://whatson.bfi.org.uk/Online/article/filmsindex"


def scrape() -> list[ShowTime]:
    showtimes = []
    display = Display(visible=False, size=(1920, 1080))
    display.start()
    with sync_playwright() as p:
        # Couldn't make it work headlessly, maybe because I have no idea
        # what I'm doing
        browser = p.chromium.launch(headless=False)
        index_page = browser.new_page()
        index_page.goto(INDEX_URL)
        listings_container = index_page.locator("div.Rich-text")

        assert listings_container.count() == 1
        # print(listings_container.inner_html())
        lis = listings_container.locator("ul > li > a")

        for i in range(lis.count()):
            print(f"Film {1 + i} of {lis.count()} (bfi)")
            li = lis.nth(i)
            title = li.inner_text()
            href = li.get_attribute("href")
            if href is None:
                raise ScrapingError(f"Could not get href for {title}")
            if not href.startswith("https://"):
                href = f"https://whatson.bfi.org.uk/Online/{href}"
            # print(f"{href=}", type(href))
            film_page = browser.new_page()
            film_page.goto(href)
            try:
                articleContext = film_page.evaluate("articleContext")
            except PlayWrightError:
                import traceback

                traceback.print_exc()
                print(f"Skipping {href}")
                film_page.close()
                continue
            try:
                searchNames = articleContext["searchNames"]
                searchResults = articleContext["searchResults"]
            except KeyError:
                # This doesn't look like it has listings on it
                print(f"skipping {href}")
                film_page.close()
                continue
            listings = [
                dict(zip(searchNames, searchResult)) for searchResult in searchResults
            ]
            # print(listings)

            desc_container = film_page.locator("div.Rich-text").first
            description = desc_container.inner_text()
            img_e = film_page.locator("img.Media__image").first
            img_src = img_e.get_attribute("src")
            assert img_src
            if not img_src.startswith("http"):
                img_src = f"https://whatson.bfi.org.uk{img_src}"

            for listing in listings:
                date_and_time = dateparser.parse(listing["start_date"])
                if date_and_time is None:
                    raise ScrapingError("Could not parse date and time")

                showtime = ShowTime(
                    cinema_shortcode=CINEMA_SHORTCODE,
                    title=title,
                    link=href,
                    datetime=date_and_time,
                    description=description,
                    image_src=img_src,
                )
                # print(showtime)
                showtimes.append(showtime)
            film_page.close()

    display.stop()
    return showtimes
