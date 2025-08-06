import datetime
from pathlib import Path

CINESCRAPERS_ROOT = Path(__file__).parent
CACHE_FOLDER = CINESCRAPERS_ROOT / "cache"
DATA_FOLDER = CINESCRAPERS_ROOT / "data"
CACHE_FOLDER.mkdir(parents=True, exist_ok=True)
DATA_FOLDER.mkdir(parents=True, exist_ok=True)

TMDB_CACHE_DIR = CACHE_FOLDER / "tmdb"
TMDB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
TMDB_ID_CACHE = TMDB_CACHE_DIR / "tmdb_id_cache.json"
if not TMDB_ID_CACHE.exists():
    TMDB_ID_CACHE.write_text("{}")
TMDB_RECOMMENDATIONS_CACHE = TMDB_CACHE_DIR / "tmdb_recommendations_raw.json"
if not TMDB_RECOMMENDATIONS_CACHE.exists():
    TMDB_RECOMMENDATIONS_CACHE.write_text("{}")
TMDB_DETAILS_CACHE_DIR = TMDB_CACHE_DIR / "tmdb_details_cache"
if not TMDB_DETAILS_CACHE_DIR.exists():
    TMDB_DETAILS_CACHE_DIR.mkdir(parents=True, exist_ok=True)


CINEMAS_JSON = DATA_FOLDER / "cinemas.json"
SHOWTIMES_JSON = DATA_FOLDER / "cinescrapers.json"
TMDB_RECOMMENDATIONS_FILTERED = DATA_FOLDER / "tmdb_recommendations.json"

IMAGES_CACHE = CACHE_FOLDER / "scraped_images" / "source_images"
IMAGES_CACHE.mkdir(parents=True, exist_ok=True)
THUMBNAILS_FOLDER = CACHE_FOLDER / "scraped_images" / "thumbnails"
THUMBNAILS_FOLDER.mkdir(parents=True, exist_ok=True)
SITEMAP_XML = DATA_FOLDER / "sitemap.xml"
SITEMAP_XML_TEMPLATE = CINESCRAPERS_ROOT / "sitemap.xml.template"
MAP_HTML = DATA_FOLDER / "cinema_map.html"

DB_PATH = CACHE_FOLDER / "showtimes.db"

TMDB_IMAGE_PATH = TMDB_CACHE_DIR / "tmdb_images"
TMDB_IMAGE_PATH.mkdir(exist_ok=True)

# How long since the last update before we need to refresh a cinema's listings
MAX_STALENESS = datetime.timedelta(days=5)
