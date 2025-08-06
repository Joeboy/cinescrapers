"""Utility functions to read from TMDB API"""

import json
import os
import time
from functools import lru_cache
from io import BytesIO

import requests
from PIL import Image
from rich import print

from cinescrapers.config import TMDB_DETAILS_CACHE_DIR, TMDB_IMAGE_PATH

TMDB_API_KEY = os.environ["TMDB_API_KEY"]
TMDB_BASE_URL = "https://api.themoviedb.org/3"


def tmdb_image_from_path(image_path: str) -> Image.Image:
    """Fetch an image from TMDB using the image path"""
    # The image paths returned by the API are relative and need to be
    # prefixed
    assert image_path.startswith("/")
    image_filename = image_path.split("/")[-1]
    image_filepath = TMDB_IMAGE_PATH / image_filename
    if image_filepath.exists():
        im = Image.open(image_filepath)
    else:
        image_url = f"https://image.tmdb.org/t/p/w500{image_path}"
        response = requests.get(image_url)
        response.raise_for_status()
        image_buffer = BytesIO(response.content)
        image_filepath.write_bytes(image_buffer.getvalue())
        image_buffer.seek(0)
        im = Image.open(image_buffer)
    return im


@lru_cache(maxsize=None)
def search_tmdb_by_title(title, year: int | None = None) -> list[dict]:
    """Search TMDB for a movie by title and optional year"""
    search_url = f"{TMDB_BASE_URL}/search/movie"
    params = {"api_key": TMDB_API_KEY, "query": title}

    if year:
        params["primary_release_year"] = str(year)

    response = requests.get(search_url, params=params)
    response.raise_for_status()
    response_data = response.json()

    results = []
    total_pages = response_data.get("total_pages", 0)
    if total_pages == 0:
        print(f"No results found for '{title}'")
        return []

    for page in range(1, total_pages + 1):
        params["page"] = page
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        response_data = response.json()
        if response_data["results"]:
            results.extend(response_data["results"])
    print(f"Found {len(results)} results for {title} (year: {year})")

    return results


def get_tmdb_movie_details(tmdb_id) -> dict:
    """Get detailed movie information from TMDB by movie ID with file caching"""

    cache_file = TMDB_DETAILS_CACHE_DIR / f"{tmdb_id}.json"

    # Calculate cache expiry based on TMDB ID
    # Lower IDs means films have been in the db longer, which means they're
    # less likely to update frequently
    if tmdb_id < 10000:
        cache_seconds = 30 * 24 * 3600  # 30 days for very old films
    elif tmdb_id < 100000:
        cache_seconds = 14 * 24 * 3600  # 14 days for old films
    elif tmdb_id < 1000000:
        cache_seconds = 7 * 24 * 3600  # 7 days for medium age films
    else:
        cache_seconds = 1 * 24 * 3600  # 1 day for recent films

    # Check if cached file exists and is not expired
    if cache_file.exists():
        file_age = time.time() - cache_file.stat().st_mtime
        if file_age < cache_seconds:
            print(f"Using cached data for TMDB ID {tmdb_id}")
            return json.loads(cache_file.read_text())
        else:
            print(f"Cache expired for TMDB ID {tmdb_id}, fetching fresh data")

    details_url = f"{TMDB_BASE_URL}/movie/{tmdb_id}"
    params = {"api_key": TMDB_API_KEY}

    response = requests.get(details_url, params=params)
    response.raise_for_status()
    data = response.json()

    cache_file.write_text(json.dumps(data))
    print(
        f"Cached TMDB details for ID {tmdb_id} (expires in {cache_seconds//3600} hours)"
    )

    return data


@lru_cache(maxsize=None)
def get_tmdb_recommendations(tmdb_id: int) -> list[dict]:
    """Get movie recommendations from TMDB for a specified movie ID"""
    recommendations_url = f"{TMDB_BASE_URL}/movie/{tmdb_id}/recommendations"
    params = {"api_key": TMDB_API_KEY}

    response = requests.get(recommendations_url, params=params)
    if response.status_code == 404:
        print(f"No recommendations found for TMDB ID {tmdb_id}")
        return []
    response.raise_for_status()
    return response.json().get("results", [])
