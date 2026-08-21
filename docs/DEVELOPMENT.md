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

Pick one of the three setup commands based on what you need. All support `--reset --yes` to wipe non-superuser data first.

### Option A: `setup_localtest3_database` (recommended for manual testing)

Self-contained test environment with everything pre-wired (nodes, equipment, orgs, funding agencies, users, calls, sample applications). **No TSV data files required.**

```bash
python manage.py setup_localtest3_database --reset --yes
```

Creates 3 nodes, 6 equipment, 2 organizations, 7 funding agencies, 10 users (password `testpass123`), 2 calls, and 16 sample applications spanning every live + terminal state — covers the full manual-test surface. One applicant has an intentionally incomplete profile for Scenario 1 testing.

### Option B: `setup_base_database` (real reference data only)

Loads real ReDIB data from `data/*.tsv` files. No fake calls or applications.

```bash
python manage.py setup_base_database --reset --yes
```

All TSV users get password `changeme123` and pre-verified emails. If your superuser email matches a row in `data/users.tsv`, that user also gets the TSV roles assigned.

### Option C: `setup_test_database` (real reference data + test applicants)

Extends `setup_base_database` with `seed_dev_data` and `seed_test_applicants` (7 test applicants, 17 apps across all workflow states).

```bash
python manage.py setup_test_database --reset --yes
```

Pass `--skip-applicants` if you just want the base data.

See [TEST_APPLICANTS_GUIDE.md](TEST_APPLICANTS_GUIDE.md) for the full applicant inventory.

## Database Management

### Complete Database Reset

When you need a fully clean slate (new database file, fresh migrations):

```bash
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
# For manual testing (self-contained — nodes, equipment, orgs, funding
# agencies, users, calls, sample applications, all inline)
python manage.py setup_localtest3_database --reset --yes
# OR, to load real reference data from data/*.tsv
python manage.py setup_base_database
```

**Note:** You do not need to delete or regenerate migration files. The existing migration files apply cleanly to a new empty database.

## Data Loading

The recommended path is to use one of the `setup_*_database` commands above. Run the individual population commands only when you need fine-grained control.

### Individual Population Commands (dependency order)

```bash
# 1. Email templates (no dependencies)
python manage.py seed_email_templates

# 2. Nodes (no dependencies; required by users and equipment)
python manage.py populate_redib_nodes

# 3. Organizations (no dependencies; users link to these)
python manage.py populate_redib_organizations

# 4. Users (requires nodes + organizations)
python manage.py populate_redib_users   # create-only; --update-existing to overwrite profiles

# 5. Equipment (requires nodes)
python manage.py populate_redib_equipment

# 6. Funding agencies (no dependencies)
python manage.py populate_redib_funding_agencies
```

All commands read from `data/*.tsv` files — see [data/README.md](../data/README.md) for the TSV format and column reference.

### Sync Mode

All `populate_redib_*` commands support `--sync` to update existing records without deleting:

```bash
python manage.py populate_redib_nodes --sync
python manage.py populate_redib_users --sync
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

Send all workflow email templates to a single recipient to verify rendering and links:

```bash
# Send test emails
python manage.py send_test_emails --to your-email@example.com

# Clean up test data afterward
python manage.py send_test_emails --cleanup
```

See [TEST_EMAIL_TEMPLATES.md](TEST_EMAIL_TEMPLATES.md) for full details on what is created and how to verify.

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

Celery workers are **not required** for core development. When `DEBUG=True`, the setting `CELERY_TASK_ALWAYS_EAGER=True` is set automatically (see `redib/settings.py`), which causes `.delay()` calls to run **synchronously in-process**. This means:

- All workflow emails (feasibility requests, evaluation assignments, resolution notifications, etc.) print to the terminal via the console email backend immediately when triggered.
- No Redis or Celery worker is needed to see these emails during dev.
- Allauth account emails (signup confirmation, password reset) also print to the terminal — these run synchronously regardless of Celery.

In production (`DEBUG=False`), `CELERY_TASK_ALWAYS_EAGER` is `False` and tasks queue normally to Celery + Redis.

If you specifically want to test the **async behavior** locally (e.g., scheduled reminders via Celery beat), install Redis and start workers. See [SETUP_GUIDE.md](SETUP_GUIDE.md#running-celery-workers-optional-in-development) for setup instructions.

```bash
# Start Celery worker (requires Redis running, and you'd typically also set
# CELERY_TASK_ALWAYS_EAGER=False in your .env to actually exercise the queue)
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
# Self-contained dev test environment (no TSV needed) — recommended for manual testing
python manage.py setup_localtest3_database --reset --yes

# Real reference data only (loads from data/*.tsv)
python manage.py setup_base_database --reset --yes

# Real reference data + test applicants (17 apps across all workflow states)
python manage.py setup_test_database --reset --yes

# Seed just the test applicants (if base data already exists)
python manage.py seed_test_applicants --clear
```

See [SETUP_GUIDE.md#initial-data-setup](SETUP_GUIDE.md#initial-data-setup) for the full breakdown of what each command creates.

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
