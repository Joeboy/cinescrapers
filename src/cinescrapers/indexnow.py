import json
from typing import List
import requests


HOST = "filmhose.uk"
KEY = "2ecc17a53f9c441c9b9ace180a511698"
KEY_LOCATION = f"https://filmhose.uk/{KEY}.txt"
API_URL = "https://api.indexnow.org/IndexNow"


def submit_to_indexnow(
    url: str,
) -> None:
    """
    Submit URLs to IndexNow API to notify search engines of content changes.
    """

    payload = {
        "host": HOST,
        "key": KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": [url],
    }

    headers = {"Content-Type": "application/json; charset=utf-8"}

    response = requests.post(API_URL, headers=headers, data=json.dumps(payload))

    response.raise_for_status()
    print(response.status_code, response.text)
