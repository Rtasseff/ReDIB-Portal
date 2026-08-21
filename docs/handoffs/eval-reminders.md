# Handoff — `feature/eval-reminders`

<!-- Copy of docs/developer/handoff-template.md, seeded by scripts/new-worktree.sh.
     Lives at docs/handoffs/eval-reminders.md on the branch. Keep "Status" current. -->

| | |
|---|---|
| Branch | `feature/eval-reminders` |
| Worktree dir | `/home/rtasseff/projects/ReDIB-Portal-wt/eval-reminders` |
| Base | `main` @ `81958b9` |
| Created | 2026-08-20 |
| Runserver port | 8003 |
| Handoff session | `main` checkout at `~/projects/ReDIB-Portal/` |

Read this first, then `CLAUDE.md`, then `docs/README.md`. This directory is
a git worktree: it *is* this branch — do not `git checkout` another branch
here (see `docs/developer/worktrees.md`).

**Development document.** These are instructions for the agent session working
in this worktree. Once the branch merges, this file lands on `main` as a
record — on the production VPS it is history, not a task list.

## Goal

Stop the portal shouting at the people it depends on, and give the ReDIB
coordinator a lever to nudge off-cycle.

On REDIB-2601 two evaluators received **42 reminder emails each** and a third
got 29 — 113 of 130 reminder emails went to three people. The cause is one
loop: `send_evaluation_reminders` sends one email *per pending evaluation* every
day for the seven days before the deadline, with no digest and no dedupe of any
kind. An evaluator holding six applications gets six mails a morning. These are
unpaid volunteers, and the real risk is that they filter portal mail before the
next call opens. **This must land before evaluations open on the October call.**

Same shape, three more places: node coordinators get one completion reminder per
open project (#49), applicants who never submit get nothing at all (#35), and
the coordinator has no way to prompt anyone off-schedule (#5).

**The rule this round now works to, established by `acceptance-repair`:**

> **A beat task may compute and notify. Only a human writes a transition.**

Everything in this bucket is on the safe side of that line — every item is an
email. **Nothing here may write an `Application.status`, an `Evaluation`
completion, or a `Call.status`.** If you find yourself reaching for `.save()` on
a workflow object inside a beat task, stop and park it under "Questions".

## Scope

**In, in this order.** #5 reuses the helper #32 builds, so #32 goes first.

1. **#32 — per-evaluator digest.** The core of the bucket. One email per
   evaluator listing every pending evaluation they hold, on a fixed cadence
   instead of daily-per-item. Details below.
2. **#5 — on-demand reminder dispatch.** A coordinator panel that fires the
   same emails for a chosen call, off-cycle. Built on #32's helper so the
   manual button and the scheduled task produce identical mail.
3. **#35 — draft nudge.** Applicants sitting on a `draft` when the submission
   deadline approaches currently get nothing. Three REDIB-2601 applications
   never left `draft` and two went quiet ~3 weeks before close.
4. **#49 — completion-reminder digest.** Same digest treatment for
   `send_completion_reminders`. **Gated — read the note under Conflict
   watchlist before starting it.**

**Out** (do not do here — belongs on `main` or another bucket):

- **The evaluator lockout stays exactly as it is.** `evaluations/utils.py
  is_evaluation_locked()` derives "deadline + 7 days" at page load — nothing
  stored, nothing emailed to the evaluator. It is the one automatic thing in
  the system Ryan is comfortable with, precisely because it writes nothing.
  **Do not touch it, do not store it, do not email the evaluator about it.**
- **#4** (auto-assign evaluators: confirm-and-review before emails go out) —
  deferred this round. #5's preview screen is *not* the place to sneak it in.
- Anything in `applications/views.py`, `process_acceptance_deadlines`, or the
  acceptance/expiry flow — that is `acceptance-repair`, live in parallel.
- `send_feasibility_reminders` and `send_waitlist_digest` — both were fixed in
  `closeout` and are not yours. #50 (their dedupe is keyed per application where
  it should be per node) is filed and deliberately deferred; leave it.

## Acceptance

- An evaluator with N pending evaluations receives **one** email, not N, on any
  day the cadence fires — verifiable in a seeded sandbox with one evaluator
  holding several applications.
- Running the daily task twice on the same day sends nothing the second time.
- The coordinator's manual dispatch produces the **same email body** as the
  scheduled task, and its preview screen names exactly who will be mailed and
  who will be skipped before anything sends.
- An applicant with a `draft` on an open call is nudged at T−7 and T−2, once
  each, and never after `submission_end`.
- No beat task writes a workflow status (see the rule above).
- `python manage.py check` and `makemigrations --check` clean; the suite **not
  worse than the baseline you record before starting**. New tests per item.

  **Run both commands.** `tests/` has no `__init__.py`, so Django's default
  discovery walks straight past it and `manage.py test` alone gives you a green
  light from 5% of the suite:

  ```bash
  python manage.py test tests    # 201 tests — the workflow suite
  python manage.py test          #  11 tests — reports/tests.py
  ```

## Context & decisions already made

Settled in the 2026-08-18 round-planning chat and refined 2026-08-20. **Do not
reopen these; if one looks wrong, put it under "Questions for the handoff
session" and keep going.**

### #32 — what to build

**Cadence.** Three reminders before the deadline — **T−7, T−3, T−1** relative to
`call.evaluation_deadline` — then, once overdue, a digest **every 2 days until
the lockout at deadline + 7 days**, and then nothing. The stop is not arbitrary:
after `is_evaluation_locked()` returns `grace_period_expired` the evaluator
physically cannot submit, so continuing to email them is pure noise. Derive the
stop from the same +7 constant rather than hard-coding a second copy of it.

**Shape.** One email per evaluator per send, listing every one of their pending
evaluations (application code, brief description, call, days remaining, direct
link). Rework the existing `evaluation_reminder` and `evaluation_overdue`
templates to loop over a list rather than describing a single evaluation — do
not add new template types for this.

**Dedupe.** Per (evaluator, day) via `EmailLog`, keyed on
`template__template_type` + `recipient_email` + a date window. A digest spans
several applications, so **do not set `related_application_id`** on it —
`send_waitlist_digest` in `applications/tasks.py` is the pattern to copy,
including how it groups recipients before sending.

**Fold in `notify_overdue_evaluators`.** It has the same per-evaluation
one-email-each problem and it belongs in the same digest. Two things to fix
while you are in there:

- Its dedupe is `subject__icontains='overdue'` — it matches on *rendered subject
  text*. It happens to work because the seeded subject says "is Overdue", but
  rewording the template or translating it silently disables the dedupe. Key it
  on `template__template_type` like every other dedupe in the codebase.
- Its 25-hour query window is what currently keeps it to one send. Once it is a
  cadenced digest, that window is no longer the thing preventing repeats — make
  sure the dedupe is doing the work.

Leave `notify_coordinator_overdue_evaluations` alone: it is already a per-call
digest and its day-0 / day-7 lockout notices to the coordinator are wanted.

**Notification preferences** move from per-evaluation to per-evaluator — check
`notify_reminders` / `notify_evaluation_assigned` once, when deciding whether to
build that evaluator's digest at all.

### #5 — what to build

A coordinator-only panel scoped to **one call**, on `templates/calls/detail.html`
next to the lifecycle buttons (`@coordinator_required`, like the rest of that
page). Two actions to start:

- "Remind evaluators with unsubmitted scores"
- "Remind open feasibility reviews"

Both `GET` a **preview screen** and `POST` to send — the same
confirm-before-anything-leaves pattern as `calls/resolve_confirm.html`. The
preview lists each recipient and, next to them, either *will send* or *skipped —
already reminded today*.

**Recently-reminded recipients are skipped by default, with an override
checkbox** ("send anyway, including people reminded today"). Respecting the
dedupe silently would make the button do nothing right after the daily task ran,
which reads as broken; ignoring the dedupe entirely re-creates the flooding this
bucket exists to stop. Showing the coordinator both lists and letting them
decide is the same principle `acceptance-repair` uses for its expire email.

Both actions call **the same helper functions the beat tasks call**, scoped to
the chosen call and run synchronously per click. Do not duplicate the email
assembly — if a helper is not reusable as written, refactor it so it is, and say
so in the PR.

### #35 — what to build, and where

A beat task nudging applicants who still hold a `draft` on an `open` call, at
**T−7 and T−2 before `submission_end`**, once each, `EmailLog`-deduped per
(application, offset). One new template. Stop at `submission_end` — never nudge
about a call that has closed.

**Put it in `calls/tasks.py`, not `applications/tasks.py`.** Two reasons: the
anchor is `call.submission_end` and that file already owns the
submission-deadline lifecycle (`check_call_deadlines`); and `applications/tasks.py`
belongs to `acceptance-repair` for the duration, so putting it there buys a
merge conflict for nothing. Iterate calls, then their drafts.

Note the deliberate asymmetry with the acceptance flow: nudging someone to
finish their own draft *before* a deadline is exactly the kind of automation
this project wants. It is what happens *after* a deadline that must be human.

### #49 — what to build

`send_completion_reminders` (`applications/tasks.py`) sends a node coordinator
one email per open application. REDIB-2601 has 22 running projects handed off
within days of each other, so every 30-day checkpoint — and the one-time nudge
after `call.execution_end` — arrives as a burst of near-identical mail on one
morning.

Group by recipient and send one digest listing every application awaiting
completion, exactly as `send_waitlist_digest` already does. **Keep the 60/30
cadence and the `_milestone_window` catch-up as they are** — they were settled
and reviewed in `closeout`; only the shape changes. **The applicant half stays
one-per-application** — an applicant has one project and the mail is about
theirs specifically.

## Where things are

- `evaluations/tasks.py:16 send_evaluation_reminders` — the 42-emails loop.
- `evaluations/tasks.py:73 notify_overdue_evaluators` — fold in; fix the
  subject-text dedupe.
- `evaluations/tasks.py:130 notify_coordinator_overdue_evaluations` — leave.
- `evaluations/utils.py:135 is_evaluation_locked` — the +7 lockout. Read it,
  derive from it, do not change it.
- `applications/tasks.py:508 send_waitlist_digest` — **the digest pattern to
  copy**: recipient grouping, dedupe without `related_application_id`, and the
  `_reminder_is_due` / `_milestone_window` helpers next to it.
- `applications/tasks.py:628 send_completion_reminders` — #49's target.
- `calls/tasks.py:12 check_call_deadlines` — #35's neighbour.
- `calls/views.py:308 coordinator_dashboard`, `calls/views.py:614 call_resolve`
  and `templates/calls/resolve_confirm.html` — the coordinator-action and
  confirm-screen patterns for #5.
- Beat schedule: `redib/celery.py:22`. Evaluation reminders run 09:00, overdue
  09:30, coordinator overdue 09:45 — keep that ordering intact.
- Role checks always via `UserRole`; see `CLAUDE.md`.

## Conflict watchlist

`acceptance-repair` is **live in parallel** on port 8002
(`~/projects/ReDIB-Portal-wt/acceptance-repair`). It owns `applications/tasks.py`
and the acceptance half of `applications/views.py`.

- **#49 is gated on it.** Before starting step 4, `git fetch && git rebase
  origin/main` and check that `acceptance-repair` has merged (look for
  `docs/handoffs/acceptance-repair.md` marked *Merged* on `main`). If it has
  not, **park #49**, note it in Status, and open the PR with the first three
  items. It is a ~30-line change that can go inline on `main` later; it is not
  worth a three-way tangle in a file another branch is rewriting.
- Steps 1–3 touch nothing that branch touches.

Shared with `acceptance-repair` regardless — **rebase early and often**:

- `redib/celery.py:22` (both add beat entries)
- `communications/management/commands/seed_email_templates.py` and
  `communications/models.py:16` (`TEMPLATE_TYPES` — both add templates, so both
  generate a choices-only `AlterField` migration; expect to regenerate yours
  after a rebase rather than hand-editing the conflict)
- `templates/calls/detail.html` (they add nothing there, but `main` may move)

## Status

<!-- Keep this current as you work. -->

- [x] Baseline recorded (`test tests`, `test`, `check`, `makemigrations --check`)
      before any change — 201 + 11 tests green, `check` clean, no missing
      migrations (2026-08-20)
- [x] 1. #32 — per-evaluator digest, T−7/−3/−1 then every 2 days to lockout
- [x] 1b. `notify_overdue_evaluators` folded in; subject-text dedupe replaced
- [x] 2. #5 — per-call manual dispatch with preview + override
- [x] 3. #35 — draft nudge at T−7 / T−2, in `calls/tasks.py`
- [x] 4. #49 — completion digest **(gated: rebase first, park if
      `acceptance-repair` has not merged)** — `acceptance-repair` merged to
      `main` 2026-08-20 while this bucket was in progress; rebased
      (resolved conflicts in `seed_email_templates.py`,
      `communications/models.py`, the choices migration — regenerated
      fresh per the conflict watchlist note; `redib/celery.py` auto-merged
      cleanly) and implemented #49 on top
- [x] `/code-review` at **medium**, on this branch, before opening the PR —
      3-finder-angle fan-out + Phase 2 verification, 5 findings, all
      CONFIRMED. 4 fixed: completion-digest milestone dedupe used `min()`
      instead of `max()` (silently dropped a later application's
      execution_end nudge); the feasibility per-call dispatch's dedupe
      collided across a multi-node application's separate
      `FeasibilityReview`s (fixed with a run-scoped snapshot; a narrower
      cross-run gap remains, same structural limitation as backlog #50);
      the evaluator per-call dispatch's dedupe could shadow the full daily
      digest for a different call (fixed via `related_call_id` scoping);
      a hardcoded `timedelta(days=7)` remained in two spots instead of
      `GRACE_PERIOD_DAYS`. The 5th (overdue notices now respect the
      per-evaluator opt-out, per the brief) is a settled-decision question,
      parked above rather than reopened.
- [x] Suite green — record both counts — 315 in `tests/` (was 201 at
      baseline), 11 in `reports/`, both green; `check` clean, no missing
      migrations
- [x] PR opened — [#38](https://github.com/Rtasseff/ReDIB-Portal/pull/38)

## Questions for the handoff session

<!-- Park anything needing the human or `main` here and continue with what does
     not depend on it. Do not guess on these. -->

- `/code-review medium` flagged that folding `notify_overdue_evaluators` into
  the digest means an evaluator who opted out via `notify_reminders` /
  `notify_evaluation_assigned` now gets **zero** overdue warning too (the old
  task sent overdue notices unconditionally, no preference check at all).
  This matches the brief's explicit instruction — "check
  `notify_reminders`/`notify_evaluation_assigned` once, when deciding whether
  to build that evaluator's digest at all" — so I implemented it as written
  rather than reopening it, but flagging it since the practical effect (an
  opted-out evaluator can drift into the 7-day lockout with no warning at
  all) is exactly the kind of silent-miss this bucket exists to prevent.
  Worth a deliberate call: should the overdue half ignore the opt-out (since
  missing a lockout is worse than an unwanted email), or is per-evaluator "no
  reminders at all, including overdue" genuinely what should happen?

## Review

This bucket is in the **`/code-review` at medium** tier
(`docs/developer/worktrees.md` § Review policy): it rewrites an email fan-out
that reaches unpaid volunteers, and adds a coordinator-triggered send. **Run it
yourself on this branch before opening the PR**, at *medium*, so the findings
and your fixes land in the PR — the handoff session then reads only what was
flagged, instead of re-reading the whole diff. Running it from the handoff
session instead costs roughly ten times as much; that is the whole reason the
tier exists.

## Return protocol

1. Keep this doc's **Status** current; note anything you deviated from.
2. `python manage.py check`; `python manage.py makemigrations --check`;
   both test commands — record the pass/fail counts against the baseline you
   took before starting (do not make it worse).
3. Push the branch and open a PR against `main`. PR body = the review
   packet: what changed and why, deviations from this brief, the test
   counts, **every new or reworded email quoted in full for review**, whether
   #49 landed or was parked, and any pre-existing bug you noticed but did not
   fix.
4. The handoff session reviews proportionately to risk (see
   `docs/developer/worktrees.md` § Review policy), merges, and updates the
   registry.

## Running locally (this worktree)

```bash
cd /home/rtasseff/projects/ReDIB-Portal-wt/eval-reminders
source venv/bin/activate
python manage.py runserver 8003
```

`.env`, `db.sqlite3` and `media/` were copied from the `main` checkout at
creation time. To rebuild the sandbox: `python manage.py setup_localtest3_database`
(see `docs/DEVELOPMENT.md`).

**Testing a beat task without waiting a day:** call it directly in
`manage.py shell` and move `call.evaluation_deadline` / `submission_end`
backwards on a sandbox call to land on a cadence day. `EMAIL_BACKEND` is the
console backend in dev, so the rendered mail prints to the runserver output —
which is the fastest way to check that an evaluator with six applications gets
one message listing six, not six messages.
