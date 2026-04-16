# Developer Backlog

Running list of feature requests, UX polish, and known issues to address in
future batches. **This file is dynamic** — add new items as they come up,
mark items done (or remove) when they ship in a batch.

## How to use this file

- **Add new entries** to the bottom of the relevant section. Keep each
  entry to a short title plus a one-paragraph description (what + why).
- **Tag** with priority (`Low` / `Medium` / `High`) and category in the
  table column.
- **Cross-link** to source when applicable: a test-log entry, a chat
  conversation, an issue number.
- **When picked up**: move the entry into a batch implementation plan
  (`docs/developer/batchN-implementation-plan.md`) and either delete it
  here or strike it through with a pointer to the batch. Keep the file
  short — this is a backlog, not an archive.

For comparison: `developer-notes.md` records *design decisions already
made* (with a "what to do next when ready" section). This file records
*work not yet started*.

---

## UX polish

| # | Priority | Item |
|---|----------|------|
| 1 | Low | **Equipment details drill-in on calls listing.** On `/calls/`, equipment is listed by name only with no way to view details. A click or hover affordance to surface equipment specs/availability/photos would help applicants assess fit before opening a full application. (Source: localtest3 walkthrough P1.) |
| 2 | Low | **Role-relative status coloring.** Today the status badges on application lists use the same colors regardless of who is viewing. Red could be reserved for "this viewer needs to act on this app" rather than a globally "bad" state — so an applicant sees red on apps awaiting their response, an evaluator sees red on assignments they owe, etc. Requires per-role rendering of the shared `templates/includes/status_badge.html`. (Source: localtest3 walkthrough P2.) |
| 3 | Low | **Organization picker: search/better sort in the profile form.** The organization dropdown on `/profile/` has many options and is hard to scan. Add a typeahead/autocomplete (e.g., select2 or similar lightweight HTMX widget), or at minimum sort by frequency-of-use. (Source: 2026-04-16 chat.) |

## Features

| # | Priority | Item |
|---|----------|------|
| 4 | Medium | **Auto-assign evaluators: confirm-and-review step before emails go out.** Today the ReDIB coordinator clicks the per-call auto-assign button and the system immediately creates `Evaluation` rows AND sends assignment emails. The assignments can be edited after, but the emails are already out — hard to walk back. Add a two-step flow: (1) auto-assign computes a *preview* (which evaluators would be assigned to which apps, with COI/area annotations); (2) coordinator reviews and tweaks; (3) coordinator clicks "Confirm and notify" which persists the assignments and triggers the emails. Affected: `evaluations/views.py:auto_assign_call`, `evaluations/tasks.py:assign_evaluators_to_call`, plus a new preview template. (Source: 2026-04-16 chat.) |
| 5 | Medium | **One-button reminder dispatch for outstanding work.** The daily Celery tasks (`send_feasibility_reminders`, `send_evaluation_reminders`, `notify_overdue_evaluators`, `notify_coordinator_overdue_evaluations`) handle automatic reminders well. But the ReDIB coordinator should also have an on-demand button to fire reminders for a chosen scope ("remind all open feasibility reviews now", "remind all evaluators with un-submitted scores"). Useful when a deadline is approaching off-cycle or after manual data updates. Likely a new coordinator dashboard panel that calls the existing reminder helpers in `applications/tasks.py` and `evaluations/tasks.py` synchronously per click. (Source: 2026-04-16 chat.) |
| 6 | Medium | **Application PDF download for non-applicant roles (NCs, ReDIB coordinator, evaluators).** Today `download_application_pdf` (`applications/views.py:1816`, URL `applications:download_pdf`) is hard-gated to the applicant (`pk=pk, applicant=request.user`). Extend so any user who can see an application's detail page can also download a PDF that mirrors *exactly what they see*. Three viewer scopes: **(a) ReDIB coordinator** — full PDF identical to the applicant's. **(b) Node coordinator** — full PDF for any application that requests equipment from one of their nodes. **(c) Evaluator** — *blind* PDF for any application they're assigned to evaluate, with PII stripped (applicant name, ORCID, email, phone, organization, applicant_entity) to match the blind portal view. Approach: replace the applicant-only filter with the same role-scoped permission check used by `application_detail` (see `applications/views.py:_can_view_application` or equivalent — verify); add a `blind` flag to the rendering context and a conditional in `templates/applications/application_pdf.html` that hides PII fields when `blind=True`; surface a "Download PDF" button on the detail page for these roles. Use cases: NCs/coordinators want a portable document to share with internal stakeholders; evaluators want a printable blind copy to read offline. (Source: 2026-04-16 chat.) |

## Test infrastructure

| # | Priority | Item |
|---|----------|------|
| 6 | Low | **8 tests blocked by `ProfileCompletionMiddleware`.** The middleware (`core/middleware.py`, added in batch-1) redirects logged-in users with incomplete profiles to `/profile/`. Several tests in `tests/test_design.py`, `tests/test_phase7_acceptance.py`, `tests/test_phase9_publications.py`, and `reports/tests.py` create users via `User.objects.create_user(username, email, password)` only — no `first_name`, `last_name`, `phone`, `organization`, or `position` — and so get redirected when they try to GET/POST a protected view. Fix: add a shared `make_complete_user()` helper (e.g., in `tests/__init__.py`) that fills the required fields, and update the affected `setUp` methods. (Source: 2026-04-16 chat / pre-merge review.) |
| 7 | Low | **3 tests blocked by `ManifestStaticFilesStorage`.** `tests/test_design.AuthPageRenderTest.{test_login,test_logout,test_signup}_page_renders` render templates that include `{% static 'images/Logo-ICTS-def-low.jpg' %}`. The configured storage backend requires a built `staticfiles.json` manifest, which the test environment doesn't produce. Easiest fix: override `STORAGES['staticfiles']['BACKEND']` to `django.contrib.staticfiles.storage.StaticFilesStorage` in test settings (or in those test classes via `@override_settings`). (Source: 2026-04-16 chat / pre-merge review.) |
