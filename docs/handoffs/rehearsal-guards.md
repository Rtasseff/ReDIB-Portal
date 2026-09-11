# Handoff — `feature/rehearsal-guards`

<!-- Copy of docs/developer/handoff-template.md, seeded by scripts/new-worktree.sh.
     Lives at docs/handoffs/rehearsal-guards.md on the branch. Keep "Status" current. -->

| | |
|---|---|
| Branch | `feature/rehearsal-guards` |
| Worktree dir | `/home/rtasseff/projects/ReDIB-Portal-wt/rehearsal-guards` |
| Base | `main` @ `53c4fae` |
| Created | 2026-09-10 |
| Runserver port | 8003 |
| Handoff session | `main` checkout at `~/projects/ReDIB-Portal/` |
| Suggested model | **Opus** (`/model opus`) — two workflow-state fixes with regression tests, one seed default, one cadence constant |

Read this first, then `CLAUDE.md`, then `docs/README.md`. This directory is
a git worktree: it *is* this branch — do not `git checkout` another branch
here (see `docs/developer/worktrees.md`).

**Development document.** These are instructions for the agent session working
in this worktree. Once the branch merges, this file lands on `main` as a
record — on the production VPS it is history, not a task list.

## Goal

Two of the dress rehearsal's findings (2026-09-08, round plan § 4.7c) change
what the portal **does**, not what it shows — and both are *silent* state
changes: nothing throws, so no test in the suite could have caught them.

- **#73** — one click on **Auto-Assign Evaluators** closes a call that is
  still accepting applications. It vanishes from `/calls/`, new applicants are
  bounced, nobody is warned, and there is no UI way back (#54).
- **#74** — **Promote to Accepted** on a waitlisted application never updates
  the node's `NodeResolution`, so the published resolution table and both CSVs
  print *Wait List / En espera* for someone who was actually granted access.
  It never surfaced on REDIB-2601 because none of its seven waitlisted
  applications was promoted; the October round is built to promote them (#30).

This branch fixes both **at the source**, with regression tests, and takes the
two small code halves of **#80** that make the completion reminders safe to
switch back on once Ryan settles the deadline policy. Four items; nothing
else. The portal is small and the last call went well enough — the bar is the
smallest change that closes each hole, and anything else you notice goes to
the backlog, not into this PR.

## Scope

**In** — four items, one commit each, in this order:

| | Backlog | What |
|---|---|---|
| G1 | #73 | Auto-assign closes the call only when the deadline has actually passed |
| G2 | #74 | Promotion from the waitlist records `accept` on the node's resolution |
| G3 | #80(c) | `seed_email_templates` sets `is_active` on create only — the admin's off switch survives deploys |
| G4 | #80(b) | The coordinator completion digest is floored at one per recipient per 7 days |

**Out** (do not do here):
- **#80(a)**, the deadline policy for REDIB-2601's fifteen running projects —
  Ryan's decision, recorded in round plan § 0. **Re-enabling the beat entry**
  (`redib/celery.py`, commented out on prod 2026-09-09) is a prod action taken
  only after that decision; leave the file alone.
- **#54** (a reopen path for a closed call), **#64**, **#37** (deploy
  mechanics — separate), every `rehearsal-polish` item.
- `reports/resolution_table.py` — it is **correct** and must not special-case
  promotions. Decision 1 in `docs/handoffs/resolution-report.md` (the published
  resolution is `NodeResolution.resolution`, never `Application.status`)
  stands; G2 is what makes it hold.
- Any migration, new model field, new email template, or setting.

## Items

### G1 — #73 Auto-assign must not close a live call

**Decision: guard, don't remove.** The auto-close at the end of
`assign_evaluators_to_call` is legitimate in exactly one case — the deadline
has passed and the daily `check_call_deadlines` has not run yet — and that
case is the beat task's own condition (`calls/tasks.py:110–113`:
`status='open', submission_end__lt=now`). Any earlier, closing is wrong.

- `evaluations/tasks.py` — both sites, `:589–591` (the zero-pool early
  return) and `:733–735`: `if call.status == 'open' and call.submission_end <
  timezone.now():` (`timezone` is already imported at `:10`). Say in the
  function docstring when it closes the call and why.
- **Do not refuse assignment while the call is open.** The harm was the close,
  not the assignment. A coordinator assigning early to get a head start on
  applications already through feasibility is doing something reasonable;
  applications that arrive later stay `pending_evaluation` and are picked up
  on the next run (the task only touches `pending_evaluation` applications —
  confirm that when you read it).
- `templates/evaluations/call_assignment_detail.html`: when `call.is_open`
  (`calls/models.py:99`, a property), an `alert-info` beside the auto-assign
  form: "This call is still accepting applications until
  {{ call.submission_end|date:"j F Y, H:i" }}. Assigning now is fine; anything
  submitted after today will need evaluators assigned on a later run."
- **Tests** (`tests/test_rehearsal_guards.py`): (1) open call,
  `submission_end` 20 days ahead, one `pending_evaluation` application, two
  eligible evaluators → assignments made **and the call is still `open`**;
  (2) same with `submission_end` yesterday → `closed` (existing behaviour,
  kept); (3) the zero-pool early return (no eligible evaluators) on an open
  call inside its window → still `open`; (4) the page shows the notice for an
  open call and not for a closed one. Fixtures:
  `tests/test_phase4_evaluator_assignment.py`.

### G2 — #74 Promotion records the node's decision

**Decision: fix where the decision is made, not where it is printed.**
`promote_waitlisted_application` (`applications/views.py:1543`) is the node
coordinator's own later decision, so *it* updates the `NodeResolution` rows;
the resolution table keeps reading `NodeResolution.resolution` and nothing
else.

- After `application.save()` (~`:1642`), for every `NodeResolution` of this
  application with `resolution='waitlist'`: `resolution='accept'`,
  `reviewed_at=now`, and append to `comments` (blank line between) —
  `Promoted from the waitlist by <full name, or email> on YYYY-MM-DD.`
  Leave `reviewer` as it is: it records who made the original decision; the
  promotion is in `comments` and in `simple_history` (the model has
  `HistoricalRecords`). Rows already `accept` are untouched.
- **Why every `waitlist` row, not "the promoter's node":**
  `Application.status='accepted'` means, under the aggregation rule in the
  model docstring (`applications/models.py:595`), that every node accepted. A
  multi-node application that is accepted while one node still reads
  `waitlist` is the exact inconsistency this closes. Who may promote is
  already restricted by `_can_manage_application`.
- `close_out_waitlisted_application` (decline / expire from the waitlist) is
  **not** changed: the applicant's later action does not alter the node's
  decision (decision 1; REDIB-2601-026 publishes as Accepted even though it
  later expired).
- **No backfill.** None of REDIB-2601's seven waitlisted applications was ever
  promoted (backlog #74), so no prod row is wrong today. Do not write a data
  migration.
- **Tests:** (1) promote → the node's row reads `accept`, `reviewed_at` set,
  comment appended, `reviewer` unchanged; (2)
  `reports.resolution_table.build_resolution_table(call, 'en')` and `'es'`
  show *Accepted* / *Aceptada* for it (helpers in
  `tests/test_resolution_report.py`); (3) two-node application, node A
  `accept`, node B `waitlist` → after promotion both `accept`, A's `comments`
  untouched; (4) a `reject` row is never touched (defensive — it cannot
  co-exist with `pending` under the aggregation, so construct it directly).
  `tests/test_backfill_waitlist_hours_approved.py` already drives
  `promote_waitlisted_application`; start from its fixtures.

### G3 — #80(c) The admin's per-template off switch

**Decision: `is_active=True` applies on create only.**
`communications/management/commands/seed_email_templates.py:2559–2568` passes
`'is_active': True` in `update_or_create`'s `defaults`, and
`docker/entrypoint.sh:25` reseeds on every container start — so deactivating a
template in the Django admin is undone by the next deploy. Prod found this
while pausing the completion reminders and had to comment out a beat entry
instead. Django 5.0's `update_or_create(..., defaults=..., create_defaults=...)`
does exactly what is wanted: move `is_active` from `defaults` to
`create_defaults` (which must also carry the four content fields, since
`create_defaults` replaces `defaults` on create rather than extending it).

- Cost, stated: a template someone deactivated on purpose stays off across
  deploys. That is what an off switch is. Today every template on prod is
  active (each deploy reseeds it that way), so nothing changes at the moment
  this lands.
- `docs/DEPLOYMENT.md`, where `seed_email_templates` is described: one
  sentence — the admin's `is_active` toggle now survives deploys; subject and
  body edits still do **not** (the seed overwrites them; unchanged, and
  deliberate).
- **Tests:** deactivate a seeded template, run `seed_email_templates` → still
  inactive, subject still refreshed; a template type absent from the DB is
  created active.

### G4 — #80(b) The coordinator completion digest's floor

**Decision: one digest per recipient per seven days.**
`send_completion_reminders` (`applications/tasks.py:636`) already lists
**every** application awaiting completion at the recipient's nodes whenever
any one of them hits a 60/30 checkpoint — the docstring says so and
`test_coordinator_digest_lists_every_application_awaiting_completion` pins it
— so widening the per-recipient dedupe from 24 hours to 7 days loses nothing:
the next digest carries the full list anyway. The 24-hour window was right for
REDIB-2601's original burst (22 handoffs within days) and wrong for its
trickle (the 15 still running were handed off 63–92 days apart → a checkpoint
almost every day → a digest every second morning; see backlog #80).

- Change the coordinator-branch `recently_sent` window
  (~`:741`, `sent_at__gte=now - timedelta(days=1)`) to seven days, as a named
  module constant with a one-line comment pointing at #80. The **applicant**
  email is per application on exact cadence days — unchanged. The milestone
  (`_milestone_window`) dedupe — unchanged.
- **Do not touch `redib/celery.py`.** The beat entry stays commented out until
  Ryan decides #80(a); re-enabling is a prod action. Say so in Status.
- **Tests** (extend `tests/test_closeout_completion_reminders.py`): a second
  application reaching a checkpoint three days after a digest went out → no
  second digest; eight days after → a digest, listing both.

## Acceptance

- `python manage.py check`; `python manage.py makemigrations --check` — nothing
  to migrate (this branch adds no migration).
- `python manage.py test tests reports` — baseline at cut **404 OK** (393 in
  `tests/` + 11 in `reports/`). Not worse, plus the new tests.
- Click-through in the sandbox (runserver 8003; `python scripts/rehearsal.py
  seed`, then Part B of `docs/developer/dress-rehearsal.md` from Stage 8):
  Auto-Assign on the still-open call leaves it listed on `/calls/`; promote
  the waitlisted application and the resolution table in Stage 11 reads
  *Accepted*. The rehearsal doc already describes both screens; round plan
  § 4.7c records what they showed before the fix.
- Review tier (`docs/developer/worktrees.md` § Review policy): *ordinary
  features* — suite plus a targeted read of the two state-writing diffs by
  the handoff session. No `/code-review`.

## Context & decisions already made

- Governing principle of the round: *a beat task may compute and notify; only
  a human writes a transition.* G1 makes the auto-close obey the same
  condition as the beat task; G2 records a human's transition where it
  happened.
- The competitive-funding rule (CLAUDE.md § Critical business rule) is
  untouched by this branch.
- `docs/handoffs/resolution-report.md` decision 1 stands (see Scope).
- Change-control posture (round plan § 0): this branch deploys in the
  **09-15 → 10-13** window, when no live application exists. G1 and G2 are
  the point; G3 and G4 ride along because they are small and tested. If time
  is short, G4 is the one to leave — the reminders are paused in prod and
  stay paused regardless.

## Conflict watchlist

- `applications/views.py` — `rehearsal-polish` edits 709–763, 985–1003 and
  1158–1195; you edit ~1543–1700. Different regions; still
  `git fetch && git rebase origin/main` before opening the PR.
- `docs/developer/backlog.md` — both buckets retire rows. Rebase; keep both.
- `evaluations/tasks.py`, `applications/tasks.py`,
  `communications/management/commands/seed_email_templates.py`,
  `templates/evaluations/call_assignment_detail.html` (polish adds ✓ marks in
  the evaluator list at `:168`; you add an alert near the auto-assign form —
  different blocks) — rebase before the PR.

## Status

- [x] Baseline taken — `python manage.py test tests reports`: **404 OK**, as at cut
- [x] G1 #73 — `d610882`. Both close sites guarded; notice on the assignment page.
- [x] G2 #74 — `52e52bd`. Per-row `save()`, so the promotion is in `simple_history` too.
- [x] G3 #80(c) — `27faf14`. DEPLOYMENT.md note under *Deploying Code Updates*.
- [x] G4 #80(b) — `f89ad75`. **Deviates from the brief — see below.**
- [x] Backlog rows #73, #74 removed; #80 trimmed to (a) the policy decision and re-enabling the beat entry
- [x] PR opened against `main`

Final: `check` clean, `makemigrations --check` → no changes, suite **416 OK**
(404 + 12 new: 10 in `tests/test_rehearsal_guards.py`, 2 in
`tests/test_closeout_completion_reminders.py`). Every new state test was run
against the pre-fix code and fails there.

Click-through (2026-09-11, headless: `rehearsal.py seed`, then the real views
driven as coordinator / `nc.cicbio` / applicant with the Django test client,
not a browser): Auto-Assign on the open REHEARSAL-2701 made 5 assignments, the
call stayed `open` and stayed listed on `/calls/`, and the page showed the
notice; a waitlisted application, accepted by the applicant and promoted by
`nc.cicbio`, reads **Accepted** / **Aceptada** on the Stage 11 page and in both
CSVs, with no *Wait List* / *En espera* left anywhere.

`redib/celery.py` is untouched: the completion-reminder beat entry stays
commented out on prod until Ryan decides #80(a). Re-enabling it is a prod
action.

### Deviations

- **G4 needed one more line of change than the brief said.** The brief took
  it that a coordinator digest already lists every application awaiting
  completion at the recipient's nodes. The docstring, the test name and the
  template intro ("The following applications at your node(s) are still
  open") all say it does — but the code dropped any application not at a
  checkpoint that day *before* it reached the digest, and the pinning test
  only passed because both its applications were due on the same day. With
  just the window widened to 7 days, an application whose checkpoint fell
  inside the floor would get no coordinator mention for another 30 days, and
  the brief's own "eight days after → listing both" test fails (checked). So
  every awaiting application now goes into the recipient's digest, and only
  a due one makes it fire. Visible effect: a coordinator's digest lists all
  of their node's running projects, not just the one or two that hit a
  checkpoint that day. It's in its own commit, so it can be dropped alone.
- **G2 fixtures**: `tests/test_backfill_waitlist_hours_approved.py` doesn't
  drive `promote_waitlisted_application` (it tests the backfill command);
  `tests/test_batch2_phase4.py` does, and the new tests follow that one.

## Questions for the handoff session

- (none at cut)
- The round plan's "Do these" rows 6, 7 and 9 (#73, #74, #80(b)(c)) are live
  status for you to update on merge; this branch doesn't touch
  `round-october-2026.md`. Row 9 describes G4 as "the 7-day floor" — it also
  now lists every awaiting application (see Deviations).

## Return protocol

1. Keep this doc's **Status** current; note anything you deviated from.
2. `python manage.py check`; `python manage.py makemigrations --check`;
   full suite `python manage.py test tests reports` — record the pass/fail
   counts against the baseline you took before starting (do not make it worse).
3. Push the branch and open a PR against `main`. PR body = the review
   packet: what changed and why, deviations from this brief, the test
   counts, anything user-facing (the assignment-page notice, the promotion
   comment text, the DEPLOYMENT.md sentence) quoted for review, and any
   pre-existing bug you noticed but did not fix.
4. The handoff session reviews proportionately to risk (see
   `docs/developer/worktrees.md` § Review policy), merges, and updates the
   registry.

## Running locally (this worktree)

```bash
cd /home/rtasseff/projects/ReDIB-Portal-wt/rehearsal-guards
source venv/bin/activate
python manage.py runserver 8003
```

`.env`, `db.sqlite3` and `media/` were copied from the `main` checkout at
creation time. To rebuild the sandbox: `python scripts/rehearsal.py seed`
(the rehearsal call) or `python manage.py setup_localtest3_database`
(see `docs/DEVELOPMENT.md`).
