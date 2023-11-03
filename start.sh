#!/bin/sh
flask db upgrade
exec gunicorn -b :8080 --workers 4 --worker-class gevent "app:create_app()"
