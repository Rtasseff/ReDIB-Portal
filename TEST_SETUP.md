# Test Database Setup Guide

For development testing, this document describes the minimal viable dataset that exercises all workflows.

**STATUS: ✅ IMPLEMENTED** - Use the `seed_dev_data` management command (see Usage section below).

## Minimal Test Database Setup

### Users (8 total)

| Username | Role | Purpose |
|----------|------|---------|
| `admin` | Admin | System configuration, full access |
| `coordinator` | Coordinator | Manages calls, assigns evaluators, resolves |
| `node_cic` | Node Coordinator | CIC biomaGUNE feasibility reviews |
| `node_cnic` | Node Coordinator | TRIMA@CNIC feasibility reviews |
| `evaluator1` | Evaluator | Preclinical expertise |
| `evaluator2` | Evaluator | Clinical expertise |
| `applicant1` | Applicant | Primary test applicant |
| `applicant2` | Applicant | Secondary (for testing multiple apps) |

### Organizations (3 total)

- **ReDIB** (internal - for node coordinators)
- **Universidad Test** (Spanish university - for applicants)
- **External Research Institute** (international - for applicant2)

### Nodes (2 of 4)

You don't need all four nodes for development. Pick two that cover different equipment types:

- **CIC biomaGUNE** - has MRI, PET-CT, SPECT, cyclotron (preclinical focus)
- **TRIMA@CNIC** - has MRI, PET-CT, SPECT (clinical focus)

### Equipment (4-5 items)

Just enough to test multi-node and multi-equipment requests:

| Node | Equipment | Category |
|------|-----------|----------|
| CIC biomaGUNE | MRI 7T | MRI |
| CIC biomaGUNE | PET-CT | Nuclear |
| TRIMA@CNIC | MRI 3T | MRI |
| TRIMA@CNIC | PET-CT | Nuclear |

### Calls (2)

- **COA-TEST-01** - Status: `RESOLVED` (closed call with completed workflow)
- **COA-TEST-02** - Status: `OPEN` (active call for testing submissions)

### Applications (3-4)

One application in each key state:

| Code | Applicant | Call | Status | Purpose |
|------|-----------|------|--------|---------|
| `APP-001` | applicant1 | COA-TEST-01 | `COMPLETED` | Full history, has evaluations, grant, publication |
| `APP-002` | applicant2 | COA-TEST-01 | `REJECTED` | Shows rejection flow |
| `APP-003` | applicant1 | COA-TEST-02 | `DRAFT` | Test submission flow |
| `APP-004` | applicant2 | COA-TEST-02 | `UNDER_FEASIBILITY_REVIEW` | Test node review |

### Evaluations (2-4)

For APP-001 only (the completed one):
- evaluator1 → scores filled, completed
- evaluator2 → scores filled, completed

---

## Implementation Details

The management command is located at:
```
applications/management/commands/seed_dev_data.py
```

**Key features:**
- ✅ Idempotent: Safe to run multiple times (uses `get_or_create`)
- ✅ Correct model field values (email-based auth, AEI subject areas, proper equipment categories)
- ✅ Proper model imports from correct apps
- ✅ Complete UserRole assignments with nodes and specialization areas
- ✅ Full workflow coverage: draft → feasibility review → evaluation → completed/rejected

---

## Usage

```bash
# First time or reset everything
python manage.py seed_dev_data --clear

# Just add missing items (idempotent)
python manage.py seed_dev_data
```

---

## What This Lets You Test

| Workflow | How to Test |
|----------|-------------|
| **Submit application** | Login as `applicant1`, complete APP-TEST-003 |
| **Feasibility review** | Login as `node_cnic`, review APP-TEST-004 |
| **Evaluator workflow** | Login as `evaluator1`, view assigned apps |
| **Coordinator resolution** | Login as `coordinator`, resolve a call |
| **View completed history** | APP-TEST-001 has full audit trail |
| **Statistics/reporting** | Has enough data for basic stats |
| **Email templates** | Trigger actions, check console/logs |

All passwords are `testpass123` for simplicity. Adapt the model imports and field names to match your actual implementation.
