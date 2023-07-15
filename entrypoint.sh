#!/bin/bash

redis-server --daemonize yes

cd flask

celery -A server.celery_app worker --detach --loglevel=info \
    --pidfile="/run/celery.pid" \
    --logfile="/log/celery/celery.log"

python3 server.py