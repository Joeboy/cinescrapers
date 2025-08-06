"""Functions for extracting features from showtimes and TMDB data, so we can match them to TMDB IDs."""

import datetime
from pathlib import Path

import clip
import torch
from PIL import Image
from rich import print
from sentence_transformers import SentenceTransformer

from cinescrapers.cinescrapers_types import EnrichedShowTime, TmdbItemFeatures
from cinescrapers.xmdb_integration.api import tmdb_image_from_path

last_year = datetime.datetime.now().year - 1


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
