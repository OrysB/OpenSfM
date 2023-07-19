# OpenSfM viewer

## Workflow

### Setup

1. `./node_modules.sh`
   - Download npm dependencies from unpkg

### Serve datasets

1. Run `python3 ./flask/server.py`
   - Serve the reconstructions for datasets
2. Browse to `http://localhost:8080/<path:dataset>/viewer`
   - Where `dataset` is the path to the dataset (e.g. `berlin`, `lund` or `mapillary/qube`)
3. Select the reconstruction file

### Extended API

1. run `cd flask && celery -A flask/server.celery_app worker --loglevel=info`
   - Start the celery worker
2. make sure you started the flask server
3. access the api:
   - run a task: POST `localhost:8080/<path:dataset>/run` (BODY (e.G.): { "command": "all" }, { "command": "extract_metadata" }, ...)
   - list running tasks: GET `localhost:8080/,path:dataset>/tasks`
   - check status of a running task: GET `/<path:dataset>/status/<task_id>`

### Load datasets manually

Note that images will not be loaded for this case.

1. `python3 server.py`
   - Serve the reconstruction for a dataset
2. Browse to `http://localhost:8080`
3. Pick or drop the reconstruction files
