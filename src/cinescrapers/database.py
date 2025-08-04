import sqlite3
from contextlib import contextmanager
from typing import Iterator

from cinescrapers.config import DB_PATH


@contextmanager
def database_connection() -> Iterator[sqlite3.Connection]:
    """
    Context manager for SQLite database connection with row_factory set to sqlite3.Row.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")

    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()


def ensure_database_tables() -> None:
    """
    Create the database tables if they don't exist.

    Args:
        db_path: Path to the SQLite database file
    """
    with database_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS showtimes (
                id TEXT PRIMARY KEY,
                cinema_shortcode TEXT NOT NULL,
                title TEXT NOT NULL,
                norm_title TEXT,
                datetime TEXT NOT NULL,
                link TEXT NOT NULL,
                description TEXT,
                image_src TEXT,
                thumbnail TEXT,
                release_year INTEGER,
                last_updated TEXT NOT NULL,
                scraper TEXT NOT NULL,
                tmdb_id INTEGER
            )"""
        )

        # This represents some features calculated from a possible TMDB match
        # For use in analysis and eventually training a model to match
        # showtimes with TMDB IDs
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tmdb_features (
                norm_title TEXT,
                tmdb_id INTEGER,
                overview_embed_similarity REAL,
                overview_tf_similarity REAL,
                image_embed_similarity REAL,
                is_recent BOOLEAN,
                vote_count integer,
                vote_average REAL,
                is_correct BOOLEAN
            )
        """
        )
