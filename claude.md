# ReDIB COA Portal - Claude Code Configuration

## Project Overview

This is the ReDIB Competitive Open Access (COA) Management System - a Django-based web application that automates the complete COA lifecycle for the ReDIB (Red Distribuida de Imagen Biomédica) distributed biomedical imaging network.

**Status:** Initial development complete, moving to comprehensive testing phase.

## Technology Stack

- **Backend:** Django 5.0, Python 3.11
- **Database:** PostgreSQL 15
- **Task Queue:** Celery + Redis
- **Frontend:** Django Templates + HTMX + Alpine.js + Bootstrap 5
- **Testing:** Django TestCase framework
- **Authentication:** django-allauth

## Project Structure

- `core/` - Users, organizations, nodes, equipment (foundation)
- `calls/` - Call management
- `applications/` - Application submission and workflow (5-step wizard)
- `evaluations/` - Evaluator assignment and scoring
- `access/` - Access grants and publication tracking
- `communications/` - Email templates and sending (Celery tasks)
- `reports/` - Reporting and exports (Excel workbooks)
- `tests/` - Comprehensive test suites (29 tests total)
- `data/` - CSV fixture files (nodes, equipment, users)

## Development Guidelines

### Python Virtual Environment
Always activate the virtual environment before running commands:
```bash
source venv/bin/activate
```
Use full path for Python commands when venv not activated:
```bash
/Users/rtasseff/projects/ReDIB-Portal/venv/bin/python
```

### Database Management
- **Development (NOW):** virtual enviornment and mySQL
- **Production (LATER):** Uses Docker Compose for PostgreSQL and Redis
- **Migrations:** Always run `makemigrations` before `migrate`
- **Fixtures:** Use CSV-based data loading commands (see below)

### CSV Data Loading
The project uses CSV files in `/data/` for initial data:
- `data/nodes.csv` - 4 ReDIB network nodes
- `data/equipment.csv` - 17 equipment items
- `data/users.csv` - 8 core users (coordinators, evaluators)

**Population commands:**
```bash
python manage.py populate_redib_nodes [--sync] [--csv path/to/file.csv]
python manage.py populate_redib_equipment [--sync] [--csv path/to/file.csv]
python manage.py populate_redib_users [--sync] [--csv path/to/file.csv]
```

**Sync mode:** Use `--sync` flag to mark orphaned records as `is_active=False` (never deletes, maintains referential integrity).

### Email System
- Uses Celery for asynchronous email sending
- Templates managed via `seed_email_templates` command
- Always seed templates after database purge:
  ```bash
  python manage.py seed_email_templates
  ```
- In development, do not use celery but do manage email templates as if active.

## Testing Guidelines

### Test Structure
- **Location:** `/tests/` primary directory
- **Total:** 29 automated integration tests
- **Coverage:** First 9 phases of the COA workflow
- **Phase 10: Reporting & Statistics** Test Suite: reports.tests

### Running Tests
```bash
# Run all tests
python manage.py test tests

# Run specific phase tests
python manage.py test tests.test_phase1_phase2_workflow
python manage.py test tests.test_phase3_feasibility_review
python manage.py test tests.test_phase4_evaluator_assignment
python manage.py test tests.test_phase5_evaluation_submission
python manage.py test tests.test_phase6_resolution
python manage.py test tests.test_phase7_acceptance
python manage.py test tests.test_phase9_publications
python manage.py test reports.tests
```

### Test Data Setup
For integration testing, use the dev data seeding command:
```bash
# Create test data (calls, applications, evaluations)
python manage.py seed_dev_data

# Clear and rebuild test data
python manage.py seed_dev_data --clear
```

### Database Purge for Testing
When you need a clean slate for end-to-end testing, see [DEVELOPMENT.md](DEVELOPMENT.md) for complete database reset procedures.

**Quick reference:**
```bash
# 1. Drop and recreate database (Docker)
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d

# 2. Run migrations
python manage.py migrate

# 3. Create superuser
python manage.py createsuperuser

# 4. Seed email templates (REQUIRED)
python manage.py seed_email_templates

# 5. Populate nodes (MUST be first), then users and equipment
python manage.py populate_redib_nodes
python manage.py populate_redib_users
python manage.py populate_redib_equipment
```

**IMPORTANT:** Never use `find` commands that delete migrations without excluding `venv/`:
```bash
# CORRECT - excludes venv
find . -path "./venv" -prune -o -path "*/migrations/*.py" -not -name "__init__.py" -type f -delete

# WRONG - will delete Django's core files
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
```

## Workflow Phases

The system implements a 10-phase workflow:

1. **Phase 0:** Foundation & Dashboard
2. **Phase 1:** Call Management
3. **Phase 2:** Application Submission (5-step wizard)
4. **Phase 3:** Feasibility Review (multi-node)
5. **Phase 4:** Evaluator Assignment (COI detection)
6. **Phase 5:** Evaluation Process (5 criteria, 1-5 scale)
7. **Phase 6:** Resolution & Prioritization (auto-approval at >3.5)
8. **Phase 7:** Acceptance & Handoff (10-day deadline)
9. **Phase 9:** Publication Tracking (6-month follow-ups)
10. **Phase 10:** Reporting & Statistics (Excel exports)

## Key Models

### Core Models
- `User` - Extended with ORCID, organization, phone
- `Organization` - Parent organizations
- `Node` - ReDIB network nodes (4 nodes)
- `Equipment` - Imaging equipment (17 items)
- `UserRole` - Role assignments with node/area qualifiers

### Application Workflow Models
- `Call` - COA call periods
- `Application` - COA applications with full scientific content
- `RequestedAccess` - Equipment requests within applications
- `FeasibilityReview` - Node technical assessments
- `Evaluation` - Evaluator scores (5 criteria)
- `AccessGrant` - Approved access tracking
- `Publication` - Publication outcomes

## Important Conventions

### Email Notifications
Email sending follows this pattern:
```python
from communications.tasks import send_email_from_template
from django.urls import reverse

# Build absolute URL
review_url = request.build_absolute_uri(
    reverse('app:view_name', kwargs={'pk': obj.pk})
)

# Send email asynchronously
send_email_from_template.delay(
    template_type='template_name',
    recipient_email=user.email,
    context_data={
        'variable': 'value',
        'url': review_url,
    },
    recipient_user_id=user.id,
    related_application_id=application.id  # Optional
)
```

### Role Management
Users can have multiple roles with qualifiers:
- Simple: `coordinator`, `evaluator`
- Node-specific: `node_coordinator:CIC-biomaGUNE`
- Area-specific: `evaluator:preclinical`, `evaluator:clinical`, `evaluator:radiotracers`
- Multiple: `coordinator;evaluator:clinical`

Check roles programmatically:
```python
user.has_role('coordinator')
user.has_role('node_coordinator', node=node_obj)
user.has_role('evaluator', area='preclinical')
```

### Security Considerations
- Never commit files with secrets (`.env`, credentials, etc.)
- Validate user input at system boundaries
- Use Django's built-in protections (CSRF, XSS, SQL injection)
- Check permissions before allowing actions
- Use `login_required` and `permission_required` decorators

## Code Style

### Avoid Over-Engineering
- Make only the changes directly requested
- Don't add unnecessary features, error handling, or abstractions
- Don't add comments/docstrings to unchanged code
- Keep solutions simple and focused

### Django Best Practices
- Use `get_object_or_404` for object retrieval in views
- Use `select_related` and `prefetch_related` for query optimization
- Use transactions for multi-step database operations
- Use Django messages framework for user feedback

## Documentation

### Core Docs
- [README.md](README.md) - Main project documentation and overview
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide for new users
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Detailed setup and configuration
- [TESTING.md](TESTING.md) - Testing procedures and guidelines
- [DEVELOPMENT.md](DEVELOPMENT.md) - Development workflows and common commands

### Reference Materials
- [docs/reference/redib-coa-system-design.md](docs/reference/redib-coa-system-design.md) - Complete system architecture
- [docs/reference/coa-application-form-spec.md](docs/reference/coa-application-form-spec.md) - Application form specification
- [docs/test-reports/](docs/test-reports/) - Test validation reports

### Archived Documentation
- [archive/dev-docs/](archive/dev-docs/) - Development-phase documentation (PROJECT_STRUCTURE.md, design decisions)
- [archive/](archive/) - Historical documentation (CHANGELOG.md, etc.)

## Current Focus: Testing Phase

We are transitioning from initial development to comprehensive testing. Focus areas:

1. **End-to-End Testing:** Complete workflow from call creation to publication tracking
2. **Email Verification:** Ensure all email notifications send correctly
3. **Permission Testing:** Verify role-based access controls work properly
4. **Data Integrity:** Test CSV sync mode and data consistency
5. **Edge Cases:** Test boundary conditions, error handling, and unusual workflows

## Common Commands Reference

```bash
# Development server
python manage.py runserver

# Celery (background tasks)
celery -A redib worker -l info
celery -A redib beat -l info

# Database
python manage.py makemigrations
python manage.py migrate
python manage.py dbshell

# Testing
python manage.py test tests
python manage.py test tests.test_phase1_phase2_workflow --keepdb

# Data management
python manage.py seed_email_templates
python manage.py populate_redib_nodes --sync
python manage.py populate_redib_equipment --sync
python manage.py populate_redib_users --sync
python manage.py seed_dev_data --clear

# Shell
python manage.py shell
```

## Notes for Claude Code

- Always use the virtual environment or full Python paths
- Check git status before making changes to understand current state
- Read files before editing them
- Use specialized tools (Read, Edit, Write) instead of bash commands for file operations
- When exploring the codebase, use the Task tool with Explore agent for non-specific queries
- Verify code compiles after making changes
- Follow existing commit message style (see git log)
