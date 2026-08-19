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

- **#9** (feasibility fan-out) — fires the moment the first application is
  submitted. Late means reproducing REDIB-2601's single-arbitrary-coordinator
  problem on the new call.
- **#13-minimal** — **shipped and deployed 2026-08-19.** Its new `--dry-run`
  immediately paid for itself: prod ran it and found **#43**, which now blocks
  the load it was meant to make safe. A plain `populate_redib_users` today would
  deactivate a serving evaluator and clear `auto_data_consent` on ~14 accounts,
  because the shared loader rule writes a blank cell as `False`. **Do not load
  users on prod until #43 is settled** — it is the one thing standing between us
  and preparing the new call's accounts.

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
| 4 | `eval-reminders` | 32, 5 | `closeout` | 2026-10-09 | 2026-10-13 (else before evaluator assignments, ~12) | Sonnet | `/code-review` medium |
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

### 4.4 `eval-reminders` — stop flooding evaluators

**Goal.** One digest per evaluator on a backoff schedule, plus a manual lever
for the coordinator.

**In:** #32 (per-evaluator digest, backoff, dedupe — REDIB-2601 sent two
evaluators 42 reminders each), #5 (on-demand reminder dispatch for a chosen
scope) as phase 2. #5 is the escape hatch if #32's backoff turns out too quiet.

**Out:** #4 (auto-assign preview) — deferred this round.

**Acceptance.** A day with N pending evaluations for one evaluator produces one
email, not N. Backoff verifiable in a seeded sandbox. The coordinator's manual
dispatch respects the same dedupe.

**Watchlist.** `evaluations/tasks.py`, `CELERY_BEAT_SCHEDULE`,
`seed_email_templates`.

### 4.5 `release-gate` — hold resolutions until ReDIB releases them

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

### 4.6 `resolution-report` — bilingual results table

**Goal.** Produce the per-call resolution table ReDIB publishes, in English and
Spanish as two separate tables.

**In:** #20 — each submitted application, its applicant organization, the node,
and the node coordinator's resolution.

**Out:** #21 (public past-calls archive) — deferred, confirmed 2026-08-18.
Publication happens via this export until the marketing cutover decides where
public pages live.

**Acceptance.** Both language tables generate for REDIB-2601 and match the
resolution data. Read-only: it must not mutate anything.

**Watchlist.** `reports/` only — the most isolated bucket of the six. Depends on
#33's hours fix being correct.

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
| `baseline` | 2026-08-18 | **2026-08-18** (PR #35) | **2026-08-19** | Suite green: **173 tests, 0 failures** — that is the number later buckets measure against. Review caught one defect: `resolution_accepted` would have mailed promoted applicants a blank deadline and an empty accept link. Worktree removed. |
| `call-hardening` | 2026-08-18 | **2026-08-18** (PR #34) | **2026-08-19** | #27, #33, #13-min, #9. Review added the regression tests for #27 and #33. Worktree removed. Left for `closeout`, now #45: `feasibility_reminder` still emails only the original assignee — and has no dedupe at all. |
| `closeout` | **2026-08-19** | | | Cut from `main` @ `0971e16`, worktree `closeout/` port 8002. #45, #17, #28, #36, #30, #29; #35 stretch. Owns `applications/tasks.py`. |
| `eval-reminders` | | | | cut once `closeout` merges |
| `release-gate` | | | | cut once `call-hardening` merges; abort 2026-12-05 |
| `resolution-report` | | | | cut once `eval-reminders` merges |

**Deployed to prod so far:** help-guide (PR #32) and public-calls (PR #33),
2026-08-18.

**Deployed 2026-08-19** (prod pulled `0971e16`): #27, #31, #33, #13-min, #9,
the `resolution_accepted` template guard, and the announcement-email switch
(`CALL_ANNOUNCEMENT_EMAILS_ENABLED=False`). Nothing is waiting on a deploy right now.

Prod's post-deploy verification produced two findings, both in the backlog:
**#43** (High, blocks the user load — see § 5) and **#44** (Low, blocked on
BioImaC confirming two 0-hour lines were deliberate). The waitlist
`hours_approved` backfill turned out **not to be needed**: prod checked and
neither 0-hour application was ever waitlisted, so #31's promotion fix covers
the round with no data command to run.
