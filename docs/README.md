# ReDIB Portal Documentation

This directory contains all project documentation, reference materials, and test reports.

## When should I read what?

**I need to run the app locally tomorrow** → [QUICKSTART.md](QUICKSTART.md).

**I'm deploying to production this weekend** → [DEPLOYMENT.md](DEPLOYMENT.md). Skim [SETUP_GUIDE.md](SETUP_GUIDE.md) first for the env-var table.

**I want to understand the workflow as a user** → [USER_GUIDE.md](USER_GUIDE.md).

**I'm adding a feature or fixing a bug** → [DEVELOPMENT.md](DEVELOPMENT.md), then the latest file in [developer/](developer/).

**I have an idea / found a small UX nit / spotted a known test failure** → drop it in [developer/backlog.md](developer/backlog.md) for the next batch.

**I want to test the system end to end** → [TESTING.md](TESTING.md) plus [TEST_APPLICANTS_GUIDE.md](TEST_APPLICANTS_GUIDE.md) for seeded data, and [TEST_EMAIL_TEMPLATES.md](TEST_EMAIL_TEMPLATES.md) for verifying outgoing mail.

## Documentation Index

### Getting Started
- **[QUICKSTART.md](QUICKSTART.md)** — Development setup (venv + SQLite) and optional local Docker testing
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** — Environment-variable reference and initial data loading
- **[DEVELOPMENT.md](DEVELOPMENT.md)** — Day-to-day workflows, common commands, data loading
- **[DEPLOYMENT.md](DEPLOYMENT.md)** — Production deployment (VPS, Docker Compose, Caddy, backups, pre-launch checklist)

### User Documentation
- **[USER_GUIDE.md](USER_GUIDE.md)** — End-user guide for all roles (applicant, node coordinator, evaluator, ReDIB coordinator, admin). Rendered live in the portal at `/help/user-guide/`, so keep it self-contained: only `#anchor` links and absolute URLs — no images, no relative links to other docs.

### Testing
- **[TESTING.md](TESTING.md)** — Automated test suite summary and manual end-to-end test plan
- **[TEST_APPLICANTS_GUIDE.md](TEST_APPLICANTS_GUIDE.md)** — What `seed_test_applicants` creates and how to use it
- **[TEST_EMAIL_TEMPLATES.md](TEST_EMAIL_TEMPLATES.md)** — `send_test_emails` command for verifying every email template

### Reference Data
- **[../data/README.md](../data/README.md)** — TSV fixture format (nodes.tsv, organizations.tsv, users.tsv, equipment.tsv, funding_agencies.tsv)

### Historical / Archived
- **[archive/](archive/)** — Completed planning documents and historical notes (includes `UPDATE_PDF_APP.md` — the pre-implementation plan for the now-shipped PDF flow)

## Directory Structure

### `/developer/`
Developer guides, planning documents, and running notes:
- `round-october-2026.md` — **Current round's operating plan** (2026-27 COA call): bucket order, worktree assignments, production deadlines, settled decisions, live status. Start here when resuming work.
- `backlog.md` — **Dynamic backlog** of feature requests, UX polish, and known test issues to address in future batches. Add new ideas here when they come up but aren't being implemented immediately.
- `developer-notes.md` — Running log of design decisions, deferred improvements, and gotchas
- `worktrees.md` — **Parallel agent sessions**: one worktree dir per branch under `~/projects/ReDIB-Portal-wt/`, handoff-doc convention, registry of active worktrees, `scripts/new-worktree.sh`
- `handoff-template.md` — Template seeded into `docs/handoffs/<slug>.md` on each new worktree branch
- `branding-and-styles.md` — How to change branding, logo, colors, and CSS
- `tier1-manual-test-checklist.md` — Manual QA checklist
- `batch1-implementation-plan.md` / `batch1-progress.md` — Batch 1 (merged to main)
- `batch2-implementation-plan.md` / `batch2-progress.md` — Batch 2 (current)
- `localtest3-database-plan.md` — Spec for the `setup_localtest3_database` sandbox (10 users, 2 calls, 16 apps spanning every status)
- `localtest3-test-log.md` — Running log of the manual end-to-end walkthrough against the localtest3 sandbox
- `issue-action-plan-20260204.md`, `issues-actionplan-20260301.md` — Older dated action plans (historical)

### `/handoffs/`
One brief per worktree branch (`<slug>.md`), committed on that branch and landing here at merge as a record. See `developer/worktrees.md`.

### `/reference/`
Reference materials and specifications:
- `redib-coa-system-design.md` — Complete system design document
- `coa-application-form-spec.md` — Application form specification
- `evaluationForm_en.md` — Evaluation form specification

### `/test-reports/`
Comprehensive test reports for each phase:
- `PHASE1_PHASE2_TEST_REPORT.md` - Call Management & Application Submission
- `PHASE3_TEST_REPORT.md` - Feasibility Review
- `PHASE4_TEST_REPORT.md` - Evaluator Assignment
- `PHASE_8_9_10_TEST_RESULTS.md` - Acceptance, Publications, and Reporting

### `/archive/`
Completed planning documents and historical notes:
- `PHASE_6_CHANGE.md` - Node coordinator resolution workflow implementation
- `PHASES_8_9_10_REVIEW.md` - Phases 8-10 review and implementation
- `ACCEPTANCE_WORKFLOW_FIXED.md` - Acceptance workflow fixes
- `OPTIMIZE_SPEED.md` - Performance optimization plan
- `TESTING_NOTES.md` - Historical testing notes

## Related Documentation

- [../README.md](../README.md) - Main project README
- [../tests/README.md](../tests/README.md) - Test suite documentation
