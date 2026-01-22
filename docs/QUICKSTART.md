# ReDIB COA Portal - Quick Start Guide

## What Has Been Built

A complete Django-based Competitive Open Access (COA) management system with:

### Core Features Implemented
- **Complete data model** with 15+ models across 7 Django apps
- **Role-based access control** with 5 user types (Applicant, Node Coordinator, Evaluator, Coordinator, Admin)
- **Application workflow** with 13 application states
- **Evaluation system** with 5 scoring criteria (1-5 scale)
- **Django admin interfaces** for all models with advanced filtering and search
- **Docker configuration** for production deployment
- **Celery + Redis** setup for background tasks and scheduled jobs
- **Email system** configuration (console backend for development)
- **Audit trail** using django-simple-history

### Technology Stack
- Django 5.0 + Python 3.11
- PostgreSQL 15 (or SQLite for local dev)
- Redis 7 + Celery 5.6
- Bootstrap 5 + HTMX + Alpine.js
- django-allauth for authentication

## Current Status

The ReDIB COA Portal is **fully implemented and production-ready** with all 10 development phases complete:

- ✅ Complete application workflow from submission to completion
- ✅ Automated evaluator assignment with conflict-of-interest detection
- ✅ Multi-criteria evaluation system with score aggregation
- ✅ Publication tracking and reporting
- ✅ 29 integration tests covering all phases
- ✅ Ready for production deployment

See [README.md](../README.md) for complete feature list and technical details.

## How to Use

### Local Development

1. **Activate virtual environment**
   ```bash
   source venv/bin/activate
   ```

2. **Run development server**
   ```bash
   python manage.py runserver
   ```

3. **Access the application**
   - Homepage: http://localhost:8000
   - Admin: http://localhost:8000/admin
   - Accounts: http://localhost:8000/accounts/login

4. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```

### Using Docker (Production-like Environment)

Docker provides a complete environment with PostgreSQL, Redis, Celery workers, and the Django application.

#### Services Included

| Service | Port | Purpose |
|---------|------|---------|
| web | 8000 | Django application |
| db | 5432 | PostgreSQL database |
| redis | 6379 | Cache & Celery broker |
| celery | - | Background task worker |
| celery-beat | - | Scheduled tasks |

#### Quick Start

1. **Copy the Docker environment file**
   ```bash
   cp .env.docker .env
   ```

2. **Build and start all services**
   ```bash
   docker compose up -d --build
   ```

3. **Run migrations**
   ```bash
   docker compose exec web python manage.py migrate
   ```

4. **Create superuser**
   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

5. **Load test data (recommended for testing)**
   ```bash
   docker compose exec web python manage.py setup_localtest1_database
   ```

6. **Access the portal**
   - Application: http://localhost:8000
   - Admin: http://localhost:8000/admin

#### Test Accounts (after running setup_localtest1_database)

All test accounts use password: `testpass123`

| Email | Role |
|-------|------|
| coordinator@test.redib.net | ReDIB Coordinator |
| nc.cicbio@test.redib.net | Node Coordinator (CICBIO) |
| nc.bioimac@test.redib.net | Node Coordinator (BIOIMAC) |
| nc.cnic@test.redib.net | Node Coordinator (CNIC) |
| eval.preclinical@test.redib.net | Evaluator (preclinical) |
| eval.clinical@test.redib.net | Evaluator (clinical) |
| eval.radiotracers@test.redib.net | Evaluator (radiotracers) |
| applicant1@test.redib.net | Applicant |
| applicant2@test.redib.net | Applicant |
| applicant3@test.redib.net | Applicant |

#### Common Docker Commands

```bash
# View logs
docker compose logs -f web

# View all service logs
docker compose logs -f

# Stop services
docker compose down

# Stop and remove volumes (full reset)
docker compose down -v

# Rebuild after code changes
docker compose up -d --build

# Run Django management commands
docker compose exec web python manage.py <command>

# Access Django shell
docker compose exec web python manage.py shell

# Access database shell
docker compose exec db psql -U redib_user -d redib_db
```

## Initial Data Setup

After creating a superuser, load the required data using management commands:

```bash
# Load email templates
python manage.py seed_email_templates

# Load ReDIB nodes (must run first)
python manage.py populate_redib_nodes

# Load users (requires nodes)
python manage.py populate_redib_users

# Load equipment (requires nodes)
python manage.py populate_redib_equipment
```

**For comprehensive setup instructions**, see [SETUP_GUIDE.md](SETUP_GUIDE.md).

**For test data**, use: `python manage.py seed_dev_data --clear`

## Project Structure

The project is organized into 7 Django apps:

- **core/** - Users, organizations, nodes, equipment
- **calls/** - Call management and equipment allocation
- **applications/** - Application workflow and feasibility review
- **evaluations/** - Evaluation system and scoring
- **access/** - Access grants and publications
- **communications/** - Email system and notifications
- **reports/** - Statistics and Excel exports

For detailed structure, see [README.md](README.md#project-structure).

## Deployment

For production deployment, see the comprehensive deployment guide in [README.md](README.md#production-deployment) and [SETUP_GUIDE.md](SETUP_GUIDE.md).

## Key Design Decisions

1. **Email-based authentication** - Users log in with email, not username
2. **Modular apps** - Each major feature in its own Django app for maintainability
3. **Docker-first deployment** - All services containerized for easy deployment
4. **Admin-heavy initial release** - Django admin provides immediate functionality
5. **Audit trail** - All models have change history via django-simple-history

## Troubleshooting

### Issue: Database connection errors
- **Solution**: Make sure PostgreSQL is running (via Docker or locally)
- For local dev, use SQLite: `DATABASE_URL=sqlite:///db.sqlite3` in `.env`

### Issue: Celery tasks not running
- **Solution**: Start Celery worker: `celery -A redib worker -l info`
- And Celery beat: `celery -A redib beat -l info`

### Issue: Static files not loading
- **Solution**: Run `python manage.py collectstatic`
- Make sure `STATIC_ROOT` directory exists

### Issue: django-allauth deprecation warnings
- **Solution**: These are warnings about newer config syntax
- Update settings.py to use new ACCOUNT_LOGIN_METHODS format (optional)
- Does not affect functionality

## Additional Documentation

- **Detailed Setup**: [SETUP_GUIDE.md](SETUP_GUIDE.md)
- **Testing Guide**: [TESTING.md](TESTING.md)
- **Development Workflows**: [DEVELOPMENT.md](DEVELOPMENT.md)
- **System Design**: [reference/redib-coa-system-design.md](reference/redib-coa-system-design.md)
- **Complete Documentation**: [README.md](../README.md)
