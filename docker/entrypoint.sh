#!/bin/bash
set -e

echo "Waiting for database..."
while ! python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redib.settings')
django.setup()
from django.db import connections
conn = connections['default']
conn.ensure_connection()
" 2>/dev/null; do
    echo "Database unavailable - sleeping 2s"
    sleep 2
done
echo "Database ready."

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Seeding email templates..."
python manage.py seed_email_templates

exec "$@"
