# ReDIB COA Portal -- Setup & Configuration Guide

The environment-variable reference and the data-loading how-to. For a first local run,
start with [QUICKSTART.md](QUICKSTART.md); for the production server, [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Environment Configuration

The app reads one `.env` file in the project root (`redib/settings.py`, via
`django-environ`). Real environment variables win over `.env`, which is how you point a
single command at another database, for example
`DATABASE_URL=sqlite:////tmp/scratch.sqlite3 python manage.py migrate`.

| Template | For | Copy |
|---|---|---|
| `.env.example` | Local development: venv, SQLite, console email | `cp .env.example .env` |
| `.env.production.template` | The production VPS: Docker, PostgreSQL, Redis, SMTP | `cp .env.production.template .env` |

**Production reads `.env` at container creation.** `docker-compose.prod.yml` passes it
in as `env_file`, and the image contains no `.env`. After editing it, run
`docker compose -f docker-compose.prod.yml up -d`, which recreates the containers.
`restart` keeps the old environment.

### Variable reference

"Default" is what the code uses when the variable is unset. The dev column is what
`.env.example` sets.

**Read by Django** (`redib/settings.py`):

| Variable | Default | Dev | Prod | What it does |
|---|---|---|---|---|
| `SECRET_KEY` | `django-insecure-dev-key-change-in-production` | any | long random string, set once | Signs sessions, CSRF tokens and password-reset links. Changing it signs everyone out and voids outstanding reset links, so don't rotate it casually. |
| `DEBUG` | `False` | `True` | `False` | `True` adds the debug toolbar and runs Celery tasks inline (below). `False` turns on HSTS, secure cookies and the proxy-SSL header. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | same | `portal.redib.net` | Comma-separated Host header allow-list. |
| `CSRF_TRUSTED_ORIGINS` | empty | empty | `https://portal.redib.net` | Needed for HTTPS form posts behind Caddy. Include the scheme. |
| `DATABASE_URL` | `sqlite:///db.sqlite3` | same | `postgresql://redib_user:<pw>@db:5432/redib_db` | Database. The password must match `POSTGRES_PASSWORD`. |
| `USE_REDIS` | `False` | `False` | `True` | **Cache only**: Redis at `REDIS_URL` instead of in-process memory. Celery doesn't read it. |
| `REDIS_URL` | `redis://localhost:6379/0` | same | `redis://redis:6379/0` | Cache location when `USE_REDIS=True`. |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | same (unused) | `redis://redis:6379/0` | Celery broker. |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | same (unused) | `redis://redis:6379/0` | Celery result store. |
| `EMAIL_BACKEND` | `django.core.mail.backends.console.EmailBackend` | console | `django.core.mail.backends.smtp.EmailBackend` | Console prints mail to the terminal; SMTP sends it. |
| `EMAIL_HOST` | `smtp.ionos.es` | — | the provider's host | Read only when the backend is **not** console. |
| `EMAIL_PORT` | `587` | — | `587` | Same condition. |
| `EMAIL_USE_TLS` | `True` | — | `True` | Same condition. |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | empty | — | SMTP login | Same condition. |
| `DEFAULT_FROM_EMAIL` | `noreply@redib.net` | same | `noreply@redib.net` | From address for all mail, ops alerts included. |
| `CONTACT_EMAIL` | `info@redib.net` | same | `info@redib.net` | Shown in every email template and in the site's help links. |
| `CALL_ANNOUNCEMENT_EMAILS_ENABLED` | `False` | `False` | **`False`** | Feature flag. When on, announcing or opening a call emails every active account with call notifications on, which is all ~1,200 of them. It stays off until backlog #41 is done: no rate limit, retry, bounce handling or unsubscribe link yet. While off, the coordinator sees "No announcement email was sent" and announces by hand. |
| `SITE_URL` | `https://portal.redib.net` | `http://127.0.0.1:8000` | `https://portal.redib.net` | Base of every link in emails. No trailing slash. **On dev, set it,** or emailed links point at production. |
| `SENTRY_DSN` | empty | empty | optional | Sentry error reporting; blank disables it. |
| `SECURE_SSL_REDIRECT` | `False` | ignored | `False` | Read only when `DEBUG=False`. Keep `False`: Caddy terminates TLS, and `True` loops. |
| `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` | `True` | ignored | `True` | Read only when `DEBUG=False`. |

**Read at setup time, not at runtime.** Django uses them through the `Site` record,
which allauth's emails use:

| Variable | Default | Dev | Prod | What it does |
|---|---|---|---|---|
| `SITE_DOMAIN` | `portal.redib.net` | `127.0.0.1:8000` | `portal.redib.net` | Host (no scheme) written to `Site` id 1. |
| `SITE_NAME` | `ReDIB COA Portal` | same | same | Name written to `Site` id 1. |

These are written by `docker/entrypoint.sh` on every container start, and by the
`setup_*` commands (`setup_base_database`, `setup_test_database`,
`setup_localtest1_database`, `setup_localtest3_database`,
`setup_livetest_small_database`). On dev, after changing them, rerun a setup command or
edit **Sites** in the admin. After changing `SITE_URL`, restart `runserver`.

**Read by Docker Compose** (interpolated into `docker-compose.prod.yml` from `.env`):

| Variable | Default | Prod | What it does |
|---|---|---|---|
| `DOMAIN` | `localhost` | `portal.redib.net` | The Caddy site address. Caddy gets the TLS certificate for it. |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | none | `redib_db` / `redib_user` / strong password | Create the database the **first** time the `postgres_data` volume starts; also used by the db healthcheck. Changing them later doesn't change the existing database. |

**Read by `scripts/backup-db.sh` from its own shell environment.** The script does
**not** read `.env`, so set these on the cron line
([DEPLOYMENT.md § 6.2](DEPLOYMENT.md#62-schedule-daily-backups)):

| Variable | Default | What it does |
|---|---|---|
| `ALERT_RECIPIENT` | `coordinator@redib.net` | Where the failure email goes. |
| `HEALTHCHECK_URL` | empty (no ping) | Dead-man's-switch URL pinged on success. |
| `BACKUP_DIR` | `/home/deploy/backups/redib` | Where dumps go. |
| `RETENTION_DAYS` | `7` | Prune age, applied only after a good backup. |
| `MIN_SIZE_RATIO_PERCENT` | `50` | Size check against the previous dump. |
| `POSTGRES_USER` / `POSTGRES_DB` | `redib_user` / `redib_db` | Passed to `pg_dump`. |
| `COMPOSE_FILE` | `docker-compose.prod.yml` | Compose file the script drives. |

**Not a variable: Celery eager mode.** `CELERY_TASK_ALWAYS_EAGER` is `True` whenever
`DEBUG=True` or the test runner is active. Every `.delay()` then runs inline in the
request, so workflow emails print to the dev console with no Redis and no worker, and
tests catch them in `mail.outbox`. Only the **scheduled** (beat) jobs need a worker and
beat to run. See [Running Celery Workers](#running-celery-workers-optional-in-development).

---

## Admin Account Setup

```bash
python manage.py createsuperuser
```

It asks for email, first name, last name and password. Log in at
http://127.0.0.1:8000/admin/. The portal's own login page also requires a verified
email address, and `createsuperuser` doesn't create one. Mark it verified with the
snippet in [DEPLOYMENT.md § 4.4](DEPLOYMENT.md#44-create-the-admin-superuser). The
accounts `setup_localtest3_database` creates are already verified.

---

## Initial Data Setup

After `python manage.py migrate` (and `createsuperuser`, if you want one), pick **one**
setup command. The TSV formats, the loader rules and their failure modes are in
[data/README.md](../data/README.md).

### Option A: `setup_localtest3_database`, the default for dev

```bash
python manage.py setup_localtest3_database --reset --yes
```

Self-contained: it reads no TSV. It creates 3 nodes, 6 equipment, 5 organizations,
7 funding agencies, 10 users (password `testpass123`), 2 calls (one open, one resolved),
16 applications covering every live and terminal status, and all 31 email templates. It
also sets the `Site` record. At the end it prints a login table and a what-to-test table.
Accounts: [QUICKSTART.md](QUICKSTART.md#test-accounts-after-running-setup_localtest3_database).
Walkthrough: [developer/localtest3-database-plan.md](developer/localtest3-database-plan.md).

### Option B: `setup_base_database`, real reference data only

```bash
python manage.py setup_base_database               # add to what is there
python manage.py setup_base_database --reset --yes # wipe everything but superusers first
```

It runs, in order: `populate_redib_organizations` → `populate_redib_nodes` →
`populate_redib_users` → `populate_redib_equipment` → `populate_redib_funding_agencies`
→ `seed_email_templates` → sets the `Site` record. Result on 2026-09-28: 186
organizations, 4 nodes, 28 users (1 coordinator, 5 node-coordinator and 21 evaluator
roles), 14 equipment, 375 funding agencies, 31 templates. **New** users get the password
`changeme123` and a verified email address.

- It stops at the first step that fails, prints `Failed: <reason>`, and **exits 0**. The
  steps before it stay loaded. Read the output.
- It is for an empty database. It is not a way to sync a live one. `--reset` deletes
  every call, application and non-superuser account. On production that is the
  [Full Database Reset](DEPLOYMENT.md#full-database-reset-and-reload) and nothing else.

### Option C: `setup_test_database`, real reference data plus fake workflow data

```bash
python manage.py setup_test_database --reset --yes
python manage.py setup_test_database --reset --yes --skip-applicants
```

It runs the same five loaders, then `seed_dev_data` (3 extra organizations, 2 nodes,
4 equipment, 8 `@test.redib.net` users, 2 calls, 4 applications), the email templates,
the `Site` record, and `seed_test_applicants` (7 applicants, 17 applications in every
status; skip it with `--skip-applicants`).

> **Currently broken part-way (2026-09-28).** `seed_dev_data` crashes after its
> applications, at "Creating evaluations and grants", on renamed evaluation score
> fields. This command reports every failed step as "may already exist" and carries on,
> so it exits 0 without dev-data evaluations or grants. Use Option A unless you need the
> real reference data plus fake applications.

`setup_localtest1_database` and `setup_livetest_small_database` also exist. See the
command reference in [DEVELOPMENT.md](DEVELOPMENT.md).

### Individual population commands

To load or reload one table, run the loaders yourself **in this order**. Nodes need
organizations, users need both, and equipment needs nodes:

```bash
python manage.py populate_redib_organizations      # data/organizations.tsv
python manage.py populate_redib_nodes              # data/nodes.tsv
python manage.py populate_redib_users --dry-run    # read the output, then:
python manage.py populate_redib_users              # data/users.tsv
python manage.py populate_redib_equipment          # data/equipment.tsv
python manage.py populate_redib_funding_agencies   # data/funding_agencies.tsv
python manage.py seed_email_templates              # any time; no TSV
```

- Each takes `--tsv <path>` to read another file.
- `populate_redib_users` is **create-only**: existing accounts keep their profile, but
  their roles are applied. `--update-existing` overwrites profiles, blanks included.
  `--dry-run` writes nothing.
- `--sync` does **not** mean "update". It deactivates what isn't in the file: nodes,
  equipment, and, for users, **every non-superuser account not listed, applicants
  included**. Never use `populate_redib_users --sync` on production. Details:
  [data/README.md § `--sync`](../data/README.md).
- `seed_email_templates` creates the 31 templates and, on every rerun, **overwrites
  their subject and body** from the code. A template switched off with **Is active** in
  the admin stays off. Production runs it on every container start.
- On production, prefix each command with
  `docker compose -f docker-compose.prod.yml exec web`. Before touching users there,
  read [DEPLOYMENT.md § Running Management Commands](DEPLOYMENT.md#running-management-commands).

---

## Running Celery Workers (Optional in Development)

With `DEBUG=True` you don't need Celery: every emailed step runs inline (see above).
What you *don't* get is the **scheduled** jobs: the daily reminders, deadline checks and
digests listed in `redib/celery.py`. To try one once, call it directly:

```bash
python manage.py shell -c "from calls.tasks import check_call_deadlines; check_call_deadlines()"
```

To run the scheduler for real, start Redis at `CELERY_BROKER_URL`
(`sudo apt-get install redis-server`), then in separate terminals:

```bash
celery -A redib worker -l info
celery -A redib beat -l info
python manage.py runserver
```

`USE_REDIS` isn't needed for this. It only moves the cache.

---

## Common Issues

**"No such table: core_user"**: run `python manage.py migrate`.

**"UNIQUE constraint failed: core_user.email"**: a user with that email exists. Emails are
the login and must be unique.

**Emails not arriving in dev**: with the console backend they print in the
`runserver` terminal. Nothing is sent.

**"Error connecting to redis:6379" when logging in**: `.env` has `USE_REDIS=True` and no
Redis is running. Set `USE_REDIS=False` for dev, or start Redis.

**A loader crashes with `UnicodeDecodeError`, or skips every row**: the TSV isn't
plain UTF-8 (Windows-1252, or a BOM). See [data/README.md](../data/README.md).

---

## Next Steps

- Day-to-day commands and the management-command reference: [DEVELOPMENT.md](DEVELOPMENT.md)
- Code structure, status machines and scheduled jobs: [ARCHITECTURE.md](ARCHITECTURE.md)
- Tests: [TESTING.md](TESTING.md)
- Production: [DEPLOYMENT.md](DEPLOYMENT.md)
