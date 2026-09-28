# ReDIB COA Portal -- Quick Start Guide

This guide gets you running in **Development Mode** (Python venv + SQLite) in
about five minutes. No Docker, Redis or Celery required.

For production deployment, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Prerequisites

- Python 3.11 or newer (production runs 3.11; dev also works on 3.12)
- Git
- The Pango system libraries WeasyPrint needs, if you want the *Download PDF*
  buttons to work. Everything else runs without them. See
  [DEVELOPMENT.md - System Dependencies](DEVELOPMENT.md#system-dependencies-for-pdf-generation).

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

No edits needed. The defaults are correct for development:
- `DEBUG=True`
- SQLite database (`db.sqlite3` in the repo root, created by `migrate`)
- `USE_REDIS=False` (in-memory cache)
- Console email backend: every email prints to the `runserver` terminal
- No Celery worker: with `DEBUG=True`, tasks run in-process

See [SETUP_GUIDE.md](SETUP_GUIDE.md#environment-configuration) for a full reference of all settings.

## 3. Initialize Database

```bash
python manage.py migrate
python manage.py createsuperuser     # optional; asks for email, first name, last name, password
```

The superuser is only for the Django admin (`/admin/`); the test accounts in
step 4 cover every portal role. To create one without prompts, set
`DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_FIRST_NAME`,
`DJANGO_SUPERUSER_LAST_NAME` and `DJANGO_SUPERUSER_PASSWORD` and add
`--noinput`.

## 4. Load Test Data (recommended)

```bash
python manage.py setup_localtest3_database --reset --yes
```

`--reset` clears every non-superuser row first; `--yes` skips the confirmation
prompt. The command creates a self-contained sandbox, with no TSV files
involved:
- 3 nodes (CICBIO, BIOIMAC, CNIC), 6 instruments
- 5 organizations, 7 funding agencies
- 10 users: 1 ReDIB coordinator, 2 node coordinators, 3 evaluators, 4 applicants
- 2 calls: `COA-LIVE-2026` (open) and `COA-PAST-2025` (resolved)
- 16 applications spanning every live and terminal status
- All email templates, and the Django Site record

It finishes by printing the login table and a cheat-sheet of which application
to use for which test. More in [TESTING.md](TESTING.md#the-localtest3-sandbox).

> Alternative: `python manage.py setup_test_database --reset --yes` loads the
> real reference data from `data/*.tsv` (the 4 ReDIB nodes and their
> instruments, the organization list, staff accounts) plus sample calls and
> applications. It is closer to production but less convenient to log in to.
> See [DEVELOPMENT.md](DEVELOPMENT.md#management-command-reference) for every
> setup command.

## 5. Run the Development Server

```bash
python manage.py runserver
```

- Application: http://127.0.0.1:8000
- Admin: http://127.0.0.1:8000/admin/
- Login: http://127.0.0.1:8000/accounts/login/

`.env.example` sets `SITE_URL=http://127.0.0.1:8000`, so links inside the
emails printed to the terminal point at this server.

### Test Accounts (after running setup_localtest3_database)

All test accounts use password `testpass123` and have pre-verified email
addresses, so they log straight in.

| Email | Role |
|-------|------|
| coordinator@test.redib.net | ReDIB Coordinator |
| nc.cicbio@test.redib.net | Node Coordinator (CICBIO) |
| nc.cnic@test.redib.net | Node Coordinator (CNIC) |
| eval.preclinical@test.redib.net | Evaluator (preclinical) |
| eval.clinical@test.redib.net | Evaluator (clinical) |
| eval.radio@test.redib.net | Evaluator (radiochemistry, clinical) |
| applicant1@test.redib.net | Applicant |
| applicant2@test.redib.net | Applicant |
| applicant3@test.redib.net | Applicant |
| applicant4@test.redib.net | Applicant (**incomplete** profile: the portal redirects to `/profile/` until it is filled in) |

BIOIMAC has no node coordinator in this sandbox. The dress-rehearsal harness
(`python scripts/rehearsal.py seed`) adds `nc.bioimac@test.redib.net`, and
replaces the two calls and 16 applications with one empty draft call; see
[TESTING.md](TESTING.md#the-dress-rehearsal-harness).

Your superuser logs in at `/admin/`. If you sign in with it at
`/accounts/login/` instead, allauth first asks you to confirm the email
address, and the confirmation link prints in the `runserver` terminal.

---

## What's Next

- **Commands, workflows, PDF libraries**: [DEVELOPMENT.md](DEVELOPMENT.md)
- **How the code is organised**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Running tests**: [TESTING.md](TESTING.md)
- **Configuration reference**: [SETUP_GUIDE.md](SETUP_GUIDE.md)
- **End-user guide**: [USER_GUIDE.md](USER_GUIDE.md)

---

## Local Docker Testing (Optional)

To try the production-like stack (PostgreSQL, Redis, Celery worker and beat)
on your own machine, use `docker-compose.yml`. It runs `runserver` inside the
`web` container with the repo bind-mounted, so code edits reload live.

### Setup

1. Install [Docker](https://docs.docker.com/get-docker/) with the Compose plugin.

2. Start from the dev template and point it at the compose services:
   ```bash
   cp .env.example .env
   ```
   then change these lines in `.env`. The password is the one hard-coded for
   the `db` service in `docker-compose.yml`.
   ```
   DATABASE_URL=postgresql://redib_user:redib_password@db:5432/redib_db
   USE_REDIS=True
   REDIS_URL=redis://redis:6379/0
   CELERY_BROKER_URL=redis://redis:6379/0
   CELERY_RESULT_BACKEND=redis://redis:6379/0
   ```

3. Build and start all services:
   ```bash
   docker compose up -d --build
   ```
   Each container's entrypoint (`docker/entrypoint.sh`) waits for the database,
   then runs `migrate`, `collectstatic` and `seed_email_templates` and sets the
   Site record from `SITE_DOMAIN`. You don't run those by hand.

4. Create an admin user and load test data:
   ```bash
   docker compose exec web python manage.py createsuperuser
   docker compose exec web python manage.py setup_localtest3_database --reset --yes
   ```

5. Open http://localhost:8000

With `DEBUG=True`, `CELERY_TASK_ALWAYS_EAGER` is on (settings derive it from
`DEBUG`; it is not read from `.env`), so tasks run inline in whichever process
calls them and the `celery` worker sees little traffic.

### Services

| Service | Port | Purpose |
|---------|------|---------|
| web | 8000 | Django (`runserver`) |
| db | 5432 | PostgreSQL 15 |
| redis | 6379 | Cache and Celery broker |
| celery | - | Background task worker |
| celery-beat | - | Scheduled tasks |

`docker-compose.dev.yml` is a smaller alternative that starts only `db` and
`redis`, for running the app from your venv against them (use `localhost`
instead of `db`/`redis` in the URLs above).

### Common Docker Commands

```bash
docker compose logs -f web                     # one service's logs
docker compose logs -f                         # all logs
docker compose down                            # stop
docker compose down -v                         # stop and delete the volumes (full reset)
docker compose up -d --build                   # rebuild after changing requirements.txt or the Dockerfile
docker compose exec web python manage.py <command>
docker compose exec web python manage.py shell
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

### Database connection errors
In development mode, SQLite needs no setup; just run `python manage.py migrate`.
A PostgreSQL connection error means `.env` still has a Postgres
`DATABASE_URL`. Re-copy it from `.env.example`.

### "Error connecting to redis:6379" when logging in
Your `.env` has `USE_REDIS=True`. Set it to `False`, or re-copy `.env.example`.
Redis is not needed for local development.

### Workflow emails don't appear
With `DEBUG=True`, Celery tasks run synchronously in-process
(`CELERY_TASK_ALWAYS_EAGER`), and every email, workflow and allauth alike,
prints to the terminal running `runserver`. Nothing is sent. To exercise a
real queue, see [SETUP_GUIDE.md](SETUP_GUIDE.md#running-celery-workers-optional-in-development).

### Static files missing, or "Missing staticfiles manifest entry"
With `DEBUG=True`, `runserver` serves `static/` directly and needs nothing.
With `DEBUG=False` the manifest storage is in use: run
`python manage.py collectstatic --noinput`.

### "Download PDF" fails with a Pango, Cairo or `libgobject` error
The WeasyPrint system libraries are missing. See
[DEVELOPMENT.md](DEVELOPMENT.md#system-dependencies-for-pdf-generation).

### A test account keeps landing on `/profile/`
Expected for `applicant4@test.redib.net`, whose profile is deliberately
incomplete. `ProfileCompletionMiddleware` sends any non-staff user with a
missing name, phone, organization or position there (the login, help and
public consult pages are exempt).
