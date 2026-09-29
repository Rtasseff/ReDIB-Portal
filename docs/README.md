# ReDIB Portal Documentation

Everything a developer or administrator needs to run, change and support the
portal. The files under **Current** are kept in step with the code. Everything
under **History** is a record of how the portal got here; don't expect it to be
current.

## Start here

| I want to… | Read |
|---|---|
| Understand what the portal is and get it running locally | [../README.md](../README.md), then [QUICKSTART.md](QUICKSTART.md) |
| Understand how the code is organised: apps, statuses, rules, scheduled jobs, email | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Find a management command or script and know when to use it | [DEVELOPMENT.md](DEVELOPMENT.md) |
| Load or change reference data (users, roles, evaluators, equipment, organizations) | [SETUP_GUIDE.md § Initial Data Setup](SETUP_GUIDE.md#initial-data-setup), then [../data/README.md](../data/README.md) for formats and recipes |
| Look up an environment variable or feature flag | [SETUP_GUIDE.md § Environment Configuration](SETUP_GUIDE.md#environment-configuration) |
| Deploy, back up, restore, or pause a scheduled job on the production server | [DEPLOYMENT.md](DEPLOYMENT.md) |
| Run the tests, or walk through the portal by hand | [TESTING.md](TESTING.md) |
| Know what users see and click | [USER_GUIDE.md](USER_GUIDE.md) |
| Know what's being worked on now and what's deferred | [developer/round-october-2026.md](developer/round-october-2026.md), [developer/backlog.md](developer/backlog.md) |

## Current

These are the canonical homes. When a change alters behaviour, update the one
file that owns it and link to it from elsewhere instead of repeating it.

| File | Owns |
|---|---|
| [QUICKSTART.md](QUICKSTART.md) | Local setup: venv, SQLite, sample data, test accounts; optional local Docker |
| [ARCHITECTURE.md](ARCHITECTURE.md) | The code map as built: apps and models, call and application status machines and who writes each transition, business rules, scheduled jobs, email plumbing, "where to look when…" |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Day-to-day commands; the reference table of every management command and script |
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | Every environment variable; how to do a first data load |
| [../data/README.md](../data/README.md) | TSV formats, loader rules and failure modes, and recipes for everyday edits |
| [DEPLOYMENT.md](DEPLOYMENT.md) | The production VPS: install, deploy, run commands, backups and restore, pausing a scheduled job, troubleshooting |
| [TESTING.md](TESTING.md) | The automated suite, the dress-rehearsal harness, and the sandboxes for manual testing |
| [TEST_EMAIL_TEMPLATES.md](TEST_EMAIL_TEMPLATES.md) | `send_test_emails`, for checking every email template |
| [USER_GUIDE.md](USER_GUIDE.md) | The end-user guide, per role |
| [developer/branding-and-styles.md](developer/branding-and-styles.md) | Logo, colours and CSS |

**The user guide is a live page.** The portal renders `USER_GUIDE.md` at
`/help/user-guide/`, so it must stay self-contained: only `#anchor` links and
absolute URLs, no images, no relative links to other docs
(`tests/test_help_guide.py` checks the anchors). It is baked into the Docker
image, so a change reaches `portal.redib.net` only after a production
`git pull` and `up -d --build`.

### Working documents (`developer/`)

| File | What it is |
|---|---|
| [round-october-2026.md](developer/round-october-2026.md) | The operating plan for the 2026-27 round: status board, deadlines, settled decisions. Read first when picking work back up |
| [backlog.md](developer/backlog.md) | Deferred work, known bugs and ideas. Add to it when you find something you aren't fixing now |
| [worktrees.md](developer/worktrees.md) | How large changes get their own branch and directory, the registry of active worktrees, and `scripts/new-worktree.sh` |
| [handoff-template.md](developer/handoff-template.md) | Seeded into `handoffs/<slug>.md` for each new worktree branch |
| [dress-rehearsal.md](developer/dress-rehearsal.md) | The pre-call rehearsal with `scripts/rehearsal.py`, and what it found in September 2026 |
| [call-lifecycle-proposal.md](developer/call-lifecycle-proposal.md) | The announced/open/closed design and its open disagreement on auto-open emails (backlog #41) |
| [developer-notes.md](developer/developer-notes.md) | Running log of design decisions and gotchas |
| [localtest3-database-plan.md](developer/localtest3-database-plan.md) | Spec for the `setup_localtest3_database` sandbox |

### Reference (`reference/`)

- [coa-application-form-spec.md](reference/coa-application-form-spec.md) and
  [evaluationForm_en.md](reference/evaluationForm_en.md): the paper forms the
  application wizard and the evaluation form reproduce.
- [redib-coa-system-design.md](reference/redib-coa-system-design.md): the
  original design specification. Parts no longer match the code;
  [ARCHITECTURE.md](ARCHITECTURE.md) is the as-built reference.

## History

Kept for the record. None of these are maintained.

- [handoffs/](handoffs/): one brief per worktree branch, describing what that
  branch changed and why. Useful for the reasoning behind a feature.
- `developer/`: `batch1-*` and `batch2-*` (the spring 2026 batches, merged),
  `issue-action-plan-20260204.md` and `issues-actionplan-20260301.md` (older
  action plans), `localtest3-test-log.md` (the April walk-through) and
  `tier1-manual-test-checklist.md` (February QA checklist).
- [test-reports/](test-reports/): phase-by-phase test reports from the build.
- [archive/](archive/): completed plans and notes, including
  `TESTING_MANUAL_PLAN_2026-04.md` (the old phase-by-phase manual test plan)
  and `root-archive/` (what used to sit in the repository's top-level
  `archive/` and `workflows/` directories).
