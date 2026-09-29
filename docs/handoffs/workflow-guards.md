# Handoff — `feature/workflow-guards`

<!-- Copy of docs/developer/handoff-template.md, seeded by scripts/new-worktree.sh.
     Lives at docs/handoffs/workflow-guards.md on the branch. Keep "Status" current. -->

| | |
|---|---|
| Branch | `feature/workflow-guards` |
| Worktree dir | `/home/rtasseff/projects/ReDIB-Portal-wt/workflow-guards` |
| Base | `main` @ `67b80dc` |
| Created | 2026-09-29 |
| Runserver port | 8003 |
| Handoff session | `main` checkout at `~/projects/ReDIB-Portal/` |

Read this first, then `CLAUDE.md`, then `docs/README.md`. This directory is
a git worktree: it *is* this branch — do not `git checkout` another branch
here (see `docs/developer/worktrees.md`).

**Development document.** These are instructions for the agent session working
in this worktree. Once the branch merges, this file lands on `main` as a
record — on the production VPS it is history, not a task list.

## Goal

Close the workflow gaps the 2026-09-28 documentation audit found, before the REDIB-2602
call opens on 2026-10-15:
- Remove the old coordinator resolution tools. Their *Finalize* re-sends every decision email.
- Make the call's Announce, Publish and Close actions refuse the wrong state.
- Close two view gaps.
- Correct wording that no longer matches what the portal does.

Keep every change small. This is a guard-and-cleanup branch, not a redesign.

**Timing:** PR ready by **2026-10-06**. The handoff session merges by 10-08 and prod
deploys by 10-10, before the 10-13 → 10-15 freeze. If a piece isn't ready by 10-06,
cut it and say so.

## Scope

**In** (backlog rows in `docs/developer/backlog.md`; read each one, and
`docs/ARCHITECTURE.md` §3, §6, §8 and §10 for the as-built picture):

1. **#84: remove the legacy ReDIB-coordinator resolution tools.** Ryan (2026-09-29):
   "Definitely remove the Finalize option". He approved removing all three.
   - Delete **Decide** (per-application resolve), **Apply Bulk Resolution**
     (`bulk_auto_allocate`) and **Finalize Resolution & Send Notifications**
     (`finalize_resolution` → `send_resolution_notifications_task`), including their
     buttons, URLs, views, forms (`ApplicationResolutionForm`) and service methods.
   - Delete their tests, and any code that only they used. Verify each with grep
     before deleting; `ResolutionService` may go entirely if nothing else uses it.
   - **Keep** the Resolution page (the call list, and the per-call list ranked by
     score) as a read-only watch list.
   - **Keep everything the node flow uses:** `NodeResolutionService`,
     `send_single_resolution_notification_task`, `Call.ensure_resolutions_released`,
     `Application.has_any_denied_evaluation`, and **Mark Call Resolved**.
   - Why nothing is lost: Finalize's check, deadline, lock and emails are all already
     done by the node flow (`aggregate_application_resolution`) and by `call_resolve`.
     Only its duplicate emails go.
   - Fix the `resolution/dashboard.html` intro: it says the coordinator "makes final
     decisions" and names a "Release Resolutions" button; the real one is
     **Release to Nodes**.
   - Update the competitive-funding "Enforced in" list in `CLAUDE.md` to match.
2. **#85: call actions refuse the wrong state.**
   - `call_announce`, `call_publish` and `call_close` become POST-only
     (`@require_POST`). The buttons become small forms with the CSRF token and keep
     their existing confirm text.
   - Each refuses a wrong starting status with a message and a redirect: Announce only
     from `draft`, Publish/Open Now only from `draft` or `announced`, Close only from
     `open`. A GET on a resolved call must no longer reopen it; add a regression test.
   - **Auto-close**: today the beat task (`calls/tasks.py`) and the page fallback
     (`calls.views._auto_close_expired_calls`) each use queryset `.update()`, so no
     history row is written, and they disagree on announced calls whose window has
     passed.
     - Make them call **one** shared function in `calls/services.py` that saves each
       call (`call.save()`), so simple_history records it.
     - Keep today's outcomes: an open call past `submission_end` closes, and an
       announced call whose whole window has passed closes. Both paths get the same
       result.
3. **#86: two view gaps.**
   - (a) `remove_evaluator_assignment` re-runs
     `check_and_transition_application` after removing, so an application whose last
     outstanding evaluation was removed moves to `evaluated`. That goes through the
     release gate as usual. If no evaluations remain, leave the status alone (the
     coordinator assigns someone else).
   - (b) `access.views.mark_application_complete` refuses, with a message and no 500,
     unless the application is `accepted` and the applicant has accepted.
4. **#87: copy that no longer matches behaviour, plus one fan-out fix.**
   - (a) The "Publish Call" confirmation on `call_form.html` branches on
     `CALL_ANNOUNCEMENT_EMAILS_ENABLED`, like the other confirmations did in #68:
     `announcement_emails_enabled` in the context.
   - (b) After an evaluation is submitted, don't claim "The coordinator has been
     notified". Say what's true.
   - (c) Remove "You can decline later" from the waitlist accept page.
   - (d) The waitlist close-out error no longer says to "let it auto-expire".
   - (e) The completion-reminder email (`seed_email_templates.py`) describes the real
     action: **Mark Complete + Log Hours**, entering actual hours for every piece of
     equipment. It is reseeded on deploy.
   - (f) The **pre-submission consult** (wizard step 5,
     `_send_consult_request_emails`) emails **every** active node coordinator of each
     node, and ReDIB coordinators for a node with none. That matches the public
     consult; reuse its recipient logic rather than writing a second copy.
5. **Docs** for all of the above:
   - `docs/USER_GUIDE.md`: drop the "older tools… leave them alone" paragraph under
     *Watching resolution*, and check each section you touched. Keep only `#anchor`
     links, and keep `tests/test_help_guide.py` green.
   - `docs/ARCHITECTURE.md`: §3.1 table, §3.3 caveats, §6, §8 template table, §10
     legacy table, §11.
   - `CLAUDE.md`.

**Out:**
- Management commands, loaders, `send_test_emails` and `tests/` cleanup: that's the
  `commands-cleanup` bucket, running in parallel.
- Backups (#89, on `main`).
- Reopening a closed call (#54).
- Any new feature.

## Acceptance

- The full suite (`python manage.py test tests reports`) is green. The legacy
  tool's tests are removed, and there are new tests for:
  - each refused call action
  - GET no longer changing a call
  - the auto-close history row
  - #86 (a) and (b)
  - the consult fan-out
  - the Publish-confirm wording both ways
- `python manage.py makemigrations --check` reports no changes. If removing a form or
  service would need a migration, stop and ask. Don't remove model fields on this
  branch.
- Click-through on `localtest3` (`runserver 8003`):
  - announce, publish and close a call
  - the Resolution page renders, with no Decide, Bulk or Finalize
  - a node resolution still resolves and emails
  - promote from the waitlist still works
- One `/code-review` at **medium** before the PR. It changes who gets emailed and
  touches call lifecycle writes. List what it flagged and what you did in the PR body.

## Context & decisions already made

- **Main moved after this branch was cut: #92, `3da147b`, rebased in on 2026-09-29.** Bot sign-ups are stopped. The applicant role is now granted on email *confirmation* (`core/signals.py`), the signup form has a browser check and a honeypot, and there is a new command, `purge_unverified_signups`. Prod found that most of the ~1,200–1,480 accounts were bots. **Suite baseline is now 494.** Read `3da147b`'s message before you start. Don't change what it built.
- **For this branch:** nothing in #92 overlaps your scope. `USER_GUIDE.md` and `ARCHITECTURE.md` changed on `main` (the signup and role wording, and the new command), so edit the versions you now have.
- The governing rule: *a scheduled task may compute and notify; only a human writes a
  transition*. The call auto-open/close is the documented exception (`ARCHITECTURE.md`
  §3.3). Don't widen it.
- Resolution as it works today, which is why Finalize is redundant: the release gate,
  then each node decides, then each application resolves and emails the moment its
  last node decides, then **Mark Call Resolved**. Ryan has this explained and agreed.
- Never read `.env` (not with cat, grep, ls or Read); it holds secrets.

## Conflict watchlist

- `commands-cleanup` (parallel) edits the `ARCHITECTURE.md` §4 `Commands:` lists, the
  `CLAUDE.md` "TSV loaders" section, `data/README.md` and the dev docs. Leave those
  alone.
- `main` (#89) edits `DEPLOYMENT.md` § 6 and `scripts/backup-db.sh`.

## Status

- [x] #84 · [x] #85 · [x] #86 · [x] #87 a–f · [x] docs · [x] click-through · [x] /code-review · [x] PR
- Suite: baseline 494 → 490 after removing the four legacy `ResolutionService` tests
  in `test_release_gate.py` → **516** with 26 new (`tests/test_workflow_guards.py`, plus
  four consult tests in `tests/test_wizard_step5_consult.py`). `check` and
  `makemigrations --check` clean; no migration.
- Click-through (2026-09-29, fresh `localtest3`, runserver 8003, scripted over HTTP
  with real login + CSRF): announce, publish, close and their refusals; GET on
  announce/close → 405, a resolved call stays resolved; close + Release to Nodes on
  COA-LIVE-2026; Resolution pages render with no Decide/Bulk/Finalize, old URLs 404;
  both nodes decide LIVE-007 → `accepted`, `resolution_accepted` logged; applicant
  accepts LIVE-010's waitlist offer, NC promotes → `resolution_accepted` +
  `handoff_notification` logged. History rows present for every call change.
- `/code-review` (medium): one low finding, fixed. With no node coordinator *and* no
  active ReDIB coordinator, the wizard consult said "no equipment selected" and "went
  to the ReDIB coordinators" though nothing was sent; it now says nobody could be
  emailed (test added). Everything else checked clean.
- Deviations:
  - `ResolutionService` stays, trimmed to its two read methods: the watch-list pages
    use them, and `tests/test_phase6_resolution.py` (no TestCase, never runs; the
    `commands-cleanup` bucket owns deleting it) still imports the class.
  - Also fixed `completion_reminder_coordinator`: it had the same "confirm the
    equipment lines as done" wording as (e).
  - The feasibility consult template gained a `no_node_coordinator` branch for the
    ReDIB fallback (f), like the public consult's.
  - `ARCHITECTURE.md` §4's `applications` row still calls `services/resolution.py`
    the "older route": that line also holds the `Commands:` list `commands-cleanup`
    edits, so it is left for the merge.

## Questions for the handoff session

-

## Return protocol

1. Keep this doc's **Status** current; note anything you deviated from.
2. `python manage.py check`; `python manage.py makemigrations --check`;
   full suite `python manage.py test tests reports` — record the pass/fail counts
   against the baseline you took before starting (do not make it worse).
3. Push the branch and open a PR against `main`. PR body = the review
   packet: what changed and why, deviations from this brief, the test
   counts, anything user-facing (email wording, guide copy) quoted for
   review, and any pre-existing bug you noticed but did not fix.
4. The handoff session reviews proportionately to risk (see
   `docs/developer/worktrees.md` § Review policy), merges, and updates the
   registry.

## Running locally (this worktree)

```bash
cd /home/rtasseff/projects/ReDIB-Portal-wt/workflow-guards
source venv/bin/activate
python manage.py runserver 8003
```

`.env`, `db.sqlite3` and `media/` were copied from the `main` checkout at
creation time. To rebuild the sandbox: `python manage.py setup_localtest3_database`
(see `docs/DEVELOPMENT.md`).
