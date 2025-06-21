from collections import defaultdict
import dateparser
from playwright.sync_api import sync_playwright

from cinescrapers.types import ShowTime

CINEMA_NAME = "Prince Charles Cinema"


def scrape() -> list[ShowTime]:
    url = "https://princecharlescinema.com/whats-on/"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url)

        page.wait_for_selector("div.film_list-outer")
        film_divs = page.locator("div.film_list-outer")
        showtimes = []
        for i in range(film_divs.count()):
            print(f"Film {1 + i} of {film_divs.count()} ({CINEMA_NAME})")
            fd = film_divs.nth(i)
            # print(fd.inner_html())
            img = fd.locator("div.film_img img")
            img_src = img.get_attribute("src")

            a = fd.locator("a.liveeventtitle")
            title = a.inner_text()
            link = a.get_attribute("href")

            desc_paras = fd.locator("div.jacro-formatted-text p").all_inner_texts()
            description = "".join(desc_paras)

            performance_list_items = fd.locator("ul.performance-list-items")
            assert performance_list_items.count() == 1
            children = performance_list_items.locator(":scope > *").element_handles()

            # The PCC's website has a weird / invalid HTML structure
            # where the showtimes are demarcated by headings, so we
            # have to do this nonsense:
            grouped = defaultdict(list)
            current_heading = None
            for child in children:
                tag = child.evaluate("e => e.tagName.toLowerCase()")

                if tag == "div":
                    class_name = child.get_attribute("class")
                    if "heading" in class_name:  # type: ignore
                        current_heading = child.inner_text()
                elif tag == "li" and current_heading:
                    time_span = child.query_selector("span.time")
                    time_text = time_span.inner_text() if time_span else "(no time)"
                    grouped[current_heading].append(time_text)

            for date_str, time_strs in grouped.items():
                for time_str in time_strs:
                    date_and_time_str = f"{date_str} {time_str}"
                    date_and_time = dateparser.parse(date_and_time_str)
                    if date_and_time is None:
                        raise RuntimeError(
                            f"Could not parse '{date_and_time_str} as a date/time string"
                        )

                    showtime_data = {
                        "cinema": CINEMA_NAME,
                        "title": title,
                        "link": link,
                        "datetime": date_and_time,
                        "description": description,
                        "image_src": img_src,
                    }
                    # print(film_data)
                    showtimes.append(showtime_data)

        page.close()
        browser.close()

    return showtimes
