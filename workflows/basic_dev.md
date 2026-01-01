# Basic Development Workflows

## Purgining and repopulating database
# Basic Development Workflows
rm db.sqlite3
find ./applications ./calls ./core ./evaluations ./access ./communications ./reports -path "*/migrations/*.py" -not -name "__init__.py" -delete

python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_email_templates
python manage.py populate_redib_nodes
python manage.py populate_redib_users
python manage.py populate_redib_equipment



