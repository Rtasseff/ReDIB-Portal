# ReDIB COA Portal - Claude Code Configuration

## Project Overview

Django 5.0 / Python 3.11 COA management system for the ReDIB distributed biomedical imaging network. Automates the complete COA lifecycle from call publication through application, evaluation, resolution, and access tracking.

**Current Phase:** Rapid iterative improvement — fixing bugs, adding features, and updating content based on recent testing. Changes are developed and tested locally (often on feature branches), merged to main, pushed to origin, then pulled on the production VPS.

**Active Branch:** None — `fixes-batch-2` was merged to `main` on 2026-04-16. Next batch will start as `fixes-batch-3` when there's enough scoped work; check [docs/developer/backlog.md](docs/developer/backlog.md) for candidate items.

## Environment Context

**Always ask which environment we are working in** before making changes or giving instructions:

- **Development (local):** Python venv + SQLite + `runserver`. No Docker, Redis, or Celery required.
- **Production (VPS):** Docker Compose with PostgreSQL, Redis, Celery, Caddy (auto-TLS) on IONOS VPS (`portal.redib.net`). Currently deployed and running.

The app reads a single `.env` file (gitignored). Two tracked templates are provided (`.env.example` for dev, `.env.production.template` for prod) — see [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md) for the full environment variable reference.

**Deployment workflow:** merge to main → push → SSH to VPS → `git pull` → rebuild containers. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Documentation

All docs live in `docs/`. Start with [docs/README.md](docs/README.md) for the full index.

Key references:
- **Setup & workflows:** [QUICKSTART.md](docs/QUICKSTART.md), [DEVELOPMENT.md](docs/DEVELOPMENT.md), [SETUP_GUIDE.md](docs/SETUP_GUIDE.md)
- **Production:** [DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **Testing:** [TESTING.md](docs/TESTING.md), [TEST_APPLICANTS_GUIDE.md](docs/TEST_APPLICANTS_GUIDE.md)
- **System design:** [reference/redib-coa-system-design.md](docs/reference/redib-coa-system-design.md)
- **Branding/styles:** [developer/branding-and-styles.md](docs/developer/branding-and-styles.md)
- **Backlog:** [developer/backlog.md](docs/developer/backlog.md) — drop new feature requests, UX polish, and known test issues here when they aren't going into the current batch

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
data/               # TSV fixtures (nodes.tsv, organizations.tsv, users.tsv, equipment.tsv, funding_agencies.tsv)
tests/              # Integration tests by workflow phase
```

## Application Workflow States

`draft` → `submitted` → `under_feasibility_review` → `pending_evaluation` → `under_evaluation` → `evaluated` → `accepted` / `pending` / `rejected`

`pending` is the waitlist state. The applicant gets the same 10-day accept/decline window as `accepted`, but the hand-off fires only when a node coordinator promotes the application to `accepted` via "Mark as Accepted" on the Access Tracking page (`applications:promote_waitlisted`).

Terminal states: `rejected_feasibility`, `rejected`, `declined_by_applicant`, `expired`, `completed`.

### Competitive funding & reject protection

Applications with `has_competitive_funding=True` are protected from rejection at the **resolution** phase (`NodeResolutionService.apply_node_resolution`, `ApplicationResolutionService.apply_resolution`) — coordinators must accept or waitlist — **unless** at least one completed evaluation has `recommendation='denied'`. In that case the evaluator's independent denial provides grounds for rejection and the reject option is re-enabled. Use `Application.has_any_denied_evaluation` to check. Feasibility rejection (phase 3) and evaluator denial (phase 5) remain available regardless of funding status.

## Key Models

- **User** (`core/models.py`): Extended with ORCID (regex-validated), phone (regex-validated), `organization`, `position`, `auto_data_consent`
- **UserRole** (`core/models.py`): Role assignments with `role` (`applicant` / `evaluator` / `coordinator` / `node_coordinator`) and `areas` (semicolon-separated multi-area CharField for evaluators)
- **Node** / **Equipment** (`core/models.py`): ReDIB network nodes and imaging equipment
- **Call** (`calls/models.py`): COA call periods with dates, status, equipment allocations
- **Application** (`applications/models.py`): Full application with scientific content; human-subject declarations include `uses_humans`, `has_human_ethics`, `has_insurance`, `has_informed_consent`
- **RequestedAccess** (`applications/models.py`): Equipment hours requests per application (`hours_requested`, `hours_approved`)
- **FeasibilityReview** (`applications/models.py`): Per-node technical assessment with `status` (`pending` / `approved` / `rejected` / `edits_requested`) — the authoritative field (legacy `is_feasible` boolean still present for history)
- **FundingAgency** (`applications/models.py`): Funding agency directory, `origin_of_funds` matches the 7-key `PROJECT_TYPES` set
- **Evaluation** (`evaluations/models.py`): 6 scoring criteria (0-2 each), `completed_at` timestamp, recommendation
- **AccessGrant** / **Publication** (`access/models.py`): Approved access and publication outcomes
- **EmailTemplate** / **EmailLog** (`communications/models.py`): Email templates and send history

### Email recipients
Applicant-facing emails prefer `Application.applicant_email` (the form-declared PI contact) and fall back to `Application.applicant.email`. The hand-off email is sent as one message with `to=[applicant]` and `cc=[node_coordinators]` so everyone can reply-all. ReDIB coordinators no longer receive a per-app `evaluations_complete` email — they are covered by the daily `notify_coordinator_overdue_evaluations` and by `coordinator_evaluations_locked` at window close.

## Important Conventions

### Role Checks
Roles live on `UserRole` — query them off the user:
```python
# Any active role of a given type
user.roles.filter(role='coordinator', is_active=True).exists()

# Scoped to a specific node
user.roles.filter(role='node_coordinator', node=node_obj, is_active=True).exists()

# Evaluators have multi-area assignments; use UserRole.has_area() to match one
any(r.has_area('preclinical')
    for r in user.roles.filter(role='evaluator', is_active=True))
```
Shortcut decorators live in `core/decorators.py`: `@coordinator_required`,
`@node_coordinator_required`, `@evaluator_required`, `@applicant_required`,
and the generic `@role_required('role_a', 'role_b')`.

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
| `setup_localtest3_database` | **Recommended for full manual-test pass.** Self-contained sandbox: 10 users, 2 calls, 16 apps spanning every live + terminal status, with tester cheat-sheet. See `docs/developer/localtest3-database-plan.md`. |
| `setup_base_database` | Populate real reference data from `data/*.tsv` (nodes, organizations, users, equipment, funding agencies, email templates) |
| `setup_test_database` | Full test setup (base data + fake calls, applications, test applicants) |
| `setup_localtest1_database` | Minimal test setup (legacy — use `setup_localtest3_database` instead) |
| `seed_email_templates` | Load/update email templates (run after DB reset) |
| `populate_redib_nodes` | Load nodes from `data/nodes.tsv` (must run before users/equipment) |
| `populate_redib_organizations` | Load organizations from `data/organizations.tsv` |
| `populate_redib_users` | Load users from `data/users.tsv` (requires nodes + organizations); sets password + email verification |
| `populate_redib_equipment` | Load equipment from `data/equipment.tsv` (requires nodes) |
| `populate_redib_funding_agencies` | Load funding agencies from `data/funding_agencies.tsv` |
| `seed_dev_data` | Seed calls and organizations (used inside `setup_test_database`) |
| `seed_test_applicants` | Create test applicants with applications at various stages |

All `populate_redib_*` commands support `--sync` flag to update without deleting existing records.

## Code Style

- Make only changes directly requested; don't add unnecessary features or abstractions
- Use `get_object_or_404`, `select_related`/`prefetch_related`, Django messages framework
- Use `login_required` and role checks for access control
- Never commit secrets (`.env`, credentials)
- Read files before editing; verify code works after changes
- Follow existing commit message style (see `git log`)
