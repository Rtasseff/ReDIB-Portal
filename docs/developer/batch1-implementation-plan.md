# Implementation Plan: Issues Batch 1 (26 Issues)

## Context

User testing surfaced 26 issues across registration, application workflow, PDF signatures, funding, ethics, feasibility review, and wizard UX. This plan implements all actionable issues (24 of 26, with 25 and 26 deferred) in 6 phases, ordered by dependency and risk. The `fixes-batch-1` branch is the working branch. Development is local (SQLite + runserver).

## Progress Tracking

After each phase, update `docs/developer/batch1-progress.md` with:
- Issues completed (by number)
- Files modified
- Migrations created
- Any decisions made
- Phase-specific test results

This file serves as a recovery document if a session is interrupted and as a deployment checklist for production.

---

## Phase 1: Quick Fixes (Issues 18, 23, 17)

No model changes. Low risk. Independent of everything else.

### Issue 18: Remove animal ethics hard requirement
- **File:** `applications/forms.py` ~line 286-296
- **Change:** Remove the two `if` blocks in `ApplicationStep5Form.clean()` that raise `ValidationError` when `uses_animals=True` but `has_animal_ethics=False` (and same for humans). Keep the `data_consent` required check.
- **File:** `templates/applications/wizard_step5.html` — Update help text from "you must have" to "recommended before starting experiments"

### Issue 23: Fix Step 2 back button
- **File:** `templates/applications/wizard_step2.html` line 113 — Change link from `applications:my_applications` to `applications:edit_step1` with `application.pk`
- **File:** `applications/urls.py` line 24 — Currently `edit_step1` is a stub pointing to `edit_step2`. Create a proper `application_edit_step1` view.
- **File:** `applications/views.py` — Add `application_edit_step1` view that loads `ApplicationStep1Form(instance=application, user=request.user)`, renders `wizard_step1.html`, saves, and redirects to step2.
- **File:** `templates/applications/wizard_step1.html` — Minor: handle both create (no application yet) and edit (existing application) context.

### Issue 17: Replace "Project type" with "Origin of funds"
- **File:** `applications/models.py` ~line 44-52 — Update `PROJECT_TYPES` display labels:
  - `national` → "National (Spain)"
  - `regional` → "Regional (Autonomous Communities)"  
  - `european` → "European Union (EU)"
  - `international_non_european` → "International (non-EU)"
  - `internal` → "Internal / Institutional"
  - `private` → "Private"
  - `other` → "Other"
- **File:** `applications/forms.py` — Change label on `project_type` field to "Origin of Funds"
- **Files:** `templates/applications/preview.html`, `templates/applications/application_pdf.html`, any detail templates — Update display label from "Project Type" to "Origin of Funds"
- No migration needed (label-only changes, DB values stay the same)

---

## Phase 2: Remove PDF Signature Workflow (Issues 11, 12, 13)

Major workflow simplification. Key discovery: **`application_submit` view already exists** at `views.py:331-449` and handles direct submission without PDF. The preview template just needs to point there.

### Issue 11: Remove signed-PDF from application submission
- **File:** `templates/applications/preview.html` lines 224-273 — Replace the entire "Download & Sign" card with a direct "Submit Application" button (POST form to `applications:submit`). Add a JS `confirm()` dialog: "Once submitted, you cannot make further changes. Continue?"
- **File:** `applications/views.py` — In `application_submit` (line 331), ensure it does NOT check `pdf_generated_at`. Currently it doesn't — confirmed clean.
- **File:** `applications/views.py` — In `upload_signed_pdf`, add redirect to `applications:preview` for anyone hitting the old URL.
- Do NOT remove PDF model fields from Application (existing data references them).

### Issue 12: Confirm no PDF in evaluations
- Already confirmed: no PDF signature logic in `evaluations/`. Document in progress log only.

### Issue 13: Keep optional PDF download
- **File:** `templates/applications/preview.html` — Below the Submit button, add a secondary "Download PDF for your records (optional)" link pointing to `applications:download_pdf`.
- **File:** `applications/views.py` `download_application_pdf` — Relax the `status='draft'` check to also allow downloading for submitted applications (for record-keeping).

---

## Phase 3: Funding Step Redesign (Issues 14, 15, 16)

Issues 14 and 15 are form/template changes. Issue 16 adds a new model.

### Issue 14: Move Project Name to Step 1, rename in Step 2
- **Approach:** Add a new `project_name` field to Application model (CharField, max_length=300, blank=True). This is the general research project name shown in Step 1 above "Project Summary" (brief_description). The existing `project_title` stays in Step 2 but gets relabeled to "Funded Project Name" and becomes conditional on `has_competitive_funding`.
- **File:** `applications/models.py` — Add `project_name` field after `brief_description`
- **File:** `applications/forms.py` `ApplicationStep1Form` — Add `project_name` to fields, placed above `brief_description`. Make it required.
- **File:** `applications/forms.py` `ApplicationStep2Form` — Change `project_title` label to "Funded Project Name". Remove `project_title` required status (it's conditional now).
- **Files:** `templates/applications/wizard_step1.html`, `wizard_step2.html`, `preview.html`, `application_pdf.html` — Update layouts. Step 1 shows "Project Name" above "Project Summary". Step 2 shows "Funded Project Name" inside the conditional funding section.
- **Migration:** Yes, add `project_name` field

### Issue 15: Conditional funding fields
- **File:** `templates/applications/wizard_step2.html` — Move `has_competitive_funding` checkbox to top of form. Wrap `project_title`, `project_code`, `funding_agency`, `project_type` in a `<div id="funding-details">`. Add JS: toggle visibility on checkbox change.
- **File:** `applications/forms.py` `ApplicationStep2Form` — Make funding-specific fields not required (they already are `blank=True` on the model). Validate in `clean()`: if `has_competitive_funding=False`, clear funding fields to empty/null.
- **File:** `applications/views.py` `application_edit_step2` — On save, if `has_competitive_funding=False`, set funding fields to blank.

### Issue 16: DB-backed FundingAgency dropdown
- **File:** `applications/models.py` — Add `FundingAgency` model (name, created_at, updated_at) and `funding_agency_obj` ForeignKey on Application (null=True, blank=True). Keep old `funding_agency` CharField for backward compat.
- **File:** `applications/forms.py` — Replace `funding_agency` text input with a Select + "Other" pattern (similar to org dropdown).
- **File:** `applications/admin.py` — Register FundingAgencyAdmin
- **File:** `templates/applications/wizard_step2.html` — Add "Other" toggle with text input for new agency
- **Migration:** Yes, new model + FK field

---

## Phase 4: Profile, Consent & Organization Enhancements (Issues 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)

Largest phase. Model changes to User and Organization, profile completion enforcement, consent flow, and application-profile sync.

### Issue 6: Organization model update
- **File:** `core/models.py` Organization — Add `vat` field (CharField, blank=True). Replace `ORG_TYPES` with 3 choices: `('company', 'Company / Empresa')`, `('university', 'University / Universidad')`, `('other', 'Other / Otro')`.
- **Migration:** Yes — schema migration for `vat` field + data migration to remap existing types: `research_center` → `other`, `hospital` → `other`, `ministry` → `other`. `university` and `company` stay. `other` stays.

### Issue 2: Add required profile fields
- **File:** `core/forms.py` `ProfileForm` — Add `position` to fields. In `__init__`, set `required=True` on `first_name`, `last_name`, `phone`, `organization`, `position`.
- **File:** `templates/core/profile.html` — Add position field row

### Issue 3: Add auto_data_consent
- **File:** `core/models.py` User — Add `auto_data_consent = BooleanField(default=False)`
- **File:** `core/forms.py` `ProfileForm` — Add `auto_data_consent` checkbox with consent text
- **File:** `templates/core/profile.html` — Add consent section with legal text from Step 5
- **File:** `core/admin.py` — Add to UserAdmin fieldsets
- **Migration:** Yes (combined with Issue 6)

### Issue 1: Profile completion gate
- **New file:** `core/middleware.py` — `ProfileCompletionMiddleware` that checks authenticated users' profile completeness. Exempt paths: `/accounts/`, `/profile/`, `/admin/`, `/static/`, `/media/`. Exempt superusers.
- **File:** `core/models.py` User — Add `is_profile_complete` property checking: first_name, last_name, phone, organization, position
- **File:** `redib/settings.py` — Add middleware after `AuthenticationMiddleware`
- **File:** `templates/core/profile.html` — Show alert when profile incomplete

### Issues 4 & 5: Consent in application
- **File:** `applications/forms.py` `ApplicationStep5Form.__init__` — Accept `user` kwarg. If `user.auto_data_consent`, set `initial['data_consent']=True` and `self.fields['data_consent'].disabled=True`.
- **File:** `applications/views.py` `application_edit_step5` — Pass `user=request.user` to form. On POST, if `user.auto_data_consent`, force `application.data_consent=True`.
- **File:** `templates/applications/wizard_step5.html` — Show "Data consent provided via profile" message when auto-consent active.

### Issue 7: Self-extending organization dropdown
- **File:** `core/forms.py` `ProfileForm` — Add sentinel "Other" option to organization choices. Add hidden fields: `new_org_name`, `new_org_type`, `new_org_country`.
- **File:** `core/views.py` `profile` — On POST, if org selection is "other", create new Organization from provided fields.
- **File:** `templates/core/profile.html` — JS to show/hide new org fields when "Other" selected.

### Issue 8: Country from organization
- Display-only change. Show `user.organization.country` where appropriate (preview, PDF, detail).
- **Files:** `templates/applications/preview.html`, `application_pdf.html`

### Issues 9 & 10: Auto-fill and read-only profile fields
- **File:** `applications/forms.py` `ApplicationStep1Form.__init__` — Add ORCID auto-fill: `self.initial['applicant_orcid'] = user.orcid`. Set profile fields as `disabled=True`.
- **File:** `applications/views.py` `application_create` — On POST, overwrite profile fields from `request.user` (disabled fields don't submit).
- **File:** `templates/applications/wizard_step1.html` — Add "These fields come from your profile. Edit profile to change." note with link.

---

## Phase 5: Feasibility Review Reopen (Issues 19, 20, 21, 22)

Most complex workflow change. Adds a third feasibility outcome.

### Issue 19: Add "reopen for edits" state
- **File:** `applications/models.py` FeasibilityReview — Add `status` CharField (choices: pending, approved, rejected, edits_requested; default='pending'). Keep `is_feasible` for backward compat.
- **File:** `applications/models.py` Application.VALID_TRANSITIONS — Add `'draft'` to transitions from `'under_feasibility_review'`.
- **Migration:** Yes + data migration to populate `status` from `is_feasible`

### Issue 20: Require comments for reopen
- **File:** `applications/forms.py` `FeasibilityReviewForm` — Change `is_feasible` to a 3-choice field: Approve, Reject, Request Edits. Update `clean()` to require comments for both reject and request_edits.
- **File:** `templates/applications/feasibility_review.html` — Add reviewer guidance note about providing clear edit instructions.

### Issue 21: Return to editable draft
- **File:** `applications/views.py` `feasibility_review` — Add branch for "edits_requested": set `application.status='draft'`, `application.submitted_at=None`, reset FeasibilityReview records to pending, store comments.
- **File:** `templates/applications/my_applications.html` — Show badge for "edits requested" applications
- **File:** `templates/applications/detail.html` — Show coordinator comments when application is in draft after reopen

### Issue 22: Email notification
- **File:** `communications/models.py` — Add `'feasibility_edits_requested'` to TEMPLATE_TYPES
- **File:** `communications/management/commands/seed_email_templates.py` — Add template content
- **File:** `applications/views.py` — Send email on edits_requested with coordinator comments and application link
- **Migration:** Yes (new template type choice)

---

## Phase 6: Wizard UX — Cancel Button (Issue 24)

### Issue 24: Cancel button with confirmation and delete
- **File:** `applications/views.py` — Add `application_cancel` view (POST only, deletes draft, redirects to my_applications)
- **File:** `applications/urls.py` — Add `<pk>/cancel/` URL
- **Files:** All wizard step templates (step1-5), `preview.html` — Add Cancel button (POST form with JS confirm)
- Cascade delete handles RequestedAccess cleanup automatically.

---

## Deferred (Not Implementing)

- **Issue 25:** Scientific guidance text — waiting on Angel
- **Issue 26:** Seed data for dropdowns — waiting on external input

---

## Resolved Decisions

1. **"Contact ID"** — Skip. Not a real field, no new model addition needed.
2. **Organization types** — Replace with 3 types: Company/Empresa, University/Universidad, Other/Otro. Requires data migration to remap existing values (research_center, hospital, ministry → Other).
3. **Project Name** — Add a new `project_name` CharField to Application model for Step 1 (above "Project Summary" / brief_description). Keep existing `project_title` in Step 2 but relabel to "Funded Project Name" — it becomes part of the conditional funding section (only shown/required when has_competitive_funding=True).

---

## Manual Testing Plan (After All Phases)

### Scenario 1: New User Full Flow
1. Register new account (email + password only)
2. Verify email
3. Login → redirected to profile page with "complete your profile" alert
4. Try navigating to dashboard → blocked, redirected to profile
5. Fill in: first name, last name, phone, organization (select existing or create new via "Other"), position, ORCID (optional), auto_data_consent (check it)
6. Save profile → can now navigate freely
7. Browse calls → click "Apply" on an open call
8. Step 1: verify profile fields are pre-filled and read-only, enter brief_description and project_name
9. Step 2: uncheck "has competitive funding" → funding fields disabled. Check it → fields appear. Fill funding details. Note "Origin of Funds" label.
10. Step 3: select equipment
11. Step 4: fill scientific content
12. Step 5: verify consent shows "Data consent provided via profile" (not the checkbox)
13. Preview: verify all data correct, click "Submit Application" → confirm dialog → submitted
14. Verify application status is "Under Feasibility Review"
15. Optional: download PDF for records

### Scenario 2: Application Without Auto-Consent
1. Edit profile, uncheck auto_data_consent
2. Create new application
3. At Step 5, verify the data consent checkbox is shown with full legal text
4. Must check it to proceed

### Scenario 3: Feasibility Reopen Cycle
1. Login as node coordinator
2. Open feasibility queue → review an application
3. Select "Request Edits" without comments → validation error
4. Add comments explaining what to fix → submit
5. Login as applicant → application shows as "Draft" with "Edits Requested" badge
6. View application → coordinator comments visible
7. Edit and resubmit → new feasibility review created

### Scenario 4: Cancel Application
1. Start new application, reach Step 3
2. Click "Cancel" → confirmation popup: "All application data will be deleted"
3. Cancel the popup → stays on Step 3
4. Click "Cancel" again → confirm → redirected to My Applications, draft is gone

### Scenario 5: Wizard Back Navigation
1. Start application → Step 1 → Step 2
2. Click "Back" on Step 2 → returns to Step 1 with saved data
3. Can edit Step 1 fields → save → proceeds to Step 2

### Scenario 6: Animal Ethics Without Approval
1. In Step 5, check "Uses animals" but leave "Has ethics approval" unchecked
2. Check data consent → save → should succeed (no validation error)
3. Preview shows "Uses animals: Yes", "Has ethics approval: No"

### Scenario 7: Organization "Other" Flow
1. Go to profile
2. Select "Other" in organization dropdown
3. Fill in new org name, type, country
4. Save → new organization created and associated with user
5. Start new application → applicant_entity shows the new organization name

### Scenario 8: Funding Agency Selection (Origin of Funds Auto-Populated)
1. Start a new application → reach Step 2
2. Check "Has competitive funding" → funding fields appear
3. Verify the **"Origin of Funds"** dropdown is **not visible** — only the Funding Agency dropdown is shown
4. Select an existing agency (e.g. "Agencia Estatal de Investigacion (AEI)")
5. Fill in project title, project code, subject area → save / next
6. Go to Preview → verify "Origin of Funds" displays "Spanish Government" (auto-derived from the agency)
7. Check the admin or DB: `Application.project_type` should be `spanish_government`

### Scenario 9: Funding Agency "Other (enter new)" Flow
1. Start a new application → reach Step 2
2. Check "Has competitive funding"
3. In the Funding Agency dropdown, select **"Other (enter new)"**
4. Verify a card appears with two fields: "Funding Agency Name" (text) and "Origin of Funds" (dropdown)
5. Leave both blank → try to submit → validation errors on both fields
6. Fill in name only, leave Origin of Funds blank → submit → validation error on Origin of Funds
7. Fill in both: name = "My New Agency", Origin of Funds = "European Union"
8. Save / next → should succeed
9. Go to Preview → verify Funding Agency shows "My New Agency", Origin of Funds shows "European Union"
10. Start another application → the Funding Agency dropdown should now include "My New Agency"
11. Check admin: `FundingAgency` table has "My New Agency" with `origin_of_funds=european_union`

### Scenario 10: Funding Agency Without Origin (Edge Case)
_This scenario tests the rare case where a FundingAgency record exists in the DB but has a blank `origin_of_funds` (e.g. created before this feature was added)._
1. In Django admin, create a FundingAgency with name "Legacy Agency" and leave `origin_of_funds` blank
2. Start a new application → reach Step 2
3. Check "Has competitive funding"
4. Select "Legacy Agency" from the Funding Agency dropdown
5. Verify an **"Origin of Funds"** dropdown appears with a warning: "This agency is missing its Origin of Funds classification. Please select one."
6. Try to submit without selecting an origin → validation error
7. Select an origin (e.g. "Private / Philanthropic") → save / next → succeeds
8. Check admin: the "Legacy Agency" `FundingAgency` record now has `origin_of_funds=private` (backfilled)
9. Start another application → select "Legacy Agency" again → no warning this time, origin is already set

### Scenario 11: Competitive Funding Toggle Clears Fields
1. Start a new application → reach Step 2
2. Check "Has competitive funding" → fill in project title, select an agency
3. Uncheck "Has competitive funding" → funding fields should hide
4. Save / next → go to Preview → verify no funding information is displayed
5. Check DB: `project_type`, `project_title`, `funding_agency_obj` should all be blank/null
