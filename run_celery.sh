#!/bin/bash

cd flask

celery -A server.celery_app worker --loglevel=info