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
| `EMAIL_*` | Your SMTP provider credentials |

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

Both are saved to `/home/deploy/backups/redib/` with matching timestamps and automatically cleaned up after 30 days.

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

This runs daily at 2 AM and keeps backups for 30 days.

### 6.3 Backing Up Additional Files

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

### 6.4 Restore Database from Backup

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

### 6.5 Off-site Backup (Recommended)

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

- [ ] **License**: Choose and add a license to `LICENSE` file and update `README.md` (currently says "[To be determined]")
