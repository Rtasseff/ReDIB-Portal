# Handoff — `feature/acceptance-repair`

<!-- Copy of docs/developer/handoff-template.md, seeded by scripts/new-worktree.sh.
     Lives at docs/handoffs/acceptance-repair.md on the branch. Keep "Status" current. -->

| | |
|---|---|
| Branch | `feature/acceptance-repair` |
| Worktree dir | `/home/rtasseff/projects/ReDIB-Portal-wt/acceptance-repair` |
| Base | `main` @ `ca2a389` |
| Created | 2026-08-20 |
| Runserver port | 8002 |
| Handoff session | `main` checkout at `~/projects/ReDIB-Portal/` |

Read this first, then `CLAUDE.md`, then `docs/README.md`. This directory is
a git worktree: it *is* this branch — do not `git checkout` another branch
here (see `docs/developer/worktrees.md`).

**Development document.** These are instructions for the agent session working
in this worktree. Once the branch merges, this file lands on `main` as a
record — on the production VPS it is history, not a task list.

## Goal

Delete the last Celery beat task that writes an applicant-visible state change,
and replace it with a nag and two coordinator actions. Today
`process_acceptance_deadlines` flips an `accepted` or `pending` application to
`expired` and emails the applicant, with no human in the loop. After this
branch, nothing expires unless a node coordinator clicks a button.

**The principle this bucket establishes. Apply it to everything you touch here:**

> **A beat task may compute and notify. Only a human writes a transition.**

The evaluator lockout is the model to copy. `evaluations/utils.py
is_evaluation_locked()` derives "deadline + 7 days" at page load — nothing is
stored, nothing is emailed to the evaluator, and moving the deadline moves the
lockout with it. That is why it is safe to leave automatic. Auto-expire is the
opposite: it writes a terminal status and tells the applicant about it.

**Why this is worth a bucket.** ReDIB is a small, informally coordinated
network running this process systematically for the first time; what came
before was scattered email and people's memories. Everything needs room to be
repaired. An email to an applicant that has to be walked back costs more than a
missed deadline does. And node behaviour is the part ReDIB does not control —
so anything that fires without the ReDIB coordinator knowing surfaces late,
when it is hard to reverse.

## Scope

**In, in this order.** Each step leaves the tree working; do not reorder 4 and
5, or there is a window with no way to expire anything at all.

1. **Delete `access/tasks.py process_acceptance_deadlines`.** Dead code:
   unscheduled, called from nowhere, and its name collides with the live task
   in `applications/tasks.py`. It is worse than the live one — it sets
   `accepted → rejected` with `resolution='rejected'`, not `expired`. Delete
   the function; leave `send_publication_followups` alone.
2. **#52 — the two acceptance templates.** `acceptance_reminder` and
   `acceptance_expired` are written for someone who was granted access, and
   `closeout`'s #17 now sends both to **waitlisted** applicants too. One tells
   them the grant "will be automatically expired **and offered to the next
   applicant on the waiting list**" — nonsense to someone who *is* on the
   waiting list, and an expiring `pending` application frees no allocation at
   all. The other calls their application "**approved**" and refers to "the
   **access grant**" they never had. Branch on status inside the template
   (`{% if is_waitlist %}`) rather than splitting into four templates.
   `acceptance_expired` also stops being automatic — reword it as something a
   coordinator chose to send (see step 4).
3. **Pre-deadline reminder ladder.** Today the applicant gets roughly two
   reminders, both inside the last three days. Make it **day 3, day 7 and day
   9** after `resolution_date` (equivalently, 7 / 3 / 1 days before a 10-day
   deadline). The coordinator nag in step 6 asserts the applicant was chased
   repeatedly; that has to be true.
4. **The two coordinator actions.** New views on the acceptance half of
   `applications/views.py`, buttons on Access Tracking, confirmation screens
   like `waitlist_close_out_confirm.html`. Details below.
5. **Delete the auto-expire branch** from `applications/tasks.py
   process_acceptance_deadlines`. The task keeps its reminder half and its
   name. `_notify_freed_capacity` moves to the manual expire action in step 4 —
   it currently fires from inside the branch you are deleting, so it silently
   stops working if you forget.
6. **The stalled-acceptance nag.** New beat task. Details below.
7. **#18 — reinstate an expired application.** Now the repair path for a
   mis-clicked expire, which is why it is in this bucket. Details below.

**Out** (do not do here — belongs on `main` or another bucket):

- **Do not rewire Access Tracking to admit the `coordinator` role.** It is
  `@node_coordinator_required` and it stays that way — settled, see Decisions.
- **#54** — an auto-closed call has no reopen path. Same family, filed for
  later, explicitly not this bucket.
- **#40** (call lifecycle redesign, ~2027-03) — do not anticipate it.
- Anything in `evaluations/`. The evaluator side is `eval-reminders`, and the
  evaluator lockout described above **stays exactly as it is** — it is the one
  automatic thing Ryan is comfortable with, and this branch must not touch it.
- **#49/#50/#51** — they live in `applications/tasks.py` too, but they are not
  yours. Leave `send_completion_reminders`, `send_waitlist_digest` and
  `send_feasibility_reminders` alone.

## Acceptance

- No Celery beat task writes an `Application.status` anywhere. Grep the beat
  schedule's tasks for `.save(`, `.update(` and `status =` and be able to say
  what each remaining write is.
- An application whose acceptance deadline passes with no applicant response
  stays exactly where it is, indefinitely, and produces a repeating email to
  its node coordinator(s) with the ReDIB coordinator cc'd and a reminder
  counter in the body.
- A node coordinator can expire it or force-accept it, each with a required
  reason, each notifying the ReDIB coordinator.
- Expiring a previously-`accepted` application still fires the freed-capacity
  notice; expiring a `pending` one still does not.
- An expired application can be reinstated to the status its `resolution`
  names, with a fresh deadline.
- `python manage.py check` and `makemigrations --check` clean; the suite **not
  worse than the baseline you record before starting**. New tests for each of
  the seven steps.

  **Run both commands.** `tests/` has no `__init__.py`, so Django's default
  discovery walks straight past it and `manage.py test` alone gives you a green
  light from 5% of the suite:

  ```bash
  python manage.py test tests    # 201 tests — the workflow suite
  python manage.py test          #  11 tests — reports/tests.py
  ```

  `tests/test_phase7_acceptance.py` and
  `tests/test_closeout_waitlist_deadlines.py` both assert the auto-expire
  behaviour you are deleting. **Rewrite them, do not delete them** — they
  become the tests that auto-expire no longer happens and that the nag fires
  instead.

## Context & decisions already made

Settled 2026-08-20 with Ryan. **Do not reopen these; if one looks wrong, put it
under "Questions for the handoff session" and keep going.**

### The deadline still means something

The applicant's accept/decline link **stays closed** once `acceptance_deadline`
has passed. `application_acceptance` already refuses in that case — leave that
behaviour in place. After the deadline the applicant hears **nothing further
from the system** about it; a node coordinator may contact them off-system if
they want. Resolution is entirely in coordinator hands.

One wording fix: that refusal currently says "This application will be marked as
expired," which is no longer true of anything automatic. Reword to say the
deadline has passed and their node coordinator will be in touch.

### It stays the node coordinator's job

Access Tracking is `@node_coordinator_required`, which excludes the plain
`coordinator` role — a superuser can back-door it if it is ever genuinely
needed, and that is enough. **Do not add the `coordinator` role to that
decorator or build a parallel coordinator-facing page.** The ReDIB coordinator's
involvement is by email: cc'd on every nag, notified on every action.

Use `send_email_from_template`'s existing `cc_emails=[...]` argument (see
`communications/tasks.py:16`) — CC'd addresses are visible to everyone so they
can Reply All, which is the point. The nag's body must state plainly that the
**node coordinator** is the one who must act; the ReDIB coordinator is there to
know it is happening.

### The nag repeats, with a counter

Not a one-time notice. First send **1 day after** `acceptance_deadline`, then
**every 3 days**, indefinitely, until the application leaves the stalled state.
The body carries "this is reminder #N". Nagging the nodes is intended and
wanted — do not add a cap or a backoff.

Compute N from `EmailLog`, not a new field:

```python
n = EmailLog.objects.filter(
    template__template_type='stalled_acceptance_reminder',
    related_application_id=app.id,
).values('sent_at__date').distinct().count() + 1
```

Counting **distinct days** rather than rows matters: a node with two active
coordinators produces two rows per send, and both people must see the same
number.

`applications/tasks.py` already has `_reminder_is_due(anchor, first_days,
repeat_days, now)` — use it (`_reminder_is_due(app.acceptance_deadline, 1, 3,
now)`), do not write a second cadence helper.

### Two resolution options, not three

An earlier draft of the nag offered the applicant a chance to act as option 1.
It was dropped when the deadline decision above was settled — do not
reintroduce it, and make sure no email copy implies the applicant can still
click anything.

### Force-accept is the dangerous one

It commits an applicant to an execution window without their word. Node
coordinators keep the power anyway — blocking them just moves the mess back to
private email where nobody can see it — but it must never happen silently:

- A **reason is required** and is stored with the other resolution comments.
- The **ReDIB coordinator is emailed every single time**, with the reason, who
  did it, and which application.

### Applicant email on manual expire — a checkbox, defaulted off

*This one is the handoff session's judgement call rather than Ryan's
instruction; he said the applicant hears nothing further from the system, which
was about the nag. Reasoning: a manual expire is a human act, not an automatic
one, so an email at that moment is coordinator-initiated — the same shape as
the waitlist "not reached" close-out, which does email. But sometimes the node
has already phoned them and a mail is confusing. So put the choice in the
coordinator's hands: a checkbox on the expire confirmation screen, **unchecked
by default**, "also email the applicant". Unchecked → the system stays silent.
If Ryan vetoes it, drop the checkbox and send nothing.*

## What the actions do, precisely

Both live in `applications/views.py` beside `promote_waitlisted_application`
and `close_out_waitlisted_application`, and both reuse
`_can_manage_waitlisted_application(user, application)` — rename it to
`_can_manage_application` if that reads better, updating both existing callers.
Both are `@login_required @transaction.atomic`, both `POST` to act and `GET` to
render a confirmation screen, both require a non-empty `reason`.

**Shared guards** (refuse with a message and redirect if any fails):

- `application.status in ('accepted', 'pending')`
- `application.accepted_by_applicant is None` — nobody has responded
- `application.acceptance_deadline_passed` — **before** the deadline this is
  the applicant's decision, not a coordinator's

### Expire

- `status → 'expired'`, `accepted_by_applicant = False`, `accepted_at = now`.
- Append to `resolution_comments`:
  `[EXPIRED BY COORDINATOR] by <name> on <date>` + the reason.
- **If the prior status was `accepted`** (not `pending`): call
  `_notify_freed_capacity(application, reason='expired')`. A waitlisted
  application holds no allocation and frees nothing — same rule the deleted
  auto-expire branch used, and `closeout`'s tests already assert it.
- If the "also email the applicant" box was ticked: send `acceptance_expired`
  with its step-2 wording.
- Notify the ReDIB coordinator (below).

### Force-accept

Mirrors `application_acceptance`'s accept branch exactly — read it first
(`applications/views.py:~1348`) and match it, including the try/except around
the handoff email.

- `accepted_by_applicant = True`, `accepted_at = now`.
- **Status `accepted`:** fire `_send_handoff_email(application)` and set
  `handoff_email_sent_at`. This is the one system email the applicant does get
  after the deadline, and it is correct — they are being handed off to a node
  and need to know.
- **Status `pending`:** no handoff. The waitlist path defers it until a node
  coordinator promotes the application later. Status stays `pending`.
- Append `[FORCE-ACCEPTED BY COORDINATOR] by <name> on <date>` + the reason.
- Notify the ReDIB coordinator (below).

### Reinstate (#18)

From the application detail page, not Access Tracking — it is a rare repair,
not part of the daily flow. Same authorization and a required reason.

- Guard: `status == 'expired'` and `application.resolution in ('accepted',
  'pending')`.
- `status → application.resolution` — the node's decision is untouched by
  expiry, so it is the honest thing to restore. **No new field is needed;** do
  not add one.
- `accepted_by_applicant = None`, `accepted_at = None`, and set a **fresh**
  `acceptance_deadline` of `now + 10 days`.
- `VALID_TRANSITIONS['expired']` is `[]` today — it becomes
  `['accepted', 'pending']`. Choices do not change, so **no migration**.
- Append `[REINSTATED BY COORDINATOR] ...` + the reason.
- Notify the ReDIB coordinator (below).
- The applicant needs to know their link works again: send them
  `acceptance_reminder` with the new deadline.

## New email templates

Three, all seeded by `seed_email_templates`, all with pre-formatted date
strings (never a raw datetime in `context_data` — see #28's note in
`docs/handoffs/closeout.md`). Add them to `EmailTemplate.TEMPLATE_TYPES`; the
choices-only `AlterField` migration that Django wants is expected and harmless.

**`stalled_acceptance_reminder`** — to each node coordinator of the
application's nodes, `cc_emails` = every active ReDIB `coordinator`. Draft copy,
adapt but keep the shape and the counter:

```
Dear {{ coordinator_name }},

This is reminder #{{ reminder_number }}.

The applicant {{ applicant_name }} has not officially acknowledged their
application's status of {{ status_label }}. The deadline for them to
acknowledge and accept ({{ deadline }}) has passed. They were sent several
reminders before it did.

Application: {{ application_code }} - {{ call_code }}
Applicant:   {{ applicant_name }} ({{ applicant_email }})
Node(s):     {{ node_name }}

Unless there are extenuating circumstances the application itself should be
expired. **The node coordinator must act** - the ReDIB coordinator is copied
on this message for visibility, not to resolve it.

Resolution options:

(1) Expire the application:
    {{ expire_url }}
{% if not is_waitlist %}    Once expired, you may promote a waitlisted application to fill the space.
{% endif %}
(2) Override and force the acceptance on the applicant's behalf:
    {{ force_accept_url }}
    Not recommended. You must be sure the applicant is prepared to start work
    within the execution window{% if is_waitlist %}, and this moves them from the
    waiting list to accepted{% endif %}. A reason is required and the ReDIB
    coordinator is notified.

Best regards,
The ReDIB COA Team
```

**`stalled_acceptance_actioned`** — to every active ReDIB `coordinator`, sent by
all three actions. One template, with `action` (`expired` /
`force-accepted` / `reinstated`), `actioned_by`, `reason`, the application
details, and a line stating what changed. Keep it factual; this is an audit
trail Ryan reads, not a notification he acts on.

**No new template for the applicant.** Reinstate reuses `acceptance_reminder`;
expire optionally reuses `acceptance_expired`; force-accept uses the existing
handoff email.

## Where things are

- The live task: `applications/tasks.py:299 process_acceptance_deadlines` —
  reminder half at the top, the auto-expire branch you are deleting from
  `# === DAY 10+: Auto-Expire ===`.
- The dead one: `access/tasks.py:16`, same name, different app.
- Applicant accept/decline: `applications/views.py:1302
  application_acceptance`.
- The coordinator-action pattern to copy:
  `applications/views.py close_out_waitlisted_application` and
  `templates/applications/waitlist_close_out_confirm.html`, both landed last
  week in `closeout` (PR #36).
- Access Tracking buttons: `templates/access/access_tracking.html:~49`.
- Beat schedule: `redib/celery.py:22`. The acceptance task runs at 10:00;
  put the nag after it.
- Role checks always via `UserRole` — see `CLAUDE.md`.

## Conflict watchlist

This branch **owns** `applications/tasks.py` and the acceptance half of
`applications/views.py` for its lifetime. Also touched, and shared with other
work — rebase early if `main` moves:

- `redib/celery.py:22` (beat schedule)
- `communications/management/commands/seed_email_templates.py` and
  `communications/models.py:16` (`TEMPLATE_TYPES`)
- `templates/access/access_tracking.html`
- `applications/models.py` (`VALID_TRANSITIONS` only)

`eval-reminders` may be cut in parallel; it owns `evaluations/tasks.py` and will
touch the same beat schedule and seed command. Nothing else is live.

## Status

<!-- Keep this current as you work. -->

- [x] Baseline recorded before any change: `test tests` **201 OK**, `test`
      **11 OK**, `check` clean, `makemigrations --check` clean
- [x] 1. dead `access/tasks.py process_acceptance_deadlines` deleted (the
      now-unused `AccessGrant` import went with it; `send_publication_followups`
      untouched)
- [x] 2. #52 — acceptance templates reworded for waitlist + manual expiry,
      branching on `{% if is_waitlist %}` inside the template as instructed
- [x] 3. pre-deadline reminder ladder — **7 / 3 / 1 days before the
      deadline**. See Deviations: anchored on `acceptance_deadline`, not
      `resolution_date`.
- [x] 4. expire + force-accept actions, with `_notify_freed_capacity`'s call
      site moved out of the deleted branch and into the expire action
- [x] 5. auto-expire branch deleted
- [x] 6. stalled-acceptance nag beat task, cc + counter (10:15, after the
      10:00 reminder task)
- [x] 7. #18 reinstate
- [x] `tests/test_phase7_acceptance.py` and
      `tests/test_closeout_waitlist_deadlines.py` rewritten, not deleted
- [x] `/code-review` at **medium**, on this branch, before opening the PR
- [x] Suite green — `test tests` **278 OK** (from 201), `test` **11 OK**;
      `check` and `makemigrations --check` clean
- [x] PR opened — [#37](https://github.com/Rtasseff/ReDIB-Portal/pull/37), rebased onto `main` @ `69caa17`

### `/code-review` at medium — findings and disposition

Ten findings, ordered by the reviewer's severity. Eight fixed on this branch,
one message-only fix over a pre-existing hole, one reported rather than
changed. Regression tests for the fixes live in
`tests/test_acceptance_repair.py::ReviewFindingsTest`.

| # | Finding | Disposition |
|---|---|---|
| 1 | `resolution_accepted` still promised "your access will expire automatically" | **Fixed.** Reworded to match the acceptance templates. This is the first email an accepted applicant gets; leaving it would have contradicted everything downstream. |
| 2 | `resolution_pending` carried the identical false promise | **Fixed**, same wording. |
| 3 | `freed_capacity_notice` said the application "auto-expired without a response" | **Fixed** → "was expired by a coordinator after the applicant did not respond". Its only `reason='expired'` caller is now the coordinator's own click, so it was telling them the system did what they had just done. |
| 4 | The nag's option (2) told coordinators force-accept "moves them from the waiting list to accepted" | **Fixed.** It does not — `force_accept_stalled_application` deliberately leaves `status='pending'`. The wording came from this brief's draft copy but contradicted the brief's own spec, so I followed the spec. |
| 5 | The nag could reach **nobody**, silently | **Fixed.** Node coordinators are the only `To`, and CC cannot exist without one — so a node with no active coordinator (or all with reminders off) sent zero mail while the task reported success. Now falls back to addressing the ReDIB coordinator directly, with a template line saying why, and logs a warning. This was the one finding that defeated the bucket's own purpose. |
| 6 | `handoff_sent` could never be `False`, so the audit email could claim a handoff that never went out | **Fixed.** `send_email_from_template` catches everything and returns `False` rather than raising, so the mirrored `try/except` never fired. `_send_handoff_email` now returns its result and force-accept checks it; `handoff_email_sent_at` is stamped only on a real send. See Deviations 6. |
| 7 | The 7/3/1 ladder had no catch-up — a beat outage on a rung lost it permanently | **Fixed.** Rungs are now counted owed-vs-sent within the acceptance window rather than matched to an exact day, so a missed rung is caught up on the next run. The nag asserts the applicant "was sent several reminders"; a silently skipped rung would have made that false. |
| 8 | An `accepted`/`pending` application with a NULL `acceptance_deadline` is unreachable by every path | **Message fixed; hole reported.** Verified **pre-existing, not a regression** — the deleted auto-expire filtered on `acceptance_deadline__lt=now` and skipped these too. The refusal now says there is no deadline recorded instead of claiming one "has not passed yet". The underlying gap (such an application is invisible to the nag, both actions, and has a permanently open applicant link) belongs in the backlog. |
| 9 | Node coordinators were not filtered on a non-empty email, unlike the CC list | **Fixed.** A blank address produced a failed `EmailLog` row that then satisfied the dedupe for every other blank-address user. |
| 10 | All three actions send email synchronously inside `@transaction.atomic` | **Reported, not changed.** Real, but inherited verbatim from `close_out_waitlisted_application` — the pattern this brief explicitly named as the one to copy. Switching these three to `.delay()` while their sibling stays synchronous would be worse than either consistent choice. Worth a follow-up that converts the whole acceptance half at once. |

### Acceptance criterion: no beat task writes an `Application.status`

Every task in `redib/celery.py`'s beat schedule was walked with
`inspect.getsource` and grepped for `.save(`, `.update(` and `status =`.
The only remaining **writes** are in `calls.tasks.check_call_deadlines`,
and both are on `Call`, not `Application`:

| Task | Write | What it is |
|---|---|---|
| `calls.tasks.check_call_deadlines` | `open_announced_calls()` → `announced` → `open` | Date-driven, on `submission_start`. Public-page visibility, not an applicant-specific state change; has a view-level fallback. |
| `calls.tasks.check_call_deadlines` | `expired_calls.update(status='closed')` | `open` → `closed` on `submission_end`. This is the one #54 flags as having no reopen path — filed, explicitly not this bucket. |

Everything else the grep matched is a `status='...'` **filter** keyword, not
an assignment. `process_acceptance_deadlines`,
`send_stalled_acceptance_reminders` and `send_publication_followups` contain
no writes of any kind. A regression test locks this in:
`Step5NoBeatTaskWritesStatusTest.test_every_scheduled_application_task_leaves_statuses_alone`
runs every scheduled `applications.*` / `access.*` task against three live
applications and asserts none of their statuses moved.

### Deviations from this brief

1. **The reminder ladder is anchored on `acceptance_deadline`, not
   `resolution_date`.** The brief gives "day 3 / 7 / 9 after
   `resolution_date`" and "7 / 3 / 1 days before a 10-day deadline" as
   equivalent, and for a normal application they are. They diverge after a
   reinstate (step 7), which sets a fresh `acceptance_deadline` of now + 10
   days while leaving `resolution_date` where it was: anchored on
   `resolution_date` the ladder would never fire again on the new window.
   Covered by `test_reinstated_application_runs_the_reminder_ladder_again`.
2. **The "also email the applicant" checkbox on manual expire is
   implemented as the handoff session proposed** — present, unchecked by
   default, silent if left unticked. This was flagged in the brief as the
   handoff session's judgement rather than Ryan's instruction. See Questions.
3. `_notify_freed_capacity` itself stays in `applications/tasks.py`; only its
   call site moved to `applications/views.py`. Its docstring was updated —
   it no longer describes an auto-expire caller.
4. `applications/views.py` gained module-level `from django.conf import
   settings` and `from datetime import timedelta`; both were previously only
   available via function-local imports.
5. `application_detail`'s context gained `can_manage_application`, so the
   detail template can offer the reinstate button on exactly the same terms
   as the Access Tracking actions.
6. **Force-accept does not mirror `application_acceptance` exactly**, despite
   the brief's instruction to match it including the try/except. The mirrored
   code stamps `handoff_email_sent_at` whenever no exception escapes — but
   `send_email_from_template` never raises, it returns `False`. Copying it
   faithfully would have made the new audit email tell the ReDIB coordinator a
   handoff had gone out when it had not, which is precisely the kind of claim
   this bucket exists to make trustworthy. `_send_handoff_email` now returns
   its result and force-accept checks it. The two pre-existing callers
   (`application_acceptance`, `promote_waitlisted_application`) are unchanged
   and still ignore the return value — worth fixing on `main`, but not
   this branch's to touch.
7. Two email templates outside the brief's step 2 were reworded
   (`resolution_accepted`, `resolution_pending`), plus `freed_capacity_notice`.
   All three asserted that expiry was automatic, which this branch made false.
   Review finding, see the table above.

## Questions for the handoff session

<!-- Park anything needing the human or `main` here and continue with what does
     not depend on it. Do not guess on these. -->

- **The "also email the applicant" checkbox on manual expire needs Ryan's
  yes or no.** The brief marks it as the handoff session's judgement call,
  not his instruction. It is built and defaulted off, so the system stays
  silent unless a coordinator deliberately ticks it. If Ryan vetoes it,
  removing it is small: drop the `notify_applicant` block from
  `expire_stalled_application`, drop the `form-check` from
  `templates/applications/expire_stalled_confirm.html`, and delete
  `test_expire_emails_the_applicant_when_the_box_is_ticked`. The reworded
  `acceptance_expired` template would then have no live caller — worth
  deciding whether to keep it seeded for manual use or retire it.
- **Nothing else was blocked.** Every scope item is complete.

## Review

This bucket is in the **`/code-review` at medium** tier
(`docs/developer/worktrees.md` § Review policy): it changes an
applicant-facing email fan-out, adds coordinator actions that write terminal
statuses, and deletes an automatic one. **Run it yourself on this branch before
opening the PR**, at *medium*, so the findings and your fixes land in the PR —
the handoff session then reads only what was flagged, instead of re-reading the
whole diff. Running it from the handoff session instead costs roughly ten times
as much; that is the whole reason the tier exists.

## Return protocol

1. Keep this doc's **Status** current; note anything you deviated from.
2. `python manage.py check`; `python manage.py makemigrations --check`;
   both test commands — record the pass/fail counts against the baseline you
   took before starting (do not make it worse).
3. Push the branch and open a PR against `main`. PR body = the review
   packet: what changed and why, deviations from this brief, the test
   counts, **every new or reworded email quoted in full for review**, and any
   pre-existing bug you noticed but did not fix.
4. The handoff session reviews proportionately to risk (see
   `docs/developer/worktrees.md` § Review policy), merges, and updates the
   registry.

## Running locally (this worktree)

```bash
cd /home/rtasseff/projects/ReDIB-Portal-wt/acceptance-repair
source venv/bin/activate
python manage.py runserver 8002
```

`.env`, `db.sqlite3` and `media/` were copied from the `main` checkout at
creation time. To rebuild the sandbox: `python manage.py setup_localtest3_database`
(see `docs/DEVELOPMENT.md`).

**Testing a beat task without waiting a day:** call it directly in
`manage.py shell` (`from applications.tasks import send_stalled_acceptance_reminders;
send_stalled_acceptance_reminders()`) and move `acceptance_deadline` backwards
on a sandbox application to land on a cadence day. `EMAIL_BACKEND` is the
console backend in dev, so the rendered mail prints to the runserver output —
which is also the fastest way to proof-read the copy above.
