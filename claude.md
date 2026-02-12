# ReDIB COA Portal - Claude Code Configuration

## Project Overview

Django-based Competitive Open Access (COA) management system for the ReDIB distributed biomedical imaging network. Automates the complete COA lifecycle from call publication through application, evaluation, resolution, and access tracking.

**Current Status:** Production deployment infrastructure ready, preparing for live testing on IONOS VPS. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for full deployment guide.

## Technology Stack

- **Backend:** Django 5.0, Python 3.11
- **Database:** SQLite (local dev) / PostgreSQL (Docker/production)
- **Task Queue:** Celery + Redis (scheduled emails, reminders, deadline processing)
- **Frontend:** Django Templates + Bootstrap 5 + HTMX + Alpine.js
- **PDF Generation:** WeasyPrint (requires system libs: pango, cairo, gdk-pixbuf)
- **Authentication:** django-allauth (email-based login, `ACCOUNT_EMAIL_VERIFICATION = 'mandatory'`)
- **Audit Trail:** django-simple-history on all models
- **Static Files:** WhiteNoise with compression

## Documentation

```
docs/
├── README.md                    # Documentation index
├── QUICKSTART.md                # Fast setup guide
├── SETUP_GUIDE.md               # Detailed environment setup
├── DEVELOPMENT.md               # Development workflow
├── TESTING.md                   # Test running guide
├── USER_GUIDE.md                # End-user documentation
├── TEST_APPLICANTS_GUIDE.md     # Test data and user accounts
├── UPDATE_PDF_APP.md            # How to update the signed PDF application form
│
├── developer/
│   ├── branding-and-styles.md   # Logo, colors, CSS customization
│   ├── issue-action-plan-20260204.md  # Issue tracking and fixes
│   └── tier1-manual-test-checklist.md # Manual QA checklist
│
├── reference/
│   ├── redib-coa-system-design.md     # System architecture
│   ├── coa-application-form-spec.md   # Application form specification
│   └── evaluationForm_en.md           # Evaluation criteria reference
│
├── test-reports/                # Automated test reports by phase
└── archive/                     # Historical development notes
```

## Development Environment (venv + SQLite)

### Initial Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # Edit as needed
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_email_templates
python manage.py collectstatic --noinput
```

### Superuser Email Verification Fix
django-allauth requires an EmailAddress record. After createsuperuser:
```bash
python manage.py shell -c "
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.get(email='YOUR_EMAIL')
EmailAddress.objects.create(user=u, email=u.email, verified=True, primary=True)
"
```

### Running the Dev Server
```bash
source venv/bin/activate
python manage.py runserver
```
Access: http://localhost:8000 | Admin: http://localhost:8000/admin

### Test Data
```bash
python manage.py setup_localtest1_database       # Minimal test setup
python manage.py setup_test_database --reset --yes  # Full: all data + applications at various stages
```
All test user passwords: `testpass123`

### Running Tests
```bash
python manage.py test                                   # All tests
python manage.py test tests.test_phase1_phase2_workflow # Specific phase
python manage.py test tests.test_design                 # Design/static files tests
python manage.py test reports.tests                     # Reports tests
```

### Notes for Local Dev
- Celery/Redis not required. Email tasks will fail silently (try/except fallback).
- SQLite is used by default (`db.sqlite3`).
- Static files served by Django's dev server (no collectstatic needed for dev).

## Docker Deployment (Full Stack)

### Services
- **db:** PostgreSQL 15
- **redis:** Redis 7 (Alpine)
- **web:** Django app (Gunicorn)
- **celery:** Celery worker (async task processing)
- **celery-beat:** Celery Beat (scheduled tasks)

### Quick Start
```bash
cp .env.docker .env
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py seed_email_templates
docker compose exec web python manage.py setup_localtest1_database
```
Access: http://localhost:8000

### Useful Commands
```bash
docker compose logs -f web              # View web logs
docker compose logs -f celery           # View Celery worker logs
docker compose exec web python manage.py shell  # Django shell
docker compose down                     # Stop all services
docker compose down -v                  # Stop and remove volumes (full reset)
```

### Environment Variables (.env.docker)
```
DEBUG=False
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgres://redib_user:redib_password@db:5432/redib_db
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.ionos.es
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@redib.net
EMAIL_HOST_PASSWORD=your-email-password
```

## Production Deployment

Production uses `docker-compose.prod.yml` with Caddy (auto-TLS), PostgreSQL, Redis, Celery, and Gunicorn. See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for the complete guide covering VPS setup, DNS, email, backups, and monitoring.

Key production files:
- `docker-compose.prod.yml` - Production Docker Compose stack
- `docker/Caddyfile` - Reverse proxy and media file serving
- `.env.production.template` - Documented environment template
- `scripts/backup-db.sh` - PostgreSQL backup with 30-day retention

## Project Structure

```
redib/              # Django project settings, celery config
core/               # Users, organizations, nodes, equipment, UserRole model
calls/              # Call management and equipment allocation
applications/       # Application workflow (5-step wizard), feasibility review, PDF generation
evaluations/        # Evaluator assignment (auto + manual), scoring (6 criteria, 0-2 scale)
access/             # Access grants and publication tracking
communications/     # Email templates (DB-stored) and Celery send tasks
reports/            # Statistics dashboard and Excel exports
templates/          # All HTML templates
static/             # CSS, images, JS source files
staticfiles/        # Collected static files (git-ignored)
data/               # CSV fixtures (nodes.csv, equipment.csv, users.csv)
tests/              # Integration tests by workflow phase
```

## Application Workflow States

`draft` → `submitted` → `under_feasibility_review` → `pending_evaluation` → `under_evaluation` → `evaluated` → `accepted` / `pending` / `rejected`

Terminal states: `rejected_feasibility`, `rejected`, `declined_by_applicant`, `expired`

## Key Models

- **User** (`core/models.py`): Extended with ORCID, organization, phone
- **UserRole** (`core/models.py`): Role assignments with `role` (applicant/evaluator/coordinator/node_coordinator) and `area` field
- **Node** / **Equipment** (`core/models.py`): ReDIB network nodes and imaging equipment
- **Call** (`calls/models.py`): COA call periods with dates, status, equipment allocations
- **Application** (`applications/models.py`): Full application with scientific content, PDF signature fields
- **RequestedAccess** (`applications/models.py`): Equipment hours requests per application
- **FeasibilityReview** (`applications/models.py`): Per-node technical assessments
- **Evaluation** (`evaluations/models.py`): 6 scoring criteria (0-2 each), `completed_at` timestamp, recommendation
- **AccessGrant** / **Publication** (`access/models.py`): Approved access and publication outcomes
- **EmailTemplate** / **EmailLog** (`communications/models.py`): Email templates and send history

## Important Conventions

### Role Checks
```python
user.has_role('coordinator')
user.has_role('node_coordinator', node=node_obj)
user.has_role('evaluator', area='preclinical')
```

### Email Notifications
```python
from communications.tasks import send_email_from_template
send_email_from_template.delay(
    template_type='template_name',
    recipient_email=user.email,
    context_data={'variable': 'value', 'url': absolute_url},
    recipient_user_id=user.id,
    related_application_id=application.id
)
```
Email templates are stored in the database. Seed with `python manage.py seed_email_templates`.

### Scheduled Celery Tasks
| Task | Schedule | Purpose |
|------|----------|---------|
| `check_call_deadlines` | 00:15 daily | Auto-close expired calls |
| `send_feasibility_reminders` | 09:00 daily | Remind node coordinators (5+ days pending) |
| `send_evaluation_reminders` | 09:00 daily | Remind evaluators (7 days before deadline) |
| `notify_overdue_evaluators` | 09:30 daily | Alert evaluators when deadline passes |
| `notify_coordinator_overdue_evaluations` | 09:45 daily | Alert coordinators about overdue/locked evals |
| `process_acceptance_deadlines` | 10:00 daily | Reminders + auto-expire (days 7/10) |
| `send_publication_followups` | 10:00 Mondays | 6-month post-access follow-up |

## Management Commands

| Command | Purpose |
|---------|---------|
| `seed_email_templates` | Load/update email templates (run after DB reset) |
| `populate_redib_nodes` | Load nodes from CSV (must run before users/equipment) |
| `populate_redib_users` | Load users from CSV (requires nodes) |
| `populate_redib_equipment` | Load equipment from CSV (requires nodes) |
| `setup_localtest1_database` | Minimal test setup |
| `setup_test_database` | Full test setup (all data + test applications) |
| `seed_dev_data` | Seed calls and organizations |
| `seed_test_applicants` | Create test applicants with applications at various stages |

All population commands support `--sync` flag to update without deleting existing records.

## Code Style

- Make only changes directly requested; don't add unnecessary features or abstractions
- Use `get_object_or_404`, `select_related`/`prefetch_related`, Django messages framework
- Use `login_required` and role checks for access control
- Never commit secrets (`.env`, credentials)
- Read files before editing; verify code works after changes
- Follow existing commit message style (see `git log`)
