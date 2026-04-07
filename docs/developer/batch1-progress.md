# Batch 1 Implementation Progress

## Phase 1: Quick Fixes (Issues 18, 23, 17) - COMPLETE

### Issue 18: Remove animal ethics hard requirement
- Removed validation blocks in `ApplicationStep5Form.clean()` that required ethics approval when using animals/humans
- Updated help text in `wizard_step5.html` to say "recommended" instead of "must have"

### Issue 23: Fix Step 2 back button
- Created `application_edit_step1` view for editing Step 1 of existing drafts
- Updated `applications/urls.py` to point `edit_step1` to the new view
- Changed Step 2 back button to link to Step 1

### Issue 17: Replace "Project Type" with "Origin of Funds"
- Updated `PROJECT_TYPES` display labels in models (DB values unchanged)
- Updated label in 7 templates + form

### Migrations: None

---

## Phase 2: Remove PDF Signature Workflow (Issues 11, 12, 13) - COMPLETE

### Issue 11: Remove signed-PDF from application submission
- Replaced the "Download & Sign" card in `preview.html` with a direct "Submit Application" button
- Submit uses the existing `application_submit` view (POST-only with `@require_POST`)
- Replaced `upload_signed_pdf` view with a redirect to preview
- Removed `SignedPdfUploadForm` import from views

### Issue 12: No PDF in evaluations - confirmed, no changes needed

### Issue 13: Optional PDF download
- Added secondary "Download PDF for your records" link on preview page
- Relaxed `download_application_pdf` to work for any application status (not just draft)

### Migrations: None

---

## Phase 3: Funding Step Redesign (Issues 14, 15, 16) - COMPLETE

### Issue 14: Move Project Name to Step 1
- Added `project_name` CharField to Application model
- Added to Step 1 form above `brief_description`
- Relabeled Step 2's `project_title` to "Funded Project Name"

### Issue 15: Conditional funding fields
- Moved `has_competitive_funding` checkbox to top of Step 2
- Wrapped funding fields in `#funding-details` div, toggled by JS
- Form `clean()` clears funding fields when checkbox unchecked

### Issue 16: DB-backed FundingAgency dropdown
- Created `FundingAgency` model with name, timestamps, history
- Added `funding_agency_obj` FK on Application
- Step 2 form uses Select + "Other" pattern with `new_funding_agency_name` field
- Registered `FundingAgencyAdmin`

### Migrations:
- `applications/0007_fundingagency_application_project_name_and_more.py`

---

## Phase 4: Profile, Consent & Organization (Issues 1-10) - COMPLETE

### Issue 6: Organization model update
- Replaced 6 org types with 3: Company/Empresa, University/Universidad, Other/Otro
- Added `vat` field to Organization

### Issue 2: Required profile fields
- Added `position` to ProfileForm
- Made first_name, last_name, phone, position, organization required

### Issue 3: Auto data consent
- Added `auto_data_consent` BooleanField to User model
- Added consent checkbox with legal text to profile page

### Issue 1: Profile completion gate
- Created `ProfileCompletionMiddleware` in `core/middleware.py`
- Added `is_profile_complete` property to User model
- Exempts: /accounts/, /profile/, /admin/, static, media, superusers/staff

### Issues 4 & 5: Consent in application
- Step 5 form accepts `user` kwarg; auto-consent users see "Data consent provided" message
- Application always stores `data_consent=True` regardless of auto-consent path

### Issue 7: Self-extending organization dropdown
- Added "Other (create new)" sentinel to org dropdown
- JS shows/hides new org fields (name, type, country)
- Form creates Organization on save when "Other" selected

### Issue 8: Country from organization - display-only, derived from org

### Issues 9 & 10: Auto-fill and read-only profile fields
- Step 1 form auto-fills all profile fields including ORCID
- Profile-derived fields are `disabled=True` in form
- Views overwrite profile fields from user on every save
- Template shows "Edit your profile" link

### Migrations:
- `core/0004_historicalorganization_vat_and_more.py` (vat, auto_data_consent, org type choices)
- `core/0005_remap_organization_types.py` (data migration)

---

## Phase 5: Feasibility Review Reopen (Issues 19-22) - COMPLETE

### Issue 19: Add "reopen for edits" state
- Added `status` CharField to FeasibilityReview (pending/approved/rejected/edits_requested)
- Added `draft` to VALID_TRANSITIONS from `under_feasibility_review`

### Issue 20: Required comments for reopen
- Updated FeasibilityReviewForm with 3-choice `decision` field (Approve/Reject/Request Edits)
- Comments required for reject and edits_requested

### Issue 21: Return to editable draft
- On "edits_requested": sets application.status='draft', resets submitted_at, resets other reviews to pending

### Issue 22: Email notification
- Added `feasibility_edits_requested` template type
- Added template to seed command with reviewer comments and application URL
- View sends email on edits_requested decision

### Migrations:
- `applications/0008_feasibilityreview_status_and_more.py`
- `applications/0009_populate_feasibility_status.py` (data migration)
- `communications/0005_alter_emailtemplate_template_type_and_more.py`

---

## Phase 6: Cancel Button (Issue 24) - COMPLETE

### Issue 24: Cancel button with confirmation
- Created `application_cancel` view (POST-only, deletes draft, redirects to My Applications)
- Added `<pk>/cancel/` URL
- Added cancel form with JS confirm to: wizard steps 2-5 and preview page
- Step 1 already had a cancel link (to call detail page)

### Migrations: None

---

## Post-Implementation Verification Fixes (Round 1)

### Bug Fix: Legacy `is_feasible__isnull` queries
- Updated `core/views.py` dashboard to query `status='pending'` instead of `is_feasible__isnull=True`
- Updated `applications/tasks.py` feasibility reminder task similarly
- Updated `application_detail` view to use `review.status` instead of legacy `is_feasible` mapping
- Updated `detail.html` template to use new status values (approved/rejected/edits_requested/pending)
- Added `status` to `FeasibilityReviewAdmin` list_display and list_filter

## Post-Implementation Verification Fixes (Round 2)

### Bug Fix: Feasibility reopen workflow architecture
The first round of fixes had a follow-on issue: bulk-resetting all reviews on `edits_requested` wiped the reviewer comments from the database. The architecture has been redesigned:
- On `edits_requested`: only the triggering review is saved (with status='edits_requested' and comments preserved). The application moves to draft. Other reviews stay as-is.
- On RE-submit (in `application_submit`): the view now uses `get_or_create` for reviews (handles new nodes if equipment changed) and bulk-resets ALL reviews to pending. The application code is preserved across resubmissions.
- The first-submission path now creates ONE review per node (using `get_or_create`), fixing a latent bug where the original code tried to create one review per coordinator and would have hit the unique_together constraint.

### Feature: Edit-request comments visible to applicant
- `application_detail` view now passes `edit_requests` (list of feasibility reviews with status='edits_requested') to the template when application is in draft state.
- `detail.html` shows a yellow alert at the top with the coordinator's comments and an "Edit Application" button when edits have been requested.

### Bug Fix: PDF template missing project_name and label inconsistencies
- Added `project_name` row to Section 1 of `application_pdf.html`
- Renamed `brief_description` label from "Brief Description / Descripcion" to "Project Summary / Resumen del proyecto"
- Renamed `project_title` label from "Project Title / Titulo" to "Funded Project Name / Nombre del proyecto financiado"
- Funding agency display now uses `funding_agency_obj` with fallback to legacy `funding_agency` text field

### Doc Fix: Stale tasks.py docstring
- Updated the `send_feasibility_reminders` task docstring to reference `status='pending'` instead of `is_feasible is None`

## Post-Implementation Verification Fixes (Round 3)

### Critical Bug: ModelChoiceField rejected `__other__` sentinel
The "Other" dropdown patterns for ProfileForm.organization and ApplicationStep2Form.funding_agency_obj were broken. Both fields are FK ModelChoiceFields that run `to_python()` BEFORE `clean()`, calling `queryset.get(pk='__other__')` and raising "not a valid choice".

**Fix:** Created two custom ModelChoiceField subclasses:
- `OrgWithOtherChoiceField` in `core/forms.py`
- `FundingAgencyWithOtherChoiceField` in `applications/forms.py`

Each subclass overrides `to_python` and `validate` to whitelist the `'__other__'` sentinel. Both forms now declare the FK field explicitly using the custom class instead of relying on ModelForm auto-generation. The form's `clean()` method converts `'__other__'` into a real instance via `get_or_create`.

Verified working with end-to-end form validation tests for:
- Profile: existing org, "Other" with valid new org, "Other" with missing fields
- Step 2: no funding, funding with "Other" agency, "Other" with missing name

### High Bug: Middleware ordering caused 500 errors on redirect
`ProfileCompletionMiddleware` was listed BEFORE `MessageMiddleware` in `MIDDLEWARE`. The profile middleware called `messages.warning()` before `MessageMiddleware` had set up `request._messages`, causing `MessageFailure` exceptions on every redirect (i.e., every page load for users with incomplete profiles).

**Fix:** Swapped middleware order in `redib/settings.py` so `MessageMiddleware` runs first.

### Low Issue: Duplicate warning messages
Removed the `messages.warning()` call from `ProfileCompletionMiddleware` entirely. The profile page already shows a `profile_incomplete` alert via the view context, so the redirect message was redundant and could accumulate under HTMX/multi-request scenarios.

---

## All Phases Complete

### Full Migration List:
1. `applications/0007_fundingagency_application_project_name_and_more.py`
2. `applications/0008_feasibilityreview_status_and_more.py`
3. `applications/0009_populate_feasibility_status.py`
4. `core/0004_historicalorganization_vat_and_more.py`
5. `core/0005_remap_organization_types.py`
6. `communications/0005_alter_emailtemplate_template_type_and_more.py`

### New Files:
- `core/middleware.py`

### Production Deployment Notes:
- Run `python manage.py migrate` (6 migrations)
- Run `python manage.py seed_email_templates` (new feasibility_edits_requested template)
- Rebuild containers: migrations run automatically via entrypoint.sh
