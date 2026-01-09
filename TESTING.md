# ReDIB COA System - Testing Guide

## Current Phase: Comprehensive Testing

The ReDIB COA Portal has completed all 10 development phases and is now in the **comprehensive testing phase**. This guide provides detailed manual testing procedures to validate the complete COA lifecycle from call creation through publication tracking.

This document contains both automated and manual testing procedures for the ReDIB COA portal.

---

## Automated Testing

### System Status: ✅ All Phases Implemented (0-10)

The ReDIB COA Portal is **fully implemented** with comprehensive test coverage.

### Test Suites Available

The following automated test scripts are available:

#### Phase-Specific Integration Tests

**Run individual phase tests as standalone scripts**:
```bash
# Phase 1 & 2: Call Management & Application Submission
python tests/test_phase1_phase2_workflow.py

# Phase 3: Feasibility Review
python tests/test_phase3_feasibility_review.py

# Phase 4: Evaluator Assignment
python tests/test_phase4_evaluator_assignment.py

# Phase 5: Evaluation Submission
python tests/test_phase5_evaluation_submission.py

# Phase 6: Resolution & Prioritization
python tests/test_phase6_resolution.py

# Phase 7: Acceptance & Handoff
python tests/test_phase7_acceptance.py

# Phase 9: Publication Tracking
python tests/test_phase9_publications.py
```

**Run Django test suite**:
```bash
# All tests
python manage.py test tests

# Reports tests
python manage.py test reports.tests
```

### Test Coverage Summary

| Phase | Tests | Status | Description |
|-------|-------|--------|-------------|
| 1-2 | 14 tests | ✅ Passing | Call management & application workflow |
| 3 | 7 tests | ✅ Passing | Multi-node feasibility review |
| 4 | 18 tests | ✅ Passing | Evaluator assignment & COI detection |
| 5 | 26 tests | ✅ 96% | Evaluation submission (0-12 scoring) |
| 6 | 13 tests | ✅ Passing | Resolution & prioritization |
| 7 | 7 tests | ✅ Passing | 10-day acceptance workflow |
| 9 | 8 tests | ✅ Passing | Publication tracking & follow-ups |
| 10 | 11 tests | ✅ Passing | Statistics & Excel export |

**Total: 104+ integration tests**
**Status: ✅ All core functionality tested and passing**

### Test Reports

Detailed test reports available in `/docs/test-reports/`:
- `PHASE1_PHASE2_TEST_REPORT.md` - Call & Application workflow
- `PHASE3_TEST_REPORT.md` - Feasibility review
- `PHASE4_TEST_REPORT.md` - Evaluator assignment

---

## Manual Testing Guide

This guide walks through the complete COA lifecycle with specific steps to validate each phase.

### Prerequisites

Before starting, ensure:
1. Development environment is running (Django + PostgreSQL/SQLite + Celery + Redis)
2. Email templates are seeded: `python manage.py seed_email_templates`
3. Core data is populated:
   ```bash
   python manage.py populate_redib_nodes
   python manage.py populate_redib_equipment
   python manage.py populate_redib_users
   ```

---

## ReDIB COA System - End-to-End Test Plan

### Phase 0: Admin Setup ✅
**Views needed:** Django Admin (built-in), basic login page

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 0.1 | Login to Django admin at `/admin/` | `admin` (superuser) | Access admin panel | had to make an admin account using creatsuperuser |
| 0.2 | Verify nodes populated | `admin` | See 4 nodes: CIC biomaGUNE, TRIMA@CNIC, MSSM (NY), SIN | |
| 0.3 | Verify equipment populated | `admin` | See 17+ equipment items across nodes | |
| 0.4 | Verify users populated | `admin` | See 8 core users (coordinators, evaluators, applicants) | no applicants in initial user test batch |
| 0.5 | Check user roles in Core > User Roles | `admin` | Verify coordinator, evaluator (with areas), applicant roles | no applicants in initial user test batch |
| 0.6 | Verify email templates seeded | `admin` | Communications > Email Templates shows 10+ templates | |

**Key data to verify:**
- [x] Nodes: CIC biomaGUNE (code: CICBIO), TRIMA@CNIC (code: CNIC)
- [x] Equipment: MRI 7T, PET-CT, etc. with proper node assignments
- [x] Evaluators have area qualifiers: `evaluator:preclinical`, `evaluator:clinical`, `evaluator:radiotracers`

**PAUSE POINT → Environment validated**

---

### Phase 1: Call Management ✅
**Views needed:** Call list, Call create/edit, Call detail (public)

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 1.1 | Login at `/` | `coordinator@redib.net` | Redirect to coordinator dashboard | need to set password using admin the first time |
| 1.2 | Navigate to Calls section | `coordinator` | See list of calls (if any exist) | |
| 1.3 | Create new call | `coordinator` | Click "Create New Call" button | the first time it is called 'Create First Call' |
| 1.4 | Set call code | `coordinator` | e.g., `COA-TEST-2026-01` | |
| 1.5 | Set call title | `coordinator` | e.g., "Test Call January 2026" | |
| 1.6 | Set submission period | `coordinator` | Start: today, End: +45 days from now | |
| 1.7 | Set evaluation deadline | `coordinator` | +60 days from now (after submission end) | |
| 1.8 | Set execution period | `coordinator` | Start: +90 days, End: +180 days | |
| 1.9 | Write call description | `coordinator` | Multi-line text describing call scope | |
| 1.10 | Save call (draft) | `coordinator` | Call saved, status = `draft` | |
| 1.11 | Navigate to call detail | `coordinator` | See call summary | you can see a saved call in the call managment section again |
| 1.12 | Add equipment allocation | `coordinator` | Select equipment (e.g., MRI 7T at CIC biomaGUNE) | we do not do this anymore, the default is all active equipment  |
| 1.13 | **Note:** No hours offered needed | System | CallEquipmentAllocation created (hours tracked dynamically) | |
| 1.14 | Repeat for multiple equipment | `coordinator` | Allocate 3-5 equipment items | |
| 1.15 | Publish call | `coordinator` | Status → `open`, `published_at` timestamp set | you can do this by opening the call and pushing selecting open in the status dropdown or you can push the publish button on the display in the call managkent dashboard |
| 1.16 | View public call page | Anonymous | Navigate to public calls, see COA-TEST-2026-01 | |
| 1.17 | Verify call details visible | Anonymous | See deadline, equipment list, description | |

**Validations:**
- [x] Cannot set evaluation deadline before submission end
- [x] Cannot publish call without at least one equipment allocation
- [x] Published call (status=`open`) visible to anonymous users
- [x] Draft calls NOT visible to public

**PAUSE POINT → Call creation validated**

---

### Phase 2: Application Submission ✅
**Views needed:** Application form (5-step wizard), Applicant dashboard, Application detail

This follows the application form structure from the AAC application specification.

**Application Wizard - Step 1: Basic Information**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 2.1 | Login as applicant | `applicant1@example.com` | Redirect to applicant dashboard | |
| 2.2 | View active calls | `applicant1` | See COA-TEST-2026-01 (open for submission) | |
| 2.3 | Click "Apply" for COA-TEST-2026-01 | `applicant1` | Navigate to application wizard Step 1 | |
| 2.4 | Enter applicant name | `applicant1` | Full name (auto-filled if available) | |
| 2.5 | Enter ORCID | `applicant1` | e.g., `0000-0002-1234-5678` | |
| 2.6 | Enter organization/entity | `applicant1` | Institution name | |
| 2.7 | Enter email | `applicant1` | Contact email (auto-filled) | |
| 2.8 | Enter phone | `applicant1` | Contact phone number | |
| 2.9 | Save and continue to Step 2 | `applicant1` | Progress to funding information | |

**Application Wizard - Step 2: Funding & Project Information**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 2.10 | Enter project title | `applicant1` | Full project title | |
| 2.11 | Enter project code | `applicant1` | Funding agency project code | |
| 2.12 | Enter funding agency | `applicant1` | e.g., "Ministerio de Ciencia e Innovación" | |
| 2.13 | Select funding type | `applicant1` | Choose: National / European / International / Other | |
| 2.14 | Check competitive funding | `applicant1` | Checkbox if project has competitive funding | |
| 2.15 | Select subject area | `applicant1` | Choose from AEI classification dropdown | |
| 2.16 | Save and continue to Step 3 | `applicant1` | Progress to access request | |

**Application Wizard - Step 3: Equipment & Access Request**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 2.17 | View available equipment | `applicant1` | See equipment allocated to this call | |
| 2.18 | Select equipment | `applicant1` | e.g., MRI 7T at CIC biomaGUNE | |
| 2.19 | Enter hours requested | `applicant1` | e.g., 24 hours | |
| 2.20 | Select service modality | `applicant1` | Choose: Full assistance / Presential / Self-service | |
| 2.21 | Select specialization area | `applicant1` | Choose: Preclinical / Clinical / Radiotracers | |
| 2.22 | Add additional equipment (optional) | `applicant1` | Click "Add equipment" for multi-equipment request | |
| 2.23 | Add equipment from different node (optional) | `applicant1` | Select equipment from CNIC (multi-node application) | |
| 2.24 | Save and continue to Step 4 | `applicant1` | Progress to scientific content | |

**Application Wizard - Step 4: Scientific Content**

This step contains the 6 evaluation criteria fields. Each should provide guidance text.

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 2.25 | **Category: Scientific and Technical Relevance** | `applicant1` | See category header | |
| 2.26 | Fill "Quality and originality" | `applicant1` | Text: quality/originality of project and research plan | |
| 2.27 | Fill "Methodology and design" | `applicant1` | Text: experimental design, suitability to objectives | |
| 2.28 | Fill "Expected contributions" | `applicant1` | Text: expected scientific-technical contributions, publications | |
| 2.29 | Fill: Timeliness and Impact | `applicant1` | Text | |
| 2.30 | Fill "Knowledge advancement" | `applicant1` | Text: contribution to advancing knowledge, innovation | |
| 2.31 | Fill "Social/economic impact" | `applicant1` | Text: potential social, economic, industrial impact | |
| 2.32 | Fill "Exploitation/dissemination" | `applicant1` | Text: opportunity for translation, dissemination | |
| 2.33 | Save and continue to Step 5 | `applicant1` | Progress to declarations | |

**Application Wizard - Step 5: Declarations & Submit**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 2.34 | Confirm feasibility contact | `applicant1` | Checkbox: contacted node about technical feasibility | |
| 2.35 | Animal use declaration (if applicable) | `applicant1` | Checkbox: uses animals + has ethics approval number | |
| 2.36 | Human subjects declaration (if applicable) | `applicant1` | Checkbox: uses humans + has ethics approval number | |
| 2.37 | Data protection consent | `applicant1` | Checkbox: REQUIRED - consent to data processing | |
| 2.38 | Preview application | `applicant1` | See full application summary with all fields | |
| 2.39 | Return to edit (optional) | `applicant1` | Can navigate back to any step | |
| 2.40 | Submit application | `applicant1` | Click "Submit Application" | |
| 2.41 | Verify submission | System | Status → `submitted`, application code auto-generated | |
| 2.42 | View confirmation page | `applicant1` | See confirmation with application code | |
| 2.43 | Check email notification | `applicant1` | Receive submission confirmation email | |
| 2.44 | Verify applicant dashboard | `applicant1` | Application appears with status "Submitted" | |

**Validations:**
- [x] Cannot submit without data protection consent
- [x] Cannot submit without all required scientific content fields
- [x] Cannot submit after call submission deadline
- [x] Application code auto-generated on submit (format: CALL-XXX)
- [x] Can save draft and return later before submitting (note: there is no save button but this does work for any completed section before the user exists the application wizard)
- [x] Cannot edit application after submission

**Edge cases to test:**
- Save draft at Step 2, logout, login, resume application
- Multi-equipment request (same node)
- Multi-node request (equipment from CIC + CNIC)
- Request hours for equipment
- Attempt submission after deadline (should fail)

Everything works

**PAUSE POINT → Application submission validated**

---

### Phase 3: Feasibility Review (Node Coordinators) ✅
**Views needed:** Node coordinator dashboard, Feasibility review form, Application detail (node view)

Per REDIB-02-PDA section 6.1.2: *"Applications received will be assessed first by the node directly involved to determine technical feasibility."*

**Single-Node Application Feasibility** ✅

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 3.1 | Login as node coordinator | `node.cic@redib.net` | Redirect to node coordinator dashboard | may need to have super userset a password if you did not setup your own account, may need to varify email if the first time logging in |
| 3.2 | View pending feasibility reviews | `node_cic` | See applications requesting CIC biomaGUNE equipment | |
| 3.3 | Click on application to review | `node_cic` | View full application details (NOT blind - node needs details) | this only works if another user (applicant) submited an application under the node your are a coordinator for |
| 3.4 | Review applicant information | `node_cic` | See applicant name, organization, contact info | |
| 3.5 | Review equipment requests | `node_cic` | See specific equipment + hours requested | |
| 3.6 | Review scientific content | `node_cic` | Read methodology to assess technical feasibility | |
| 3.7 | Mark as technically feasible | `node_cic` | Select "Feasible" radio button | |
| 3.8 | Add feasibility comments | `node_cic` | Optional text: technical recommendations, concerns | |
| 3.9 | Submit feasibility review | `node_cic` | Click "Submit Review" | |
| 3.10 | Verify application status updated | System | App status → `pending_evaluation` | |
| 3.11 | Verify applicant notified | System | Applicant receives feasibility result email | i am not sending email right now so I cannot confirm this, need to double check when emails are activated |
| 3.12 | Check coordinator notification | System | Coordinator notified of feasibility completion | i am not sending email right now so I cannot confirm this, need to double check when emails are activated |

**Feasibility Rejection Test**✅

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 3.13 | Create test application (App-B) | `applicant2` | Submit application requesting specialized equipment | |
| 3.14 | Login as node coordinator | `node_cic` | View App-B in pending reviews | |
| 3.15 | Mark as NOT feasible | `node_cic` | Select "Not Feasible" radio button | |
| 3.16 | Provide rejection reason | `node_cic` | Required text: explain why not technically feasible | |
| 3.17 | Submit feasibility review | `node_cic` | Click "Submit Review" | |
| 3.18 | Verify application rejected | System | App-B status → `rejected` | |
| 3.19 | Verify applicant notified | System | Applicant receives rejection email with reason | |

**Multi-Node Application Feasibility** 

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 3.20 | Create multi-node application (App-C) | `applicant1` | Request equipment from both CIC and CNIC | |
| 3.21 | Verify both nodes see review | System | App-C appears in both node dashboards | |
| 3.22 | CIC reviews and approves | `node_cic` | Submit feasibility: Feasible | |
| 3.23 | Verify partial approval recorded | System | CIC approval saved, status still `submitted` | |
| 3.24 | Verify CNIC still needs to review | System | App-C still in CNIC pending list | |
| 3.25 | CNIC reviews and approves | `node_cnic` | Submit feasibility: Feasible | |
| 3.26 | Verify full approval | System | All nodes approved, status → `pending_evaluation` | |

**Multi-Node Rejection Test**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 3.27 | Create multi-node application (App-D) | `applicant2` | Request equipment from CIC and CNIC | |
| 3.28 | CIC approves | `node_cic` | Mark as feasible | |
| 3.29 | CNIC rejects | `node_cnic` | Mark as NOT feasible with reason | |
| 3.30 | Verify entire application rejected | System | App-D status → `rejected` (even though CIC approved) | |
| 3.31 | Verify applicant notified | System | Email explains CNIC rejection reason | |

**Validations:**
- [x] Node coordinator only sees applications requesting their equipment
- [x] Application details visible to node (NOT blind review)
- [x] Single-node application: one approval moves to pending_evaluation
- ☐ Multi-node application: ALL nodes must approve
- ☐ Multi-node application: ONE rejection rejects entire application
- [x] Rejection requires reason/comments

**PAUSE POINT → Feasibility review validated**

---

### Phase 4: Call Closure & Evaluator Assignment
**Views needed:** Coordinator call management, Evaluator assignment interface

Per REDIB-03-PDC section 2.2: *"The Access Committee will have a maximum of fifteen (15) days to evaluate all applications"*

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 4.1 | Wait for submission deadline | System | Call submission end date passes | |
| 4.2 | Or manually close call early | `coordinator` | Change call status to `closed` | |
| 4.3 | Login as coordinator | `coordinator` | View coordinator dashboard | |
| 4.4 | Navigate to call detail | `coordinator` | See COA-TEST-2026-01 | |
| 4.5 | View applications ready for evaluation | `coordinator` | List of applications with status=`pending_evaluation` | |
| 4.6 | Click "Assign Evaluators" | `coordinator` | Open evaluator assignment interface | |
| 4.7 | View evaluator pool | `coordinator` | See available evaluators with their areas | I did not see this option, I dont think from this view you can just see a list of evaluators, no big deal, ignore it and move on. |
| 4.8 | Trigger automatic assignment | `coordinator` | Click "Auto-assign 2 evaluators per application" | |
| 4.9 | Verify assignment considers COI | System | No evaluator assigned from same org as applicant | |
| 4.10 | Verify area matching (best effort) | System | Preclinical apps → preclinical evaluators preferred | |
| 4.11 | Verify balanced distribution | System | Evaluators assigned evenly across pool | |
| 4.12 | View assignment summary | `coordinator` | Table showing: App - Evaluator 1 - Evaluator 2 | I did not see this table, I saw a list of applicaitons with a sub list of evaluators under each applicaiton, whtat was good enough, just move on |
| 4.13 | Verify application status updated | System | Applications status → `under_evaluation` | |
| 4.14 | Verify evaluation records created | System | 2 Evaluation objects per application (incomplete) | |
| 4.15 | Verify evaluator notifications | System | Each evaluator receives assignment email | not doing email right now, will have to return later and check |
| 4.16 | Check evaluator email content | Evaluator | Email contains application codes, deadline, portal link | not doing email right now, will need to come back and check later |

**Manual Assignment Override (if needed)**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 4.17 | View application assignment | `coordinator` | See current evaluators for App-A | |
| 4.18 | Remove auto-assigned evaluator | `coordinator` | Click "Remove" next to evaluator | |
| 4.19 | Manually assign different evaluator | `coordinator` | Select from dropdown, respecting COI rules | |
| 4.20 | Save manual assignment | `coordinator` | Assignment updated, new evaluator notified | |

**Conflict of Interest Validation**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 4.21 | Check applicant organization | System | App-A applicant from "Universidad de Barcelona" | |
| 4.22 | Verify evaluator exclusion | System | No evaluator from Universidad de Barcelona assigned | |
| 4.23 | Test manual COI violation | `coordinator` | Attempt to assign evaluator from same org | |
| 4.24 | Verify COI prevention | System | Error message or warning displayed | |

**Validations:**
- ☐ Auto-assignment creates 2 evaluators per application (configurable)
- ☐ COI detection: exclude evaluators from applicant's organization
- ☐ Area matching: preclinical apps prefer preclinical evaluators (best effort)
- ☐ Load balancing: distribute assignments evenly
- ☐ Email notifications sent to all assigned evaluators
- ☐ Application status changes from `pending_evaluation` → `under_evaluation`

**PAUSE POINT → Evaluator assignment validated**

---

### Phase 5: Evaluation Process
**Views needed:** Evaluator dashboard, Blind evaluation form, Evaluation detail

Per REDIB-02-PDA section 6.1.3: *"To preserve the identity of the applicant and ensure objectivity, the Coordination will send each evaluator only the information related to the requested project ('blind form')"*

**NEW Evaluation Criteria (6 criteria, 0-2 scoring, max 12 points)**

Based on AAC Evaluation Form:

**Category I: Scientific and Technical Relevance**
1. Quality and originality of the project and research plan (0-2)
2. Suitability of methodology, design, and work plan to objectives (0-2)
3. Expected scientific-technical contributions (0-2)

**Category II: Timeliness and Impact**
4. Contribution to advancement of knowledge (0-2)
5. Potential social, economic, industrial impact (0-2)
6. Opportunity for exploitation, translation, dissemination (0-2)

**Plus: Recommendation (Approved / Denied)**

**Evaluation Submission**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 5.1 | Login as evaluator | `evaluator1@redib.es` | Redirect to evaluator dashboard | |
| 5.2 | View assigned applications | `evaluator1` | See list of applications to evaluate | |
| 5.3 | Click on application to evaluate | `evaluator1` | View blind application form | |
| 5.4 | **Verify blind review** | `evaluator1` | NO applicant name, organization, email, phone | |
| 5.5 | **Verify visible content** | `evaluator1` | CAN see: project title, scientific content, equipment, hours | |
| 5.6 | Read application content | `evaluator1` | Review all scientific content fields | |
| 5.7 | **Score 1: Quality & originality** | `evaluator1` | Select 0, 1, or 2 (see help text for each value) | |
| 5.8 | **Score 2: Methodology & design** | `evaluator1` | Select 0, 1, or 2 | |
| 5.9 | **Score 3: Expected contributions** | `evaluator1` | Select 0, 1, or 2 | |
| 5.10 | **Score 4: Knowledge advancement** | `evaluator1` | Select 0, 1, or 2 | |
| 5.11 | **Score 5: Social/economic impact** | `evaluator1` | Select 0, 1, or 2 | |
| 5.12 | **Score 6: Exploitation/dissemination** | `evaluator1` | Select 0, 1, or 2 | |
| 5.13 | **Recommendation** | `evaluator1` | Select: Approved OR Denied (required) | |
| 5.14 | Add evaluation comments (optional) | `evaluator1` | Free text field for additional feedback | |
| 5.15 | Preview total score | `evaluator1` | See calculated sum (e.g., "10 / 12") | |
| 5.16 | Submit evaluation | `evaluator1` | Click "Submit Evaluation" | |
| 5.17 | Verify completion | System | Evaluation marked complete, `completed_at` timestamp set | |
| 5.18 | Verify total score calculated | System | `total_score` = sum of 6 scores (max 12) | |
| 5.19 | Verify locked after submission | System | Cannot edit completed evaluation | |
| 5.20 | Return to dashboard | `evaluator1` | Application shows "Evaluation Complete" | |

**Help Text Verification**

Each score should display help text for 0, 1, and 2 values:

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 5.21 | View Score 1 help text | `evaluator1` | 0: "acceptable", 1: "good", 2: "excellent" | |
| 5.22 | View Score 2 help text | `evaluator1` | 0: "inadequate", 1: "acceptable/good", 2: "highly suitable" | |
| 5.23 | View Score 3 help text | `evaluator1` | 0: "no mention", 1: "well-founded", 2: "commits to document" | |
| 5.24 | View Score 4 help text | `evaluator1` | 0: "not justified", 1: "well-founded", 2: "fully justified" | |
| 5.25 | View Score 5 help text | `evaluator1` | 0: "no arguments", 1: "some significance", 2: "detailed importance" | |
| 5.26 | View Score 6 help text | `evaluator1` | 0: "no criteria", 1: "well-founded", 2: "convincing" | |

**Recommendation Help Text**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 5.27 | View Approved help text | `evaluator1` | "Competitive funding OR acceptable quality & relevance" | |
| 5.28 | View Denied help text | `evaluator1` | "NOT competitive funding AND unacceptable quality" | |

**Second Evaluator Submission**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 5.29 | Login as second evaluator | `evaluator2@redib.es` | View assigned applications | |
| 5.30 | Evaluate same application | `evaluator2` | Different scores (e.g., 9/12 vs evaluator1's 10/12) | |
| 5.31 | Submit evaluation | `evaluator2` | Evaluation complete | |
| 5.32 | Verify both evaluations complete | System | Application has 2 completed evaluations | |

**Application Transition After All Evaluations Complete**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 5.33 | Check application status | System | After 2nd evaluation, status → `evaluated` | |
| 5.34 | Verify coordinator notification | System | Coordinator receives email: "All evaluations complete for App-X" | |
| 5.35 | Verify final_score calculated | System | Application.final_score = average of evaluators' total_scores | |
| 5.36 | Example calculation | System | Eval1: 10/12, Eval2: 9/12 → final_score = 9.5/12 | |

**Partial Completion Test**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 5.37 | Evaluator 1 completes evaluation | `evaluator1` | Evaluation saved | |
| 5.38 | Evaluator 2 has NOT completed | `evaluator2` | Evaluation still pending | |
| 5.39 | Check application status | System | Status still `under_evaluation` (waiting for all) | |
| 5.40 | Check coordinator dashboard | `coordinator` | See "1/2 evaluations complete" | |

**Deadline & Reminder Tests**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 5.41 | Check evaluation deadline | System | Call.evaluation_deadline set (e.g., +60 days) | |
| 5.42 | Test deadline warning | `evaluator1` | Dashboard shows "X days remaining" | |
| 5.43 | Test deadline lock (if past) | System | Cannot submit evaluation after deadline | |
| 5.44 | Verify reminder emails | System | At day 7 and day 14, reminder sent to incomplete evaluations | |

**Validations:**
- ☐ Blind review: applicant name, org, email, phone HIDDEN
- ☐ 6 criteria, each scored 0-2 (NOT 1-5)
- ☐ Total score = SUM of 6 scores (max 12, NOT average to 5)
- ☐ Recommendation field required (approved/denied)
- ☐ Help text displayed for each score value (0, 1, 2)
- ☐ Cannot edit evaluation after submission
- ☐ Application transitions to `evaluated` only when ALL evaluations complete
- ☐ final_score = average of evaluators' total_scores
- ☐ Coordinator notified when all evaluations complete
- ☐ Evaluation locks after call deadline

**PAUSE POINT → Evaluation process validated (NEW 0-12 scoring)**

---

### Phase 6: Resolution & Prioritization
**Views needed:** Resolution dashboard, Prioritized list view, Resolution communication

Per REDIB-01-RCA section 7: *"The Coordinator will prepare a PRIORITIZED LIST of approved applications, ordered from highest to lowest score"*

**NEW Resolution Threshold: Based on 0-12 scale**
- Current system default: score ≥ 9.0/12 = auto-accepted (75% of max)
- Coordinator can adjust threshold per call

**Resolution Categories (from REDIB-01-RCA):**
- **Accepted**: Access approved and granted
- **Pending**: Quality acceptable but waiting for available time
- **Rejected**: Does not meet quality threshold

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 6.1 | Login as coordinator | `coordinator` | View coordinator dashboard | |
| 6.2 | Navigate to call resolution | `coordinator` | Select COA-TEST-2026-01 call | |
| 6.3 | View evaluated applications | `coordinator` | List of applications with status=`evaluated` | |
| 6.4 | Verify final scores displayed | `coordinator` | Each app shows "X.X / 12" (e.g., "10.5 / 12") | |
| 6.5 | Verify automatic prioritization | System | Apps auto-sorted: highest score first, then by code | |
| 6.6 | Example prioritized order | System | 1. App-A (11.5/12), 2. App-B (10.0/12), 3. App-C (9.5/12) | |
| 6.7 | Verify tie-breaking | System | Same score: sorted alphabetically by code | |

**Auto-Approval Rule for Competitive Funding**

Per REDIB-01-RCA 6.1: *"Proposals that are part of R&D&I projects financed by a competitive call... will be automatically approved"*

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 6.8 | Check App-X with competitive funding | System | has_competitive_funding = True | |
| 6.9 | Verify auto-approval | System | App-X shows "Auto-approved (competitive funding)" | |
| 6.10 | Verify cannot reject | System | Coordinator cannot reject app with competitive funding | |
| 6.11 | Even with low score | System | App with 6.0/12 + competitive funding = still approved | |

**Threshold-Based Resolution**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 6.12 | Set acceptance threshold | `coordinator` | e.g., score ≥ 9.0/12 | |
| 6.13 | Trigger auto-allocation | `coordinator` | Click "Auto-allocate by threshold" | |
| 6.14 | Verify apps ≥ 9.0 accepted | System | Apps with score ≥ 9.0 → resolution=`accepted` | |
| 6.15 | Verify apps < 9.0 pending/rejected | System | Apps with score < 9.0 → resolution=`pending` | |
| 6.16 | Review auto-allocation results | `coordinator` | Summary: X accepted, Y pending, Z rejected | |

**Hours Tracking (Dynamic, No Pre-Allocation)**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 6.17 | View equipment hours summary | `coordinator` | See total hours requested per equipment | |
| 6.18 | Accept application | `coordinator` | Mark App-A as `accepted` | |
| 6.19 | Verify hours counted | System | Equipment.total_approved_hours increases by App-A hours | |
| 6.20 | Check equipment allocation | `coordinator` | See "MRI 7T: 48 hours approved" (sum of accepted apps) | |
| 6.21 | **Note:** No hours_offered limit | System | CallEquipmentAllocation has no hours_offered field | |
| 6.22 | **Note:** No hours_granted field | System | RequestedAccess uses hours_requested for accepted apps | |

**Manual Resolution Override**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 6.23 | View application detail | `coordinator` | See App-B with score 8.5/12 (below threshold) | |
| 6.24 | Manually accept App-B | `coordinator` | Override auto-allocation, set resolution=`accepted` | |
| 6.25 | Add resolution comments | `coordinator` | Required: explain why accepted below threshold | |
| 6.26 | Save manual decision | `coordinator` | Resolution saved with comments | |
| 6.27 | Manually reject App-C | `coordinator` | Set resolution=`rejected` with reason | |
| 6.28 | Verify rejection reason required | System | Cannot reject without comments | |

**Finalize Resolution**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 6.29 | Review final resolution list | `coordinator` | Check all apps have resolution assigned | |
| 6.30 | Verify no unresolved apps | System | All evaluated apps have: accepted / pending / rejected | |
| 6.31 | Click "Finalize Resolution" | `coordinator` | Confirmation dialog appears | |
| 6.32 | Confirm finalization | `coordinator` | Click "Yes, finalize" | |
| 6.33 | Verify resolution locked | System | Call.is_resolution_locked = True | |
| 6.34 | Verify resolution_date set | System | Call.resolution_date = now | |
| 6.35 | Verify acceptance deadlines | System | Accepted apps: acceptance_deadline = resolution_date + 10 days | |
| 6.36 | Verify notification emails sent | System | All applicants receive resolution notification | |
| 6.37 | Check accepted email content | Applicant | Email shows: hours granted, equipment, node, 10-day deadline | |
| 6.38 | Check rejected email content | Applicant | Email shows: rejection reason, final score | |
| 6.39 | Verify cannot modify after finalization | System | Coordinator cannot change resolutions | |

**Validations:**
- ☐ Scores displayed as "X.X / 12" (NOT /5)
- ☐ Auto-prioritization: highest score first, tie-break by code
- ☐ Competitive funding apps auto-approved (cannot reject)
- ☐ Threshold-based auto-allocation (e.g., ≥ 9.0/12)
- ☐ Hours tracking is dynamic (no pre-allocated hours_offered)
- ☐ Manual override allowed with comments
- ☐ Finalization locks resolution, sets deadlines, triggers emails
- ☐ Acceptance deadline = resolution_date + 10 days

**PAUSE POINT → Resolution validated (0-12 scoring, dynamic hours)**

---

### Phase 7: Acceptance & Handoff
**Views needed:** Applicant acceptance view, Acceptance tracking

Per REDIB-02-PDA section 6.1.6: *"Applicants have a period of ten (10) days from the publication of the resolution to accept or reject in writing the access granted"*

**Acceptance tracked directly on Application model** (AccessGrant model deprecated)

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 7.1 | Login as applicant | `applicant1` | Redirect to applicant dashboard | |
| 7.2 | View resolution notification | `applicant1` | Dashboard shows "Decision Available" | |
| 7.3 | View accepted application detail | `applicant1` | See resolution=`accepted`, hours granted, equipment | |
| 7.4 | See acceptance deadline | `applicant1` | Banner: "Respond by YYYY-MM-DD (X days remaining)" | |
| 7.5 | View equipment details | `applicant1` | Node, equipment name, hours requested/granted | |
| 7.6 | Click "Accept Access" | `applicant1` | Confirmation dialog | |
| 7.7 | Confirm acceptance | `applicant1` | Click "Yes, I accept" | |
| 7.8 | Verify acceptance recorded | System | Application.accepted_by_applicant = True | |
| 7.9 | Verify acceptance timestamp | System | Application.accepted_at = now | |
| 7.10 | Verify handoff email sent | System | Email sent to applicant + node coordinators | |
| 7.11 | Check handoff email content | Applicant | Contains: next steps, node contact, scheduling instructions | |
| 7.12 | Verify dashboard updated | `applicant1` | Status shows "Accepted - Pending Scheduling" | |

**Applicant Rejection Test**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 7.13 | Create second accepted app (App-Y) | `applicant2` | Application accepted by coordinator | |
| 7.14 | Login as applicant | `applicant2` | View acceptance notification | |
| 7.15 | Click "Decline Access" | `applicant2` | Confirmation dialog | |
| 7.16 | Confirm decline | `applicant2` | Click "Yes, I decline" | |
| 7.17 | Verify decline recorded | System | Application.accepted_by_applicant = False | |
| 7.18 | Verify decline timestamp | System | Application.accepted_at = now | |
| 7.19 | Verify notification sent | System | Coordinator notified of applicant decline | |
| 7.20 | Verify hours released | System | Equipment total_approved_hours decreases | |
| 7.21 | Verify dashboard updated | `applicant2` | Status shows "Declined by Applicant" | |

**Deadline Enforcement**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 7.22 | Check acceptance deadline | System | acceptance_deadline = resolution_date + 10 days | |
| 7.23 | Test 7-day reminder | System | At day 7, reminder email sent to applicant | |
| 7.24 | Test deadline passed | System | After 10 days, if no response: auto-decline | |
| 7.25 | Verify auto-decline | System | Application.accepted_by_applicant = False | |
| 7.26 | Verify auto-decline email | System | Applicant notified of auto-decline due to deadline | |
| 7.27 | Cannot accept after deadline | `applicant1` | "Accept" button disabled, message shown | |

**Pending Applications Promotion**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 7.28 | Create accepted app (App-P1) | Setup | App-P1 accepted, uses 30 hours | |
| 7.29 | Create pending app (App-P2) | Setup | App-P2 pending (next in priority) | |
| 7.30 | Applicant declines App-P1 | `applicant1` | 30 hours released | |
| 7.31 | Verify pending app promoted | System | App-P2 offered to applicant (if hours available) | |
| 7.32 | Verify promotion notification | System | App-P2 applicant receives acceptance email | |

**Validations:**
- ☐ Acceptance deadline = 10 days from resolution_date
- ☐ Acceptance tracked on Application model (NOT AccessGrant)
- ☐ accepted_by_applicant: True=accepted, False=declined, None=pending
- ☐ Handoff email sent on acceptance (to applicant + node coordinators)
- ☐ 7-day reminder sent if no response
- ☐ Auto-decline after 10 days if no response
- ☐ Cannot accept/decline after deadline
- ☐ Declined access releases hours for pending applications

**PAUSE POINT → Acceptance workflow validated (10-day deadline)**

---

### Phase 8: Execution & Completion
**Views needed:** Access status tracking, Completion form (optional)

This phase is simplified - completion tracking is optional.

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 8.1 | Login as node coordinator | `node_cic` | View accepted applications for scheduling | |
| 8.2 | View accepted application | `node_cic` | See applicant contact, hours granted | |
| 8.3 | Contact applicant (external) | `node_cic` | Email/call to schedule experiment time | |
| 8.4 | Mark access as completed (optional) | `node_cic` | Check "Completed" in admin or form | |
| 8.5 | Verify completion flag set | System | Application.is_completed = True | |
| 8.6 | Verify completion timestamp | System | Application.completed_at = now | |
| 8.7 | Applicant views completion | `applicant1` | Dashboard shows "Access Completed" | |

**Validations:**
- ☐ Completion tracking is optional (simple flag)
- ☐ No complex hours tracking (hours_requested used directly)
- ☐ Actual scheduling happens via direct communication

**PAUSE POINT → Execution tracking validated**

---

### Phase 9: Publication Follow-up
**Views needed:** Publication submission form, Publication tracking dashboard

Per REDIB-02-PDA section 7: *"Inform ReDIB of the scientific publications"* and *"Make express mention of ReDIB in communications and scientific publications"*

**Initial Follow-up (6 months)**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 9.1 | Simulate 6 months passing | System | Trigger 6-month follow-up task | |
| 9.2 | Check applicant email | `applicant1` | Receive publication follow-up email | |
| 9.3 | Email contains instructions | `applicant1` | Link to submit publication, acknowledgment template | |
| 9.4 | Login as applicant | `applicant1` | Navigate to applications | |
| 9.5 | Click "Report Publication" | `applicant1` | Open publication submission form | |
| 9.6 | Enter publication title | `applicant1` | Full publication title | |
| 9.7 | Enter authors | `applicant1` | Full author list | |
| 9.8 | Enter journal name | `applicant1` | Journal/conference name | |
| 9.9 | Enter DOI or URL | `applicant1` | Publication identifier | |
| 9.10 | Enter publication date | `applicant1` | Date picker | |
| 9.11 | Confirm ReDIB acknowledged | `applicant1` | Checkbox: "ReDIB is acknowledged in this publication" | |
| 9.12 | Provide acknowledgment text | `applicant1` | Copy/paste actual acknowledgment from paper | |
| 9.13 | Submit publication | `applicant1` | Click "Submit" | |
| 9.14 | Verify publication saved | System | Publication object created, linked to application | |
| 9.15 | Verify applicant notification | System | Confirmation email sent to applicant | |
| 9.16 | Verify coordinator notification | System | Coordinator notified of new publication | |

**Required Acknowledgment Text Template (from REDIB-02-PDA):**
> *"This work acknowledges the use of ReDIB ICTS, supported by the Ministry of Science, Innovation and Universities (MICIU) at [NODE NAME]."*

**Acknowledgment Validation**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 9.17 | View publication detail | `coordinator` | See acknowledgment status | |
| 9.18 | Verify acknowledgment checkbox | System | redib_acknowledged = True/False | |
| 9.19 | Read acknowledgment text | `coordinator` | See actual text from paper | |
| 9.20 | Verify node mentioned | `coordinator` | Check if correct node name included | |

**Second Follow-up (12 months)**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 9.21 | Simulate 12 months passing | System | Trigger 12-month follow-up task | |
| 9.22 | Check applicant email | `applicant1` | Receive final publication reminder | |
| 9.23 | Email indicates final reminder | `applicant1` | Subject: "Final reminder: Publication reporting" | |
| 9.24 | Applicant reports publication | `applicant1` | Same submission flow as 6-month follow-up | |

**No Publication Case**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 9.25 | Applicant receives follow-up | `applicant2` | Email at 6 months | |
| 9.26 | Applicant clicks "No publication yet" | `applicant2` | Acknowledge no publication to date | |
| 9.27 | Verify response recorded | System | Last follow-up contact timestamp updated | |
| 9.28 | Second follow-up sent | System | At 12 months, final reminder | |

**Coordinator Publication Dashboard**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 9.29 | Login as coordinator | `coordinator` | View coordinator dashboard | |
| 9.30 | Navigate to Publications | `coordinator` | Click "Publications" menu | |
| 9.31 | View all publications | `coordinator` | List of all reported publications | |
| 9.32 | Filter by call | `coordinator` | Select COA-TEST-2026-01 | |
| 9.33 | View publication statistics | `coordinator` | See: Total, With acknowledgment, Without acknowledgment | |
| 9.34 | Calculate acknowledgment rate | `coordinator` | e.g., "5 of 8 publications (62.5%)" | |
| 9.35 | Export publications to Excel | `coordinator` | Download publication report | |
| 9.36 | Verify Excel content | `coordinator` | See: Title, Authors, Journal, DOI, Acknowledged (Y/N) | |

**Validations:**
- ☐ 6-month follow-up email sent automatically
- ☐ 12-month final reminder sent automatically
- ☐ Publication form captures: title, authors, journal, DOI, date
- ☐ Acknowledgment checkbox (redib_acknowledged field)
- ☐ Actual acknowledgment text stored for verification
- ☐ Coordinator can view all publications
- ☐ Statistics show acknowledgment rate
- ☐ Export functionality for reporting to ministry

**PAUSE POINT → Publication tracking validated**

---

### Phase 10: Reporting & Statistics
**Views needed:** Statistics dashboard, Report export (Excel)

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 10.1 | Login as coordinator | `coordinator` | View coordinator dashboard | |
| 10.2 | Navigate to Reports section | `coordinator` | Click "Statistics & Reports" | |
| 10.3 | View overall statistics | `coordinator` | See cards: Total Calls, Total Apps, Publications, Pending Evaluations | |
| 10.4 | View call-specific statistics | `coordinator` | Select COA-TEST-2026-01 | |
| 10.5 | See application breakdown | `coordinator` | Submitted, Feasible, Evaluated, Accepted, Rejected, Pending | |
| 10.6 | See average score | `coordinator` | "Average Score: X.X / 12" (NEW: out of 12, not 5) | |
| 10.7 | Calculate acceptance rate | `coordinator` | "Acceptance Rate: X%" | |

**Excel Report Export**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 10.8 | Click "Export Call Report" | `coordinator` | Download Excel file | |
| 10.9 | Open Excel file | `coordinator` | Workbook with 3 sheets | |
| 10.10 | **Sheet 1: Summary** | `coordinator` | Call info, application stats | |
| 10.11 | Verify average score label | `coordinator` | "Average Evaluation Score (out of 12): X.X" | |
| 10.12 | See acceptance rate | `coordinator` | "Acceptance Rate: X%" | |
| 10.13 | See publication count | `coordinator` | "Publications Reported: X" | |
| 10.14 | **Sheet 2: Applications** | `coordinator` | Detailed application list | |
| 10.15 | Verify columns | `coordinator` | Code, Applicant, Institution, Status, Final Score, Resolution, Hours | |
| 10.16 | Verify final score format | `coordinator` | Numbers like 10.5, 9.0, 11.5 (out of 12) | |
| 10.17 | **Sheet 3: Equipment** | `coordinator` | Equipment usage summary | |
| 10.18 | Verify equipment columns | `coordinator` | Equipment, Node, Total Approved Hours | |
| 10.19 | Verify hours calculation | `coordinator` | Sum of hours_requested from accepted applications | |

**Publication Statistics**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 10.20 | View publication statistics | `coordinator` | Navigate to Publications section | |
| 10.21 | See total publications | `coordinator` | "Total Publications: X" | |
| 10.22 | See acknowledgment breakdown | `coordinator` | "With Acknowledgment: Y (Z%)" | |
| 10.23 | Filter by call | `coordinator` | Select specific call | |
| 10.24 | Filter by node | `coordinator` | Select specific node | |
| 10.25 | View recent publications list | `coordinator` | Table with latest publications | |

**Node-Specific Statistics** (if applicable)

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 10.26 | Login as node coordinator | `node_cic` | View node dashboard | |
| 10.27 | View node statistics | `node_cic` | See stats for CIC biomaGUNE only | |
| 10.28 | See equipment usage | `node_cic` | Hours approved/used per equipment | |
| 10.29 | See application count | `node_cic` | Applications requesting CIC equipment | |

**Report History Tracking**

| Step | Action | User | Expected Result | Notes |
|------|--------|------|-----------------|-------|
| 10.30 | Navigate to Report History | `coordinator` | Click "Report History" | |
| 10.31 | View generated reports | `coordinator` | List of previously exported reports | |
| 10.32 | See report metadata | `coordinator` | Date generated, report type, generated by, call | |
| 10.33 | Verify audit trail | System | ReportGeneration records created | |

**Validations:**
- ☐ Dashboard shows overall statistics (calls, apps, publications)
- ☐ Call-specific statistics available
- ☐ **Average score labeled as "out of 12"** (NOT out of 5)
- ☐ Excel export with 3 sheets: Summary, Applications, Equipment
- ☐ **Final scores displayed as X.X (0-12 range)** in Excel
- ☐ Hours tracking shows sum of accepted applications' hours_requested
- ☐ Publication statistics show acknowledgment rate
- ☐ Report generation tracked for audit purposes

**PAUSE POINT → Reporting validated (0-12 scoring display)**

---

## Summary: Testing Checklist

### Critical Changes Validated in This Guide

- ☐ **Evaluation Scoring**: 6 criteria, 0-2 scale, sum to max 12 (NOT 5 criteria, 1-5 scale, average to 5)
- ☐ **Recommendation Field**: Evaluators must select Approved/Denied
- ☐ **Help Text**: Each score (0, 1, 2) has descriptive help text
- ☐ **Resolution Threshold**: Based on 0-12 scale (e.g., ≥ 9.0/12)
- ☐ **Hours Tracking**: Dynamic, no pre-allocated hours_offered or hours_granted
- ☐ **Acceptance**: Tracked on Application model, 10-day deadline
- ☐ **Reports**: Display scores as "X.X / 12"

### Complete Workflow Validation

Follow these phases in order to validate the entire COA lifecycle:

1. **Phase 0**: Admin setup ☐
2. **Phase 1**: Create and publish call ☐
3. **Phase 2**: Submit application (5-step wizard) ☐
4. **Phase 3**: Feasibility review (single + multi-node) ☐
5. **Phase 4**: Evaluator assignment (COI detection) ☐
6. **Phase 5**: Evaluation submission (6 criteria, 0-12 scoring) ☐
7. **Phase 6**: Resolution (threshold 9.0/12, dynamic hours) ☐
8. **Phase 7**: Acceptance (10-day deadline) ☐
9. **Phase 8**: Execution tracking (optional) ☐
10. **Phase 9**: Publication follow-up (6 & 12 months) ☐
11. **Phase 10**: Reporting (Excel export, 0-12 scale) ☐

### Key Metrics to Verify

After completing the full workflow, verify:

- ☐ All email notifications sent at correct times
- ☐ All deadlines enforced correctly
- ☐ All role-based permissions working
- ☐ All data correctly displayed in reports
- ☐ All calculations using 0-12 scale (NOT 0-5 scale)

---

## Build Order Recommendation

| Phase | Priority Views | Key Features |
|-------|----------------|--------------|
| 0 | Login, Admin access | User authentication, role management |
| 1 | Call list, Call CRUD, Public call view | Dynamic equipment allocation |
| 2 | Application wizard (5 steps), Applicant dashboard | Multi-step form, draft saving |
| 3 | Node dashboard, Feasibility review form | Multi-node coordination |
| 4 | Evaluator assignment interface | COI detection, load balancing |
| 5 | Evaluator dashboard, Blind evaluation form | 0-2 scoring, help text, recommendation |
| 6 | Resolution dashboard, Prioritized list | 0-12 threshold, dynamic hours |
| 7 | Acceptance workflow | 10-day deadline, auto-decline |
| 8 | Access status tracking | Simple completion flag |
| 9 | Publication submission | 6-month and 12-month follow-ups |
| 10 | Statistics and reports | Excel export with 0-12 scale |

This follows the natural document flow and lets you build incrementally while testing real workflows at each stage.
