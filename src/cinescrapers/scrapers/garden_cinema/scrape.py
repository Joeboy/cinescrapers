from datetime import datetime
from zoneinfo import ZoneInfo

from cinescrapers.types import ShowTime
from cinescrapers.exceptions import ScrapingError
from playwright.sync_api import sync_playwright
import unicodedata

# ── site-specific values (replace) ─────────────────────────────────────────────
BASE_URL = "https://www.thegardencinema.co.uk/"
CINEMA_NAME = "The Garden Cinema"
CINEMA_SHORTNAME = "Garden Cinema"

LIST_ITEM_SELECTOR = ".films-list__by-date__film"
TITLE_SELECTOR = ".films-list__by-date__film__title a"
LINK_SELECTOR = "h1 a"

IMAGE_SELECTOR = ".film-detail__image__wrapper img"                
DESCRIPTION_SELECTOR = ".film-detail__synopsis"         
 
SCREENING_SELECTOR = ".screening-panel"  
DATE_SELECTOR = ".screening-panel__date-title"     
TIME_SELECTOR = ".screening-time a"    

def scrape() -> list[ShowTime]:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        showtimes: list[ShowTime] = []
        seen_titles = set()

        url = BASE_URL
        page.goto(url)

        items = page.locator(LIST_ITEM_SELECTOR)
        for idx in range(items.count()):

            item = items.nth(idx)

            title = item.locator(TITLE_SELECTOR).evaluate("el => el.childNodes[0].textContent.trim()")

            if title in seen_titles:
                continue

            print(f"Film {1 + idx} of {items.count()} ({CINEMA_NAME}) - {title}")

            seen_titles.add(title)

            link = item.locator(LINK_SELECTOR).get_attribute("href") or ""

            detail_page = browser.new_page()
            detail_page.goto(link)


            image = detail_page.locator(IMAGE_SELECTOR).get_attribute("src") or ""
            desc_container = detail_page.locator(DESCRIPTION_SELECTOR)
            paragraphs = desc_container.locator("p")
            description_parts = []

            for i in range(paragraphs.count()):
                text = paragraphs.nth(i).text_content().strip()
                if "Cast:" in text:
                    break
                if text:
                    description_parts.append(text)

            description = clean_description(" ".join(description_parts))
            screenings = detail_page.locator(SCREENING_SELECTOR)

            date_str = None
            for j in range(screenings.count()):
                date_loc = screenings.nth(j).locator(DATE_SELECTOR)
                
                # Multiple screenings on the same day are in different divs,
                # so reuse the last date if we don't find a date in this div
                if date_loc.count() > 0:
                    date_str = date_loc.text_content()

                if date_str is None:
                    raise ScrapingError(
                        f"Missing datetime on performances page for {link}"
                    )

                time_str = screenings.nth(j).locator(TIME_SELECTOR).text_content()
                if time_str is None:
                    raise ScrapingError(
                        f"Missing time on performances page for {link}"
                    )
                
                dt = parse_datetime(date_str, time_str)

                showtimes.append(
                    ShowTime(
                        cinema_shortname=CINEMA_SHORTNAME,
                        cinema_name=CINEMA_NAME,
                        title=title,
                        link=f"{link}",
                        datetime=dt,
                        description=description,
                        image_src=f"{image}",
                    )
                )
            detail_page.close()

        page.close()
        browser.close()

    return showtimes


def parse_datetime(date_str: str, time_str: str) -> datetime:
    current_year = datetime.now().year
    full_str = f"{date_str} {current_year} {time_str}" 

    dt = datetime.strptime(full_str, "%a %d %b %Y %H:%M")

    dt = dt.replace(tzinfo=ZoneInfo("Europe/London")).astimezone(ZoneInfo("Europe/London")).replace(tzinfo=None)
    return dt

def clean_description(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = unicodedata.normalize("NFKC", text)
    text = text.strip()
    return text