# COA Application Form - Data Model & Web Form Specification

## Overview

This document specifies the exact fields needed for the ReDIB Competitive Open Access (COA) application form. The web form collects this information from applicants and stores it for evaluation.

---

## Data Model

### Application Model

The main `Application` model should contain these fields:

#### System Fields (auto-generated, not user-editable)

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID/AutoField | Primary key |
| `code` | CharField(30) | Auto-generated application code, unique |
| `call` | ForeignKey(Call) | The COA call this application is for |
| `applicant` | ForeignKey(User) | The user who created the application |
| `status` | CharField | Application workflow status |
| `created_at` | DateTimeField | Auto timestamp |
| `updated_at` | DateTimeField | Auto timestamp |
| `submitted_at` | DateTimeField | Null until submitted |

#### Section 1: Header Information

| Field | Type | Required | Max Length | Notes |
|-------|------|----------|------------|-------|
| `brief_description` | CharField | Yes | 100 | "Brief description of the requested proposal" - max 100 characters |

#### Section 2: Applicant Information

| Field | Type | Required | Max Length | Notes |
|-------|------|----------|------------|-------|
| `applicant_name` | CharField | Yes | 200 | "Name and Surname" |
| `applicant_orcid` | CharField | No | 25 | "ORCID" - format: 0000-0000-0000-0000 |
| `applicant_entity` | CharField | Yes | 300 | "Entity" - institution/organization name |
| `applicant_email` | EmailField | Yes | 254 | "Email" |
| `applicant_phone` | CharField | Yes | 30 | "Phone" |

**Note:** These fields are on the Application, not pulled from User model, because the applicant may submit on behalf of a different PI or the user's profile data may change over time. The application should capture the data as submitted.

#### Section 3: Source of Funding

| Field | Type | Required | Max Length | Notes |
|-------|------|----------|------------|-------|
| `project_title` | CharField | No | 500 | "Project Title" - can be blank if no external funding |
| `project_code` | CharField | No | 100 | "Official code Project" |
| `funding_agency` | CharField | No | 300 | "Funding agency" |
| `project_type` | CharField | Yes | 30 | "Type of Project" - single select from choices |

**Project Type Choices:**

```python
PROJECT_TYPE_CHOICES = [
    ('national', 'National'),
    ('international_non_eu', 'International, non-European'),
    ('regional', 'Regional'),
    ('european', 'European'),
    ('internal', 'Internal'),
    ('private', 'Private'),
    ('other', 'Other'),
]
```

#### Section 4: Subject Area

| Field | Type | Required | Max Length | Notes |
|-------|------|----------|------------|-------|
| `subject_area` | CharField | Yes | 10 | Single select from AEI classification |
| `subject_area_other` | CharField | No | 200 | Only if subject_area = 'other' |

**Subject Area Choices (AEI Classification):**

```python
SUBJECT_AREA_CHOICES = [
    ('CSO', '1. CSO / Social Sciences'),
    ('DER', '2. DER / Law'),
    ('ECO', '3. ECO / Economy'),
    ('MLP', '4. MLP / Mind, language and thought'),
    ('FLA', '5. FLA / Culture: Philology, literature and art'),
    ('PHA', '6. PHA / Studies in history and archaeology'),
    ('EDU', '7. EDU / Educational Sciences'),
    ('PSI', '8. PSI / Psychology'),
    ('MTM', '9. MTM / Mathematical Sciences'),
    ('FIS', '10. FIS / Physical Sciences'),
    ('PIN', '11. PIN / Industrial production, engineering'),
    ('TIC', '12. TIC / Information and communications technologies'),
    ('EYT', '13. EYT / Energy and Transport'),
    ('CTQ', '14. CTQ / Chemical sciences and technologies'),
    ('MAT', '15. MAT / Materials Sciences and Technology'),
    ('CTM', '16. CTM / Environmental science and technology'),
    ('CAA', '17. CAA / Agricultural sciences'),
    ('BIO', '18. BIO / Biosciences and biotechnology'),
    ('BME', '19. BME / Biomedicine'),
    ('OTHER', '20. Other (specify)'),
]
```

#### Section 5: Service Modality & Specialization

| Field | Type | Required | Max Length | Notes |
|-------|------|----------|------------|-------|
| `service_modality` | CharField | Yes | 20 | Single select |
| `specialization_area` | CharField | Yes | 20 | Single select |

**Service Modality Choices:**

```python
SERVICE_MODALITY_CHOICES = [
    ('full_assistance', 'Full assistance'),
    ('presential', 'Presential'),
    ('self_service', 'Self service'),
]
```

**Specialization Area Choices:**

```python
SPECIALIZATION_AREA_CHOICES = [
    ('clinic', 'Clinic'),
    ('preclinic', 'Preclinic'),
    ('radiotracers', 'Radiotracers'),
    ('radiochemistry', 'Radiochemistry Lab'),
]
```

#### Section 6: Declarations (Checkboxes)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `declares_technical_feasibility` | BooleanField | No | "I have already contacted ReDIB or one of its nodes, where they have confirmed the TECHNICAL FEASIBILITY of the experimentation" |
| `declares_animal_use` | BooleanField | No | "This Proposal involves the use of EXPERIMENTAL ANIMALS" |
| `declares_animal_ethics` | BooleanField | No | "...and for this purpose I have the corresponding approval from the Ethics Committee" - only relevant if animal_use is True |
| `declares_human_use` | BooleanField | No | "This Proposal involves HUMANS as subjects of study" |
| `declares_human_ethics` | BooleanField | No | "...has the mandatory approval by the Ethics Committee" - only relevant if human_use is True |
| `declares_data_consent` | BooleanField | **Yes** | "Having been informed of the processing to which my personal data will be subject, I freely give my consent" - **REQUIRED to submit** |

#### Section 7: Scientific Content (Long Text Fields)

All are required text fields with no character limit specified in the form.

| Field | Type | Required | Label/Prompt |
|-------|------|----------|--------------|
| `scientific_relevance` | TextField | Yes | "Provide arguments supporting the scientific-technical relevance of the proposal, its quality and originality" |
| `methodology_description` | TextField | Yes | "Briefly describe the experimental and methodological design that you intend to carry out during your access to ReDIB" |
| `expected_contributions` | TextField | Yes | "Justify your expectations for future scientific-technical contributions and express your commitment to publish and disseminate the ICTS access you are now requesting." |
| `impact_strengths` | TextField | Yes | "Describe the strengths and/or impact of your proposal, in terms of advancing knowledge and innovation" |
| `socioeconomic_significance` | TextField | Yes | "Explain the social, economic or industrial significance of the result obtained with the access granted" |
| `opportunity_criteria` | TextField | Yes | "Explain criteria of opportunity or impact on the advancement of knowledge or in the translational or applied field of the research you plan to carry out during your access to ReDIB." |

---

### RequestedAccess Model (Separate Related Model)

This is a many-to-many relationship between Application and Equipment, with an extra field for hours requested.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | AutoField | - | Primary key |
| `application` | ForeignKey(Application) | Yes | on_delete=CASCADE |
| `equipment` | ForeignKey(Equipment) | Yes | on_delete=PROTECT |
| `hours_requested` | DecimalField(6,1) | Yes | Positive number, max constrained by call allocation |

**Constraints:**
- An application can request multiple equipment items
- Equipment items can be from different nodes (multi-node applications are allowed)
- Hours requested cannot exceed the hours offered for that equipment in the associated call
- At least one equipment request is required to submit the application

---

### Equipment Reference Data

The Equipment model should already exist. For reference, here is the full list from the form:

**BioImaC:**
- MRI 1 T
- Cyclotron
- Radiochemistry Lab

**CIC biomaGUNE:**
- MRI 7 T
- MRI 11.7 T
- PET-CT
- SPECT-CT
- PET-SPECT-CT-OI
- Cyclotron
- Radiochemistry Lab

**Imaging La Fe:**
- MRI 3 T
- PET-MRI

**TRIMA – CNIC:**
- MRI 3 T
- MRI 7 T
- PET-CT
- SPECT-CT
- Multidetector-CT

---

## Web Form Structure

### Recommended Form Layout (Multi-Step or Single Page with Sections)

The form can be implemented as either:
1. A single long page with clearly marked sections, or
2. A multi-step wizard

Either way, organize into these sections:

#### Form Section 1: Basic Information
- Call (display only, auto-selected based on URL/context)
- Date (display only, auto-filled)
- Brief description (text input, 100 char limit with counter)

#### Form Section 2: Applicant Details
- Name and Surname (text input)
- ORCID (text input, optional, validate format if provided)
- Entity (text input)
- Email (email input)
- Phone (text input)

**UX Note:** Pre-fill from logged-in user's profile if available, but allow editing.

#### Form Section 3: Source of Funding
- Project Title (text input, optional)
- Official code Project (text input, optional)
- Funding agency (text input, optional)
- Type of Project (radio buttons or select dropdown)

**UX Note:** Show helper text explaining that competitively funded projects get automatic quality approval.

#### Form Section 4: Subject Area
- Subject Area (radio buttons or select dropdown with all 20 options)
- If "Other" selected, show text input for specification

#### Form Section 5: Equipment & Access Request
Display equipment grouped by node. For each node, show its equipment list. User can:
- Check/select which equipment they want
- Enter hours requested for each selected equipment

**UI Suggestion:**
```
□ BioImaC
  □ MRI 1 T          [___] hours
  □ Cyclotron        [___] hours
  □ Radiochemistry Lab [___] hours

□ CIC biomaGUNE
  □ MRI 7 T          [___] hours
  □ MRI 11.7 T       [___] hours
  ... etc
```

Show available hours from the call allocation next to each equipment item (e.g., "max 50 hours available").

#### Form Section 6: Service Preferences
- Service modality (radio buttons: Full assistance / Presential / Self service)
- Specialization area (radio buttons: Clinic / Preclinic / Radiotracers / Radiochemistry Lab)

#### Form Section 7: Scientific Content
Six text areas, each with the full prompt text as label:

1. Scientific-technical relevance, quality and originality
2. Experimental and methodological design
3. Expected future contributions and commitment to publish
4. Strengths and impact on knowledge advancement
5. Social, economic or industrial significance
6. Opportunity criteria and translational impact

**UX Note:** Consider using rich text editors or at minimum allow paragraphs. These are the main content evaluated by the Access Committee.

#### Form Section 8: Declarations & Consent
Checkboxes with full legal text:

- [ ] Technical feasibility confirmed (optional but recommended)
- [ ] Uses experimental animals
  - [ ] Has animal ethics approval (show only if above checked)
- [ ] Uses human subjects
  - [ ] Has human ethics approval (show only if above checked)
- [ ] **Data protection consent** (REQUIRED - cannot submit without this)

Display the full data protection text from the form.

#### Form Section 9: Submission
- Preview/summary of application
- Submit button
- Save draft button (available throughout)

---

## Validation Rules

### On Submit

1. `brief_description` - Required, max 100 characters
2. `applicant_name` - Required
3. `applicant_entity` - Required
4. `applicant_email` - Required, valid email format
5. `applicant_phone` - Required
6. `project_type` - Required (must select one)
7. `subject_area` - Required (must select one)
8. `subject_area_other` - Required if subject_area = 'OTHER'
9. `service_modality` - Required (must select one)
10. `specialization_area` - Required (must select one)
11. `declares_data_consent` - Must be True
12. All six scientific content fields - Required, non-empty
13. At least one equipment item must be selected with hours > 0
14. For each requested equipment, hours must not exceed call allocation

### Conditional Validation

- If `declares_animal_use` is True, `declares_animal_ethics` should be True (warn if not, but don't block)
- If `declares_human_use` is True, `declares_human_ethics` should be True (warn if not, but don't block)
- `applicant_orcid` if provided should match pattern: `^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$`

---

## Auto-Calculated/Derived Fields

These fields can be computed and stored on the Application model for convenience:

| Field | Type | Calculation |
|-------|------|-------------|
| `has_competitive_funding` | BooleanField | True if `project_type` in ['national', 'international_non_eu', 'regional', 'european'] AND `project_code` is not blank |
| `total_hours_requested` | DecimalField | Sum of all related RequestedAccess.hours_requested |
| `nodes_involved` | Derived | List of distinct nodes from requested equipment (for routing feasibility reviews) |

---

## Form Behavior

### Draft Saving
- Allow saving incomplete applications as draft
- User can return and continue editing
- Only validate required fields on final submit, not on draft save

### Pre-fill from User Profile
- If User model has name, email, phone, ORCID, organization - pre-fill the applicant fields
- User can override these values

### Equipment Filtering
- Only show equipment that has hours allocated in the selected call
- Show "0 hours available" or hide equipment with no allocation

### After Submission
- Application status changes from 'draft' to 'submitted'
- `submitted_at` timestamp is set
- Application becomes read-only to the applicant
- Confirmation email is sent
- Application is routed to relevant node(s) for feasibility review

---

## Notes for Implementation

1. The form collects applicant info directly rather than linking to User profile because:
   - Applicants may submit on behalf of a PI
   - Historical record should not change if user updates profile later

2. The six scientific content fields map directly to evaluation criteria used by the Access Committee.

3. Equipment/hours are stored in a separate model to allow multiple equipment requests per application.

4. The `project_type` and `project_code` together determine `has_competitive_funding` which affects the approval rules (competitively funded projects cannot be rejected for quality, only prioritized by score).
