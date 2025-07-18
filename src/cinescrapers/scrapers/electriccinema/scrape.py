from datetime import datetime

from playwright.sync_api import sync_playwright
from rich import print

from cinescrapers.exceptions import ScrapingError
from cinescrapers.types import ShowTime

BASE_URL = "https://www.electriccinema.co.uk"
URL = f"{BASE_URL}/programme/list/"


def scrape() -> list[ShowTime]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL)

        # Evaluate the "electric" JavaScript variable
        try:
            electric_var = page.evaluate("() => window.electric")
        except Exception:
            raise ScrapingError("Failed to evaluate 'electric' variable")

        film_data = electric_var["filmData"]
        cinemas = film_data["cinemas"]
        films = film_data["films"]
        screenings = film_data["screenings"]

        cinemas_dict = {c["id"]: c["url"] for c in cinemas.values()}

        showtimes = []
        for i, screening in enumerate(screenings.values()):
            print(f"Processing screening {i + 1} of {len(screenings)}")
            film_id = screening["film"]
            date_str = f"{screening['d']} {screening['t']}"
            date_time = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            cinema_slug = cinemas_dict[screening["cinema"]]
            if cinema_slug == "portobello":
                CINEMA_SHORTCODE = "EP"
            elif cinema_slug == "white-city":
                CINEMA_SHORTCODE = "EW"
            else:
                raise ScrapingError(f"Unknown cinema slug: {cinema_slug}")
            film_data = films[str(film_id)]
            title = film_data["title"]
            description = film_data["short_synopsis"]
            link = film_data["link"]
            if not link.startswith("http"):
                link = f"{BASE_URL}{link}"
            image_src = film_data["image"]
            if not image_src.startswith("http"):
                image_src = f"{BASE_URL}{image_src}"

            showtime_data = ShowTime(
                cinema_shortcode=CINEMA_SHORTCODE,
                title=title,
                link=link,
                datetime=date_time,
                description=description,
                image_src=image_src,
            )
            showtimes.append(showtime_data)

        page.close()
        browser.close()

    return showtimes
