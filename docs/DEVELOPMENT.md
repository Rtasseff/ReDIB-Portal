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
If you want others to see it at biomaGUNE
```bash
python manage.py runserver 0.0.0.0:8000
PS C:\Users\rtasseff> python .\tcp_forward.py --target-host 172.26.220.46 --target-port 8000 --listen-host 0.0.0.0 --listen-port 8000
```

Access points:
- **Application**: http://localhost:8000
- **Admin Interface**: http://localhost:8000/admin

## Email Templates

### Seeding Templates

Email templates are loaded into the database from `seed_email_templates.py`:

```bash
python manage.py seed_email_templates
```

This is also run automatically during deployment via the Docker entrypoint.

### Testing All Templates

Send all 15 templates to a single recipient to verify rendering and links:

```bash
# Send test emails
python manage.py send_test_emails --to your-email@example.com

# Clean up test data afterward
python manage.py send_test_emails --cleanup
```

See [docs/TEST_EMAIL_TEMPLATES.md](docs/TEST_EMAIL_TEMPLATES.md) for full details on what is created and how to verify.

### Contact Email

The contact email used across all templates is configured in `redib/settings.py`:

```python
CONTACT_EMAIL = env('CONTACT_EMAIL', default='info@redib.net')
```

This is automatically injected into every template as `{{ contact_email }}`. To change it, update the setting or set `CONTACT_EMAIL` in your `.env` file.

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

## System Dependencies for PDF Generation

The portal uses WeasyPrint to generate PDF documents for application signing. WeasyPrint requires certain system libraries to be installed.

### Ubuntu/Debian

```bash
sudo apt-get install -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-dejavu-core \
    fonts-liberation
```

### macOS (Homebrew)

```bash
brew install pango cairo gdk-pixbuf libffi
```

### Windows (WSL recommended)

For Windows development, we recommend using WSL2 with Ubuntu. Install the Ubuntu dependencies listed above within WSL.

### Docker

The Dockerfile already includes all required dependencies. No additional setup needed when using Docker.

### Verifying PDF Generation

After installing dependencies, you can test PDF generation:

```bash
# Start the development server
python manage.py runserver

# Create a test application and navigate to the preview page
# Click "Download Application PDF" to test PDF generation
```

If you encounter errors like "Pango" or "Cairo" not found, ensure the system dependencies are properly installed.

## Related Documentation

- [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md) - Initial project setup and configuration
- [docs/TESTING.md](docs/TESTING.md) - Testing procedures and guidelines
- [docs/TEST_APPLICANTS_GUIDE.md](docs/TEST_APPLICANTS_GUIDE.md) - Test data documentation
- [docs/TEST_EMAIL_TEMPLATES.md](docs/TEST_EMAIL_TEMPLATES.md) - Email template testing guide
- [docs/USER_GUIDE.md](docs/USER_GUIDE.md) - End-user guide for portal users
- [README.md](README.md) - Project overview and features
