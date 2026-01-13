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

### 4. Phase 4 Evaluator Assignment
**File**: `test_phase4_evaluator_assignment.py`
**Purpose**: Validates evaluator assignment workflow.

**Run**:
```bash
python tests/test_phase4_evaluator_assignment.py
```

---

### 5. Phase 5 Evaluation Submission
**File**: `test_phase5_evaluation_submission.py`
**Purpose**: Validates evaluation form submission and scoring.

**Run**:
```bash
python tests/test_phase5_evaluation_submission.py
```

---

### 6. Phase 6 Resolution (Legacy Coordinator Workflow)
**File**: `test_phase6_resolution.py`
**Purpose**: Validates the legacy ReDIB coordinator resolution workflow.

**Run**:
```bash
python tests/test_phase6_resolution.py
```

---

### 7. Phase 6 Node Resolution (New Distributed Workflow)
**File**: `test_phase6_node_resolution.py`
**Tests**: 18 workflow tests
**Purpose**: Validates the new node coordinator resolution workflow with multi-node aggregation.

**What it tests**:
- ✅ Multi-node aggregation: ALL accept → accepted
- ✅ Multi-node aggregation: ANY reject → rejected
- ✅ Multi-node aggregation: No rejects but waitlist → pending
- ✅ Competitive funding protection (cannot reject)
- ✅ Single-node immediate resolution
- ✅ Hours approval (can differ from requested)
- ✅ Equipment completion tracking
- ✅ Node coordinator validation
- ✅ Service query methods

**Run**:
```bash
python tests/test_phase6_node_resolution.py
```

**Expected output**: 18/18 tests passed

**Test data created**:
- Call: NR-TEST-CALL-01
- Nodes: NR-TEST-NODE1, NR-TEST-NODE2
- Coordinators: nc1.nr.test@redib.test, nc2.nr.test@redib.test
- Applications: Multiple test applications with different resolution outcomes

---

### 8. Phase 7 Acceptance Workflow
**File**: `test_phase7_acceptance.py`
**Purpose**: Validates applicant acceptance/rejection of approved applications.

**Run**:
```bash
python tests/test_phase7_acceptance.py
```

---

### 9. Phase 9 Publications
**File**: `test_phase9_publications.py`
**Purpose**: Validates publication tracking and reporting.

**Run**:
```bash
python tests/test_phase9_publications.py
```

---

## Running All Tests

To run all automated test suites:

```bash
# Run all tests sequentially
python tests/test_application_form_spec.py && \
python tests/test_phase1_phase2_workflow.py && \
python tests/test_phase3_feasibility_review.py && \
python tests/test_phase4_evaluator_assignment.py && \
python tests/test_phase5_evaluation_submission.py && \
python tests/test_phase6_resolution.py && \
python tests/test_phase6_node_resolution.py && \
python tests/test_phase7_acceptance.py && \
python tests/test_phase9_publications.py
```

**Note**: Test counts vary by file. Run individual tests to see specific counts.

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
| Phase 2 | ✅ Automated | test_phase1_phase2_workflow.py + test_application_form_spec.py | 13 + 63 |
| Phase 3 | ✅ Automated | test_phase3_feasibility_review.py | 29 |
| Phase 4 | ✅ Automated | test_phase4_evaluator_assignment.py | - |
| Phase 5 | ✅ Automated | test_phase5_evaluation_submission.py | - |
| Phase 6 | ✅ Automated | test_phase6_resolution.py + test_phase6_node_resolution.py | 18 (node resolution) |
| Phase 7 | ✅ Automated | test_phase7_acceptance.py | - |
| Phase 8 | ⏳ Pending | - | - |
| Phase 9 | ✅ Automated | test_phase9_publications.py | - |
| Phase 10 | ⏳ Pending | - | - |

---

## Support

For questions or issues with tests:
1. Check test reports in `/docs/test-reports/`
2. Review test output for specific failure messages
3. Consult [TEST.md](../TEST.md) for manual testing procedures
4. Check Django logs for error details
