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

After logging in to the admin, set up the core data:

### Create the 4 ReDIB Nodes

Navigate to **Core > Nodes** and create:

1. **CIC biomaGUNE**
   - Code: `CICBIO`
   - Name: `CIC biomaGUNE`
   - Location: `San Sebastián, Spain`
   - Director: (assign after creating users)

2. **BioImaC**
   - Code: `BIOIMAC`
   - Name: `Biomedical Imaging Center (BioImaC)`
   - Location: `Murcia, Spain`

3. **La Fe**
   - Code: `LAFE`
   - Name: `Hospital La Fe`
   - Location: `Valencia, Spain`

4. **CNIC**
   - Code: `CNIC`
   - Name: `Centro Nacional de Investigaciones Cardiovasculares`
   - Location: `Madrid, Spain`

### Add Equipment to Nodes

For each node, navigate to **Core > Equipment** and add imaging equipment:

**Example for CIC biomaGUNE**:
- MRI 7T (category: MRI, is_essential: Yes)
- PET-CT (category: PET-CT, is_essential: Yes)
- etc.

### Create Organizations

Navigate to **Core > Organizations** and add:
- Universities
- Research centers
- Hospitals
- Companies

### Create Email Templates

Navigate to **Communications > Email Templates** and create templates for all 13 types:

**Required templates**:
1. call_published
2. application_received
3. feasibility_request
4. feasibility_reminder
5. feasibility_rejected
6. evaluation_assigned
7. evaluation_reminder
8. resolution_accepted
9. resolution_pending
10. resolution_rejected
11. acceptance_reminder
12. access_scheduled
13. publication_followup

**Template example** (application_received):

**Subject**: `Your Application {{ application.code }} Has Been Received`

**HTML Content**:
```html
<p>Dear {{ applicant.first_name }},</p>

<p>Thank you for submitting your COA application to ReDIB.</p>

<p><strong>Application Details:</strong></p>
<ul>
  <li>Application Code: {{ application.code }}</li>
  <li>Call: {{ call.title }}</li>
  <li>Submitted: {{ application.submitted_at }}</li>
</ul>

<p>Your application is now under review. You will be notified of any updates.</p>

<p>Best regards,<br>ReDIB Team</p>
```

**Text Content**: (similar, plain text version)

---

## Create Test Data (Optional)

### Create a Test Call

Navigate to **Calls > Calls** and create:

- **Code**: `COA-2025-01`
- **Title**: `First Quarter 2025 COA Call`
- **Status**: `draft` (change to `open` when ready)
- **Submission start**: Future date
- **Submission end**: Future date + 30 days
- **Evaluation deadline**: Future date + 45 days
- **Execution start**: Future date + 60 days
- **Execution end**: Future date + 365 days

Then add **Equipment Allocations** inline:
- For each equipment, specify hours offered (e.g., 100 hours)

### Create Test Users

Navigate to **Core > Users** and create:

1. **Test Applicant**
   - Email: `applicant@example.com`
   - First/Last name
   - Organization: (select one)

2. **Test Evaluator**
   - Email: `evaluator@example.com`
   - First/Last name

3. **Test Node Coordinator**
   - Email: `coordinator@example.com`
   - First/Last name

### Assign User Roles

Navigate to **Core > User Roles** and assign:

- Test Applicant → Role: `Applicant`
- Test Evaluator → Role: `Evaluator`, Area: `Preclinical`
- Test Node Coordinator → Role: `Node Coordinator`, Node: `CICBIO`

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

## Quick Test Data Setup (Recommended)

Instead of manually creating test data, use the **seed_dev_data** command to automatically create a complete test environment:

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

See **TEST_SETUP.md** for detailed information about the test data.

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

- **Design Document**: See `redib-coa-system-design.md`
- **Changelog**: See `CHANGELOG.md`
- **Validation**: See `VALIDATION_SUMMARY.md`
- **Quick Start**: See `QUICKSTART.md`

---

**Ready to use!** 🚀
