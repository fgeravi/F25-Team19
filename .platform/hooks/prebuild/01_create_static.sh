#!/bin/bash
set -e

# Make sure staticfiles directory exists
mkdir -p /var/app/staging/staticfiles
chmod 755 /var/app/staging/staticfiles

# Activate the virtual environment
source /opt/python/run/venv/bin/activate

# Run collectstatic using the environment variables already set in EB
python manage.py collectstatic --noinput

echo "Collectstatic finished successfully!"