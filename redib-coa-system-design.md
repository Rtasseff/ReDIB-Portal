# ReDIB Competitive Open Access (COA) Management System

## High-Level Design Document

**Version:** 1.0  
**Date:** December 2025  
**Prepared for:** CIC biomaGUNE / ReDIB ICTS Network

---

## 1. Executive Summary

This document outlines the architecture and implementation strategy for a web-based application to automate the Competitive Open Access (COA) process for the ReDIB distributed biomedical imaging network. The system will replace the current manual email-based workflow with an integrated platform handling application submission, node feasibility review, committee evaluation, automated communications, and reporting.

### Key Goals

- Automate the full COA lifecycle from call publication to access completion
- Provide role-based access for applicants, node coordinators, evaluators, and administrators
- Enable automated email communications with configurable templates and reminders
- Track application status and generate statistics for ministry reporting
- Build a flexible foundation for future enhancements (usage tracking, publication follow-up)

---

## 2. Current Process Analysis

### Workflow Summary (from documents)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. Call Publication → 2. Application Submission → 3. Node Review           │
│         ↓                      ↓                        ↓                   │
│  4. Committee Evaluation → 5. Scoring/Ranking → 6. Decision Communication   │
│         ↓                                                                   │
│  7. Acceptance Confirmation → 8. Experiment Execution → 9. Follow-up        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Current Pain Points

| Step | Current Method | Problem |
|------|----------------|---------|
| Call Publication | Manual website post | Manual, error-prone |
| Application Receipt | Email to info@redib.net | No tracking, manual filing |
| Node Assignment | Manual email to node directors | Delays, no visibility |
| Feasibility Review | Email response | Lost in inbox, no deadline tracking |
| Evaluator Assignment | Manual random selection | Time-consuming, tracking issues |
| Evaluation Collection | Email-based | Reminder burden, score aggregation manual |
| Results Communication | Manual emails | Repetitive, easy to miss applicants |

---

## 3. System Architecture

### 3.1 Technology Stack

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Django Templates + HTMX + Alpine.js                         │   │
│  │  (Simple, server-rendered, progressive enhancement)          │   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                         BACKEND                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Django 5.x                                                  │   │
│  │  ├── Django REST Framework (for potential API/mobile)       │   │
│  │  ├── Celery (background tasks, emails, reminders)           │   │
│  │  ├── django-allauth (authentication)                        │   │
│  │  └── django-simple-history (audit trail)                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                         DATA LAYER                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  PostgreSQL 15+                                              │   │
│  │  └── TimescaleDB extension (optional, for time-series stats)│   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                     SUPPORTING SERVICES                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐   │
│  │  Redis           │  │  Celery Beat     │  │  File Storage  │   │
│  │  (cache + queue) │  │  (scheduling)    │  │  (S3/local)    │   │
│  └──────────────────┘  └──────────────────┘  └────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Why This Stack?

| Choice | Rationale |
|--------|-----------|
| **Django** | Full-featured, mature, excellent admin, strong ORM, Python-native |
| **HTMX + Alpine.js** | Simple interactivity without SPA complexity, SEO-friendly |
| **PostgreSQL** | Robust, excellent JSON support, future extensibility |
| **Celery + Redis** | Proven async task handling for emails and scheduled jobs |
| **Django Templates** | Simple, maintainable, no separate frontend build process |

---

## 4. Data Model Design

### 4.1 Core Entities

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ENTITY RELATIONSHIPS                         │
│                                                                     │
│  Organization ──────┬──── Node ────────── Equipment                 │
│       │             │       │                  │                    │
│       │             │       │                  │                    │
│   User ─────────────┤       │           EquipmentHours              │
│   (roles)           │       │                  │                    │
│                     │       │                  │                    │
│              Call ──┴───────┴──── Application ─┴── RequestedAccess  │
│                │                      │                             │
│                │                      │                             │
│           Evaluation ─────────────────┤                             │
│                                       │                             │
│                                  AccessGrant                        │
│                                       │                             │
│                                  Publication                        │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Key Models (Django)

```python
# Simplified model definitions - actual implementation will be more detailed

class Organization(models.Model):
    """Parent organizations (ministries, universities, companies)"""
    name = models.CharField(max_length=255)
    country = models.CharField(max_length=100)
    organization_type = models.CharField(choices=ORG_TYPES)

class Node(models.Model):
    """ReDIB network nodes (4 nodes: CICbiomaGUNE, BioImaC, La Fe, CNIC)"""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    director = models.ForeignKey('User', on_delete=models.PROTECT)
    location = models.CharField(max_length=200)
    acknowledgment_text = models.TextField()  # For publication requirements

class Equipment(models.Model):
    """Essential infrastructure at each node"""
    node = models.ForeignKey(Node, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)  # e.g., "MRI 7T", "PET-CT"
    category = models.CharField(choices=EQUIPMENT_CATEGORIES)
    is_essential = models.BooleanField(default=True)  # ICTS essential facility
    description = models.TextField()
    
class User(AbstractUser):
    """Extended user with roles and affiliations"""
    organization = models.ForeignKey(Organization, null=True)
    orcid = models.CharField(max_length=20, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    
class UserRole(models.Model):
    """Role assignments (users can have multiple roles)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(choices=ROLES)  # applicant, node_coordinator, 
                                            # evaluator, admin, coordinator
    node = models.ForeignKey(Node, null=True)  # For node-specific roles
    area = models.CharField(choices=AREAS, blank=True)  # preclinical, clinical

class Call(models.Model):
    """COA Call periods"""
    code = models.CharField(max_length=20, unique=True)  # e.g., "COA-2025-01"
    title = models.CharField(max_length=200)
    status = models.CharField(choices=CALL_STATUSES)  # draft, open, closed, resolved
    submission_start = models.DateTimeField()
    submission_end = models.DateTimeField()
    evaluation_deadline = models.DateTimeField()
    execution_start = models.DateTimeField()
    execution_end = models.DateTimeField()
    description = models.TextField()
    published_at = models.DateTimeField(null=True)

class CallEquipmentAllocation(models.Model):
    """Hours offered per equipment per call"""
    call = models.ForeignKey(Call, on_delete=models.CASCADE)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    hours_offered = models.DecimalField(max_digits=6, decimal_places=1)
    
class Application(models.Model):
    """COA application submitted by researcher"""
    call = models.ForeignKey(Call, on_delete=models.PROTECT)
    applicant = models.ForeignKey(User, on_delete=models.PROTECT)
    code = models.CharField(max_length=30, unique=True)  # Auto-generated
    status = models.CharField(choices=APPLICATION_STATUSES)
    
    # Basic info
    brief_description = models.CharField(max_length=100)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    # Funding source
    project_title = models.CharField(max_length=300, blank=True)
    project_code = models.CharField(max_length=100, blank=True)
    funding_agency = models.CharField(max_length=200, blank=True)
    project_type = models.CharField(choices=PROJECT_TYPES)
    has_competitive_funding = models.BooleanField(default=False)
    
    # Subject area
    subject_area = models.CharField(choices=SUBJECT_AREAS)
    
    # Service modality
    service_modality = models.CharField(choices=SERVICE_MODALITIES)
    specialization_area = models.CharField(choices=SPECIALIZATION_AREAS)
    
    # Scientific content (text fields for evaluation)
    scientific_relevance = models.TextField()
    methodology_description = models.TextField()
    expected_contributions = models.TextField()
    impact_strengths = models.TextField()
    socioeconomic_significance = models.TextField()
    opportunity_criteria = models.TextField()
    
    # Declarations
    technical_feasibility_confirmed = models.BooleanField(default=False)
    uses_animals = models.BooleanField(default=False)
    has_animal_ethics = models.BooleanField(default=False)
    uses_humans = models.BooleanField(default=False)
    has_human_ethics = models.BooleanField(default=False)
    data_consent = models.BooleanField(default=False)
    
    # Resolution
    final_score = models.DecimalField(null=True)
    resolution = models.CharField(choices=RESOLUTIONS, blank=True)
    resolution_date = models.DateTimeField(null=True)

class RequestedAccess(models.Model):
    """Equipment access requests within an application"""
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT)
    hours_requested = models.DecimalField(max_digits=6, decimal_places=1)

class FeasibilityReview(models.Model):
    """Node technical feasibility assessment"""
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    node = models.ForeignKey(Node, on_delete=models.PROTECT)
    reviewer = models.ForeignKey(User, on_delete=models.PROTECT)
    is_feasible = models.BooleanField(null=True)
    comments = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True)

class Evaluation(models.Model):
    """Evaluator assessment of application"""
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    evaluator = models.ForeignKey(User, on_delete=models.PROTECT)
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    # Scoring (1-5 scale per criteria)
    score_relevance = models.IntegerField(null=True, validators=[1-5])
    score_methodology = models.IntegerField(null=True)
    score_contributions = models.IntegerField(null=True)
    score_impact = models.IntegerField(null=True)
    score_opportunity = models.IntegerField(null=True)
    
    total_score = models.DecimalField(null=True)  # Computed
    comments = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True)
    
class AccessGrant(models.Model):
    """Granted access after approval"""
    application = models.ForeignKey(Application, on_delete=models.PROTECT)
    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT)
    hours_granted = models.DecimalField(max_digits=6, decimal_places=1)
    scheduled_start = models.DateField(null=True)
    scheduled_end = models.DateField(null=True)
    accepted_by_user = models.BooleanField(null=True)
    accepted_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)
    actual_hours_used = models.DecimalField(null=True)

class Publication(models.Model):
    """Publications resulting from COA access"""
    access_grant = models.ForeignKey(AccessGrant, on_delete=models.CASCADE)
    title = models.CharField(max_length=500)
    doi = models.CharField(max_length=100, blank=True)
    journal = models.CharField(max_length=200, blank=True)
    publication_date = models.DateField(null=True)
    redib_acknowledged = models.BooleanField(default=False)
    reported_at = models.DateTimeField(auto_now_add=True)
```

---

## 5. User Roles and Permissions

### 5.1 Role Definitions

| Role | Description | Access Level |
|------|-------------|--------------|
| **Applicant** | External researchers submitting COA applications | Submit applications, view own applications, accept/reject grants |
| **Node Coordinator** | Staff at each ReDIB node (4 total) | Review feasibility, view node applications, manage node equipment |
| **Evaluator** | Access Committee members (10+ external experts) | View assigned applications (blind), submit evaluations |
| **Coordinator** | ReDIB network coordinator | Full access, assign evaluators, resolve calls, publish results |
| **Admin** | System administrator | User management, system configuration, all data access |

### 5.2 Permission Matrix

```
┌──────────────────────────┬───────┬───────┬───────┬───────┬───────┐
│ Action                   │ Appl. │ Node  │ Eval. │ Coord.│ Admin │
├──────────────────────────┼───────┼───────┼───────┼───────┼───────┤
│ Submit application       │   ✓   │       │       │       │   ✓   │
│ View own applications    │   ✓   │       │       │   ✓   │   ✓   │
│ Review feasibility       │       │   ✓   │       │   ✓   │   ✓   │
│ View assigned evals      │       │       │   ✓   │   ✓   │   ✓   │
│ Submit evaluation        │       │       │   ✓   │       │   ✓   │
│ Assign evaluators        │       │       │       │   ✓   │   ✓   │
│ Resolve calls            │       │       │       │   ✓   │   ✓   │
│ Manage calls             │       │       │       │   ✓   │   ✓   │
│ Manage users             │       │       │       │       │   ✓   │
│ View all statistics      │       │   ✓*  │       │   ✓   │   ✓   │
│ System configuration     │       │       │       │       │   ✓   │
└──────────────────────────┴───────┴───────┴───────┴───────┴───────┘
* Node-specific statistics only
```

---

## 6. Application Workflow Engine

### 6.1 Application State Machine

```
                                        ┌──────────────────┐
                                        │     DRAFT        │
                                        │ (incomplete app) │
                                        └────────┬─────────┘
                                                 │ submit
                                                 ▼
                                        ┌──────────────────┐
                                        │    SUBMITTED     │
                                        │ (awaiting review)│
                                        └────────┬─────────┘
                                                 │ auto-assign to node(s)
                                                 ▼
                                        ┌──────────────────┐
                           ┌───────────│ UNDER_FEASIBILITY│
                           │           │    _REVIEW       │
                           │           └────────┬─────────┘
                           │                    │
               not feasible│                    │ feasible
                           ▼                    ▼
                  ┌──────────────┐     ┌──────────────────┐
                  │   REJECTED   │     │ PENDING_EVALUATION│
                  │ (not viable) │     │ (awaiting call    │
                  └──────────────┘     │  closure)         │
                                       └────────┬─────────┘
                                                │ call closes + evaluators assigned
                                                ▼
                                       ┌──────────────────┐
                                       │ UNDER_EVALUATION │
                                       │ (being scored)   │
                                       └────────┬─────────┘
                                                │ all evaluations complete
                                                ▼
                                       ┌──────────────────┐
                                       │    EVALUATED     │
                                       │ (awaiting coord. │
                                       │  resolution)     │
                                       └────────┬─────────┘
                                                │ coordinator resolves
                       ┌────────────────────────┼────────────────────────┐
                       │                        │                        │
                       ▼                        ▼                        ▼
              ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
              │   ACCEPTED   │        │   PENDING    │        │   REJECTED   │
              │(with time)   │        │ (waiting list)│       │(low score)   │
              └──────┬───────┘        └──────┬───────┘        └──────────────┘
                     │                       │
                     │ user accepts          │ time becomes available
                     ▼                       │
              ┌──────────────┐               │
              │  SCHEDULED   │◄──────────────┘
              │(experiments  │
              │  planned)    │
              └──────┬───────┘
                     │ work begins
                     ▼
              ┌──────────────┐
              │ IN_PROGRESS  │
              │(work ongoing)│
              └──────┬───────┘
                     │ work complete
                     ▼
              ┌──────────────┐
              │  COMPLETED   │
              │(pending pubs)│
              └──────────────┘
```

### 6.2 Automated Triggers

| Event | System Action |
|-------|---------------|
| Application submitted | Assign to node(s) based on equipment selected, notify node coordinators |
| Feasibility approved | Change status to PENDING_EVALUATION |
| Call submission period closes | Auto-assign evaluators (random 2 per app), notify evaluators |
| Evaluation reminder (7 days before deadline) | Send reminder email to incomplete evaluations |
| All evaluations complete | Calculate average scores, notify coordinator |
| Coordinator resolves call | Notify all applicants of resolution, publish on website |
| User accepts grant | Notify relevant node, create AccessGrant record |
| 10 days without acceptance | Send reminder, then auto-decline |
| 6 months after completion | Send publication follow-up email |

---

## 7. Email System Design

### 7.1 Email Infrastructure

```
┌─────────────────────────────────────────────────────────────────────┐
│                         EMAIL FLOW                                  │
│                                                                     │
│  Django App ──► Celery Task ──► SMTP Server ──► Recipient          │
│      │              │                                               │
│      │              │                                               │
│      ▼              ▼                                               │
│  Template      Redis Queue                                          │
│  Selection     (background)                                         │
│                                                                     │
│  Features:                                                          │
│  • HTML + plain text templates                                      │
│  • Variable substitution                                            │
│  • Attachment support (PDFs)                                        │
│  • Send logging and tracking                                        │
│  • Bounce handling                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.2 Email Templates Required

| Template ID | Trigger | Recipients |
|-------------|---------|------------|
| `call_published` | Call published | All registered users (opt-in) |
| `application_received` | Submission complete | Applicant |
| `feasibility_request` | Application assigned | Node coordinator(s) |
| `feasibility_reminder` | 5 days without response | Node coordinator |
| `feasibility_rejected` | Node marks not feasible | Applicant |
| `evaluation_assigned` | Call closes | Evaluators |
| `evaluation_reminder` | 7 days before deadline | Evaluators with incomplete |
| `resolution_accepted` | COA accepted | Applicant |
| `resolution_pending` | COA accepted (waiting list) | Applicant |
| `resolution_rejected` | COA rejected | Applicant |
| `acceptance_reminder` | 7 days without response | Applicant |
| `access_scheduled` | Node schedules access | Applicant + node |
| `publication_followup` | 6/12 months after completion | Applicant |

### 7.3 Celery Beat Schedule (Periodic Tasks)

```python
CELERYBEAT_SCHEDULE = {
    'check-feasibility-reminders': {
        'task': 'core.tasks.send_feasibility_reminders',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
    },
    'check-evaluation-reminders': {
        'task': 'core.tasks.send_evaluation_reminders',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
    },
    'check-acceptance-deadlines': {
        'task': 'core.tasks.process_acceptance_deadlines',
        'schedule': crontab(hour=10, minute=0),  # Daily at 10 AM
    },
    'send-publication-followups': {
        'task': 'core.tasks.send_publication_followups',
        'schedule': crontab(hour=10, minute=0, day_of_week=1),  # Mondays
    },
}
```

---

## 8. Frontend Design

### 8.1 Design Philosophy

- **Server-rendered**: Django templates with HTMX for dynamic updates
- **Simple and functional**: No flashy UI, focus on usability
- **Responsive**: Works on desktop and tablet (admin tasks)
- **Accessible**: WCAG 2.1 compliance

### 8.2 Key Views/Pages

#### Public Area
- Home/landing page with current call info
- Call details and application form
- FAQ and documentation

#### Applicant Portal
- Dashboard: My applications, status overview
- Application form (multi-step wizard)
- Application detail with history
- Accept/reject grant

#### Node Coordinator Portal
- Dashboard: Pending feasibility reviews
- Feasibility review form
- Node statistics

#### Evaluator Portal
- Dashboard: Assigned applications
- Blind evaluation form (applicant info hidden)
- Evaluation history

#### Coordinator/Admin Portal
- Dashboard: Overview, alerts, statistics
- Call management (create, edit, publish)
- Evaluator assignment tool
- Resolution management
- User management
- Reports and exports

### 8.3 Example: Application Form Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│  Step 1: Basic Information                                           │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Call: [COA-2025-01 (January - February)]                       │ │
│  │ Brief description: [________________________________] (100 ch) │ │
│  │ Name: [________________]  ORCID: [________________]            │ │
│  │ Organization: [____________________]                           │ │
│  │ Email: [____________________]  Phone: [____________]           │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                         [Save Draft] [Next →]        │
├──────────────────────────────────────────────────────────────────────┤
│  Step 2: Funding Source                                              │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Project Title: [________________________________]              │ │
│  │ Project Code: [________________]                               │ │
│  │ Funding Agency: [________________]                             │ │
│  │ Project Type: ( ) National ( ) International ( ) Regional...  │ │
│  │ Subject Area: [▼ Select AEI classification]                   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                    [← Back] [Save Draft] [Next →]   │
├──────────────────────────────────────────────────────────────────────┤
│  Step 3: Access Request                                              │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Select node(s) and equipment:                                  │ │
│  │                                                                 │ │
│  │ □ BioImaC                                                       │ │
│  │   □ MRI 1T: [__] hours (max 50h available)                     │ │
│  │   □ Cyclotron: [__] hours                                      │ │
│  │                                                                 │ │
│  │ ☑ CIC biomaGUNE                                                 │ │
│  │   ☑ MRI 7T: [24] hours (max 100h available)                    │ │
│  │   □ PET-CT: [__] hours                                         │ │
│  │   ...                                                           │ │
│  │                                                                 │ │
│  │ Service modality: ( ) Full assistance (•) Presential ( ) Self  │ │
│  │ Specialization: ( ) Clinical (•) Preclinical ( ) Radiotracers  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                    [← Back] [Save Draft] [Next →]   │
├──────────────────────────────────────────────────────────────────────┤
│  Step 4: Scientific Content                                          │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Scientific relevance and originality:                          │ │
│  │ ┌──────────────────────────────────────────────────────────┐  │ │
│  │ │                                                          │  │ │
│  │ │ (rich text editor)                                       │  │ │
│  │ │                                                          │  │ │
│  │ └──────────────────────────────────────────────────────────┘  │ │
│  │                                                                 │ │
│  │ Methodology and experimental design:                           │ │
│  │ ┌──────────────────────────────────────────────────────────┐  │ │
│  │ │                                                          │  │ │
│  │ └──────────────────────────────────────────────────────────┘  │ │
│  │ ... (more text areas for each criterion)                       │ │
│  └────────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────┤
│  Step 5: Declarations & Submit                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ ☑ I have confirmed technical feasibility with ReDIB node       │ │
│  │ □ This proposal involves experimental animals                   │ │
│  │   □ I have ethics committee approval                           │ │
│  │ □ This proposal involves human subjects                        │ │
│  │   □ I have ethics committee approval                           │ │
│  │ ☑ I consent to data processing as described                    │ │
│  │                                                                 │ │
│  │ [Preview PDF]                                                   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                    [← Back] [Save Draft] [SUBMIT]   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 9. Reporting and Statistics

### 9.1 Required Reports

| Report | Audience | Frequency |
|--------|----------|-----------|
| Call summary | Coordinator | Per call |
| Node usage statistics | Node directors | Monthly/Quarterly |
| Ministry annual report | Ministry (MICIU) | Annual |
| Equipment utilization | All nodes | Quarterly |
| Publication outcomes | Coordinator | Annual |
| User activity | Admin | On demand |

### 9.2 Ministry Report Data Points

Based on typical ICTS reporting requirements:

- Total applications received (by call, by node)
- Acceptance rates
- Hours allocated vs. hours used
- User demographics (nationality, institution type)
- Subject areas distribution
- Publications and acknowledgments
- Equipment utilization rates

### 9.3 Implementation Approach

```python
# Reports module structure
reports/
├── generators/
│   ├── call_summary.py
│   ├── node_statistics.py
│   ├── ministry_report.py
│   └── publication_tracking.py
├── exports/
│   ├── excel.py      # openpyxl for XLSX export
│   ├── pdf.py        # WeasyPrint for PDF
│   └── csv.py        # Standard CSV
└── views.py
```

---

## 10. Future Extensibility

### 10.1 Planned Future Modules

| Module | Description | Priority |
|--------|-------------|----------|
| **Equipment Usage Tracking** | Nodes report actual equipment usage (not just COA) | High |
| **Financial Module** | Track Access on Demand (AoD) invoicing | Medium |
| **Publication Scraping** | Auto-detect publications mentioning ReDIB | Medium |
| **API for External Systems** | REST API for integration with node LIMS | Low |
| **Mobile App** | Lightweight mobile view for notifications | Low |

### 10.2 Design for Extensibility

```python
# Django apps structure for modularity
redib/
├── core/           # Users, organizations, base models
├── calls/          # Call management
├── applications/   # Application submission and workflow
├── evaluations/    # Evaluator assignment and scoring
├── access/         # AccessGrant and scheduling
├── communications/ # Email templates and sending
├── reports/        # Reporting and exports
├── api/            # REST API (DRF) - future
├── usage/          # Equipment usage tracking - future
└── billing/        # AoD billing - future
```

---

## 11. Hosting and Infrastructure

### 11.1 IONOS Hosting Recommendation

Based on the preference for IONOS and the application requirements:

#### Option A: IONOS VPS (Recommended for Start)

**IONOS VPS Linux XL or XXL**

| Specification | XL | XXL (Recommended) |
|--------------|-----|-------------------|
| vCPUs | 4 | 6 |
| RAM | 8 GB | 12 GB |
| Storage | 160 GB NVMe | 240 GB NVMe |
| Price (approx) | ~€18/month | ~€26/month |

**Rationale**: A single VPS can handle Django + PostgreSQL + Redis + Celery for the expected load (< 1000 users, < 100 concurrent). Start with XL and upgrade if needed.

#### Option B: IONOS Cloud Server (More Control)

If you need more flexibility:

- **Cloud Server L**: 4 vCPU, 8 GB RAM
- Add managed PostgreSQL database
- Better for scaling but more complex setup

### 11.2 Infrastructure Setup

```
┌─────────────────────────────────────────────────────────────────────┐
│                    IONOS VPS SETUP                                  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     Ubuntu 22.04 LTS                         │   │
│  │  ┌─────────────────────────────────────────────────────┐    │   │
│  │  │ Docker + Docker Compose                              │    │   │
│  │  │                                                      │    │   │
│  │  │  ┌──────────────┐  ┌──────────────┐               │    │   │
│  │  │  │   Nginx      │  │  Certbot     │               │    │   │
│  │  │  │  (reverse    │  │  (SSL certs) │               │    │   │
│  │  │  │   proxy)     │  │              │               │    │   │
│  │  │  └──────┬───────┘  └──────────────┘               │    │   │
│  │  │         │                                          │    │   │
│  │  │         ▼                                          │    │   │
│  │  │  ┌──────────────┐  ┌──────────────┐               │    │   │
│  │  │  │   Gunicorn   │  │    Redis     │               │    │   │
│  │  │  │   (Django)   │  │   (cache +   │               │    │   │
│  │  │  │              │  │    queue)    │               │    │   │
│  │  │  └──────────────┘  └──────────────┘               │    │   │
│  │  │                                                      │    │   │
│  │  │  ┌──────────────┐  ┌──────────────┐               │    │   │
│  │  │  │  PostgreSQL  │  │ Celery Worker│               │    │   │
│  │  │  │              │  │ + Beat       │               │    │   │
│  │  │  └──────────────┘  └──────────────┘               │    │   │
│  │  └─────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  External: IONOS DNS, IONOS Backup                                 │
└─────────────────────────────────────────────────────────────────────┘
```

### 11.3 Docker Compose Structure

```yaml
# docker-compose.yml (simplified)
version: '3.8'

services:
  web:
    build: .
    command: gunicorn redib.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    depends_on:
      - db
      - redis
    env_file:
      - .env

  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    env_file:
      - .env.db

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  celery:
    build: .
    command: celery -A redib worker -l info
    depends_on:
      - db
      - redis
    env_file:
      - .env

  celery-beat:
    build: .
    command: celery -A redib beat -l info
    depends_on:
      - db
      - redis
    env_file:
      - .env

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - certbot_certs:/etc/letsencrypt
    depends_on:
      - web

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
  certbot_certs:
```

### 11.4 Email Configuration

**Option 1: IONOS Email (Simple)**
- Use IONOS email hosting included with domain
- Configure Django to use SMTP: `smtp.ionos.es:587`
- Good for low volume (< 1000 emails/day)

**Option 2: Transactional Email Service (Recommended)**
- **Brevo (Sendinblue)**: Free tier 300 emails/day, EU-based
- **Mailgun**: Good deliverability, pay-as-you-go
- Better tracking, templates, and deliverability

```python
# Django email settings for IONOS
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.ionos.es'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'noreply@redib.net'
EMAIL_HOST_PASSWORD = env('EMAIL_PASSWORD')
```

### 11.5 Backup Strategy

```
┌─────────────────────────────────────────────────────────────────────┐
│                       BACKUP SCHEDULE                               │
│                                                                     │
│  Database (PostgreSQL):                                             │
│  ├── Daily: Full pg_dump → IONOS Cloud Storage                     │
│  ├── Retain: 30 daily, 12 weekly, 6 monthly                        │
│  └── Test restore: Monthly                                          │
│                                                                     │
│  Media Files (uploads):                                             │
│  ├── Daily: Sync to IONOS Cloud Storage                            │
│  └── Retain: 90 days versioning                                     │
│                                                                     │
│  Configuration:                                                      │
│  ├── Git repository (non-sensitive)                                 │
│  └── Encrypted backup of .env files                                 │
│                                                                     │
│  VPS Snapshot:                                                       │
│  └── Weekly IONOS snapshot (keep 4)                                 │
└─────────────────────────────────────────────────────────────────────┘
```

### 11.6 Security Considerations

| Area | Measure |
|------|---------|
| **SSL/TLS** | Let's Encrypt via Certbot, auto-renewal |
| **Firewall** | UFW: only 22, 80, 443 open |
| **SSH** | Key-based auth only, disable password auth |
| **Django** | DEBUG=False, ALLOWED_HOSTS set, CSRF protection |
| **Database** | Not exposed externally, strong passwords |
| **Secrets** | Environment variables, not in code |
| **Updates** | Unattended security updates enabled |
| **GDPR** | All data in EU (IONOS EU datacenter) |

---

## 12. Development and Deployment Plan

### 12.1 Recommended Development Phases

```
Phase 1: Foundation (6-8 weeks)
├── Project setup, Docker configuration
├── Core models, authentication
├── Basic admin interface
├── Call management
└── User registration

Phase 2: Application Workflow (6-8 weeks)
├── Application form (multi-step)
├── Feasibility review workflow
├── Status tracking
├── Basic email notifications
└── Applicant dashboard

Phase 3: Evaluation System (4-6 weeks)
├── Evaluator assignment (random)
├── Blind evaluation form
├── Score aggregation
├── Resolution workflow
└── Results communication

Phase 4: Reporting & Polish (4-6 weeks)
├── Statistics dashboards
├── Report generation (PDF, Excel)
├── Email template refinement
├── User acceptance testing
└── Documentation

Phase 5: Deployment & Training (2-4 weeks)
├── Production deployment
├── Data migration (if any)
├── User training
├── Monitoring setup
└── Go-live
```

### 12.2 Estimated Timeline

**Total: 5-7 months** for full implementation

| Phase | Duration | Milestone |
|-------|----------|-----------|
| Phase 1 | Weeks 1-8 | Basic system running, can create calls |
| Phase 2 | Weeks 9-16 | Applications can be submitted and reviewed |
| Phase 3 | Weeks 17-22 | Full evaluation workflow working |
| Phase 4 | Weeks 23-28 | Reports and final polish |
| Phase 5 | Weeks 29-32 | Production deployment |

### 12.3 Development Environment

```bash
# Local development setup
git clone https://github.com/your-org/redib-coa.git
cd redib-coa
cp .env.example .env
docker-compose -f docker-compose.dev.yml up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
# Access at http://localhost:8000
```

---

## 13. Monitoring and Maintenance

### 13.1 Monitoring Stack (Simple)

For a system of this scale, complex monitoring is overkill. Recommended:

- **UptimeRobot** (free): External uptime monitoring, alerts via email/SMS
- **Django Admin**: Built-in view of users, applications, etc.
- **Sentry** (free tier): Error tracking and alerting
- **Server logs**: Centralized via Docker, reviewed weekly

### 13.2 Maintenance Tasks

| Task | Frequency | Method |
|------|-----------|--------|
| Security updates | Automated | unattended-upgrades |
| Django/Python updates | Monthly | Manual review, test, deploy |
| Database vacuum | Weekly | pg_cron or Celery task |
| Log rotation | Automatic | logrotate |
| SSL cert renewal | Automatic | Certbot |
| Backup verification | Monthly | Manual test restore |

---

## 14. Cost Estimate

### 14.1 Infrastructure Costs (Annual)

| Item | Provider | Monthly | Annual |
|------|----------|---------|--------|
| VPS XXL | IONOS | €26 | €312 |
| Domain | IONOS | - | €12 |
| Email hosting | IONOS (included) | €0 | €0 |
| Cloud storage (backups) | IONOS | €5 | €60 |
| SSL | Let's Encrypt | €0 | €0 |
| **Total Infrastructure** | | | **~€385/year** |

### 14.2 Optional Services

| Service | Purpose | Annual Cost |
|---------|---------|-------------|
| Brevo (email) | Better email deliverability | €0-200 |
| Sentry | Error tracking | €0 (free tier) |
| UptimeRobot | Uptime monitoring | €0 (free tier) |

**Total estimated: €400-600/year**

---

## 15. Appendices

### A. Technology Alternatives Considered

| Current Choice | Alternative | Why Not |
|---------------|-------------|---------|
| Django | FastAPI | Less mature admin, more frontend work |
| Django | Flask | Less batteries-included |
| PostgreSQL | MySQL | Less robust JSON, worse for analytics |
| HTMX | React/Vue | Complexity overkill for this use case |
| Celery | Django-Q | Less mature, smaller community |
| IONOS | AWS/GCP | Overkill, EU preference, cost |

### B. Key Django Packages

```txt
# requirements.txt (key packages)
Django>=5.0
psycopg[binary]>=3.1
celery>=5.3
redis>=5.0
django-allauth>=0.58
djangorestframework>=3.14
django-simple-history>=3.4
django-htmx>=1.17
django-environ>=0.11
weasyprint>=60.0  # PDF generation
openpyxl>=3.1     # Excel export
gunicorn>=21.0
whitenoise>=6.6   # Static files
sentry-sdk>=1.35
```

### C. Reference Documents

- REDIB-01-RCA: Regulations of the Access Committee
- REDIB-02-PDA: Access Protocol
- REDIB-03-PDC: Planning COA Calls
- REDIB-APP: Application Form

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | December 2025 | Claude (Anthropic) | Initial design document |

---

*End of Document*
