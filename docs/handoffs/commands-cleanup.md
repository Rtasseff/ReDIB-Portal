# Handoff — `feature/commands-cleanup`

<!-- Copy of docs/developer/handoff-template.md, seeded by scripts/new-worktree.sh.
     Lives at docs/handoffs/commands-cleanup.md on the branch. Keep "Status" current. -->

| | |
|---|---|
| Branch | `feature/commands-cleanup` |
| Worktree dir | `/home/rtasseff/projects/ReDIB-Portal-wt/commands-cleanup` |
| Base | `main` @ `67b80dc` |
| Created | 2026-09-29 |
| Runserver port | 8002 |
| Handoff session | `main` checkout at `~/projects/ReDIB-Portal/` |

Read this first, then `CLAUDE.md`, then `docs/README.md`. This directory is
a git worktree: it *is* this branch — do not `git checkout` another branch
here (see `docs/developer/worktrees.md`).

**Development document.** These are instructions for the agent session working
in this worktree. Once the branch merges, this file lands on `main` as a
record — on the production VPS it is history, not a task list.

## Goal

Make the management commands safe to use and honest when they fail, before the
REDIB-2602 call opens on 2026-10-15. Five things change:
- Accounts the users loader creates stop sharing a published password.
- The users loader loses the `--sync` flag, which would deactivate every account not in the file.
- The loaders stop half-loading a file.
- The portal can **export** its users in the `users.tsv` format.
- Dev tooling that no longer works is deleted.

None of this touches a web page or a scheduled job. Everything here runs only when someone types the command.

**Timing:** PR ready by **2026-10-06**. The handoff session merges by 10-08 and prod
deploys by 10-10, before the 10-13 → 10-15 change freeze. If a piece isn't ready by
10-06, cut it from the branch and say so. Don't let it hold up the rest.

## Scope

**In** (backlog numbers from `docs/developer/backlog.md`; read each row):

1. **#82: no default password.** `populate_redib_users` creates new users with
   `set_unusable_password()` instead of `changeme123` (`:341`). A new person sets
   their own through "Forgot password" on the login page. Remove `changeme123` from
   every command's output (`populate_redib_users :498`, `setup_base_database :223`,
   `setup_test_database`), and from the docs except where history is described.
   Existing users are untouched, as today. Dev sandboxes (`setup_localtest3_database`
   and similar) keep their own documented test passwords; they are dev-only.
2. **#83: remove `--sync` from `populate_redib_users` only.** The file lists the
   ~28 people ReDIB manages, not the ~1,200 accounts on prod, so "not in the file"
   means nothing for users. Keep `--sync` on the nodes, equipment, organizations and
   funding-agency loaders, where the file is the complete list. Someone who leaves is
   deactivated by hand (recipe in `data/README.md`).
3. **New: `export_redib_users`**, the direction Ryan set in backlog #91 (read it).
   The portal becomes the authority for people, and the file becomes an export of it.
   - Writes every user who holds at least one non-applicant `UserRole` (active or
     retired), plus any `is_staff` user, in exactly the `users.tsv` columns and order.
     The one addition is a trailing `retired_roles` column: roles whose `UserRole`
     is inactive. `roles` lists active roles only, `areas` comes from the evaluator
     role, and booleans are written `TRUE`/`FALSE`. The loader reads with
     `csv.DictReader`, so it ignores `retired_roles`. Confirm that with a test, and
     say so in `data/README.md`.
   - This is what fixes #81: a retired evaluator is recorded without being re-granted.
   - **Output:** TSV to stdout by default, so on prod
     `docker compose ... exec -T web python manage.py export_redib_users > data/users.tsv`
     writes the host's checkout. Use UTF-8 with no BOM, CRLF line endings (like the
     current file), and rows sorted by email so diffs stay small. Offer
     `--output <path>` and `--format xlsx` (openpyxl is already installed, for the
     call report). The xlsx is the read-only copy people open from SharePoint.
   - **Round-trip test:** load the committed `data/users.tsv` into the test DB, export,
     and the rows and values match, apart from the new column. Don't regenerate
     `data/users.tsv` on this branch. The dev DB isn't prod, so prod regenerates it
     after deploy (write that step into the PR body).
   - **Docs:** rewrite the `data/README.md` users section and recipes around it. The
     DB is the authority for people: change it in the admin or shell, then run the
     export and commit the file. The file is still what `setup_base_database` loads on
     a fresh database. Update `DEPLOYMENT.md` § Running Management Commands the same
     way (the drift check and `--dry-run` gate stay, for anyone who does run a load).
4. **#88: loader and dev-command rough edges.** Each has a test where it's cheap.
   - (a) `setup_base_database` and `setup_test_database` raise `CommandError` (non-zero
     exit) on a failed step, instead of printing `Failed:` and exiting 0.
   - (c) The users and equipment loaders become all-or-nothing: wrap the write phase in
     `transaction.atomic()`, so a bad row leaves the DB unchanged. `--dry-run` behaves
     as now.
   - (d) An unknown role name in `users.tsv` aborts the load with `CommandError`
     listing the valid names. Validate ORCID and phone with the **same validators the
     profile form uses** (find them; don't write new ones), so a load can't create a
     user whose profile then refuses to save.
   - (e) `populate_redib_equipment` writes `technical_specs` only when the file has
     that column. Today it blanks the field on every run.
   - (f) `send_test_emails`:
     - Build each template's context the way the real sender now does, so the reminder
       and overdue subjects render (today: "Evaluation Reminder ( Pending)").
     - `--cleanup` removes the evaluator role the command granted, and **only** that
       one: never a role the person already had. Record what it created in a way
       cleanup can find.
5. **#90 and #88(b): delete dead dev tooling.**
   - The seven files in `tests/` that hold no TestCase and never run:
     `test_application_form_spec`, `test_phase1_phase2_workflow`,
     `test_phase3_feasibility_review`, `test_phase4_evaluator_assignment`,
     `test_phase5_evaluation_submission`, `test_phase6_node_resolution`,
     `test_phase6_resolution`.
   - `scripts/add_feasibility_test_apps.py` and `setup_livetest_small_database`.
   - `seed_dev_data` (it crashes on renamed `Evaluation` fields). **It feeds
     `setup_test_database` and `seed_test_applicants`** (the calls they need), so
     retire that chain too if nothing else uses it: grep tests, `scripts/rehearsal.py`
     and the docs. Then `TEST_APPLICANTS_GUIDE.md` goes to `docs/archive/`. If
     something does depend on it, fix `seed_dev_data`'s crash instead, keep the chain,
     and say which you did. Either way, `setup_localtest3_database` stays the sandbox
     of record.
   - Update every doc that names what you removed, and the `ARCHITECTURE.md` §4
     `Commands:` lists.

**Out:**
- Anything in `calls/`, `applications/views.py`, `evaluations/`, `access/` or
  templates. That's the `workflow-guards` bucket, running in parallel.
- `scripts/backup-db.sh`, `.env.production.template` and the docker-compose files:
  the handoff session is changing them on `main` (#89).
- Equipment, nodes and organizations becoming DB-authoritative. That's #91, for 2027.
- An admin button for the export.

## Acceptance

- The full suite (`python manage.py test tests reports`) is green, with new tests
  for #82, #83, the export round trip, the all-or-nothing loads, unknown role names,
  `technical_specs`, and the `send_test_emails` cleanup.
- Run on a scratch DB (`DATABASE_URL=sqlite:////<scratch>/x.sqlite3`) and record in
  Status:
  - `setup_base_database`, then `export_redib_users` diffed against
    `data/users.tsv` (only the new column differs)
  - a deliberately bad `users.tsv` (exit code non-zero, and the DB unchanged)
  - `send_test_emails --to you@example.org` then `--cleanup` with the console
    backend (subjects render; no leftover role)
- `grep -rn changeme123` finds nothing outside history.
- One `/code-review` at **medium** before the PR. It touches passwords, so this is
  the review tier from `docs/developer/worktrees.md`. Fix or answer what it flags,
  and list it in the PR body.

## Context & decisions already made

- **Main moved after this branch was cut: #92, `3da147b`, rebased in on 2026-09-29.** Bot sign-ups are stopped. The applicant role is now granted on email *confirmation* (`core/signals.py`), the signup form has a browser check and a honeypot, and there is a new command, `purge_unverified_signups`. Prod found that most of the ~1,200–1,480 accounts were bots. **Suite baseline is now 494.** Read `3da147b`'s message before you start. Don't change what it built.
- **For this branch:** add `purge_unverified_signups` to the `DEVELOPMENT.md` command table (18 commands now). The case for #83 stands, and is stronger: the file lists the few dozen real staff, not every account. **#82:** allauth's reset form (`ResetPasswordForm`, allauth 65.13) looks users up by email and `is_active` only, not by usable password. So "Forgot password" works for a loaded user with an unusable password. Add a test that proves it: load a user, then POST the reset form, and one email goes out with a reset link. Loaded users are created with a verified email and staff roles, so the new purge never touches them. Keep it that way.
- Ryan, 2026-09-29: remove `--sync` for users, add an export, and delete the dead
  scripts and commands listed above. His reasoning on why `data/*.tsv` exists at all
  is backlog #91. Don't re-open it.
- How prod edits people today, which the export simplifies, is `data/README.md`
  § Recipes. Loader rules and failure modes are in `data/README.md`. Commands are in
  `docs/DEVELOPMENT.md`.
- Never read `.env` (not with cat, grep, ls or Read); it holds secrets.

## Conflict watchlist

- `workflow-guards` (parallel) owns `USER_GUIDE.md`, most of `ARCHITECTURE.md`, and
  the competitive-funding section of `CLAUDE.md`. Here, edit only the `ARCHITECTURE.md`
  §4 `Commands:` lists and the `CLAUDE.md` "TSV loaders" section.
- `main` (#89) edits `DEPLOYMENT.md` § 6 (backups). Stay out of § 6.

## Status

- [x] #82 · [x] #83 · [x] export · [x] #88 a/c/d/e/f · [x] #90 · [x] docs · [x] /code-review · [x] PR
- **Suite:** baseline 494 OK → 522 OK (28 new, `tests/test_commands_cleanup.py`).
- **/code-review (medium):** one finding. The export can write an organization the
  profile form created that isn't in `organizations.tsv`, and a fresh
  `setup_base_database` would then fail at step 3. **Fixed:** the export warns on stderr
  for each such organization (tested), and the recipe in `data/README.md` and
  `DEPLOYMENT.md` says to add the row.
  `check` clean; `makemigrations --check` no changes.
- **#90 / #88(b):** nothing outside docs used `seed_dev_data`, so the chain is
  retired: `seed_dev_data`, `seed_test_applicants`, `setup_test_database` deleted;
  `TEST_APPLICANTS_GUIDE.md` archived. (#88(a) then only applies to `setup_base_database`.)
- **Scratch DB runs (2026-09-29, `DATABASE_URL=sqlite:///…/scratchpad/x.sqlite3`):**
  - `setup_base_database`: exit 0; 28 users, 27 roles, 14 equipment. "Password: none;
    each sets one via Forgot password".
  - `export_redib_users` vs `data/users.tsv`: every value matches as the loader reads
    it. Textual differences beyond the new column, both expected: blank booleans come
    back `FALSE`, and `bioimac@ucm.es` is not exported (no role, not staff, so the
    brief's selection rule leaves it out). Rows are sorted by email, so prod's first
    regeneration also reorders the file. Output is UTF-8, CRLF, no BOM.
  - Bad `users.tsv` (unknown role `evalutor` on row 3): exit 1, 28 users / 27 roles
    before and after. Bad org on row 3 after a good row 2: row 2 was written then
    rolled back, exit 1, counts unchanged.
  - `send_test_emails --to you@example.org` with the console backend: 15/15 sent;
    "Evaluation Reminder (1 Pending)" and "1 Evaluation Overdue" render with their
    item. `--cleanup` removed the granted evaluator role; no role left.
- **Decisions:** the export leaves out the `applicant` role (in both role columns):
  the portal grants it itself on email confirmation, and the file is ReDIB's staff
  list. `areas` comes from the active evaluator role, else the retired one, so a
  former evaluator's areas stay on record (the loader warns and ignores them).
  `send_test_emails` records the role it granted as a marker line in the test
  call's description; `--cleanup` reads it.

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
cd /home/rtasseff/projects/ReDIB-Portal-wt/commands-cleanup
source venv/bin/activate
python manage.py runserver 8002
```

`.env`, `db.sqlite3` and `media/` were copied from the `main` checkout at
creation time. To rebuild the sandbox: `python manage.py setup_localtest3_database`
(see `docs/DEVELOPMENT.md`).
