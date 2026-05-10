#! /bin/bash

python manage.py migrate

gunicorn -c gunicorn.conf.py core.asgi:application

