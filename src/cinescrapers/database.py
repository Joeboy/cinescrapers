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
            )
        """
        )

        conn.commit()
