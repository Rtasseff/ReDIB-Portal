# Handoff — `feature/public-calls`

> **Merged 2026-08-18** into `main` (`705552f`, PR #33) with four review fix-ups (`2ee0c7c`). Worktree and branch removed. Kept as a record.

| | |
|---|---|
| Branch | `feature/public-calls` |
| Worktree dir | `~/projects/ReDIB-Portal-wt/public-calls` |
| Base | `main` @ `f813575` |
| Created | 2026-08-17 |
| Runserver port | **8003** (main 8000, marketing 8001, help-guide 8002) |
| Handoff session | `main` checkout at `~/projects/ReDIB-Portal/` |
| Backlog items | Features **#24** (upcoming calls) and **#25** (public equipment consult) in `docs/developer/backlog.md` |
| Status | **Ready to start.** All design decisions taken; see "Context & decisions". |

Read this first, then `CLAUDE.md`, then `docs/README.md`. This directory is
a git worktree: it *is* this branch — do not `git checkout` another branch
here (see `docs/developer/worktrees.md`). This is the **dev** environment
(SQLite, venv, runserver); nothing here is production.

## Goal

For the **October 2026 call** ReDIB wants to (1) advertise the call on the
public `/calls/` page **before** it opens, and (2) let anyone — logged in
or not — ask a node coordinator for a consult about **specific equipment**
listed on that call, directly from the call page, even while the call is
still upcoming.

Two workstreams, one branch, because (2) depends on (1):

- **A. Announce ≠ Open.** A coordinator can *announce* a call; it appears
  under "Upcoming Calls" with a clickable detail page showing dates and
  equipment and "Opens on …" instead of Apply. It auto-promotes to `open`
  at `submission_start`, and the existing "Now Open" email fires *then*,
  not at announce time.
- **B. Public "Request a consult".** Per-equipment buttons and a general
  button on the public call detail lead to a public form; the request is
  persisted, emailed to **all** node coordinators of the nodes involved,
  confirmed to the requester, and listed for coordinators.

## Scope

### A — Upcoming (announced) calls  (backlog #24)

- `calls/models.py`: add `('announced', 'Announced - Opens Soon')` to
  `Call.CALL_STATUSES` (between `draft` and `open`). Migration. Add helper
  properties `is_announced` and `is_publicly_visible` (announced/open/closed/resolved).
- Coordinator actions (`calls/views.py`, `templates/calls/detail.html`,
  `coordinator_dashboard.html`):
  - New **Announce** action (`calls:announce`, `<pk>/announce/`): allowed
    from `draft` when `submission_start` is in the future and equipment
    allocations exist; sets `status='announced'`, `published_at=now`; sends
    the new `call_announced` email to users with `receive_call_notifications=True`
    (same audience as publish). Confirm dialog like Publish.
  - Existing **Publish** (`call_publish`) stays as "open now": allowed from
    `draft` *or* `announced`. If `submission_start` is still in the future
    when a coordinator clicks Publish, either refuse with a message
    ("Use Announce; the call opens automatically on …") **or** open it
    anyway — pick refuse; the auto-open makes early Publish unnecessary.
    Publish sends the existing `call_published` ("Now Open") email.
  - Status badges/labels wherever `status == 'open'` is branched in
    templates: `templates/calls/detail.html`, `coordinator_dashboard.html`,
    `core/dashboard.html`, `evaluations/assignment_dashboard.html`,
    `evaluations/call_assignment_detail.html`, `calls/public_detail.html`.
    `grep -rn "status == 'open'" templates` and `grep -rn "status='open'" --include=*.py`
    (calls/views.py ×5, calls/tasks.py ×2, core/views.py, evaluations/views.py,
    reports/views.py, access/tasks.py) — decide per site whether `announced`
    should be included (usually **no**: announced calls take no
    applications, no evaluations, no reports).
- **Auto-open**: `calls/tasks.py:check_call_deadlines` (Celery beat, daily)
  additionally promotes `announced` calls with `submission_start <= now` to
  `open` and sends `call_published` to the opted-in audience (factor the
  email fan-out out of `call_publish` into a helper both call). Add a
  view-level fallback `_auto_open_announced_calls()` next to
  `_auto_close_expired_calls()` in `calls/views.py`, called from the two
  public views — **but** the fallback must not send emails from a request
  cycle if Celery is down; mirror the existing "gracefully handle Celery
  unavailability" try/except in `call_publish`. Note beat runs daily, so
  the open moment can lag by up to a day unless the fallback fires first —
  acceptable; say so in the coordinator UI ("opens automatically on …").
- **Public list** (`public_call_list`, `templates/calls/public_list.html`):
  `upcoming_calls = Call.objects.filter(status='announced')` (drop the
  `status='open' & future start` variant — after this branch an open call
  with a future start can't exist). Render upcoming calls as **cards linking
  to `calls:public_detail`**, showing opens/closes dates and equipment count.
- **Public detail** (`public_call_detail`): allow `status__in=['announced','open','closed','resolved']`;
  for `announced` show an "Opens on {{ submission_start }}" callout in place
  of Apply (`can_apply` already gates on `is_open`), full equipment table,
  execution window. Add the consult buttons (part B).
- Emails: new template `call_announced` in
  `communications/management/commands/seed_email_templates.py`
  ("ReDIB COA: Upcoming Call {{ call_code }} — opens {{ submission_start }}",
  same context keys as `call_published` plus `submission_start`). Reseed
  (`python manage.py seed_email_templates`) — the entrypoint does this in prod.
- Tests (`tests/test_public_calls.py`): announce action + permissions;
  Publish refused when start is future; announced call visible in list and
  detail, absent from apply/evaluation surfaces; auto-open task promotes and
  emails once; view fallback promotes without emailing when Celery is down.

### B — Public equipment consult request  (backlog #25)

- Model `calls/models.py:ConsultRequest`: `call` FK, `equipment` M2M
  (`core.Equipment`), `user` FK nullable (`settings.AUTH_USER_MODEL`,
  `on_delete=SET_NULL`), `name`, `email`, `phone` (blank), `organization`
  (blank), `message` (TextField, blank, max ~2000), `created_at`,
  `emails_sent_at` (nullable), `ip_hash` (blank; SHA-256 of REMOTE_ADDR for
  rate limiting/abuse follow-up, never displayed). Migration. Admin
  registration (read-only list).
- Form `calls/forms.py:ConsultRequestForm`: `equipment` as
  `ModelMultipleChoiceField` limited to the call's allocated equipment
  (`call.equipment_allocations`), rendered as checkboxes **grouped by node**;
  contact fields; a honeypot field (e.g. `website`, hidden via CSS, must be
  empty). At least one equipment item required.
- View `calls/views.py:public_consult_request(request, pk)` at
  `calls:public_consult` = `<pk>/consult/`. Public (no login). Call must be
  `announced` or `open`. `?equipment=<id>` pre-checks that item (from the
  per-row buttons). If `request.user.is_authenticated`, initial =
  profile values (`get_full_name()`, email, `phone`, `organization` name);
  fields stay editable. On valid POST: create `ConsultRequest`; group its
  equipment by node; for each node email **every** active `node_coordinator`
  (`UserRole.objects.filter(node=node, role='node_coordinator', is_active=True)`
  — deliberately *not* `.first()`; backlog UX #9 flags the single-recipient
  problem elsewhere, don't repeat it) using new template
  `equipment_consult_request`; send `equipment_consult_confirmation` to the
  requester; set `emails_sent_at`; redirect to a thank-you page
  (`<pk>/consult/thanks/`) that says which node(s) will get in touch and
  echoes the contact email. Nodes with no active coordinator: log a warning
  and tell the requester the ReDIB contact address (`settings.CONTACT_EMAIL`)
  as fallback; also email the ReDIB coordinator(s) in that case.
  Wrap email dispatch in the same try/except-Celery-down pattern as
  `applications/views.py:_send_consult_request_emails`; the DB row is the
  source of truth regardless.
- Abuse protection (anonymous form): honeypot + rate limit via the cache
  backend (`django.core.cache`): e.g. max 5 submissions per IP per hour and
  1 per (IP, call, identical equipment set) per 10 minutes; return the form
  with a polite error when exceeded. No captcha. Exempt `/calls/<pk>/consult/`
  paths from `ProfileCompletionMiddleware` (`core/middleware.py`,
  `EXEMPT_PREFIXES` — note `feature/help-guide` adds `'/help/'` to the same
  list; expect a trivial merge).
- Public detail template: a **"Request a consult"** button in each equipment
  row (`?equipment=<id>`) and one general button near the top of the
  equipment section; both visible for `announced` and `open` calls; not for
  closed/resolved.
- Coordinator visibility: `templates/calls/detail.html` gets a "Consult
  requests" section (count + table: when, who, contact, equipment, node),
  visible to ReDIB coordinators; node coordinators see the same list filtered
  to their node's equipment on the call detail they can already reach (or a
  small `calls:consult_requests` page — pick the least new-surface option).
- Emails: two new templates in `seed_email_templates.py`:
  `equipment_consult_request` (to NC: requester name/email/phone/org, call
  code + title, node, equipment list, message, submission window,
  `call_url`; make clear it's an informal pre-application consult, no
  workflow triggered) and `equipment_consult_confirmation` (to requester:
  what they asked for, which node(s) will contact them, `call_url`,
  ReDIB contact address). Reuse wording/tone from `feasibility_consult_request`.
- Tests: form validation (equipment required, honeypot, equipment must
  belong to the call); anonymous submit creates row + emails all NCs of
  each node + confirmation; logged-in prefill; `?equipment=` preselect;
  rate limit; closed call → 404/refused; announced call works; middleware
  exemption; coordinator list renders.

### Out (do not do here)

- redib.net / marketing-site integration (parked branch).
- Captcha or third-party anti-spam services.
- Turning consult requests into applications or feasibility reviews — this
  is informal contact only.
- Changing the existing step-5 wizard consult flow (leave
  `_send_consult_request_emails` and `tests/test_wizard_step5_consult.py`
  as they are; you may share a small helper for "all NCs of a node" if it
  stays a pure addition).
- Backlog #21 (past-calls archive) — adjacent, separate bucket.

## Acceptance

- `python manage.py check` clean; `python manage.py test tests` not worse
  than the baseline you record first; new tests green.
- Walkthrough on port 8003 with the localtest3 sandbox: coordinator creates
  a call with a future `submission_start`, clicks **Announce** → it appears
  on `/calls/` under Upcoming as a card → click → detail shows "Opens on …",
  equipment, and consult buttons; anonymous visitor submits a consult for
  two instruments on two nodes → row created, one email per NC of both
  nodes (`EMAIL_BACKEND` console in dev — show the output), confirmation to
  requester, thank-you page; logged-in applicant sees prefilled fields;
  coordinator sees the request listed. Move `submission_start` to the past
  and hit `/calls/` → call auto-opens (fallback) → Apply appears.
- Publish on a future-start call is refused with guidance.
- All new/changed email templates seeded and rendering with real context
  (`python manage.py seed_email_templates`; see `docs/TEST_EMAIL_TEMPLATES.md`).
- `docs/USER_GUIDE.md`: short additions — coordinators: Announce vs Publish;
  applicants: requesting a consult from a call page. Keep the file
  self-contained (only `#anchors`/absolute URLs — it is rendered live by
  the help-guide branch). List the exact wording in "Questions" for Ryan.
- `docs/reference/redib-coa-system-design.md` / workflow cheat-sheet in
  `CLAUDE.md`: add the `announced` call status where call statuses are
  described.

## Context & decisions already made (with Ryan, 2026-08-17)

1. **New `Call.status='announced'`**, not derived-from-dates. Reason:
   `call_publish` currently conflates "make visible" with "open" and emails
   "Now Open" regardless of the window; an explicit state keeps every
   `status='open'` assumption elsewhere true.
2. **Both** per-equipment consult buttons *and* a general button.
3. **Anonymous allowed**; honeypot + cache rate limit; **no captcha**.
4. **Announcement email** goes out at announce time to the same opted-in
   audience as Publish; "Now Open" email goes out when it actually opens.
5. **Coordinator-visible list** of consult requests in v1 (not email-only).
6. Consult emails go to **all** active NCs of each node.
7. Requests are **persisted** (`ConsultRequest`) — audit + resilience.
8. Test-suite baseline on `main` has known failures — run
   `python manage.py test tests` first and record F/E in Status.
9. Sandbox DB was rebuilt clean 2026-08-17 (`setup_localtest3_database`);
   re-run with `--reset --yes` if needed. Redis is not running in dev, so
   the cache is local-memory and Celery `.delay()` will raise → the
   try/except-Celery-down pattern is exercised for real here.

## Conflict watchlist

- `core/middleware.py` `EXEMPT_PREFIXES` — `feature/help-guide` adds
  `'/help/'`; you add the consult path. One-line merge.
- `templates/base.html` — don't touch (help-guide and marketing both do).
- `communications/management/commands/seed_email_templates.py` — append
  new templates at the end of the list; nothing else on `main` is editing
  it right now.
- `feature/marketing-site` (parked) rewrites `calls/views.py` paths to
  `reverse()`; keep new URLs named and reversed, never hardcoded.

## Status

- [x] Baseline `python manage.py test tests` recorded (2026-08-17, 94 tests): **7F / 2E**
      — `test_phase9_publications` ×2 (E), `test_phase7_acceptance` ×4,
      `test_design` ×2 (`test_calls_list_renders`, `test_dashboard_renders`),
      `test_batch2_phase4.test_node_coord_can_promote_waitlisted_application`.
- [x] A: `announced` status + migration + helpers
      (`calls/migrations/0003_…`; `is_announced`, `is_publicly_visible`,
      `accepts_consult_requests`, `Call.PUBLIC_STATUSES`)
- [x] A: Announce action, Publish guard, badges everywhere
- [x] A: auto-open (beat task + view fallback), emails factored into
      `calls/services.py`
- [x] A: public list cards + public detail for announced calls
- [x] A: `call_announced` template seeded; tests green
- [x] B: `ConsultRequest` model + migration + admin (read-only)
- [x] B: form (grouped checkboxes, honeypot), view, thank-you, prefill, `?equipment=`
- [x] B: emails to all NCs + confirmation; templates seeded
- [x] B: rate limit + middleware exemption
- [x] B: coordinator list; tests green
- [x] Docs: USER_GUIDE additions, system-design/CLAUDE.md status list
- [x] Pushed; PR opened against `main` — [#33](https://github.com/Rtasseff/ReDIB-Portal/pull/33)

**Result** (2026-08-17): `python manage.py check` clean.
`python manage.py test tests` → 134 tests, **7F / 2E — identical to the
baseline list above**, no regressions. `tests/test_public_calls.py` → 40 tests,
all green. Dev walkthrough run end-to-end on the localtest3 sandbox (announce →
public list card → detail with "Opens on" → anonymous consult across CICBIO +
CNIC → one email per NC + confirmation + thank-you → BIOIMAC has no NC, so the
ReDIB office was emailed and the requester was told → logged-in prefill →
`?equipment=` preselect → coordinator and node-coordinator lists → auto-open on
`/calls/` once the start date passed → Apply appears).

### Deviations / decisions taken while building

1. **Node-coordinator view of consult requests** = a small
   `calls:consult_requests` page (`<pk>/consult-requests/`,
   `@role_required('coordinator', 'node_coordinator')`, filtered to the NC's
   own nodes). Widening `calls:detail` (a whole call-management page) to node
   coordinators was the bigger surface. ReDIB coordinators additionally see the
   table inline on `calls/detail.html`; both render the same include
   (`templates/calls/includes/consult_requests_table.html`).
2. **Middleware exemption is by URL name**, not path prefix: `EXEMPT_URL_NAMES`
   + `resolve()` in `ProfileCompletionMiddleware`, because the consult paths
   carry a `<pk>` that a prefix list can't express — and it survives the
   `/portal/` move on `feature/marketing-site`. `EXEMPT_PREFIXES` is untouched,
   so the `feature/help-guide` `'/help/'` line still merges cleanly.
3. **`emails_sent_at` is only stamped when something actually went out**, so
   the coordinator table can flag a request nobody was told about ("Not
   emailed" badge). The DB row is written regardless.
4. **Dates in email context are pre-formatted strings** — see Questions below.
5. **Coordinator dashboard** (`core/views.py:dashboard`) now includes
   `announced` in `active_calls`; evaluation/report/assignment surfaces
   deliberately stay `['open', 'closed']`.
6. `Publish` on an `announced` call is allowed once its window has started
   (button reads **Open Now**), and refused with guidance before that.

## Questions for the handoff session

### For Ryan — wording to approve before merge

Three new email templates in
`communications/management/commands/seed_email_templates.py` (full text there;
subjects and the substance below):

1. **`call_announced`** — to everyone with `receive_call_notifications=True`,
   at announce time.
   *Subject:* `ReDIB COA: Upcoming Call {{ call_code }} - opens {{ submission_start }}`
   Says the call has been announced but is **not open yet**; lists code,
   title, opens/closes dates; points out that the equipment list is already
   visible and that a consult can be requested without an account; promises a
   second email on the opening date.
2. **`equipment_consult_request`** — to **every** active node coordinator of
   each node involved (and to the ReDIB coordinator(s) when a node has none).
   *Subject:* `ReDIB COA: Equipment consult requested for {{ node_name }} ({{ call_code }})`
   Requester name / email / phone / institution, node, equipment list, call
   code + title + status, submission window, their message, a link to the call
   and to the consult-request list. Closes with "No application, feasibility
   review, or other workflow step has been triggered by this request." Tone
   follows `feasibility_consult_request`.
3. **`equipment_consult_confirmation`** — to the requester.
   *Subject:* `ReDIB COA: We received your consult request for {{ call_code }}`
   Names the node(s) that will contact them, echoes what they asked about and
   their message, states plainly that no application has been started, gives
   `settings.CONTACT_EMAIL` as the fallback contact.

USER_GUIDE additions (all self-contained, `#anchors` only):

- Phase 1 overview: two bullets on announced calls + public consult.
- Applicants → new **"Asking a node about equipment before you apply"**
  subsection (Consult button per instrument, prefill when logged in, informal
  contact only, no account needed).
- Node coordinators → new **"Consult requests from the public call pages"**
  subsection (what arrives, reply directly, nothing automatic, no-coordinator
  fallback).
- Coordinators → **"Announce vs Publish"** subsection + the Creating-a-call
  steps reworded (Draft is invisible; Announce vs Publish; auto-open lag).

### Bugs noticed in existing calls code (not fixed here)

- `call_publish` used to put **datetime objects** into `context_data` for
  `send_email_from_template.delay`. Under Celery's JSON serializer those
  arrive at the worker as raw ISO strings, so production "Now Open" emails
  would render `2026-10-01T00:00:00+00:00` while dev (eager) renders a
  formatted date. The factored-out helper (`calls/services.notify_call_audience`)
  now formats dates as `%B %d, %Y` strings before queueing, which fixes
  `call_published` as a side effect of the refactor. One other sender has the
  same shape and was left alone: `applications/tasks.py:338`
  (`'deadline': app.acceptance_deadline` in the acceptance-reminder email).
  Worth a follow-up backlog item.
- `calls/views.py:_auto_close_expired_calls` uses `.update()`, which skips
  `simple_history` (no historical row for auto-closes) and `updated_at`. Same
  pre-existing behaviour; the new `open_announced_calls` saves per instance
  instead, so auto-opens *are* recorded.
- `call_close` has no status guard — a `draft` or `announced` call can be
  closed directly from a crafted URL. Not reachable from the UI (the button
  only renders for `open`), so left alone.

## Return protocol

1. Keep **Status** current; note anything you deviated from.
2. `python manage.py check`; `python manage.py test tests` (not worse than
   baseline) and `python manage.py test tests.test_public_calls`.
3. Push the branch and open a PR against `main`; put the summary, the email
   wording, and the guide additions in the PR body; reference this doc.
4. The handoff session reviews/merges and deploys (entrypoint runs
   `migrate` + `seed_email_templates`), then updates the registry in
   `docs/developer/worktrees.md`.

## Running locally (this worktree)

```bash
cd ~/projects/ReDIB-Portal-wt/public-calls
source venv/bin/activate
python manage.py runserver 8003      # http://localhost:8003/calls/
```

`.env`, `db.sqlite3` and `media/` were copied from the `main` checkout at
creation time; `venv/` and `staticfiles/` were built here.
