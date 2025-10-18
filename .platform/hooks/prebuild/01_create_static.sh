#!/bin/bash
set -e

# Make sure staticfiles folder exists
mkdir -p /var/app/staging/staticfiles
chmod 755 /var/app/staging/staticfiles

# Activate virtual environment
source /opt/python/run/venv/bin/activate

# Collect static files
python manage.py collectstatic --noinput
