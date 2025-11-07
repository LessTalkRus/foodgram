#!/bin/bash
sleep 5

python manage.py collectstatic
cp -r /app/collected_static/. /backend_static/static/
python manage.py makemigrations
python manage.py migrate

python manage.py backfill ingredients.json

gunicorn backend.wsgi:application --bind 0:8000