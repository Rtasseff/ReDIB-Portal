# ReDIB COA Portal -- Setup & Configuration Guide

Detailed configuration reference for the ReDIB Portal. For a quick first-time setup, see [QUICKSTART.md](QUICKSTART.md).

---

## Environment Configuration

### How the App Determines Its Mode

The application reads a single `.env` file in the project root (`redib/settings.py`). Two templates are provided:

| Template | Purpose | Copy Command |
|----------|---------|-------------|
| `.env.example` | Local development (venv + SQLite + console email) | `cp .env.example .env` |
| `.env.production.template` | Production VPS deployment (Docker + PostgreSQL + Redis + SMTP) | `cp .env.production.template .env` |

For rare cases where you want to run the full stack locally in Docker, start from `.env.production.template` and adjust values (DEBUG=True, simple passwords, `ALLOWED_HOSTS=localhost,127.0.0.1`).

### Key Settings That Control Behavior

| Setting | Dev Default | Prod Value | Effect |
|---------|-----------|------------|--------|
| `DEBUG` | `True` | `False` | Debug toolbar on; when `False`, enables HSTS, secure cookies, proxy SSL header detection. |
| `SECRET_KEY` | Insecure dev default | **Must set unique value** | Cryptographic signing. Rotate on deploy. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Your domain(s) | HTTP Host header validation. Comma-separated. |
| `CSRF_TRUSTED_ORIGINS` | _(empty)_ | `https://your.domain` | Required for HTTPS POSTs behind a reverse proxy. Include the `https://` scheme. |
| `DATABASE_URL` | `sqlite:///db.sqlite3` | `postgres://user:pw@db:5432/redib` | Database engine. |
| `USE_REDIS` | `False` | `True` | Cache backend: LocMemCache (dev) vs Redis (prod). |
| `REDIS_URL` | `redis://localhost:6379/0` | `redis://redis:6379/0` | Redis location (used when `USE_REDIS=True`). |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | `redis://redis:6379/0` | Celery broker. |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | `redis://redis:6379/0` | Celery result store. |
| `EMAIL_BACKEND` | `django.core.mail.backends.console.EmailBackend` | `django.core.mail.backends.smtp.EmailBackend` | Console vs real SMTP. |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_USE_TLS` | — | `smtp.ionos.es` / `587` / `True` | SMTP connection (only needed when the backend is SMTP). |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | — | SMTP creds | SMTP auth. |
| `DEFAULT_FROM_EMAIL` | `noreply@redib.net` | `noreply@redib.net` | Envelope-from for all outgoing mail. |
| `CONTACT_EMAIL` | `info@redib.net` | `info@redib.net` | Contact address rendered in every email template. |
| `SITE_URL` | `http://127.0.0.1:8000` | `https://portal.redib.net` | Full URL used in emailed links (must match the real host). |
| `SITE_DOMAIN` | `127.0.0.1:8000` | `portal.redib.net` | Host written to the Django Site record (used by allauth). |
| `SITE_NAME` | `ReDIB COA Portal` | `ReDIB COA Portal` | Display name in email headers. |
| `SENTRY_DSN` | _(empty)_ | _(optional)_ | Sentry error reporting; leave blank to disable. |

**Celery eager mode.** `CELERY_TASK_ALWAYS_EAGER` is set automatically — True whenever `DEBUG=True` **or** the test runner is active (see `redib/settings.py`). You never set it by hand. Result: in development, workflow emails print to the console without needing a running worker; under tests, `mail.outbox` captures sent messages.

**Security auto-enables when `DEBUG=False`:** HSTS, secure session + CSRF cookies, `SECURE_PROXY_SSL_HEADER` for Caddy. See `redib/settings.py`.

After changing `SITE_URL`/`SITE_DOMAIN`/`SITE_NAME`, re-run your setup command (`setup_localtest3_database`, `setup_base_database`, `setup_test_database`) so the Django Site record in the database picks up the new values. In production, the `docker/entrypoint.sh` reads these env vars on container start, so a `docker compose up` is enough.

**Production deployment** is a one-way setup on a VPS -- see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Admin Account Setup

### Create Superuser

```bash
python manage.py createsuperuser
```

You'll be prompted for:
- **Email address**: Your admin email (used for login)
- **First name**: Your first name
- **Last name**: Your last name
- **Password**: Strong password (won't be visible as you type)

### First Login

1. Go to http://localhost:8000/admin
2. Login with your superuser email and password
3. You should see the Django admin dashboard

---

## Initial Data Setup

After migrating the database and creating a superuser, populate data using one of the setup commands below. Most users should just pick one.

### Option A: `setup_localtest3_database` — Recommended for manual testing (dev)

Self-contained test environment. **Does not require any TSV data files.**

```bash
python manage.py setup_localtest3_database --reset --yes
```

Creates: 3 nodes, 6 equipment, 2 organizations, 7 funding agencies, 10 users, 2 calls (1 open + 1 resolved), 16 sample applications spanning every live + terminal status, and all email templates. All users have password `testpass123`. See the test accounts table in [QUICKSTART.md](QUICKSTART.md#test-accounts-after-running-setup_localtest3_database).

### Option B: `setup_base_database` — Real reference data only

Loads real ReDIB data from `data/*.tsv` files. No fake calls or applications. Useful for production setup or when you want to test with the real node/equipment inventory.

```bash
python manage.py setup_base_database --reset --yes
```

Runs (in order): `populate_redib_nodes` → `populate_redib_organizations` → `populate_redib_users` → `populate_redib_equipment` → `populate_redib_funding_agencies` → `seed_email_templates` → `configure_site`. All TSV users get password `changeme123` and pre-verified emails.

### Option C: `setup_test_database` — Real reference data + test applicants

Runs `setup_base_database` equivalent plus `seed_dev_data` (calls, orgs) and `seed_test_applicants` (7 test applicants with 17 applications in all workflow states).

```bash
python manage.py setup_test_database --reset --yes
```

Pass `--skip-applicants` to skip the test applicants step.

### Individual Population Commands

If you need fine-grained control, run the individual commands in dependency order. They read from `data/*.tsv` files (see [data/README.md](../data/README.md) for TSV format details):

```bash
# 1. Email templates (no dependencies)
python manage.py seed_email_templates

# 2. Nodes (no dependencies; required by users and equipment)
python manage.py populate_redib_nodes

# 3. Organizations (no dependencies; users link to these)
python manage.py populate_redib_organizations

# 4. Users (requires nodes and organizations)
python manage.py populate_redib_users

# 5. Equipment (requires nodes)
python manage.py populate_redib_equipment

# 6. Funding agencies (no dependencies)
python manage.py populate_redib_funding_agencies
```

All `populate_redib_*` commands support `--sync` mode to update existing records without deleting:

```bash
python manage.py populate_redib_nodes --sync
python manage.py populate_redib_users --sync
python manage.py populate_redib_equipment --sync
```

### TSV Data Sources

All population commands read tab-separated value files from `data/`:
- `data/nodes.tsv` — ReDIB network nodes
- `data/organizations.tsv` — Parent organizations
- `data/users.tsv` — Staff users with roles and areas
- `data/equipment.tsv` — Imaging devices per node
- `data/funding_agencies.tsv` — Funding agencies with origin_of_funds

See [data/README.md](../data/README.md) for TSV column reference and value constraints.

---

## Running Celery Workers (Optional in Development)

Background tasks (email sending, scheduled reminders) require Celery + Redis. **In development mode, these are optional** -- emails print to the console via the console email backend, and background tasks are simply not executed unless a worker is running.

If you want to test Celery locally:

1. Install and start Redis:
   ```bash
   # macOS
   brew install redis && redis-server
   # Linux
   sudo apt-get install redis && redis-server
   ```

2. Update `.env`: set `USE_REDIS=True`

3. Run in three separate terminals:

   **Terminal 1** - Celery Worker:
   ```bash
   source venv/bin/activate
   celery -A redib worker -l info
   ```

   **Terminal 2** - Celery Beat (scheduler):
   ```bash
   source venv/bin/activate
   celery -A redib beat -l info
   ```

   **Terminal 3** - Django server:
   ```bash
   source venv/bin/activate
   python manage.py runserver
   ```

---

## Common Issues

### Issue: "Email field must be set"
**Solution**: You're trying to create a user without an email. Email is required for all users.

### Issue: "UNIQUE constraint failed: core_user.email"
**Solution**: A user with that email already exists. Use a different email.

### Issue: "No such table: core_user"
**Solution**: Run migrations: `python manage.py migrate`

### Issue: Celery tasks not running
**Solution**: In development mode, Celery is optional. If you want background tasks, see [Running Celery Workers](#running-celery-workers-optional-in-development) above.

### Issue: Emails not sending
**Solution**: In development mode, emails print to the terminal (console backend). Check your terminal output. For real email delivery, configure SMTP in your `.env` file.

### Issue: "Error connecting to redis:6379" when logging in
**Solution**: Your `.env` has `USE_REDIS=True` but Redis is not running. Either:
- Set `USE_REDIS=False` in `.env` (recommended for development)
- Or install and start Redis (see Celery section above)

---

## Next Steps

- **Development workflows**: [DEVELOPMENT.md](DEVELOPMENT.md)
- **Testing guide**: [TESTING.md](TESTING.md)
- **Quick start**: [QUICKSTART.md](QUICKSTART.md)
- **System design**: [reference/redib-coa-system-design.md](reference/redib-coa-system-design.md)
