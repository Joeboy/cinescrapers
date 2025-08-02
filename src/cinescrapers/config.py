import datetime
from pathlib import Path

CACHE_FOLDER = Path(__file__).parent / "cache"
TMDB_ID_CACHE = CACHE_FOLDER / "tmdb_id_cache.json"
if not TMDB_ID_CACHE.exists():
    # Create the cache file if it doesn't exist
    TMDB_ID_CACHE.write_text("{}")
TMDB_RECOMMENDATIONS_CACHE = CACHE_FOLDER / "tmdb_recommendations_raw.json"
if not TMDB_RECOMMENDATIONS_CACHE.exists():
    TMDB_RECOMMENDATIONS_CACHE.write_text("{}")
TMDB_RECOMMENDATIONS_FILTERED = CACHE_FOLDER / "tmdb_recommendations.json"


# TODO: Move images and thumbnails into CACHE_FOLDER
IMAGES_CACHE = Path(__file__).parent / "scraped_images" / "source_images"
IMAGES_CACHE.mkdir(parents=True, exist_ok=True)
THUMBNAILS_FOLDER = Path(__file__).parent / "scraped_images" / "thumbnails"
THUMBNAILS_FOLDER.mkdir(parents=True, exist_ok=True)

# How long since the last update before we need to refresh a cinema's listings
MAX_STALENESS = datetime.timedelta(days=5)
