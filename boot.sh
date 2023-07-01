#!/bin/sh
flask db upgrade
exec gunicorn -b :8080 --workers 4 "app:create_app()"