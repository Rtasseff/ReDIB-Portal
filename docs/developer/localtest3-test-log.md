# localtest3 Manual Test Log — 2026-04-16

Walkthrough of the 11-phase manual-test protocol in
[localtest3-database-plan.md](localtest3-database-plan.md) using the sandbox
seeded by `python manage.py setup_localtest3_database --reset --yes`.

## Status legend
- PASS — worked as specified
- PASS* — worked with minor deviation (noted)
- FAIL — bug filed in table below
- SKIP — not exercised this pass

## Sandbox state at start
- 10 users (password `testpass123`, email pre-verified)
- 2 calls: `COA-LIVE-2026` (open), `COA-PAST-2025` (resolved)
- 16 applications: 10 LIVE-* + 6 PAST-*

Status distribution verified by sanity-check query (see top of session).

## Phases

### P1 Browse calls — PASS
User(s): anonymous / any.
URL: `/calls/`.
Expected: `COA-LIVE-2026` = Open, `COA-PAST-2025` = Resolved.

Notes:
- Both calls listed with the expected status labels.
- Nice-to-have logged under "Future enhancements" (equipment detail drill-in).

### P2 Application submission — PASS
User(s): `applicant1@test.redib.net`, then `applicant4@test.redib.net`.
- applicant1 → My Applications → **LIVE-001** (draft) → finish wizard → submit → expect status `submitted`.
- applicant4 (incomplete profile) → login → expect middleware redirect to `/profile/`.

Notes:
- 2a: Wizard steps 2–5 + declarations + submit all worked; status flipped to `submitted`.
- 2b: Middleware redirect to `/profile/` fired as expected.
- Nice-to-have logged: status/alert coloring should be role-relative (red = things *this viewer* needs to act on).

### P3 Feasibility review — PASS
User(s): `nc.cicbio@test.redib.net`, `nc.cnic@test.redib.net`.
- nc.cicbio: queue shows **LIVE-002**, **LIVE-003** (A side). Approve LIVE-002 → expect `pending_evaluation`. LIVE-003 A already approved.
- nc.cnic: queue shows **LIVE-003** (B side). Approve → expect aggregate `pending_evaluation`. Optional: exercise "Request edits" on LIVE-002 before approving.

Notes:
- 3a (nc.cicbio): queue showed **LIVE-001** (submitted in P2a → auto-advanced to `under_feasibility_review`) and **LIVE-002**. Approved LIVE-002 → transitioned to `pending_evaluation` ✅.
- LIVE-003 correctly **not** in nc.cicbio's queue because Node A was already approved (seed, -3d). Queue filters to `status='pending'` for the user's nodes (`applications/views.py:693-700`). Confirmed by user: node coordinators not seeing apps outside their pending actions is **by design**.
- 3b (nc.cnic): approved CNIC side → LIVE-003 aggregator transitioned the app to `pending_evaluation` ✅ (confirmed via shell: both FRs `approved`).
- **Deferred:** "Request edits" flow on a feasibility review — not exercised yet; revisit later with a fresh test app.

### P4 Evaluator assignment — PASS
User(s): `coordinator@test.redib.net`.
- Coordinator runs per-call auto-assign on COA-LIVE-2026 (not per-app — balances load across all `pending_evaluation` apps at once; COI enforced).

Notes:
- Entering P4 state: 3 apps in `pending_evaluation` (LIVE-002, LIVE-003, LIVE-004 — LIVE-002/003 arrived via P3; LIVE-004 was seeded). LIVE-005/006 already had seeded evaluator assignments.
- Auto-assign distributed LIVE-002, LIVE-003, LIVE-004 across `eval.clinical`, `eval.radio`, `eval.preclinical` with COI enforced.
- **LIVE-003 got only 1 evaluator (eval.preclinical, cross-area)** because applicant2's org (Instituto de Investigacion Sanitaria) matches both eval.clinical and eval.radio → both COI-blocked. Auto-assigner fell back to the only non-COI candidate despite area mismatch. Working as intended; the 3-evaluator sandbox roster simply can't supply 2 non-COI matches for every app.
- **LIVE-004 cannot accept a 3rd evaluator:** the only remaining candidate (eval.preclinical) shares applicant3's org → UI correctly refuses with COI error. Verified.
- Manual-assign code (`evaluations/views.py:268-333`) enforces COI only (same-org block), not area match — area is `auto`-assigner's responsibility; coordinator can override area manually.
- **Note for future seeds / future version:** a 10-user sandbox with 3 evaluators / 2 orgs will always leave some multi-applicant configurations undersupplied after COI filtering. A future localtest4 could add 1-2 more evaluators across additional orgs if this constrains tests.

### P5 Evaluation scoring — PASS
User(s): `eval.preclinical@test.redib.net`, `eval.clinical@test.redib.net`, `eval.radio@test.redib.net`.
- **LIVE-005**: both evaluators submit scores → expect auto-transition to `evaluated`.
- **LIVE-006**: evaluator 1 already scored; second evaluator submits → same auto-transition.

Notes:
- LIVE-005: both evaluators scored; status → `evaluated`, final_score=9.00 (6 + 12) ✅.
- LIVE-006: eval.radio submitted `denied` with a comment; status → `evaluated`, final_score=4.50 (8 + 1) ✅.
- During this phase we surfaced and fixed 4 bugs (see bug table #1–#4: score-0 display, completed/assigned denominator, seed-marker comments, denial-requires-comment).
- Evaluator dashboard correctly separates pending vs completed assignments (`evaluations/views.py:40-41`) — completed evaluations move out of the "to do" view into a recent-completed section. Confirmed not a bug.
- LIVE-002, LIVE-003, LIVE-004 (now also `under_evaluation` after P4) still have pending evaluations. Not exercised this pass; can be scored later if we revisit P5 after other phases.

### P6 Node resolution — PASS (with rule change landed)
User(s): `nc.cicbio@test.redib.net`, `nc.cnic@test.redib.net`.
- **LIVE-007** (multi-node): nc.cicbio submits one decision, nc.cnic submits another. Try mixed (accept + waitlist) first.
- **LIVE-008** (competitive funding, low score): confirm Reject option is disabled/blocked for NC.

Notes:
- 6a (LIVE-007): multi-node resolution worked, aggregator behaved as expected ✅.
- 6b (LIVE-008): original "reject is blocked for competitive funding" behavior confirmed. User pointed out the real-world rule is more nuanced — an evaluator's `denied` recommendation should allow the NC to reject. See bug #5.
- Post-fix: LIVE-008 now has `has_any_denied_evaluation=True` (both seeded evaluators recommended denied, sum=4 triggers the `<7` denial rule in seed), so with the new logic the NC **can** reject LIVE-008. User should re-test the resolution form on LIVE-008 to confirm the reject radio is now present.

### P7 Acceptance — _pending_
User(s): `applicant2@test.redib.net`, `applicant3@test.redib.net`.
- applicant2 → **LIVE-009** → Accept (or Decline). Watch console for handoff email.
- applicant3 → **LIVE-010** (waitlist) → Accept. Status stays `pending` until NC promotes.

Notes:

### P8 Waitlist promotion — _pending_
User(s): `nc.cicbio@test.redib.net`.
- Access Tracking → **LIVE-010** → "Mark as Accepted" → expect transition + handoff email.

Notes:

### P9 Access tracking — PASS
User(s): `nc.cicbio@test.redib.net` or `applicant1@test.redib.net`.
- **PAST-001** → mark each equipment block complete with actual hours used.

Notes:
- Mark Complete + Log Hours form loaded cleanly; submitting actual hours flipped status `accepted` → `completed`, set `is_completed=True`, stamped `completed_at`, saved `actual_hours_used` ✅.
- After completion the green button drops off and the gray "Completed M d, Y" badge appears in the Actions column.
- UX nit fixed mid-phase: the Completed status badge previously used `bg-info text-dark` (light blue / dark text), inconsistent with the other terminal states (Expired, Declined, Rejected) which all use gray. Changed to `bg-secondary` in the shared `templates/includes/status_badge.html` so completed apps look like the other terminal states everywhere the badge is used. See bug #9.

### P10 Publications — PASS
User(s): `applicant2@test.redib.net`.
- **PAST-002** → view existing publication → add new one with DOI + ReDIB acknowledgment ticked.

Notes:
- Found and fixed bug #10 (dropdown filtered to `accepted`, missing completed apps) and bug #11 (no Add Publication entry point on My Applications) before the test could complete cleanly.
- After fixes: My Applications shows the green "Add Publication" button for PAST-002, deep-links to the submit form with PAST-002 pre-selected, dropdown shows only completed apps. New publication created and listed alongside the seed publication ✅.
- Also tightened the form (bug #12): all fields except `acknowledgment_text` are now required.

### P11 Reports — DEFERRED
User(s): `coordinator@test.redib.net`.
- Statistics dashboard → review counts per status / per call.
- Export Excel for **COA-PAST-2025** → confirm download.

Notes:
- Deliberately deferred. The data layer captures everything needed; the reports/exports surface can be reshaped later with input from the people who actually submit audit reports and use the export. Since all state is in the DB and can be queried any time (even after a call closes), there's no urgency to lock the UI now.
- When we revisit: pull the audit-side users into the conversation first, then iterate on the templates/exports (`reports/views.py`, `reports/exports.py`).

## Bugs found

| # | Phase | Symptom | Severity | Resolution |
|---|-------|---------|----------|------------|
| 1 | P5 (coordinator app-detail view, Evaluation Summary card) | Scores of `0` rendered as `—` because template used `\|default:"—"`, which treats 0 as falsy. Made real zero scores indistinguishable from "not scored yet". | Minor | Fixed: changed 6 score cells + `total_score` + avg/min/max to `\|default_if_none:"—"` in `templates/applications/detail.html:215-253`. |
| 2 | P5 (same card) | "Completed evaluations" showed only the completed count (e.g. `1`) with no denominator — no context whether 1/1, 1/2, 1/3. | Minor | Fixed: added `assigned` to context dict (`applications/views.py:144`) and render as `{count}/{assigned}` in `templates/applications/detail.html:211`. |
| 3 | P5 (evaluation form) | Incomplete seeded evaluations pre-filled the `comments` textarea with "Seed evaluation by <email>"; if an evaluator submitted without editing, that marker text was saved as a real comment. | Moderate | Fixed `_add_evaluation` in `core/management/commands/setup_localtest3_database.py:620-648` to only inject the seed-marker comment when scores are supplied (completed seed eval); incomplete seeded evals now start with empty comments. Cleared the one lingering offender in the current DB (LIVE-006 eval.radio, id=28). |
| 4 | P5 (evaluation form) | Selecting "Denied" and submitting with no comment was accepted — evaluators could deny without explaining why. | Moderate | Mirrored the `FeasibilityReviewForm` pattern in `evaluations/forms.py`: `clean()` now raises "Please provide comments explaining why the application is denied." when `recommendation='denied'` and comments are blank. Updated comment field label from "Comments (optional)" → "Comments" and help text to "Required when the recommendation is Denied." |
| 5 | P6 (node resolution) | Competitive-funding applications were *unconditionally* protected from rejection at the resolution phase. The real-world rule is that an NC may reject a competitively-funded application **only if at least one evaluator recommended Denied** — the evaluator's independent denial provides the grounds. | Major (business-rule correctness) | Implemented. Added `Application.has_any_denied_evaluation` property (`applications/models.py:450-464`). Relaxed the reject-block in four places (`NodeResolutionForm` + `ApplicationResolutionForm` in `applications/forms.py`, `NodeResolutionService.apply_node_resolution` in `applications/services/node_resolution.py:177-188`, `ApplicationResolutionService.apply_resolution` in `applications/services/resolution.py:97-107`). View passes the flag to the form (`applications/views.py:1586-1587, 1644-1645`). Documented in `CLAUDE.md` (Application Workflow States → Competitive funding & reject protection) and corrected the outdated line in `docs/USER_GUIDE.md:121-125`. `python manage.py check` clean. |
| 6 | P6 (seed data inconsistency) | Seeded apps had a `funding_agency_obj` set on every application but `has_competitive_funding=False` on most — violating the real-world invariant that a funding agency is set IF AND ONLY IF the application is competitive. Surfaced when the user expected LIVE-005 (with ERC agency listed) to be reject-protected and it wasn't. | Moderate (test-fixture realism) | Enforced invariant inside `_base_application_fields` in `core/management/commands/setup_localtest3_database.py:535-554`: when `agency=None`, sets `has_competitive_funding=False`, `project_type='institutional'`, blank `project_code`; when `agency` is provided, sets `has_competitive_funding=True` and derives `project_type` from the agency. Removed the now-redundant `competitive=True` kwarg from LIVE-008's seed call. Flipped PAST-003, PAST-005, PAST-006 to non-competitive (pass `agency=None`) for variety. Patched the live DB to match (set flag=True on 11 apps with agencies; cleared agency + reset fields on the 3 non-competitive PAST apps). Final audit: 13 competitive, 3 non-competitive, 0 invariant violations. |
| 7 | P7 (applicant My Applications + Dashboard) | Waitlist (`status='pending'`) applications had no Accept/Decline action button on either My Applications or the Dashboard, despite the backend (`application_acceptance` view) explicitly supporting both `accepted` and `pending` statuses. Applicants on a waitlist had no UI path to accept the offer. The `accepted` status was also missing an action button on My Applications (only View + Continue-for-drafts existed). | Major (blocked workflow) | Added Accept/Decline buttons in both templates, gated on `status in ('accepted','pending') and accepted_by_applicant is None`. Also added the missing "Pending (Waitlist)" status badge on the dashboard for visual consistency. Files: `templates/applications/my_applications.html:58-77`, `templates/core/dashboard.html:63-69, 76-84`. |
| 8 | P7 (NC access tracking page) | The Actions column already contained the right buttons (Mark as Accepted for waitlist promotion, Mark Complete for active apps), but they were visually drowned out by an adjacent "Completed" column whose only content was "In Progress" / "—" for non-completed apps — pure noise. Users were missing the action buttons. | UX (visibility) | Dropped the standalone "Completed" column in `templates/access/access_tracking.html`. Folded the completion badge into the Actions column. Renamed buttons for clarity: "Mark as Accepted" → **"Promote to Accepted"** (waitlist), "Mark Complete" → **"Mark Complete + Log Hours"**. Verified server-render: LIVE-009/PAST-001 show Mark-Complete; LIVE-010 shows Promote. |
| 9 | P9 (status badge styling) | Completed apps showed up with a light-blue background / dark-text badge, inconsistent with the other terminal states (Expired, Declined, Rejected — all gray). For node coordinators, completed apps are off the active mental load and should look the same as other terminal states. | UX (consistency) | `templates/includes/status_badge.html`: changed Completed from `bg-info text-dark` to `bg-secondary`, matching the rest of the terminal-state palette. Updated the palette comment block to reflect that grey now covers all terminal states (no more "blue = informational, complete"). |
| 10 | P10 (publication submit form) | The "Which ReDIB application is this publication related to?" dropdown filtered to `status='accepted'` + `accepted_by_applicant=True`, so it showed in-progress accepted apps (e.g. LIVE-009) and excluded actually-completed apps (PAST-002). Publications can only meaningfully be reported against completed access. | Major (workflow) | Fixed `PublicationForm.__init__` in `access/forms.py:49-60`: queryset now filters to `status='completed'`, ordered by `-completed_at`. Verified server-side: applicant2 now sees only PAST-002 in the dropdown. |
| 11 | P10 (My Applications discoverability) | A user with a completed application had no obvious entry point to add a publication from My Applications — the only path was Dashboard → My Publications → Submit Publication, which buried the action. | UX (discoverability) | Added a green **"Add Publication"** button in `templates/applications/my_applications.html` for `status == 'completed'` apps. The button deep-links to `/access/publications/submit/?application=<id>` so the application dropdown is pre-selected. New `publication_submit` view honors the `?application=<id>` query param to pre-populate `initial['application']`. The form's queryset still gates which apps the user can actually attach to, so the deep-link can't be abused. |
| 12 | P10 (publication submit form completeness) | Most publication fields were optional at the form level (`authors`, `doi`, `journal`, `publication_date` all `blank=True` on the model), so users could submit a publication with virtually no metadata. | Minor (data quality) | `PublicationForm.__init__` now sets `required=True` on `application`, `title`, `authors`, `doi`, `journal`, `publication_date`, and `redib_acknowledged` (the last forces the checkbox to be ticked). Only `acknowledgment_text` remains optional. Added matching `*` indicators in `templates/access/publication_submit.html` for the four newly-required fields. |

## Future enhancements (nice-to-haves, not current-version bugs)

> **Now tracked in [`backlog.md`](backlog.md).** The two items below have
> been copied into the `UX polish` section there (entries #1 and #2).
> New ideas surfaced after this walkthrough should go directly into
> `backlog.md`, not here. The list is preserved for historical context.

| # | Phase | Idea | Priority |
|---|-------|------|----------|
| 1 | P1 (calls listing) | Let users see equipment details from the calls page (click or hover on equipment — UI TBD). Currently equipment is listed by name only without a way to drill in. | Low |
| 2 | P2 (applicant views) | Make status/alert coloring role-relative: red should indicate something *the current viewer* needs to do (not just a globally "bad" state). Today coloring is the same regardless of which role is looking. | Low |

