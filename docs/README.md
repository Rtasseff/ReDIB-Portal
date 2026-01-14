# ReDIB Portal Documentation

This directory contains all project documentation, reference materials, and test reports.

## Documentation Index

### Getting Started
- **[QUICKSTART.md](QUICKSTART.md)** - Quick start guide for new users
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Detailed setup and configuration
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Development workflows and common commands

### User Documentation
- **[USER_GUIDE.md](USER_GUIDE.md)** - Complete end-user guide for all portal roles

### Testing
- **[TESTING.md](TESTING.md)** - Testing procedures and guidelines
- **[TEST_APPLICANTS_GUIDE.md](TEST_APPLICANTS_GUIDE.md)** - Test data and manual testing scenarios

## Directory Structure

### `/reference/`
Reference materials and specifications:
- `redib-coa-system-design.md` - Complete system design document
- `coa-application-form-spec.md` - Application form specification
- `evaluationForm_en.md` - Evaluation form specification

### `/test-reports/`
Comprehensive test reports for each phase:
- `PHASE1_PHASE2_TEST_REPORT.md` - Call Management & Application Submission
- `PHASE3_TEST_REPORT.md` - Feasibility Review
- `PHASE4_TEST_REPORT.md` - Evaluator Assignment
- `PHASE_8_9_10_TEST_RESULTS.md` - Acceptance, Publications, and Reporting

### `/archive/`
Completed planning documents and historical notes:
- `PHASE_6_CHANGE.md` - Node coordinator resolution workflow implementation
- `PHASES_8_9_10_REVIEW.md` - Phases 8-10 review and implementation
- `ACCEPTANCE_WORKFLOW_FIXED.md` - Acceptance workflow fixes
- `OPTIMIZE_SPEED.md` - Performance optimization plan
- `TESTING_NOTES.md` - Historical testing notes

## Test Scripts

All automated test scripts are located in `/tests/`:
- `test_application_form_spec.py` - Application form specification validation (63 tests)
- `test_phase1_phase2_workflow.py` - Call Management & Application Submission (23 tests)
- `test_phase3_feasibility_review.py` - Feasibility Review (29 tests)
- `test_phase4_evaluator_assignment.py` - Evaluator Assignment
- `test_phase5_evaluation_submission.py` - Evaluation Process
- `test_phase6_resolution.py` - Resolution & Prioritization (legacy)
- `test_phase6_node_resolution.py` - Node Coordinator Resolution (18 tests)
- `test_phase7_acceptance.py` - Acceptance & Handoff
- `test_phase9_publications.py` - Publication Tracking

**Total:** 47+ integration tests across all phases.

## Quick Database Setup

```bash
# Set up complete test database with one command
python manage.py setup_test_database --reset --yes
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for more options.

## Current Implementation Status

### All Phases Complete (Production-Ready)

- **Phase 0**: Foundation & Dashboard
- **Phase 1**: Call Management
- **Phase 2**: Application Submission (5-step wizard)
- **Phase 3**: Feasibility Review (multi-node)
- **Phase 4**: Evaluator Assignment (COI detection)
- **Phase 5**: Evaluation Process (5 criteria, 1-5 scale)
- **Phase 6**: Resolution & Prioritization (node coordinator ownership)
- **Phase 7**: Acceptance & Handoff (10-day deadline)
- **Phase 8**: Access Handoff (email automation)
- **Phase 9**: Publication Tracking
- **Phase 10**: Reporting & Statistics

## Related Documentation

- [../README.md](../README.md) - Main project README
- [../tests/README.md](../tests/README.md) - Test suite documentation
- [../archive/](../archive/) - Historical project documentation
