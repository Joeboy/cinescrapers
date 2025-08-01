import datetime
import os
from io import BytesIO
from pathlib import Path

import clip
import requests
import torch
from PIL import Image
from rich import print
from sentence_transformers import SentenceTransformer

from cinescrapers.title_normalization import normalize_title
from cinescrapers.cinescrapers_types import EnrichedShowTime, ShowTime

TMDB_API_KEY = os.environ["TMDB_API_KEY"]
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_PATH = Path(__file__).parent / "tmdb_images"
TMDB_IMAGE_PATH.mkdir(exist_ok=True)
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


def search_tmdb_by_title(title, year=None) -> list[dict]:
    """Search TMDB for a movie by title and optional year"""
    search_url = f"{TMDB_BASE_URL}/search/movie"
    params = {"api_key": TMDB_API_KEY, "query": title}

    if year:
        params["year"] = year

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
            print(f"Found {len(response_data['results'])} results on page {page}")
            results.extend(response_data["results"])

    return results


def get_tmdb_movie_details(tmdb_id) -> dict:
    """Get detailed movie information from TMDB by movie ID"""
    details_url = f"{TMDB_BASE_URL}/movie/{tmdb_id}"
    params = {"api_key": TMDB_API_KEY}

    response = requests.get(details_url, params=params)
    response.raise_for_status()
    return response.json()


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


def get_similarity_score(
    showtime: EnrichedShowTime, tmdb_data: dict, images_cache: Path
) -> float:
    """Calculate cosine similarity score between text and image embeddings"""

    description_embedding = get_sentence_embedding(showtime.description)
    tmdb_overview_embedding = get_sentence_embedding(tmdb_data["overview"])
    overview_similarity = torch.nn.functional.cosine_similarity(
        description_embedding, tmdb_overview_embedding, dim=0
    ).item()

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
        poster_path = tmdb_data.get("poster_path")
        backdrop_path = tmdb_data.get("backdrop_path")
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
        print(f"Poster similarity: {poster_similarity}")
        print(f"Backdrop similarity: {backdrop_similarity}")
        max_image_similarity = max(
            poster_similarity.item() if poster_similarity is not None else 0,
            backdrop_similarity.item() if backdrop_similarity is not None else 0,
        )

    print(f"Max image similarity: {max_image_similarity}")

    # Increase points if films have similar overviews:
    if overview_similarity > 0.2:
        overview_similarity_points = (overview_similarity - 0.2) * 1.0 / 0.8
    else:
        overview_similarity_points = 0.0
    print(f"Adding {overview_similarity_points} points for overview similarity")

    # increase points if either image is similar to the showtime image:
    if max_image_similarity > 0.65:
        image_similarity_points = (max_image_similarity - 0.65) * 1.0 / 0.35
    else:
        image_similarity_points = 0.0
    print(f"Adding {image_similarity_points} points for image similarity")

    release_date = tmdb_data.get("release_date")
    recency_points = 0.0
    if release_date:
        release_year = int(release_date.split("-")[0])
        if release_year >= last_year:
            # If it's a recent film, that makes it more likely to be showing
            recency_points = 0.05
    print(f"Adding {recency_points} points for recency")

    return (
        overview_similarity_points + image_similarity_points + recency_points
    ) / 2.05


def get_best_tmdb_match(showtime: EnrichedShowTime, images_cache: Path) -> dict | None:
    """Find the best TMDB match for a showtime data entry"""
    tmdb_results = search_tmdb_by_title(showtime.norm_title)

    # Discard any results that don't have a title (which seems to happen)
    tmdb_results = [r for r in tmdb_results if r["title"].strip()]

    # Let's discard anyhing that isn't an exact title match
    tmdb_results = [
        r for r in tmdb_results if normalize_title(r["title"]) == showtime.norm_title
    ]
    if len(tmdb_results) == 0:
        return None
    results_with_scores = []
    for tmdb_result in tmdb_results:
        similarity_score = get_similarity_score(showtime, tmdb_result, images_cache)
        print(f"Similarity score for {showtime.norm_title}: {similarity_score}")
        tmdb_result["similarity_score"] = similarity_score
        results_with_scores.append(tmdb_result)

    results_with_scores.sort(key=lambda x: x["similarity_score"], reverse=True)
    return results_with_scores[0]
