# Round plan — October 2026 call

> **Development document.** This plans and directs work in a dev checkout. On the
> production VPS (`/home/deploy/ReDIB-Portal/`) it is background context only — read
> it, don't act on it. Problems found in production go into
> [backlog.md](backlog.md) as new entries; the work itself happens in dev and arrives
> via `git pull origin main`.

**Status: active** (opened 2026-08-18). This is the operating plan for the
2026–27 COA round: what ships, in what order, in which worktree, by when,
and what must be on the production server before each hard date.

It is expected to outlive many agent sessions. **On restart, read this file
plus [worktrees.md](worktrees.md) and you have the whole picture** — the
bucket sections below contain enough to write a `docs/handoffs/<slug>.md`
brief without re-deriving anything. Item numbers refer to
[backlog.md](backlog.md); this file does not restate their diagnoses.

Keep the **Live status** table at the bottom current. When a bucket merges,
mark it there and in the worktrees registry in the same commit.

---

## 1. The two dates everything hangs off

| Date | Event |
|---|---|
| **~2026-09-15** | ReDIB **announces** the new call (`announced`, public on `/calls/`, accepting `ConsultRequest`s). |
| **~2026-10-15** | The call **opens** — `submission_start` passes, applicants submit. First real application enters the workflow. |

A third date closes the previous round: **2026-10-30**, when REDIB-2601's
execution phase ends. Anything meant to nudge that call's participants has
to be live weeks before it, not on it.

### Estimated phases of the new call

Derived from REDIB-2601's shape, **not yet confirmed**. When the `Call`
object is created in the portal, replace these with its real dates:

| Phase | Estimate |
|---|---|
| Submissions open → close | 2026-10-15 → ~2026-11-30 |
| Feasibility review | ~2026-12 |
| Evaluation | ~2026-12 → ~2027-01 |
| Resolution + acceptance windows | ~2027-01 → ~2027-02 |
| Execution starts | ~2027-03 |

## 2. The production deadline rule

Merging is not shipping. Each bucket below carries a **"in prod by"** date,
and that is the date that matters. Two consequences:

- **Pre-open (now → ~2026-10-13): deploy after every merge.** Deploys are
  cheap while no live application exists. Do not batch them up.
- **Post-open (~2026-10-15 onward): every deploy lands in a live call.**
  Take a `scripts/backup-db.sh` snapshot before anything with a migration,
  pick a window when no beat task is about to fire, and re-check the public
  `/calls/` pages and the applicant dashboard afterwards.

Deploy machinery itself has one known defect: **#37**, the three app containers
racing to run `migrate`. Fix it before the December `release-gate` deploy — see
§ 5.

**On the announcement critical path** — must be in prod by ~2026-09-12:

- **#27** (CallForm status guard) — announcing is done through that form, and
  the 2026-08-18 prod walkthrough found two silent bad states it lets a
  coordinator create. **Fixed in PR #34.**
- **The announcement email is off** (`CALL_ANNOUNCEMENT_EMAILS_ENABLED=False`,
  shipped inline 2026-08-18). Ryan and the node coordinators announce by hand
  with the `/calls/` link; the portal's job for 09-15 is only to have the call
  listed as upcoming on `/calls/`, which already works. Re-enabling is #41,
  wanted before the ~2027-05 call and built on top of #40 — see
  [call-lifecycle-proposal.md](call-lifecycle-proposal.md).

That is the whole announcement path. It was briefly a bucket of its own
(`announce-email`, #38 + #39) on 2026-08-18; Ryan's call to turn the fan-out
off instead removed it from the round.

**On the first-application critical path** — must be in prod by 2026-10-15:

- **#9** (feasibility fan-out) — **shipped and deployed 2026-08-19.** But it
  only helps a node that *has* an active coordinator, and **#48** says a node
  without one is silently dropped from feasibility review entirely. Fix #48
  inline once `closeout` merges.
- **Coordinator coverage — checked on prod 2026-08-19: every node has at least
  one active `node_coordinator`.** So #48 is latent rather than firing, and
  `aac.bioimac@ucm.es` is in place at BioImaC despite the loader still being
  blocked by #43. Re-run the check after any role change during call prep:

  ```python
  from core.models import Node, UserRole
  for n in Node.objects.order_by('code'):
      c = UserRole.objects.filter(node=n, role='node_coordinator', is_active=True).count()
      print(f'{n.code:16} {c} active coordinator(s)', '  <-- NONE' if not c else '')
  ```

Not on the critical path but worth knowing: **#35**'s draft nudge must be live
about a week before `submission_end` (~2026-11-23); **#17/#28** are not needed
until the acceptance windows (~2027-01); **#20** is not needed until results
are published (~2027-01/02).

## 3. Buckets

Six buckets, at most **two branch sessions live at once** plus the handoff
session on `main` — the human relays between them, and that is the real
bandwidth limit. Ports are reused as buckets retire; the registry table in
[worktrees.md](worktrees.md) is the source of truth for what is live.

"Cut from" names the bucket that must merge first, not a calendar date.

| # | Slug | Items | Cut after | Merge by | In prod by | Model | Review |
|---|---|---|---|---|---|---|---|
| 1 | `baseline` | 7, 8, 31 | — (`main`) | 2026-08-21 | 2026-08-22 | Sonnet | diff read + suite |
| 2 | `call-hardening` | 27, 33, 13-min, 9 | — (`main`) | 2026-09-08 | **#27 by 09-12**, rest by 10-13 | Sonnet | targeted read + suite |
| 3 | `closeout` | 45, 17, 28, 36, 30, 29 (35 stretch) | `baseline` | 2026-09-11 | 2026-09-15 | Sonnet | `/code-review` medium |
| 3b | `acceptance-repair` | 53, 52, 18 | `closeout` | 2026-09-10 | **with `closeout`, 2026-09-15** | Sonnet | `/code-review` medium |
| 4 | `eval-reminders` | 32, 5, 35, 49 | `closeout` | 2026-10-09 | 2026-10-13 (else before evaluator assignments, ~12) | Sonnet | `/code-review` medium |
| 5 | `release-gate` | 15 (16 stretch) | `call-hardening` | **2026-12-05 (abort date)** | before the first evaluation completes | Opus | `/code-review` medium |
| 6 | `resolution-report` | 20 | `eval-reminders` | 2027-01-15 | before results are published | Sonnet | targeted read + suite |

**#40 (call lifecycle) is not in this round.** It is agreed in principle and
written up in [call-lifecycle-proposal.md](call-lifecycle-proposal.md) so it can
be picked up cold in the ~2027-03 → ~2027-05 window. Nothing in this round
depends on it; the October call runs fine on the current code now that #27 has
removed the dropdown.

Review tiers follow [worktrees.md § Review policy](worktrees.md#review-policy-proportionate--never-pay-twice);
where it says `/code-review` medium, the **branch session** runs it on its own
branch before opening the PR, and the handoff session then reads only what was
flagged.

**Stays inline on `main` in the handoff session:** backlog and doc edits, the
registry, the stale GitHub issue triage (#14–#30, see backlog side note), and
any single-file fix that surfaces mid-round.

### Cross-bucket rules (put these in every brief)

- **Shared files.** Three files are touched by every bucket that adds a
  reminder or an email: `app.conf.beat_schedule` in **`redib/celery.py:22`**,
  **`communications/management/commands/seed_email_templates.py`**, and
  `TEMPLATE_TYPES` in `communications/models.py:16`. (Corrected 2026-08-19 —
  this rule named two paths that do not exist.) Always **append at the end**, and on conflict **keep both sides** —
  that turns a scary-looking conflict into a mechanical one.
- **File ownership.** While `closeout` is live it owns `applications/tasks.py`;
  nothing on `main` or in another bucket edits that file until it merges.
- **Rebase early** against the conflict watchlist in each brief.
- **Baseline.** From bucket #1 onward the suite is expected **green**. Record
  the pre-start counts anyway and never make them worse.

## 4. Bucket briefs (seed material)

Each subsection is enough to fill `docs/handoffs/<slug>.md` from
[handoff-template.md](handoff-template.md). Decisions recorded here are
**settled** — a branch session must not reopen them.

### 4.1 `baseline` — green suite + waitlist hours

**Goal.** Get the test suite to a green baseline every later bucket can
measure against, and fix the live REDIB-2601 data bug in the same code path.

**In:** #7 (8 tests blocked by `ProfileCompletionMiddleware`), #8 (3 tests
blocked by `ManifestStaticFilesStorage`), #31 (`promote_waitlisted_application`
never sets `hours_approved`).

**Out:** any other backlog item; refactoring the test base classes beyond what
#7/#8 need.

**Decisions.** The promotion screen defaults each line to `hours_requested`
and a human confirms — nothing auto-approves. Check whether any REDIB-2601
application was *already* promoted with zero hours; the 7 waitlisted ones may
simply not have been promoted yet, in which case the promotion-time fix is
enough and no data command is needed. If some were, the correction ships as a
**small idempotent management command** (reviewable, repeatable) — never a
shell one-liner against prod — and it must not copy `hours_requested` into
`hours_approved`, because approved hours are a coordinator's decision.

**Acceptance.** `python manage.py test tests` green (from 134 tests / 2 ERROR /
7 FAIL). Two of those failures — `test_node_coord_can_promote_waitlisted_application`
and `test_handoff_email_timestamp_set` — are believed to be #31 itself
surfacing; confirm rather than assume. `manage.py check`, `makemigrations --check`
clean. Backfill command runs twice with the same result.

**Watchlist.** `applications/views.py` (`promote_waitlisted_application`,
~line 1404) — `call-hardening` edits the same file around line 585.

### 4.2 `call-hardening` — bugs that would hurt the new call

**Goal.** Fix the four diagnosed bugs that the new call would otherwise walk
straight into.

**In, in this order:** #27 (CallForm exposes raw `status`), #33
(`total_approved_hours` sums the wrong field), #13-minimal (`populate_redib_users`
sync semantics — stop clobbering passwords; make re-running prod-safe), #9
(fan out feasibility requests to all node coordinators).

**Out:** the full #13 rewrite (only the minimal prod-safe slice); #12; #16.

**Decisions.** **#27 is committed first, on its own**, because it gates the
09-15 announce. If the bucket is at risk of missing 09-08, the handoff session
cherry-picks that commit and ships it alone.

**Acceptance.** A coordinator cannot hand-set `announced`/`open` from the call
form; announce/publish still work through their guarded paths. Call detail,
admin and `reports/utils.py` agree on approved hours (REDIB-2601: 1,991 h, not
2,176 h). Re-running the user loader on an existing user does not reset their
password. A submitted application creates work for **every** active node
coordinator of the node, and all of them are emailed.

**Watchlist.** `applications/views.py` (~585, feasibility assignment) vs
`baseline`; `calls/models.py` vs `closeout`'s #36. Rebase on `main` once
`baseline` merges.

### 4.3 `closeout` — finish REDIB-2601, and the waitlist lifecycle

> **Merged 2026-08-19 (PR #36).** All six required items shipped; #35 was
> dropped and reassigned to `eval-reminders`. Kept below as the record of what
> was asked for. Review of the PR added four backlog items (#49–#52) and one
> **pre-deploy check** — see § 7.

**Goal.** Give the running call an ending: nudge participants to log actual
hours and complete, resolve the waitlist, and move the call itself to
`resolved`.

**In, in this order** (smallest first, then #36 before #30 because #36 is what
fires #30's closure email): #45 (`send_feasibility_reminders` has no dedupe and
still emails one assignee — left over from #9), #17 (acceptance deadline task
ignores waitlisted applicants), #28 (datetimes in Celery `context_data`), #36
(call close-out: `closed → resolved` + `is_resolution_locked` from the UI), #30
(waitlist follow-up), #29 (execution-phase completion reminders). **Stretch, only once the rest is green:**
#35 (draft nudge before the submission deadline) — same shape, same files,
near-zero marginal setup cost.

**Out:** anything that changes application *statuses* beyond what #36 needs;
#18 (reinstate expired); #34/#26 (email delivery truth).

**Decisions — settled 2026-08-18, do not reopen:**

- **Cadences: 60/30 for the completion reminders (#29), 30/30 for the waitlist
  follow-up (#30).**
- **Waitlisted applicants get no recurring reminder.** They cannot act on it;
  it reads as nagging about someone else's decision. The **node coordinator**
  gets the recurring action reminder. The **applicant** gets exactly one email
  — a "not reached this call" closure — fired by #36's `closed → resolved`
  transition. This is why #30 and #36 must ship together: the closure email has
  no trigger without #36.
- Dedupe every reminder against `EmailLog`, as the existing tasks do.

**Acceptance.** REDIB-2601 can be walked to `resolved` from the UI with
resolution locked. Reminders fire on the stated cadences against a seeded
sandbox and do not double-send. Every new email is seeded by
`seed_email_templates` and rendered with pre-formatted dates (#28). Waitlisted
applications get the day-7 reminder and day-10 expiry (#17).

**Watchlist.** Owns `applications/tasks.py` for its lifetime.
`CELERY_BEAT_SCHEDULE`, `seed_email_templates`, `calls/models.py` (vs #33).

**Urgency note.** REDIB-2601's execution window closes 2026-10-30. Reminders
deployed in October have almost no runway — the 09-15 prod date is the point of
the bucket, not a nicety.

### 4.3b `acceptance-repair` — no transition without a human

> **Merged 2026-08-20 (PR #37).** All three items shipped (#53, #52, #18).
> Review added #55–#57. Kept below as the record of what was asked for; the
> **principle** it establishes is not a record — it governs everything after
> it.

**Goal.** Delete the last beat task that writes an applicant-visible state
change, and replace it with a nag plus two coordinator actions.

**The principle this bucket establishes — apply it to everything after it:**

> **A beat task may compute and notify. Only a human writes a transition.**

The evaluator lockout is the model. `is_evaluation_locked()` derives
"deadline + 7 days" at page load: nothing is stored, nothing is emailed to the
evaluator, and moving the deadline moves the lockout. That is why it is safe to
leave automatic and why auto-expire is not — auto-expire writes a terminal
status and emails the applicant about it.

**Why now, and why it is not a nicety.** This network is small, informally
coordinated, and running the process systematically for the first time; the
prior system was scattered email and people's memories. Everything needs room
to be repaired. An email to an applicant that has to be walked back costs more
than a missed deadline does — and node behaviour is the part ReDIB does not
control, so anything that fires without the ReDIB coordinator knowing is a
problem that surfaces late.

**In:** #53 (the replacement, below), #52 (the two acceptance templates read as
if the recipient had been granted access), #18 (reinstate expired — it is the
repair path, and expiry becoming a human click is what makes it necessary).

**Out:** #54 (call reopen — same family, filed for later). #40. Anything in
`evaluations/`.

**Decisions — settled 2026-08-20 with Ryan, do not reopen:**

- **The deadline still means something.** The applicant's accept/decline link
  stays closed once `acceptance_deadline` passes, and after that point the
  applicant hears **nothing further from the system** about it. A node
  coordinator may contact them off-system. Resolution is entirely in
  coordinator hands.
- **It stays the node coordinator's job.** Do **not** rewire Access Tracking
  to admit the `coordinator` role; a superuser can back-door it if ever needed.
  The ReDIB coordinator is **cc'd** on the reminder, and the body must state
  plainly that the *node coordinator* is the one who must act.
- **The nag repeats, with a counter.** Not a one-time notice. Every 3 days
  until the application leaves the stalled state, and the body carries "this is
  reminder #N". Nagging the nodes is intended.
- **Two resolution options, not three.** Expire, or force-accept on the
  applicant's behalf. (An earlier draft had the applicant acting as option 1;
  dropped — see the deadline decision above.)
- **Force-accept requires a reason and notifies the ReDIB coordinator every
  time.** It is the most dangerous action in the system — it commits an
  applicant to an execution window without their word. Node coordinators keep
  the power anyway, because blocking them just moves the mess back to email,
  but it must never happen silently.
- **Pre-deadline reminders to the applicant become a real ladder:** day 3,
  day 7, day 9. The reminder to coordinators asserts the applicant was chased;
  that has to be true.

**Watchlist.** Owns `applications/tasks.py` and the acceptance half of
`applications/views.py`. `redib/celery.py`, `seed_email_templates`,
`templates/access/access_tracking.html`.

**Timing.** `closeout`'s prod deploy is **held** until this merges — #17
extended auto-expire to waitlisted applicants and this deletes it; shipping
both to prod separately is work for nothing, and deploying `closeout` alone
would retroactively expire and email REDIB-2601's unanswered waitlist offers
(see § 7's pre-deploy check, which this bucket removes rather than defuses).

### 4.4 `eval-reminders` — stop flooding evaluators

> **Merged 2026-08-21 (PR #38).** All four items shipped (#32, #5, #35, #49).
> Review added #58 and #59; one migration hand-edit was corrected on `main`
> immediately after the merge — see § 7.

**Goal.** One digest per evaluator on a backoff schedule, plus a manual lever
for the coordinator.

**In:** #32 (per-evaluator digest, backoff, dedupe — REDIB-2601 sent two
evaluators 42 reminders each), #5 (on-demand reminder dispatch for a chosen
scope) as phase 2. #5 is the escape hatch if #32's backoff turns out too quiet.
Picked up from `closeout` 2026-08-19: **#35** (draft nudge, dropped there as the
stretch item) and **#49** (`send_completion_reminders` is per-application where
it should be a per-coordinator digest — the same bug as #32, one call cycle
later). #49 is cheap here because #32 builds the digest shape anyway.

**Out:** #4 (auto-assign preview) — deferred this round. The evaluator lockout
(`is_evaluation_locked`, deadline + 7) is **not** in scope: it writes nothing and
is the one automatic behaviour Ryan wants kept.

**Acceptance.** A day with N pending evaluations for one evaluator produces one
email, not N. Backoff verifiable in a seeded sandbox. The coordinator's manual
dispatch respects the same dedupe.

**Watchlist.** `evaluations/tasks.py`, `CELERY_BEAT_SCHEDULE`,
`seed_email_templates`.

### 4.5 `release-gate` — hold resolutions until ReDIB releases them

> **Merged 2026-08-21 (PR #39).** #15 and #16 both shipped, well inside the
> 2026-12-05 abort date. Review found a second resolution path this brief did
> not know about — see § 7. Added #60.

**Goal.** Stop evaluated applications from independently becoming actionable;
let the ReDIB coordinator release a call's resolutions as a batch.

**In:** #15, on the **minimal design**: a per-call `resolutions_released` flag
that holds the node-coordinator emails and queue. **No new application state.**
**Stretch:** #16 (distinguish node-accepted from applicant-accepted in the
badges) — display only, no state-machine change, and only after the gate is
done and green.

**Out:** anything that adds an `Application` status; #12.

**Decisions.** #15 stays in this round (confirmed 2026-08-18). It is the only
item that touches the workflow, so it gets the top-tier model and the full
review tier.

**Abort criterion.** If it is not merged by **2026-12-05**, park the branch and
run the winter resolution piecemeal as REDIB-2601 did. This is what keeps a
structural item from being able to sink the round — check the date, don't
negotiate with it.

**Deploy note.** Adds a migration to `calls.Call` and deploys into a **live**
call: `scripts/backup-db.sh` first, and it must be in prod before the first
evaluation completes, since that is the transition it gates.

**Watchlist.** `applications/services/resolution.py` and `calls/models.py` —
both touched by `closeout`'s #36; read what #36 did before starting.

**Backfill rule (settled 2026-08-21).** The migration grandfathers a call only
if it **already has at least one application with a non-blank `resolution`** —
not "every existing call". The October call may already exist as a `draft` when
this deploys, and grandfathering it would silently defeat the bucket on the one
call it was built for.

### 4.6 `resolution-report` — bilingual results table

**Goal.** Produce the per-call resolution table ReDIB publishes, in English and
Spanish as two separate tables.

**In:** #20 — each submitted application, its applicant organization, the node,
and the node coordinator's resolution.

**Out:** #21 (public past-calls archive) — deferred, confirmed 2026-08-18.
Publication happens via this export until the marketing cutover decides where
public pages live.

**Acceptance.** Both language tables generate and match the resolution data.
Read-only: it must not mutate anything — asserted by a test, not by inspection.

**Watchlist.** `reports/` only — the most isolated bucket of the six.

**Two corrections to this seed material, made when the bucket was cut
(2026-08-21):**

- It said the tables must "generate for REDIB-2601". **They can't be checked
  against REDIB-2601 in dev** — that call exists only on production; the dev
  sandbox holds `COA-LIVE-2026` and `COA-PAST-2025`. The branch builds fixtures
  reproducing the *shape*; #20's real answer (24 rows, 16 accepted / 7 wait
  list / 1 rejected) is a **production** check, which is safe to run precisely
  because the report is read-only.
- It said the bucket "depends on #33's hours fix being correct". **It does
  not** — the resolution table has no hours column. Same mistake in the other
  direction as #44 below: proximity in the backlog read as a dependency.

**#44 is out of this bucket.** § 6 and the #44 entry both call this table "the
natural moment" to fix the declined-vs-unfilled `hours_approved=0` ambiguity.
On inspection it isn't: the table publishes application / organization / node /
resolution and no hours at all, so there is nothing in it to disambiguate.
Fixing #44 means a new explicit state on `RequestedAccess` — a migration, and a
different bucket. Recorded here so the link isn't re-made later.

**Merged 2026-08-21 (PR #40)**, with no deviations from the brief. Brief:
`docs/handoffs/resolution-report.md`. Still open: the Spanish column headers in
`reports/resolution_table.py`'s `COLUMN_HEADERS` are the brief's proposal, not
wording ReDIB has published — Ryan confirms or corrects, one dict entry.

**With this, all six buckets of the round are merged.** Five are deployed;
`resolution-report` is not, and does not need to be until results are published
(~2027-01/02). It carries no migration, no beat task and no email, so its deploy
is the cheapest of the round — it can ride along with whatever ships next.

## 4.7 Pre-launch verification — the dress rehearsal

Merging and deploying is not the same as knowing it works. Six buckets shipped
in three weeks, the suite is green at **382 + 11**, and prod is healthy — but
**no human has walked a call from announce to close in one sitting**, and the
defects that survive a green suite are exactly the ones a rehearsal catches:
wording that reads wrong, a button nobody would look for, a screen that is
blank where it should explain itself.

- **The click-through**: [dress-rehearsal.md](dress-rehearsal.md). Part A (six
  stages, ~90 min) covers announce → consult → open → apply → nudge → close,
  which is everything between now and the first submitted application. Part B
  is the December half.
- **The harness**: `scripts/rehearsal.py` — `seed` / `status` / `advance N` /
  `beat` / `inbox`. It simulates time passing so a ten-week sequence fits in an
  afternoon, and `beat` answers "what would the portal email today?" without
  waiting for tomorrow.
- **Safety**: dev only, three independent guards — console email backend,
  `CELERY_TASK_ALWAYS_EAGER` under `DEBUG`, and the script refusing to run
  unless `DEBUG` is on *and* the database is SQLite.

Time simulation works because nothing in this system stores "now": call
transitions compare dates against the clock and reminder ladders measure
elapsed days from an anchor, so moving a call's dates back N days is
indistinguishable from N days passing. The exception, documented in both files:
`advance` moves the **call**, not applications, so application-anchored
reminders must be set directly.

## 4.7b Pre-launch audit of the announce → submit path (2026-09-01)

Traced the literal October sequence — announce, consult, auto-open, register,
draft, submit, nudge, auto-close — against `main` at `105739b`. **The sequence
is sound.** Two findings, both filed and neither blocking: **#64** (editing an
open call's dates can leave `status` and `is_open` disagreeing) and **#65**
(`published_at` relabelled but not restamped on auto-open).

What the audit **cleared**, which is the part worth keeping, because these are
the assumptions the whole window rests on:

- **A Celery outage cannot let a late submission through.** `application_submit`
  (`applications/views.py:761`) compares against `call.submission_end`
  **directly**, never `call.status`. So even with beat completely down and the
  call still reading `open`, the deadline holds.
- **Both date-driven transitions have working view-level fallbacks.**
  `open_announced_calls` and `_auto_close_expired_calls` are re-checked on
  `public_call_list` / `public_call_detail`, so a missed beat run self-corrects
  on the next page view rather than waiting 24 hours.
- **Timezones line up.** `CELERY_TIMEZONE = TIME_ZONE = 'Europe/Madrid'`
  (`redib/settings.py:135, 221`) is the same zone `CallForm.clean()` normalizes
  into, so the 00:15 beat lands ~15 minutes after a true midnight boundary — not
  a day late.
- **No dead ends and no redirect loop.** Every wizard step has a back link and a
  cancel path; `ProfileCompletionMiddleware`'s required fields are exactly what
  `ProfileForm` collects, and `/profile/` is excluded from its own redirect.
- **No null surprises.** All `Call` lifecycle dates are non-nullable, and the
  applicant contact fields the nudge and submit paths read are already forced
  non-blank by the profile gate before the wizard is reachable.

Not covered by this audit, and verified separately by hand: **#48**, confirmed
real at `applications/views.py:803` — `if node_coordinators:` with no `else`, so
a node with no active coordinator gets no `FeasibilityReview` and no warning.

## 4.8 What the portal will email, unattended, Sept–Nov 2026

Audited 2026-09-01 against all ten beat tasks. Four will fire in this window,
six will not. Two of the four reach **applicants** with no human clicking
anything, so they belong on the calendar rather than in a backlog nobody reads.

| Date | Task | Who | Why |
|---|---|---|---|
| ~Oct 20 onward | `send_feasibility_reminders` | Node coordinators | A `FeasibilityReview` still pending 5 days after submission. Rows are created **at submit**, so this starts as soon as applications arrive. |
| **Oct 31 – Nov 6** | `send_completion_reminders` | **Applicants** + node coordinators | REDIB-2601's `execution_end` is **2026-10-30**, and `_milestone_window` fires a catch-up nudge in the week after. Every still-open accepted grant (up to 15) gets one, on one morning. |
| Oct 31 – Nov 6 | `send_waitlist_digest` | Node coordinators | Same milestone window; REDIB-2601's 7 waitlisted applications. Digested per recipient, so one mail each, not seven. |
| ~Nov 23 and ~Nov 28 | `send_draft_nudges` | **Applicants** | T-7 and T-2 before `submission_end`. Purpose-built for this call; deduped; stops at close. |

**The one to know about is Oct 31 – Nov 6.** It is correct, designed, already
deployed and already approved — but it lands mid-submission-window, so the same
people may be applying to the new call the same week they are asked whether
they have finished the old one. Nothing to fix; the burst is bounded by how
many REDIB-2601 grants are still `is_completed=False`, so **nodes marking
finished projects complete before 2026-10-30 is what shrinks it.** Worth an
ask to the nodes in October.

Silent for the window, with the reason: `send_evaluation_reminders` and
`notify_coordinator_overdue_evaluations` (no `Evaluation` rows until ~Dec, and
REDIB-2601's are complete); `process_acceptance_deadlines` and
`send_stalled_acceptance_reminders` (no application in `accepted`/`pending`
with an open deadline — prod confirmed the population empty on 2026-08-19);
`check_call_deadlines` (moves `Call.status` on ~Oct 15 but its fan-out is
suppressed by `CALL_ANNOUNCEMENT_EMAILS_ENABLED=False`).

**`send_publication_followups` is the one to watch just past the window.** It is
not scoped to a call — it queries every application on `handoff_email_sent_at`
6 months back — so REDIB-2601's June/July handoffs start maturing in
**December**. And it carries **#42**: it emails applicants in `accepted` *or*
`completed`, while `PublicationForm` only offers `completed` applications, so a
recipient still mid-execution clicks into a form with nothing to select. That
raises #42 from "Medium, someday" to **wanted before December** — it is the
next unattended applicant email after this window, and it currently lands them
on a dead end.

## 5. Unscheduled — inline on `main` if a window opens

Not in any bucket, but still wanted this round. Tagged `T3 inline` in the
backlog; each is one or two files, so they go inline in the handoff session
between merges rather than earning a bucket:

- **#34 + #26 together** — email delivery truth (failed sends are logged and
  forgotten; `emails_sent_at` means "queued"). Same fix, same file; doing them
  apart is wasted setup. Not before `closeout` merges — it is adding emails to
  the same module.
- **#37** — the three app containers race to run `migrate` on every deploy
  (found on prod during the 2026-08-18 deploy). Benign today because postgres
  DDL is transactional, but it makes a real migration failure indistinguishable
  from a spurious one in the log — and `release-gate` deploys a migration into
  a **live call** in December. Wanted in the pre-open batch (2026-10-13), and
  required before that December deploy. Cannot be verified in dev — no Docker
  locally — so the next real deploy is the test.
- **#43** — `populate_redib_users` treats a blank cell as an explicit `False`.
  Found on prod 2026-08-19 by the `--dry-run` that #13-min added. One file, but
  it carries a decision: the blank→False rule is **shared by all five
  `populate_redib_*` loaders** and documented in `CLAUDE.md`, so either
  `is_active`/`auto_data_consent` become an explicit exception (blank = leave
  alone, matching the password-on-create-only rule) or `data/users.tsv` is
  refreshed from prod first. Decide before touching code. **Blocks the October
  user load**, so it is the first inline item, not the last.
- **#52** — `acceptance_reminder` and `acceptance_expired` read as if the
  recipient had been granted access, and `closeout`'s #17 has just started
  sending both to **waitlisted** applicants. One tells them their grant will be
  "offered to the next applicant on the waiting list"; the other calls their
  application "approved". Applicant-facing, template-only, no migration. Fires
  on the first October waitlist offer, so it wants doing before the call
  resolves — and before the pre-deploy check in § 7 is answered.
- **#18** — coordinator "reinstate expired application". Wanted before the
  first expiry of the new call (~2027-01).
- **#23** — scientific-project guidance text. Blocked on Ángel's worked
  examples; do it whenever they arrive.

Also unscheduled: triage of the stale GitHub issues #14–#30 (see the backlog
side note) — a no-code chore, good filler while waiting on a branch session.

## 6. Deferred this round

Items 4, 12, 19, 21, 22, 6, 1, 2, 3, 10, 11, and the `feature/marketing-site`
branch (parked until 2027). Revisit after the winter resolution.

Two more were added on 2026-08-18 and deliberately deferred together, in that
order, to the window after this call closes (~2027-03) and before the next one
(~2027-05):

- **#40** — call status becomes one manual gate plus a derived phase. Proposal:
  [call-lifecycle-proposal.md](call-lifecycle-proposal.md).
- **#41** — re-enable the call announcement email, after the IONOS bulk-mail
  rules, an unsubscribe path, bounce handling and a throttle. Built **on top
  of** #40.

## 7. Live status

Update on every merge, in the same commit as the registry change.

| Bucket | Cut | Merged | Deployed | Notes |
|---|---|---|---|---|
| `baseline` | 2026-08-18 | **2026-08-18** (PR #35) | **2026-08-19** | Suite green — but it takes **two commands**, because `tests/` has no `__init__.py` and default discovery skips it: `manage.py test tests` = **162**, `manage.py test` = **11** (`reports/tests.py`). 173 total; that pair is what later buckets measure against (see #46). Review caught one defect: `resolution_accepted` would have mailed promoted applicants a blank deadline and an empty accept link. Worktree removed. |
| `call-hardening` | 2026-08-18 | **2026-08-18** (PR #34) | **2026-08-19** | #27, #33, #13-min, #9. Review added the regression tests for #27 and #33. Worktree removed. Left for `closeout`, now #45: `feasibility_reminder` still emails only the original assignee — and has no dedupe at all. |
| `closeout` | 2026-08-19 | **2026-08-19** (PR #36) | **2026-08-21** | All six shipped: #45, #17, #28, #36, #30, #29. Suite **201 + 11**, verified in the handoff session on the branch and again on merged `main`. `/code-review` medium ran on the branch: 6 findings, 5 fixed in the PR, 1 answered here (keep `call_resolve`'s narrow `evaluated`-only guard — a wider "is this call done" test could permanently block closing a call with one stuck application, which is the exact problem this bucket exists to fix; the broader concept stays with #40). Handoff review added #49–#52. #35 dropped → `eval-reminders`. Worktree removed. **Has a pre-deploy check — see below.** |
| `acceptance-repair` | 2026-08-20 | **2026-08-20** (PR #37) | **2026-08-21** | #53, #52, #18. Suite **278 + 11**, verified in the handoff session on the branch and again on merged `main`. `/code-review` medium on the branch: 10 findings, 8 fixed, 1 message-only fix over a pre-existing hole (#55), 1 reported (#56). Finding 5 was the one that mattered — the nag could reach **nobody** when a node had no active coordinator, since CC cannot exist without a To; it now falls back to addressing the ReDIB coordinator directly. Review also added #57. Worktree removed. **Ships with `closeout`.** |
| `eval-reminders` | 2026-08-20 | **2026-08-21** (PR #38) | **2026-08-21** | #32, #5, #35, #49 — #49's gate opened mid-session when `acceptance-repair` merged, so the branch rebased and did it. Suite **315 + 11**. `/code-review` medium on the branch: 5 findings, 4 fixed, 1 parked (#58). Review here added #59 and caught a **hand-edited migration** — see below. Worktree removed. |
| `release-gate` | 2026-08-21 | **2026-08-21** (PR #39) | **2026-08-21** | #15 + #16 (stretch, done). Suite **342 + 11**. `/code-review` medium on the branch: 5 findings, all applied — including `ResolutionService`, a **second fully-wired path** from `evaluated` to resolved that this brief never mentioned and that bypassed the gate entirely. Handoff session ran the end-to-end walkthrough the PR left open, on a fresh sandbox: all five stages pass. Added #60. Worktree removed. Its DDL deploy is what finally made #37 crash — see below. |
| `resolution-report` | 2026-08-21 | **2026-08-21** (PR #40) | | #20. Suite **382 + 11** on merged `main` (branch was 373 + 11 against a 351 baseline; `main` had moved to 360 meanwhile). Targeted read + suite per this bucket's tier — no `/code-review`. **The only bucket of six whose brief had no hole:** zero deviations, and the two things #20 left open shipped as decided — multi-node applications render as one row with stacked cells, kept parallel by a single ordered prefetch, and `NODE_PUBLIC_NAMES` lives in `reports/` with a three-step defensive fallback. Warnings sit in the page chrome, never in a table or a CSV. Worktree removed. **One item open:** the Spanish column headers are the brief's proposal, not published ReDIB wording — one dict entry to confirm or correct. |

**Deployed to prod so far:** help-guide (PR #32) and public-calls (PR #33),
2026-08-18.

**Deployed 2026-08-19** (prod pulled `0971e16`): #27, #31, #33, #13-min, #9,
the `resolution_accepted` template guard, and the announcement-email switch
(`CALL_ANNOUNCEMENT_EMAILS_ENABLED=False`).

**`eval-reminders` + `release-gate` shipped 2026-08-21** (prod pulled
`2aa0a0c`, backup `redib_db_20260821_130515.sql.gz` validated first). It was a different shape from the last one: `release-gate`
adds **real DDL** (`calls/0004`, two new columns on `Call` and `HistoricalCall`)
where the last three deploys were choices-only no-ops. So: `scripts/backup-db.sh`
**before** the pull, and watch the three-container `migrate` race (#37) on this
one specifically — prod's own forensics show it has been firing harmlessly since
day one, and this is the first migration in a while where "harmlessly" is an
assumption rather than a fact about no-op SQL.

The backfill grandfathers only calls that already have at least one application
with a non-blank `resolution`, so REDIB-2601 comes out released and anything
drafted for October stays gated. Confirm that on prod after the deploy:

```python
from calls.models import Call
for c in Call.objects.all():
    print(c.code, c.status, 'released' if c.resolutions_released else 'GATED')
```

**It also carries the #61 loader fix, and the beat schedule changes by exactly
one line.** `notify-overdue-evaluators` (09:30) is *replaced* by
`send-draft-nudges` (08:30) — #32 folded the evaluator flood into the 09:00
digest, so the separate overdue task is gone. Still ten entries.

**Nothing in this deploy sends a new email into a live population.** The draft
nudge only looks at calls with `status='open'` and only at T-7/T-2 before
`submission_end`; there is no open call. The evaluation digest needs pending
evaluations; REDIB-2601's are done. `release-gate`'s one behavioural change to
mail is a *suppression* — `notify_coordinator_evaluations_complete` is held
until the call is released. The 10:15 stalled-acceptance nag was already live
and prod confirmed an empty population on 2026-08-21.

**The one thing prod must not do after this deploy is run
`populate_redib_users` for real.** The dry-run is the verification; see below.

**Prediction to check the #61 fix against, once the rebuild is done** (and only
once it is done — `git pull` does not change what `manage.py` runs; that is
#62). Re-running `populate_redib_users --dry-run` should still report 0 to
update / 14 protected / 8 unchanged, and the **six** role lines of 2026-08-21
should drop to **zero**:

| 2026-08-21 role line | Why it is gone |
|---|---|
| 4 × `'clinical;preclinical' -> 'preclinical;clinical'` | Areas compare as a set; a reorder is not a change. |
| `mamunozb@` `areas: 'preclinical' -> ''` | A blank TSV cell is no longer written. |
| `mangel.morcillo@` `'preclinical;radiochemistry' -> 'radiochemistry'` | The TSV was stale, not the DB. Corrected 2026-08-21 (Ryan: he should have both). |

A dry-run that reports **anything** under Roles is a signal to stop and read it,
not to proceed. #61 is closed; the drift check plus the dry-run are now the
standing gate on any load, per `data/README.md`.

### Outcome, 2026-08-21 — everything predicted held, and #37 finally crashed

Every check came back as forecast. The dry-run reported 0 to create / 0 to
update / 14 protected / 8 unchanged and **zero** role lines; prod confirmed in
the DB that this is the fix working rather than the check going quiet — Arrate
still holds `areas='preclinical'` against a blank TSV cell, Morcillo holds both
areas. The backfill released REDIB-2601 (24 resolved applications) and left
REDIB-2602 **GATED**, which is the case the migration was written for. Beat came
up with ten entries, `send-draft-nudges` 08:30 in place of
`notify-overdue-evaluators` 09:30. One template created (`draft_nudge`), 31
total. `migrate --check` exits 0.

**But the deploy did not go cleanly: #37 fired and this time it crashed.**
`celery-beat` won and applied both migrations; `web` and `celery` died with
`psycopg.errors.DuplicateColumn: column "resolutions_released" of relation
"calls_call" already exists`, then `restart: unless-stopped` returned them to
"No migrations to apply". ~40 s lost, no damage, schema correct on both tables,
backfill committed exactly once. #37 said its verification could only come from
a real deploy; it came on the deploy the entry itself named as its deadline.

The detail worth keeping is prod's: **the symptom inverts with the DDL.** A
choices-only migration leaves three duplicate `django_migrations` rows and no
crash; real DDL leaves one row and two tracebacks. Duplicate rows mean the
migration was a no-op, a crash means it was real — and neither can be told from
a genuine failure by reading the log. `DEPLOYMENT.md` now carries that table
plus the two commands that actually settle it (`migrate --check`, then query the
field the migration added). #37 stays open for the advisory lock; what changed
is that it is no longer theoretical.

Prod also corrected two things in the instructions it was given: the compose
services are `web` / `celery` / `celery-beat` (not `worker` / `beat`), and the
container that wins the race — and therefore the only one whose log shows "N
templates created" — moved between deploys, so seeding checks must grep all
three. Both fixed in `DEPLOYMENT.md`.

Two findings raised while verifying, neither a deploy problem: **#63** (only 10
of 15 active evaluator roles sit on active accounts; effective coverage is
preclinical 10 / clinical 4 / radiochemistry 3, and clinical is thin for
October) and confirmation that `gonzalo.pizarro@cnic.es`'s extra `applicant`
role is self-acquired and needs no action.

**`closeout` + `acceptance-repair` shipped together on 2026-08-21**, three
weeks ahead of the 2026-09-15 target. The hold worked as intended: the
auto-expire that `closeout`'s #17 extended was deleted by `acceptance-repair`
before either reached prod, so it never ran against REDIB-2601.

What `closeout` carries when it does go: two choices-only
`AlterField` migrations (`applications.0014`, `communications.0008` — `sqlmigrate`
confirms no-op DDL), five new `EmailTemplate` rows seeded by the entrypoint's
`seed_email_templates`, and two new beat tasks at 08:00 and 08:15.

### `release-gate`: the brief had a hole, and the review found it

The brief named four places that must refuse while a call is unreleased. There
were **five**. `applications/services/resolution.py`'s `ResolutionService` is a
second, fully-wired path from `evaluated` to a resolved status — reachable from
the "Resolution" sidebar link every ReDIB coordinator sees, via
`resolution_dashboard → call_resolution_detail →` per-application resolve /
bulk auto-allocate / finalize. It never checked the flag, so a coordinator could
have resolved applications one at a time through it: exactly the piecemeal
pattern the bucket exists to prevent, through a door the brief did not know was
there.

The branch's `/code-review` caught it, gated all three entry points, and
excluded unreleased calls from `resolution_dashboard`. It also pulled the
repeated check into `Call.ensure_resolutions_released()` so the next entry point
cannot quietly skip it.

**Lesson for future briefs:** "here are the call sites" is a claim that needs
checking, not a list to work from. When a brief gates a transition, the branch
should grep for every writer of that transition before trusting the enumeration.

### `eval-reminders`: a migration was hand-edited, and corrected on `main`

The branch resolved its rebase conflict by editing
`communications/migrations/0009` in place — appending `draft_nudge` to the
choices list — rather than adding `0010`. **`0009` was already applied on prod**
in the 2026-08-21 deploy, and Django records migrations by name, so it would
never have re-run: `draft_nudge` would have existed in the model and in the
repo's migration file while prod's migration history said otherwise.

Harmless in effect — a choices-only `AlterField` emits no SQL, so prod's schema
was never wrong — but the history would have been a lie, and the next person to
read it would have had no way to tell. Fixed on `main` immediately after the
merge: `0009` restored byte-for-byte to the version prod applied, `draft_nudge`
regenerated as `0010` (`sqlmigrate` confirms `(no-op)`).

**The rule, for every brief from here:** never edit a migration that has been
applied anywhere. On a rebase conflict in a generated migration, delete your
copy and re-run `makemigrations` — the new file gets the next free number.

### Deployed 2026-08-21 — `closeout` + `acceptance-repair` are live

Matched the forecast exactly: 3 migrations applied, `seed_email_templates`
reported **7 created / 23 updated → 30 templates**, beat restarted with the
three new entries at 08:00 / 08:15 / 10:15 alongside the seven existing.
No templates had been hand-edited in the admin, so nothing was lost to
`update_or_create`.

**The pre-deploy count came back empty, and that is the interesting part.**

```
accepted + pending:            22   (15 accepted, 7 pending)
  accepted_by_applicant set:   22   ← all of them
stalled (deadline passed):      0
no deadline recorded (#55):     0
```

Every one of the 22 has an applicant response on record, including all seven
waitlisted (`accepted_by_applicant=True`, `handoff_email_sent_at=None` — they
accepted their place and were never promoted). The only non-`True` rows fall
outside the filter: 3 drafts, 1 rejected, and `REDIB-2601-026` at `False`,
already expired under the old auto-expire before it was deleted. Prod confirmed
the query is not structurally dead — `accepted_by_applicant` is
`BooleanField(null=True)`, so `__isnull=True` can match; it just doesn't here.

Consequences worth holding on to:

- **The stalled-acceptance nag deployed into an empty population.** No mail
  fired, and none will on this call unless a future applicant goes silent. The
  Expire / Force-Accept buttons render nowhere on prod for the same reason —
  their guard is `accepted_by_applicant is None` **and**
  `acceptance_deadline_passed`. Correct-and-quiet, not broken. Worth knowing
  before someone reports the buttons as missing.
- **#55 is not reachable on this call** — zero applications with a NULL
  deadline. It stays filed as a latent gap for future calls.
- **The seven waitlisted applications are the live population for
  `send_waitlist_digest`**, not for the nag: they answered, so the thing that
  surfaces them is the 30/30 digest to their node coordinators, plus the
  `not_reached` close-out action when a slot will not open. That is exactly the
  path `closeout` built for them.
- **The 15 accepted are the population for `send_completion_reminders`.** The
  #49 burst risk therefore still stands and still lands the week after
  `execution_end` (2026-10-30).

### What the joint deploy did on prod

Three migrations, all choices-only `AlterField` (`applications.0014`,
`communications.0008`, `communications.0009`) — `sqlmigrate` confirms no-op DDL.
`seed_email_templates` runs from the entrypoint and should report **7 created**
(`waitlist_digest`, `waitlist_not_reached`, `freed_capacity_notice`,
`completion_reminder`, `completion_reminder_coordinator`,
`stalled_acceptance_reminder`, `stalled_acceptance_actioned`) and the rest
updated. Three new beat entries: 08:00, 08:15, 10:15.

**`seed_email_templates` uses `update_or_create`** — it overwrites subject and
body on every deploy. Any template hand-edited in the Django admin is silently
reverted. Worth asking prod once whether anything was edited that way; if so it
needs to move into the seed file to survive.

**What fires the first morning.** Only one of the new tasks will produce mail
against REDIB-2601:

- `send_stalled_acceptance_reminders` (10:15) — every application still sitting
  in `accepted`/`pending` with no applicant response and a deadline in the past.
  The cadence is "1 day after the deadline, then every 3 days", so on any given
  day about a third of them fire; all of them will have fired within three days
  of the deploy. Each goes to that node's coordinator(s) with the ReDIB
  coordinator cc'd, and the counter starts at reminder #1. **This is the
  intended effect**, not a side effect.
- `send_completion_reminders` (08:15) — cadence is 60 days after handoff then
  every 30, matched on the exact day, so only projects landing on a checkpoint
  fire on deploy day. The burst risk is **not** at deploy: it is the week after
  `execution_end` (2026-10-30), when every still-open project hits the
  milestone window at once. That is #49, and it gives `eval-reminders` a real
  deadline — #49 wants to be in prod before ~2026-10-31.
- `send_waitlist_digest` (08:00) — same exact-day cadence off the applicant's
  acceptance; likely nothing on day one.
- `process_acceptance_deadlines` (10:00) — its ladder only covers deadlines in
  the next 7 days. REDIB-2601's are all past, so nothing.

**The count query**, kept for re-running on the next call (read-only):

```python
from django.utils import timezone
from applications.models import Application

now = timezone.now()
stalled = Application.objects.filter(
    status__in=['accepted', 'pending'],
    accepted_by_applicant__isnull=True,
    acceptance_deadline__lt=now,
)
print('stalled acceptances (will be nagged over ~3 days):', stalled.count())
for a in stalled:
    print(' ', a.code, a.status, a.acceptance_deadline.date())

# #55: these are invisible to the nag and to both coordinator actions.
print('no deadline recorded (invisible to everything):', Application.objects.filter(
    status__in=['accepted', 'pending'],
    accepted_by_applicant__isnull=True,
    acceptance_deadline__isnull=True,
).count())
```

(The seven `pending` REDIB-2601 applications prod counted on 2026-08-19 are the
population to check; whether any has an unanswered deadline is not knowable from
dev. Note #55: an application with a NULL `acceptance_deadline` is invisible to
this query *and* to the nag.)

Prod's post-deploy verification produced two findings, both in the backlog:
**#43** (High, blocks the user load — see § 5) and **#44** (Low, answered
2026-08-19 — the two 0-hour lines are deliberate; what survives is that a
declined instrument and an unfilled one are indistinguishable, which #20's
resolution table is the natural moment to fix). The waitlist
`hours_approved` backfill turned out **not to be needed**: prod checked and
neither 0-hour application was ever waitlisted, so #31's promotion fix covers
the round with no data command to run.
