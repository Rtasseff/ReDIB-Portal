# ReDIB Portal Documentation

This directory contains all project documentation, reference materials, and test reports.

## Directory Structure

### `/reference/`
Reference materials and specifications:
- `redib-coa-system-design.md` - Complete system design document
- `coa-application-form-spec.md` - Application form specification
- `REDIB-APP-application-form-coa-redib.docx` - Official application form (DOCX)

### `/test-reports/`
Comprehensive test reports for each phase:
- `PHASE1_PHASE2_TEST_REPORT.md` - Call Management & Application Submission tests
- `PHASE3_TEST_REPORT.md` - Feasibility Review tests

## Related Documentation

### Root Directory
- [README.md](../README.md) - Main project documentation and overview
- [QUICKSTART.md](../QUICKSTART.md) - Quick start guide for new users
- [SETUP_GUIDE.md](../SETUP_GUIDE.md) - Detailed setup and configuration
- [TESTING.md](../TESTING.md) - Testing procedures and guidelines
- [DEVELOPMENT.md](../DEVELOPMENT.md) - Development workflows and common commands

### Archive Directory (`../archive/`)
- `../archive/` - Historical documentation (CHANGELOG.md, old validation reports)
- `../archive/dev-docs/` - Development-phase documentation (PROJECT_STRUCTURE.md, design decisions)

## Test Scripts

All automated test scripts are located in `/tests/`:
- `test_phase1_phase2_workflow.py` - Call Management & Application Submission
- `test_phase3_feasibility_review.py` - Feasibility Review
- `test_phase4_evaluator_assignment.py` - Evaluator Assignment
- `test_phase5_evaluation_submission.py` - Evaluation Process
- `test_phase6_resolution.py` - Resolution & Prioritization
- `test_phase7_acceptance.py` - Acceptance & Handoff
- `test_phase9_publications.py` - Publication Tracking
- `reports/tests.py` - Reporting & Statistics

**Total:** 29 integration tests across all phases.

## Current Implementation Status

### ✅ All Phases Complete (Production-Ready)

All 10 development phases have been completed and validated with comprehensive test coverage:

- **Phase 0**: Foundation & Dashboard
- **Phase 1**: Call Management
- **Phase 2**: Application Submission (5-step wizard)
- **Phase 3**: Feasibility Review
- **Phase 4**: Evaluator Assignment (COI detection)
- **Phase 5**: Evaluation Process (5 criteria, 1-5 scale)
- **Phase 6**: Resolution & Prioritization
- **Phase 7**: Acceptance & Handoff
- **Phase 9**: Publication Tracking
- **Phase 10**: Reporting & Statistics

**Current Phase:** Comprehensive testing and validation.

Total automated tests: **29 integration tests** covering all workflow phases.

## Key Features Implemented

### Application Form (Phase 2)
- ✅ 5 applicant information fields (name, ORCID, entity, email, phone)
- ✅ 7 project types (expanded from 5)
- ✅ 20 AEI subject area classifications (expanded from 13)
- ✅ Auto-population from user profile
- ✅ Data snapshot at submission time

### Feasibility Review (Phase 3)
- ✅ Multi-node workflow
- ✅ One review per node with requested equipment
- ✅ Approval/rejection logic
- ✅ State machine compliance
- ✅ Email notifications (via Celery)

## Running Tests

See [TESTING.md](../TESTING.md) for comprehensive testing documentation.

**Quick reference:**
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

## Documentation Maintenance

When updating documentation:
1. Keep this README current with directory structure changes
2. Move outdated docs to `../archive/`
3. Update test reports after running new tests
4. Keep reference materials in `/reference/`
