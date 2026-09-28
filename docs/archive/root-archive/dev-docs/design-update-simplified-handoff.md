# Design Updates: Simplified Acceptance & Handoff Process

## Summary of Change

The ReDIB COA portal **does not** manage equipment scheduling or time allocation tracking. After evaluation resolution:

1. Applicants accept or decline their approved access
2. For mutually accepted applications (approved by committee + accepted by applicant), the system sends a **handoff email** to both the applicant and relevant node coordinator(s)
3. The node coordinates scheduling internally using their own systems
4. ReDIB portal simply logs the handoff and tracks the requested hours for reporting purposes

---

## Updated Phase 7: Acceptance & Handoff

**Views needed:** Applicant acceptance view, Handoff confirmation (admin/coordinator view)

Per REDIB-02-PDA section 6.1.6: *"Applicants have a period of ten (10) days from the publication of the resolution to accept or reject in writing the access granted"*

| Step | Action | User | Expected Result |
|------|--------|------|-----------------|
| 7.1 | View resolution notification | `applicant1` | See acceptance email with details |
| 7.2 | Login and view granted access | `applicant1` | See approved application, hours requested, node(s) involved |
| 7.3 | Accept access grant | `applicant1` | Acceptance recorded, status → `accepted` |
| 7.4 | System sends handoff email | System | Email to applicant AND node coordinator(s) with application details |
| 7.5 | Verify handoff logged | `coordinator` | Can see list of handed-off applications |
| 7.6 | Test: Applicant declines | `applicant2` | Status → `declined_by_applicant`, no handoff email sent |
| 7.7 | Test: 10-day deadline passes | System | Reminder at day 7, auto-decline at day 10 if no response |

**What the system tracks:**
- Application status: `accepted` or `declined_by_applicant`
- `accepted_at` timestamp
- Hours originally requested (from application, for reporting)
- Handoff email sent timestamp

**What the system does NOT track:**
- Actual scheduled dates
- Time slot allocation
- Whether work was completed
- Actual hours used

---

## Handoff Email Template

**To:** Applicant, Node Coordinator(s)  
**Subject:** ReDIB COA Access Approved - Application {code} Ready for Scheduling

```
Dear {applicant_name} and {node_name} Team,

This is to confirm that COA application {application_code} has been approved 
and accepted by the applicant.

APPLICATION DETAILS
-------------------
Application Code: {code}
Applicant: {applicant_name} ({applicant_entity})
Email: {applicant_email}
Phone: {applicant_phone}

Project: {project_title}
Brief Description: {brief_description}

REQUESTED ACCESS
----------------
Node: {node_name}
Equipment: {equipment_name}
Hours Requested: {hours_requested}
Service Modality: {service_modality}

NEXT STEPS
----------
Please coordinate directly to schedule the access time. The applicant and 
node team should arrange mutually convenient dates for the requested work.

For any questions about this application, contact: info@redib.net

---
This is an automated notification from the ReDIB COA Management System.
```

**Note:** If application involves multiple nodes, send separate emails to each node coordinator (or CC all).

---

## Updated Data Model

### Simplified AccessGrant Model (or remove entirely)

**Option A: Keep minimal AccessGrant**

```python
class AccessGrant(models.Model):
    """Records approved and accepted access - minimal tracking"""
    application = models.ForeignKey(Application, on_delete=models.PROTECT)
    
    # Acceptance tracking
    accepted_by_applicant = models.BooleanField(null=True)  # True=accepted, False=declined, None=pending
    accepted_at = models.DateTimeField(null=True)
    
    # Handoff tracking
    handoff_email_sent_at = models.DateTimeField(null=True)
    
    # For reporting only (copied from application at time of approval)
    hours_requested = models.DecimalField(max_digits=6, decimal_places=1)
    
    class Meta:
        # One grant record per application (not per equipment)
        unique_together = []  # Remove if previously had application+equipment
```

**Option B: No separate model - track on Application**

Just add fields to Application model:

```python
# Add to Application model
accepted_by_applicant = models.BooleanField(null=True)  # True/False/None
accepted_at = models.DateTimeField(null=True)
handoff_email_sent_at = models.DateTimeField(null=True)
```

This is simpler since we're not tracking per-equipment grants, just per-application acceptance.

**Recommendation:** Option B - keep it on the Application model. Less complexity.

---

## Updated Application Status Flow

```
SUBMITTED
    ↓
UNDER_FEASIBILITY_REVIEW
    ↓
FEASIBILITY_REJECTED ←── (if node says not feasible)
    ↓
PENDING_EVALUATION
    ↓
UNDER_EVALUATION
    ↓
EVALUATED
    ↓
┌───────────────────────────────────────┐
│           RESOLUTION                  │
├───────────────────────────────────────┤
│ APPROVED_PENDING_ACCEPTANCE           │ ← Approved by committee, awaiting applicant response
│     ↓                                 │
│ ACCEPTED → (handoff email sent)       │ ← Applicant accepted, handed to node
│     or                                │
│ DECLINED_BY_APPLICANT                 │ ← Applicant declined
│     or                                │
│ EXPIRED (after 10 days)               │ ← No response, auto-declined
├───────────────────────────────────────┤
│ REJECTED                              │ ← Rejected by committee (low score)
└───────────────────────────────────────┘
```

**Final statuses:**
- `ACCEPTED` - Approved, applicant accepted, handoff complete
- `DECLINED_BY_APPLICANT` - Approved, but applicant declined
- `EXPIRED` - Approved, but applicant didn't respond in 10 days
- `REJECTED` - Not approved by evaluation committee
- `FEASIBILITY_REJECTED` - Not feasible per node review

---

## What We Remove

From the original design, remove:

1. ~~Scheduled start/end dates on AccessGrant~~
2. ~~Node scheduling interface~~
3. ~~Time slot allocation logic~~
4. ~~"Time released" → waiting list promotion~~
5. ~~Actual hours used tracking~~
6. ~~Completion recording by node~~
7. ~~IN_PROGRESS and COMPLETED statuses~~

---

## Updated Phase 8: Completion Tracking (Simplified)

**Original Phase 8 was about tracking execution. With the simplified model, we remove most of this.**

If you want *any* completion tracking for reporting purposes, it could be a simple optional flag:

| Step | Action | User | Expected Result |
|------|--------|------|-----------------|
| 8.1 | (Optional) Mark access as completed | `coordinator` or `node` | Simple checkbox/flag for reporting |

But this is optional - the ministry report can simply count `ACCEPTED` applications as "access granted" without tracking completion.

---

## Updated Phase 9: Publication Follow-up (Unchanged)

Publication tracking remains the same - it's still valuable to know if ReDIB access resulted in publications. The follow-up emails go to applicants of `ACCEPTED` applications.

---

## Summary: What the Portal Actually Tracks

| Data Point | Tracked? | Notes |
|------------|----------|-------|
| Application submitted | ✓ | Full application data |
| Feasibility review | ✓ | Per-node feasible/not feasible |
| Evaluation scores | ✓ | Committee scores and average |
| Resolution decision | ✓ | Approved/rejected |
| Applicant acceptance | ✓ | Accepted/declined/expired |
| Handoff email sent | ✓ | Timestamp |
| Hours requested | ✓ | From application, for reporting |
| Scheduled dates | ✗ | Node's responsibility |
| Actual hours used | ✗ | Node's responsibility |
| Work completion | ✗ | Node's responsibility |
| Publications reported | ✓ | Applicant self-reports |

This keeps the portal focused on the evaluation workflow and handoff, leaving operational scheduling to the nodes.
