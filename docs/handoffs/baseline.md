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
- [ ] Baseline recorded (`python manage.py test tests` before any change)
- [ ] #7 — middleware-blocked tests
- [ ] #8 — static-manifest-blocked tests
- [ ] #31 — approved hours confirmed at promotion
- [ ] Prod-data question answered (already-promoted applications? command needed?)
- [ ] Suite green; `check` + `makemigrations --check` clean
- [ ] PR opened

## Questions for the handoff session

<!-- Don't guess — park it here and continue with what doesn't depend on it. -->
- (none open at cut time)

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
