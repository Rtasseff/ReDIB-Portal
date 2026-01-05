# Development Guide

This guide contains common development workflows and procedures for ReDIB-Portal contributors.

## Table of Contents

- [Database Management](#database-management)
- [Data Loading](#data-loading)
- [Development Server](#development-server)
- [Common Commands](#common-commands)

## Database Management

### Complete Database Reset and Repopulation

When you need to completely reset your development database (purge and repopulate):

```bash
# Remove existing database
rm db.sqlite3

# Remove all migration files (except __init__.py)
find ./applications ./calls ./core ./evaluations ./access ./communications ./reports -path "*/migrations/*.py" -not -name "__init__.py" -delete

# Recreate migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

After resetting the database, proceed with [Data Loading](#data-loading).

## Data Loading

### Initial Data Setup

After creating a fresh database, load the required data in the following order:

**IMPORTANT:** Commands must be run in this specific order due to dependencies.

```bash
# 1. Load email templates (no dependencies)
python manage.py seed_email_templates

# 2. Load ReDIB nodes FIRST (required by users and equipment)
python manage.py populate_redib_nodes

# 3. Load users (depends on nodes existing)
python manage.py populate_redib_users

# 4. Load equipment (depends on nodes existing)
python manage.py populate_redib_equipment
```

### Data Loading Dependencies

- `seed_email_templates` - No dependencies, can run anytime
- `populate_redib_nodes` - **MUST run first** - loads 4 nodes from `data/nodes.csv`
- `populate_redib_users` - Requires nodes to exist, loads users from `data/users.csv`
- `populate_redib_equipment` - Requires nodes to exist, loads equipment from `data/equipment.csv`

### Sync Mode

All population commands support `--sync` mode for updating existing data without deleting records:

```bash
# Update nodes without deleting existing data
python manage.py populate_redib_nodes --sync

# Update users without deleting existing data
python manage.py populate_redib_users --sync

# Update equipment without deleting existing data
python manage.py populate_redib_equipment --sync
```

## Development Server

Start the development server after loading data:

```bash
python manage.py runserver
```

Access points:
- **Application**: http://localhost:8000
- **Admin Interface**: http://localhost:8000/admin

## Common Commands

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific test file
python manage.py test tests.test_phase1_phase2_workflow

# Run with verbose output
python manage.py test --verbosity=2
```

See [TESTING.md](TESTING.md) for comprehensive testing documentation.

### Celery (Background Tasks)

For email notifications and background tasks:

```bash
# Start Celery worker
celery -A redib worker -l info

# Start Celery beat (scheduled tasks)
celery -A redib beat -l info
```

### Checking Migrations

```bash
# Check for migration issues
python manage.py makemigrations --check --dry-run

# Show all migrations
python manage.py showmigrations

# Show SQL for a specific migration
python manage.py sqlmigrate core 0001
```

### Creating Test Data

```bash
# Create comprehensive test data (optional)
python manage.py seed_dev_data
```

## Quick Reference: Complete Setup from Scratch

```bash
# 1. Database setup
rm db.sqlite3
find ./applications ./calls ./core ./evaluations ./access ./communications ./reports -path "*/migrations/*.py" -not -name "__init__.py" -delete
python manage.py makemigrations
python manage.py migrate

# 2. Create superuser
python manage.py createsuperuser

# 3. Load data in order
python manage.py seed_email_templates
python manage.py populate_redib_nodes
python manage.py populate_redib_users
python manage.py populate_redib_equipment

# 4. Start server
python manage.py runserver
```

## Related Documentation

- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Initial project setup and configuration
- [TESTING.md](TESTING.md) - Testing procedures and guidelines
- [README.md](README.md) - Project overview and features
- [workflows/basic_dev.md](workflows/basic_dev.md) - Original basic workflow reference
