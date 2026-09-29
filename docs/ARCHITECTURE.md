# Architecture: the portal as built

The code map for a developer new to the project: where things live, what writes each
status, what each scheduled job sends, and where to look when something breaks. Checked
against the code at `d7ff65a` (2026-09-28). When this file and the code disagree, the
code wins; fix this file.

Not repeated here: setup ([QUICKSTART.md](QUICKSTART.md)), commands
([DEVELOPMENT.md](DEVELOPMENT.md)), env vars and first data load
([SETUP_GUIDE.md](SETUP_GUIDE.md)), TSVs ([../data/README.md](../data/README.md)),
production ([DEPLOYMENT.md](DEPLOYMENT.md)), tests ([TESTING.md](TESTING.md)) and what
users click ([USER_GUIDE.md](USER_GUIDE.md)). The original design spec,
[reference/redib-coa-system-design.md](reference/redib-coa-system-design.md), no longer
matches the code everywhere.

## 1. The system in one paragraph

The portal runs ReDIB's Competitive Open Access (COA) calls end to end. A ReDIB
coordinator creates a call, lists the equipment it offers, and announces or publishes
it. Researchers apply through a five-step wizard, and each node whose equipment is
requested checks technical feasibility. The coordinator assigns independent evaluators,
who score each application blind. ReDIB then releases the whole evaluated pool to the
nodes at once. Each node accepts, waitlists or rejects its share, and the system
combines those decisions. The applicant has ten days to accept, after which the nodes
schedule the access, track it and log the hours used. Every hand-off is an email. Daily
Celery jobs send reminders and digests but never move an application. It is one Django
project with eight local apps.

| Layer | What | Notes |
|---|---|---|
| Web | Django 5.0 / Python 3.11. Prod: gunicorn (2 workers × 4 threads) behind Caddy | Caddy does TLS and serves `/media/`; whitenoise serves `/static/` |
| Auth | django-allauth; email login; mandatory email verification | `core.User` is `AUTH_USER_MODEL`; the email is the username |
| Database | PostgreSQL 15 (prod), SQLite (dev), via `DATABASE_URL` | |
| Background | Celery worker and Celery beat, with Redis as broker | Tasks run in-process when `DEBUG=True` or under the test runner (`CELERY_TASK_ALWAYS_EAGER`) |
| Documents | WeasyPrint (application PDF), openpyxl (call report), Markdown (user guide page) | |
| Audit | django-simple-history | Gives most models a `history` |
| UI | Django templates, Bootstrap 5, crispy-forms | `djangorestframework` and `django-htmx` are installed but unused: no API endpoints; `base.html` loads htmx but no template uses it |

**Dev vs prod.** Dev runs `runserver` on SQLite, with no Redis and no worker, so
`.delay()` runs inline. **Beat never runs in dev**, so a scheduled job runs only when you
call it (`manage.py shell`, or `scripts/rehearsal.py beat`). Prod runs six services from
`docker-compose.prod.yml`: `db`, `redis`, `web`, `celery`, `celery-beat` and `caddy`.

## 2. Repository map

| Path | Contents |
|---|---|
| `redib/` | `settings.py` (one `.env`, read by django-environ), `urls.py` (root URLconf), `celery.py` (Celery app and beat schedule) |
| `core/` `calls/` `applications/` `evaluations/` `access/` `communications/` `reports/` `newsletters/` | The eight local apps (§4) |
| `templates/` | **Every** template, one folder per app. Also `base.html` (public chrome), `dashboard_base.html` (role-driven sidebar), `includes/` (status badge, phase tracker), `help/`, and `account/` (allauth pages and account emails) |
| `static/`, `data/`, `docker/` | CSS and images; reference TSVs for the `populate_redib_*` loaders; `entrypoint.sh` and `Caddyfile` |
| `scripts/` | `backup-db.sh`, `check_role_drift.py` (run before a user load), `rehearsal.py` (dev-only harness), `new-worktree.sh` |
| `tests/` | The suite; plus `reports/tests.py` |
| `home/`, `marketing/` | Present only in some dev checkouts: `__pycache__` left over from the parked `feature/marketing-site`. Not apps on `main` |

## 3. The lifecycle

### 3.1 Call statuses

```
draft ─Announce─▶ announced ─start date (auto)─▶ open ─end date (auto)─▶ closed ─Mark Call Resolved─▶ resolved
draft or announced ─Publish / Open Now─▶ open        (refused while submission_start is in the future)
open ─Close Submissions─▶ closed                      (manual, any time)
announced ─end date passed (auto)─▶ closed           (never opened; the window is gone)
```

| Transition | Written by | Code |
|---|---|---|
| draft → announced | Coordinator, **Announce**. Refused unless `draft`, with no equipment, or once `submission_start` has passed | `calls.views.call_announce` |
| draft / announced → open | Coordinator, **Publish** (the button reads **Open Now** on an announced call). Refused from any other status | `calls.views.call_publish` |
| announced → open | Automatic when `submission_start ≤ now < submission_end` | `calls.services.open_announced_calls`, called by beat `check_call_deadlines` and on every load of `/calls/` or `/calls/<pk>/` |
| open → closed; announced → closed | Automatic after `submission_end`: `calls.services.close_expired_calls`, called by the same beat task and by the page-load fallback `calls.views._auto_close_expired_calls`. It saves each call, so history records it. An announced call whose whole window has passed closes the same way. Also `assign_evaluators_to_call` run on an open call past its deadline, and the coordinator's **Close Submissions** (refused unless `open`) | `calls/services.py`, `calls/views.py`, `evaluations/tasks.py` |
| closed → resolved | Coordinator, **Mark Call Resolved**. Refused while any application is `evaluated`. Sets `is_resolution_locked` and sends no email | `calls.views.call_resolve` |

The edit form cannot change `status` (#27). It warns when saved dates disagree with the
status (`_dates_vs_status_warning`). Reopening a closed call needs a developer (backlog
#54). Start dates save as 00:00 and end dates as 23:59:59, Madrid time. Announce, Publish
and Close are POST-only (#85): a GET, such as an old link, gets a 405 and changes nothing.
`Call.resolutions_released` is a flag rather than a status: the release gate (§6.4).

### 3.2 Application statuses

This is the main path. Every transition, including the side exits, is in the table.

```
draft
  │ Submit Application (applicant)
  ▼
submitted ─(same request)─▶ under_feasibility_review
  │ every requested node has decided, none rejected
  ▼
pending_evaluation
  │ evaluator assigned (coordinator)
  ▼
under_evaluation
  │ last evaluation submitted (evaluator)
  ▼
evaluated            ◀── release gate: nodes cannot act until "Release to Nodes"
  │ last node decides; the decisions are combined (§6.5)
  ▼
accepted  |  pending (waitlist)  |  rejected ■
  │ applicant accepts → handoff email → access runs
  ▼
completed ■
```

| Transition | Written by | Code (`applications/views.py` unless noted) |
|---|---|---|
| (new) → draft | Applicant, on an open call; one draft per applicant per call. `Application.save()` assigns the code `<CALL>-NNN` | `application_create` |
| draft → submitted → under_feasibility_review | Applicant, **Submit Application**. One request makes both changes and creates a `FeasibilityReview` for each requested node | `application_submit` |
| under_feasibility_review → draft | A node coordinator picks **Request Edits** | `feasibility_review` |
| under_feasibility_review → rejected_feasibility / pending_evaluation | Whoever decides the last pending review. Any rejection gives `rejected_feasibility` | `feasibility_review` |
| pending_evaluation → under_evaluation | Coordinator, **Auto-Assign Evaluators** (moves only applications that got ≥1 evaluator), or a manual assignment | `evaluations.tasks.assign_evaluators_to_call` (run synchronously by `auto_assign_call`); `evaluations.views.manual_assign_evaluator` |
| under_evaluation → evaluated | The evaluator who submits the last outstanding evaluation, or the coordinator who **Remove**s the last outstanding one (not the only one). `final_score` becomes the mean of the `total_score`s | `evaluations.utils.check_and_transition_application`, from `submit_evaluation` and `remove_evaluator_assignment` |
| evaluated → accepted / pending / rejected | The node coordinator whose decision completes the set | `NodeResolutionService.aggregate_application_resolution` |
| accepted / pending → declined_by_applicant | Applicant, **Decline**, before the deadline | `application_acceptance` |
| accepted → completed | Applicant or node coordinator, **Mark Complete + Log Hours**; every line needs its hours. Refused unless `accepted` and the applicant has accepted | `access.views.mark_application_complete` |
| pending → accepted | **Promote to Accepted**, once the applicant has accepted the waitlist offer | `promote_waitlisted_application` |
| pending → not_reached | **Not Reached This Call**; needs the same acceptance, plus a reason | `close_out_waitlisted_application` |
| accepted / pending → expired | **Expire**, only after the deadline has passed with no answer | `expire_stalled_application` |
| expired → accepted / pending | **Reinstate**, on the application detail page. Returns to the status that `resolution` names and starts a fresh 10-day window | `reinstate_expired_application` |

Terminal: `rejected_feasibility`, `rejected`, `declined_by_applicant`, `completed`,
`not_reached`; `expired` too, unless reinstated. Acceptance itself sets flags and leaves
the status alone. When an applicant accepts an `accepted` grant, `accepted_by_applicant`
becomes True and the handoff email goes out. Accepting a waitlist offer only records the
answer. **Accept on Behalf** (`force_accept_stalled_application`) records acceptance for
a silent applicant once the deadline has passed.

**The guard.** `Application.save()` checks every status change, admin edits included,
against `Application.VALID_TRANSITIONS`, and raises `ValidationError` on any other. It
also allows `submitted → rejected_feasibility` and `pending → rejected`, which no UI
writes today. A queryset `.update()` skips both this guard and the history record.

### 3.3 Who writes a transition

The rule since #53 (August 2026): **"A beat task may compute and notify. Only a human
writes a transition."** It holds for applications: no beat task writes
`Application.status`. There are two kinds of write without a click:

- **Follow-on writes inside a person's request.** A submit, the last feasibility
  decision, the last evaluation and the last node decision each move the application on
  a step, within the request of whoever made that decision.
- **Date-driven call writes, the one exception.** `announced → open` and
  `open → closed` are written by beat `check_call_deadlines` and by the page-load
  fallback, which any visitor fires, even anonymous ones. They fit the rule because a
  coordinator chose the dates and pressed Announce or Publish; the automation only
  carries out that choice. They touch `Call.status` only. With
  `CALL_ANNOUNCEMENT_EMAILS_ENABLED` off, auto-open emails nobody. Both paths call the
  same `calls.services` functions, so they agree, and each call is saved on its own, so
  history records every change (with no user).

Some deadline states are never stored, only worked out when a page loads: the evaluation
lockout (`is_evaluation_locked`, deadline + 7 days), `acceptance_deadline_passed` and
`Call.is_open`.

## 4. Django apps

Templates for every app live in `templates/<app>/`. The only exceptions are two shadowed
copies (§10).

| App | Owns | Models | Where the code is |
|---|---|---|---|
| `core` | Users, roles, organizations, nodes, equipment. Dashboard, profile, user guide page, startup lock | `User` (`is_profile_complete`, `receive_call_notifications`), `UserRole`, `Organization`, `Node` (`name` is `organization.name`), `Equipment` (`category`, `area`) | `views.py` (`dashboard` has one section per role; `profile`; `user_guide`), `decorators.py`, `middleware.py`, `signals.py`, `context_processors.py`, `checks.py` (`core.E001`), `forms.ProfileForm`, `forms.SignupForm` (the signup browser check, #92). Commands: `populate_redib_{organizations,nodes,users,equipment}`, `setup_*_database`, `run_locked`, `purge_unverified_signups` |
| `calls` | Calls and their equipment; public call pages and consult requests; call lifecycle; per-call reminder buttons | `Call`, `CallEquipmentAllocation`, `ConsultRequest` | `views.py` (public list, detail and consult pages; coordinator manage/create/edit/detail, announce, publish, close, resolve, release, remind, and delete for a draft with no applications), `services.py` (call-audience email, auto-open, consult email, feasibility reminders), `tasks.py` |
| `applications` | Wizard, feasibility, resolution, acceptance, waitlist, stalled acceptances, execution end, PDF | `Application`, `RequestedAccess` (hours requested / approved / used per equipment line, per-line completion), `FeasibilityReview` and `NodeResolution` (one per node each), `FundingAgency` | `views.py` (~3,000 lines, sectioned by phase), `services/node_resolution.py`, `services/resolution.py` (older route), `tasks.py`, `forms.py`. Commands: `populate_redib_funding_agencies`, `seed_test_applicants`, `seed_dev_data`, `backfill_waitlist_hours_approved` |
| `evaluations` | Assignment, blind scoring, evaluator reminders | `Evaluation`: six criteria scored 0–2, `total_score` = their sum (max 12), `recommendation` approved/denied, `completed_at` set once all six are scored | `views.py` (evaluator list and form; assignment pages for `coordinator`/`admin`), `utils.py` (`check_and_transition_application`, `get_blind_application_data`, `is_evaluation_locked`, `GRACE_PERIOD_DAYS = 7`), `tasks.py` |
| `access` | After the grant: node **Scheduling** and **Access Tracking**, the applicant's **My Active Access**, completion, publications | `Publication`; `AccessGrant` (deprecated) | `views.py`, `tasks.py` |
| `communications` | All workflow email | `EmailTemplate`, `EmailLog`, `NotificationPreference` | `tasks.send_email_from_template`. Commands: `seed_email_templates`, `send_test_emails`, `send_ops_alert` |
| `reports` | Coordinator statistics and exports | `ReportGeneration` (log of Excel exports) | `views.py`, `resolution_table.py`, `utils.py` |
| `newsletters` | Public newsletters, managed in the admin | `Newsletter` (`slug`, `html_file`, `is_published`) | `views.py`: list, detail (in an iframe), raw |

**`redib/`.** In `settings.py`, `SITE_URL` is the base for absolute links in email and
`CONTACT_EMAIL` feeds templates and emails. `CALL_ANNOUNCEMENT_EMAILS_ENABLED` is off
by default; `USE_REDIS` switches the cache from LocMem to Redis; `TIME_ZONE` is
`Europe/Madrid`, and Celery uses it too. Every variable is in
[SETUP_GUIDE.md](SETUP_GUIDE.md). `urls.py` mounts `admin/`, `accounts/` (allauth; a
password change sends the user back to login), core at `''`, then `calls/`,
`applications/`, `evaluations/`, `access/`, `reports/` and `newsletters/`. Django
serves `/media/` and `/static/` itself only when `DEBUG` is on.

## 5. Roles and access

| `UserRole.role` | `node` | `areas` | Opens |
|---|---|---|---|
| `applicant` | – | – | My Applications, My Active Access, Publications. Creating a draft needs only a login |
| `node_coordinator` | required | – | Feasibility Reviews, Resolution Queue, Scheduling and Access Tracking, for that node |
| `evaluator` | – | used | My Evaluations: only their own assignments |
| `coordinator` | – | – | The ReDIB coordinator: Call Management, Assign Evaluators, Resolution, Reports. Sees every application |
| `admin` | – | – | Evaluator-assignment pages, the Resolution dashboard, and a sidebar link to `/admin/`. The Django admin itself needs `is_staff`, not this role |

- **Model.** `UserRole(user, role, node, areas, is_active)` is unique on
  `(user, role, node)`; a user may hold several. Switch a role off with
  `is_active=False` rather than deleting it. `areas` is a semicolon list of `clinical` /
  `preclinical` / `radiochemistry`, read with `area_list` or `has_area()`. It is set in
  the admin (checkboxes), by evaluators on their own **Profile**, and by
  `populate_redib_users`, which never writes a blank cell (#61).
- **Decorators** (`core/decorators.py`). `role_required(*roles)` and its shortcuts
  (`coordinator_required`, `node_coordinator_required`, `evaluator_required`,
  `applicant_required`, `admin_or_coordinator_required`) imply `login_required` and let
  superusers through. A failed check flashes an error and redirects to the dashboard,
  not a 403.
- **Object-level checks inside views** decide most access:

  | Where | Who gets through |
  |---|---|
  | `application_detail` | The applicant; a coordinator or superuser; a node coordinator of a requested node. Anyone else gets a 404 |
  | `download_application_pdf` | The same people, plus assigned evaluators, who get the **blind** PDF |
  | `feasibility_review` | An active node coordinator of that review's node, or else a 404. `reviewer` is only the default assignee |
  | `node_resolution_review` | A node coordinator of that node, or else a redirect |
  | `_can_manage_application` | A coordinator or superuser, or a node coordinator of a requested node. Guards promote, not reached, expire, accept on behalf, reinstate and execution end. The buttons are on Access Tracking, which only node coordinators can open, so ReDIB coordinators reach these actions by URL (for example, the stalled-nag links) |
  | `evaluation_detail` | Only the assigned evaluator (the query filters on it) |
  | `consult_requests` | Coordinators see all; node coordinators see only requests that touch their nodes |

  A superuser passes every decorator but holds no node role, so node-scoped pages give
  them a 404 or an empty list.
- **Template flags.** `core.context_processors.user_roles` sets `is_applicant`,
  `is_node_coordinator`, `is_evaluator`, `is_coordinator` and `is_admin`, which drive
  the sidebar in `dashboard_base.html`.
- **`ProfileCompletionMiddleware`** redirects a logged-in user to `/profile/` while
  their first name, last name, phone, organization or position is missing. Not
  redirected: staff, superusers, `/accounts/`, `/admin/`, `/help/`, `/static/`,
  `/media/`, and the public consult form and its thanks page.
- **Applicant role.** Granted when a self-registered user confirms their email, through
  `core.signals.assign_applicant_role_on_email_confirmed` (on allauth's
  `email_confirmed`). It is not granted at signup, because bots sign up with strangers'
  addresses and never confirm (#92). `application_submit` also calls `get_or_create` for
  it, as a safety net. The signal fires on every confirmation, including an address added
  later at `/accounts/email/`. So an account that already holds another role is left
  alone: a loaded or hand-added evaluator, node coordinator or coordinator never gains
  it this way.
- **Signup bot protection (#92).** Three checks run on the public signup form:
  - **Browser check.** `core.forms.SignupForm` (set in `ACCOUNT_FORMS`) refuses a post
    whose hidden `browser_check` field the page's script did not fill, or that arrived
    within 3 s of the page rendering. The person sees an error, and the web log gets a
    `Signup refused by the browser check` warning.
  - **Honeypot.** allauth's own (`ACCOUNT_SIGNUP_FORM_HONEYPOT_FIELD = 'website'`). A
    bot that fills the hidden field sees the normal "verification sent" page, but no
    account is created and no email is sent.
  - **Rate limit.** `ACCOUNT_RATE_LIMITS` caps signup POSTs at 10 an hour per IP.

  `purge_unverified_signups` deletes accounts that never confirmed their email and never
  logged in.

## 6. Business rules and where they are enforced

**6.1 Competitive-funding reject protection.** An application with
`has_competitive_funding=True` cannot be rejected at resolution unless at least one
completed evaluation recommended `denied`; always test with
`Application.has_any_denied_evaluation`. *Enforced in:*
`NodeResolutionService.apply_node_resolution` (raises `ValidationError`) and
`NodeResolutionForm` (drops the reject choice). It does not cover feasibility rejection,
an evaluator's `denied`, Not Reached This Call or Expire.

**6.2 Feasibility.** Submit gives each node with requested equipment one
`FeasibilityReview`, resets them all to `pending`, and emails every active node
coordinator of each node. A node with **no** coordinator still gets its row: `reviewer`
is parked on the first ReDIB coordinator, who is emailed instead (#48). Since only that
node's coordinator can act, the application waits until the node has one. **Request
Edits** sends it straight back to `draft`. Once none are pending, any **Reject** gives
`rejected_feasibility`, otherwise `pending_evaluation`, and the applicant gets
`feasibility_complete`. *Code:* `application_submit`, `feasibility_review`.

**6.3 Evaluator assignment** (`evaluations.tasks.assign_evaluators_to_call`, run by
**Auto-Assign Evaluators**). It takes the call's `pending_evaluation` applications, 2
evaluators each by default, from every active `evaluator` role on an active account.
*Hard rules:* no conflict of interest (the evaluator's organization name must not equal
the application's `applicant_entity`, or failing that the applicant's organization;
trimmed, case-insensitive); at most `floor(apps × n / pool) + 1` evaluations per
evaluator, counting existing ones; no duplicate pairs. *Soft rule:* prefer evaluators
whose `areas` include the application's `specialization_area`, else anyone eligible.
Applications with a conflict go first and each pass reshuffles. The page warns about
area mismatches and unfilled applications. Manual assignment
(`manual_assign_evaluator`) checks conflict of interest only. Only an incomplete
evaluation can be removed.

**6.4 Release gate.** `Call.resolutions_released` stays False until **Release to Nodes**
(`calls.views.call_release_resolutions`). The GET previews every score and flags spreads
of 5 or more; the POST sets the flag under `select_for_update`. Until then, `evaluated`
applications are missing from the node queue, `node_resolution_review` refuses,
`Call.ensure_resolutions_released()` raises in both resolution services, and
`check_and_transition_application` holds the `evaluations_complete` email. Release sends
that email once per evaluated application (skipping any already in `EmailLog`); later
evaluations send it at once.

**6.5 Combining node decisions.** Each node stores a `NodeResolution` (accept, waitlist
or reject) plus approved hours per line; a reject forces its hours to 0. When **every**
node with requested equipment has decided, `aggregate_application_resolution` (under
`select_for_update`) combines them: any reject → `rejected`, else any waitlist →
`pending`, else `accepted`. It sets `resolution_date`, sets `acceptance_deadline =
resolution_date + 10 days` for accepted or pending, and sends `resolution_<outcome>` to
the applicant.

**6.6 Acceptance window.** Accepted and waitlisted applicants get the same 10 days, after
which their page refuses and **nothing expires on its own** (#53). The stalled nag (§7)
asks the node to **Expire** or **Accept on Behalf**; both need a reason and email every
ReDIB coordinator (`stalled_acceptance_actioned`). Expiring or declining an `accepted`
grant sends `freed_capacity_notice`.

**6.7 Waitlist promotion.** **Promote to Accepted** needs `status='pending'` and
`accepted_by_applicant=True`. It sets approved hours per line (refused if all are 0) and
turns every `waitlist` `NodeResolution` into `accept`, with a comment, because the
published resolution table reads `NodeResolution`. It then clears `acceptance_deadline`
and sends `resolution_accepted`, followed by the handoff email. **Not Reached This Call**
has the same preconditions and emails `waitlist_not_reached`.

**6.8 Per-application execution end.** `effective_execution_end` returns
`Application.execution_end`, or the call's `execution_end` when that is empty. The node
sets it beside the hours on a node-resolution **accept**, at **Promote to Accepted**, or
later from the detail page (`set_execution_end`; accepted, not-completed applications
only). `set_execution_end()` stores 23:59:59 local time, and stores `None` when the date
equals the call's, so the application keeps following the call. The date may not fall
before the call's `execution_start`; across nodes, the last edit wins. The waitlist
digest and the paused completion reminders read it.

## 7. Scheduled jobs (`redib/celery.py` → `beat_schedule`)

All times are Europe/Madrid. Only the first job writes a status; all the others just
send mail. "EmailLog 24 h" means a recipient is skipped if they already have a `sent`
row for that template (and application, where one is given) in the last day.

| Time | Task | Picks out | Sends (template → to) | Duplicate guard |
|---|---|---|---|---|
| 00:15 daily | `calls.tasks.check_call_deadlines` | Announced calls whose window has started → `open`; open calls past `submission_end` → `closed` | `call_published` → opted-in users, **only if** `CALL_ANNOUNCEMENT_EMAILS_ENABLED` | The status change itself |
| 08:00 daily | `applications.tasks.send_waitlist_digest` | `pending` applications the applicant has accepted. Due at 30 days after `accepted_at`, every 30 days after that, and once in the 7 days after `effective_execution_end` | `waitlist_digest` → node coordinators, one digest per person | EmailLog 24 h per recipient. Milestone: any digest since the latest execution end |
| 08:30 daily | `calls.tasks.send_draft_nudges` | Drafts on open calls, 7 and 2 days before `submission_end` | `draft_nudge` → applicant | EmailLog 24 h per recipient + application |
| 09:00 daily | `applications.tasks.send_feasibility_reminders` | Pending reviews on applications submitted more than 5 days ago | `feasibility_reminder` → every node coordinator of the node | EmailLog 24 h per recipient + application, so it repeats daily until reviewed |
| 09:00 daily | `evaluations.tasks.send_evaluation_reminders` | Incomplete evaluations. An evaluator is due 7, 3 and 1 days before the deadline, on the deadline day, then every 2 days until lockout (deadline + 7) | One digest per evaluator: `evaluation_reminder`, or `evaluation_overdue` if any is overdue | EmailLog 24 h per recipient + template; a per-call **Remind…** send doesn't count |
| 09:45 daily | `evaluations.tasks.notify_coordinator_overdue_evaluations` | Closed calls past `evaluation_deadline` that still have incomplete evaluations. Fires in the 25 h after the deadline, and again after deadline + 7 | `coordinator_overdue_evaluations` / `coordinator_evaluations_locked` → ReDIB coordinators | The 25 h window only |
| 10:00 daily | `applications.tasks.process_acceptance_deadlines` | `accepted` / `pending` applications with no answer, deadline still ahead. Reminders fall 7, 3 and 1 days before `acceptance_deadline`; a missed one is made up | `acceptance_reminder` → applicant | Counts sends this window against rungs due, plus a 24 h guard |
| 10:15 daily | `applications.tasks.send_stalled_acceptance_reminders` | The same applications once the deadline has passed. First nag 1 day after, then every 3 days, with no limit | `stalled_acceptance_reminder` → node coordinators, ReDIB coordinators in CC (addressed to them if no node coordinator is reachable) | EmailLog 24 h per recipient + application |
| 10:00 Mon | `access.tasks.send_publication_followups` | `accepted` / `completed` applications handed off 180–187 days ago, with no `Publication` | `publication_followup` → applicant | The 7-day window matches the weekly run |
| **Paused** (08:15) | `applications.tasks.send_completion_reminders` | Grants handed off and not completed. Due 60 days after handoff, every 30 days after that, and once after `effective_execution_end` | `completion_reminder` → applicant; `completion_reminder_coordinator` → node coordinators (at most one every 7 days) | EmailLog |

The completion entry has been commented out since 2026-09-09. Missed checkpoints are
dropped, not queued, so re-enabling it resumes at the next one. The re-enable steps are
in [backlog #80](developer/backlog.md).

To run a job by hand:
`venv/bin/python manage.py shell -c "from applications.tasks import send_waitlist_digest; print(send_waitlist_digest())"`.
With a real mail backend configured, this sends real mail.

## 8. Email plumbing

**One send.** Every workflow email goes through
`communications.tasks.send_email_from_template(template_type, recipient_email,
context_data, recipient_user_id=None, related_call_id=None, related_application_id=None,
related_evaluation_id=None, cc_emails=None)`. It loads the active `EmailTemplate` for
the type and renders subject, HTML and text with Django's template engine (adding
`contact_email` if missing). It then logs an `EmailLog` row as `queued`, sends from
`DEFAULT_FROM_EMAIL` to one To address (CC deduplicated, To removed), and marks the row
`sent` with `sent_at`, or `failed` with `error_message`. A missing **or inactive**
template logs a `failed` row reading "does not exist", with no template and no related
ids. It returns True or False and **never raises**, so a caller's `try/except` never
sees a failed send (backlog #57). `.delay()` queues it on Redis (inline in dev and
tests), so its context must survive JSON: format dates first. A direct call runs
synchronously; beat tasks and several views call it that way.

**Templates live in the database**, seeded from
`communications/management/commands/seed_email_templates.py` (31 templates). The
entrypoint reseeds on **every deploy** with
`update_or_create(..., create_defaults={..., 'is_active': True})`. Subject and body are
overwritten every time, so admin edits to wording are lost; change the seed file and
reseed. `is_active` is written only on create, so switching a template off in the admin
survives deploys (#80). A new template type needs a `TEMPLATE_TYPES` entry (then
`makemigrations`) and a seed entry.

**Recipients.** Mail for an applicant goes to `application.applicant_email or
application.applicant.email`. Wizard Step 1 copies the account email into
`applicant_email` as a read-only field, so the two normally match. The exception:
`application_received` goes to the submitting account. The handoff email is addressed
to the applicant, with node coordinators in CC.

**Preferences.** A `NotificationPreference` row exists only if created in the admin; no
row means everything is on. It is read by the jobs in §7 (except the call-deadline
check and the coordinator overdue notice), the two **Remind…** buttons, the
freed-capacity notice and `evaluations_complete`. One-off workflow emails ignore it
(submission, feasibility request, assignment, resolution, handoff).
`notify_call_published` is read nowhere: call announcements go to users with
`User.receive_call_notifications=True` (default True; admin-only).

**`CALL_ANNOUNCEMENT_EMAILS_ENABLED`** is False in both env templates. While it is off,
`calls.services.notify_call_audience` logs and returns 0, and the Announce / Publish
messages tell the coordinator to announce by hand. Backlog #41 lists what must be true
before it goes on.

**EmailLog** (admin → Communications → Email logs) has a row for every send that got as
far as looking up its template. A row stuck at `queued` means the process died
mid-send. Nothing ever sets `bounced`. The duplicate checks in §7 filter on
`template__template_type`, `recipient_email`, `related_application_id` and `sent_at`, so
a failed row never counts as sent.

**Outside this path, with no EmailLog row:** allauth's account emails (confirm address,
password reset), which come from `templates/account/email/`, and `send_ops_alert`,
which calls `send_mail` directly.

| Template | Sent from | To |
|---|---|---|
| `call_announced`, `call_published` | Announce, Publish, auto-open → `calls.services.notify_call_audience` | Opted-in users; flag must be on |
| `equipment_consult_request` / `_confirmation` | Public consult form → `calls.services` | Every node coordinator of each node (ReDIB coordinators if a node has none) / the requester |
| `application_received` | `application_submit` | Applicant's account email |
| `feasibility_request` | `application_submit` | Every node coordinator of each node; ReDIB coordinators for a node with none |
| `feasibility_consult_request` | Wizard Step 5 consult request (`_send_consult_request_emails`) | Every node coordinator of each node (ReDIB coordinators if a node has none), via `calls.services.consult_recipients`, the public consult's rule |
| `feasibility_edits_requested`, `feasibility_complete` | `feasibility_review` | Applicant |
| `evaluation_assigned` | `assign_evaluators_to_call`, `manual_assign_evaluator` | Evaluator |
| `evaluations_complete` | `check_and_transition_application` (after release); **Release to Nodes** | The application's node coordinators |
| `resolution_accepted` / `_pending` / `_rejected` | `send_single_resolution_notification_task` (after the node decisions are combined, and on promotion) | Applicant |
| `handoff_notification` | `_send_handoff_email`: applicant accepts, **Promote to Accepted**, **Accept on Behalf** | Applicant; node coordinators in CC |
| `acceptance_reminder` | Beat; **Reinstate** | Applicant |
| `acceptance_expired` | **Expire**, if "notify applicant" is ticked | Applicant |
| `stalled_acceptance_actioned` | Expire / Accept on Behalf / Reinstate | ReDIB coordinators |
| `freed_capacity_notice` | Decline or Expire of an `accepted` grant (`_notify_freed_capacity`) | Node coordinators |
| `waitlist_not_reached` | **Not Reached This Call** | Applicant |
| Every other template (`feasibility_reminder`, `evaluation_reminder` / `_overdue`, `coordinator_*`, `waitlist_digest`, `stalled_acceptance_reminder`, `draft_nudge`, `publication_followup`, `completion_*`) | Beat only (§7). The two **Remind…** buttons on a call also send `feasibility_reminder` and the evaluator digests | See §7 |

## 9. Other pieces

- **PDF.** `download_application_pdf` renders `templates/applications/application_pdf.html`
  with WeasyPrint on each request and stores nothing. Evaluators get a blind version
  without applicant-identity sections. Only the applicant's own download stamps
  `pdf_generated_at`. If WeasyPrint's system libraries are missing, the log says "PDF
  generation failed" (see [DEVELOPMENT.md](DEVELOPMENT.md)).
- **Audit history.** `HistoryRequestMiddleware` records the user behind each change;
  beat-task changes carry no user, and a queryset `.update()` leaves no row. Not
  tracked: `ConsultRequest`, `EmailLog`, `NotificationPreference`, `Newsletter`,
  `ReportGeneration`. Each admin object has a **History** button. Coordinator actions
  also stamp `resolution_comments` (`[PROMOTED FROM WAITLIST]`,
  `[EXPIRED BY COORDINATOR]`, `[REINSTATED BY COORDINATOR]`, `[NOT REACHED THIS CALL]`,
  `[DECLINED BY APPLICANT]`).
- **Public pages (no login).**
  - `/calls/` and `/calls/<pk>/`: each load also runs the auto-open/close fallback.
  - `/calls/<pk>/consult/`: open while the call is announced or open. Limited to 5 per
    IP per hour, with repeats within 10 minutes dropped (tracked in the cache, which is
    Redis in prod); the IP is stored only as a SHA-256 hash.
  - `/newsletters/`: shown in an iframe.
  - `/help/user-guide/`: renders `docs/USER_GUIDE.md` (cached until the file changes).
    `.dockerignore` must keep `!docs/USER_GUIDE.md`; if the file is missing, check
    `core.E001` fails the deploy at `migrate`.
  - `/` itself is the dashboard and needs a login.
- **Reports** (coordinator-only, `/reports/`): a statistics dashboard; a three-sheet
  **Excel export** per call (`call/<id>/export/`, logged in `ReportGeneration`); and the
  **bilingual resolution table** (`call/<id>/resolution/`, plus `…/csv/en/` and
  `…/csv/es/`). The table has one row per non-draft application, takes the outcome from
  `NodeResolution` (never `Application.status`) and node names from
  `NODE_PUBLIC_NAMES`, warns about missing data, and writes nothing.
- **Django admin** (`/admin/`, needs `is_staff`). Most models use `SimpleHistoryAdmin`,
  and status edits still pass through `VALID_TRANSITIONS`. `ConsultRequest` is
  read-only; `RequestedAccess` has a "Reset completion status" action;
  `EmailTemplate.is_active` is the switch that survives deploys; newsletters are
  created here.
- **Startup lock.** `web`, `celery` and `celery-beat` all run `docker/entrypoint.sh`:
  wait for the DB → `run_locked migrate --noinput` → `collectstatic` →
  `run_locked seed_email_templates` → set the `Site` domain → `exec` the command.
  `core/management/commands/run_locked.py` holds a Postgres advisory lock (key
  `20260914`) around the command so the containers take turns (#37). On SQLite it just
  runs the command.

## 10. Legacy still in the tree

| Item | Status |
|---|---|
| `access.models.AccessGrant` | Deprecated; create no rows |
| `signed_pdf*` fields; `applications:upload_signed_pdf` | No signature is required any more; the URL redirects to the preview |
| `applications:handoff_dashboard` / `mark_completed` | Linked from nowhere. Sets `is_completed` without changing `status`; the linked path is `access:mark_complete` |
| `assign_evaluators_to_application`; `communications.tasks.send_bulk_email` | The first is used only by tests; the second is not used |
| Template types `access_scheduled`, `feasibility_rejected` | Declared but never sent, and not seeded |
| `access/templates/access/publication_*.html`; `templates/home.html`; `templates/applications/coming_soon.html` | The first are shadowed by `templates/access/`; the other two are unused |

## 11. Where to look when…

| Symptom | Look at |
|---|---|
| **An email didn't go out** | Admin → Email logs, filtered by recipient. **No row** means the code never reached the send. Check the job's filter and schedule (§7), the recipient's `NotificationPreference`, the 24 h guard, and in prod `docker compose logs celery celery-beat`. For call announcements, check `CALL_ANNOUNCEMENT_EMAILS_ENABLED`. **A `failed` row**: read `error_message`; "does not exist" can also mean the template is switched off. Signup and password emails are never logged |
| **An email's wording is wrong** | `seed_email_templates.py`, not the admin: the next deploy overwrites admin edits |
| **A status looks wrong** | The object's admin **History**, the writer tables in §3, and the `[…]` stamps in `resolution_comments`. An admin edit that is refused was blocked by `VALID_TRANSITIONS` |
| **Stuck in `under_feasibility_review`** | A `FeasibilityReview` still `pending`, often at a node with no active coordinator (#48) |
| **Stuck in `under_evaluation`** | An incomplete `Evaluation`, or an evaluator locked out after deadline + 7. Removing the last outstanding evaluator moves it on; removing the only one leaves it for a new assignment |
| **A node coordinator has nothing to resolve** | `Call.resolutions_released`; whether the application is `evaluated`; whether their node already decided (`NodeResolution`); their `UserRole` `node` and `is_active` |
| **A user can't open a page** | `user.roles.filter(is_active=True)`, the view's decorator and object check (§5), an incomplete profile (redirects to `/profile/`), and whether the account is active |
| **Auto-assign left gaps** | The warnings shown after **Auto-Assign Evaluators**, the pool size (role active *and* account active), conflict of interest by organization name, and the load cap |
| **A call is missing from `/calls/`** | Its status and its dates must agree (`Call.is_open`); saving the edit form shows a warning when they don't |
| **A loader failed** | [../data/README.md](../data/README.md). Run `scripts/check_role_drift.py`, then `--dry-run`, before any real load |
| **A reminder fired twice or not at all** | The job's row in §7 (exact days vs a window, its duplicate guard), the recipient's preferences, whether `celery-beat` is running, whether the entry is commented out, and the Madrid time zone. Running the task in `manage.py shell` against a scratch DB shows what it would pick |
| **Deploy: migrations raced, or the guide 404s** | `run_locked` and the entrypoint logs; for `core.E001`, `.dockerignore` |

## 12. Conventions

- **Role checks** go through `UserRole` (snippets in [../CLAUDE.md](../CLAUDE.md)). Give
  every protected view a decorator, and add an object-level check whenever the role
  alone isn't enough.
- **Business logic.** Multi-step rules go in `applications/services/` or
  `calls/services.py`, with views only orchestrating. A lot still lives in
  `applications/views.py`, so follow what the surrounding code does.
- **Status writes.** Set the attribute and call `save()`, so `VALID_TRANSITIONS` and
  history both run. Never use `queryset.update(status=…)`.
- **Email.** Only through `send_email_from_template`. For absolute links, use
  `settings.SITE_URL + reverse(…)` in tasks and `request.build_absolute_uri` in views.
- **Beat tasks** work out who is due and send mail; they never write a transition. They
  avoid duplicates by checking `EmailLog`, and they are registered in `redib/celery.py`.
- **Tests** live in `tests/test_<area>.py` (Django `TestCase`, no `__init__.py`) and
  `reports/tests.py`; run them with `venv/bin/python manage.py test tests reports`.
  Build users with `core.test_utils.create_complete_user`. `mail.outbox` works because
  Celery is eager under test. More in [TESTING.md](TESTING.md).
