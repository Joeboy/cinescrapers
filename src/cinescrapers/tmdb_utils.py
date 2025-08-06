import datetime
import json
import os
import sqlite3
import time
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import clip
import requests
import torch
from PIL import Image
from rich import print
from sentence_transformers import SentenceTransformer

from cinescrapers.cinescrapers_types import EnrichedShowTime, TmdbItemFeatures
from cinescrapers.config import (
    DB_PATH,
    TMDB_DETAILS_CACHE_DIR,
    TMDB_IMAGE_PATH,
    TMDB_RECOMMENDATIONS_CACHE,
)
from cinescrapers.database import database_connection
from cinescrapers.title_normalization import normalize_title

TMDB_API_KEY = os.environ["TMDB_API_KEY"]
TMDB_BASE_URL = "https://api.themoviedb.org/3"

last_year = datetime.datetime.now().year - 1


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


def get_all_tmdb_recommendations():
    """Get tmdb recommendations for all TMDB IDs in the database"""
    cache = json.loads(TMDB_RECOMMENDATIONS_CACHE.read_text())
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT tmdb_id FROM showtimes WHERE tmdb_id IS NOT NULL"
        )
        tmdb_ids = [row[0] for row in cursor.fetchall()]
    tmdb_id_count = len(tmdb_ids)
    for i, tmdb_id in enumerate(tmdb_ids):
        if str(tmdb_id) in cache.keys():
            continue
        print(
            f"Fetching recommendations for TMDB ID {tmdb_id} ({i + 1}/{tmdb_id_count})"
        )
        recommendations = get_tmdb_recommendations(tmdb_id)
        cache[str(tmdb_id)] = [r["id"] for r in recommendations]

    TMDB_RECOMMENDATIONS_CACHE.write_text(json.dumps(cache))

    # So that gets us all of the recommendations for all TMDB IDs in the db.
    # But, we only care about recommendations if we have them in our showtimes db
    recommendations = {k: set(v) & set(tmdb_ids) for k, v in cache.items()}
    recommendations = {k: list(v) for k, v in recommendations.items() if v}
    return recommendations


def get_similarity_model():
    """Load the SentenceTransformer model for text similarity"""
    if not hasattr(get_similarity_model, "_model"):
        get_similarity_model._model = SentenceTransformer("all-MiniLM-L6-v2")
    return get_similarity_model._model


def get_sentence_embedding(text: str) -> torch.Tensor:
    """Get embedding for a given text using SentenceTransformer"""

    similarity_model = get_similarity_model()
    embedding = similarity_model.encode(text, convert_to_tensor=True)
    return embedding


def get_clip_embedding(im: Image.Image) -> torch.Tensor:
    """Get CLIP embedding for an image"""
    if not hasattr(get_clip_embedding, "_cache"):
        model, preprocess = clip.load("ViT-B/32")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        get_clip_embedding._cache = (model, preprocess, device)
    model, preprocess, device = get_clip_embedding._cache
    image = preprocess(im).unsqueeze(0).to(device)  # type: ignore
    with torch.no_grad():
        image_features = model.encode_image(image)
    return image_features / image_features.norm(dim=-1, keepdim=True)


def get_nlp_model():
    """Load the spaCy model for named entity recognition"""
    if not hasattr(get_nlp_model, "_nlp"):
        import spacy

        model_name = "en_core_web_sm"

        # Check if model is already installed
        try:
            get_nlp_model._nlp = spacy.load(model_name)
            print(f"Loaded existing {model_name} model")
        except OSError:
            spacy.cli.download(model_name)  # type: ignore
            get_nlp_model._nlp = spacy.load(model_name)
            print(f"Downloaded and loaded {model_name} model")

    return get_nlp_model._nlp


def extract_named_entities(text: str) -> list[tuple[str, str]]:
    """Extract named entities from text using spaCy"""
    nlp = get_nlp_model()
    doc = nlp(text)
    return [(ent.text, ent.label_) for ent in doc.ents]


INTERESTING_NER_LABELS = {
    "PERSON",
    "GPE",
    "LOC",
    "LANGUAGE",
    "EVENT",
    "ORG",
    "NORP",
    "WORK_OF_ART",
    "PRODUCT",
    "FAC",
    "LAW",
}
UNINTERESTING_NER_LABELS = {
    # These probably don't have much relevance
    "CARDINAL",
    "DATE",
    "QUANTITY",
    "ORDINAL",
    "TIME",
    "MONEY",
    "PERCENT",
}
ALL_NER_LABELS = INTERESTING_NER_LABELS | UNINTERESTING_NER_LABELS


def overlapping_ner_features(text1, text2) -> float:
    ents1 = set(extract_named_entities(text1))
    ents2 = set(extract_named_entities(text2))
    all_labels = {label for _, label in ents1 | ents2}
    assert not all_labels - ALL_NER_LABELS

    valid_ents1 = {
        (text, label) for text, label in ents1 if label in INTERESTING_NER_LABELS
    }
    valid_ents2 = {
        (text, label) for text, label in ents2 if label in INTERESTING_NER_LABELS
    }

    common = valid_ents1 & valid_ents2

    # Normalize by average text length (in words)
    word_count1 = len(text1.split())
    word_count2 = len(text2.split())
    avg_word_count = (word_count1 + word_count2) / 2

    if avg_word_count == 0:
        return 0.0

    # Return overlap count per 100 words (makes numbers more interpretable)
    return (len(common) / avg_word_count) * 100


def get_tmdb_features(
    showtime: EnrichedShowTime,
    tmdb_details: dict,
    images_cache: Path,
) -> TmdbItemFeatures:
    """Calculate cosine similarity score between text and image embeddings"""

    description_embedding = get_sentence_embedding(showtime.description)
    tmdb_overview_embedding = get_sentence_embedding(tmdb_details["overview"])
    overview_similarity = torch.nn.functional.cosine_similarity(
        description_embedding, tmdb_overview_embedding, dim=0
    ).item()

    overlapping_ner_count = overlapping_ner_features(
        showtime.description, tmdb_details["overview"]
    )

    showtime_image_src = showtime.thumbnail
    showtime_image_embedding = None
    if showtime_image_src:
        image_src_path = images_cache / showtime_image_src
        if image_src_path.exists():
            im = Image.open(image_src_path)
            showtime_image_embedding = get_clip_embedding(im)
        else:
            print("Does not exist:", image_src_path)

    if showtime_image_embedding is None:
        max_image_similarity = 0
    else:
        # print("Checking result:", result)
        poster_path = tmdb_details["poster_path"]
        backdrop_path = tmdb_details["backdrop_path"]
        poster_similarity = None
        backdrop_similarity = None

        if poster_path:
            im = tmdb_image_from_path(poster_path)
            poster_embedding = get_clip_embedding(im)
            poster_similarity = torch.nn.functional.cosine_similarity(
                showtime_image_embedding, poster_embedding
            )
        if backdrop_path:
            im = tmdb_image_from_path(backdrop_path)
            backdrop_embedding = get_clip_embedding(im)
            backdrop_similarity = torch.nn.functional.cosine_similarity(
                showtime_image_embedding, backdrop_embedding
            )
        max_image_similarity = max(
            poster_similarity.item() if poster_similarity is not None else 0,
            backdrop_similarity.item() if backdrop_similarity is not None else 0,
        )

    print(f"Max image similarity: {max_image_similarity}")

    release_date = tmdb_details["release_date"]

    is_recent = False
    if release_date:
        release_year = int(release_date.split("-")[0])
        is_recent = release_year >= last_year
    else:
        release_year = None
        is_recent = False

    return TmdbItemFeatures(
        tmdb_id=tmdb_details["id"],
        overview_embed_similarity=overview_similarity,
        overview_ner_similarity=overlapping_ner_count,
        image_embed_similarity=max_image_similarity,
        release_year=release_year or showtime.release_year,
        vote_count=tmdb_details["vote_count"],
        vote_average=tmdb_details["vote_average"],
        runtime=tmdb_details["runtime"],
        has_description=bool(tmdb_details["overview"]),
        is_recent=is_recent,
        popularity=tmdb_details["popularity"],
        video=tmdb_details["video"],
    )


def get_best_tmdb_match(showtime: EnrichedShowTime, images_cache: Path) -> dict | None:
    """Find the best TMDB match for a showtime data entry"""
    if showtime.release_year:
        # It turns out the release year isn't super-reliable. Let's also try adjacent years
        tmdb_results = (
            search_tmdb_by_title(title=showtime.norm_title, year=showtime.release_year)
            + search_tmdb_by_title(
                title=showtime.norm_title, year=showtime.release_year - 1
            )
            + search_tmdb_by_title(
                title=showtime.norm_title, year=showtime.release_year + 1
            )
        )
    else:
        tmdb_results = search_tmdb_by_title(title=showtime.norm_title)

    # Discard any results that don't have a title (which seems to happen)
    tmdb_results = [r for r in tmdb_results if r["title"].strip()]

    # Let's discard anyhing that isn't an exact title match
    tmdb_results_filtered = [
        r for r in tmdb_results if normalize_title(r["title"]) == showtime.norm_title
    ]
    if tmdb_results_filtered == [] and showtime.release_year:
        # If we have no results but we have the year, let's try again but
        # without constraining to identical titles
        tmdb_results_filtered = tmdb_results

    if tmdb_results_filtered == []:
        print(
            f"No TMDB results found for {showtime.norm_title} ({showtime.release_year})"
        )
        return None

    results_with_scores = []
    for tmdb_result in tmdb_results_filtered:
        tmdb_id = tmdb_result["id"]
        tmdb_details = get_tmdb_movie_details(tmdb_id)
        print(tmdb_details)

        tmdb_features = get_tmdb_features(showtime, tmdb_details, images_cache)
        print("features:", tmdb_features)
        similarity_score = tmdb_features.get_score()
        print(f"Similarity score for {showtime.norm_title}: {similarity_score}")
        tmdb_result["similarity_score"] = similarity_score
        tmdb_result["features"] = tmdb_features
        results_with_scores.append(tmdb_result)

    results_with_scores.sort(key=lambda x: x["similarity_score"], reverse=True)
    results_with_scores[0][
        "is_correct"
    ] = True  # For now let's assume the best match is correct

    with database_connection() as conn:
        cursor = conn.cursor()
        rows_to_insert = [
            (
                showtime.norm_title,
                result["features"].tmdb_id,
                result["features"].overview_embed_similarity,
                result["features"].overview_ner_similarity,
                result["features"].image_embed_similarity,
                result["features"].release_year,
                result["features"].is_recent,
                result["features"].vote_count,
                result["features"].vote_average,
                result["features"].popularity,
                result["features"].video,
                result["features"].runtime,
                result["features"].has_description,
                result.get("is_correct", False),
            )
            for result in results_with_scores
        ]
        cursor.executemany(
            "INSERT INTO tmdb_features (norm_title, tmdb_id, overview_embed_similarity, "
            "overview_ner_similarity, image_embed_similarity, release_year, is_recent, "
            "vote_count, vote_average, popularity, video, runtime, has_description, is_correct) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows_to_insert,
        )
        conn.commit()

    return results_with_scores[0]
