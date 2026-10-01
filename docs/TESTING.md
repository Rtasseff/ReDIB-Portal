# Testing

How to run the automated suite, how it is laid out, and the two sandboxes for
testing by hand. Development only: none of this runs on the production VPS.

## Run the suite

```bash
source venv/bin/activate
python manage.py test tests reports
```

**555 tests, about 2½ minutes** (148 s on the dev laptop, 2026-10-01). All
should pass on `main`.

**Why the two labels.** `tests/` has no `__init__.py`, so a bare
`python manage.py test` never looks inside it and runs only the 11 tests in
`reports/tests.py`. Naming `tests` on the command line makes Django treat it
as a start directory. The `tests.py` files in the other apps (`access`,
`applications`, `calls`, `communications`, `core`, `evaluations`,
`newsletters`) are empty stubs.

**What the runner does for you.** Django builds a throwaway in-memory SQLite
database, so your `db.sqlite3` is never touched. `redib/settings.py` detects
the test runner and runs Celery tasks eagerly and falls back to plain static
storage, so no Redis, no worker and no `collectstatic` are needed. Outgoing
email lands in `django.core.mail.outbox`, never in a real inbox.

Narrower runs while you work:

```bash
python manage.py test tests.test_release_gate                       # one file
python manage.py test tests.test_release_gate.ServiceLayerGateTest  # one class
python manage.py test tests -k waitlist                             # names matching a substring
```

Before you push a change to models or loaders, also run:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run   # "No changes detected"
```

## How the tests are organised

Each file's opening docstring names the backlog items (`#NN`) or handoff brief
it covers. File names follow the bucket of work that added them
(`test_closeout_*`, `test_eval_reminders_*`, `test_batch2_*`), so group them by
area rather than by name:

| Area | Files (`tests/` unless noted) |
|---|---|
| Calls: announce, open, edit, resolve; public pages | `test_public_calls`, `test_call_edit_warning`, `test_closeout_call_resolve` |
| Signup bot protection, applicant role on email confirmation, purging bot accounts (#92) | `test_signup_bot_protection` |
| Application wizard and applicant form | `test_wizard_save_draft`, `test_wizard_step5_consult`, `test_batch2_phase5`, `test_eval_reminders_draft_nudge` |
| Feasibility review | `test_feasibility_no_coordinator`, `test_closeout_feasibility_reminder` |
| Evaluation and evaluator reminders | `test_eval_reminders_digest`, `test_eval_reminders_dispatch` |
| Resolution, release gate, resolution table | `test_release_gate`, `test_resolution_report`, `test_batch2_phase1` |
| Acceptance, waitlist, hand-off | `test_phase7_acceptance`, `test_acceptance_repair`, `test_batch2_phase4`, `test_closeout_waitlist_deadlines`, `test_closeout_waitlist_followup` |
| Execution, completion, publications | `test_execution_deadline`, `test_closeout_completion_reminders`, `test_phase9_publications` |
| Reports and Excel export | `reports/tests.py` |
| Loaders and ops commands; the users export, `send_test_emails` | `test_user_loader_create_only`, `test_commands_cleanup`, `test_backfill_waitlist_hours_approved`, `test_run_locked` |
| UI, help page, rehearsal regressions | `test_design`, `test_help_guide`, `test_rehearsal_guards`, `test_rehearsal_polish` |

**Adding a test.** Create `tests/test_<topic>.py` with Django `TestCase`
classes; the runner picks it up with no registration. If the test logs a user
in and drives a real view, build that user with
`core.test_utils.create_complete_user`. `ProfileCompletionMiddleware`
redirects any non-staff user with an incomplete profile to `/profile/`, and a
bare `User.objects.create_user` will quietly test that redirect instead of your
view.

## Testing by hand

### The localtest3 sandbox

For clicking through screens as each role:

```bash
python manage.py setup_localtest3_database --reset --yes
python manage.py runserver
```

`--reset` wipes every non-superuser row first (without it the command fails on
a database that already has data). It creates 3 nodes, 6 instruments, 10
pre-verified accounts (password `testpass123`) and two calls:

- **`COA-LIVE-2026`** (open), with `LIVE-001` to `LIVE-010`, one or two
  applications at each live status from `draft` to `pending` (except
  `submitted`, which a real submission passes straight through to
  `under_feasibility_review`)
- **`COA-PAST-2025`** (resolved), with `PAST-001` to `PAST-006` in the
  terminal and post-resolution states (`accepted`, `completed`,
  `declined_by_applicant`, `rejected`, `rejected_feasibility`, `expired`)

The command ends by printing a cheat-sheet that maps each application code to
what it is for (for example, "`LIVE-008`: competitive funding, Reject is
blocked for the node coordinator"). The account table is in
[QUICKSTART.md](QUICKSTART.md#test-accounts-after-running-setup_localtest3_database).
The command's original design and phase walk-through are in
[developer/localtest3-database-plan.md](developer/localtest3-database-plan.md)
(April 2026; its references to `setup_localtest2_database` are historical).

### The dress-rehearsal harness

To walk a whole call in time order (announce, open, submit, nudge, close,
resolve) and see every email the portal would send at each step:

```bash
python scripts/rehearsal.py seed          # localtest3 reset + one draft call, REHEARSAL-2701, no applications
python scripts/rehearsal.py status        # call dates, application counts, emails logged
python scripts/rehearsal.py advance 15    # simulate 15 days passing (moves the call's dates back)
python scripts/rehearsal.py beat          # run every scheduled task once and report
python scripts/rehearsal.py inbox --full  # every email the sandbox logged, with bodies
```

`seed` also adds a BIOIMAC node coordinator, `nc.bioimac@test.redib.net`,
so every node has one. The script refuses to run unless `DEBUG` is on and the
database is SQLite. The stage-by-stage script to follow in the browser, and
the caveats on what `advance` does not move, are in
[developer/dress-rehearsal.md](developer/dress-rehearsal.md).

### Other test data and email checks

- **Real reference data, no calls or applications**:
  `python manage.py setup_base_database --reset --yes`.
- **Render every workflow email at once**: `send_test_emails`. See
  [TEST_EMAIL_TEMPLATES.md](TEST_EMAIL_TEMPLATES.md).
- In dev, every email, workflow and allauth alike, prints to the `runserver`
  terminal.

## Historical

- The April 2026 phase-by-phase manual test plan:
  [archive/TESTING_MANUAL_PLAN_2026-04.md](archive/TESTING_MANUAL_PLAN_2026-04.md)
- Phase-era test reports: [test-reports/](test-reports/)
- The 2026-04-16 localtest3 walk-through log:
  [developer/localtest3-test-log.md](developer/localtest3-test-log.md)
