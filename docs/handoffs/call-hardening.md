# Handoff — `feature/call-hardening`

<!-- Copy of docs/developer/handoff-template.md, seeded by scripts/new-worktree.sh.
     Lives at docs/handoffs/call-hardening.md on the branch. Keep "Status" current. -->

| | |
|---|---|
| Branch | `feature/call-hardening` |
| Worktree dir | `/home/rtasseff/projects/ReDIB-Portal-wt/call-hardening` |
| Base | `main` @ `e4388a1` |
| Created | 2026-08-18 |
| Runserver port | 8003 |
| Handoff session | `main` checkout at `~/projects/ReDIB-Portal/` |

Read this first, then `CLAUDE.md`, then `docs/README.md`. This directory is
a git worktree: it *is* this branch — do not `git checkout` another branch
here (see `docs/developer/worktrees.md`).

**Round context:** bucket 2 of 6 in
[docs/developer/round-october-2026.md](../developer/round-october-2026.md).
**Merge by 2026-09-08.** Two hard production dates hang off this branch:

- **#27 must be in prod by ~2026-09-12** — ReDIB announces the new call around
  2026-09-15 *through the form this item fixes*.
- **#9 and #13-minimal must be in prod by ~2026-10-13** — the call opens
  ~2026-10-15 and #9 fires the moment the first application is submitted.

## Goal

Fix the four diagnosed bugs the new call would otherwise walk straight into:
a call-status guard that can be bypassed from the form, an hours figure that
reports 39% high, a user loader that is unsafe to re-run on production, and
feasibility requests that reach one arbitrary node coordinator instead of all
of them.

## Scope

**In, in this order** (diagnoses with file:line are in
[docs/developer/backlog.md](../developer/backlog.md) — read them there, they
are not restated here):

1. **#27** — `CallForm` exposes the raw `status` dropdown.
2. **#33** — `Call.total_approved_hours` sums `hours_requested`.
3. **#13 (minimal slice only)** — `populate_redib_users` sync semantics.
4. **#9** — fan out feasibility requests to all node coordinators.

**Out** (do not do here):
- The full #13 rewrite. Only the prod-safety slice below.
- **#12** (dedicated `edits_requested` status) and **#16** (splitting the two
  acceptance steps in the badges) — both deferred/other buckets.
- `applications/tasks.py` — owned by `feature/closeout` for the whole time
  this branch is live. Do not edit it.

## Acceptance

- **#27:** a coordinator cannot hand-set `announced` or `open` on a call from
  the edit form. The guarded announce/publish/close actions still work, and
  publish is still refused while `submission_start` is in the future (announce
  instead) — see the workflow cheat-sheet in `CLAUDE.md`.
- **#33:** the call-detail page, the admin and `reports/utils.py` agree.
  REDIB-2601 reports **1,991 h approved, not 2,176 h**; BioImaC's MRI 1T ICON
  reports 310 h, not 430 h.
- **#13:** re-running the loader against an existing user does **not** reset
  that user's password, and a dry run shows what would change before anything
  is written.
- **#9:** submitting an application creates feasibility work visible to
  **every** active `node_coordinator` of that node, all of them are emailed,
  and any one of them can act on it.
- Suite not worse than the baseline recorded below; `check` and
  `makemigrations --check` clean.

## Context & decisions already made

Settled in the round plan — implement these, don't re-litigate:

- **#27: drop `status` from `CallForm.Meta.fields`** (and from
  `templates/calls/call_form.html`) rather than validating transitions in
  `CallForm.clean`. The guarded action paths already own transitions;
  validating in the form would be a second copy of that logic to keep in
  sync. Check that call *creation* still lands in `draft`.
- **#33: fix the property to mean what its name says** — sum `hours_approved`,
  falling back to `hours_requested` only for lines not yet resolved. If a
  template loses useful information by the change, add the requested figure
  as a **separate labelled column**; don't overload one number.
- **#13 minimal = two things.** (a) `set_password` only when the row creates a
  new user; existing users keep the password they set. (b) A `--dry-run` flag
  that prints the per-field diff it would apply, so a human approves before it
  runs against prod. Anything beyond that (full sync semantics, deletions,
  reconciliation) is the deferred full item.
- **#9: keep one `FeasibilityReview` row.** Do not create a row per
  coordinator. The first question to answer is **how the feasibility views
  authorize** — if they check `review.reviewer == request.user`, change them
  to check the node role instead (`user.roles.filter(role='node_coordinator',
  node=..., is_active=True).exists()`, per `CLAUDE.md`), because emailing four
  people who then get a 403 is worse than the bug being fixed. Whoever acts
  first claims it. If that authorization change turns out to be larger than it
  looks, stop and park it in "Questions" rather than growing the bucket.
- Email sending goes through `send_email_from_template.delay(...)` with the
  argument shape in `CLAUDE.md`. Pre-format dates in `context_data` — never
  pass raw datetimes (that's backlog #28, being fixed in `closeout`).

## Conflict watchlist

- **`applications/views.py`** — `feature/baseline` is live in parallel and
  edits `promote_waitlisted_application` (~line 1404); #9 is around line 585.
  Different region, but **rebase on `main` as soon as `baseline` merges**
  (expected ~2026-08-21), because that branch also turns the test suite green
  and you want that baseline.
- **`calls/models.py`** — `feature/closeout` (cut ~2026-08-21) touches call
  status for #36. Land #33 early rather than late.
- `seed_email_templates` and `CELERY_BEAT_SCHEDULE`: if you touch them,
  **append at the end** and on conflict **keep both sides**.

## Status

<!-- Keep this current. Checklist + short dated notes. -->
- [x] Baseline recorded (`python manage.py test tests` before any change): 145 tests, 7 failures / 2 errors — 2026-08-18. Pre-existing (test_phase7_acceptance x4, test_phase9_publications x2 errors, test_batch2_phase4 x1, test_design x2). Not caused by this branch; target is "not worse," not green (green comes after `baseline` merges).
- [x] #27 — `CallForm.Meta.fields` and `call_form.html` no longer expose
  `status`. Verified via test client: rendered edit form has no `status`
  input, and POSTing a raw `status=closed`/`status=open` field is ignored
  (call status unchanged); a fresh call still lands in `draft` even when
  `status=open` is smuggled into the create POST. **Committed on its own,
  first**, per the note below — 2026-08-18.
- [x] #33 — `Call.total_approved_hours`, `CallEquipmentAllocation.total_approved_hours`
  (`calls/models.py`) now `Sum(Coalesce('hours_approved', 'hours_requested'))`
  instead of summing `hours_requested`. `reports/utils.py` Equipment Summary
  sheet calls the same (now-fixed) property, so it agrees automatically; its
  stale comment acknowledging the bug is removed. No template changes needed —
  `templates/calls/detail.html` and the admin only ever showed one number
  (mislabeled "Total Approved Hours"), so fixing the property doesn't drop any
  information that was actually being shown. Verified the aggregate logic
  with a rolled-back transaction (partial-approval row correctly changes the
  total); could not reproduce the exact 1,991h/310h REDIB-2601 figures
  locally since that data isn't in this worktree's dev DB — logic is
  verified, not the literal prod numbers.
- [x] #13 — `core/management/commands/populate_redib_users.py`: (a)
  `set_password('changeme123')` now only runs when `update_or_create` reports
  `user_created`; existing users keep their password across re-runs. (b)
  added `--dry-run`, which diffs TSV values against the DB per field (and per
  role) and writes nothing — validated end-to-end in a rolled-back
  transaction (create shows full field dump, drifted field shows old→new,
  unchanged user shows nothing, `--sync --dry-run` lists would-be
  deactivations without touching `is_active`). Orphan detection in `--sync`
  now matches by email instead of by id, so it works the same in dry-run and
  real runs.
- [x] #9 — `applications/views.py` `application_submit`: feasibility request
  emails now go to every active `node_coordinator` of each node (not just
  `review.reviewer`); the assignee stored on the single `FeasibilityReview`
  row is deterministic (`order_by('pk')`, first active coordinator). **No
  authorization change was needed** — `feasibility_queue` and
  `feasibility_review` already authorize by node role
  (`UserRole(role='node_coordinator', node=review.node, is_active=True)`),
  not by `review.reviewer == request.user`, and `feasibility_review already
  reassigns `review.reviewer = request.user` on save — so "whoever acts first
  claims it" already worked. `applications/tasks.py`'s `feasibility_reminder`
  was left untouched per the conflict watchlist (owned by `closeout`), so the
  *reminder* email for an unclaimed review still goes only to the original
  assignee, not the full fan-out — noted for the handoff session, not fixed
  here.
- [ ] Rebase on `main` after `baseline` merges — not yet needed, `baseline`
  hasn't merged as of 2026-08-18; revisit before opening the PR.
- [x] `check` + `makemigrations --check` clean, suite not worse: 145 tests,
  7 failures / 2 errors — identical to the pre-change baseline recorded
  above (same test names, no new failures).
- [ ] PR opened

**#27 ships as its own commit, first.** It gates the ~2026-09-15 announce; if
this bucket looks like missing 2026-09-08, the handoff session cherry-picks
that single commit and ships it alone. Keep it clean and self-contained.

## Questions for the handoff session

<!-- Don't guess — park it here and continue with what doesn't depend on it. -->
- **When is the next production user load?** #13's deadline is "before the
  next time `populate_redib_users` runs against prod", which is likely part of
  preparing the new call. Ryan to confirm; assume before 2026-10-13.
- **#9 leftover: `feasibility_reminder` in `applications/tasks.py` still
  emails only `review.reviewer`, not the full node-coordinator fan-out.**
  Left alone because this branch is barred from touching `applications/tasks.py`
  (owned by `closeout`). Once `closeout` merges or releases that file, worth a
  follow-up so the reminder matches the initial-request fan-out — otherwise a
  node with multiple coordinators only nags the original assignee, not the
  others, on stale pending reviews. Not blocking for October; parking here
  rather than the backlog since it's a direct consequence of this bucket's
  scope line, not a new discovery.

## Return protocol

1. Keep this doc's **Status** current; note anything you deviated from.
2. `python manage.py check`; `python manage.py makemigrations --check`;
   full suite `python manage.py test tests` — record the pass/fail counts
   against the baseline you took before starting (do not make it worse;
   after rebasing on a merged `baseline` the target is green).
3. Push the branch and open a PR against `main`. PR body = the review
   packet: what changed and why, deviations from this brief, the test
   counts, the before/after hours figures for #33, anything user-facing
   quoted for review, and any pre-existing bug you noticed but did not fix.
4. **Review tier for this bucket: targeted read + suite** — the handoff
   session reads the permission and query changes in #9 and #27 closely.
   No `/code-review` unless #9's authorization change ends up touching the
   role checks broadly, in which case run **one** at *medium* on this branch
   before opening the PR. See `docs/developer/worktrees.md` § Review policy.

## Running locally (this worktree)

```bash
cd /home/rtasseff/projects/ReDIB-Portal-wt/call-hardening
source venv/bin/activate
python manage.py runserver 8003
```

`.env`, `db.sqlite3` and `media/` were copied from the `main` checkout at
creation time. To rebuild the sandbox: `python manage.py setup_localtest3_database`
(see `docs/DEVELOPMENT.md`). If `localhost:8003` doesn't reach the server
from a Windows browser, see the WSL note in `docs/developer/worktrees.md`.
