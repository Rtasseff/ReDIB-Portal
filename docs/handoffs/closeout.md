# Handoff — `feature/closeout`

<!-- Copy of docs/developer/handoff-template.md, seeded by scripts/new-worktree.sh.
     Lives at docs/handoffs/closeout.md on the branch. Keep "Status" current. -->

| | |
|---|---|
| Branch | `feature/closeout` |
| Worktree dir | `/home/rtasseff/projects/ReDIB-Portal-wt/closeout` |
| Base | `main` @ `c883be7` (rebased 2026-08-19) |
| Created | 2026-08-19 |
| Runserver port | 8002 |
| Handoff session | `main` checkout at `~/projects/ReDIB-Portal/` |

Read this first, then `CLAUDE.md`, then `docs/README.md`. This directory is
a git worktree: it *is* this branch — do not `git checkout` another branch
here (see `docs/developer/worktrees.md`).

**Development document.** These are instructions for the agent session working
in this worktree. Once the branch merges, this file lands on `main` as a
record — on the production VPS it is history, not a task list.

## Goal

Give REDIB-2601 an ending. The call has been sitting at `closed` since its
submission deadline: 22 accepted projects are running with nobody nudging them
to record hours or mark themselves done, 7 waitlisted applicants have heard
nothing since they accepted in June, and there is no UI path to move the call to
`resolved` at all. This bucket adds the missing end-of-lifecycle machinery —
reminders, a waitlist outcome, and a close-out action — and fixes the three small
bugs sitting in the same code path while we are in it.

**Why the date matters.** REDIB-2601's execution window closes **2026-10-30**.
A reminder deployed in October has almost no runway. Merge by **2026-09-11**, in
prod by **2026-09-15** — that date is the point of the bucket, not a nicety.

## Scope

**In**, and this is the order to build them (rationale in "Decisions" below):

1. **#45** — `send_feasibility_reminders` has no dedupe *and* still emails only
   the original assignee. High, ~15 lines, and the smallest thing here. Left
   over from #9; see the note below before you fan anything out.
2. **#17** — `process_acceptance_deadlines` ignores waitlisted applicants. High,
   ~one line in two places, plus verification.
3. **#28** — datetimes in Celery `context_data`. Small; **the backlog diagnosis
   is partly wrong, read the note below before fixing.**
4. **#36** — call close-out: `closed → resolved` + `is_resolution_locked` from
   the UI. Must land before #30 because it is what fires #30's closure email.
5. **#30** — waitlist follow-up, three parts (a) coordinator digest, (b) "not
   reached this call" close-out action + applicant email, (c) freed-capacity
   notice.
6. **#29** — execution-phase completion reminders (applicant + node
   coordinators).

**Stretch — only once all six are green and committed:** #35, the draft nudge
at T−7 / T−2 before `submission_end`. Same shape, same files, near-zero marginal
setup cost. If time is short, drop it without hesitation; it is wanted for the
October call, not for REDIB-2601.

**Out** (do not do here — belongs on `main` or another bucket):

- Anything that changes application statuses beyond the single new terminal
  value #30(b) needs. No release gate (#15), no node-accepted/applicant-accepted
  split (#16), no reinstate-expired (#18).
- **#34 / #26 — email delivery truth.** You will notice that
  `applications/tasks.py` calls `send_email_from_template(...)` **synchronously**
  rather than `.delay(...)`, so a failed send blocks the beat task and is logged
  and forgotten. That is a real bug and it is *not yours* — it is #34/#26, going
  inline on `main` after this bucket merges. Match the surrounding style; do not
  convert the existing calls.
- Evaluator reminder flooding (#32) — that is `eval-reminders`, the next bucket.
- The call lifecycle redesign (#40). It is agreed in principle and deliberately
  deferred to ~2027-03; see `docs/developer/call-lifecycle-proposal.md`. **Do not
  anticipate it.** #36 adds a manual "Mark call resolved" action to the *current*
  status field, which is exactly what the proposal says stays manual.

## Acceptance

- REDIB-2601 can be walked to `resolved` from the UI, with resolution locked,
  and with **no email side-effects** from that action itself.
- Every reminder fires on its stated cadence against a seeded sandbox and **does
  not double-send** when the task runs twice on the same day.
- Waitlisted applications get the day-7 acceptance reminder and the day-10
  expiry (#17), and a waitlist row can be closed out as "not reached this call"
  with the applicant emailed exactly once.
- Every new email is seeded by `seed_email_templates` and renders **pre-formatted
  date strings** (#28).
- `python manage.py check` and `makemigrations --check` clean; the suite **not
  worse than the baseline you record before starting**. New tests for each item.

  **Run both commands.** `tests/` has no `__init__.py`, so Django's default
  discovery walks straight past it and `manage.py test` alone gives you a green
  light from 6% of the suite:

  ```bash
  python manage.py test tests    # 162 tests — the workflow suite
  python manage.py test          #  11 tests — reports/tests.py
  ```

  Both were green on `main` @ `c883be7`. Do not "fix" this by adding
  `tests/__init__.py` — it is backlog #46, deliberately not this bucket.

## Context & decisions already made

These are settled — from `docs/developer/round-october-2026.md` § 4.3 and the
2026-08-18 round-planning chat. **Do not reopen them; if one looks wrong, put it
under "Questions for the handoff session" and keep going.**

### Cadences

| Reminder | Cadence |
|---|---|
| #29 completion reminders | first at **60 days** after `handoff_email_sent_at`, then every **30 days**, plus one the day after `call.execution_end`; stop when `is_completed=True` |
| #30(a) waitlist digest | first at **30 days** after the applicant's acceptance, then every **30 days**, plus one the day after `call.execution_end` |
| #35 draft nudge (stretch) | T−7 and T−2 days before `submission_end` |

### Who gets nagged, and who does not

**Waitlisted applicants get no recurring reminder.** They cannot act on it — it
reads as nagging someone about a decision that is not theirs. The split is:

- **Node coordinator** gets the recurring action reminder (#30a): "have any of
  these been promoted? if the slot will not open this call, close them out."
- **Applicant** gets exactly **one** email — the "not reached this call" closure
  from #30(b) — and it is the `closed → resolved` transition in #36 that makes
  that closure meaningful. This is why #30 and #36 ship together.

### The new terminal status (#30b)

A waitlisted application whose capacity never opened has no honest status today.
`rejected` is wrong — they were not rejected, and it would collide with the
competitive-funding reject protection. `expired` is wrong — they *did* respond,
on time. So add one value:

```python
('not_reached', 'Not Reached This Call'),   # terminal, waitlist close-out
```

Settled, so you do not have to design it:

- **Name it `not_reached`.** Terminal. Set only by the close-out action, never by
  a task.
- It needs a **reason field** (free text, on the action form, stored where the
  other resolution comments live) and the `waitlist_not_reached` applicant email.
- The **competitive-funding reject protection does not apply** — this is not a
  resolution-phase reject and must not be routed through
  `has_any_denied_evaluation`. Do not touch
  `applications/services/node_resolution.py` or `resolution.py`.
- Adding the value is contained: only `applications/models.py`
  (`APPLICATION_STATUSES`, ~line 56), `templates/includes/status_badge.html`,
  `applications/views.py`, and the two test-data commands mention comparable
  terminals today. **Grep for `declined_by_applicant` and handle every place it
  appears** — that is the checklist. Django will want an `AlterField` migration
  for the choices change; that is expected and harmless.

### Dedupe

Dedupe every reminder against `EmailLog`, the way the existing tasks do — query
by `template` + `related_application_id` + a date window. Every one of these
tasks will run daily against live data; a task that double-sends on a restart is
worse than one that does not exist.

### #28 — verify before you fix

The backlog says the `acceptance_expired` email passes a raw datetime that
"Celery's JSON serializer delivers to the worker as an ISO string". **That
diagnosis is wrong as written**, and the handoff session checked:
`applications/tasks.py` calls `send_email_from_template(...)` **synchronously**,
so nothing is serialized and the datetime arrives intact. Every `.delay()` site
in `applications/views.py` already pre-formats (`submission_end.strftime(...)`),
and `calls/services.py` pre-formats too.

So the real content of #28 is **prophylactic, and it is still worth doing**:

- The raw-datetime values are at `applications/tasks.py:~338` (`'deadline':
  app.acceptance_deadline`) and `:~52` (`'deadline':
  review.application.call.evaluation_deadline`). Pre-format both to strings.
- **Every new task you write in this bucket puts strings in `context_data`, full
  stop** — no dates, no model instances, no `Decimal`. That is the rule that
  survives someone later converting these calls to `.delay()`.
- Finish the audit: `grep -rn 'context_data' --include=*.py .` and check the
  value types. Correct the backlog entry's diagnosis in your PR body so the next
  reader is not misled.

### #45 — fix the dedupe *before* the fan-out, not after

`send_feasibility_reminders` (`applications/tasks.py:15`) has two defects and
the order you fix them in matters.

Its docstring says it sends only if "no reminder sent in last 3 days". **That
check does not exist.** There is no `EmailLog` query anywhere in the function.
Compare `process_acceptance_deadlines` (`:278`) and
`evaluations.tasks.send_evaluation_reminders` (`:97`), which both do it properly
— copy one of those. So today, once a feasibility review is 5 days old, its
reviewer is emailed **every morning at 09:00** until they act.

It also emails `review.reviewer` only, while #9 (shipped, PR #34) fanned the
initial `feasibility_request` out to every active node coordinator of the node.
The reminder should match — **but do the dedupe first.** Fanning out a
daily-repeating email multiplies it by the coordinator count, which is how the
evaluator side ended up sending two people 42 reminders each (#32, next bucket).

Reuse the fan-out query from `applications/views.py:~834` (the #9 fan-out) so the reminder and
the request address the same people:

```python
UserRole.objects.filter(node=review.node, role='node_coordinator', is_active=True)
```

Dedupe **per (review, recipient)**, not per review — otherwise one coordinator
being emailed suppresses the others. Keep the existing
`notification_preferences` opt-out check, and apply it per recipient. While you
are in this function, its `'deadline'` context value is one of #28's two raw
datetimes; fix it here rather than making a second pass.

### #17 — the two filters, and what changes downstream

`process_acceptance_deadlines` (`applications/tasks.py:241`) filters
`status='accepted'` in **both** branches — the day-7 reminder (`:263`) and the
day-10 auto-expire (`:316`). Change both to
`status__in=['accepted', 'pending']`. Then check the consequences, because this
is the item most likely to have a tail:

- A `pending` application that auto-expires goes to `expired`, same as an
  accepted one. That is intended — they were offered a slot and did not answer.
- **An expiring `pending` application frees nothing**, because a waitlisted
  applicant holds no allocation. Make sure #30(c)'s freed-capacity notice does
  **not** fire for it.
- Re-read the reminder/expiry email context for a `pending` application. The
  wording is written for someone who was granted access; check it is not
  actively wrong for a waitlist offer, and if it is, say so rather than
  rewording the shared template unilaterally.

### #36 — do not press the legacy button

The only existing lock path is `finalize_resolution`
(`applications/services/resolution.py:~234`), the legacy ReDIB-coordinator bulk
flow. It **re-dispatches resolution notifications**, so it is not safe to press
on a call whose node resolutions already went out — which is exactly REDIB-2601.

Build a *separate* small coordinator action on call detail: "Mark call resolved"
→ `status='resolved'` + `is_resolution_locked=True`, **no email side-effects**,
guarded by "no application still in `evaluated`". Confirmation screen before it
commits. Do not refactor `finalize_resolution`; leave it where it is.

### Where things are

- Beat schedule: **`redib/celery.py:22`** (`app.conf.beat_schedule`) — *not*
  `redib/settings.py`, whatever `round-october-2026.md` § 3 says.
- Email template seeding: **`communications/management/commands/seed_email_templates.py`**
  — *not* `core/...`, same caveat. New `template_type` values also need adding to
  `communications/models.py` `TEMPLATE_TYPES` (line 16) and get a
  migration.
- Access Tracking: `access/urls.py:12` → `access:access_tracking`. The waitlist
  promotion action is `applications:promote_waitlisted`
  (`applications/urls.py:52`) — it grew a confirmation screen in #31; **read it
  before adding #30's close-out action beside it** and match its shape.
- `Call.execution_end` / `is_resolution_locked`: `calls/models.py:43` / `:53`.

## Conflict watchlist

**This bucket owns `applications/tasks.py` for its lifetime** — nothing on
`main` or in another bucket edits that file until it merges. Also touched
elsewhere:

- **`redib/celery.py`** (`beat_schedule`) and
  **`communications/management/commands/seed_email_templates.py`** — every
  bucket that adds an email touches these. **Append at the end; on conflict keep
  both sides.** That turns a scary conflict into a mechanical one.
- **`calls/models.py`** — `release-gate` (#15) adds a field here in December and
  its brief says to read what #36 did first. Keep #36's model change minimal.
- **`applications/views.py`** — large and shared. Rebase on `main` early if you
  see it move.
- `main` is also carrying #34/#26 inline **after** this merges, in the same
  email module. Merge first, and you avoid it entirely.

## Status

<!-- Keep this current as you work. -->

- [x] Baseline recorded (`test`, `check`, `makemigrations --check`) before any change
      — `manage.py test tests`: 162 passed. `manage.py test`: 11 passed. Both
      clean on `check` / `makemigrations --check` @ `c883be7`.
- [x] #45 feasibility reminder: dedupe first, then fan out
- [x] #17 acceptance deadlines include waitlisted applicants
- [x] #28 datetimes pre-formatted + `context_data` audit
- [x] #36 "Mark call resolved" action
- [x] #30(a) waitlist digest to node coordinators
- [x] #30(b) "not reached this call" close-out + applicant email
- [x] #30(c) freed-capacity notice on expiry/decline
- [x] #29 completion reminders (applicant + node coordinators)
- [x] `/code-review` at **medium**, on this branch, before opening the PR
      — 6 findings, all applied except the `call_resolve` guard scope
      (flagged above instead, per the brief's own settled scope). See PR
      body for the full list and what changed.
- [x] Suite green — `manage.py test tests`: 201 passed (162 baseline + 39
      new). `manage.py test`: 11 passed. `check` / `makemigrations --check`
      clean.
- [x] PR opened — https://github.com/Rtasseff/ReDIB-Portal/pull/36
- [ ] *(stretch)* #35 draft nudge — **dropped**, per brief's own
      "drop it without hesitation" guidance: all six required items plus
      their test coverage and the code review already consumed the budget
      this bucket warranted, and #35 is wanted for the October call, not
      REDIB-2601.

## Questions for the handoff session

<!-- Park anything needing the human or `main` here and continue with what does
     not depend on it. Do not guess on these. -->

- **`call_resolve`'s guard only checks `status='evaluated'`, per this brief's
  own spec** ("guarded by 'no application still in evaluated'"). `/code-review`
  flagged that this lets a coordinator mark a call resolved while it still has
  applications earlier in the pipeline (`under_feasibility_review`,
  `pending_evaluation`, `under_evaluation`) or applications mid-way through
  their 10-day accept/decline window (`accepted`/`pending` with
  `accepted_by_applicant` unset). For REDIB-2601 specifically this can't
  happen — everything left is `evaluated`-and-resolved or already terminal —
  but as a general guard for future calls it's narrower than "is this call
  actually done." Left exactly as specified rather than widening it
  unilaterally, since #40 (deferred call-lifecycle redesign, ~2027-03) is the
  place a broader "is this call done" concept belongs. Flagging for a
  decision: tighten the guard now, or fold into #40.

## Review

This bucket is in the **`/code-review` at medium** tier
(`docs/developer/worktrees.md` § Review policy): it adds email fan-out and a new
terminal application status. **Run it yourself on this branch before opening the
PR**, at *medium*, so the findings and your fixes land in the PR — the handoff
session then reads only what was flagged, instead of re-reading the whole diff.
Running it from the handoff session instead costs roughly ten times as much;
that is the whole reason the tier exists.

## Return protocol

1. Keep this doc's **Status** current; note anything you deviated from.
2. `python manage.py check`; `python manage.py makemigrations --check`;
   `python manage.py test tests` **and** `python manage.py test` — record both
   pass/fail counts against the baseline you took before starting (do not make
   either worse).
3. Push the branch and open a PR against `main`. PR body = the review
   packet: what changed and why, deviations from this brief, the test
   counts, **the exact subject + body of every new email quoted for review**,
   whether you ran `/code-review` and what it found, and any pre-existing bug
   you noticed but did not fix.
4. The handoff session reviews proportionately to risk (see
   `docs/developer/worktrees.md` § Review policy), merges, and updates the
   registry.

## Running locally (this worktree)

```bash
cd /home/rtasseff/projects/ReDIB-Portal-wt/closeout
source venv/bin/activate
python manage.py runserver 8002
```

`.env`, `db.sqlite3` and `media/` were copied from the `main` checkout at
creation time. To rebuild the sandbox: `python manage.py setup_localtest3_database`
(see `docs/DEVELOPMENT.md`).

**Testing a beat task without waiting for a cadence.** These tasks are plain
functions — call them from `manage.py shell` (`from applications.tasks import
...; send_completion_reminders()`) after back-dating `handoff_email_sent_at` /
`accepted_at` on a seeded application. Then call again immediately and assert
nothing new lands in `EmailLog`; that second call is the dedupe test and it is
the one that matters in production.
