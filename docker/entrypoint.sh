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

echo "Configuring site..."
python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redib.settings')
django.setup()
from django.contrib.sites.models import Site
site = Site.objects.get(id=1)
site.domain = os.environ.get('SITE_DOMAIN', 'portal.redib.net')
site.name = os.environ.get('SITE_NAME', 'ReDIB COA Portal')
site.save()
print(f'  Site: {site.name} ({site.domain})')
"

exec "$@"
