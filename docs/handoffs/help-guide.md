# Handoff — `feature/help-guide`

| | |
|---|---|
| Branch | `feature/help-guide` |
| Worktree dir | `~/projects/ReDIB-Portal-wt/help-guide` |
| Base | `main` @ `243254e` |
| Created | 2026-08-17 |
| Runserver port | **8002** (main = 8000, marketing = 8001) |
| Handoff session | `main` checkout at `~/projects/ReDIB-Portal/` |
| Status | **Ready to start** — Phase 1 is fully specified; Phase 2 needs Ryan's review at the end. |

Read this first, then `CLAUDE.md`, then `docs/README.md`. This directory is
a git worktree: it *is* this branch — do not `git checkout` another branch
here (see `docs/developer/worktrees.md`). This is the **dev** environment
(SQLite, venv, runserver); nothing here is production.

## Goal

Make the end-user guide a **single source of truth served as a normal
portal web page**. Today `docs/USER_GUIDE.md` is the source, but the portal
hands users a static PDF (`static/documents/user_guide.pdf`) that was
converted once on 2026-04-20 and drifts silently. After this branch:

- `docs/USER_GUIDE.md` stays exactly where it is and remains the only copy.
- The portal renders it to HTML at request time at **`/help/user-guide/`**.
- "Need help? → User guide" in the navbar links to that page (no download).
- The static PDF is deleted. Printing is the browser's job (print stylesheet).

Decisions below were made with Ryan on 2026-08-17; don't re-open them.

## Scope

**In (Phase 1 — render pipeline):**
- Add `Markdown` (Python-Markdown) to `requirements.txt` (pin a `>=3.6,<4`
  style range like the other entries).
- `.dockerignore`: add `!docs/USER_GUIDE.md` **as the last line** with a
  comment. It must come after both `docs/` and `*.md` (last matching rule
  wins). Nothing else under `docs/` enters the image.
- `core/views.py`: `user_guide(request)` — public (no `login_required`).
  Reads `settings.BASE_DIR / 'docs' / 'USER_GUIDE.md'`, renders with
  `markdown.markdown(text, extensions=['tables', 'toc', 'fenced_code', 'sane_lists'])`,
  caches the rendered HTML + TOC in a module-level dict keyed by the file's
  mtime (re-read when mtime changes; effectively once per process in prod).
  Pass `html`, `toc` (from `md.toc`) and the guide's title to the template.
  Content is our own repo file — `mark_safe` it, no sanitizer.
- `core/urls.py`: `path('help/user-guide/', views.user_guide, name='user_guide')`.
- `core/middleware.py`: add `'/help/'` to `ProfileCompletionMiddleware.EXEMPT_PREFIXES`
  so a logged-in user with an incomplete profile can still read the guide.
- **System check** (`core/checks.py`, registered from `CoreConfig.ready()`):
  `Error` (id `core.E001`) if the guide file is missing. `manage.py migrate`
  runs system checks and the container entrypoint runs `migrate`, so a bad
  `.dockerignore` fails the deploy loudly instead of 404-ing the help page.
- `templates/help/user_guide.html` extending `base.html`: title "User guide";
  content column + a **sticky right-hand TOC** (`md.toc`) on `lg+` (collapse
  to top on small screens); scoped CSS under `.user-guide` so Markdown tables
  render as Bootstrap tables (`table table-sm table-striped`-equivalent via
  CSS, or post-process the HTML to add classes — either is fine); headings
  get `scroll-margin-top` so anchors aren't hidden under the navbar; a
  "Back to top" link; `@media print` hides navbar/footer/TOC.
- `templates/base.html` line ~43: dropdown item → `{% url 'core:user_guide' %}`,
  drop `download`, `target`, `rel`. Keep the "Contact us" item.
- Delete `static/documents/user_guide.pdf` (git rm). `staticfiles/` is
  gitignored; it regenerates.
- Put an HTML comment at the top of `docs/USER_GUIDE.md` (renders invisibly):
  "Rendered live in the portal at /help/user-guide/ (core.views.user_guide).
  Keep it self-contained: only `#anchor` links and absolute URLs — no
  images, no relative links to other docs." Also add one line to
  `docs/README.md` next to the USER_GUIDE entry saying the same.
- Tests (new file `tests/test_help_guide.py`, style of the existing files):
  1. `GET /help/user-guide/` anonymous → 200, contains the md's H1 text
     ("ReDIB COA Portal - User Guide").
  2. Logged-in user with incomplete profile → 200 (middleware exemption).
  3. **Anchor integrity**: parse every `](#slug)` in the md; assert each
     `slug` appears as `id="slug"` in the rendered HTML. This is the
     regression test that keeps the hand-written TOC honest.
  4. Nav: `base.html` contains the reverse of `core:user_guide` and no longer
     references `documents/user_guide.pdf`.
  5. System check fires when the guide path is patched to a missing file.
- Docs: `docs/DEPLOYMENT.md` — add "open `https://portal.redib.net/help/user-guide/`"
  to the post-deploy verify list (§4.6 / redeploy section) and note the
  `.dockerignore` exception. `docs/USER_GUIDE.md` §"Getting Help" — point at
  the page instead of the PDF if it mentions downloading.

**In (Phase 2 — content refresh, needs Ryan's review):**
The guide's body was last edited 2026-04-20 ("Version 1.2 | April 2026").
User-facing changes on `main` since then that it probably doesn't cover —
check each against the current UI in this worktree and update the relevant
role section (bump the version line to 1.3 / August 2026):
- Wizard: interstitial **"General Information"** page between step 3 and
  step 4 (2026-05-28); **pre-submission feasibility consult** flow from
  step 5 (2026-05-26); "Save Draft" behaviour fixes.
- Applicants: self-signup now auto-assigns the applicant role (2026-05-16)
  — check the "No Roles" section still describes reality.
- Reviewers/coordinators: draft PDF download visible to reviewers
  (2026-06-04); edits-requested drafts stay visible on the coordinator
  status wall (2026-05-19); auto-assign load-balancing + active-account
  requirement for evaluators (2026-05-20/21).
- **Newsletters** public section (2026-05-29) — new, not in the guide.
- Anything else you find by walking the localtest3 sandbox
  (`docs/developer/localtest3-database-plan.md`; logins are printed by the
  setup command). Compare against `docs/USER_GUIDE.md` §"Using the Portal"
  per role.
Write the changes, then **stop and list them in "Questions for the handoff
session"** — Ryan reviews copy before it ships. Don't rewrite sections that
are still accurate.

**Out** (do not do here):
- A real "Download PDF" endpoint (WeasyPrint could render the same HTML on
  the fly; deliberately deferred — print stylesheet is v1).
- Role-specific deep links in the "Need help?" dropdown (`#for-evaluators`
  etc.). Trivial later; not v1.
- Moving the guide into an app, a `help` app, i18n, or any CMS. The
  marketing branch (Wagtail) is parked and unrelated.
- Any change to production config beyond `.dockerignore`.

## Acceptance

- `python manage.py check` clean; `python manage.py test tests` not worse
  than baseline (see below); `tests/test_help_guide.py` all green.
- `/help/user-guide/` renders anonymously on port 8002 with the sticky TOC,
  every TOC link lands on its heading, tables look like Bootstrap tables,
  print preview hides chrome.
- "Need help? → User guide" opens the page in the same tab; no PDF anywhere
  in `static/` or `templates/`.
- `.dockerignore` exception present and, if Docker is available locally,
  verified: `docker build -t redib-test . && docker run --rm redib-test ls -la /app/docs/`
  shows **only** `USER_GUIDE.md`. If Docker isn't available here, say so in
  Status; the handoff session verifies at deploy time
  (`docker compose exec web ls /app/docs`).
- Phase 2 diff of `docs/USER_GUIDE.md` listed for review.

## Context & decisions already made

- Rendering happens at **request time from `docs/USER_GUIDE.md`**; the file
  does not move (Ryan wants it discoverable in `docs/`). Rejected: build
  step converting md→template (drift), moving md into an app (link churn),
  hand-written HTML template (loses GitHub-readable source).
- Public page, no login. The PDF was already public static.
- Python-Markdown's `toc` extension slugifies the same way GitHub does for
  every heading currently in the file (checked by eye for the tricky ones:
  "Getting Started (Phase 0)" → `getting-started-phase-0`,
  "For Applicants (Researchers)" → `for-applicants-researchers`,
  "Role Assignment and the \"No Roles\" State" → `role-assignment-and-the-no-roles-state`).
  Test 3 above makes this a hard guarantee.
- The md currently has: 13 tables, 0 images, 0 raw HTML, 0 relative links,
  0 mermaid. Keep it that way (comment at top).
- Test suite baseline on `main` has known failures — run
  `python manage.py test tests` **before** you change anything and record
  the count in Status; you only need to not make it worse. Known-broken
  tests are listed in `docs/developer/backlog.md` §"Test infrastructure".
- Sandbox DB in this worktree was rebuilt clean on 2026-08-17
  (`setup_localtest3_database`; 10 users / 16 applications / 20 email
  templates). Re-run it with `--reset --yes` if you break the data.

## Conflict watchlist

`feature/marketing-site` (parked, own worktree) rewrites these; keep the
edits here minimal and surgical so its eventual rebase is trivial:
- `templates/base.html` — touch **only** the dropdown `<a>` (line ~43).
- `core/urls.py` — one added `path(...)`.
- `core/middleware.py` — one list entry.
- `requirements.txt` — one appended line.
- `.dockerignore` — one line at the end.
Nothing else on `main` is currently moving in these files.

## Status

- [ ] Baseline `python manage.py test tests` recorded: __F / __E
- [ ] Phase 1: dependency + `.dockerignore` + system check
- [ ] Phase 1: view + URL + middleware exemption
- [ ] Phase 1: template (TOC, table CSS, print CSS, back-to-top)
- [ ] Phase 1: navbar link swapped, static PDF removed
- [ ] Phase 1: tests green, docs updated (README, DEPLOYMENT, guide comment)
- [ ] Docker context verified (or noted as "verify at deploy")
- [ ] Phase 2: content-refresh diff written and listed below for review
- [ ] Pushed; PR opened against `main`

## Questions for the handoff session

- (Phase 2) List each guide section you changed and why, so Ryan can review
  the copy before merge.
- Anything in the current UI that contradicts the guide and *looks like a
  bug rather than a doc gap* — note it here, don't fix it on this branch;
  the handoff session routes it to the backlog or another bucket.

## Return protocol

1. Keep **Status** current; note anything you deviated from.
2. `python manage.py check`; `python manage.py test tests` (not worse than
   baseline) and `python manage.py test tests.test_help_guide`.
3. Push the branch and open a PR against `main`; put the summary and the
   Phase 2 change list in the PR body and reference this doc.
4. The handoff session reviews/merges, deploys (entrypoint runs `migrate`
   → system check → `collectstatic` drops the removed PDF), and updates
   the registry in `docs/developer/worktrees.md`.

## Running locally (this worktree)

```bash
cd ~/projects/ReDIB-Portal-wt/help-guide
source venv/bin/activate
python manage.py runserver 8002      # http://localhost:8002/help/user-guide/
```

`.env`, `db.sqlite3` and `media/` were copied from the `main` checkout at
creation time; `venv/` and `staticfiles/` were built here. After adding
`Markdown` to `requirements.txt`, run `pip install -r requirements.txt` in
this venv.
