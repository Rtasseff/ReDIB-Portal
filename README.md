# ReDIB COA Portal

Competitive Open Access (COA) Management System for the ReDIB (Red Distribuida de Imagen Biomédica) distributed biomedical imaging network.

## Overview

This Django-based web application automates the complete COA lifecycle, from call publication to access completion, replacing the previous manual email-based workflow.

## Documentation

All documentation is organized in the `docs/` folder:

- **[docs/QUICKSTART.md](docs/QUICKSTART.md)** - Get started quickly (new users start here)
- **[docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md)** - Detailed setup and configuration
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Production deployment guide (VPS, Docker, Caddy, backups)
- **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** - Development workflows and common commands
- **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)** - End-user guide for portal users
- **[docs/TESTING.md](docs/TESTING.md)** - Testing procedures and guidelines
- **[docs/TEST_APPLICANTS_GUIDE.md](docs/TEST_APPLICANTS_GUIDE.md)** - Comprehensive test data for manual testing
- **[docs/TEST_EMAIL_TEMPLATES.md](docs/TEST_EMAIL_TEMPLATES.md)** - Email template testing and verification
- **[docs/developer/](docs/developer/)** - Developer guides (branding, styles, issue plans)
- **[docs/reference/](docs/reference/)** - Technical reference and system design documentation
- **[docs/test-reports/](docs/test-reports/)** - Automated test reports by phase

### Key Features

- **Role-based access control** for applicants, node coordinators, evaluators, and administrators
- **Automated workflow** for application submission, feasibility review, and evaluation
- **Email notifications** with configurable templates and automated reminders
- **Comprehensive reporting** for ministry requirements and internal statistics
- **Publication tracking** to monitor research outcomes

## Technology Stack

- **Backend**: Django 5.0, Python 3.11
- **Database**: PostgreSQL 15
- **Task Queue**: Celery + Redis
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

- **[docs/QUICKSTART.md](docs/QUICKSTART.md)** - Docker setup (recommended, includes PostgreSQL, Redis, Celery)
- **[docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md)** - Local venv + SQLite setup (no Docker required)
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Production deployment on VPS with Caddy, auto-TLS, backups

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
