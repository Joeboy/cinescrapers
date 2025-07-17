from datetime import datetime
import re
from cinescrapers.types import ShowTime
from cinescrapers.exceptions import ScrapingError
from playwright.sync_api import sync_playwright
from rich import print


CINEMA_SHORTCODE = "CL"
CINEMA_NAME = "Ciné Lumière"
BASE_URL = "https://www.institut-francais.org.uk"
URL = f"{BASE_URL}/whats-on/?type=72&period=any&location=onsite#/"

DATE_RE = re.compile(r".*(\d\d\.\d\d\.\d\d)$")


def scrape() -> list[ShowTime]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL)

        #        html = page.locator("html").inner_html()
        showtimes = []
        articles = page.locator("article")
        assert articles.count()
        for i in range(articles.count()):
            print(f"Film {1 + i} of {articles.count()} ({CINEMA_NAME})")
            article = articles.nth(i)
            article_a = article.locator(":scope >a")
            assert article_a.count() == 1
            link = article_a.get_attribute("href")
            assert link
            # print(f"Link: {link}")
            if "/festivals-and-series/" in link:
                print(f"Skipping festival link: {link}")
                continue
            metadata = article.locator("div.card__metadata")
            assert metadata.count() == 1
            tags = metadata.locator("div.tag")
            assert tags.count() > 0
            is_film = False
            for j in range(tags.count()):
                tag = tags.nth(j)
                # print(f"Tag: {tag.text_content()}")
                if tag.text_content().strip() == "Films":  # type: ignore
                    is_film = True
                    continue
            if not is_film:
                print(f"Skipping as this is not a film {link}")
                continue

            film_page = browser.new_page()
            film_page.goto(link)

            title = film_page.locator("meta[property='og:title']").get_attribute(
                "content"
            )
            assert title
            if title.endswith(" at Ciné Lumière - Institut Français · Royaume-Uni"):
                title = title[
                    : -len(" at Ciné Lumière - Institut Français · Royaume-Uni")
                ].strip()
            # print(f"Title: {title}")
            description = film_page.locator(
                "meta[property='og:description']"
            ).get_attribute("content")
            assert description
            image_src = film_page.locator("meta[property='og:image']").get_attribute(
                "content"
            )
            assert image_src

            showtime_table = film_page.locator("table")
            if showtime_table.count() == 0:
                # There's no showtime table, so we have to get the date
                # from elsewhere
                timetable_e = film_page.locator("div.timetable")
                assert timetable_e.count() == 1

                # Get date from first time element
                date_time_e = timetable_e.locator("div.date time")
                assert date_time_e.count() == 1
                date_str = date_time_e.get_attribute("datetime")
                assert date_str

                # Get time from second time element
                time_e = timetable_e.locator("time.time")
                assert time_e.count() == 1
                time_str = time_e.get_attribute("datetime")
                assert time_str

                # Combine date and time
                date_and_time_str = f"{date_str} {time_str}"
                date_and_time = datetime.fromisoformat(date_and_time_str)


                showtime_data = ShowTime(
                    cinema_shortcode=CINEMA_SHORTCODE,
                    title=title,
                    link=link,
                    datetime=date_and_time,
                    description=description,
                    image_src=image_src,
                )
                showtimes.append(showtime_data)

            elif showtime_table.count() == 1:
                showtime_rows = showtime_table.locator("tr")
                assert showtime_rows.count()
                for j in range(showtime_rows.count()):
                    row = showtime_rows.nth(j)
                    # print("--------")
                    # print(row.inner_html())
                    th_es = row.locator("th")
                    if th_es.count() > 0:
                        # This is a header row, skip it
                        continue
                    time_e = row.locator("time.time")
                    assert time_e.count() == 1
                    time_str = time_e.get_attribute("datetime")
                    date_e = row.locator("time.date")
                    assert date_e.count() == 1
                    date_str = date_e.get_attribute("datetime")
                    assert date_str
                    date_and_time_str = f"{date_str} {time_str}"
                    date_and_time = datetime.fromisoformat(date_and_time_str)

                    showtime_data = ShowTime(
                        cinema_shortcode=CINEMA_SHORTCODE,
                        title=title,
                        link=link,
                        datetime=date_and_time,
                        description=description,
                        image_src=image_src,
                    )
                    showtimes.append(showtime_data)
            else:
                raise ScrapingError(f"Multiple showtime tables found for {link}")

            film_page.close()
        page.close()
        browser.close()

    return showtimes
