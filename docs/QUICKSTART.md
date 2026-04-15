# ReDIB COA Portal -- Quick Start Guide

This guide gets you running in **Development Mode** (Python venv + SQLite) in under 5 minutes.
No Docker, Redis, or Celery required.

For production deployment, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Prerequisites

- Python 3.11+
- Git
- (Optional) System libraries for PDF generation -- see [DEVELOPMENT.md - System Dependencies](DEVELOPMENT.md#system-dependencies-for-pdf-generation)

## 1. Clone and Create Virtual Environment

```bash
git clone <repo-url>
cd ReDIB-Portal
python3 -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate          # Windows (WSL recommended)
pip install -r requirements.txt
```

## 2. Configure Environment

```bash
cp .env.example .env
```

No edits needed -- the defaults are correct for development:
- `DEBUG=True`
- SQLite database (no PostgreSQL needed)
- `USE_REDIS=False` (in-memory cache, no Redis needed)
- Console email backend (emails print to terminal)
- Celery workers not required

See [SETUP_GUIDE.md](SETUP_GUIDE.md#environment-configuration) for a full reference of all settings.

## 3. Initialize Database

```bash
python manage.py migrate
python manage.py createsuperuser
```

## 4. Load Test Data (recommended)

```bash
python manage.py setup_localtest2_database --reset --yes
```

This single command creates a self-contained test environment with:
- 3 nodes, 6 equipment items
- 2 organizations
- 7 funding agencies (with origin_of_funds values)
- 10 users (coordinator, 3 node coordinators, 3 evaluators, 3 applicants)
- 2 calls (1 resolved, 1 open)
- 3 sample applications at different workflow stages
- All email templates

No TSV data files required. See [TEST_APPLICANTS_GUIDE.md](TEST_APPLICANTS_GUIDE.md) for more on test data, and the table below for test account credentials.

> Alternative: `python manage.py setup_test_database --reset --yes` loads from the real `data/*.tsv` files (4 real ReDIB nodes, 87 equipment items, etc.) and is closer to production. Use `setup_localtest2_database` for most manual testing.

## 5. Run the Development Server

```bash
python manage.py runserver
```

- Application: http://localhost:8000
- Admin: http://localhost:8000/admin
- Login: http://localhost:8000/accounts/login/

### Test Accounts (after running setup_localtest2_database)

All test accounts use password: `testpass123`

| Email | Role |
|-------|------|
| coordinator@test.redib.net | ReDIB Coordinator |
| nc.cicbio@test.redib.net | Node Coordinator (CICBIO) |
| nc.bioimac@test.redib.net | Node Coordinator (BIOIMAC) |
| nc.cnic@test.redib.net | Node Coordinator (CNIC) |
| eval.preclinical@test.redib.net | Evaluator (preclinical) |
| eval.clinical@test.redib.net | Evaluator (clinical) |
| eval.radiochemistry@test.redib.net | Evaluator (radiochemistry) |
| applicant1@test.redib.net | Applicant (complete profile) |
| applicant2@test.redib.net | Applicant (complete profile) |
| applicant3@test.redib.net | Applicant (**incomplete** profile — for Scenario 1 testing) |

---

## What's Next

- **Development workflows**: [DEVELOPMENT.md](DEVELOPMENT.md)
- **Configuration reference**: [SETUP_GUIDE.md](SETUP_GUIDE.md)
- **Running tests**: [TESTING.md](TESTING.md)
- **End-user guide**: [USER_GUIDE.md](USER_GUIDE.md)

---

## Local Docker Testing (Optional)

If you want to test with the full production-like stack (PostgreSQL, Redis, Celery) locally without deploying to a VPS:

### Setup

1. Install [Docker](https://docs.docker.com/get-docker/) and Docker Compose

2. Create your `.env` from the production template (adjust to local values — DEBUG=True, ALLOWED_HOSTS=localhost,127.0.0.1, simple passwords, and use service names `db`/`redis` as the hosts):
   ```bash
   cp .env.production.template .env
   # Edit .env to set DEBUG=True, simple passwords, and local ALLOWED_HOSTS
   ```

3. Build and start all services:
   ```bash
   docker compose up -d --build
   ```

4. Run migrations and create admin user:
   ```bash
   docker compose exec web python manage.py migrate
   docker compose exec web python manage.py createsuperuser
   ```

5. Load test data:
   ```bash
   docker compose exec web python manage.py setup_localtest2_database --reset --yes
   ```

6. Access the portal at http://localhost:8000

### Services

| Service | Port | Purpose |
|---------|------|---------|
| web | 8000 | Django application |
| db | 5432 | PostgreSQL database |
| redis | 6379 | Cache & Celery broker |
| celery | - | Background task worker |
| celery-beat | - | Scheduled tasks |

### Common Docker Commands

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

### Switching Back to Development Mode

```bash
docker compose down
cp .env.example .env
source venv/bin/activate
python manage.py runserver
```

---

## Troubleshooting

### Issue: Database connection errors
**Solution**: In development mode, the default SQLite database requires no setup -- just run `python manage.py migrate`. If you see PostgreSQL connection errors, make sure your `.env` file was copied from `.env.example` (not `.env.production.template`).

### Issue: "Error connecting to redis:6379" when logging in
**Solution**: Your `.env` may have `USE_REDIS=True`. For development, set `USE_REDIS=False` or re-copy from `.env.example`. Redis is not needed for local development.

### Issue: Celery tasks not running
**Solution**: In development mode (`DEBUG=True`), Celery tasks run synchronously in-process via `CELERY_TASK_ALWAYS_EAGER=True`, and all emails (workflow + allauth) print to the terminal via the console backend. No Redis or Celery worker needed. If you specifically want to test the async Celery queue, see the optional setup in [SETUP_GUIDE.md](SETUP_GUIDE.md#running-celery-workers-optional-in-development).

### Issue: Static files not loading
**Solution**: Run `python manage.py collectstatic`

### Issue: django-allauth deprecation warnings
**Solution**: These are warnings about newer config syntax. Does not affect functionality.

## Additional Documentation

- **Configuration reference**: [SETUP_GUIDE.md](SETUP_GUIDE.md)
- **Development workflows**: [DEVELOPMENT.md](DEVELOPMENT.md)
- **Testing guide**: [TESTING.md](TESTING.md)
- **Production deployment**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **System design**: [reference/redib-coa-system-design.md](reference/redib-coa-system-design.md)
