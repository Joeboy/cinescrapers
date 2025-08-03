"""Just a little dev server for serving the data locally for testing purposes"""

import sqlite3
from pathlib import Path

import pandas as pd
from flask import Flask, send_file, send_from_directory
from ydata_profiling import ProfileReport

THUMBNAILS_DIR = (
    Path(__file__).parent / "src" / "cinescrapers" / "scraped_images" / "thumbnails"
)

app = Flask(__name__)


@app.route("/cinescrapers.json")
def serve_showtimes():
    path = Path(__file__).parent / "src" / "cinescrapers" / "cinescrapers.json"
    response = send_file(path, mimetype="application/json")
    response.headers["Content-Type"] = "application/json"
    # response.headers["Content-Encoding"] = "gzip"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@app.route("/cinemas.json")
def serve_cinemas():
    path = Path(__file__).parent / "src" / "cinescrapers" / "cinemas.json"
    response = send_file(path, mimetype="application/json")
    response.headers["Content-Type"] = "application/json"
    # response.headers["Content-Encoding"] = "gzip"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@app.route("/tmdb_recommendations.json")
def serve_tmdb_recommendations():
    path = (
        Path(__file__).parent
        / "src"
        / "cinescrapers"
        / "data"
        / "tmdb_recommendations.json"
    )
    response = send_file(path, mimetype="application/json")
    response.headers["Content-Type"] = "application/json"
    # response.headers["Content-Encoding"] = "gzip"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@app.route("/thumbnails/<path:filename>")
def serve_thumbnail(filename):
    return send_from_directory(THUMBNAILS_DIR, filename)


@app.route("/stats")
def serve_stats():
    DB_PATH = Path(__file__).parent.parent / "showtimes.db"
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query("SELECT * FROM showtimes", conn)
    profile = ProfileReport(df, title=f"Data Profile", minimal=True)
    return profile.to_html(), 200


app.run(host="0.0.0.0", port=8080)
