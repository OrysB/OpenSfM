import argparse
from dotenv import load_dotenv

from celery import Celery, Task, shared_task
from celery.result import AsyncResult
from subprocess import Popen
from werkzeug.utils import secure_filename

import os
from os import (
    walk
)
from os.path import (
    join,
    isfile
)
import fnmatch

from typing import List

from flask import (
    Flask,
    abort,
    Response,
    send_file,
    jsonify,
    request,
    redirect,
)

import uuid
import time

load_dotenv()

ROOT_DIR = os.getenv("ROOT_DIR")
DATA_DIR = os.getenv("DATA_DIR")
DATA = join(ROOT_DIR, DATA_DIR)
IMAGES = os.getenv("IMAGES_DIR")

COMMAND_LIST = ["all", "extract_metadata", "detect_features", "match_features", "create_tracks", "reconstruct", "mesh", "undistort", "compute_depthmaps"]
ALLOWED_IMAGE_FORMATS = ['png', 'jpg']

def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app

app = Flask(__name__, static_folder="./", static_url_path="")
app.secret_key = os.getenv("SECRET_KEY")
app.config.from_mapping(
    CELERY=dict(
        broker_url=os.getenv("CELERY_BROKER_URL"),
        result_backend=os.getenv("CELERY_RESULT_BACKEND")
    ),
)
celery_app = celery_init_app(app)

@shared_task(bind = True, ignore_result=False, track_started=True)
def sfm_background(self, dataset, command, task_id):
    path = join(ROOT_DIR, DATA, dataset, "logs", task_id+".txt");
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w+') as logFile:
        try:
            task = Popen("bash "+join(ROOT_DIR,"bin", command)+" "+join(DATA, dataset), stdout=logFile, stderr=logFile, shell=True)
            self.update_state(state="PROGRESS",
                            meta={'code': 102 })
            while task.poll() is None:
                time.sleep(5)
                self.update_state(state="PROGRESS",
                                meta={'code': 200 })
            else:
                if task.returncode == 0:
                    self.update_state(state="SUCCESS",
                                    meta={'code': 200 })
                else:
                    self.update_state(state="FAILURE",
                                    meta={'code': 400 })
        except Exception as e:
            self.update_state(state="FAILURE",
                            meta={'code': 500 })
            logFile.write(str(e))

@app.route("/<path:dataset>/run", methods = ["POST"])
def run(dataset) -> Response:
    req_json = request.get_json();
    if req_json is None or "command" not in req_json:
        abort(400, description="missing command")

    if req_json["command"] not in COMMAND_LIST:
        abort(400, description="command not supported")

    command = "opensfm_run_all"

    if req_json["command"] != "all":
        command = "opensfm " + req_json["command"]

    last = AsyncResult(dataset)
    if last.state == "PROGRESS":
        return redirect("status", code=302)
    task_id = str(uuid.uuid1())
    sfm_background.apply_async((dataset, command, task_id), task_id = task_id)
    return redirect(join("status", task_id), code=302)

@app.route("/<path:dataset>/tasks")
def get_status_all(dataset) -> Response:
    path = join(DATA, dataset, "logs");
    if not os.path.isdir(path):
         return 'NOT FOUND', 404
    task_ids = []
    for file in os.listdir(path):
        if fnmatch.fnmatch(file, '*.txt'):
            task_ids.append(file.replace('.txt', ''))
    return task_ids

@app.route("/<path:dataset>/status/<task_id>", methods =["GET"])
def get_status(dataset, task_id) -> Response:
        task = AsyncResult(task_id)        
       
        logsPath = join(ROOT_DIR, DATA, dataset, "logs", task_id + ".txt")
        response = {
            'code': 102,
            'state': task.state,
        }
        # unknown tasks will return with state "PENDING" (see celery documentation)
        if task.state == "PENDING":
                #finished processes that might have run before a restart of celery, will have left their log file
                try:
                    with open(logsPath, "r") as logFile:
                        response = {
                            'code': 200,
                            'state': "EXPIRED",
                            'logs': "\n".join(logFile.readlines())
                        }
                except Exception as e:
                    return 'NOT FOUND', 404
        elif task.state == "PROGRESS":
                if not os.path.isfile(logsPath):
                    response = {
                        'code': task.info.get('code', 102),
                        'state': task.state,
                    }
                else:
                    with open(logsPath, "r") as logFile:  
                        response = {
                            'code': task.info.get('code', 102),
                            'state': task.state,
                            'logs': "\n".join(logFile.readlines())
                        }
        elif task.state == "SUCCESS":
                with open(logsPath, "r") as logFile:  
                    response = {
                        'code': task.info.get('code', 102),
                        'state': task.state,
                        'logs': "\n".join(logFile.readlines())
                    }
        elif task.state == "FAILURE":
                with open(logsPath, "r") as logFile:  
                    response = {
                        'code': task.info.get('code', 102),
                        'state': task.state,
                        'logs': "\n".join(logFile.readlines())
                    }
        return jsonify(response)

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

@app.route("/<path:dataset>/image/<shot_id>", methods =["GET"])
def get_image(dataset, shot_id) -> Response:
    path = join(DATA, dataset, IMAGES, shot_id)
    return verified_send(path)

@app.route("/<path:dataset>/image", methods =["POST"])
def post_image(dataset) -> Response:
    if 'file' not in request.files:
            return 'missing file', 400
    file = request.files['file']
    if file.filename == '':
            return 'missing filename', 400
    if file.filename.split('.')[-1] not in ALLOWED_IMAGE_FORMATS:
            return 'file format not supported', 400
    filename = secure_filename(file.filename)
    path = join(DATA, dataset, IMAGES, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    file.save(path)
    return redirect(join("image", filename)), 301


def json_files(path) -> List[str]:
    """List all json files under a dir recursively."""
    found = []
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
