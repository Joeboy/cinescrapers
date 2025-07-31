import re

from playwright.sync_api import sync_playwright
from rich import print

from cinescrapers.cinescrapers_types import ShowTime
from cinescrapers.utils import parse_date_without_year

CINEMA_SHORTNAME = "Ciné Real"
CINEMA_NAME = "Ciné Real"
CINEMA_SHORTCODE = "CR"
BASE_URL = "https://www.cine-real.com"
LISTINGS_URL = f"{BASE_URL}/pages/next-screening"
DATE_AND_TIME_RE = re.compile(
    r"<b>[A-Z][a-z]+ (?P<date_str>\d\d? [A-Z][a-z]{2,8}) • (?P<time_str>\d{2}:\d{2})</b> ▪ <i>(?P<title>.*?)</i>"
)


def scrape() -> list[ShowTime]:
    """I'm not very confident this'll be robust. Let's try to keep an eye on the results"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(java_script_enabled=False)
        page = context.new_page()
        page.goto(LISTINGS_URL)
        print(LISTINGS_URL)

        showtimes = []
        main = page.locator("figure.wrap-center")
        print(main.count())
        assert main.count()
        titles_and_descriptions: list[tuple[str, str]] = []
        for i in range(main.count()):
            print(f"Film {1 + i} of {main.count()} ({CINEMA_SHORTNAME})")
            m = main.nth(i)
            assert m.count() == 1
            img = m.locator("img").first
            assert img.count() == 1
            img_src = img.get_attribute("src")
            title_e = m.locator("xpath=./preceding-sibling::p[1]")
            assert title_e.count() == 1
            title_text = title_e.text_content()
            assert title_text
            title_text = re.sub(r"\s+", " ", title_text, flags=re.UNICODE).strip()
            # print(f"Title text: {title_text}")
            description_e = m.locator("xpath=./following-sibling::p[position() <= 3]")
            assert description_e.count() >= 1
            description_texts = []
            for j in range(description_e.count()):
                desc_text = description_e.nth(j).text_content()
                if desc_text:
                    description_texts.append(desc_text.strip())
            description_text = "\n".join(description_texts)
            assert description_text
            # print(f"Description text: {description_text}")
            titles_and_descriptions.append((title_text, description_text))
        titles_and_descriptions_dict = {
            t.upper(): d for t, d in titles_and_descriptions
        }
        # print(f"Titles and descriptions: {titles_and_descriptions_dict}")

        page_content = page.content()
        dates_and_times = DATE_AND_TIME_RE.findall(page_content)
        # print(f"Dates and times: {dates_and_times}")

        for date_str, time_str, title in dates_and_times:
            date_time_str = f"{date_str} {time_str}"
            date_time = parse_date_without_year(date_time_str.strip())
            description = titles_and_descriptions_dict[title.upper()]

            showtime_data = ShowTime(
                cinema_shortcode=CINEMA_SHORTCODE,
                title=title,
                # Chickening out and just using the "main" link:
                link="https://www.cine-real.com/pages/next-screening",
                datetime=date_time,
                description=description,
                image_src=img_src,
            )
            showtimes.append(showtime_data)
            # print(showtime_data)

        browser.close()

    return showtimes
