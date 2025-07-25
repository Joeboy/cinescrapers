import asyncio
import dateparser
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright
from pyvirtualdisplay.display import Display
from rich import print

from cinescrapers.exceptions import ScrapingError
from cinescrapers.types import ShowTime

CINEMA_SHORTCODE = "BF"
INDEX_URL = "https://whatson.bfi.org.uk/Online/article/filmsindex"


async def process_film(
    browser, li, film_num, total_films, semaphore
) -> tuple[int, list[ShowTime]]:
    """Process a single film and return its showtimes with film number"""
    async with semaphore:  # Limit concurrent browser pages
        print(f"Film {film_num} of {total_films} (bfi)")
        title = await li.inner_text()
        href = await li.get_attribute("href")
        if href is None:
            raise ScrapingError(f"Could not get href for {title}")
        if not href.startswith("https://"):
            href = f"https://whatson.bfi.org.uk/Online/{href}"

        film_page = await browser.new_page()
        try:
            await film_page.goto(href)
            try:
                articleContext = await film_page.evaluate("articleContext")
            except PlaywrightError:
                import traceback

                traceback.print_exc()
                print(f"Skipping {href}")
                return (film_num, [])

            try:
                searchNames = articleContext["searchNames"]
                searchResults = articleContext["searchResults"]
            except KeyError:
                # This doesn't look like it has listings on it
                print(f"skipping {href}")
                return (film_num, [])

            listings = [
                dict(zip(searchNames, searchResult)) for searchResult in searchResults
            ]

            desc_container = film_page.locator("div.Rich-text").first
            description = await desc_container.inner_text()
            img_e = film_page.locator("img.Media__image").first
            img_src = await img_e.get_attribute("src")
            assert img_src
            if not img_src.startswith("http"):
                img_src = f"https://whatson.bfi.org.uk{img_src}"

            showtimes = []
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
                showtimes.append(showtime)

            return (film_num, showtimes)
        finally:
            await film_page.close()


async def scrape_async() -> list[ShowTime]:
    showtimes = []
    display = Display(visible=False, size=(1920, 1080))
    display.start()
    async with async_playwright() as p:
        # Couldn't make it work headlessly, maybe because I have no idea
        # what I'm doing
        browser = await p.chromium.launch(headless=False)
        index_page = await browser.new_page()
        await index_page.goto(INDEX_URL)
        listings_container = index_page.locator("div.Rich-text")

        assert await listings_container.count() == 1
        lis = listings_container.locator("ul > li > a")

        # Get the count once to avoid multiple awaits
        lis_count = await lis.count()

        # Create a semaphore to limit concurrent browser pages
        semaphore = asyncio.Semaphore(25)  # Limit to 10 concurrent pages

        # Create tasks for processing all films concurrently
        tasks = []
        for i in range(lis_count):
            li = lis.nth(i)
            task = process_film(browser, li, i + 1, lis_count, semaphore)
            tasks.append(task)

        # Process all films concurrently (but limited by semaphore)
        print(f"Processing {len(tasks)} films with max 10 concurrent pages...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect all showtimes from successful results
        for result in results:
            if isinstance(result, Exception):
                print(f"Error processing film: {result}")
            elif isinstance(result, tuple) and len(result) == 2:
                film_num, film_showtimes = result
                showtimes.extend(film_showtimes)
                print(
                    f"Added {len(film_showtimes)} showtimes from film {film_num} or {len(tasks)}"
                )

    display.stop()
    return showtimes


def scrape() -> list[ShowTime]:
    """Sync wrapper for the async scrape function"""
    return asyncio.run(scrape_async())
