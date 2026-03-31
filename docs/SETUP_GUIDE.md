# ReDIB COA Portal -- Setup & Configuration Guide

Detailed configuration reference for the ReDIB Portal. For a quick first-time setup, see [QUICKSTART.md](QUICKSTART.md).

---

## Environment Configuration

### How the App Determines Its Mode

The application reads a single `.env` file in the project root (`redib/settings.py`). Three templates are provided:

| Template | Purpose | Copy Command |
|----------|---------|-------------|
| `.env.example` | Local development (venv + SQLite) | `cp .env.example .env` |
| `.env.docker` | Local Docker testing (PostgreSQL + Redis) | `cp .env.docker .env` |
| `.env.production.template` | Production VPS deployment | `cp .env.production.template .env` |

### Key Settings That Control Behavior

| Setting | Dev Default | Prod Value | Effect |
|---------|-----------|------------|--------|
| `DEBUG` | `True` | `False` | Enables debug toolbar; when False, enables HSTS, secure cookies |
| `DATABASE_URL` | `sqlite:///db.sqlite3` | `postgres://...` | Database engine |
| `USE_REDIS` | `False` | `True` | Cache backend: LocMemCache (dev) vs Redis (prod) |
| `EMAIL_BACKEND` | `console` | `django.core.mail.backends.smtp.EmailBackend` | Emails print to terminal (dev) vs real SMTP delivery (prod) |
| `SECRET_KEY` | Insecure dev default | **Must set unique value** | Cryptographic signing |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Your domain | HTTP Host header validation |
| `SITE_URL` | `https://portal.redib.net` | Your domain URL | Absolute URLs in emails |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | `redis://redis:6379/0` | Celery broker (only matters if workers are running) |

When `DEBUG=False`, Django automatically enables: HSTS, secure cookies, CSRF cookie security, and proxy SSL header detection. See `redib/settings.py`.

### Switching Between Modes

**Development to Docker testing:**
```bash
docker compose down          # if previously running
cp .env.docker .env
docker compose up -d --build
```

**Docker testing back to development:**
```bash
docker compose down
cp .env.example .env
source venv/bin/activate
python manage.py runserver
```

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

## Initial Data Setup (Detailed)

After creating the database and superuser, load the required data using the provided management commands.

**IMPORTANT**: Commands must be run in the specific order below due to data dependencies.

### Step 1: Load Email Templates

Load all required email templates (no dependencies):

```bash
python manage.py seed_email_templates
```

This creates all required email templates:
- call_published
- application_received
- feasibility_request
- feasibility_reminder
- feasibility_rejected
- evaluation_assigned
- evaluation_reminder
- resolution_accepted / resolution_pending / resolution_rejected
- acceptance_reminder
- access_scheduled
- publication_followup

### Step 2: Load ReDIB Nodes (REQUIRED FIRST)

**This must run before loading users or equipment.**

```bash
python manage.py populate_redib_nodes
```

Loads 4 ReDIB nodes from `data/nodes.csv`:
- **CIC biomaGUNE** (CICBIO) - San Sebastian
- **BioImaC** (BIOIMAC) - Murcia
- **La Fe** (LAFE) - Valencia
- **CNIC** (CNIC) - Madrid

### Step 3: Load ReDIB Users

**Requires nodes to exist** (depends on Step 2):

```bash
python manage.py populate_redib_users
```

Loads 8 core staff from `data/users.csv`:
- ReDIB Coordinator
- Node Coordinators (one per node)
- Evaluators with assigned research areas
- All users created with role assignments

### Step 4: Load Equipment

**Requires nodes to exist** (depends on Step 2):

```bash
python manage.py populate_redib_equipment
```

Loads 17 imaging devices from `data/equipment.csv`:
- MRI scanners (3T, 7T)
- PET-CT scanners
- Cyclotrons
- Optical imaging equipment
- And more...

### Updating Data with Sync Mode

To update existing data without deleting records, use `--sync` mode:

```bash
# Update nodes without deleting
python manage.py populate_redib_nodes --sync

# Update users without deleting
python manage.py populate_redib_users --sync

# Update equipment without deleting
python manage.py populate_redib_equipment --sync
```

**Use sync mode** when:
- Adding new nodes/users/equipment to existing data
- Updating information for existing records
- Preserving relationships and historical data

### CSV Data Sources

All data is loaded from CSV files in the `data/` directory:
- `data/nodes.csv` - 4 ReDIB network nodes
- `data/users.csv` - 8 core staff members
- `data/equipment.csv` - 17 imaging devices

You can edit these CSV files to customize the data before loading.

---

## Quick Test Data Setup

Instead of loading data manually with the steps above, use a single command:

```bash
python manage.py setup_test_database --reset --yes
```

This creates:
- **8 test users** with different roles (all password: `testpass123`)
- **2 nodes** (CICBIO and CNIC) with 4 equipment items
- **2 calls** (one resolved, one open)
- **4 applications** in different states (draft, feasibility review, rejected, completed)
- **Complete workflow** examples with evaluations, grants, and publications

**Test user accounts:**
- `admin@test.redib.net` - Administrator
- `coordinator@test.redib.net` - ReDIB Coordinator
- `cic@test.redib.net` - Node Coordinator for CICBIO
- `cnic@test.redib.net` - Node Coordinator for CNIC
- `eval1@test.redib.net` - Evaluator (preclinical)
- `eval2@test.redib.net` - Evaluator (clinical)
- `applicant1@test.redib.net` - Applicant
- `applicant2@test.redib.net` - Applicant

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
