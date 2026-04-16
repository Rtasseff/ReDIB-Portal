# ReDIB COA Portal

Competitive Open Access (COA) Management System for the ReDIB (Red Distribuida de Imagen Biomédica) distributed biomedical imaging network.

## Overview

This Django-based web application automates the complete COA lifecycle, from call publication to access completion, replacing the previous manual email-based workflow.

## Documentation

All documentation is organized in the `docs/` folder:

- **[docs/QUICKSTART.md](docs/QUICKSTART.md)** - Development setup (venv + SQLite) and optional local Docker testing
- **[docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md)** - Detailed configuration, environment variables, and data loading reference
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Production deployment guide (VPS, Docker, Caddy, backups)
- **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** - Development prerequisites, workflows, and common commands
- **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)** - End-user guide for portal users
- **[docs/TESTING.md](docs/TESTING.md)** - Testing procedures and guidelines
- **[docs/TEST_APPLICANTS_GUIDE.md](docs/TEST_APPLICANTS_GUIDE.md)** - Comprehensive test data for manual testing
- **[docs/TEST_EMAIL_TEMPLATES.md](docs/TEST_EMAIL_TEMPLATES.md)** - Email template testing and verification
- **[docs/developer/](docs/developer/)** - Developer guides (branding, styles, issue plans). See **[developer-notes.md](docs/developer/developer-notes.md)** for design decisions, deferred improvements, and future-work notes.
- **[docs/reference/](docs/reference/)** - Technical reference and system design documentation
- **[docs/test-reports/](docs/test-reports/)** - Automated test reports by phase

### Key Features

- **Role-based access control** for applicants, node coordinators, evaluators, and administrators
- **Automated workflow** for application submission, feasibility review, and evaluation
- **Email notifications** with configurable templates and automated reminders
- **Comprehensive reporting** for ministry requirements and internal statistics
- **Publication tracking** to monitor research outcomes

## Technology Stack

The portal runs in two modes. **Development** needs only Python; **Production** uses Docker with the full service stack.

| Component | Development | Production |
|-----------|------------|------------|
| Runtime | Python 3.11, venv | Docker containers |
| Web Server | `manage.py runserver` | Gunicorn + Caddy (auto-TLS) |
| Database | SQLite (automatic, no setup) | PostgreSQL 15 |
| Cache | In-memory (LocMemCache) | Redis 7 |
| Task Queue | None required (Celery runs in-process via `CELERY_TASK_ALWAYS_EAGER=DEBUG`) | Celery 5 + Redis |
| Email | Console (prints to terminal) — workflow + allauth emails both visible | SMTP |

Shared across both modes:
- **Frontend**: Django Templates + HTMX + Alpine.js + Bootstrap 5
- **Authentication**: django-allauth
- **APIs**: Django REST Framework (for future use)

## Project Structure

```
redib/
├── core/               # Users, organizations, nodes, equipment
├── calls/              # Call management
├── applications/       # Application submission and workflow
├── evaluations/        # Evaluator assignment and scoring
├── access/             # Access grants and publication tracking
├── communications/     # Email templates and sending
├── reports/            # Reporting and exports
├── templates/          # HTML templates
├── static/             # CSS, JS, images
└── data/               # TSV reference data (see data/README.md for column specs)
    ├── nodes.tsv          # ReDIB network nodes
    ├── organizations.tsv  # Parent organizations
    ├── users.tsv          # Staff users with roles and areas
    ├── equipment.tsv      # Imaging devices per node
    └── funding_agencies.tsv  # Funding agencies with origin_of_funds
```

## Current Implementation Status

All ten design-document phases (Phase 0 Foundation → Phase 10 Reporting)
are implemented and in rapid-iteration bug-fix / content-update mode.
The workflow below is what the system actually supports today:

1. **Call publication** — coordinators create calls with submission,
   evaluation, and execution windows and allocate per-equipment hours.
2. **Application submission** — 5-step wizard with applicant snapshot,
   funding source (FundingAgency + origin-of-funds), service modality,
   scientific content (six 0-2 criteria), and declarations
   (animal/human ethics, insurance, informed consent, data consent).
3. **Feasibility review** — per-node technical sign-off by node
   coordinators with approve / reject / request-edits actions.
4. **Evaluator assignment & scoring** — COI detection, auto + manual
   assignment, blind scoring across six criteria.
5. **Resolution** — per-node coordinator decisions aggregated to
   `accepted`, `pending` (waitlist), or `rejected`. Competitive-funding
   applications are reject-protected at this phase unless at least one
   evaluator independently recommended denial.
6. **Acceptance & hand-off** — applicant accept/decline within 10 days.
   Waitlisted applications use the same accept/decline flow and can
   be promoted to `accepted` by a node coordinator via the
   "Mark as Accepted" action on Access Tracking.
7. **Access tracking & completion** — node coordinators and
   applicants both see an access-tracking dashboard; either can mark
   an equipment block complete with actual hours used.
8. **Publication tracking** — applicants report publications with a
   6-month follow-up reminder, ReDIB acknowledgment verified.
9. **Reports** — coordinator statistics dashboard, Excel export per
   call, publication statistics.

For the current active work, see
**[docs/developer/](docs/developer/)** (batch plans and progress files).

---

## Getting Started

### Development (recommended for contributors)

Set up a local Python environment with SQLite -- no Docker, Redis, or Celery required.

1. Copy `.env.example` to `.env`
2. Follow **[docs/QUICKSTART.md](docs/QUICKSTART.md)**

### Production Deployment (VPS with Docker)

Deploy with Docker Compose, PostgreSQL, Redis, Celery, and Caddy (auto-TLS).

1. Copy `.env.production.template` to `.env` and fill in all values
2. Follow **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**

### Local Docker Testing (optional)

Run the full production-like stack locally for integration testing. Start from `.env.production.template`, adjust to local values (DEBUG=True, simple passwords, `ALLOWED_HOSTS=localhost,127.0.0.1`), then follow the "Local Docker Testing" section in **[docs/QUICKSTART.md](docs/QUICKSTART.md)**.

### Environment Files

The app reads a single `.env` file. Two templates are provided:

| Template File | Copy to `.env` when... | Key Defaults |
|---------------|----------------------|--------------|
| `.env.example` | Developing locally (venv + SQLite + console email) | `DEBUG=True`, `USE_REDIS=False`, SQLite DB, `SITE_URL=http://127.0.0.1:8000` |
| `.env.production.template` | Deploying to production VPS (Docker + PostgreSQL + Redis + SMTP) | `DEBUG=False`, `USE_REDIS=True`, PostgreSQL, SMTP, `SITE_URL=https://portal.redib.net` |

See **[docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md)** for a full reference of all environment variables and how to switch between modes.

## Data Models

### Core Models
- **Organization**: Parent organizations (universities, research centers, etc.)
- **Node**: ReDIB network nodes (4 nodes: CICbiomaGUNE, BioImaC, La Fe, CNIC)
- **Equipment**: Imaging equipment at each node
- **User**: Extended user model with ORCID and phone (both regex-validated), affiliations
- **UserRole**: Role assignments (`applicant`, `evaluator`, `coordinator`, `node_coordinator`) with a semicolon-separated `areas` field for evaluator specialisations

### Call Management
- **Call**: COA call periods with submission, evaluation, and execution windows
- **CallEquipmentAllocation**: Hours offered per equipment per call

### Applications
- **Application**: COA applications with full scientific content, human/animal declarations (ethics, insurance, informed consent), and acceptance tracking (waitlist lifecycle included)
- **RequestedAccess**: Equipment access requests within applications (per-equipment requested + approved hours)
- **FeasibilityReview**: Node technical feasibility assessments with explicit `status` (pending / approved / rejected / edits_requested)
- **FundingAgency**: Funding-agency reference list with `origin_of_funds` (spanish_government, international_non_eu, spanish_regional, european_union, institutional, private, other)

### Evaluations
- **Evaluation**: Evaluator scores and comments (0-2 scale on 6 criteria)

### Access Tracking
- **AccessGrant**: Approved access with scheduling and usage tracking
- **Publication**: Publications resulting from COA access

### Communications
- **EmailTemplate**: DB-stored Django templates for every workflow email
- **EmailLog**: Every send is logged with recipient, subject, template, and status for debugging and audit

## Development

See **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** for workflows, common commands, database management, and data loading procedures.

## License

[To be determined]

## Contact

ReDIB Network - [info@redib.net](mailto:info@redib.net)

## Acknowledgments

Developed for CIC biomaGUNE and the ReDIB ICTS Network.
