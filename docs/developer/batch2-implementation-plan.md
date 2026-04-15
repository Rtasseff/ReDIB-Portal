# Implementation Plan: Issues Batch 2 (15 Issues)

## Context

A second round of user-testing feedback produced 15 open GitHub issues (#14 – #28). They cover resolution/hand-off emails, waitlist lifecycle, coordinator visibility into evaluations and workflow phase, a per-equipment hours bug on rejected applications, status colours on list views, and applicant-side form polish. Work is done on the `fixes-batch-2` branch. Development is local (SQLite + runserver); production DB will be wiped and reseeded when we deploy.

## Decisions locked in with the user

1. **#19 Pending (waitlist)** — full lifecycle: pending triggers an applicant accept/decline email with the same `acceptance_deadline` as accepted, but different body text. Once the applicant accepts the waitlist slot, a new node-coordinator-only "Mark as accepted" action promotes the application to the regular accepted lifecycle.
2. **#26 Recipient policy** — all resolution / handoff emails use `application.applicant_email` when present, falling back to `application.applicant.email`.
3. **#28 Evaluations-complete email** — drop the main ReDIB coordinator from the per-app send. The coordinator is already covered by `notify_coordinator_overdue_evaluations` (daily 09:45) and `coordinator_evaluations_locked` once the window closes, so nothing new is needed for the "evaluation period expired with outstanding evaluations" case — just verify those templates are seeded and triggered.
4. **#14.3 Subject areas** — keep all 20 AEI codes. Leadership will tell us when/if to trim.
5. **#14.5 Human-subjects extra declarations** — add `has_insurance` and `has_informed_consent` boolean fields on the Application model, shown in Step 5 only when `uses_humans=True`. Applicants can submit with or without them checked. Reviewer views (feasibility review, ReDIB-coordinator detail view) must display all four human-subject declarations (`uses_humans`, `has_human_ethics`, `has_insurance`, `has_informed_consent`). No reviewer-side checkbox, no new logic — node coordinators who want changes use the existing "request edits" flow on feasibility and explain in the comments. Applicants remain the only people who can modify their application.
6. **Phase order** — A (resolution/email correctness) → C (status colours) → D (coordinator detail enrichment) → B (pending lifecycle) → E (form polish + reviewer-display-only declarations).

## Progress Tracking

After each phase, update `docs/developer/batch2-progress.md` with:
- Issues completed (by number)
- Files modified
- Migrations created
- Any decisions made
- Phase-specific test results

This file serves as a recovery document if a session is interrupted and as a deployment checklist for production.

## Items closed without code changes

These are documented so they don't get re-opened.

### Issue #21 — Handoff email goes to applicant + node coordinators in the same email
Already fixed by batch-1 commit `6a8832b`. `_send_handoff_email` (applications/views.py:1091) sends one email with `to=[applicant]` and `cc=[node_coordinator_emails]`. Close with a pointer to the commit.

### Issue #16 — All apps from the same org (BioImaC)
Current code pulls `applicant_entity` from each user's own profile (views.py:166-174 and :208-217) and `data/users.tsv` has 5 distinct organizations. Almost certainly a stale-fixture artifact from the test session. Verify during the next full test pass; if not reproducible, close.

### Issue #23 — Editing call dates after publication
Confirmed safe. `submission_end` and `evaluation_deadline` are re-read live by every scheduled task and guard (`calls/tasks.py:22`, `evaluations/tasks.py:29,87,145`, `applications/views.py:459`). `execution_start` / `execution_end` are cosmetic. `Application.acceptance_deadline` is snapshot-by-design from the resolution date, not the call. We'll add a short note in `docs/developer/developer-notes.md` and close the issue.

---

## Phase 1 — Batch 2-A: Resolution / hand-off email correctness and hours-on-reject

Small, tightly related backend fixes. High impact, low risk.

### Issue #22 / #25 — Applicant not receiving resolution email

**Root cause:** `_trigger_resolution_notification` in `applications/services/node_resolution.py:341-348` wraps the task dispatch in `try / except: pass`, silently swallowing any failure (missing template, broker outage, programming error). Templates *are* seeded (batch-1 added `resolution_accepted/pending/rejected`), so the silent-pass is the main lever here.

- **File:** `applications/services/node_resolution.py` around line 341 — replace the bare `except: pass` with `except Exception` and call `logging.getLogger(__name__).exception(...)` so future failures surface in logs / Sentry.
- **File:** `applications/services/resolution.py` `finalize_resolution` — same pattern; add logging around the dispatch.
- **Verification:** run through the local test flow end-to-end (seed → submit → approve → resolve) and confirm an `EmailLog` row appears with `template__template_type='resolution_accepted'` and `status='sent'`. Add a lightweight integration test in `tests/test_phase6_node_resolution.py` (or similar) that asserts the email is queued when the final node resolves.

### Issue #26 — Resolution / hand-off emails should prefer `applicant_email`

- **File:** `applications/tasks.py` `send_single_resolution_notification_task` (~line 223) and `send_resolution_notifications_task` (~line 122) — change `recipient_email=application.applicant.email` to `recipient_email=application.applicant_email or application.applicant.email`.
- **File:** `applications/views.py` `_send_handoff_email` (~line 1120-1145) — same change on the `recipient_email` arg.
- **File:** any other call site that passes an `Application`-derived `recipient_email` (quick `grep 'applicant.email' --glob '**/*.py'` across the repo) — audit and apply the same fallback.
- **Test:** extend the handoff/resolution test to create an application where `applicant_email` differs from `applicant.email` and assert the email lands on the former.

### Issue #24 — Rejected apps show `Approved: hours_requested` on access tracking

**Root cause:** the template always renders an `<input required>` for hours_approved pre-filled with `hours_requested`; the view (`views.py:1369-1377`) parses it unconditionally; the service (`services/node_resolution.py:208-212`) writes it to the `RequestedAccess` row regardless of the resolution.

- **File:** `applications/services/node_resolution.py` `apply_node_resolution` (~line 208) — when the incoming `resolution == 'reject'`, set `req_access.hours_approved = 0` before `save()` for every item on that node, ignoring whatever the POST contained.
- **File:** `templates/applications/node_resolution/review.html` (~line 250) — small progressive-enhancement JS: when the reject radio is selected, disable and zero the per-equipment hours inputs so the UI reflects the saved state (purely cosmetic — the server authoritatively enforces zero).
- **Test:** assert after a reject resolution that `requested_access.hours_approved == 0` for every row on the rejecting node.

### Issue #28 — ReDIB coordinator gets per-app `evaluations_complete` email

- **File:** `evaluations/tasks.py` `notify_coordinator_evaluations_complete` (~line 438) — remove the ReDIB coordinator IDs from `recipient_ids`. Keep all node-coordinator logic, including the per-node URL we added in batch-1 (`da39147`).
- **Verify — no code change needed, just confirmation:** `notify_coordinator_overdue_evaluations` (evaluations/tasks.py:130) already runs daily at 09:45 and uses either `coordinator_overdue_evaluations` or `coordinator_evaluations_locked`. Both templates are seeded. That covers the "evaluations still outstanding when the window closes" case the user asked me to confirm.

### Commit boundary for Phase 1
One or two commits, roughly:
1. "Surface resolution/handoff email dispatch failures; prefer applicant_email" (#22, #25, #26)
2. "Zero hours_approved on node reject; drop ReDIB coord from per-app evals-complete" (#24, #28)

---

## Phase 2 — Batch 2-C: Status labels and colours on list views

Two templates, one small helper. No model changes. Low risk.

### Issue #20 — Access-tracking colour palette

Current: `bg-success` (accepted), `bg-warning` (awaiting), `bg-danger` (rejected *and* pending), `bg-secondary` (declined), `bg-info` (fallback).

Target (per reporter):
| State | Reason | Colour |
|-------|--------|--------|
| Accepted (applicant has accepted) | Moving forward | Green |
| Awaiting Acceptance | Applicant action | Amber |
| Pending (Waiting List) | ReDIB action needed | Red |
| Rejected | Terminal, no action | Grey |
| Completed | Terminal, no action | Grey |

- **File:** `templates/access/access_tracking.html` lines ~44-56 — rewrite the badge block. Extract a small template include or filter (e.g. `templates/includes/status_badge.html`) to centralise the mapping since #27 reuses it.

### Issue #27 — Call-detail applications table disambiguation

Current: every row is `<span class="badge bg-secondary">{{ app.get_status_display }}</span>`.

Target mapping (from the issue, polished):
| Underlying state | Label | Colour |
|---|---|---|
| `status='draft'` | Draft | Grey |
| `status='submitted' / 'under_feasibility_review' / 'pending_evaluation' / 'under_evaluation'` | current display label | Neutral blue |
| `status='evaluated'` | Evaluated | Blue |
| `status='accepted'` + `accepted_by_applicant is None` + `handoff_email_sent_at is None` | Accepted — Awaiting Applicant | Amber |
| `status='accepted'` + applicant accepted + handoff sent + not completed | Active | Green |
| `status='pending'` | Waitlist | Amber (distinct shade from Awaiting Applicant) |
| `status='expired'` | Expired | Muted red |
| `status='rejected' / 'rejected_feasibility' / 'declined_by_applicant'` | current display | Red |
| `is_completed=True` | Completed | Blue |

- **File:** `templates/calls/detail.html` lines ~178-190 — reuse the `status_badge` include from Issue #20 so both views stay in lock-step. Add the sub-state logic (`accepted_by_applicant`, `handoff_email_sent_at`, `is_completed`) to the include.
- **Stretch, if time allows:** sort the applications table so "action-needed" rows bubble to the top. Not required to close #27, but the reporter called it out.

### Commit boundary for Phase 2
Single commit: "Status badge palette for access tracking and call detail".

---

## Phase 3 — Batch 2-D: Enrich `application_detail` for coordinators

Two issues, same template and view.

### Issue #17 — Show evaluation results on the detail page

- **File:** `applications/views.py` `application_detail` (line ~38). In the `is_coordinator` branch, prefetch evaluations:
  ```python
  application.prefetched_evaluations = application.evaluations.select_related(
      'evaluator'
  ).order_by('completed_at')
  context['evaluations_summary'] = { ... average, min, max, recommendations ... }
  ```
- **File:** `templates/applications/detail.html` — under (or above) the existing Feasibility Review Status card, add an "Evaluations" card (only when `is_coordinator` and there is at least one completed evaluation). Show:
  - Final / average score, high/low, count complete
  - Per-evaluator row: evaluator name, scores on all 6 criteria, recommendation, completed_at, truncated comment (with expand)
  - Hide this card for non-coordinator viewers even when they have access (node coords should not see evaluator comments here — same blinding as today).

### Issue #18 — Phase tracker at top of detail page

- **File:** `templates/applications/detail.html` — add a horizontal stepper at the very top of the page (before the existing Application Timeline card). One cell per phase with a completed / current / pending style. Suggested phases, derived from `application.status`:
  1. Draft
  2. Submitted
  3. Feasibility Review
  4. Evaluation
  5. Resolution
  6. Acceptance
  7. Access (active / completed)
- Behaviour:
  - Each cell is either "complete" (green check), "current" (amber/blue, bold), or "upcoming" (grey).
  - Terminal non-success states (rejected, expired, declined) short-circuit the tracker with a terminal cell.
- **File:** `applications/views.py` `application_detail` — compute the phase list into `context['phase_tracker']` so the template stays dumb. Reuse existing status constants; don't introduce a new enum.
- **Optional include:** `templates/includes/phase_tracker.html` so future pages can drop it in.

### Commit boundary for Phase 3
Two small commits: "Show evaluation summary on application detail" (#17), "Add phase tracker to application detail" (#18).

---

## Phase 4 — Batch 2-B: Pending (waitlist) full lifecycle

Largest change in the batch — promotes pending from a dead-end state to a full lifecycle mirror of accepted.

### Design recap

Per the locked-in decision, pending flows like this:

1. Node coord submits `pending` on last involved node → aggregator sets `application.resolution='pending'`, `application.status='pending'`, and `application.acceptance_deadline = resolution_date + 10 days` (same as accepted).
2. Applicant gets a `resolution_pending` email with accept/decline link, same deadline countdown as accepted. Body text makes it clear this is a waitlist offer: "You have been placed on the waitlist. If time becomes available, a node coordinator will contact you to schedule." plus the reply-by date.
3. Applicant clicks accept. `accepted_by_applicant=True`, but `status` *stays* `pending` (waitlist). Applicant declines → `status='declined_by_applicant'`, same terminal state as for accepted.
4. Access-tracking page shows the application as "Pending (Waiting List)" (red, per #20).
5. Node coordinator sees an extra row-action button "Mark as accepted" on access-tracking (applicant does not). Clicking transitions `status='pending' → 'accepted'`, sets `resolution='accepted'` (or keeps `pending` plus a new flag — TBD below), clears any stale deadlines, and fires the `resolution_accepted` email AND the normal handoff flow as if the application had been accepted from the start.

### Model & data changes

- **File:** `applications/models.py` `VALID_TRANSITIONS` — confirm `pending → accepted` is present (it already is per review). Add `pending → declined_by_applicant`.
- **File:** `applications/models.py` — add a helper method `Application.promote_from_waitlist(actor)` that:
  1. Validates current state is `pending` and `accepted_by_applicant is True`.
  2. Transitions `status='accepted'`, sets `resolution='accepted'`, refreshes `acceptance_deadline = now + 10 days` (or keeps the prior one — decide during implementation; I lean "refresh" since the applicant already agreed).
  3. Dispatches the existing `send_single_resolution_notification_task` with the accepted template (which now sends to `applicant_email` per Phase 1) and triggers `_send_handoff_email`.
  4. Writes a `simple_history` entry.
- **Migration:** none required — uses existing fields.

### Services / aggregation

- **File:** `applications/services/node_resolution.py` — `aggregate_resolution` currently sets `acceptance_deadline` only when the aggregated resolution is `accepted` (line ~310). Extend so `pending` also sets `acceptance_deadline = resolution_date + 10 days`. Same for `applications/services/resolution.py` if the bulk-finalize path sets deadlines separately.
- **File:** `applications/services/resolution.py` `finalize_resolution` — ensure the email dispatch path fires for pending too (it does — `template_type=f'resolution_{resolution}'`).

### Applicant acceptance view

- **File:** `applications/views.py` `application_acceptance` (~line 951) — relax the status guard from `status == 'accepted'` to `status in ('accepted', 'pending')`. The existing accept / decline logic handles both: `accepted_by_applicant=True` on accept, `status='declined_by_applicant'` on decline.
- Accept semantics for a pending app: do NOT trigger handoff (no active slot yet) — only mark `accepted_by_applicant=True` and show the applicant a "You are on the waitlist — a coordinator will contact you if a slot opens" message. The handoff happens later at promotion time.

### Node-coordinator promote UI

- **File:** `applications/views.py` — new view `promote_waitlisted_application` (POST-only, `@role_required('node_coordinator', 'coordinator')`). Scope: request.user must have a node_coordinator role on at least one node with equipment in the application. Body calls `application.promote_from_waitlist(request.user)`.
- **File:** `applications/urls.py` — add `path('<int:pk>/promote/', views.promote_waitlisted_application, name='promote_waitlisted')`.
- **File:** `templates/access/access_tracking.html` — in the "Actions" column, when `app.status == 'pending' and app.accepted_by_applicant` and the current user is a node coord for an involved node, render a POST-form button "Mark as accepted". Keep the CSRF token.

### Email template

- **File:** `communications/management/commands/seed_email_templates.py` — verify `resolution_pending` template exists (from batch-1 it does). Edit the body to match the decision: mirror the accepted template's structure but replace the "work with node coordinator to schedule" lines with "you have been placed on the waitlist. A coordinator will contact you if a slot opens." Keep the accept/decline call-to-action and the deadline countdown.

### Tests

- Integration test: full pending → applicant accept → node coord promote → handoff email flow.
- Edge: applicant declines the pending offer → status lands on `declined_by_applicant`.
- Edge: promote attempted by non-node-coord → 403.
- Edge: promote attempted when `accepted_by_applicant is False` → 400 with a helpful message.

### Commit boundary for Phase 4
Two commits, roughly:
1. "Pending resolution sets acceptance_deadline and invites applicant acceptance"
2. "Node coordinator can promote waitlisted applications to accepted"

---

## Phase 5 — Batch 2-E: Applicant form polish + reviewer-side declarations display

Touches the applicant wizard (model + migration + form + templates) and the reviewer views (display only).

### Issue #14.1 — ORCID format validation

- **File:** `core/models.py` `User.orcid` — add a `RegexValidator` with pattern `^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$`, `message="ORCID must be in the format XXXX-XXXX-XXXX-XXXX"`.
- **File:** `core/forms.py` ProfileForm — the validator propagates automatically, but add a `help_text` showing the expected format.
- The `Application.applicant_orcid` snapshot field — add the same validator since it accepts arbitrary text today.
- **Migration:** yes (adds validators to field definition; run `makemigrations`).

### Issue #14.1 — Phone validation

- **File:** `core/models.py` `User.phone` — add a loose regex validator: `^[\d\s()+\-.]{5,}$`, `message="Phone numbers should contain only digits, spaces, and + ( ) - ."`.
- Apply the same validator to `Application.applicant_phone`.
- **Migration:** yes.

### Issue #14.4 — Step 4 scientific content: max_length + visible help text

- **File:** `applications/models.py` — the six scientific-content fields are `TextField` today (unbounded). Cap each at `max_length=5000` (form + model). Keep them TextField so they stay multi-line-capable; set `max_length` at the field, which Django will enforce on `full_clean`.
- **File:** `applications/forms.py` `ApplicationStep4Form` — for each of the six fields, move the placeholder text into `help_text` so the prompt stays on screen while the user is typing. Keep a short placeholder too if it adds value.
- **File:** `templates/applications/wizard_step4.html` — ensure `help_text` is rendered above/below the field label (Bootstrap `.form-text`).
- **Migration:** yes (max_length).

### Issue #14.5 — Human-subjects extra declarations (applicant side)

- **File:** `applications/models.py` — add two booleans:
  ```python
  has_insurance = models.BooleanField(default=False, help_text="Civil liability insurance in place")
  has_informed_consent = models.BooleanField(default=False, help_text="Informed consent protocol ready")
  ```
- **File:** `applications/forms.py` `ApplicationStep5Form` — add both to `Meta.fields`. Do NOT mark them required; do NOT add cross-field validation tying them to `uses_humans`. Applicants can submit with or without.
- **File:** `templates/applications/wizard_step5.html` — render both checkboxes inside the "Human subjects" sub-block, visible only when the applicant has ticked `uses_humans` (use the same progressive-enhancement pattern already used for `has_human_ethics`).
- **Migration:** yes.

### Issue #14.2 — Subject-area simplification

Decision: no action this batch. Keep the full 20-entry `SUBJECT_AREAS` list. If leadership wants to trim, they provide the short list and we revisit.

### Issue #15 + reviewer display of the four declarations

No new reviewer-side checkboxes and no new logic per the locked-in decision. The work is purely display:

- **File:** `templates/applications/feasibility_review.html` — in the Declarations card, when `application.uses_humans` is true, show four rows (Human subjects: Yes, Ethics approval: Yes/No, Insurance: Yes/No, Informed consent: Yes/No). Use a small badge style matching the existing ethics row.
- **File:** `templates/applications/detail.html` — same treatment in the coordinator-view Declarations section.
- **File:** `templates/applications/application_pdf.html` — same on the PDF so reviewers see the full declared state there too.
- **File:** `templates/applications/preview.html` — show to the applicant in their own preview for consistency.
- No form changes on the reviewer side. Node coordinators who want changes use the existing "request edits" action on feasibility with comments.

### Commit boundary for Phase 5
Two or three commits:
1. "Add ORCID and phone regex validators on User and Application"
2. "Cap Step 4 fields at 5000 chars and keep prompts visible via help_text"
3. "Add insurance and informed-consent declarations; show all four human-subject flags in reviewer views"

---

## Documentation and close-out

After all phases:

- Update `docs/developer/batch2-progress.md` with each phase's commit hashes, migration names, and test results.
- Add a short note to `docs/developer/developer-notes.md` covering the "editing call dates is safe" finding from #23 so it's not re-investigated later.
- Update `CLAUDE.md` to point at `fixes-batch-3` (or back at `main`) once this batch merges.

## Manual test plan

One scenario per issue — run before merging to main.

| # | Scenario |
|---|---|
| 14 | Profile: enter letters in ORCID → see validation error. Enter letters in phone → see validation error. Apply: Step 4 shows help text under each of the 6 fields and 5000 character cap is enforced. Step 5: with `uses_humans=True`, the insurance and informed-consent boxes appear; submit with them unchecked — application saves. |
| 15 | As a node coordinator on an application with `uses_humans=True`, open the feasibility review page. Verify the Declarations card shows Human subjects / Ethics / Insurance / Informed consent with correct Yes/No states. Verify there are no new checkboxes on the reviewer form. |
| 17 | As ReDIB coordinator, open a resolved application's detail. Verify the Evaluations card shows average score, per-evaluator scores, recommendations, and comments. |
| 18 | Same page: verify the phase tracker at the top shows completed / current / pending state for every phase correctly for an application at each stage. |
| 19 | End-to-end: submit, approve feasibility, evaluate, then have a node coord resolve as pending. Applicant receives waitlist email with deadline. Applicant clicks accept link → sees waitlist confirmation (not handoff). Node coord clicks "Mark as accepted" on access tracking → applicant receives resolution_accepted email and handoff email to applicant + node coords. |
| 20 | Access tracking page shows correct colours: accepted=green, awaiting=amber, pending=red, rejected=grey, completed=grey. |
| 21 | (close-only) verify the current handoff email flow matches batch-1 behaviour. |
| 22 / 25 | Same end-to-end as 19 but with `accepted` resolution. Verify `EmailLog` contains a `resolution_accepted` row with `status='sent'` addressed to the applicant_email. |
| 23 | (close-only) edit `submission_end` on an open call to a past date → applicants see "call closed". Edit back to the future → they can apply again. |
| 24 | Resolve a node on an application as reject. Verify RequestedAccess rows for that node have `hours_approved=0`, and the access tracking page shows "0 h" / "—" for those rows. |
| 26 | Submit an application where `applicant_email` differs from the user's account email (use the form). Trigger resolution. Verify the resolution email lands on `applicant_email`. |
| 27 | Call detail applications table: create apps in each sub-state (awaiting-applicant, active, completed, waitlist, expired, rejected, draft) and verify the colour + label is distinct for each. |
| 28 | Complete all evaluations on an application. Verify ReDIB coordinators receive NO per-app evaluations_complete email. Verify node coords still receive theirs with the per-node URL. Separately: let an evaluation period expire with outstanding evaluations and confirm the ReDIB coordinator receives the `coordinator_evaluations_locked` email. |
