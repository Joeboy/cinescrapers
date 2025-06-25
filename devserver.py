"""Just a little dev server for serving the data locally for testing purposes"""

from pathlib import Path
from flask import Flask, send_file

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


app.run(host="0.0.0.0", port=8080)
