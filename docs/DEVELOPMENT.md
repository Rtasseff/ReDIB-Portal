# Development Guide

This guide contains common development workflows and procedures for ReDIB-Portal contributors.

## Table of Contents

- [Quick Database Setup](#quick-database-setup)
- [Database Management](#database-management)
- [Data Loading](#data-loading)
- [Development Server](#development-server)
- [Common Commands](#common-commands)

## Quick Database Setup

The fastest way to set up a complete development/test database:

```bash
# Complete reset and seed with all test data (recommended)
python manage.py setup_test_database --reset --yes

# Or just seed without reset (if database is already empty)
python manage.py setup_test_database
```

This single command:
1. Clears all data except superusers (with `--reset`)
2. Populates ReDIB nodes (4 nodes)
3. Populates equipment (17 items)
4. Populates users (coordinators, evaluators, node coordinators)
5. Seeds development data (calls, organizations)
6. Seeds email templates
7. Creates test applicants with applications in various workflow stages

**Test accounts created** (password: `testpass123`):
- `testapplicant1@test.redib.net` through `testapplicant5@test.redib.net`
- Applications at different stages: draft, submitted, under review, evaluated, accepted, etc.

See [TEST_APPLICANTS_GUIDE.md](docs/TEST_APPLICANTS_GUIDE.md) for complete test data documentation.

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
# Complete test database setup (recommended - runs all seed scripts)
python manage.py setup_test_database --reset --yes

# Or seed just the test applicants (if base data already exists)
python manage.py seed_test_applicants --clear

# Or seed just development data (calls, orgs)
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

# 3. Load ALL data with one command (recommended)
python manage.py setup_test_database

# OR load data manually in order:
# python manage.py seed_email_templates
# python manage.py populate_redib_nodes
# python manage.py populate_redib_users
# python manage.py populate_redib_equipment
# python manage.py seed_dev_data
# python manage.py seed_test_applicants

# 4. Start server
python manage.py runserver
```

## Related Documentation

- [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md) - Initial project setup and configuration
- [docs/TESTING.md](docs/TESTING.md) - Testing procedures and guidelines
- [docs/TEST_APPLICANTS_GUIDE.md](docs/TEST_APPLICANTS_GUIDE.md) - Test data documentation
- [docs/USER_GUIDE.md](docs/USER_GUIDE.md) - End-user guide for portal users
- [README.md](README.md) - Project overview and features
