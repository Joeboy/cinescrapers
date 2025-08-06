import json
import sqlite3
import time
from pathlib import Path

import humanize
from rich import print

from cinescrapers.cinescrapers_types import EnrichedShowTime
from cinescrapers.config import (
    DB_PATH,
    IMAGES_CACHE,
    TMDB_ID_CACHE,
    TMDB_RECOMMENDATIONS_CACHE,
)
from cinescrapers.database import database_connection
from cinescrapers.title_normalization import normalize_title
from cinescrapers.utils import get_hashed
from cinescrapers.xmdb_integration.api import (
    get_tmdb_movie_details,
    get_tmdb_recommendations,
    search_tmdb_by_title,
)
from cinescrapers.xmdb_integration.feature_engineering import get_tmdb_features


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
        # print(tmdb_details)

        tmdb_features = get_tmdb_features(showtime, tmdb_details, images_cache)
        # print("features:", tmdb_features)
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
                showtime.id,
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
            "INSERT INTO tmdb_features (norm_title, tmdb_id, showtime_id, overview_embed_similarity, "
            "overview_ner_similarity, image_embed_similarity, release_year, is_recent, "
            "vote_count, vote_average, popularity, video, runtime, has_description, is_correct) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows_to_insert,
        )
        conn.commit()

    return results_with_scores[0]


def grab_tmdb_ids():
    """Grab TMDB IDs for all showtimes"""
    t1 = time.perf_counter()
    tmdb_id_cache = json.loads(TMDB_ID_CACHE.read_text())
    with database_connection() as conn:
        cursor = conn.cursor()
        # cursor.execute("UPDATE showtimes SET tmdb_id = NULL")
        cursor.execute("SELECT * FROM showtimes")
        rows = cursor.fetchall()
        num_showtimes = len(rows)
        num_found = 0
        for i, row in enumerate(rows, start=1):
            print(f"{i} of {num_showtimes}, {row['title']}")
            showtime = EnrichedShowTime(**row)

            movie_hash = showtime.movie_hash()
            print(f"{showtime.norm_title} -> {movie_hash}")

            if showtime.tmdb_id:
                print("Skipping, db already has TMDB ID")
                # The tmdb_id for this db row is already in the db
                num_found += 1
                continue
            if movie_hash in tmdb_id_cache.keys():
                print(f"'{showtime.norm_title}' Found in file cache")
                showtime_tmdb_id = tmdb_id_cache[movie_hash]
            else:
                print(
                    f"'{showtime.norm_title}' Not found in file cache, searching TMDB"
                )
                conn.commit()  # Avoid locked db error in get_best_tmdb_match()
                best_match = get_best_tmdb_match(showtime, IMAGES_CACHE)
                if best_match:
                    showtime_tmdb_id = best_match["id"]
                else:
                    showtime_tmdb_id = None
            if showtime_tmdb_id:
                num_found += 1
                print(
                    f"Found TMDB https://www.themoviedb.org/movie/{showtime_tmdb_id} for {showtime.norm_title}"
                )
                cursor.execute(
                    "UPDATE showtimes SET tmdb_id = ? WHERE id = ?",
                    (showtime_tmdb_id, showtime.id),
                )
                tmdb_id_cache[movie_hash] = showtime_tmdb_id

            if not i % 100:
                cursor.connection.commit()
                print("writing file cache")
                TMDB_ID_CACHE.write_text(json.dumps(tmdb_id_cache, indent=2))

        TMDB_ID_CACHE.write_text(json.dumps(tmdb_id_cache, indent=2))
        cursor.connection.commit()
    print(
        f"Found {num_found} TMDB IDs of {num_showtimes} showtimes ({num_found / num_showtimes * 100:.2f}%) in {humanize.naturaldelta(time.perf_counter() - t1)}."
    )
