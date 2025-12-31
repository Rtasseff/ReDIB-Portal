# ReDIB COA Portal

Competitive Open Access (COA) Management System for the ReDIB (Red Distribuida de Imagen Biomédica) distributed biomedical imaging network.

## Overview

This Django-based web application automates the complete COA lifecycle, from call publication to access completion, replacing the previous manual email-based workflow.

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
└── static/             # CSS, JS, images
```

## Current Implementation Status

### ✅ Completed Phases (Production-Ready)

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

**All completed phases have comprehensive automated test suites (115 tests total).**

### 🔄 Pending Phases

- Phase 4: Evaluator Assignment
- Phase 5: Evaluation Process
- Phase 6: Resolution & Prioritization
- Phase 7: Acceptance & Scheduling
- Phase 8: Execution & Completion
- Phase 9: Publication Follow-up
- Phase 10: Reporting & Statistics

---

## Quick Start

### Development Setup (Local)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ReDIB-Portal
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run with Docker (recommended)**
   ```bash
   # Start only database and Redis for local development
   docker-compose -f docker-compose.dev.yml up -d

   # Run migrations
   python manage.py migrate

   # Create superuser
   python manage.py createsuperuser

   # Run development server
   python manage.py runserver
   ```

6. **Access the application**
   - Application: http://localhost:8000
   - Admin: http://localhost:8000/admin

### Production Deployment (Docker)

1. **Build and start all services**
   ```bash
   docker-compose up -d
   ```

2. **Run migrations**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

3. **Create superuser**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

4. **Collect static files**
   ```bash
   docker-compose exec web python manage.py collectstatic --noinput
   ```

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
- **Evaluation**: Evaluator scores and comments (1-5 scale on 5 criteria)

### Access Tracking
- **AccessGrant**: Approved access with scheduling and usage tracking
- **Publication**: Publications resulting from COA access

## Development Workflow

### Running Celery (for background tasks)

```bash
# Worker
celery -A redib worker -l info

# Beat (scheduled tasks)
celery -A redib beat -l info
```

### Creating Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### Running Tests

**Automated Test Suites** (115 tests total):
```bash
# Specification validation (63 tests)
python tests/test_application_form_spec.py

# Phase 1 & 2 workflow (23 tests)
python tests/test_phase1_phase2_workflow.py

# Phase 3 workflow (29 tests)
python tests/test_phase3_feasibility_review.py
```

See [TEST.md](TEST.md) for detailed testing guide and [docs/test-reports/](docs/test-reports/) for test reports.

### Populating Test Data

```bash
# Populate equipment (17 items across 4 nodes)
python manage.py populate_redib_equipment

# Seed development data (calls, applications, evaluations)
python manage.py seed_dev_data

# Clear and rebuild test data
python manage.py seed_dev_data --clear
```

## Environment Variables

Key environment variables (see `.env.example` for full list):

- `SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode (True/False)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`: Email configuration

## Initial Setup Tasks

After deployment, perform these initial setup tasks:

1. **Create ReDIB nodes** (4 nodes)
2. **Add equipment** for each node
3. **Set up organizations** (universities, research centers)
4. **Create user accounts** for coordinators and node staff
5. **Assign roles** to users
6. **Configure email templates**

## Documentation

### Core Documentation
- **[TEST.md](TEST.md)** - Testing guide with automated and manual testing procedures
- **[QUICKSTART.md](QUICKSTART.md)** - Quick start guide for development
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Detailed setup instructions

### Reference Materials (`/docs/reference/`)
- **[System Design Document](docs/reference/redib-coa-system-design.md)** - Complete architecture and requirements
- **[Application Form Specification](docs/reference/coa-application-form-spec.md)** - Detailed form specification
- **Official Application Form (DOCX)** - Reference form in `docs/reference/`

### Test Reports (`/docs/test-reports/`)
- **[Phase 1 & 2 Test Report](docs/test-reports/PHASE1_PHASE2_TEST_REPORT.md)** - Call Management & Application Submission validation
- **[Phase 3 Test Report](docs/test-reports/PHASE3_TEST_REPORT.md)** - Feasibility Review validation

### Historical Documentation (`/archive/`)
- Old validation reports and historical documentation

## License

[To be determined]

## Contact

ReDIB Network - [info@redib.net](mailto:info@redib.net)

## Acknowledgments

Developed for CIC biomaGUNE and the ReDIB ICTS Network.
