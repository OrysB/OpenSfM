import argparse
import logging;
from os.path import (
    join,
    isfile,
    relpath
)

from os import (
    walk
)

import subprocess

from typing import List

from flask import (
    Flask,
    abort,
    Response,
    send_file,
    jsonify
)


app = Flask(__name__, static_folder="./", static_url_path="")


DATA = "../data"
IMAGES = "images"


@app.route("/<path:dataset>/viewer", )
def open_viewer(dataset) -> Response:
    return send_file(join(app.static_folder, "index.html"))


@app.route("/<path:dataset>/recs")
def get_recs(dataset) -> Response:
    reconstructions = [
        {
            "children": [],
            "name": rec,
            "type": "RECONSTRUCTION",
            "url": [join("/", "data", dataset, rec)],
        }
        for rec in reconstruction_files(join(DATA, dataset))
    ]

    return jsonify({ "recs": reconstructions})


@app.route("/data/<path:dataset>/<path:subpath>")
def get_data(dataset, subpath) -> Response:
    return verified_send(join(DATA, dataset, subpath))

@app.route("/static/<path:subpath>")
def get_static(subpath) -> Response:
    return verified_send(join(app.static_folder, subpath))

@app.route("/<path:dataset>/image/<shot_id>")
def get_image(dataset, shot_id) -> Response:
    path = join(DATA, dataset, IMAGES, shot_id)
    return verified_send(path)


def json_files(path) -> List[str]:
    """List all json files under a dir recursively."""
    found = []
    logging.warning(path)
    for root, _, files in walk(path):
        for file in files:
            if ".json" in file:
                found.append(file)
    return found


def probably_reconstruction(file) -> bool:
    """Decide if a path may be a reconstruction file."""
    return file.endswith("json") and "reconstruction" in file


def reconstruction_files(path) -> List[str]:
    """List all files that look like a reconstruction."""
    files = json_files(path)
    return sorted(filter(probably_reconstruction, files))


def verified_send(file) -> Response:
    if isfile(file):
        return send_file(file)
    else:
        # pyre-fixme[7]: Expected `Response` but got implicit return value of `None`.
        abort(404)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-p", "--port", type=int, default=8080, help="port to bind server to"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    return app.run(host="::", port=args.port)


if __name__ == "__main__":
    exit(main())
