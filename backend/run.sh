#!/bin/bash
sleep 5

python manage.py collectstatic
cp -r /app/collected_static/. /backend_static/static/
python manage.py migrate

gunicorn backend.wsgi:application --bind 0:8000