# OpenSfM viewer

## Workflow

### Setup

1. `./node_modules.sh`
   - Download npm dependencies from unpkg

### Serve datasets

1. Run `python3 server.py` from flask dir
   - Serve the reconstructions for datasets
2. Browse to `http://localhost:8080/<path:dataset>/viewer`
   - Where `dataset` is the path to the dataset (e.g. `berlin`, `lund` or `mapillary/qube`)
3. Select the reconstruction file
4. to use extended api (execution of commands via flask)
   - run `celery -A flask/server.celery_app worker --loglevel=info` in ./flask

### Load datasets manually

Note that images will not be loaded for this case.

1. `python3 server.py`
   - Serve the reconstruction for a dataset
2. Browse to `http://localhost:8080`
3. Pick or drop the reconstruction files
