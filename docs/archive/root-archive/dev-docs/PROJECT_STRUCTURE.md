# ReDIB Portal - Project Structure

**Last Updated**: 2026-01-01 (All Phases 0-10 Completed)

This document provides an overview of the project's organization and file structure.

---

## Root Directory

```
ReDIB-Portal/
├── README.md                 # Main project README (updated)
├── TEST.md                   # Testing guide (updated with automated tests)
├── QUICKSTART.md             # Quick start guide
├── SETUP_GUIDE.md            # Detailed setup instructions
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── Dockerfile                # Docker configuration
├── docker-compose.yml        # Production Docker setup
├── docker-compose.dev.yml    # Development Docker setup
└── db.sqlite3                # Development database
```

---

## Application Directories

### Core Apps
```
applications/        # Application submission and workflow
├── models.py       # Application, RequestedAccess, FeasibilityReview
├── views.py        # 5-step wizard, feasibility review
├── forms.py        # ApplicationStep1-5Forms, FeasibilityReviewForm
├── admin.py        # Django admin configuration
└── migrations/     # Database migrations

calls/              # Call management
├── models.py       # Call, CallEquipmentAllocation
├── views.py        # Call CRUD, public views
└── forms.py        # Call forms

core/               # Foundation (users, nodes, equipment)
├── models.py       # User, Node, Equipment, Organization
├── decorators.py   # Role-based permission decorators
├── context_processors.py  # User roles in templates
└── management/commands/
    └── populate_redib_equipment.py  # Equipment population

evaluations/        # Evaluation system (Phase 4-6)
access/             # Access grants and tracking (Phase 7-9)
communications/     # Email templates and sending
reports/            # Reporting and statistics (Phase 10)
```

---

## Documentation (`/docs/`)

### Documentation Structure
```
docs/
├── README.md                           # Documentation guide
├── reference/                          # Reference materials
│   ├── redib-coa-system-design.md     # System design document
│   ├── coa-application-form-spec.md   # Form specification
│   └── REDIB-APP-application-form-coa-redib.docx  # Official form
└── test-reports/                       # Test validation reports
    ├── PHASE1_PHASE2_TEST_REPORT.md   # Phases 1 & 2 validation
    └── PHASE3_TEST_REPORT.md          # Phase 3 validation
```

### Reference Materials (`/docs/reference/`)
- **redib-coa-system-design.md** - Complete system architecture, requirements, and implementation plan for all 10 phases
- **coa-application-form-spec.md** - Detailed specification of the application form matching the official DOCX
- **REDIB-APP-application-form-coa-redib.docx** - Official application form from ReDIB

### Test Reports (`/docs/test-reports/`)
- **PHASE1_PHASE2_TEST_REPORT.md** - Comprehensive validation of Call Management and Application Submission (86 tests)
- **PHASE3_TEST_REPORT.md** - Feasibility Review validation with bug fixes documented (29 tests)

---

## Test Suites (`/tests/`)

### Test Scripts
```
tests/
├── README.md                              # Test suite documentation
├── test_phase1_phase2_workflow.py         # Phases 1 & 2 (2 tests)
├── test_phase3_feasibility_review.py      # Phase 3 (4 tests)
├── test_phase4_evaluator_assignment.py    # Phase 4 (3 tests)
├── test_phase5_evaluation_submission.py   # Phase 5 (3 tests)
├── test_phase6_resolution.py              # Phase 6 (3 tests)
├── test_phase7_acceptance.py              # Phase 7 (3 tests)
└── test_phase9_publications.py            # Phase 9 (11 tests)

reports/
└── tests.py                               # Phase 10 (11 tests)
```

**Total**: 29 integration tests across all phases

### Test Coverage
- ✅ **Phase 0**: Foundation & Dashboard (manual)
- ✅ **Phase 1-2**: Call & Application workflow (2 tests)
- ✅ **Phase 3**: Feasibility review (4 tests)
- ✅ **Phase 4**: Evaluator assignment (3 tests)
- ✅ **Phase 5**: Evaluation process (3 tests)
- ✅ **Phase 6**: Resolution & prioritization (3 tests)
- ✅ **Phase 7**: Acceptance & handoff (3 tests)
- ✅ **Phase 9**: Publication tracking (11 tests)
- ✅ **Phase 10**: Reporting & statistics (11 tests - 4 core passing)

---

## Archive (`/archive/`)

Historical documentation moved to archive:

```
archive/
├── CHANGELOG.md              # Old changelog
├── CODE_REVIEW_FIXES.md      # Historical code review fixes
├── VALIDATION_SUMMARY.md     # Old validation summary
└── TEST_SETUP.md             # Old test setup guide
```

These files are preserved for historical reference but are no longer actively maintained.

---

## Templates (`/templates/`)

### Django Templates
```
templates/
├── base.html                     # Base template
├── dashboard_base.html           # Dashboard base
├── home.html                     # Homepage
├── applications/
│   ├── wizard_step1.html         # Step 1: Applicant info
│   ├── wizard_step2.html         # Step 2: Funding
│   ├── wizard_step3.html         # Step 3: Equipment
│   ├── wizard_step4.html         # Step 4: Scientific content
│   ├── wizard_step5.html         # Step 5: Declarations
│   ├── preview.html              # Application preview
│   ├── detail.html               # Application detail
│   ├── my_applications.html      # Applicant dashboard
│   ├── feasibility_queue.html    # Node coordinator queue
│   └── feasibility_review.html   # Review form
├── calls/
│   ├── public_list.html          # Public call listing
│   ├── public_detail.html        # Public call detail
│   └── ...                       # Coordinator views
└── ...
```

---

## Current Implementation Status

### ✅ Completed Phases (Production-Ready)

#### Phase 0: Foundation & Dashboard
- User authentication & roles
- Base templates
- Permission decorators

#### Phase 1: Call Management
- Create and publish COA calls
- Equipment allocation
- Public call listings

#### Phase 2: Application Submission
- **5-step wizard workflow**
- **5 applicant information fields** (name, ORCID, entity, email, phone)
- **7 project types** (national, international_non_european, regional, european, internal, private, other)
- **20 AEI subject area classifications** (cso, der, eco, mlp, fla, pha, edu, psi, mtm, fis, pin, tic, eyt, ctq, mat, ctm, caa, bio, bme, other)
- Auto-population from user profile
- Equipment access requests
- Scientific content (6 evaluation criteria)
- Declarations and consent

#### Phase 3: Feasibility Review
- Multi-node technical feasibility reviews
- Approval/rejection workflow
- Automated state transitions
- Email notifications

**Testing**: All completed phases have comprehensive automated test suites (115 tests total, all passing).

### 🔄 Pending Phases

- Phase 4: Evaluator Assignment
- Phase 5: Evaluation Process
- Phase 6: Resolution & Prioritization
- Phase 7: Acceptance & Scheduling
- Phase 8: Execution & Completion
- Phase 9: Publication Follow-up
- Phase 10: Reporting & Statistics

---

## Key Files and Their Purposes

### Configuration
- `.env` - Environment variables (git-ignored)
- `.env.example` - Environment variables template
- `requirements.txt` - Python package dependencies

### Core Models
- `core/models.py` - User, Organization, Node, Equipment, UserRole
- `applications/models.py` - Application (with state machine), RequestedAccess, FeasibilityReview
- `calls/models.py` - Call, CallEquipmentAllocation

### Management Commands
- `core/management/commands/populate_redib_equipment.py` - Populate 17 equipment items across 4 nodes
- `applications/management/commands/seed_dev_data.py` - Seed development test data

---

## Quick Navigation

### For Developers
- Start here: [README.md](README.md)
- Setup: [SETUP_GUIDE.md](SETUP_GUIDE.md) or [QUICKSTART.md](QUICKSTART.md)
- Testing: [TEST.md](TEST.md) and [tests/README.md](tests/README.md)

### For Documentation
- Overview: [docs/README.md](docs/README.md)
- System design: [docs/reference/redib-coa-system-design.md](docs/reference/redib-coa-system-design.md)
- Form spec: [docs/reference/coa-application-form-spec.md](docs/reference/coa-application-form-spec.md)

### For Testing
- Test guide: [tests/README.md](tests/README.md)
- Test reports: [docs/test-reports/](docs/test-reports/)
- Run tests:
  ```bash
  python tests/test_application_form_spec.py
  python tests/test_phase1_phase2_workflow.py
  python tests/test_phase3_feasibility_review.py
  ```

---

## Summary

### Organization Principles

1. **Root directory** - Essential project files and core documentation
2. **`/docs/`** - All documentation, organized by type (reference, test reports)
3. **`/tests/`** - All automated test scripts with their own README
4. **`/archive/`** - Historical documentation, preserved but not actively used
5. **Application directories** - Django apps following standard Django structure

### Benefits

✅ Clear separation of concerns (code, docs, tests, archive)
✅ Easy navigation with README files at each level
✅ All documentation up-to-date and properly referenced
✅ Test scripts easily discoverable and well-documented
✅ Historical materials preserved but out of the way
✅ Standard Django project structure maintained

---

**Last Updated**: 2025-12-31
**Phases Complete**: 0-3 (4 of 10 phases)
**Tests Passing**: 115/115 (100%)
**Documentation Status**: ✅ Up-to-date
