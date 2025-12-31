# ReDIB Portal - Automated Test Suites

This directory contains automated test scripts for validating the ReDIB COA portal implementation.

## Test Scripts

### 1. Application Form Specification Validation
**File**: `test_application_form_spec.py`
**Tests**: 63 validation tests
**Purpose**: Validates that the application form implementation exactly matches the official DOCX specification.

**What it tests**:
- ✅ Model fields (5 applicant information fields)
- ✅ Project types (7 choices)
- ✅ Subject areas (20 AEI classifications)
- ✅ Form field validation (required/optional)
- ✅ Template rendering (all 3 templates)

**Run**:
```bash
python tests/test_application_form_spec.py
```

**Expected output**: 63/63 tests passed

---

### 2. Phase 1 & 2 End-to-End Workflow
**File**: `test_phase1_phase2_workflow.py`
**Tests**: 23 integration tests
**Purpose**: Validates complete call creation and application submission workflows.

**What it tests**:
- ✅ Call management (Phase 1)
  - Call creation with equipment allocations
  - Call status and open/close logic
- ✅ Application submission (Phase 2)
  - 5-step wizard workflow
  - New applicant fields auto-population
  - Equipment requests
  - Scientific content
  - Declarations
  - Database persistence

**Run**:
```bash
python tests/test_phase1_phase2_workflow.py
```

**Expected output**: 23/23 tests passed

**Test data created**:
- Call: TEST-E2E-2025
- Application: TEST-E2E-2025-001
- Users: test.e2e.applicant@redib.test, test.e2e.coordinator@redib.test

---

### 3. Phase 3 Feasibility Review Workflow
**File**: `test_phase3_feasibility_review.py`
**Tests**: 29 workflow tests
**Purpose**: Validates feasibility review process and state transitions.

**What it tests**:
- ✅ Multi-node review creation
- ✅ Partial approval workflow (one node approves, others pending)
- ✅ All nodes approve → Status: pending_evaluation
- ✅ One node rejects → Status: rejected_feasibility
- ✅ State machine compliance
- ✅ Node coordinator permissions
- ✅ Terminal state validation

**Run**:
```bash
python tests/test_phase3_feasibility_review.py
```

**Expected output**: 29/29 tests passed

**Test data created**:
- Call: PHASE3-TEST-2025
- Nodes: CICBIO, CNIC
- Coordinators: cicbio.phase3.test@redib.test, cnic.phase3.test@redib.test
- Applications: 2 test applications with different outcomes

---

## Running All Tests

To run all automated test suites:

```bash
# Run all tests sequentially
python tests/test_application_form_spec.py && \
python tests/test_phase1_phase2_workflow.py && \
python tests/test_phase3_feasibility_review.py
```

**Total tests**: 115 (63 + 23 + 29)

---

## Test Characteristics

### Idempotent
All test scripts are idempotent - they clean up previous test data before running, so they can be executed multiple times safely.

### Isolated
Each test script creates its own test data and doesn't interfere with other tests or existing data.

### Comprehensive
Tests cover:
- Model validation
- Form validation
- View logic
- State transitions
- Database persistence
- Template rendering
- Multi-user workflows
- Permission checking

---

## Test Data

### Development Database
Tests use the Django ORM and will create test data in your development database. Test data is clearly marked with prefixes:
- `TEST-E2E-*` - Phase 1 & 2 test data
- `PHASE3-TEST-*` - Phase 3 test data
- `*.test@redib.test` - Test user emails

### Cleanup
Tests clean up their own data before running. To manually clean up all test data:

```bash
python manage.py shell -c "
from applications.models import Application
from calls.models import Call
from django.contrib.auth import get_user_model
User = get_user_model()

Application.objects.filter(code__contains='TEST').delete()
Call.objects.filter(code__contains='TEST').delete()
User.objects.filter(email__contains='.test@redib.test').delete()
"
```

---

## Test Reports

Detailed test reports with results, bug fixes, and validation analysis are available in `/docs/test-reports/`:

- **PHASE1_PHASE2_TEST_REPORT.md** - Comprehensive Phase 1 & 2 validation
- **PHASE3_TEST_REPORT.md** - Phase 3 validation with bug fixes documented

---

## Continuous Integration

These test scripts are designed to be run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Tests
  run: |
    python tests/test_application_form_spec.py
    python tests/test_phase1_phase2_workflow.py
    python tests/test_phase3_feasibility_review.py
```

---

## Extending Tests

When adding new phases or features:

1. Create a new test file: `test_phaseX_feature.py`
2. Follow the existing pattern:
   - Create a test class
   - Implement cleanup method
   - Implement setup method
   - Write test methods
   - Add print summary method
3. Document in this README
4. Update `/docs/test-reports/` with test results
5. Update main [TEST.md](../TEST.md)

---

## Test Coverage by Phase

| Phase | Coverage | Test File | Tests |
|-------|----------|-----------|-------|
| Phase 0 | ✅ Manual | - | - |
| Phase 1 | ✅ Automated | test_phase1_phase2_workflow.py | 5 |
| Phase 2 | ✅ Automated | test_phase1_phase2_workflow.py | 13 + 63 |
| Phase 3 | ✅ Automated | test_phase3_feasibility_review.py | 29 |
| Phase 4 | ⏳ Pending | - | - |
| Phase 5 | ⏳ Pending | - | - |
| Phase 6 | ⏳ Pending | - | - |
| Phase 7 | ⏳ Pending | - | - |
| Phase 8 | ⏳ Pending | - | - |
| Phase 9 | ⏳ Pending | - | - |
| Phase 10 | ⏳ Pending | - | - |

---

## Support

For questions or issues with tests:
1. Check test reports in `/docs/test-reports/`
2. Review test output for specific failure messages
3. Consult [TEST.md](../TEST.md) for manual testing procedures
4. Check Django logs for error details
