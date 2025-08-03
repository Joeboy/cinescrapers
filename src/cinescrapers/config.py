import datetime
from pathlib import Path

CINESCRAPERS_ROOT = Path(__file__).parent
CACHE_FOLDER = CINESCRAPERS_ROOT / "cache"
DATA_FOLDER = CINESCRAPERS_ROOT / "data"
CACHE_FOLDER.mkdir(parents=True, exist_ok=True)
DATA_FOLDER.mkdir(parents=True, exist_ok=True)

TMDB_ID_CACHE = CACHE_FOLDER / "tmdb_id_cache.json"
if not TMDB_ID_CACHE.exists():
    # Create the cache file if it doesn't exist
    TMDB_ID_CACHE.write_text("{}")
TMDB_RECOMMENDATIONS_CACHE = CACHE_FOLDER / "tmdb_recommendations_raw.json"
if not TMDB_RECOMMENDATIONS_CACHE.exists():
    TMDB_RECOMMENDATIONS_CACHE.write_text("{}")
TMDB_RECOMMENDATIONS_FILTERED = DATA_FOLDER / "tmdb_recommendations.json"
CINEMAS_JSON = CINESCRAPERS_ROOT / "cinemas.json"
SHOWTIMES_JSON = CINESCRAPERS_ROOT / "cinescrapers.json"

# TODO: Move images and thumbnails into CACHE_FOLDER
IMAGES_CACHE = CINESCRAPERS_ROOT / "scraped_images" / "source_images"
IMAGES_CACHE.mkdir(parents=True, exist_ok=True)
THUMBNAILS_FOLDER = CINESCRAPERS_ROOT / "scraped_images" / "thumbnails"
THUMBNAILS_FOLDER.mkdir(parents=True, exist_ok=True)
SITEMAP_XML = CINESCRAPERS_ROOT / "sitemap.xml"
SITEMAP_XML_TEMPLATE = CINESCRAPERS_ROOT / "sitemap.xml.template"
MAP_HTML = CINESCRAPERS_ROOT / "cinema_map.html"

# TODO: Move database to DATA_FOLDER
DB_PATH = CINESCRAPERS_ROOT.parent / "showtimes.db"

TMDB_IMAGE_PATH = CINESCRAPERS_ROOT / "tmdb_images"
TMDB_IMAGE_PATH.mkdir(exist_ok=True)

# How long since the last update before we need to refresh a cinema's listings
MAX_STALENESS = datetime.timedelta(days=5)
