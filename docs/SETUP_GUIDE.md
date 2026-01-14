# ReDIB COA Portal - Setup Guide

Quick guide to get the portal running and create your first admin user.

---

## Initial Setup

### 1. Database Setup

The migrations are already created. Just run them:

```bash
# Activate virtual environment
source venv/bin/activate

# Run migrations
python manage.py migrate
```

**Expected output**: All migrations should apply successfully.

---

### 2. Create Superuser (Admin Account)

Create your first admin account:

```bash
python manage.py createsuperuser
```

**You'll be prompted for**:
- **Email address**: Your admin email (used for login)
- **First name**: Your first name
- **Last name**: Your last name
- **Password**: Strong password (won't be visible as you type)

**Example**:
```
Email address: admin@redib.net
First name: Admin
Last name: User
Password: **********
Password (again): **********
Superuser created successfully.
```

---

### 3. Start Development Server

```bash
python manage.py runserver
```

**Access the portal**:
- **Homepage**: http://localhost:8000
- **Admin**: http://localhost:8000/admin

---

## First Login

1. Go to http://localhost:8000/admin
2. Login with your superuser email and password
3. You should see the Django admin dashboard

---

## Initial Data Setup

After creating the database and superuser, load the required production data using the provided management commands.

**IMPORTANT**: Commands must be run in the specific order below due to data dependencies.

### Step 1: Load Email Templates

Load all required email templates (no dependencies):

```bash
python manage.py seed_email_templates
```

This creates all 10 required email templates:
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
- **CIC biomaGUNE** (CICBIO) - San Sebastián
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

## Quick Test Data Setup (Recommended)

Instead of creating test data manually, use the `seed_dev_data` command to automatically create a complete test environment:

```bash
python manage.py seed_dev_data --clear
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

See `../archive/TEST_SETUP.md` for detailed information about the test data structure.

---

## Running with Docker (Production-like)

If you have Docker installed:

```bash
# Start all services
docker compose up -d

# Run migrations
docker compose exec web python manage.py migrate

# Create superuser
docker compose exec web python manage.py createsuperuser

# View logs
docker compose logs -f web

# Access at http://localhost:8000
```

---

## Running Celery Workers (for background tasks)

To enable automated emails and reminders:

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
**Solution**: Make sure Celery worker and beat are running in separate terminals.

### Issue: Emails not sending
**Solution**: Check that email templates are created and marked as active in admin.

### Issue: "Error connecting to redis:6379" when logging in
**Solution**: The app is configured for local development without Redis by default (USE_REDIS=False in .env). This is normal. If you want to use Redis for caching and Celery:

1. Install Redis: `brew install redis` (macOS) or `apt-get install redis` (Linux)
2. Start Redis: `redis-server`
3. Update `.env`: Set `USE_REDIS=True`
4. Restart the Django server

For basic testing, Redis is optional - the app uses in-memory caching instead.

---


## Next Steps

Once you have the test data loaded:

1. **Login with different roles** at http://localhost:8000/accounts/login/
2. **Test the workflow** (submit APP-TEST-003, review APP-TEST-004)
3. **Explore the admin** at http://localhost:8000/admin/
4. **Test email sending** (check console output or SMTP)
5. **Test Celery tasks** (if Redis is enabled)

---

## Getting Help

- **Development Workflows**: See [DEVELOPMENT.md](DEVELOPMENT.md)
- **Testing Guide**: See [TESTING.md](TESTING.md)
- **Quick Start**: See [QUICKSTART.md](QUICKSTART.md)
- **System Design**: See [reference/redib-coa-system-design.md](reference/redib-coa-system-design.md)
- **Archived Docs**: See [archive/](archive/) for historical documentation

---

**Ready to use!** 🚀
