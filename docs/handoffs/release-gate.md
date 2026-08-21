# Handoff — `feature/release-gate`

> **Merged 2026-08-21 (PR #39).** Record only — the branch and its worktree
> are gone. #15 and #16 both shipped. This brief listed four refusal points;
> there were five — `/code-review` found `ResolutionService` bypassing the
> gate entirely. See [round-october-2026.md § 7](../developer/round-october-2026.md).

<!-- Copy of docs/developer/handoff-template.md, seeded by scripts/new-worktree.sh.
     Lives at docs/handoffs/release-gate.md on the branch. Keep "Status" current. -->

| | |
|---|---|
| Branch | `feature/release-gate` |
| Worktree dir | `/home/rtasseff/projects/ReDIB-Portal-wt/release-gate` |
| Base | `main` @ `b6e0d93` |
| Created | 2026-08-21 |
| Runserver port | 8002 |
| Handoff session | `main` checkout at `~/projects/ReDIB-Portal/` |

Read this first, then `CLAUDE.md`, then `docs/README.md`. This directory is
a git worktree: it *is* this branch — do not `git checkout` another branch
here (see `docs/developer/worktrees.md`).

**Development document.** These are instructions for the agent session working
in this worktree. Once the branch merges, this file lands on `main` as a
record — on the production VPS it is history, not a task list.

## Goal

Stop evaluated applications from becoming actionable one at a time, and let the
ReDIB coordinator release a call's resolutions to the nodes as a single batch.

Today the moment an application's last evaluation is submitted it transitions
`under_evaluation → evaluated` and *immediately* emails its node coordinator
with a link to resolve it. So a node coordinator resolves applications
piecemeal, as they trickle in, instead of weighing the whole pool of approved
applications against the capacity they actually have. On REDIB-2601 the
resolutions spread from 06-05 to 06-26 for exactly this reason. The node
coordinator who decided application #3 on June 5th could not know what #19
would look like on June 24th.

**The decision itself stays with the node coordinator** — this bucket does not
move it to ReDIB and does not automate it. It only changes *when* the node is
allowed to start: after every evaluation score for the call is in, so the whole
set can be sorted into accepted / waitlisted / rejected in one sitting.

**This is the only item this round that touches the workflow state machine**,
which is why it is on the top-tier model and the full review tier, and why it
has an abort date.

## Scope

**In, in this order.**

1. **The flag and its backfill** — `Call.resolutions_released` (+ timestamp),
   with a data migration that grandfathers calls whose resolutions already went
   out. Details below; **read the backfill rule carefully, it is the one piece
   that can hurt a live call.**
2. **Hold the notification.** `evaluations/utils.py
   check_and_transition_application` still transitions to `evaluated` — no new
   application state — but only dispatches
   `notify_coordinator_evaluations_complete` when the call is released.
3. **Refuse to act while unreleased**, at the service layer first and the views
   second. Four call sites, listed below.
4. **The release action** — a coordinator-only "Release to nodes" on call
   detail: GET previews the whole batch with the score spread, POST sets the
   flag and sends the held emails for every `evaluated` application at once.
5. **Score spread on the release screen** — report note (I). Display only.
6. ***(Stretch, only once 1–5 are green and committed)*** **#16** — surface
   "node-accepted, awaiting applicant" in the coordinator-facing lists. **Less
   work than the backlog entry implies — read the #16 note below before
   estimating it.**

**Out** (do not do here — belongs on `main` or another bucket):

- **No new `Application` status.** Not `released`, not `awaiting_release`, not
  anything. The gate is a property of the *call*, and `evaluated` keeps meaning
  exactly what it means today. This is the single most important boundary in
  the brief — a new application state would ripple into every badge, filter,
  report and transition table in the project.
- **No third evaluator, no tiebreak rule, no re-scoring.** The score spread is
  surfaced so a human can see it. Whether a divergent pair warrants a third
  opinion is a *network policy* decision for ReDIB, not a portal change, and
  not this round's.
- **#12** (dedicated `edits_requested` status), **#40** (call lifecycle
  redesign, ~2027-03). Do not anticipate either.
- The evaluator lockout (`is_evaluation_locked`, deadline + `GRACE_PERIOD_DAYS`)
  — leave it exactly as it is.

## The rule this round works to

> **A beat task may compute and notify. Only a human writes a transition.**

Established by `acceptance-repair`, and this bucket is its clearest expression:
the `evaluated` transition stays automatic because it is bookkeeping the
evaluators' own work, but the *consequence* — putting work in front of a node
coordinator — becomes something a human releases. Nothing you add here may
write an `Application.status` from a beat task.

## Acceptance

- With a call unreleased: submitting the final evaluation on an application
  still moves it to `evaluated`, and **no node coordinator is emailed**; the
  application appears in no node's resolution queue; `apply_node_resolution`
  refuses it; the node-coordinator dashboard count does not include it.
- Pressing "Release to nodes" sends the whole batch's
  `evaluations_complete` emails in one go, and pressing it twice does not
  re-send.
- The release screen shows every application that will be released, each
  evaluator's total score, and the spread — with divergent pairs marked.
- An existing call whose resolutions already went out is **unaffected** by the
  deploy: still resolvable, no emails re-fired, nothing frozen.
- `python manage.py check` and `makemigrations --check` clean; the suite **not
  worse than the baseline you record before starting**. New tests per item.

  **Run both commands.** `tests/` has no `__init__.py`, so Django's default
  discovery walks straight past it and `manage.py test` alone gives you a green
  light from 3% of the suite:

  ```bash
  python manage.py test tests    # 315 tests — the workflow suite
  python manage.py test          #  11 tests — reports/tests.py
  ```

## Context & decisions already made

Settled 2026-08-18 and 2026-08-21. **Do not reopen these; if one looks wrong,
put it under "Questions for the handoff session" and keep going.**

### The flag, and the backfill rule that matters

```python
# calls/models.py, beside is_resolution_locked
resolutions_released = models.BooleanField(default=False, help_text=...)
resolutions_released_at = models.DateTimeField(null=True, blank=True)
```

`default=False` is right for new calls and **wrong for calls already in
flight**, so the same migration file needs a data migration. The rule:

> Set `resolutions_released=True` for every existing call that already has at
> least one application with a non-blank `resolution`.

Not "every existing call". The distinction matters: the October 2026 call may
already exist as a `draft` when this deploys (it announces ~2026-09-15), and
grandfathering it would silently defeat the entire bucket on the one call it
was built for. Keying on "resolutions already went out" gates the new call
correctly and leaves REDIB-2601 alone.

Write the data migration with `RunPython` and a working reverse (`noop` is
acceptable for the reverse). **Do not** edit a migration once it has been
applied anywhere — if you hit a rebase conflict in a generated migration,
delete your copy and re-run `makemigrations`; the new file takes the next free
number. (`eval-reminders` got this wrong last week against an already-deployed
migration; see `docs/developer/round-october-2026.md` § 7.)

### Where the hold goes

`evaluations/utils.py:57` — `check_and_transition_application` sets
`status='evaluated'`, saves, then fires
`notify_coordinator_evaluations_complete`. **Keep the transition. Gate only the
notification**, on `application.call.resolutions_released`.

Do not gate it inside `notify_coordinator_evaluations_complete` itself — the
release action needs to call that same function for the whole batch, and a
guard buried in the task would make it refuse at exactly the moment it should
fire.

### The four places that must refuse while unreleased

The service layer is the real enforcement; the views are the courtesy message.

1. **`applications/services/node_resolution.py:41`
   `get_applications_for_node_resolution`** — add
   `call__resolutions_released=True` to the queryset. This alone empties the
   queue, the dashboard count and the review page's eligibility in one move.
2. **`applications/services/node_resolution.py:146` `apply_node_resolution`** —
   refuse outright if the call is unreleased. A queryset filter is not a
   guard; someone with a stale tab or a bookmarked URL must be stopped here.
3. **`applications/views.py:2384` `node_resolution_review`** — refuse with a
   `messages.error` explaining that ReDIB has not released this call's
   resolutions yet, and redirect to the queue. Do not 404 — a node coordinator
   arriving from an old email deserves to know *why*.
4. **`core/views.py:130`** — the node-coordinator dashboard's
   `pending_resolution` count filters `status='evaluated', resolution=''`; add
   the release condition so the badge does not advertise work that cannot be
   started.

### The release action

Coordinator-only, on `templates/calls/detail.html` beside the lifecycle
buttons. Follow `call_resolve` (`calls/views.py:614`) and
`templates/calls/resolve_confirm.html` — same `@coordinator_required`, same
GET-previews / POST-acts shape, same confirmation copy discipline.

- **Guard:** refuse if already released. Refuse if the call has no `evaluated`
  applications (nothing to release). Do **not** require every application on
  the call to be `evaluated` — some will be `rejected_feasibility` or still
  `draft`, and a call with one stuck application must not be un-releasable.
  That is the same trap `call_resolve`'s guard was deliberately kept narrow to
  avoid; see `docs/handoffs/closeout.md`.
- **On POST:** set both fields, then send `evaluations_complete` for **every**
  `evaluated` application on the call by calling
  `notify_coordinator_evaluations_complete` per application — reuse it, do not
  reimplement the recipient logic, which already handles the multi-node case
  and links to the right per-node page.
- **Idempotence:** the `already released` guard is the primary defence; add an
  `EmailLog` dedupe per (recipient, application) as the secondary, matching the
  pattern in `applications/tasks.py`.
- **No new email template.** Release fires the existing
  `evaluations_complete`, which is exactly the mail that was being held.

### The release screen, and the score spread (report note I)

The screen is the point of the bucket as much as the flag is — it is where the
coordinator sees the whole call at once before handing it to the nodes. Per
application, in one table:

- code, applicant, node(s), `final_score`
- **each evaluator's `total_score` and `recommendation`**, side by side
- **the spread** (max − min), with a visible marker when it is **≥ 5**

Why ≥ 5: on REDIB-2601 the two evaluators diverged by 5 or more points out of
12 on **12 of 24 applications** — 12 vs 4, 11 vs 3, and one 7/approved against
0/denied. That is half the call. Surfacing it is all this bucket does about it;
what ReDIB *does* with a divergent pair is a policy question for Ryan and the
network, deliberately not a portal rule.

`Evaluation.total_score` is the sum of six 0–2 criteria (max 12) and
`Evaluation.recommendation` is the accept/deny field; both are on
`evaluations/models.py`. An application with one evaluation, or none complete,
has no spread — show that honestly rather than computing 0.

### #16 — much smaller than the backlog entry says

**Read this before estimating.** `templates/includes/status_badge.html` already
does the hard part: it distinguishes `Active` / `Accepted` / `Accepted —
Awaiting Applicant`, and the waitlist equivalents, computed from
`accepted_by_applicant` and `handoff_email_sent_at`. That badge is correct and
needs no changes.

The gap is **adoption**. It is included in exactly two templates
(`templates/access/access_tracking.html`, `templates/calls/detail.html`). Nine
others render `{{ app.get_status_display }}` directly and therefore still show
a flat "Accepted": `applications/my_applications.html`,
`applications/node_resolution/queue.html`, `core/dashboard.html`,
`applications/detail.html`, `evaluations/assignment_dashboard.html`,
`evaluations/call_assignment_detail.html`, `reports/statistics_dashboard.html`,
and two of `acceptance-repair`'s confirm screens.

So #16 is: swap the coordinator-facing ones to `{% include
"includes/status_badge.html" %}`, then add the filter the entry asks for
("pull node-accepted but not yet applicant-confirmed"). Use judgement on the
applicant-facing and report templates — `my_applications` probably wants it,
`statistics_dashboard` probably does not. **Display only; no view logic beyond
the filter, and no state-machine change.**

## Where things are

- `evaluations/utils.py:35-80` — `check_and_transition_application`, the hook.
- `evaluations/tasks.py:750` — `notify_coordinator_evaluations_complete`, the
  email the gate holds and the release action replays.
- `applications/services/node_resolution.py` — `NodeResolutionService`:
  `get_applications_for_node_resolution` (:41), `apply_node_resolution` (:146),
  `aggregate_application_resolution` (:239).
- `applications/views.py:2297` `node_resolution_queue`, `:2384`
  `node_resolution_review`.
- `calls/models.py:53` `is_resolution_locked` — the sibling flag; put yours
  beside it.
- `calls/views.py:614` `call_resolve` + `templates/calls/resolve_confirm.html`
  — the coordinator-action pattern to copy.
- **Read what `closeout`'s #36 did to `calls/views.py` and
  `applications/services/resolution.py` before you start** —
  `docs/handoffs/closeout.md` on `main`, particularly why `call_resolve`
  deliberately does *not* press `finalize_resolution`. The same reasoning
  applies to your release action: it is a separate, narrow, no-surprise button.
- Role checks always via `UserRole`; see `CLAUDE.md`.

## Conflict watchlist

Nothing else is live — `marketing-site` is parked and no other bucket is out.
You have `applications/`, `calls/` and `evaluations/` to yourself.

`main` may still take small inline fixes while you work (#43 is queued, and
#55–#59 are open). Rebase before opening the PR. The likely touch points are
`applications/views.py` and `calls/models.py`.

## Deploy note (carry this into the PR body)

This is the only bucket this round that **deploys a schema migration into a
live call**, and it must be in prod **before the first evaluation completes on
the October call** — that is the transition it gates. Consequences:

- `scripts/backup-db.sh` runs **before** the deploy, not after.
- The data migration must be reversible enough to roll back safely; state
  plainly in the PR what a rollback would and would not undo.
- Note in the PR whether `sqlmigrate` shows real DDL (it will — this is a new
  column, unlike the choices-only no-ops of the last three deploys) and what
  the table lock looks like on a table with ~1 call row.
- Prod runs three containers that race `migrate` on every deploy (#37, with
  prod's forensics from 2026-08-21). Benign so far, but this is the first
  migration in a while that emits real DDL, so flag it for the deploy session
  to watch.

## Abort criterion

**If this is not merged by 2026-12-05, park the branch** and run the winter
resolution piecemeal, the way REDIB-2601 was run. Check the date; do not
negotiate with it. A structural item is not allowed to sink the round — it is
better to ship a call without the gate than to ship a half-gate into a live
resolution phase.

## Status

<!-- Keep this current as you work. -->

- [x] Baseline recorded (`test tests`, `test`, `check`, `makemigrations --check`)
      before any change — `test tests`: 315 OK; `test`: 11 OK; `check`: clean
- [x] 1. `resolutions_released` + timestamp + **backfill data migration**
- [x] 2. notification held in `check_and_transition_application`
- [x] 3. the four refusals (service layer first)
- [x] 4. "Release to nodes" action + confirm screen
- [x] 5. score spread on the release screen, ≥5 marked
- [x] *(stretch)* 6. #16 — badge adoption + the filter
- [x] `/code-review` at **medium**, on this branch, before opening the PR —
      5 findings, all applied (see "Review findings" below)
- [x] Suite green — record both counts — `test tests`: 342 OK (315 baseline +
      27 new; 2 pre-existing test setups in `test_batch2_phase1.py`/
      `test_batch2_phase4.py` updated to set `resolutions_released=True`,
      since they exercise `apply_node_resolution` for unrelated behavior);
      `test`: 11 OK; new coverage in `tests/test_release_gate.py`
- [x] PR opened — [#39](https://github.com/Rtasseff/ReDIB-Portal/pull/39)

## Review findings (medium `/code-review`)

All five findings applied before opening the PR:

1. **Critical, out-of-brief scope gap — fixed.** `applications/services/resolution.py`'s
   `ResolutionService` (`apply_resolution`, `bulk_auto_allocate`, `finalize_resolution`)
   is a second, fully-wired path from `evaluated` to a resolved status —
   reachable via the "Resolution" sidebar link every ReDIB coordinator sees
   (`resolution_dashboard` → `call_resolution_detail` → per-application AJAX
   resolve / bulk auto-allocate / finalize). It never checked
   `resolutions_released` and so completely bypassed the gate this whole
   bucket exists to build. **Not one of the brief's documented "four call
   sites"** — the brief's Context section doesn't mention this service at
   all, only `NodeResolutionService`. Gated all three entry points the same
   way, plus excluded unreleased calls from `resolution_dashboard`'s list
   (mirroring the node-coordinator queue's "empties the queue" behavior).
   New tests: `LegacyResolutionServiceGateTest` in `tests/test_release_gate.py`.
2. **Batch email loop resilience — fixed.** The release action's per-application
   notify loop only caught `.delay()` failing, not the synchronous fallback
   also failing — one bad application (missing template, malformed recipient
   data) would 500 the whole batch after `resolutions_released` was already
   committed True, with no way to retry via the same button. Now matches
   `NodeResolutionService._trigger_resolution_notification`'s established
   double-try/log-and-continue pattern; a partial failure surfaces as a
   `messages.warning` with counts instead of crashing the request.
3. **Duplicated gate check — fixed.** The `if not call.resolutions_released:
   raise ValidationError(...)` guard was hand-copied across what became six
   call sites once finding 1 added three more. Centralized as
   `Call.ensure_resolutions_released()` (`calls/models.py`, beside the flag),
   used by both services now — so a future resolution entry point has one
   symbol to call instead of a pattern to remember, the same reasoning
   CLAUDE.md gives for `Application.has_any_denied_evaluation`.
4. **N+1 query — fixed.** The release action's `EmailLog` dedupe check ran
   once per application instead of one query for the whole batch.
5. **Redundant query — fixed.** `access_tracking`'s awaiting-applicant count
   re-applied the same filter that had just been applied to build the list;
   now reuses the one queryset for both.

## Questions for the handoff session

<!-- Park anything needing the human or `main` here and continue with what does
     not depend on it. Do not guess on these. -->

-

## Review

This bucket is in the **`/code-review` at medium** tier
(`docs/developer/worktrees.md` § Review policy): it changes the workflow state
machine's timing, adds a migration that deploys into a live call, and gates an
email fan-out. **Run it yourself on this branch before opening the PR**, at
*medium*, so the findings and your fixes land in the PR — the handoff session
then reads only what was flagged, instead of re-reading the whole diff. Running
it from the handoff session instead costs roughly ten times as much; that is
the whole reason the tier exists.

## Return protocol

1. Keep this doc's **Status** current; note anything you deviated from.
2. `python manage.py check`; `python manage.py makemigrations --check`;
   both test commands — record the pass/fail counts against the baseline you
   took before starting (do not make it worse).
3. Push the branch and open a PR against `main`. PR body = the review
   packet: what changed and why, deviations from this brief, the test counts,
   **the deploy note above**, `sqlmigrate` output for the new migration, and
   any pre-existing bug you noticed but did not fix.
4. The handoff session reviews proportionately to risk (see
   `docs/developer/worktrees.md` § Review policy), merges, and updates the
   registry.

## Running locally (this worktree)

```bash
cd /home/rtasseff/projects/ReDIB-Portal-wt/release-gate
source venv/bin/activate
python manage.py runserver 8002
```

`.env`, `db.sqlite3` and `media/` were copied from the `main` checkout at
creation time. To rebuild the sandbox: `python manage.py setup_localtest3_database`
(see `docs/DEVELOPMENT.md`).

**Testing the gate end to end:** `setup_localtest3_database` seeds a call with
applications at `evaluated` (`core/management/commands/setup_localtest3_database.py:850`).
Submit the last evaluation on an application through the UI with the call
unreleased and confirm the node coordinator's queue stays empty and no mail
prints; `EMAIL_BACKEND` is the console backend in dev, so held-versus-sent is
visible directly in the runserver output. Then press Release and watch the
whole batch go at once.
