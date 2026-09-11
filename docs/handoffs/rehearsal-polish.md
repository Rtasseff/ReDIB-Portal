# Handoff — `feature/rehearsal-polish`

<!-- Copy of docs/developer/handoff-template.md, seeded by scripts/new-worktree.sh.
     Lives at docs/handoffs/rehearsal-polish.md on the branch. Keep "Status" current. -->

| | |
|---|---|
| Branch | `feature/rehearsal-polish` |
| Worktree dir | `/home/rtasseff/projects/ReDIB-Portal-wt/rehearsal-polish` |
| Base | `main` @ `53c4fae` |
| Created | 2026-09-10 |
| Runserver port | 8002 |
| Handoff session | `main` checkout at `~/projects/ReDIB-Portal/` |
| Suggested model | **Sonnet** (`/model sonnet`) — every item is a 1–3 file change whose decision is already made below |

Read this first, then `CLAUDE.md`, then `docs/README.md`. This directory is
a git worktree: it *is* this branch — do not `git checkout` another branch
here (see `docs/developer/worktrees.md`).

**Development document.** These are instructions for the agent session working
in this worktree. Once the branch merges, this file lands on `main` as a
record — on the production VPS it is history, not a task list.

## Goal

The dress rehearsal of 2026-09-08 (`docs/developer/round-october-2026.md`
§ 4.7a and § 4.7c) walked the whole call lifecycle in the UI and filed
fourteen findings, backlog **#66–#79**. Three sat on the announce-date critical
path and went inline on `main` (`53c4fae`: #66, #68, #72). Two change workflow
*state* and have their own bucket (`rehearsal-guards`: #73, #74). This branch
takes the other **nine** — display, wording, harness and observability fixes
that make what the portal *shows* match what it *does*.

Nothing here changes a workflow transition, sends a new email, adds a model
field, or needs a migration. The portal is small and the last call went well
enough; the bar for every item is **the smallest change that makes the screen
honest**, not the design a large system would want. If an item seems to need
more than what is written below, stop and ask (§ Questions) rather than build it.

## Scope

**In** — nine items, **one commit each**, in this order (cheapest first, the
one with the most moving parts last):

| | Backlog | What |
|---|---|---|
| P1 | #77 | Feasibility queue's "Your Nodes" card renders an empty badge |
| P2 | #78 | Blind evaluation form shows an always-empty "Project Title: —" |
| P3 | #70 | Apple Silicon WeasyPrint line in two docs |
| P4 | #75 | Competitive-funding banner says "cannot reject" exactly when they can |
| P5 | #79 | Resolution dashboard's empty state hides calls that are only gated |
| P6 | #67 | After a call closes, the wizard stays fully open and says nothing |
| P7 | #69 | `check_call_deadlines` reports "0" on the run that opens the call |
| P8 | #71 | Three rehearsal-harness artefacts that read as portal bugs |
| P9 | #76 | Auto-assign fills an application with non-matching evaluators and says nothing |

**Out** (do not do here):
- **#73, #74** — `rehearsal-guards` bucket.
- **#80** (completion reminders, paused in prod) — `rehearsal-guards` / Ryan.
- **#63** (evaluator capacity) — Ryan's decision; P9 only makes the shortfall *visible*.
- **#54** (a UI path to reopen a closed call), **#64**, **#41** — not this round.
- The picking logic in `evaluations/tasks.py` `assign_evaluators_to_call` — P9
  must not change what auto-assign chooses.
- Any refactor, new email template, new setting, or migration.

## Items

Each backlog row in `docs/developer/backlog.md` has the exact file:line and
the rehearsal evidence; the decisions below are what to build.

### P1 — #77 Feasibility queue "Your Nodes" badge

`applications/views.py` ~985–1003, `feasibility_queue`. `my_nodes` is a
`values_list('node_id', flat=True)` queryset of **ints**, passed to the
template as `user_nodes`; `templates/applications/feasibility_queue.html:24`
renders `{{ node.code }} - {{ node.name }}` against them, so the node
coordinator sees a bare `-`. Keep `my_nodes` for the `node_id__in` filter and
pass `Node.objects.filter(pk__in=my_nodes).select_related('organization')` as
`user_nodes` (import `Node` from `core.models` if the module doesn't already).
No template change — it is already written against `Node` objects. The
node-resolution queue (`~:2396`) does this right; match it.
**Test:** log in as a node coordinator of one node, GET the queue, assert
`"<CODE> - <Name>"` is in the response.

### P2 — #78 Blind form "Project Title: —"

`templates/evaluations/evaluation_form.html:63`. `project_name` is withheld
from evaluators on purpose (`evaluations/utils.py:141`), so the row always
prints the em-dash placeholder and reads as "the applicant left it empty".
Replace the value with `<span class="text-muted">(withheld for blind
review)</span>`; keep the row and label so nothing shifts. This is the only
template under `templates/evaluations/` that renders `project_name` (checked
at cut).
**Test:** GET the form as an assigned evaluator; the phrase is present and
the application's real `project_name` is absent.

### P3 — #70 Apple Silicon WeasyPrint

`docs/developer/dress-rehearsal.md` (the macOS block, ~line 76) and
`docs/DEVELOPMENT.md` (§ macOS (Homebrew), ~line 283). After the
`brew install` line, add: on Apple Silicon Homebrew installs to
`/opt/homebrew/lib`, which the dynamic loader does not search, so `import
weasyprint` still fails until the server is started as
`DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python manage.py runserver`
(verified 2026-09-08, WeasyPrint 67.0). Docs only; no test.

### P4 — #75 Competitive-funding banner

The rule (CLAUDE.md § Critical business rule): `has_competitive_funding`
blocks rejection at resolution **unless** an evaluator recorded
`recommendation='denied'`. The forms enforce both halves correctly (verified
in the rehearsal). Only the words are wrong, in two places:

- `templates/applications/node_resolution/review.html:19` — split the alert:
  `{% if application.has_competitive_funding and not application.has_any_denied_evaluation %}`
  keeps the existing green alert and text;
  `{% elif application.has_competitive_funding %}` renders an `alert-warning`:
  **Competitive Funding:** This application has competitive funding, but an
  evaluator recommended denial, so rejection is available to you here.
- `templates/applications/resolution/call_detail.html:324` — the JS panel
  reads `app.has_competitive_funding` (`:315`) from the per-application data
  the page embeds. Find where that object is built (same template further up,
  or the view in `applications/views.py`), add `has_any_denied_evaluation`
  beside it, and branch the message the same way: current text when funding
  and no denial; the "rejection is available" text when funding and a denial;
  nothing otherwise.

`Application.has_any_denied_evaluation` is a **property**
(`applications/models.py:464`). Use it; never reimplement the check.
Do not touch the forms or services.
**Tests:** node-resolution review page for a competitive-funding application
(a) with no denied evaluation → "cannot reject" present; (b) with one
evaluation `recommendation='denied'` → "rejection is available" present,
"cannot reject" absent. Fixtures: `tests/test_phase6_node_resolution.py`.

### P5 — #79 Resolution dashboard empty state

`applications/views.py:1158` `resolution_dashboard` lists only calls with
`resolutions_released=True` — correct, that is the release gate working
(`docs/handoffs/release-gate.md`). But with a call fully evaluated and *not*
yet released, the page tells the ReDIB coordinator "No Calls Ready for
Resolution — All calls have been resolved…", which is false, and the
coordinator is the one who has to release it.

- View: alongside `calls`, compute `gated_calls` with the same `annotate`
  and `.filter(evaluated_apps__gt=0, resolutions_released=False)`; pass it.
- `templates/applications/resolution/dashboard.html`: above the existing
  list/empty-state block (~line 104), `{% if gated_calls %}` an
  `alert-warning`: **N call(s) are waiting on you to release resolutions:**
  then each as a link to `calls:detail` (`CODE — title`), and one sentence:
  evaluations are complete but the results have not been released to the node
  coordinators; **Release Resolutions** is on the call page. Show it whether
  or not the main list is empty. Keep the existing empty-state text for the
  case where nothing is gated either.
**Test:** one call with an `evaluated` application and
`resolutions_released=False` → the dashboard names it and links
`calls:detail`.

### P6 — #67 The wizard after a call closes

Three parts, one commit. Submission is already refused correctly
(`application_submit` compares to `call.submission_end`); the problem is that
the applicant is invited to finish a form that can never be submitted and
learns the truth last.

- (a) `applications/views.py:709` `application_submit`: move the "Check call
  deadline" block (currently ~760–763: `if timezone.now() >
  application.call.submission_end:` → error + redirect to detail) to directly
  after the `get_object_or_404`, ahead of every completeness check. Message
  text unchanged.
- (b) A shared partial `templates/applications/_call_closed_banner.html`:
  `{% if not application.call.is_open %}` an `alert-warning`: "This call
  closed on {{ application.call.submission_end|date:"j F Y, H:i" }}. You can
  still read and edit this draft, but it can no longer be submitted."
  `{% include %}` it at the top of the content block of `wizard_step1.html` …
  `wizard_step5.html` and `wizard_scientific_intro.html` (all six extend
  `dashboard_base.html`). Check what each wizard view names the draft in its
  context before assuming `application`. `Call.is_open` is a property
  (`calls/models.py:99`): status `open` and now inside the window. Do **not**
  disable the forms — saving a draft after close is harmless and the
  applicant may want their text.
- (c) `templates/applications/my_applications.html:41–44`: for a draft whose
  `app.call.is_open` is False, render `<span class="btn btn-outline-secondary
  disabled" title="This call closed on …">Call closed</span>` in place of
  **Continue**. **View** stays.
**Tests:** (1) POST submit on an *incomplete* draft of a closed call →
"Submission deadline has passed." and a redirect to `applications:detail`,
not to a wizard step; (2) GET step 2 of that draft → banner present; same for
a draft on an open call → absent; (3) `my_applications` shows "Call closed"
and not "Continue" for it. Fixtures: `tests/test_wizard_save_draft.py`.

### P7 — #69 `check_call_deadlines` reports both counts

`calls/tasks.py:92–124`. `open_announced_calls()` already returns
`(codes, emails_sent)` (`calls/services.py:78–120`) — capture it. Return a
string in the style of the neighbouring tasks (`send_draft_nudges` returns
"Sent N draft nudges"): `f"Opened {len(opened)}, closed {closed}"`. Drop the
"kept for backwards compatibility" sentence — nothing consumes the integer
(`tests/test_public_calls.py` calls the task and asserts on state and mail,
not on the return). `scripts/rehearsal.py` `cmd_beat` prints whatever a task
returns, so the harness needs no change; update the sentence in
`docs/developer/dress-rehearsal.md` that says the `call deadlines` line "is
what promoted it" to quote the new output.
**Test:** in `test_public_calls.py`'s promote test, assert the return value
starts with `"Opened 1"`.

### P8 — #71 Three harness artefacts

All in `scripts/rehearsal.py`; none is a portal bug, all cost time.

- (a) `cmd_seed` (~line 94) runs `setup_localtest3_database`, which creates
  node coordinators for CICBIO and CNIC only — so BIOIMAC has none, while the
  Stage 4 note in `dress-rehearsal.md` says every node has one. Create a
  BIOIMAC coordinator in `cmd_seed` (user + `UserRole(role='node_coordinator',
  node=<BIOIMAC>, is_active=True)`), named like the others (`nc.cicbio`,
  `nc.cnic` → `nc.bioimac`); copy the account/password pattern from
  `core/management/commands/setup_localtest3_database.py` and print the
  credentials in the seed summary as the others are printed. **Do not edit
  localtest3 itself.** Then correct the Stage 4 note to say the seed
  guarantees it.
- (b) line ~129: `guidelines='<p>Rehearsal guidelines.</p>'` → plain text;
  the field is rendered with `linebreaksbr` (correctly). Check whether
  `description` (line ~128) shows its tags on the public call page too; if it
  does, make it plain as well, otherwise leave it.
- (c) `cmd_advance` (~line 180) subtracts a `timedelta` from the UTC-aware
  value, so across the late-October Europe/Madrid transition a `23:59`
  deadline becomes `00:59` the next day. Do the arithmetic in local time:
  `local = getattr(call, f).astimezone(timezone.get_current_timezone())`,
  then `setattr(call, f, local - timedelta(days=days))` — aware-datetime
  arithmetic keeps the wall-clock time and recomputes the offset. Also add one
  line to the doc: sandbox emails render absolute links against `SITE_URL`,
  which in a copied `.env` is the production domain, so a link clicked from
  the console inbox goes to prod.
**Test:** for (c) — a call with `submission_end` at 23:59 local on a date
after the DST change, advanced across it, still reads 23:59 local. (a) and
(b) are seed behaviour: verify with `python scripts/rehearsal.py seed` and
`status`, and note the output in Status.

### P9 — #76 Area-match visibility on assignment

Visibility only. The rehearsal showed both preclinical applications filled
with clinical / radiochemistry evaluators (the only preclinical one was
correctly excluded by the COI rule) and plain "success". The manual-assign
modal already computes the missing signal — a ✓ on evaluators whose areas
match, from `data-app-spec` (`call_assignment_detail.html:226–233`).

- (a) `evaluations/views.py:184` `call_assignment_detail`: for each
  application's evaluations rendered in the collapse (`app.evaluations.all`,
  template ~`:165`), set `evaluation.area_match` — `None` when the
  application has no `specialization_area`, otherwise whether any of the
  evaluator's **active** evaluator roles `has_area(spec)`. The view already
  computes `combined_areas` per active evaluator (`:212–225`); build a
  `{user_id: areas}` dict from that and look it up, so an evaluator with no
  active evaluator role (the #63 case) gets `False`. Prefetch what you need;
  no query per evaluation.
- (b) `templates/evaluations/call_assignment_detail.html:168`: after the
  name, `✓` with `title="Areas match this application"` when True;
  `<span class="badge bg-warning text-dark">no area match</span>` when False;
  nothing when None.
- (c) `evaluations/views.py:239` `auto_assign_call`: after the task returns,
  count entries in `result['assignments']` whose `assigned_evaluators` (user
  ids) contain **no** evaluator matching that application's
  `specialization_area` — one `UserRole` query for all the ids, then
  `has_area`. If the count is > 0, `messages.warning`: "N application(s) were
  filled with evaluators outside their specialization area — look for the
  'no area match' marks below. Use manual assignment to swap them if a
  matching evaluator is available." The existing success and `unfilled`
  messages stay as they are.
**Tests:** a preclinical application auto-assigned when the only evaluators
are clinical → the page shows "no area match" for both and the warning
appears after the POST; with a matching evaluator → ✓ and no warning.
Fixtures: `tests/test_phase4_evaluator_assignment.py`.

## Acceptance

- `python manage.py check`; `python manage.py makemigrations --check` — nothing
  to migrate (this branch adds no migration).
- `python manage.py test tests reports` — baseline at cut **404 OK** (393 in
  `tests/` + 11 in `reports/`). Not worse, plus the new tests. Put them in
  `tests/test_rehearsal_polish.py`, one test class per item; P7's assertion
  goes in `test_public_calls.py`.
- Eyeball (runserver 8002; sandbox from `python scripts/rehearsal.py seed`
  and the stages in `docs/developer/dress-rehearsal.md`, or
  `setup_localtest3_database`): the feasibility queue as `nc.*` (P1); an
  evaluation form as an evaluator (P2); a node-resolution review of a
  competitive-funding application (P4); `/applications/resolution/` with a
  gated call (P5); the wizard and My Applications after
  `python scripts/rehearsal.py advance 61` (P6); `python scripts/rehearsal.py
  beat` output (P7); the assignment page after Auto-Assign (P9).
- Review tier (`docs/developer/worktrees.md` § Review policy): *docs, copy,
  small UI* — the handoff session reads the diff and runs the suite. No
  `/code-review`. One commit per item makes that read cheap; keep it so.

## Context & decisions already made

- Backlog rows #66–#79 are the source (`docs/developer/backlog.md`); the
  rehearsal record with the exact screens is round plan § 4.7a / § 4.7c.
- Governing principle of the round: *a beat task may compute and notify; only
  a human writes a transition.* Nothing on this branch writes a transition.
- `Application.has_any_denied_evaluation` (property) is the only competitive-
  funding check; `Call.is_open` (property) is the only "accepting now" check.
- Change-control posture (round plan § 0): this branch deploys in the
  **09-15 → 10-13** window, when no live application exists. Nothing in it is
  dated; it is a batch, not a series of hotfixes.

## Conflict watchlist

- `applications/views.py` — `rehearsal-guards` edits
  `promote_waitlisted_application` (~1543–1700). You edit 709–763, 985–1003,
  1158–1195. Different regions; still `git fetch && git rebase origin/main`
  before opening the PR.
- `docs/developer/backlog.md` — both buckets retire rows. Rebase; keep both.
- `scripts/rehearsal.py`, `docs/developer/dress-rehearsal.md`,
  `templates/evaluations/*`, `templates/applications/*` — only you.

## Status

- [x] Baseline taken (suite count before any change) — 404 tests, `tests/` + `reports/`, all passing
- [x] P1 #77
- [x] P2 #78
- [x] P3 #70
- [x] P4 #75
- [x] P5 #79
- [x] P6 #67
- [x] P7 #69
- [x] P8 #71
- [x] P9 #76
- [x] Backlog rows #67, #69, #70, #71, #75, #76, #77, #78, #79 removed (retired rows are deleted; the commit and this doc are the record)
- [x] PR opened against `main`

**Final suite:** `python manage.py test tests reports` → **415 tests, OK** (404
baseline + 11 new, in `tests/test_rehearsal_polish.py` plus one assertion added
to `tests/test_public_calls.py` for P7). `python manage.py check` and
`makemigrations --check` both clean — no migration, as scoped.

**Deviation from the brief on P4:** the brief described `call_detail.html`'s
JS `canReject` gate as a wording-only issue, but reading the code showed
`canReject = !hasCompetitiveFunding` also controls whether the Reject radio
option is rendered at all in that modal — not just the message text next to
it. Branching only the message and leaving `canReject` unfixed would have
left the coordinator reading "rejection is available" with no way to select
it. Fixed both together (`applications/views.py`'s `application_resolution`
JSON endpoint now also sends `has_any_denied_evaluation`); did not touch any
form or service, per the brief's constraint.

**Verification beyond the automated suite:** P8's seed change was checked by
actually running `python scripts/rehearsal.py seed` (BIOIMAC coordinator
created, all three nodes covered; `guidelines` renders plain, `description`
still renders as safe HTML) and P9's warning was checked end-to-end against
the real `assign_evaluators_to_call` task (including its COI exclusion) using
the seeded sandbox data, not just the unit fixtures. Did not do a full manual
browser click-through of all nine items; the new tests assert on the exact
strings each fix introduces, which covers the wording/display nature of this
batch.

## Questions for the handoff session

- (none at cut)

## Return protocol

1. Keep this doc's **Status** current; note anything you deviated from.
2. `python manage.py check`; `python manage.py makemigrations --check`;
   full suite `python manage.py test tests reports` — record the pass/fail
   counts against the baseline you took before starting (do not make it worse).
3. Push the branch and open a PR against `main`. PR body = the review
   packet: what changed and why, deviations from this brief, the test
   counts, anything user-facing (banner wording, message text) quoted for
   review, and any pre-existing bug you noticed but did not fix.
4. The handoff session reviews proportionately to risk (see
   `docs/developer/worktrees.md` § Review policy), merges, and updates the
   registry.

## Running locally (this worktree)

```bash
cd /home/rtasseff/projects/ReDIB-Portal-wt/rehearsal-polish
source venv/bin/activate
python manage.py runserver 8002
```

`.env`, `db.sqlite3` and `media/` were copied from the `main` checkout at
creation time. To rebuild the sandbox: `python scripts/rehearsal.py seed`
(the rehearsal call) or `python manage.py setup_localtest3_database`
(see `docs/DEVELOPMENT.md`).
