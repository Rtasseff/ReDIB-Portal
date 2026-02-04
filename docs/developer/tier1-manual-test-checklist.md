# Tier 1 Manual Test Checklist

Use this checklist to verify all Tier 1 issue fixes after merging the `feature/tier1-issue-fixes` branch.
The issues originally came from docs/developer/issue-action-plan-20260204.md

**Prerequisites:** Run `python manage.py migrate` and `python manage.py seed_email_templates` before testing.

---

## Issue #9 - Evaluator Email Template Fix

- [x] Run `python manage.py seed_email_templates` and confirm "Updated template: Evaluation Assigned"
- [x] In Django admin or DB, verify the `evaluation_assigned` email template text says "6 criteria (0-2 scale)" (not "5 criteria (1-5 scale)")
- [x] Verify all resolution email templates (`resolution_accepted`, `resolution_pending`, `resolution_rejected`) reference score as `X/12.00` (not `X/5.00`)
- [x] Verify `evaluations_complete` template shows `{{ average_score }} / 12.00`

## Issue #10 - Profile Page

- [x] Log in as any user and click "Profile" in the top-right user dropdown
- [x] Verify the page loads at `/profile/` without 404
- [x] Verify you can see and edit: First Name, Last Name, Phone, ORCID, Organization
  - Org is a drop down, it needs to be populated by someone 
- [x] Verify Email is displayed but **not editable** (disabled field)
- [x] Verify user roles are displayed in the sidebar (read-only)
  - they are not in the side bar, they are at the bottom which is fine
- [x] Edit a field (e.g., phone number), click "Save Changes", confirm success message
- [x] Refresh the page and verify the change persisted

## Issue #5 - Call Auto-Close

- [x] **Celery task test:** If Celery is running, verify `check-call-deadlines` appears in the beat schedule. Alternatively, test manually:
  ```python
  # In Django shell
  from calls.tasks import check_call_deadlines
  result = check_call_deadlines()
  print(result)  # Should return 0 if no expired open calls
  ```
- [x] **View fallback test:** Create/use a call with `status='open'` and `submission_end` in the past. Visit `/calls/` (public call list) and verify the call does NOT appear as open (it should have been auto-closed to 'closed' status)
- [x] Verify the call's status in the database is now 'closed'

## Issue #3 - Specialization Options Alignment

- [x] Start a new application. In Step 2 (equipment/specialization), verify the dropdown shows exactly 4 options: Clinical, Preclinical, Radiotracers, Radiochemistry Lab
- [x] In Django admin, check a UserRole with `role='evaluator'` - verify the Area field has the same 4 options (+ blank)


## Issue #12 - Evaluated At / Completed At Fix

- [x] View an application detail page (`/applications/<id>/`) for a resolved application - verify the timeline shows "Resolved" with a date (not "Evaluated" with empty value)
- [x] As a node coordinator, view a node resolution review page. If there are completed evaluations, verify the table column says "Completed On" and shows actual dates (not "Evaluated At" with blanks)

## Issue #4 - Back Button Removal

- [x] Navigate to the following pages and verify there is **no** "Back to Dashboard" or "Back to My Applications" footer button:
  - I checked a few, ot all
- [x] Verify the sidebar navigation and browser back button still work for navigation

## Issue #11 - Overdue Evaluations (Grace Period + Lockout)
**This will be tested later in the live walkthrough**
- [ ] **Grace period test:** Set a call's `evaluation_deadline` to yesterday (within 1 week ago). As an evaluator with a pending evaluation for that call:
  - [ ] Verify the evaluator dashboard shows the evaluation under "Overdue Evaluations" with an "Overdue" badge
  - [ ] Verify the dashboard shows the grace period warning message
  - [ ] Click through to the evaluation form - verify you see a red "Evaluation Overdue!" alert with grace days remaining
  - [ ] Verify you can still **submit** the evaluation (form is NOT locked)
- [ ] **Lockout test:** Set a call's `evaluation_deadline` to 8+ days ago. As an evaluator with a pending evaluation:
  - [ ] Verify the evaluation form shows "Evaluation Locked!" message mentioning the grace period has expired
  - [ ] Verify the form is **not editable** (no submit button, read-only display)
  - [ ] Verify the dashboard shows the evaluation with a "Locked" badge
- [ ] **Coordinator unlock:** Edit the call and extend the `evaluation_deadline` to the future. Verify the evaluator's form is unlocked again.
- [ ] **Email templates:** Verify 3 new templates exist:
  ```python
  # In Django shell
  from communications.models import EmailTemplate
  for t in ['evaluation_overdue', 'coordinator_overdue_evaluations', 'coordinator_evaluations_locked']:
      print(t, EmailTemplate.objects.filter(template_type=t).exists())
  ```

## Issue #6 - Feasibility Review Status Table
**Will be checked if full run later**

- [ ] As a **coordinator**, view an application that has been through feasibility review (`/applications/<id>/`)
- [ ] Verify you see a "Feasibility Review Status" table between Equipment Request and Scientific Content sections
- [ ] The table should show: Node, Status (Feasible/Not Feasible/Pending badge), Reviewer name, Date, Comments
- [ ] Verify the table shows correct status for nodes that have responded and "Pending" for those that haven't
- [ ] As a **regular applicant**, view your own application - verify the feasibility status table is **NOT visible** (coordinator-only)

## Repo Housekeeping

- [x] Verify the Word temp file `~$DIB-APP-application-form-coa-redib.docx` is no longer tracked by git
- [x] Verify `~$*` pattern is in `.gitignore`
- [x] Verify `add_feasibility_test_apps.py` has been moved to `scripts/add_feasibility_test_apps.py`

## General Checks

- [x] Run `python manage.py migrate` - no errors
- [x] Run `python manage.py makemigrations --check` - "No changes detected"
- [x] Run `python manage.py seed_email_templates` - all templates created/updated
- [x] Start the dev server with `python manage.py runserver` - no errors on startup
- [x] Navigate through the main flows (login, dashboard, calls, applications) - no broken pages
