"""Just a little dev server for serving the data locally for testing purposes"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import sqlite3

import pandas as pd
from flask import Flask, send_file, send_from_directory
from ydata_profiling import ProfileReport

from cinescrapers.config import (
    CINEMAS_JSON,
    DB_PATH,
    SHOWTIMES_JSON,
    THUMBNAILS_FOLDER,
    TMDB_RECOMMENDATIONS_FILTERED,
)

app = Flask(__name__)


@app.route("/cinescrapers.json")
def serve_showtimes():
    response = send_file(SHOWTIMES_JSON, mimetype="application/json")
    response.headers["Content-Type"] = "application/json"
    # response.headers["Content-Encoding"] = "gzip"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@app.route("/cinemas.json")
def serve_cinemas():
    response = send_file(CINEMAS_JSON, mimetype="application/json")
    response.headers["Content-Type"] = "application/json"
    # response.headers["Content-Encoding"] = "gzip"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@app.route("/tmdb_recommendations.json")
def serve_tmdb_recommendations():
    response = send_file(TMDB_RECOMMENDATIONS_FILTERED, mimetype="application/json")
    response.headers["Content-Type"] = "application/json"
    # response.headers["Content-Encoding"] = "gzip"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@app.route("/thumbnails/<path:filename>")
def serve_thumbnail(filename):
    return send_from_directory(THUMBNAILS_FOLDER, filename)


@app.route("/stats")
def serve_stats():
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query("SELECT * FROM showtimes", conn)
    profile = ProfileReport(df, title="Data Profile", minimal=True)
    return profile.to_html(), 200


app.run(host="0.0.0.0", port=8080)
