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

`SITE_DOMAIN` and `SITE_NAME` are applied to the Django `Site` record on every container start by `docker/entrypoint.sh` and by the `setup_base_database` command.

### 4.3 Start the Stack

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

This will:
1. Build the Django application image
2. Start PostgreSQL and Redis
3. Run database migrations (automatic via entrypoint)
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

If you need to populate piece-by-piece instead (e.g., to debug a specific TSV), run the individual `populate_redib_*` commands in dependency order: nodes → organizations → users → equipment → funding_agencies. See [SETUP_GUIDE.md#individual-population-commands](SETUP_GUIDE.md#individual-population-commands) for details.

### 4.6 Verify

```bash
# All containers should show "Up" or "Up (healthy)"
docker compose -f docker-compose.prod.yml ps

# Check Caddy obtained TLS certificate
docker compose -f docker-compose.prod.yml logs caddy | grep "certificate obtained"

# Visit in your browser
# https://your-domain.com
```

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

1. **Database dump** — exports the PostgreSQL database to a gzipped SQL file.
2. **Key files** — archives files not tracked in git (e.g., `.env`) into a tarball.

Both are saved to `/home/deploy/backups/redib/` with matching timestamps and automatically cleaned up after 7 days.

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
0 2 * * * cd /home/deploy/ReDIB-Portal && ./scripts/backup-db.sh >> /home/deploy/backups/redib/backup.log 2>&1
```

**Important:** The `cd /home/deploy/ReDIB-Portal &&` prefix is required — cron runs from the home directory, and the script needs to be in the project root to find `docker-compose.prod.yml`.

This runs daily at 2 AM and keeps backups for 7 days.

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
- Recipient is controlled by `ALERT_RECIPIENT` (default `coordinator@redib.net`). To change it, set the var in `.env`:
  ```
  ALERT_RECIPIENT=ops@example.com
  ```

**What this channel cannot catch:** cron daemon stopped, host powered off, script deleted, `web` container down (the command can't run). For those you need the deadman ping below.

#### Deadman-switch ping (optional but recommended)

A "deadman switch" inverts the alerting model: instead of the script paging you when it fails, an external service pages you when it **stops hearing** from the script. This closes the gap where the script can't email — no cron, no host, no script.

**Setup (using https://healthchecks.io, free tier):**

1. Sign up with `coordinator@redib.net` (or whichever operator address).
2. Create a check called `redib-backup`. Schedule: **every day**, grace period **2 hours**. Our cron runs at 02:00 UTC; the 26-hour total window handles clock skew and slow runs.
3. Copy the check's ping URL — looks like `https://hc-ping.com/<uuid>`.
4. Add it to `/home/deploy/ReDIB-Portal/.env`:
   ```
   HEALTHCHECK_URL=https://hc-ping.com/<uuid>
   ```
5. Done. The next successful run `curl`s the URL; the service emails you if a day passes with no ping.

Until `HEALTHCHECK_URL` is set, the script simply skips the ping — no errors, no noise. Alternatives with the same integration shape: Dead Man's Snitch, BetterStack Uptime, a self-hosted cron monitor. Just paste a different URL.

**Failure-mode coverage (both channels combined):**

| Failure mode | Email alert | Deadman ping |
|---|---|---|
| `pg_dump` silently broken / truncated | ✓ | ✓ |
| DB or web container down | ✓ (if web is up) | ✓ |
| web container down | ✗ | ✓ |
| Cron stopped / script deleted | ✗ | ✓ |
| Host powered off | ✗ | ✓ |

#### Off-site copy

See §6.7. Local validation and alerting catch silent corruption; only an off-site copy survives a host-level disaster. The three layers (validation → alerting → off-site) are complementary, not redundant.

### 6.5 Backing Up Additional Files

The backup script archives key files that are not tracked in git (e.g., `.env`). To change which files are backed up, edit the `BACKUP_FILES` array near the top of `scripts/backup-db.sh`:

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

To restore files from a backup:

```bash
# List contents of a file backup
tar -tzf /home/deploy/backups/redib/redib_files_YYYYMMDD_HHMMSS.tar.gz

# Extract to the project directory (overwrites existing files)
cd ~/ReDIB-Portal
tar -xzf /home/deploy/backups/redib/redib_files_YYYYMMDD_HHMMSS.tar.gz
```

### 6.6 Restore Database from Backup

```bash
# Stop application services
docker compose -f docker-compose.prod.yml stop web celery celery-beat

# Restore (replace filename with your backup)
gunzip < /home/deploy/backups/redib/redib_db_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T db \
  psql -U redib_user -d redib_db

# Restart services
docker compose -f docker-compose.prod.yml start web celery celery-beat
```

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
4. Restart web:
   ```bash
   docker compose -f docker-compose.prod.yml restart web
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

### Running Management Commands

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py <command>
```

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
# Active tasks
docker compose -f docker-compose.prod.yml exec celery \
  celery -A redib inspect active

# Scheduled tasks
docker compose -f docker-compose.prod.yml exec celery \
  celery -A redib inspect scheduled
```

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

**3. Handle the migration race condition:**

All three application containers (web, celery, celery-beat) run the same
entrypoint, which includes `migrate`. On a fresh database they all try to
create tables simultaneously. Typically one succeeds and the other two crash
with `DuplicateTable` or `UniqueViolation` errors. Check with:

```bash
docker compose -f docker-compose.prod.yml ps
```

If web or celery-beat exited or restarted, restart them — this time
migrations are already applied so the entrypoint passes cleanly:

```bash
docker compose -f docker-compose.prod.yml restart web celery-beat
```

Verify all 6 services show `Up` / `healthy` before continuing.

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
funding agencies → email templates → site config. All from the TSV files in
`data/`. The command aborts entirely on any validation error (missing FK,
bad enum), so no partial loads are possible.

All TSV-loaded users receive password `changeme123` with pre-verified
emails. The `ProfileCompletionMiddleware` will redirect users to `/profile/`
on first login if any required field (first name, last name, phone,
organization, position) is missing from the TSV data.

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

### Migration Race Condition on Fresh Database

When starting all containers against a brand-new (empty) database volume,
the web, celery, and celery-beat containers all run `migrate` via the shared
entrypoint. One wins and applies the migrations; the others crash with
`DuplicateTable` or `UniqueViolation` errors. This is harmless — restart the
failed containers and migrations will be a no-op:

```bash
docker compose -f docker-compose.prod.yml restart web celery-beat
```

This only happens on a fresh database. Normal code-update deploys
(`up -d --build`) do not trigger it because the schema already exists.

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
- [ ] Migrations applied: `docker compose -f docker-compose.prod.yml exec web python manage.py migrate` reports `No migrations to apply`.
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
- [ ] Backup script is scheduled (`scripts/backup-db.sh` in cron) and the
      first backup file landed in the configured backup dir.
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
