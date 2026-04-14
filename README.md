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
└── data/               # CSV fixture files for initial data
    ├── nodes.csv       # ReDIB network nodes (4 nodes)
    ├── equipment.csv   # Equipment at each node (17 items)
    └── users.csv       # Core users (coordinators, evaluators, 8 users)
```

## Current Implementation Status

### ✅ All Phases Completed (Production-Ready)

- **Phase 0**: Foundation & Dashboard ✅
  - User authentication & role-based access control
  - Base templates and navigation

- **Phase 1**: Call Management ✅
  - Create and publish COA calls
  - Equipment allocation management
  - Public call listings

- **Phase 2**: Application Submission ✅
  - 5-step wizard workflow
  - **5 applicant information fields** (name, ORCID, entity, email, phone)
  - **7 project types** (expanded from 5)
  - **20 AEI subject area classifications** (expanded from 13)
  - Auto-population from user profile
  - Equipment access requests

- **Phase 3**: Feasibility Review ✅
  - Multi-node technical feasibility reviews
  - Approval/rejection workflow
  - Automated state transitions
  - Email notifications

- **Phase 4**: Evaluator Assignment ✅
  - Conflict of interest (COI) detection and prevention
  - Automated evaluator assignment
  - Manual override capabilities
  - Email notifications to evaluators

- **Phase 5**: Evaluation Process ✅
  - 6-criteria evaluation system (0-2 scale)
  - Evaluator dashboard and forms
  - Progress tracking
  - Completion notifications

- **Phase 6**: Resolution & Prioritization ✅
  - Node coordinator resolution workflow (distributed ownership)
  - Multi-node aggregation (ALL accept → accepted, ANY reject → rejected)
  - Per-equipment hours approval by node coordinators
  - Competitive funding protection (cannot reject funded applications)
  - Score-based ranking and prioritization

- **Phase 7 & 8**: Acceptance & Handoff (Simplified) ✅
  - Applicant acceptance/decline workflow
  - 10-day acceptance deadline enforcement
  - Handoff email automation
  - Direct access coordination (no internal scheduling)

- **Phase 9**: Publication Tracking ✅
  - Publication submission by applicants
  - 6-month follow-up reminders
  - ReDIB acknowledgment tracking
  - Coordinator verification

- **Phase 10**: Reporting & Statistics ✅
  - Statistics dashboard for coordinators
  - Excel export for call reports (3-sheet workbooks)
  - Publication statistics integration
  - Report generation tracking

**Complete system with comprehensive automated test suites (47+ tests across all phases).**

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

Run the full production-like stack locally for integration testing.

1. Copy `.env.docker` to `.env`
2. Follow the "Local Docker Testing" section in **[docs/QUICKSTART.md](docs/QUICKSTART.md)**

### Environment Files

The app reads a single `.env` file. Three templates are provided:

| Template File | Copy to `.env` when... | Key Defaults |
|---------------|----------------------|--------------|
| `.env.example` | Developing locally (venv + SQLite) | `DEBUG=True`, `USE_REDIS=False`, SQLite DB |
| `.env.docker` | Testing with local Docker Compose | `DEBUG=True`, `USE_REDIS=True`, PostgreSQL |
| `.env.production.template` | Deploying to production VPS | `DEBUG=False`, `USE_REDIS=True`, PostgreSQL, SMTP |

See **[docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md)** for a full reference of all environment variables and how to switch between modes.

## Data Models

### Core Models
- **Organization**: Parent organizations (universities, research centers, etc.)
- **Node**: ReDIB network nodes (4 nodes: CICbiomaGUNE, BioImaC, La Fe, CNIC)
- **Equipment**: Imaging equipment at each node
- **User**: Extended user model with ORCID and affiliations
- **UserRole**: Role assignments (applicant, evaluator, coordinator, etc.)

### Call Management
- **Call**: COA call periods with dates and status
- **CallEquipmentAllocation**: Hours offered per equipment per call

### Applications
- **Application**: COA applications with full scientific content
- **RequestedAccess**: Equipment access requests within applications
- **FeasibilityReview**: Node technical feasibility assessments

### Evaluations
- **Evaluation**: Evaluator scores and comments (0-2 scale on 6 criteria)

### Access Tracking
- **AccessGrant**: Approved access with scheduling and usage tracking
- **Publication**: Publications resulting from COA access

## Development

See **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** for workflows, common commands, database management, and data loading procedures.

## License

[To be determined]

## Contact

ReDIB Network - [info@redib.net](mailto:info@redib.net)

## Acknowledgments

Developed for CIC biomaGUNE and the ReDIB ICTS Network.
