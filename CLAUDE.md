# Claude Code working context — ReDIB COA Portal

Django 5.0 / Python 3.11 web app that automates the Competitive Open Access lifecycle for the
ReDIB distributed biomedical imaging network. **Currently in rapid iterative bug-fix and
content-update mode**, deployed at `portal.redib.net`.

## Always do first

**Work out which environment we're in** before suggesting commands or making changes — the
checkout path tells you, so ask only if it's still unclear.

- **Dev (local):** `~/projects/ReDIB-Portal/` (or a worktree under `~/projects/ReDIB-Portal-wt/`).
  Python venv + SQLite + `manage.py runserver`. No Docker / Redis / Celery.
- **Prod (VPS):** `/home/deploy/ReDIB-Portal/`. Docker Compose with PostgreSQL + Redis + Celery +
  Caddy on IONOS.

**`docs/developer/` is written for dev, and only dev acts on it.** The round plan, batch plans,
handoff briefs and the backlog describe work that happens in a dev checkout and reaches prod
through `git pull origin main` — nothing else. On prod those files are **context you read, never
a to-do list you execute**: don't start a plan item, cut a branch, or run a migration because a
doc says the work is due. Prod's own work is content fixes, config tweaks, doc notes, and
**writing new entries into the backlog** — which is the right way to hand a problem you found in
production back to dev.

The app reads a single `.env` file. Templates: `.env.example` (dev) and `.env.production.template`
(prod). Full env-var reference: [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md).

**Deployment**: merge to `main` → push → SSH to VPS → `git pull` → rebuild containers. Full guide:
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Where things live

- **All documentation** is in `docs/` — start at [docs/README.md](docs/README.md). Don't put
  long-form docs in this file or the project README.
- **Reference TSVs**: `data/` — schema and load order at [data/README.md](data/README.md).
- **What we're working on right now**:
  [docs/developer/round-october-2026.md](docs/developer/round-october-2026.md) — the operating
  plan for the 2026-27 COA round (announce ~2026-09-15, call opens ~2026-10-15). Bucket order,
  worktree assignments, hard production deadlines, settled decisions, live status. **In a dev
  checkout, read this first when picking the work back up after a break**; on prod it is
  background only.
- **Backlog of deferred work**: [docs/developer/backlog.md](docs/developer/backlog.md). Drop new
  feature requests, UX nits, and known-broken-tests there when they're not in the active batch.
- **System design**: [docs/reference/redib-coa-system-design.md](docs/reference/redib-coa-system-design.md).
- **End-user walkthrough** (per role): [docs/USER_GUIDE.md](docs/USER_GUIDE.md).

## Worktrees & parallel sessions

Large buckets of work get their own branch **and directory** under
`~/projects/ReDIB-Portal-wt/<slug>/` (git worktree), with a dedicated agent
session per directory; the handoff session sits on `main` in
`~/projects/ReDIB-Portal/`. **If this checkout is a worktree, read
`docs/handoffs/<slug>.md` first** — it is the branch's brief. Conventions,
registry of active worktrees, and `scripts/new-worktree.sh` usage:
[docs/developer/worktrees.md](docs/developer/worktrees.md).

**Not on the production VPS.** The worktree scheme is a *development* device for
large code changes. On prod we work directly on `main` in
`/home/deploy/ReDIB-Portal/` and never branch: normal prod work is a content fix,
a config tweak, or a doc note — edit, commit, push, redeploy. Anything big enough
to want a branch belongs in a dev worktree and arrives here via
`git pull origin main`. Disk and the 4 GB RAM budget are tight and fully
accounted for by the running stack, so do not create extra checkouts, virtualenvs,
databases, or side containers on this machine the way you would in dev.

## In-flight long-running branches

- **`feature/marketing-site`** — Wagtail-based rebuild of the public `redib.net`
  marketing website inside this same Django project. **Parked** in its own
  worktree at `~/projects/ReDIB-Portal-wt/marketing-site/` (port 8001) as of
  2026-08-17; ships next year, not for the October 2026 call. ~40 commits
  beyond `main`, not merged or deployed. At cutover the portal moves from root
  to `/portal/` and Wagtail takes over `/`. Heads-up: changes on `main` to
  `redib/urls.py`, `redib/settings.py`, `templates/base.html`, or any portal
  app's `urls.py` are likely to conflict at merge. Full status, architecture
  decisions, and pickup instructions live on that branch at
  `docs/handoffs/marketing-site.md` and `docs/marketing/REBUILD_STATUS.md` —
  read without switching via
  `git show feature/marketing-site:docs/marketing/REBUILD_STATUS.md`. See also
  the [in-flight branches entry in the developer backlog](docs/developer/backlog.md#in-flight-branches-not-on-main).

## Workflow states (cheat-sheet)

**Call statuses**: `draft` → `announced` → `open` → `closed` → `resolved`.
`announced` is public-but-not-accepting: it shows on `/calls/` under "Upcoming
Calls" and auto-promotes to `open` on `submission_start` (daily beat task
`calls.tasks.check_call_deadlines` plus a view-level fallback on the public
pages). Publish is refused while `submission_start` is in the future — announce
instead. Announced and open calls both accept public `ConsultRequest`s.

**Application statuses**:

`draft` → `submitted` → `under_feasibility_review` → `pending_evaluation` → `under_evaluation` →
`evaluated` → `accepted` / `pending` / `rejected`

Terminals: `rejected_feasibility`, `rejected`, `declined_by_applicant`, `expired`, `completed`.

`pending` is the **waitlist** state. Same 10-day accept/decline window as `accepted`, but the
hand-off email only fires once a node coordinator clicks **"Mark as Accepted"** on Access
Tracking (`applications:promote_waitlisted`).

## Critical business rule — competitive funding reject protection

Applications with `has_competitive_funding=True` cannot be **rejected at the resolution phase** —
coordinators must accept or waitlist — **unless** at least one completed evaluation has
`recommendation='denied'`. The independent evaluator denial re-enables the reject option. Use
`Application.has_any_denied_evaluation` everywhere; do not reimplement the check. Feasibility
rejection (phase 3) and evaluator denial (phase 5) are unaffected by funding status.

Enforced in: `applications/services/node_resolution.py`, `applications/services/resolution.py`,
`applications/forms.py` (`NodeResolutionForm`, `ApplicationResolutionForm`),
`applications/views.py`.

## Conventions you'll need

### Role checks (always go through `UserRole`)

```python
user.roles.filter(role='coordinator', is_active=True).exists()
user.roles.filter(role='node_coordinator', node=node_obj, is_active=True).exists()
any(r.has_area('preclinical') for r in user.roles.filter(role='evaluator', is_active=True))
```

Decorator shortcuts in `core/decorators.py`: `@coordinator_required`, `@node_coordinator_required`,
`@evaluator_required`, `@applicant_required`, generic `@role_required('a','b')`.

### Sending an email

```python
from communications.tasks import send_email_from_template
send_email_from_template.delay(
    template_type='template_name',
    recipient_email=user.email,
    context_data={'variable': 'value', 'url': absolute_url, ...},
    recipient_user_id=user.id,
    related_application_id=application.id,
)
```
Templates live in the DB; reseed with `python manage.py seed_email_templates`. Recipient
helper: applicant emails prefer `Application.applicant_email` (form-declared PI contact) and
fall back to `Application.applicant.email`.

### TSV loaders (after the real-data prep work)

All five `populate_redib_*` commands now share these rules — match them in any new loader:
- UTF-8 read; hard-error on missing FK target or unknown enum value.
- Booleans: blank → False; only `TRUE`/`1`/`YES` (case-insensitive) flips to True.
  **One exception, and it matters:** `populate_redib_users` is **create-only by
  default** (`--update-existing` opts back in). The blank→False rule is right for
  reference data nobody edits in the portal, and wrong for the user table, where
  `phone`, `position`, `orcid`, `organization` and `auto_data_consent` are all on
  the profile form. Roles are applied in both modes. See `data/README.md` and
  backlog #43.
- Human-readable enum labels in the TSV map to short codes via a static label-map dict
  (see `populate_redib_organizations.ORG_TYPE_LABEL_MAP` and
  `populate_redib_funding_agencies.ORIGIN_LABEL_MAP`).

## Code style

- Make only the change asked for; don't refactor or add abstractions opportunistically.
- Use `get_object_or_404`, `select_related`/`prefetch_related`, the Django messages framework.
- Use `login_required` and role decorators for access control on every protected view.
- Never commit secrets (`.env`, credentials).
- Read files before editing; verify with `python manage.py check` after model/loader changes.
- Match the existing commit message style (see `git log`).
