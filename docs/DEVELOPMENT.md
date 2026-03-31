# Development Guide

This guide contains common development workflows and procedures for ReDIB-Portal contributors.

Development mode uses **Python venv + SQLite** -- no Docker, Redis, or Celery required.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Database Setup](#quick-database-setup)
- [Database Management](#database-management)
- [Data Loading](#data-loading)
- [Development Server](#development-server)
- [Common Commands](#common-commands)

## Prerequisites

Before using any command in this guide, ensure you have:

1. **Python 3.11+** installed
2. **Virtual environment created and activated**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Linux/macOS
   ```
3. **Dependencies installed**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Environment file configured** (copy once, then leave it):
   ```bash
   cp .env.example .env
   ```
   This gives you: SQLite database, `DEBUG=True`, console email backend, `USE_REDIS=False` (in-memory cache). See [SETUP_GUIDE.md](SETUP_GUIDE.md#environment-configuration) for details on all environment variables.
5. **Database initialized**:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

If you haven't done these steps yet, follow [QUICKSTART.md](QUICKSTART.md) for a complete walkthrough.

## Quick Database Setup

### Base Data Only (Real Reference Data)

For a clean database with only real nodes, equipment, users, and email templates — no fake test data:

```bash
# Step 1: Delete the old database and create a fresh one
rm db.sqlite3
python manage.py migrate

# Step 2: Create your superuser (interactive — enter email and password)
python manage.py createsuperuser

# Step 3: Populate real reference data
python manage.py setup_base_database
```

This loads:
- **4 nodes** from `data/nodes.csv`
- **17 equipment items** from `data/equipment.csv` (across all nodes)
- **9 staff users** from `data/users.csv` (coordinator, node coordinators, evaluators)
- **15+ email templates** for all workflow notifications

All CSV users get password `changeme123` and pre-verified email (ready to log in immediately).

If your superuser email matches a row in `data/users.csv`, that user also gets the CSV roles assigned and password set to `changeme123`.

### Base Data + Test Data

For a database that also includes fake calls, applications, and test applicants at various workflow stages:

```bash
python manage.py setup_test_database --reset --yes
```

See [TEST_APPLICANTS_GUIDE.md](TEST_APPLICANTS_GUIDE.md) for test data documentation.

### Soft Reset (Preserve Superuser)

To clear all data except superusers and repopulate without deleting the database file:

```bash
# Base data only
python manage.py setup_base_database --reset --yes

# Or with test data
python manage.py setup_test_database --reset --yes
```

## Database Management

### Complete Database Reset

When you need a fully clean slate (new database file, fresh migrations):

```bash
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
python manage.py setup_base_database
```

**Note:** You do not need to delete or regenerate migration files. The existing migration files apply cleanly to a new empty database.

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
source venv/bin/activate
python manage.py runserver
```

To make the server accessible on your LAN:
```bash
python manage.py runserver 0.0.0.0:8000
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

### Celery (Optional -- Background Tasks)

Celery workers are **not required** for core development. Emails print to the terminal via the console backend, and background tasks are simply skipped unless a worker is running.

If you need to test background tasks (e.g., scheduled reminders), install Redis and start workers. See [SETUP_GUIDE.md](SETUP_GUIDE.md#running-celery-workers-optional-in-development) for setup instructions.

```bash
# Start Celery worker (requires Redis running)
celery -A redib worker -l info

# Start Celery beat (scheduled tasks, requires Redis running)
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

For a complete first-time setup walkthrough, see [QUICKSTART.md](QUICKSTART.md).

For manual step-by-step data loading (nodes, users, equipment), see [SETUP_GUIDE.md](SETUP_GUIDE.md#initial-data-setup-detailed).

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

- [QUICKSTART.md](QUICKSTART.md) - First-time development setup
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Configuration reference and environment variables
- [TESTING.md](TESTING.md) - Testing procedures and guidelines
- [TEST_APPLICANTS_GUIDE.md](TEST_APPLICANTS_GUIDE.md) - Test data documentation
- [TEST_EMAIL_TEMPLATES.md](TEST_EMAIL_TEMPLATES.md) - Email template testing guide
- [USER_GUIDE.md](USER_GUIDE.md) - End-user guide for portal users
- [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment guide
- [../README.md](../README.md) - Project overview and features
