# Development Guide

Day-to-day commands for working on the portal, and a reference for every
management command and script in the repo.

Development mode is **Python venv + SQLite + `runserver`**. No Docker, Redis or
Celery. First-time setup is in [QUICKSTART.md](QUICKSTART.md); how the code is
laid out is in [ARCHITECTURE.md](ARCHITECTURE.md).

## Table of Contents

- [Everyday commands](#everyday-commands)
- [Resetting your local database](#resetting-your-local-database)
- [Management command reference](#management-command-reference)
- [Email templates](#email-templates)
- [Scheduled jobs and Celery](#scheduled-jobs-and-celery)
- [System Dependencies for PDF Generation](#system-dependencies-for-pdf-generation)

## Everyday commands

```bash
source venv/bin/activate

python manage.py runserver                    # http://127.0.0.1:8000
python manage.py test tests reports           # full suite, about 2 minutes; see TESTING.md
python manage.py check                        # after any model, settings or loader change
python manage.py makemigrations --check --dry-run   # "No changes detected" = no missing migration
python manage.py showmigrations               # what has been applied to your db.sqlite3
python manage.py shell
```

To reach the dev server from another machine on your LAN, run
`python manage.py runserver 0.0.0.0:8000` and add your machine's LAN IP to
`ALLOWED_HOSTS` in `.env`. The default only allows `localhost,127.0.0.1`.

Every email the portal sends, workflow and allauth alike, prints to the
`runserver` terminal (`EMAIL_BACKEND` is the console backend in
`.env.example`).

## Resetting your local database

`db.sqlite3` is gitignored and disposable. For a clean slate:

```bash
rm db.sqlite3
python manage.py migrate
python manage.py setup_localtest3_database --reset --yes
```

Never delete or regenerate migration files to "reset". The committed
migrations apply cleanly to an empty database, and production depends on them.

For the other data-loading options (real reference data from `data/*.tsv`,
individual loaders, load order) see
[SETUP_GUIDE.md](SETUP_GUIDE.md#initial-data-setup). TSV formats and loader
rules are in [data/README.md](../data/README.md).

## Management command reference

Every `manage.py` command the project defines, and every file in `scripts/`.
Each section heading says which environment its commands are meant for. On
prod, `manage.py` commands run inside the container:
`docker compose -f docker-compose.prod.yml exec web python manage.py <command>`
(see [DEPLOYMENT.md](DEPLOYMENT.md)).

### Sandboxes and test data (dev)

| Command | What it does | Destructive? | Key flags |
|---|---|---|---|
| `setup_localtest3_database` | **The default dev sandbox.** Creates 3 nodes, 6 instruments, 10 pre-verified accounts (`testpass123`), 2 calls and 16 applications spanning every status, plus email templates. No TSVs. Prints a login table and cheat-sheet. | `--reset` deletes every non-superuser row. Without it the command fails on a non-empty database. | `--reset`, `--yes` (skip the prompt) |
| `setup_localtest1_database` | Older, smaller sandbox: the same 3 nodes and 6 instruments, 10 accounts (3 node coordinators), **no calls or applications**. Useful for starting from an empty portal. Its account names differ slightly from localtest3's (`eval.radiochemistry@`, `nc.bioimac@`, no `applicant4`). | Same as localtest3 | `--reset`, `--yes` |
| `setup_base_database` | Real reference data only: the five `populate_redib_*` loaders in order, `seed_email_templates`, and the Site record. No calls or applications. TSV accounts get no usable password (each sets one with "Forgot password"). Stops with a non-zero exit at the first failed step. | `--reset` deletes every non-superuser row, including email templates and email logs | `--reset`, `--yes` |

`setup_test_database`, `seed_dev_data`, `seed_test_applicants` and
`setup_livetest_small_database` were removed on 2026-09-29 (#88(b), #90):
`seed_dev_data` crashed on renamed evaluation fields, and `setup_localtest3_database`
covers what they did.

### Reference data loaders (dev and prod)

Each reads one TSV from `data/`, validates it and upserts by natural key.
Load order and rules: [SETUP_GUIDE.md](SETUP_GUIDE.md#individual-population-commands)
and [data/README.md](../data/README.md). All five take `--tsv <path>`, and each runs in
one transaction or checks the whole file first, so a bad row writes nothing.

| Command | Reads | `--sync` does | Other flags |
|---|---|---|---|
| `populate_redib_organizations` | `organizations.tsv` | Lists organizations not in the TSV; changes nothing | |
| `populate_redib_nodes` | `nodes.tsv` (needs organizations) | Marks nodes not in the TSV inactive | |
| `populate_redib_users` | `users.tsv` (needs organizations and nodes). New users get no usable password. Unknown role names and bad ORCID or phone abort the load. | No `--sync` (#83) | `--dry-run` (writes nothing), `--update-existing` (overwrite existing profiles; create-only by default) |
| `populate_redib_equipment` | `equipment.tsv` (needs nodes) | Marks instruments not in the TSV inactive | |
| `populate_redib_funding_agencies` | `funding_agencies.tsv` | Lists agencies not in the TSV; changes nothing | |

`export_redib_users` goes the other way. The database is the authority for people, and
this writes `users.tsv` from it: every user with a non-applicant role (active or
retired) or `is_staff`, in the file's columns plus a trailing `retired_roles`. TSV to
stdout (UTF-8, CRLF, sorted by email); `--output <path>`, `--format xlsx`. Read-only.
Details: [data/README.md § `export_redib_users`](../data/README.md#export_redib_users).

Before any users load against production, run `scripts/check_role_drift.py`
(below), then `--dry-run`.

### Email (dev and prod)

| Command | What it does | Destructive? | Key flags |
|---|---|---|---|
| `seed_email_templates` | Creates or updates all 31 `EmailTemplate` rows from the definitions in the command file. Runs automatically in the Docker entrypoint on every container start. | Overwrites each template's subject and body, so content edits made in the admin are lost. `is_active` is set only on create, so a template switched off in the admin stays off. | none |
| `send_test_emails` | Sends 15 of the 31 templates to one existing user so you can check rendering and links. Creates the call `COA-EMAIL-TEST` and one application under it. On prod it sends real mail. See [TEST_EMAIL_TEMPLATES.md](TEST_EMAIL_TEMPLATES.md). | Adds an evaluator role (preclinical) to the recipient if they had none. `--cleanup` deletes the test call and everything under it, and that role (never one the recipient already had). | `--to <email>` (default `rtasseff@cicbiomagune.es`), `--cleanup` |

### Operations (prod)

| Command or script | What it does | Destructive? | How to run |
|---|---|---|---|
| `run_locked` | Runs another management command under a Postgres advisory lock, so the three app containers don't race `migrate` at startup (#37). On SQLite it just runs the command. Used by `docker/entrypoint.sh`. | Only as destructive as the wrapped command | `manage.py run_locked migrate --noinput` |
| `purge_unverified_signups` | Deletes self-registered accounts that never confirmed their email or logged in, are not staff, hold no role but applicant, have no applications, and joined more than `--days` ago (#92). Loaded and hand-added staff have a verified email, so it never touches them. | **Yes**, deletes accounts. Run `--dry-run` first. | `--dry-run`, `--days N` (default 7) |
| `send_ops_alert` | Sends one plain-text email synchronously through the SMTP settings, with no Celery and no template. Used by `backup-db.sh` on failure. | No | `--recipient`, `--subject`, `--body` (all required) |
| `backfill_waitlist_hours_approved` | One-off for #31: fills `RequestedAccess.hours_approved` from a TSV of figures node coordinators confirmed, only where the current value is null or 0. Prod checked and it was never needed; kept for the record. | Writes only null/0 rows | `--tsv <path>` (required), `--dry-run` |
| `scripts/backup-db.sh` | Nightly cron job on the VPS: `pg_dump` through `docker-compose.prod.yml` plus a tarball of key files (`.env` among them), validated before anything old is pruned. Keeps 7 days by default. Emails `ALERT_RECIPIENT` on failure. Details in [DEPLOYMENT.md](DEPLOYMENT.md). | Prunes backups older than `RETENTION_DAYS`, only after a good dump | `cd /home/deploy/ReDIB-Portal && ./scripts/backup-db.sh`; env overrides `RETENTION_DAYS`, `MIN_SIZE_RATIO_PERCENT`, `BACKUP_DIR`, `ALERT_RECIPIENT`, `HEALTHCHECK_URL` |
| `scripts/check_role_drift.py` | Reports where the database's `UserRole` rows (evaluator areas included) disagree with `data/users.tsv`. Self-registered applicants are counted, not flagged. Run it before any `populate_redib_users` on prod. | No, read-only | `python manage.py shell < scripts/check_role_drift.py` |

### Developer tooling (dev only)

| Script | What it does | Destructive? | How to run |
|---|---|---|---|
| `scripts/rehearsal.py` | Dress-rehearsal harness: resets to the localtest3 sandbox with one draft call (`REHEARSAL-2701`), simulates days passing, runs every scheduled task once, and lists the emails sent. Refuses to run unless `DEBUG` is on and the database is SQLite. See [developer/dress-rehearsal.md](developer/dress-rehearsal.md). | `seed` wipes like `setup_localtest3_database --reset`, then deletes all calls, applications and email logs | `python scripts/rehearsal.py {seed,status,advance N,beat,inbox [--full]}` |
| `scripts/new-worktree.sh` | Creates a git worktree for a bucket of work under `~/projects/ReDIB-Portal-wt/<slug>/`. It copies `.env`, `db.sqlite3` and `media/`, builds a venv, and seeds `docs/handoffs/<slug>.md`. See [developer/worktrees.md](developer/worktrees.md). Never on the VPS. | No | `scripts/new-worktree.sh <slug> [branch] [base-ref]` from the main checkout |

## Email templates

Templates live in the database, not in files. Their definitions are in
`communications/management/commands/seed_email_templates.py`. To change one,
edit it there and run:

```bash
python manage.py seed_email_templates
```

Production picks the change up on the next deploy, because the container
entrypoint reseeds on every start.

`CONTACT_EMAIL` (default `info@redib.net`, set in `.env`) is injected into
every template as `{{ contact_email }}`.

To render every workflow email at once, use `send_test_emails`; see
[TEST_EMAIL_TEMPLATES.md](TEST_EMAIL_TEMPLATES.md). How emails are queued and
logged is covered in [ARCHITECTURE.md](ARCHITECTURE.md).

## Scheduled jobs and Celery

You don't need Celery in development. `redib/settings.py` sets
`CELERY_TASK_ALWAYS_EAGER = DEBUG` (or when testing). It is not read from
`.env`, so with `DEBUG=True` every `.delay()` runs inline and its email prints
to the terminal.

What you don't get is the scheduled jobs in `redib/celery.py` (reminders,
deadline checks, digests). To see what they would do today, run them all once
against your sandbox:

```bash
python scripts/rehearsal.py beat      # every scheduled task once, against your dev database
python scripts/rehearsal.py inbox     # the emails they logged
```

`beat` refuses to run unless `DEBUG` is on and the database is SQLite. It does
not check the email backend, so keep the console backend from `.env.example`.

To run a real worker and beat against Redis, see
[SETUP_GUIDE.md](SETUP_GUIDE.md#running-celery-workers-optional-in-development).

## System Dependencies for PDF Generation

The *Download PDF* buttons use WeasyPrint (67.0 in the dev venv), which needs
the Pango system libraries. Nothing else in the portal needs them.

### Ubuntu/Debian

The same packages the `Dockerfile` installs:

```bash
sudo apt-get install -y \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-dejavu-core \
    fonts-liberation
```

On Ubuntu 24.04 the package is `libgdk-pixbuf-2.0-0`. The old name
`libgdk-pixbuf2.0-0` resolves to an outdated build.

### macOS (Homebrew)

```bash
brew install pango cairo gdk-pixbuf libffi
```

On Apple Silicon, Homebrew installs to `/opt/homebrew/lib`, which the dynamic
loader does not search, so `import weasyprint` still fails until the server is
started as
`DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python manage.py runserver`
(verified 2026-09-08, WeasyPrint 67.0).

### Windows

Use WSL2 with Ubuntu and install the Ubuntu packages above inside WSL.

### Docker

The `Dockerfile` already installs everything; nothing to do.

### Checking it works

```bash
python -c "import weasyprint; weasyprint.HTML(string='<p>ok</p>').write_pdf('/tmp/check.pdf'); print('PDF OK')"
```

If that prints `PDF OK`, the *Download PDF* buttons on an application's
detail and preview pages will work too.

## Related Documentation

- [QUICKSTART.md](QUICKSTART.md) - first-time development setup
- [ARCHITECTURE.md](ARCHITECTURE.md) - apps, models, status machines, scheduled jobs
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - environment variables and initial data loading
- [TESTING.md](TESTING.md) - the test suite and manual-testing sandboxes
- [DEPLOYMENT.md](DEPLOYMENT.md) - production
- [developer/branding-and-styles.md](developer/branding-and-styles.md) - logos, colours, CSS
