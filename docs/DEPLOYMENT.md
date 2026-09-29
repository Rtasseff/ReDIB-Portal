# ReDIB Portal - Production Deployment Guide

Deploy the ReDIB Portal on a Debian 13 (Trixie) VPS with Docker, Caddy (automatic HTTPS), PostgreSQL, Redis, and Celery.

## Prerequisites

- A VPS with at least 4 GB RAM running Debian 13 (Trixie)
- A registered domain name with access to DNS settings
- SMTP email credentials (host, port, username, password)
- SSH access to the VPS as root

## Architecture

```
Internet
   |
   v
[Caddy] :80/:443  -- automatic TLS via Let's Encrypt
   |
   v
[Gunicorn/Django] :8000 (internal only)
   |
   +---> [PostgreSQL] :5432 (internal only)
   +---> [Redis] :6379 (internal only)
   +---> [Celery Worker] (background email, PDF tasks)
   +---> [Celery Beat] (scheduled reminders, deadlines)
```

All services run as Docker containers on a single server. Only ports 80 and 443 are exposed to the internet.

### Memory Budget (4 GB VPS)

| Service | Limit | Notes |
|---------|-------|-------|
| PostgreSQL | 512 MB | Adequate for small-medium database |
| Redis | 128 MB | Broker + cache |
| Django/Gunicorn | 1024 MB | 2 workers, WeasyPrint headroom |
| Celery Worker | 512 MB | 2 concurrent tasks |
| Celery Beat | 256 MB | Lightweight scheduler |
| Caddy | ~50 MB | Not limited |
| OS + Docker | ~500 MB | Kernel, systemd, daemon |
| **Total** | **~3 GB** | **~1 GB buffer** |

---

## Step 1: VPS Initial Setup

### 1.1 Connect and Update

```bash
ssh root@YOUR_SERVER_IP
apt update && apt upgrade -y
```

### 1.2 Create a Deploy User

```bash
adduser deploy
usermod -aG sudo deploy
```

Copy your SSH key for passwordless login (run this on your **local machine**):

```bash
ssh-copy-id deploy@YOUR_SERVER_IP
```

### 1.3 Harden SSH

Edit `/etc/ssh/sshd_config` on the server:

```
PermitRootLogin no
PasswordAuthentication no
Port 22
Port 2222
ClientAliveInterval 120
```

> **Note:** IONOS cloud-init may override `PasswordAuthentication` via `/etc/ssh/sshd_config.d/50-cloud-init.conf`. Check that file and set it to `no` if needed:
> ```bash
> sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config.d/50-cloud-init.conf
> ```

Then restart SSH:

```bash
systemctl restart sshd
```

> **Important:** Test SSH access as `deploy` in a separate terminal before closing your root session.

### 1.4 Configure Firewall

```bash
apt install ufw -y
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 2222/tcp comment 'SSH fallback'
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

Verify:

```bash
ufw status verbose
```

> **Note:** The IONOS cloud-level firewall also controls inbound access. Currently, SSH (ports 22 and 2222) is restricted to the office network by IT policy. Web traffic (80/443) is open to all. Any changes to the cloud firewall must be made through the IONOS web panel.

### 1.5 Install fail2ban

```bash
apt install fail2ban -y
systemctl enable --now fail2ban
```

The default configuration protects SSH out of the box (5 failed attempts = 10-minute ban). Verify:

```bash
fail2ban-client status sshd
```

### 1.6 Enable Automatic Security Updates

```bash
apt install unattended-upgrades -y
dpkg-reconfigure -plow unattended-upgrades
```

Select "Yes" when prompted.

---

## Step 2: Install Docker

SSH in as the deploy user for all remaining steps:

```bash
ssh deploy@YOUR_SERVER_IP
```

### 2.1 Install Docker Engine

```bash
# Install prerequisites
sudo apt install ca-certificates curl gnupg -y

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add the Docker repository
echo "deb [arch=$(dpkg --print-architecture) \
  signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin -y
```

> **Note:** If Docker does not yet have a Trixie repository, substitute `bookworm` for `$(lsb_release -cs)` in the repository URL above. Docker built for Bookworm runs fine on Trixie.

### 2.2 Allow Deploy User to Use Docker

```bash
sudo usermod -aG docker deploy
```

Log out and back in for the group change to take effect:

```bash
exit
ssh deploy@YOUR_SERVER_IP
```

### 2.3 Verify

```bash
docker run --rm hello-world
```

---

## Step 3: DNS Configuration

In your domain registrar's DNS settings, create an **A record** pointing to your VPS:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | @ | YOUR_SERVER_IP | 3600 |

If you also want `www`:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | www | YOUR_SERVER_IP | 3600 |

Wait for propagation (usually 5-30 minutes, can take up to 48 hours):

```bash
dig +short your-domain.com
# Should return YOUR_SERVER_IP
```

> **Important:** Caddy will automatically obtain a TLS certificate from Let's Encrypt once DNS resolves to your server. If DNS is not ready, Caddy will retry.

---

## Step 4: Deploy the Application

### 4.1 Clone the Repository

```bash
cd ~
git clone https://github.com/YOUR_ORG/ReDIB-Portal.git
cd ReDIB-Portal
```

### 4.2 Configure Environment

```bash
cp .env.production.template .env
nano .env
```

Fill in every value. The critical ones:

| Variable | How to Set |
|----------|------------|
| `SECRET_KEY` | `python3 -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DOMAIN` | Your domain (e.g., `portal.redib.net`) — used by Caddy |
| `ALLOWED_HOSTS` | Same domain (e.g., `portal.redib.net,www.portal.redib.net`) |
| `CSRF_TRUSTED_ORIGINS` | With scheme (e.g., `https://portal.redib.net`) |
| `SITE_URL` | Full URL (e.g., `https://portal.redib.net`) — used in emailed links |
| `SITE_DOMAIN` | Host only (e.g., `portal.redib.net`) — written to Django Site record, used by allauth email templates |
| `SITE_NAME` | Display name in emails (default `ReDIB COA Portal`) |
| `POSTGRES_PASSWORD` | A strong random password |
| `DATABASE_URL` | Update password to match `POSTGRES_PASSWORD` |
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_USE_TLS` | SMTP connection (e.g., `smtp.ionos.es` / `587` / `True`) |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | SMTP credentials |
| `DEFAULT_FROM_EMAIL` | Envelope-from address (e.g., `noreply@redib.net`) |
| `CONTACT_EMAIL` | Contact address rendered in every email template (e.g., `info@redib.net`) |
| `USE_REDIS` | `True` |
| `REDIS_URL` | `redis://redis:6379/0` (default — matches the Redis container) |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | `redis://redis:6379/0` |
| `SENTRY_DSN` | _(optional)_ Sentry project DSN for error reporting; leave blank to disable |
| `CALL_ANNOUNCEMENT_EMAILS_ENABLED` | `False`. Leave it off until backlog #41 is done. It mass-mails every account. |

`SITE_DOMAIN` and `SITE_NAME` are applied to the Django `Site` record on every container start by `docker/entrypoint.sh` and by the `setup_base_database` command. Defaults, dev values and every other variable: [SETUP_GUIDE.md § Environment Configuration](SETUP_GUIDE.md#environment-configuration).

The backup settings `ALERT_RECIPIENT` and `HEALTHCHECK_URL` are **not** `.env` settings. `scripts/backup-db.sh` reads its own shell environment and never loads `.env`, so they go on the cron line in [§ 6.2](#62-schedule-daily-backups). An older `.env` that still has them is harmless: they are ignored there.

`.env` is read when a container is **created**. After changing it, run `docker compose -f docker-compose.prod.yml up -d`. `restart` keeps the old values.

### 4.3 Start the Stack

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

This will:
1. Build the Django application image
2. Start PostgreSQL and Redis
3. Run database migrations (automatic via entrypoint, one container at a time: see #37 under [Deploying Code Updates](#deploying-code-updates))
4. Collect static files (automatic via entrypoint)
5. Seed email templates (automatic via entrypoint)
6. Start Gunicorn, Celery, Celery Beat, and Caddy

Watch the logs to confirm everything starts cleanly:

```bash
docker compose -f docker-compose.prod.yml logs -f
```

Press `Ctrl+C` to stop following logs.

### 4.4 Create the Admin Superuser

```bash
docker compose -f docker-compose.prod.yml exec web \
  python manage.py createsuperuser
```

Fix allauth email verification for the superuser:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py shell -c "
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.get(is_superuser=True)
EmailAddress.objects.get_or_create(user=u, email=u.email, defaults={'verified': True, 'primary': True})
"
```

### 4.5 Load Initial ReDIB Data

Run the base database setup command, which populates nodes, organizations, users, equipment, funding agencies, email templates, and configures the Site record — all in dependency order:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py setup_base_database
```

It stops at the first failing step with a non-zero exit (`CommandError: Step N failed: <reason>`). The accounts it creates have no usable password: each person sets one through "Forgot password" on the login page.

If you need to populate piece-by-piece instead (e.g., to debug a specific TSV), run the individual `populate_redib_*` commands in dependency order: organizations → nodes → users → equipment → funding agencies. See [SETUP_GUIDE.md § Individual population commands](SETUP_GUIDE.md#individual-population-commands) and [data/README.md](../data/README.md) for the rules.

### 4.6 Verify

```bash
# All containers should show "Up" or "Up (healthy)"
docker compose -f docker-compose.prod.yml ps

# Check Caddy obtained TLS certificate
docker compose -f docker-compose.prod.yml logs caddy | grep "certificate obtained"

# Visit in your browser
# https://your-domain.com

# The user guide is rendered from docs/USER_GUIDE.md at request time, so it
# also confirms the docs/ exception in .dockerignore survived the build
# https://your-domain.com/help/user-guide/

# Same check from the shell -- should list USER_GUIDE.md and nothing else
docker compose -f docker-compose.prod.yml exec web ls /app/docs
```

> **Note on `.dockerignore`:** `docs/` and `*.md` are excluded from the build
> context, with a single trailing `!docs/USER_GUIDE.md` exception so the guide
> ships in the image. That exception must stay the **last** rule in the file
> (last match wins). If it is ever dropped, `manage.py migrate` — which the
> entrypoint runs on every start — fails the system check `core.E001` rather
> than letting `/help/user-guide/` 404 silently.

---

## Step 5: Email DNS Records (SPF/DKIM/DMARC)

Your SMTP provider handles sending, but you need DNS records so emails aren't flagged as spam.

### SPF Record

Add a TXT record to your domain that authorizes your email provider to send on your behalf:

| Type | Name | Value |
|------|------|-------|
| TXT | @ | `v=spf1 include:_spf.your-provider.com ~all` |

Common provider SPF includes:
- **IONOS**: `include:_spf.perfora.net`
- **Brevo**: `include:spf.sendinblue.com`
- **Gmail/Google Workspace**: `include:_spf.google.com`

### DKIM

Check your email provider's control panel for a DKIM key to add as a TXT record. This is provider-specific — consult their documentation.

### DMARC

Add a basic DMARC policy:

| Type | Name | Value |
|------|------|-------|
| TXT | _dmarc | `v=DMARC1; p=quarantine; rua=mailto:admin@your-domain.com` |

### Verify Email Delivery

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py shell -c "
from django.core.mail import send_mail
send_mail('ReDIB Portal Test', 'Email delivery is working.', None, ['your-email@example.com'])
"
```

Check the received email headers for `spf=pass`, `dkim=pass`, `dmarc=pass`.

---

## Step 6: Backups

The backup script (`scripts/backup-db.sh`) handles two things:

1. **Database dump**: `redib_db_<timestamp>.sql.gz`, the PostgreSQL database as gzipped SQL.
2. **Files**: `redib_files_<timestamp>.tar.gz`, with `.env` at the top and **every uploaded
   file** under `media/`. Uploads include newsletters, signed application PDFs from earlier
   calls, and anything uploaded in future. They are copied out of the `media_volume` Docker
   volume (`/app/media` in `web`) on every run, so a new kind of upload is covered without
   anyone having to remember it (backlog #89, 2026-09-29).

Both are saved to `/home/deploy/backups/redib/` with matching timestamps and cleaned up
after 7 days. Each run keeps a full copy of the uploads, so the files archive grows with
them. Check `du -sh /home/deploy/backups/redib` now and then. If the media copy fails (for
example, `web` is down), the whole run fails. You get the alert email (§ 6.4) and older
backups are kept.

### 6.1 Set Up Automated Backups

```bash
# Create backup directory
mkdir -p /home/deploy/backups/redib

# Test the backup manually
cd ~/ReDIB-Portal
./scripts/backup-db.sh

# Verify the backup was created
ls -lh /home/deploy/backups/redib/
```

### 6.2 Schedule Daily Backups

```bash
crontab -e
```

Add this line:

```
0 2 * * * cd /home/deploy/ReDIB-Portal && ALERT_RECIPIENT=coordinator@redib.net HEALTHCHECK_URL= ./scripts/backup-db.sh >> /home/deploy/backups/redib/backup.log 2>&1
```

**Important:** The `cd /home/deploy/ReDIB-Portal &&` prefix is required. Cron runs from the home directory, and the script needs to be in the project root to find `docker-compose.prod.yml`.

**Script settings go on this line, not in `.env`.** The script reads `ALERT_RECIPIENT`, `HEALTHCHECK_URL`, `RETENTION_DAYS`, `MIN_SIZE_RATIO_PERCENT` and `BACKUP_DIR` from its own environment and never loads `.env`. The values shown are the defaults, so the line above behaves exactly like the bare one. Full list: [SETUP_GUIDE.md](SETUP_GUIDE.md#environment-configuration).

This runs daily at 2 AM server time and keeps backups for 7 days.

### 6.3 Validation and Pruning Safety

The backup script is designed so that **pruning only runs after a verifiably good backup**. If any validation gate fails, the script exits with a non-zero status **before** the retention prune — so older backups stay on disk even if today's run is broken.

Validation gates, in order:

1. **`set -euo pipefail`** — any command failure in the dump pipeline (e.g., container down, `pg_dump` errors, disk full) aborts immediately.
2. **Non-empty** — the output file must be >0 bytes.
3. **PostgreSQL dump header** — the first ~20 decompressed lines must contain the `PostgreSQL database dump` marker. Catches gzip-of-empty, wrong database name, and roles without `SELECT` permissions — cases where `pg_dump` exits 0 but the content is useless.
4. **Size ratio** — the new dump must be at least **50%** of the most recent prior dump (configurable via `MIN_SIZE_RATIO_PERCENT`). Catches partial or truncated dumps where the header renders correctly but the body is silently missing. Skipped automatically on the very first run.

**Consequence:** if the backup process silently degrades, you will see failed runs pile up in `backup.log` and extra `redib_db_*.sql.gz` files stick around past the 7-day window — **you will not lose the last known-good backup**. We deliberately err toward keeping too much rather than too little; a cluttered backup dir is recoverable, zero good backups is not.

**After a failed run**, the bad dump is preserved (not deleted) so it can be inspected. Check `/home/deploy/backups/redib/backup.log` for the error message and the path of the preserved file.

**Legitimate shrinkage** (e.g., after a large data cleanup) will trip gate 4. To allow it through once, rerun manually with a lower ratio:

```bash
cd ~/ReDIB-Portal
MIN_SIZE_RATIO_PERCENT=10 ./scripts/backup-db.sh
```

After that run completes, subsequent automated runs will compare against the new smaller baseline and return to normal.

### 6.4 Alerting

Two independent channels watch the backup job. They catch different failure modes — keep both.

#### In-script failure email

On any non-zero exit the script sends a plain-text alert via the portal's SMTP setup (`noreply@redib.net` → `coordinator@redib.net`). This reuses the Django email stack, so no extra credentials live on the host.

Mechanics:

- The Django management command `send_ops_alert` (`communications/management/commands/send_ops_alert.py`) wraps `django.core.mail.send_mail` synchronously (no Celery), so SMTP failures surface as non-zero exit codes and alerts still go out if Redis is down.
- The shell script installs an `EXIT` trap; any failed validation gate or shell error fires one email with the exit code, hostname, backup directory, and the tail of `backup.log`.
- Recipient is controlled by `ALERT_RECIPIENT` (default `coordinator@redib.net`). To change it, edit it **on the cron line** (§ 6.2). Setting it in `.env` does nothing, because the script doesn't read `.env`.
- To test the channel by hand:
  ```bash
  docker compose -f docker-compose.prod.yml exec -T web python manage.py send_ops_alert \
    --recipient you@example.org --subject "[ReDIB] alert test" --body "test"
  ```
  It prints `Alert sent to …`, or fails with a non-zero exit if SMTP refuses.

**What this channel cannot catch:** cron daemon stopped, host powered off, script deleted, `web` container down (the command can't run). For those you need the deadman ping below.

#### Deadman-switch ping (optional but recommended)

A "deadman switch" inverts the alerting model: instead of the script paging you when it fails, an external service pages you when it **stops hearing** from the script. This closes the gap where the script can't email — no cron, no host, no script.

**Setup (using https://healthchecks.io, free tier):**

1. Sign up with `coordinator@redib.net` (or whichever operator address).
2. Create a check called `redib-backup`. Schedule: **every day**, grace period **2 hours**. Our cron runs at 02:00 server time; the 26-hour total window handles clock skew and slow runs.
3. Copy the check's ping URL. It looks like `https://hc-ping.com/<uuid>`.
4. Put it on the cron line from § 6.2 (`crontab -e`), not in `.env`:
   ```
   ... HEALTHCHECK_URL=https://hc-ping.com/<uuid> ./scripts/backup-db.sh ...
   ```
5. Done. The next successful run `curl`s the URL; the service emails you if a day passes with no ping. The log line `Deadman ping sent.` in `backup.log` confirms it.

Until `HEALTHCHECK_URL` is set, the script simply skips the ping — no errors, no noise. Alternatives with the same integration shape: Dead Man's Snitch, BetterStack Uptime, a self-hosted cron monitor. Just paste a different URL.

**Failure-mode coverage (both channels combined):**

| Failure mode | Email alert | Deadman ping |
|---|---|---|
| `pg_dump` silently broken / truncated | ✓ | ✓ |
| db container down | ✓ | ✓ |
| web container down | ✗ | ✓ |
| Cron stopped / script deleted | ✗ | ✓ |
| Host powered off | ✗ | ✓ |

#### Off-site copy

See §6.7. Local validation and alerting catch silent corruption; only an off-site copy survives a host-level disaster. The three layers (validation → alerting → off-site) are complementary, not redundant.

### 6.5 Backing Up Additional Files

Uploaded files are always included (above). For anything else on the host that isn't
tracked in git, edit the `BACKUP_FILES` array near the top of `scripts/backup-db.sh`:

```bash
BACKUP_FILES=(
    ".env"
    # Add more paths here (relative to the project root).
    # Files and directories are both supported.
    # "certs/"
    # "config/local_settings.py"
)
```

Each backup run produces a `redib_files_TIMESTAMP.tar.gz` alongside the database dump. If a listed file does not exist, the script logs a warning but continues without failing.

To restore files from a backup, unpack it somewhere temporary first. Unpacking it into the
project directory would overwrite `.env` and leave the uploads in a folder the containers
never read.

```bash
# List contents of a file backup
tar -tzf /home/deploy/backups/redib/redib_files_YYYYMMDD_HHMMSS.tar.gz

# Unpack to a temporary directory
mkdir -p /tmp/redib-restore
tar -xzf /home/deploy/backups/redib/redib_files_YYYYMMDD_HHMMSS.tar.gz -C /tmp/redib-restore

# .env: compare before replacing the live one
diff /tmp/redib-restore/.env ~/ReDIB-Portal/.env

# Uploaded files: copy back into the media volume (adds and overwrites, deletes nothing)
cd ~/ReDIB-Portal
docker compose -f docker-compose.prod.yml cp /tmp/redib-restore/media/. web:/app/media/

rm -rf /tmp/redib-restore
```

### 6.6 Restore Database from Backup

The dump is plain SQL with no `DROP` statements (`pg_dump --no-owner --no-acl`), so it
must go into an **empty** database. Piped over the live one, it fails on every existing
table and leaves a mix of old and restored data.

```bash
cd ~/ReDIB-Portal

# 0. Keep what is there now, in case you need to come back to it
./scripts/backup-db.sh

# 1. Stop everything that holds a database connection
docker compose -f docker-compose.prod.yml stop web celery celery-beat

# 2. Replace the database with an empty one (POSTGRES_USER is the superuser in the db container)
docker compose -f docker-compose.prod.yml exec -T db dropdb -U redib_user redib_db
docker compose -f docker-compose.prod.yml exec -T db createdb -U redib_user -O redib_user redib_db

# 3. Load the dump, stopping at the first error (replace the filename)
gunzip < /home/deploy/backups/redib/redib_db_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T db \
  psql -v ON_ERROR_STOP=1 -U redib_user -d redib_db

# 4. Start the app. The entrypoint's migrate applies anything newer than the dump.
docker compose -f docker-compose.prod.yml start web celery celery-beat
```

Afterwards run `migrate --check` and the counts snippet from
[Full Database Reset § 6](#full-database-reset-and-reload). If the restore is meant to
roll back a deploy, check out the matching commit and rebuild first, so the code and the
schema agree.

### 6.7 Off-site Backup (Recommended)

Copy backups to another server or object storage periodically:

```bash
# Example with rsync
rsync -avz /home/deploy/backups/redib/ user@backup-server:/backups/redib/
```

---

## Step 7: Monitoring

### 7.1 Sentry (Error Tracking)

1. Sign up at [sentry.io](https://sentry.io) (free tier available)
2. Create a Django project
3. Copy the DSN to `.env`:
   ```
   SENTRY_DSN=https://your-key@sentry.io/your-project-id
   ```
4. Recreate the containers so they pick up the new `.env` (`restart` would not):
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

### 7.2 Log Viewing

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f celery
docker compose -f docker-compose.prod.yml logs -f caddy

# Last 100 lines
docker compose -f docker-compose.prod.yml logs --tail=100 web
```

### 7.3 Disk Space

```bash
# System disk usage
df -h

# Docker-specific disk usage
docker system df

# Clean unused Docker resources (safe to run periodically)
docker system prune -f
```

---

## Step 8: Maintenance

### Deploying Code Updates

```bash
cd ~/ReDIB-Portal
git pull origin main
docker compose -f docker-compose.prod.yml up -d --build
```

The entrypoint script runs migrations and collectstatic automatically on every restart.
It also reruns `seed_email_templates`: a template switched off with the Django admin's
**Is active** toggle stays off across deploys, but subject and body edits made in the
admin do **not** survive — the seed overwrites them, deliberately (the seed is the source).

> **`git pull` alone changes nothing that runs.** The `web`, `celery` and
> `celery-beat` services all `build: .` with **no source bind mount**, so the code is baked
> into the image. Between the pull and the `--build`, the checkout on disk and
> the code in the containers are different versions — `manage.py` still runs the
> old one. Found the hard way on 2026-08-21: a management command re-run after a
> pull, to verify a fix that had just been merged, reported the pre-fix
> behaviour and looked exactly like the fix having failed.
>
> So: **never verify a code change with a management command until after the
> rebuild.** If you need to check new logic against live data before deploying
> it, pipe the *new source* into `manage.py shell` — and audit first that every
> write in it sits behind a `--dry-run` branch.

> **Migrations and the template seed run one container at a time (#37, fixed
> 2026-09-14).** All three app containers still run the same entrypoint at the
> same moment, but `migrate` and `seed_email_templates` are now wrapped in
> `manage.py run_locked`, which holds a Postgres advisory lock for the duration.
> What the logs should show on a migration-bearing deploy: **one** container
> logs `Applying <app>.<nnnn>... OK`, the other two wait on the lock (silently —
> there is no "waiting" line) and then log `No migrations to apply`. No
> `DuplicateColumn` traceback, no restart, and `django_migrations` gains one row
> per migration, not three. If you see a traceback in that step it is a real
> failure now, not the race.
>
> Confirm the schema the same way as before — these are the actual evidence:
>
> ```bash
> # 1. anything still unapplied?  exit 0 = nothing pending
> docker compose -f docker-compose.prod.yml exec web python manage.py migrate --check
> # 2. did the schema actually change?  query the field the migration added
> docker compose -f docker-compose.prod.yml exec web python manage.py shell -c \
>   "from applications.models import Application; print(Application.objects.filter(execution_end__isnull=False).count())"
> ```
>
> History, for reading old logs: before the lock the symptom inverted with the
> kind of migration — a choices-only `AlterField` left **three** rows in
> `django_migrations` (2026-08-20), real DDL crashed the two losers with
> `DuplicateColumn` until `restart: unless-stopped` brought them back
> (2026-08-21, `calls/0004`, ~40 s of downtime). The three duplicate rows from
> 08-20 are still in the table; they are harmless and were left alone.
>
> **Which container runs the seed first varies, so grep all three.** "N
> templates created" appears only in whichever container got the lock first;
> the other two find everything already there. The services are `web`,
> `celery`, `celery-beat`.

After the rebuild, spot-check the app plus the user guide (the guide is read
from `docs/USER_GUIDE.md` inside the image, so it catches a broken build
context):

```bash
# https://your-domain.com
# https://your-domain.com/help/user-guide/
```

### Running Management Commands

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py <command>
```

> This runs the code **in the image**, not the code in `~/ReDIB-Portal`. See the
> warning under *Deploying Code Updates*. **The same goes for `data/*.tsv`:** a loader
> reads the copy baked in at the last `--build`, not the file you just edited. To check an
> edited file before the next rebuild, copy it into the running container first:
>
> ```bash
> docker compose -f docker-compose.prod.yml cp data/users.tsv web:/app/data/users.tsv
> ```
>
> The copy lasts until the container is recreated, and the next build bakes in the
> same committed file. `scripts/check_role_drift.py` always reads
> `/app/data/users.tsv`, so this is the way to point it at your edit.

**People: the database is the authority, and `data/users.tsv` is its export.** Change a
user or a role in the admin or the shell, then write the file from the database and
commit it:

```bash
# -T, so the redirect writes the host's checkout, not the container's
docker compose -f docker-compose.prod.yml exec -T web \
  python manage.py export_redib_users > data/users.tsv
git diff data/users.tsv   # only the change you made
```

`--format xlsx` writes the spreadsheet copy for SharePoint. The recipes (add a user, add
an evaluator, retire a role, add equipment, add an organization) are in
[data/README.md § Recipes](../data/README.md#recipes).

**`populate_redib_users` is never run by a deploy.** The entrypoint runs `migrate`,
`collectstatic` and `seed_email_templates` only. Production has no routine need for a
users load any more. If one is ever needed, it is a deliberate, separate act with a
required order:

```bash
# 1. read-only: what do the DB and data/users.tsv disagree about?
docker compose -f docker-compose.prod.yml exec -T web \
  python manage.py shell < scripts/check_role_drift.py
# 2. write-free: exactly what would this load change?
docker compose -f docker-compose.prod.yml exec web \
  python manage.py populate_redib_users --dry-run
# 3. only if step 2 lists exactly the changes you intend, and no others
docker compose -f docker-compose.prod.yml exec web \
  python manage.py populate_redib_users
```

Do not skip step 1. Pass `--tsv` a file holding only the header and the rows you mean to
load. The load is all-or-nothing: a bad row aborts it with nothing written. Until the
first export after the `commands-cleanup` deploy, the committed file lists five retired
evaluators under `roles` (#81), and a full-file run would re-activate them; the export
moves them to `retired_roles`. `populate_redib_users` has no `--sync` (#83).

The other loaders (`populate_redib_equipment`, `populate_redib_nodes`,
`populate_redib_funding_agencies`) are safe to rerun after a rebuild. Their files are the
authority.

Examples:

```bash
# Django shell
docker compose -f docker-compose.prod.yml exec web python manage.py shell

# Database shell
docker compose -f docker-compose.prod.yml exec web python manage.py dbshell

# Check migration status
docker compose -f docker-compose.prod.yml exec web python manage.py showmigrations
```

### Restarting Services

```bash
# Restart a single service
docker compose -f docker-compose.prod.yml restart web

# Restart everything
docker compose -f docker-compose.prod.yml restart

# Full stop and start (e.g., after .env changes)
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

### Checking Celery Tasks

```bash
# Tasks the worker is running right now
docker compose -f docker-compose.prod.yml exec celery \
  celery -A redib inspect active

# Tasks the worker holds with a future ETA/countdown (NOT the beat schedule)
docker compose -f docker-compose.prod.yml exec celery \
  celery -A redib inspect scheduled
```

**The beat schedule lives in code**, in `app.conf.beat_schedule` in `redib/celery.py`.
Times are Europe/Madrid (`CELERY_TIMEZONE`). What each job does is in
[ARCHITECTURE.md](ARCHITECTURE.md). The `celery-beat` container runs that file as of the
last `--build`. To list what the image will schedule:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py shell -c \
  "from redib.celery import app; [print(k, v['task'], v['schedule']) for k, v in sorted(app.conf.beat_schedule.items())]"
```

On 2026-09-28 that prints nine entries. The tenth, `send-completion-reminders`, is
paused (below). Beat and the worker log at `warning` level, so a job that ran normally
leaves no log line. To confirm a mail-sending job ran, look for its rows in the admin
under **Email Logs**.

### Pausing and resuming a scheduled job

A beat job is paused by **commenting out its entry** in `app.conf.beat_schedule` in
`redib/celery.py`. The task function stays, and so do its tests. Beat simply stops
calling it. The live example is `send-completion-reminders`, paused on prod on
2026-09-09 (backlog #80).

**To pause:**

1. Comment out the entry and put a dated `PAUSED` comment above it, the way the
   completion-reminder block does. Say why, which emails it silences, what happens on
   resume, and which backlog item restores it.
2. Commit, push, and deploy (`git pull` then `up -d --build`). **Beat only sees the
   change after the rebuild.** Editing the file on disk does nothing.
3. Run the listing command above and check the entry is gone.

**To resume:** uncomment the entry, remove or date the `PAUSED` note, deploy, and check
the listing again.

Things to know before you pause or resume:

- **Nothing queues up while a job is paused.** The next run after resuming is simply the
  next scheduled time. Whether it then catches up on missed work depends on the task.
  The completion reminder fires only on exact cadence days, so it resumes at the next
  checkpoint and skips the ones in between (the comment in `redib/celery.py` spells this
  out).
- **To silence one email without a deploy**, untick **Is active** on its template under
  **Email Templates** in the admin. It stays off across deploys, because the seed
  preserves `is_active`. Each suppressed send then leaves a `failed` "Template … not
  found" row in Email Logs. The job itself keeps running, so this only helps when the
  email is all the job does.
- Removing an entry entirely, as opposed to commenting it out, also works, but it loses
  the note that explains why it's off.

### Updating Base Images (PostgreSQL, Redis, Caddy)

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### Full Database Reset and Reload

Use this procedure to wipe the database and reload all reference data from
the TSV files — for example, when refreshing a test environment with
production data or recovering from a corrupted database.

> **Warning:** This destroys all data (applications, calls, evaluations,
> publications, user accounts) except what is re-created by the load
> commands. Back up first if needed (`scripts/backup-db.sh`).

**1. Bring down containers and remove the database volume:**

```bash
docker compose -f docker-compose.prod.yml down
docker volume rm redib-portal_postgres_data
```

**2. Rebuild and start all containers:**

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

The entrypoint auto-runs: migrations, collectstatic, email template seeding,
and site configuration.

**3. Check the start-up:**

Since #37 (2026-09-14), `migrate` runs under a Postgres advisory lock. On an
empty database, one of `web` / `celery` / `celery-beat` creates every table,
while the other two wait and then log `No migrations to apply`. No container
should crash or restart. Check with:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml exec web python manage.py migrate --check
```

All 6 services should show `Up` / `healthy`, and `migrate --check` should exit
0. A container that is restarting is now a real failure, so read its log
(`logs <service>`) rather than restarting it.

**4. Create the superuser:**

```bash
docker compose -f docker-compose.prod.yml exec web \
  python manage.py createsuperuser
```

Do this **before** loading data so `setup_base_database` preserves the
superuser account.

**5. Load all reference data:**

```bash
docker compose -f docker-compose.prod.yml exec web \
  python manage.py setup_base_database
```

This loads in dependency order: organizations → nodes → users → equipment →
funding agencies → email templates → site config. All from the TSV files
**baked into the image**, so rebuild after any `data/` change. On a bad row
(missing FK, bad enum) it stops at that step with a non-zero exit
(`CommandError: Step N failed: <reason>`). The steps before it stay loaded; the
failed step itself writes nothing. Fix the TSV, rebuild, and run it again:
reruns are idempotent. Failure modes by loader:
[data/README.md](../data/README.md#when-a-load-fails-part-way).

TSV-loaded users are created with pre-verified emails and no usable password:
each sets one with "Forgot password" on the login page.
The `ProfileCompletionMiddleware` will redirect non-staff users to `/profile/`
on first login if any required field (first name, last name, phone,
organization, position) is missing from the TSV data.

Note what this does **not** restore: every applicant account, call and
application. It rebuilds reference data only. To recover a working production
database, restore a backup ([§ 6.6](#66-restore-database-from-backup)) instead.

**6. Verify:**

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py shell -c "
from core.models import User, Node, Equipment, Organization, UserRole
from applications.models import FundingAgency
print('orgs:', Organization.objects.count())
print('nodes:', Node.objects.count())
print('users:', User.objects.count())
print('equipment:', Equipment.objects.count())
print('funding:', FundingAgency.objects.count())
for role in ['coordinator', 'node_coordinator', 'evaluator']:
    print(f'  {role}:', UserRole.objects.filter(role=role, is_active=True).count())
"
```

Then visit `https://portal.redib.net/` and log in as the superuser to
confirm the dashboard loads.

---

## Troubleshooting

### CSRF Errors on Form Submissions

- Verify `CSRF_TRUSTED_ORIGINS` in `.env` includes `https://your-domain.com`
- Verify `SECURE_SSL_REDIRECT=False` (Caddy handles HTTPS, not Django)

### Caddy Not Getting a TLS Certificate

- Verify DNS: `dig +short your-domain.com` should return your server IP
- Verify firewall: `sudo ufw status` should show 80 and 443 allowed
- Check Caddy logs: `docker compose -f docker-compose.prod.yml logs caddy`

### Media Files Return 404

- Verify media volume is mounted in both `web` and `caddy` services
- Check uploads exist: `docker compose -f docker-compose.prod.yml exec web ls /app/media/`

### Static Files Missing or Broken

- Check collectstatic ran: `docker compose -f docker-compose.prod.yml logs web | grep "static"`
- Re-run manually: `docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput`

### High Memory Usage

```bash
# Check per-container usage
docker stats --no-stream

# If web is using too much, reduce workers in Dockerfile CMD
# If celery is using too much, reduce --concurrency in docker-compose.prod.yml
```

### `DuplicateTable` / `DuplicateColumn` / `UniqueViolation` at start-up

This was the migration race (#37): all three app containers ran `migrate` at
once. It has been fixed since 2026-09-14. The entrypoint wraps `migrate` and
`seed_email_templates` in `manage.py run_locked`, a Postgres advisory lock. If
you see one of these errors now, it is **not** the old race. Check that the
image really is current (`up -d --build`), then read the full traceback. Old
logs from before the fix are explained under
[Deploying Code Updates](#deploying-code-updates).

### Database Connection Errors

- Check the db container: `docker compose -f docker-compose.prod.yml logs db`
- Verify `DATABASE_URL` password matches `POSTGRES_PASSWORD` in `.env`

### Emails Not Sending

- Confirm `DEBUG=False` in production. When `DEBUG=True`, `CELERY_TASK_ALWAYS_EAGER` is set to `True` (see `redib/settings.py`), causing tasks to run synchronously in the web process instead of being queued to the Celery worker.
- Check celery logs: `docker compose -f docker-compose.prod.yml logs celery`
- Test email manually (see Step 5)
- Verify `EMAIL_BACKEND` is set to SMTP, not console

---

## Pre-Launch Checklist

Run through this list once before cutting over production traffic and again
before each deploy.

**Environment & secrets**
- [ ] `.env` is populated from `.env.production.template`; every `CHANGE_ME`
      or empty value is set.
- [ ] `SECRET_KEY` is a fresh random string (never reuse dev default).
- [ ] `DEBUG=False`.
- [ ] `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` match the real domain(s).
- [ ] `SITE_URL`, `SITE_DOMAIN`, `SITE_NAME` match the real host.
- [ ] `POSTGRES_PASSWORD` is strong and matches the one inside `DATABASE_URL`.
- [ ] SMTP credentials tested (see Step 5 in this guide).

**Data**
- [ ] Migrations applied: `docker compose -f docker-compose.prod.yml exec web python manage.py migrate --check` exits 0.
- [ ] Email templates seeded (the entrypoint runs `seed_email_templates` on
      every start — confirm in the web container logs).
- [ ] Real reference data loaded via `setup_base_database` **or** TSVs in
      `data/` populated via the individual `populate_redib_*` commands.
      Verify in the admin: Nodes, Equipment, Organizations, Users,
      FundingAgencies all non-empty.
- [ ] Superuser account created and its allauth `EmailAddress` row marked
      verified + primary (see Step 4.4 in this guide).
- [ ] Django `Site` record domain and name match `SITE_DOMAIN` / `SITE_NAME`
      (the entrypoint sets this, but verify once via the Django admin).

**Runtime**
- [ ] All containers healthy: `docker compose -f docker-compose.prod.yml ps`
      shows `web`, `db`, `redis`, `celery`, `celery-beat`, `caddy` as `Up`.
- [ ] Caddy has obtained its Let's Encrypt certificate — hit `https://<domain>/`
      in a browser and confirm the padlock.
- [ ] An end-to-end smoke test: register a new user, verify the verification
      email arrives, log in, create a draft application, submit, run through
      the feasibility workflow.
- [ ] Backup script is scheduled (`scripts/backup-db.sh` in cron, with
      `ALERT_RECIPIENT` / `HEALTHCHECK_URL` on the cron line, not in `.env`) and
      the first backup file landed in the configured backup dir.
- [ ] Sentry (if configured) receives its first deploy event.

**Monitoring & operations**
- [ ] Someone owns the `info@redib.net` (or equivalent) inbox for inbound
      user support.
- [ ] The daily Celery Beat tasks ran successfully at least once: check the
      `EmailLog` model in the admin for recent rows.
- [ ] Log rotation is configured on the VPS (Docker logs can grow without
      bound otherwise).

**Governance**
- [ ] **License**: Choose and add a license to `LICENSE` file and update
      `README.md` (currently says "[To be determined]").
- [ ] Access to the production VPS (SSH keys, `sudo`) is limited to the
      people who need it.
- [ ] Credentials (SMTP password, Postgres password, SECRET_KEY) are stored
      in a password manager; the `.env` file is not committed anywhere.
