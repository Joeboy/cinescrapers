"""Just a little dev server for serving the data locally for testing purposes"""

from pathlib import Path
from flask import Flask, send_file, send_from_directory

THUMBNAILS_DIR = (
    Path(__file__).parent / "src" / "cinescrapers" / "scraped_images" / "thumbnails"
)

app = Flask(__name__)


@app.route("/cinescrapers.json")
def serve_showtimes():
    path = Path(__file__).parent / "src" / "cinescrapers" / "cinescrapers.json"
    response = send_file(path, mimetype="application/json")
    response.headers["Content-Type"] = "application/json"
    response.headers["Content-Encoding"] = "gzip"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@app.route("/cinemas.json")
def serve_cinemas():
    path = Path(__file__).parent / "src" / "cinescrapers" / "cinemas.json"
    response = send_file(path, mimetype="application/json")
    response.headers["Content-Type"] = "application/json"
    response.headers["Content-Encoding"] = "gzip"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@app.route("/thumbnails/<path:filename>")
def serve_thumbnail(filename):
    return send_from_directory(THUMBNAILS_DIR, filename)


app.run(host="0.0.0.0", port=8080)
