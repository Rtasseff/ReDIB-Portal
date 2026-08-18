# Handoff — `feature/baseline`

<!-- Copy of docs/developer/handoff-template.md, seeded by scripts/new-worktree.sh.
     Lives at docs/handoffs/baseline.md on the branch. Keep "Status" current. -->

| | |
|---|---|
| Branch | `feature/baseline` |
| Worktree dir | `/home/rtasseff/projects/ReDIB-Portal-wt/baseline` |
| Base | `main` @ `e4388a1` |
| Created | 2026-08-18 |
| Runserver port | 8002 |
| Handoff session | `main` checkout at `~/projects/ReDIB-Portal/` |

Read this first, then `CLAUDE.md`, then `docs/README.md`. This directory is
a git worktree: it *is* this branch — do not `git checkout` another branch
here (see `docs/developer/worktrees.md`).

**Round context:** bucket 1 of 6 in
[docs/developer/round-october-2026.md](../developer/round-october-2026.md).
**Merge by 2026-08-21, in prod by 2026-08-22** — five other buckets are
queued behind this one and two of them cannot cut until it lands.

## Goal

Two things that everything else in the round depends on: get the test suite
to a **green baseline** that every later bucket can measure itself against,
and fix the waitlist-promotion bug that leaves approved hours at zero. They
are one bucket because two of the current failures are believed to *be* the
promotion bug surfacing.

## Scope

**In:**
- **#7** — 8 tests blocked by `ProfileCompletionMiddleware` (`core/middleware.py`
  redirects logged-in users with incomplete profiles to `/profile/`; tests
  creating users via `User.objects.create_user(...)` get a 302 they don't
  expect). Affects `tests/test_design.py`, `tests/test_phase7_acceptance.py`,
  `tests/test_phase9_publications.py`, `reports/tests.py`.
- **#8** — 3 tests blocked by `ManifestStaticFilesStorage` in
  `tests/test_design.AuthPageRenderTest`.
- **#31** — `promote_waitlisted_application` (`applications/views.py`, ~line
  1404) flips status and fires the `resolution_accepted` + handoff emails
  without ever setting `hours_approved` on the equipment lines.

**Out** (do not do here — belongs on `main` or another bucket):
- Any other backlog item. In particular **#17** (the acceptance-deadline task
  ignoring waitlisted applications) is adjacent but belongs to `closeout`,
  which owns `applications/tasks.py`. Do not touch that file.
- Refactoring the test base classes further than #7/#8 require. A shared
  helper/mixin is fine if it's what the fix needs; a test-infrastructure
  redesign is not.

## Acceptance

- `python manage.py test tests` is **green**. Starting point recorded on
  `main` before this branch: **134 tests, 2 ERROR, 7 FAIL**:
  `test_applicant_can_submit_publication`, `test_full_publication_workflow`
  (ERROR); `test_applicant_can_accept`, `test_applicant_can_decline`,
  `test_calls_list_renders`, `test_dashboard_renders`,
  `test_full_acceptance_workflow`, `test_handoff_email_timestamp_set`,
  `test_node_coord_can_promote_waitlisted_application` (FAIL).
- `python manage.py check` and `python manage.py makemigrations --check` clean.
- Promoting a waitlisted application through the UI requires the node
  coordinator to confirm approved hours per equipment line, and the handoff
  email that goes out carries the confirmed figures — not zeros.
- Promotion is **refused** when every line is zero.

## Context & decisions already made

- **Suggested order: #7 and #8 first, then #31.** The hypothesis is that
  `test_node_coord_can_promote_waitlisted_application` and
  `test_handoff_email_timestamp_set` fail because of #31 itself, and the
  other seven are the middleware/storage problems. **Confirm this rather
  than assuming it** — if a failure has a third cause, say so in Status and
  in the PR instead of forcing it green.
- **#31's UI:** default each line's approved hours to `hours_requested` and
  reuse the widget already used in `templates/applications/node_resolution/review.html`
  — same interaction the coordinator already knows. A human confirms the
  numbers; nothing auto-approves.
- **Prod data:** check whether any REDIB-2601 application was *already*
  promoted with zero approved hours. The 7 waitlisted applications may
  simply not have been promoted yet, in which case the promotion-time fix is
  sufficient and **no data command is needed** — that is the expected
  outcome. If some were already promoted, ship a small **idempotent
  management command** to correct them (never a shell one-liner run against
  prod), and note in the PR that the corrected hours have to come from the
  node coordinator — the command must not silently copy `hours_requested`
  into `hours_approved`, because approved hours are a human decision.
- **Waitlist recap** (see `CLAUDE.md`): `pending` is the waitlist state; the
  hand-off email only fires when a node coordinator clicks "Mark as Accepted"
  on Access Tracking (`applications:promote_waitlisted`). That click is
  exactly the path being fixed.
- Do not reimplement the competitive-funding reject check; use
  `Application.has_any_denied_evaluation` (see `CLAUDE.md`).

## Conflict watchlist

- `applications/views.py` — `feature/call-hardening` is live in parallel and
  edits the same file around **line 585** (feasibility assignment). Different
  region, but rebase on `main` if that branch merges first.
- `tests/` — no other bucket is touching it right now. This branch owns it.

## Status

<!-- Keep this current. Checklist + short dated notes. -->
- [x] Baseline recorded (`python manage.py test tests` before any change) —
  2026-08-18: 145 tests, 2 ERROR, 7 FAIL (branch was cut from an older `main`
  commit than HEAD of `main`; test count differs from the 134 recorded at
  cut time but the same 9 tests fail — hypothesis confirmed, see below).
- [x] #7 — middleware-blocked tests. Root cause confirmed: affected tests
  create users via `User.objects.create_user(...)` without
  phone/organization/position, so `ProfileCompletionMiddleware` 302s them to
  `/profile/` before the view under test runs. Added `core/test_utils.py`
  (`create_complete_user`) and used it in `tests/test_design.py`,
  `tests/test_phase7_acceptance.py`, `tests/test_phase9_publications.py`,
  `reports/tests.py`.
- [x] #8 — static-manifest-blocked tests. Did **not** reproduce in this
  worktree as-is (a `staticfiles/staticfiles.json` manifest from an earlier
  `collectstatic` run was already sitting on disk — gitignored, so a fresh
  checkout/CI wouldn't have it). Confirmed the real bug by moving
  `staticfiles/` aside: `AuthPageRenderTest` throws
  `ValueError: Missing staticfiles manifest entry` with no manifest present.
  Fixed at the root: `redib/settings.py` now picks plain
  `StaticFilesStorage` under `_IS_TESTING` instead of whitenoise's manifest
  storage (which requires `collectstatic` to have already run). Moved the
  existing `_IS_TESTING` computation to the top of the file since the static
  storage setting needs it earlier than the Celery eager-mode block did.
- [x] #31 — approved hours confirmed at promotion. `promote_waitlisted`
  (`applications:promote_waitlisted`) now does GET (render
  `templates/applications/promote_waitlist_confirm.html`, a per-equipment
  hours table defaulting to `hours_requested`, same interaction as
  `node_resolution/review.html`) / POST (apply it) instead of POST-only.
  Refuses promotion — message + redirect, no state change — when every
  equipment line would be 0 approved hours. `access_tracking.html`'s
  "Promote to Accepted" is now a link to that page instead of a one-click
  POST button. Also fixed: promotion never fired `resolution_accepted` (the
  function's own docstring said it should; an inline comment right above the
  email call contradicted the docstring and said the opposite) — now calls
  `NodeResolutionService()._trigger_resolution_notification(application)`
  before the handoff email, matching the normal (non-waitlist) accept path.
  Added 3 new tests to `tests/test_batch2_phase4.py` covering the GET
  confirmation page, custom-hours confirmation, and the all-zero refusal.
- [x] Prod-data question / backfill command. This worktree's brief hedged
  ("no data command needed" if nothing was already promoted), but
  `round-october-2026.md` §4.1 **Decisions** (settled, not reopened here)
  is unconditional: "#31 ships with a small idempotent management command
  that backfills `hours_approved` for the affected REDIB-2601
  applications." Also, backlog #31 already states as fact that all 7
  REDIB-2601 waitlisted applications sit at 0 approved hours today — so
  shipped the command per the settled decision rather than re-litigating
  the "if". Added
  `applications/management/commands/backfill_waitlist_hours_approved.py`:
  reads a TSV (`application_code`, `equipment_name`, `hours_approved`),
  hard-errors on an unmatched application/equipment or a value that isn't
  a valid non-negative decimal, only ever writes a line whose current
  `hours_approved` is null/0 (never overwrites an existing nonzero value —
  logged as skipped instead), and is idempotent (rewriting the same value
  is a no-op). `--dry-run` previews without writing. **Deliberately does
  not derive figures from `hours_requested`** — the TSV has to carry
  numbers a node coordinator actually confirmed. 7 tests in
  `tests/test_backfill_waitlist_hours_approved.py` (backfill, dry-run,
  idempotency, skip-nonzero, missing app/equipment, missing file).
  **Not run against prod from here** — no prod DB access from this dev
  worktree, and the real per-equipment figures have to come from the node
  coordinators, not from me. Template at
  `data/waitlist_hours_backfill.tsv.example` with the column layout and one
  documented example row (`REDIB-2601-022`, cited in backlog #31); the
  handoff session needs to get the real 7 applications' confirmed hours
  from the node coordinators, fill in a real TSV from the template, and run
  `python manage.py backfill_waitlist_hours_approved --tsv <file> --dry-run`
  first, then for real, against prod.
- [x] Suite green; `check` + `makemigrations --check` clean — 2026-08-18:
  `python manage.py test tests` → 155 tests (145 + 3 promotion tests + 7
  backfill-command tests), 0 failures. `python manage.py test reports` and
  full `python manage.py test` also green. `check` and
  `makemigrations --check --dry-run` both clean.
- [ ] PR opened

### Deviation: a third, unrelated cause behind 2 of the 9 baseline failures

`test_applicant_can_submit_publication` and `test_full_publication_workflow`
(`tests/test_phase9_publications.py`) were in the recorded-baseline FAIL
list and looked like #7 (they errored on a `Publication.DoesNotExist` after
a masked redirect), but fixing #7 alone didn't turn them green — they hit a
**separate, pre-existing bug**: `PublicationForm`'s `application` queryset
only includes `status='completed'` applications
(`access/forms.py`), a rule explicitly locked in by
`test_form_shows_only_completed_applications` in the same test file
("Updated for the rule that publications can only be reported against
completed access"). Both failing tests used fixture applications with
`status='accepted'` (not completed) — stale from before that rule existed.
Fixed by updating the two tests' fixtures (one now creates its own
completed application instead of reusing the shared accepted one; the other
marks the application complete between the follow-up-email step and the
submission step), not by touching the form. **Did not touch** `access/forms.py`.

Noticed but **not fixed** (genuinely out of scope, flagging for backlog):
`access/tasks.py send_publication_followups` sends the 6-month reminder
email to applications with `status__in=['accepted', 'completed']`, but the
form that reminder points to only accepts `status='completed'` — an
applicant who gets the nudge while still merely `accepted` can't yet act on
it. Not a regression from this branch; pre-existing.

## Questions for the handoff session

<!-- Don't guess — park it here and continue with what doesn't depend on it. -->
- Run the backfill command against prod (see Status above): get the 7
  REDIB-2601 applications' confirmed approved hours from the node
  coordinators, build a real TSV from
  `data/waitlist_hours_backfill.tsv.example`, `--dry-run` it, then run it
  for real. Needs prod DB access this worktree doesn't have.
- Backlog item worth filing: `send_publication_followups` reminds
  `accepted`-but-not-`completed` applicants to report a publication before
  they're actually allowed to submit one (see Deviation note above).

## Return protocol

1. Keep this doc's **Status** current; note anything you deviated from.
2. `python manage.py check`; `python manage.py makemigrations --check`;
   full suite `python manage.py test tests` — record the pass/fail counts
   against the baseline above (do not make it worse; the target is green).
3. Push the branch and open a PR against `main`. PR body = the review
   packet: what changed and why, deviations from this brief, the test
   counts, anything user-facing (the promotion screen's wording and
   defaults) quoted for review, and any pre-existing bug you noticed but
   did not fix.
4. **Review tier for this bucket: diff read + suite** (no `/code-review`) —
   it is test configuration plus one coordinator-facing form. See
   `docs/developer/worktrees.md` § Review policy.

## Running locally (this worktree)

```bash
cd /home/rtasseff/projects/ReDIB-Portal-wt/baseline
source venv/bin/activate
python manage.py runserver 8002
```

`.env`, `db.sqlite3` and `media/` were copied from the `main` checkout at
creation time. To rebuild the sandbox: `python manage.py setup_localtest3_database`
(see `docs/DEVELOPMENT.md`). If `localhost:8002` doesn't reach the server
from a Windows browser, see the WSL note in `docs/developer/worktrees.md`.
