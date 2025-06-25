import dateparser
from playwright.sync_api import sync_playwright
from rich import print

from cinescrapers.exceptions import ScrapingError
from cinescrapers.types import ShowTime

INDEX_URL = "https://whatson.bfi.org.uk/Online/article/filmsindex"


def scrape() -> list[ShowTime]:
    showtimes = []
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
            print(f"Film {1 + i} of {lis.count()}")
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
            articleContext = film_page.evaluate("articleContext")
            try:
                searchNames = articleContext["searchNames"]
                searchResults = articleContext["searchResults"]
            except KeyError:
                # This doesn't look like it has listings on it
                print("skipping")
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
            img_src = f"https://whatson.bfi.org.uk{img_src}"

            for listing in listings:
                date_and_time = dateparser.parse(listing["start_date"])
                if date_and_time is None:
                    raise ScrapingError("Could not parse date and time")

                if "southbank" in listing["venue_name"].lower():
                    cinema_name = "BFI Southbank"
                else:
                    cinema_name = "BFI"

                showtime = ShowTime(
                    cinema_shortname="BFI",
                    cinema_name=cinema_name,
                    title=title,
                    link=href,
                    datetime=date_and_time,
                    description=description,
                    image_src=img_src,
                )
                # print(showtime)
                showtimes.append(showtime)
            film_page.close()

    return showtimes
