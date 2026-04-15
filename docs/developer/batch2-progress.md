# Batch 2 Progress

Tracks implementation of issues #14–#28 against the plan in
`batch2-implementation-plan.md`. Branch: `fixes-batch-2`.

## Close-only (no code changes)

| Issue | Outcome |
|-------|---------|
| #16   | Not reproducible in current code — `applicant_entity` is pulled from each user's own `user.organization` on create/edit. `data/users.tsv` has 5 distinct orgs. Almost certainly a stale-fixture artefact. Verify on next full test pass; close if green. |
| #21   | Already fixed by batch-1 commit `6a8832b`. `_send_handoff_email` sends one email with `to=[applicant]` and `cc=[node_coordinators]`. Close. |
| #23   | Confirmed safe: all downstream behaviour re-reads current Call date values on demand. Documented in `docs/developer/developer-notes.md`. Close. |

## Phase 1 — Batch 2-A: resolution email correctness + hours on reject

**Commit:** `190fadd` "Phase 1 / Batch 2-A: resolution email correctness + hours-on-reject"

Issues #22, #24, #25, #26, #28.

- `_trigger_resolution_notification` (services/node_resolution.py) and the
  `finalize_resolution` dispatch (services/resolution.py) no longer swallow
  exceptions — failures now surface through `logger.exception`.
- Every applicant-facing email (resolution bulk + single, handoff, feasibility
  complete / edits_requested, acceptance reminder, acceptance expired,
  publication follow-up, access reminder) now targets
  `application.applicant_email or application.applicant.email`.
- On `resolution == 'reject'`, `NodeResolutionService.apply_node_resolution`
  forces `RequestedAccess.hours_approved = 0` regardless of what the form
  posted, so rejected apps no longer show phantom approved hours on access
  tracking.
- `notify_coordinator_evaluations_complete` no longer includes ReDIB
  coordinators in the per-app recipient list (they're already covered by
  the daily `notify_coordinator_overdue_evaluations` task and the
  `coordinator_evaluations_locked` email on window close).

**New test file:** `tests/test_batch2_phase1.py` (4 tests, all pass).

## Phase 2 — Batch 2-C: shared status badge with sub-state colours

**Commit:** `1363b24` "Phase 2 / Batch 2-C: shared status-badge include with sub-state colours"

Issues #20, #27.

- New include `templates/includes/status_badge.html` disambiguates the
  post-resolution sub-states (Accepted — Awaiting Applicant, Active,
  Completed, Waitlist sub-states, Expired, Declined, Draft) with semantic
  colours.
- `templates/access/access_tracking.html` and `templates/calls/detail.html`
  both render the include so the palette stays in sync.

## Phase 3 — Batch 2-D: phase tracker + evaluation summary

**Commit:** `737d2c2` "Phase 3 / Batch 2-D: phase tracker + evaluation summary on app detail"

Issues #17, #18.

- `_build_phase_tracker()` helper in `applications/views.py` walks seven
  phases (Draft → Access) and marks each as complete/current/pending/
  terminal-fail. Template include at
  `templates/includes/phase_tracker.html` renders it as a horizontal
  stepper at the top of the application detail page.
- Coordinator / superuser view of `application_detail` now shows an
  Evaluation Summary card with per-evaluator scores across all six
  criteria, recommendations, completion timestamps, truncated comments,
  and header stats (count, average, min, max). Non-coordinator viewers
  still don't see it — blinding preserved.

## Phase 4 — Batch 2-B: full pending (waitlist) lifecycle

**Commit:** `d0c68f4` "Phase 4 / Batch 2-B: full waitlist lifecycle for pending resolutions"

Issue #19.

- Aggregation now sets `acceptance_deadline` for both `accepted` and
  `pending` resolutions; `finalize_resolution` does the same on the bulk
  path.
- `application_acceptance` view accepts both `status='accepted'` and
  `status='pending'`. On the waitlist path, accept records
  `accepted_by_applicant=True` but defers the handoff.
- `resolution_pending` email rewritten to match accepted structure with
  waitlist-specific copy, deadline display, and accept/decline call-to-
  action.
- `acceptance_form.html` branches on `is_waitlist` for headings, body,
  and button labels.
- New view `promote_waitlisted_application` (POST, node-coord or
  coordinator scoped). Promotes `pending + accepted_by_applicant=True`
  to `accepted`, refreshes `resolution_date`, clears
  `acceptance_deadline`, and fires resolution_accepted + handoff.
- New "Mark as Accepted" button in `access_tracking.html` rendered only
  for pending + applicant-accepted rows.
- `Application.VALID_TRANSITIONS['pending']` extended to include
  `declined_by_applicant` and `expired`.

**New test file:** `tests/test_batch2_phase4.py` (5 tests, all pass).

## Phase 5 — Batch 2-E: applicant form polish + reviewer declarations display

**Commit:** `56e4f83` "Phase 5 / Batch 2-E: applicant form polish + reviewer declarations view"

Issues #14 (parts 1, 4, 5), #15.

- `ORCID_VALIDATOR` and `PHONE_VALIDATOR` defined in `core/models.py` and
  attached to `User.orcid` / `User.phone`, plus the snapshot fields
  `Application.applicant_orcid` / `applicant_phone`.
- Six Step 4 scientific-content TextFields capped at 5000 chars
  (`Application.SCIENTIFIC_CONTENT_MAX_LENGTH`); prompts moved from
  placeholder to help_text so they stay visible while typing.
- New `Application.has_insurance` and `Application.has_informed_consent`
  booleans; Step 5 wizard shows them inside the Human Subjects Ethics
  block only when `uses_humans=True`. Neither is required — applicants
  can submit either way.
- Reviewer-side display updated in `feasibility_review.html`,
  `detail.html`, `preview.html`, and `application_pdf.html` to show all
  four human-subject declarations when `uses_humans=True`.
- Part 14.3 (subject areas) intentionally deferred — full 20-entry AEI
  list retained until leadership provides a short list.
- Issue #15 resolved by display-only changes; no reviewer-side
  checkboxes added (per locked-in decision — node coordinators use the
  existing "request edits" feasibility flow to get the applicant to
  update declarations).

**New test file:** `tests/test_batch2_phase5.py` (9 tests, all pass).

**Migrations:**
- `applications.0012_application_has_informed_consent_and_more.py`
- `core.0008_alter_historicaluser_orcid_and_more.py`

Both are field-metadata only (choices / validators / max_length) — no
data migration needed.

## Test suite state

Running `python manage.py test tests -v 2` on each phase produced the
same 11 pre-existing failures as on `main`; zero new regressions.

## Deployment checklist when this branch merges

1. `python manage.py migrate` — applies 0012 and 0008.
2. `python manage.py seed_email_templates` — refreshes the
   `resolution_pending` body with the waitlist-specific copy.
3. Re-run the manual test plan from `batch2-implementation-plan.md`.
4. Update `CLAUDE.md` to point at the next active branch (or back to
   `main`) and close issues #14–#28 (with any notes from #16 / #21 /
   #23 per the Close-only table above).
