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
- `README.md` - Main project README with setup instructions
- `TEST.md` - Testing guide and workflow validation
- `QUICKSTART.md` - Quick start guide for development
- `SETUP_GUIDE.md` - Detailed setup instructions

### Archive Directory (`../archive/`)
Historical documentation and old validation reports.

## Test Scripts

All automated test scripts are located in `/tests/`:
- `test_application_form_spec.py` - Application form specification validation
- `test_phase1_phase2_workflow.py` - End-to-end workflow for Phases 1 & 2
- `test_phase3_feasibility_review.py` - Feasibility review workflow validation

## Current Implementation Status

### ✅ Completed Phases (Phases 0-3)
- **Phase 0**: Foundation & Dashboard
- **Phase 1**: Call Management
- **Phase 2**: Application Submission (5-step wizard)
- **Phase 3**: Feasibility Review

All phases have been independently tested and validated with automated test suites.

### 🔄 Pending Phases (Phases 4-10)
- Phase 4: Evaluator Assignment
- Phase 5: Evaluation Process
- Phase 6: Resolution & Prioritization
- Phase 7: Acceptance & Scheduling
- Phase 8: Execution & Completion
- Phase 9: Publication Follow-up
- Phase 10: Reporting & Statistics

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

All test scripts can be run independently:

```bash
# Specification validation
python tests/test_application_form_spec.py

# Phase 1 & 2 workflow
python tests/test_phase1_phase2_workflow.py

# Phase 3 workflow
python tests/test_phase3_feasibility_review.py
```

## Documentation Maintenance

When updating documentation:
1. Keep this README current with directory structure changes
2. Move outdated docs to `../archive/`
3. Update test reports after running new tests
4. Keep reference materials in `/reference/`
