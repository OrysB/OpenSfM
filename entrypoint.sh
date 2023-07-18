#!/bin/bash

redis-server --daemonize yes

chmod +x ./run_celery.sh
chmod +x ./run_flask.sh

sh ./run_celery.sh & PID_CELERY=$!
sh ./run_flask.sh & PID_FLASK=$!

wait $PID_CELERY
wait $PID_FLASK
