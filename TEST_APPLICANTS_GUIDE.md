# Test Applicants & Applications Guide

This guide describes the test data created by the `seed_test_applicants` management command.

## Overview

The script creates **7 test applicants** with **17 applications** across all workflow stages to facilitate comprehensive testing of the ReDIB COA Portal.

## Test Applicants

All test applicants use the password: **`testpass123`**

| Email | Name | Applications | Organization Type |
|-------|------|--------------|-------------------|
| testapplicant1@university.es | María García | 3 | University |
| testapplicant2@research.de | Thomas Schmidt | 3 | Research Center |
| testapplicant3@hospital.fr | Claire Dubois | 3 | Hospital |
| testapplicant4@biotech.com | John Williams | 2 | Company |
| testapplicant5@institute.it | Lucia Rossi | 2 | Research Center |
| testapplicant6@university.uk | David Brown | 2 | University |
| testapplicant7@lab.ch | Anna Mueller | 2 | Company |

## Applications by Status

The script creates applications in the following stages:

| Status | Count | Test Purpose |
|--------|-------|--------------|
| Draft | 1 | Test saving and resuming applications |
| Submitted | 1 | Test feasibility review workflow |
| Under Feasibility Review | 1 | Test node coordinator review process |
| Rejected - Not Feasible | 1 | Test feasibility rejection |
| Pending Evaluation | 1 | Test evaluator assignment |
| Under Evaluation | 2 | Test partial evaluations (1 of 2 complete vs both complete) |
| Evaluated | 2 | Test resolution decisions |
| Accepted | 5 | Test acceptance workflow and hours tracking |
| Pending (Waiting List) | 1 | Test waiting list functionality |
| Rejected | 1 | Test rejection notifications |
| Declined by Applicant | 1 | Test applicant declining accepted access |

**Total: 17 applications**

## Application Details

### Early Stage Applications (Phase 1-3)
- **TEST-APP-001**: Draft - No equipment selected yet
- **TEST-APP-002**: Submitted - Awaiting feasibility review
- **TEST-APP-003**: Under Feasibility Review - Node coordinator needs to review
- **TEST-APP-012**: Rejected (Feasibility) - Failed technical feasibility

### Evaluation Stage Applications (Phase 4-6)
- **TEST-APP-004**: Pending Evaluation - Ready for evaluator assignment
- **TEST-APP-005**: Under Evaluation - **1 of 2 evaluations complete** (tests partial evaluation)
- **TEST-APP-014**: Under Evaluation - Both evaluations complete
- **TEST-APP-006**: Evaluated - Score: 9.5/12 - Ready for resolution
- **TEST-APP-017**: Evaluated - Score: 9.0/12 - Ready for resolution

### Resolution & Acceptance (Phase 6-7)
- **TEST-APP-007**: Accepted - Score: 10.5/12 - Awaiting applicant acceptance
- **TEST-APP-008**: Pending (Waiting List) - Score: 8.5/12
- **TEST-APP-009**: Rejected - Score: 4.0/12
- **TEST-APP-010**: Accepted - Score: 11.0/12
- **TEST-APP-011**: Declined by Applicant - Score: 9.0/12 - Applicant declined
- **TEST-APP-013**: Accepted - Score: 10.0/12
- **TEST-APP-015**: Accepted - Score: 8.0/12 (below threshold but manually accepted)
- **TEST-APP-016**: Accepted - Score: 11.5/12 - **Has competitive funding**

## Testing Scenarios

### Test Feasibility Review (Phase 3)
1. Login as `node.cic@redib.net` or `node.cnic@redib.net` (password: need to set via admin)
2. View applications under feasibility review
3. Approve or reject based on technical feasibility
4. Test multi-node applications (some applications request equipment from multiple nodes)

### Test Evaluator Assignment (Phase 4)
1. Login as `coordinator@redib.net` (password: need to set via admin)
2. Navigate to call management
3. Assign evaluators to applications in "Pending Evaluation" status
4. Verify COI detection (evaluators from same organization excluded)

### Test Evaluation Process (Phase 5)
1. Login as `evaluator1@redib.net`, `evaluator2@redib.net`, or `evaluator3@redib.net`
2. View assigned applications (blind - no applicant details)
3. Score applications using 0-2 scale (6 criteria, max 12 points)
4. Submit evaluations with recommendations

### Test Resolution & Prioritization (Phase 6)
1. Login as `coordinator@redib.net`
2. View evaluated applications
3. Test auto-resolution based on threshold (e.g., ≥9.0/12)
4. Test manual overrides (accepting below threshold, rejecting above threshold)
5. Verify competitive funding applications auto-approved

### Test Acceptance Workflow (Phase 7)
1. Login as test applicants
2. View accepted applications
3. Accept or decline access within 10-day deadline
4. Test acceptance deadline enforcement

### Test Hours Tracking
- Applications have varied hours requested: 16, 24, or 32 hours
- Test the three-tier tracking system:
  - `hours_requested`: Original request
  - `hours_approved`: Approved hours
  - `actual_hours_used`: Actual usage (to be recorded on completion)

## Special Test Cases

### Multi-Equipment Applications
- Every 5th application (TEST-APP-001, TEST-APP-006, etc.) requests equipment from **multiple nodes**
- Tests multi-node feasibility review workflow
- All nodes must approve for application to proceed

### Competitive Funding
- Every 4th application has `has_competitive_funding=True`
- **TEST-APP-016** specifically tests competitive funding auto-approval
- These applications should be auto-approved regardless of score

### Specialization Areas
- Applications rotate through: Preclinical, Clinical, Radiotracers
- Tests area-based evaluator matching

### Partial Evaluation
- **TEST-APP-005**: Only 1 of 2 evaluations complete
- Tests "waiting for all evaluators" functionality
- Application should remain in "Under Evaluation" status

## Running the Script

### Initial Setup
```bash
# 1. Ensure basic data is seeded
python manage.py seed_email_templates
python manage.py populate_redib_nodes
python manage.py populate_redib_equipment
python manage.py populate_redib_users

# 2. Create organizations and calls (if not already done)
# See the inline shell script in the implementation

# 3. Run the test applicants script
python manage.py seed_test_applicants
```

### Clearing and Recreating
```bash
# Clear existing test applicants and recreate
python manage.py seed_test_applicants --clear
```

**Note:** The `--clear` flag only removes test applicants (emails containing 'testapplicant'), not the applicants from `seed_dev_data.py`.

## Integration with Existing Data

This script works alongside:
- `seed_dev_data.py`: Creates basic roles and 2 applicants with simple applications
- `populate_redib_*`: Loads nodes, equipment, and core users from CSV files
- `seed_email_templates`: Loads email templates

The test applicants script requires:
- At least one Call (open or resolved)
- Active nodes and equipment
- Organizations for applicant affiliations
- Evaluators and node coordinators (from populate_redib_users)

## Verification

After running the script, verify the data:

```bash
python manage.py shell
```

```python
from applications.models import Application
from django.db.models import Count

# Check application counts by status
for status, label in Application.APPLICATION_STATUSES:
    count = Application.objects.filter(status=status).count()
    if count > 0:
        print(f"{label}: {count}")

# Check evaluations
from evaluations.models import Evaluation
print(f"\nTotal evaluations: {Evaluation.objects.count()}")
print(f"Completed: {Evaluation.objects.filter(completed_at__isnull=False).count()}")
```

## Next Steps

1. **Set passwords** for coordinator and evaluator accounts (use admin or shell)
2. **Login as different users** to test workflows
3. **Progress applications** through stages manually
4. **Test email notifications** (if Celery is configured)
5. **Test reporting** and statistics views with diverse data

## Troubleshooting

### No calls found error
- Run the organizations and calls creation script
- Or run `seed_dev_data.py` to create calls

### No evaluators found
- Run `python manage.py populate_redib_users`
- Ensure evaluators have `is_active=True` roles

### Evaluation field errors
- This script uses the NEW 0-12 scoring system (6 criteria, 0-2 scale)
- Field names: `score_quality_originality`, `score_methodology_design`, `score_expected_contributions`, `score_knowledge_advancement`, `score_social_economic_impact`, `score_exploitation_dissemination`

## Additional Notes

- All applications have realistic scientific content for each specialization area
- Project titles are randomized based on the specialization area
- Scores are distributed to create realistic test scenarios
- Applications are timestamped in the past (-10 days) to simulate real workflow timing
