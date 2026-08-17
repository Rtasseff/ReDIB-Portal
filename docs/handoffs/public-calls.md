# Handoff — `feature/public-calls`

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

- [ ] Baseline `python manage.py test tests` recorded: __F / __E
- [ ] A: `announced` status + migration + helpers
- [ ] A: Announce action, Publish guard, badges everywhere
- [ ] A: auto-open (beat task + view fallback), emails factored
- [ ] A: public list cards + public detail for announced calls
- [ ] A: `call_announced` template seeded; tests green
- [ ] B: `ConsultRequest` model + migration + admin
- [ ] B: form (grouped checkboxes, honeypot), view, thank-you, prefill, `?equipment=`
- [ ] B: emails to all NCs + confirmation; templates seeded
- [ ] B: rate limit + middleware exemption
- [ ] B: coordinator list; tests green
- [ ] Docs: USER_GUIDE additions, system-design/CLAUDE.md status list
- [ ] Pushed; PR opened against `main`

## Questions for the handoff session

- Exact wording of the two/three new email templates and the USER_GUIDE
  additions — list them here for Ryan's review before merge.
- Anything in the current calls code that looks like a bug rather than a
  gap for this feature — note it here, don't fix it on this branch.

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
