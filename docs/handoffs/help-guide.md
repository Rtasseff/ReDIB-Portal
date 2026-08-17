# Handoff — `feature/help-guide`

> **Merged 2026-08-17** into `main` (`f8c6ae3`, PR #32). Worktree and branch removed. Kept as a record.

| | |
|---|---|
| Branch | `feature/help-guide` |
| Worktree dir | `~/projects/ReDIB-Portal-wt/help-guide` |
| Base | `main` @ `243254e` |
| Created | 2026-08-17 |
| Runserver port | **8002** (main = 8000, marketing = 8001) |
| Handoff session | `main` checkout at `~/projects/ReDIB-Portal/` |
| Status | **Both phases done, pushed, PR open** — Phase 2 copy needs Ryan's review before merge. |

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

- [x] Baseline `python manage.py test tests` recorded: **7F / 2E** of 94 tests
      (all in `test_phase7_acceptance`, unchanged by this branch). After the
      branch: 105 tests, still 7F / 2E — same failures, no regressions.
- [x] Phase 1: dependency + `.dockerignore` + system check
- [x] Phase 1: view + URL + middleware exemption
- [x] Phase 1: template (TOC, table CSS, print CSS, back-to-top)
- [x] Phase 1: navbar link swapped, static PDF removed
- [x] Phase 1: tests green (11/11), docs updated (README, DEPLOYMENT, guide comment)
- [x] Docker context verified **here** — `docker build -t redib-test .` then
      `docker run --rm redib-test ls -la /app/docs/` lists only `USER_GUIDE.md`.
      The entrypoint's `migrate` also ran the new system check clean.
- [x] Phase 2: content-refresh diff written and listed below for review
- [x] Pushed; PR opened against `main`

### Deviations from the brief

- **TOC depth.** The spec's plain `markdown.markdown(...)` call would put all
  86 headings in the sidebar. Rendering uses `toc_depth: '2-3'` so the sidebar
  lists 46 h2/h3 entries; **every** heading (h4 included) still gets an `id`,
  so no in-page anchor broke — the anchor-integrity test covers this.
- **Page `<title>`** is the guide's own H1 ("ReDIB COA Portal - User Guide")
  rather than the literal "User guide", which is what the brief's
  "pass the guide's title to the template" is actually good for.
- **The brief says "13 tables"** — that's 13 pipe-delimited *lines*. The guide
  has exactly **one** markdown table (the dashboard-sections matrix, §Understanding
  the Dashboard). It renders correctly with the Bootstrap-style CSS.
- **No visual/print screenshot.** No headless browser in this worktree, so the
  render was verified structurally (HTML, ids, TOC div, table markup) plus by
  eye over the served HTML. Ryan did open the live page on 2026-08-17 and
  signed off on how it looks — but only after working around a WSL networking
  problem; see *WSL: `localhost:<port>` does not reach runserver* at the end
  of this doc before you try to serve it.

### Judgment call worth a second opinion

`docs/USER_GUIDE.md` has its own hand-written `## Table of Contents` section,
which now renders in the page body *next to* the sticky sidebar TOC — two
tables of contents on one screen. I left it: it's what makes the markdown
readable on GitHub, and the anchor-integrity test exists specifically to keep
it honest. If you'd rather the page showed only the sidebar, the cheap fix is
to strip that one section in `_render_user_guide()` — say the word.

## Questions for the handoff session

### Phase 2 — copy to review before merge

Bumped to **v1.3 | August 2026** with a version-history entry. Ten edits, each
tied to a change on `main` since 2026-04-20. Nothing still-accurate was rewritten.

| # | Section | Change | Driven by |
|---|---------|--------|-----------|
| 1 | Getting Started → Accessing the Portal | **New**: list of pages readable without logging in (`/calls/`, `/newsletters/`, `/help/user-guide/`) + a line that self-registration grants the applicant role | `3514e20` newsletters, `efba7a5` signup, this branch |
| 2 | Using the Portal → preamble | "Need help?" is now a dropdown (User guide + Contact us), not a bare mailto | this branch |
| 3 | Role Assignment → How roles are assigned | Self-signup auto-assigns applicant; all other roles still admin-assigned | `efba7a5` |
| 4 | Role Assignment → No-roles state | Framed as only applying to imported/admin-created accounts now | `efba7a5` |
| 5 | Applicants → Submitting an application | Save Draft on steps 2–5 really saves partial input (it used to discard it); reworded the misleading "auto-save after each step" | `2040cad`, `6f859d1` |
| 6 | Applicants → Submitting an application | **New**: the General Information interstitial between step 3 and step 4 | `110e50f` |
| 7 | Applicants → **new h4** "Talking to the node before you submit" | The two step-5 modals, what each button does, that a consult doesn't submit or block submission, and the no-equipment-yet soft path | `025b304`, `e94fcf4` |
| 8 | Node Coordinators → Feasibility review | Download PDF works on drafts for reviewers; edit buttons are applicant-only | `2c7bf91` |
| 9 | Coordinators → **new h4** "Watching a call's applications" | Edits-requested drafts stay on the call status wall; never-submitted drafts stay hidden | `6c45f2b`, `2c7bf91` |
| 10 | Coordinators → Assigning evaluators, and Evaluators → **new h4** "How you get assigned" | Auto-assign is now a whole-call allocator: COI by organization, per-evaluator cap, area match preferred-not-required, deactivated accounts excluded, unfilled-applications warning | `a745d94`, `fa9c827` |
| 11 | Coordinators → Creating a call | Start dates open at 00:00, end dates/deadlines run to 23:59 (was "23:59 for everything") | `3f6164b` |

**Checked and deliberately left alone:**

- The evaluator section already said the blind view shows funding origin. It
  was *right* and the code was wrong; `8de57bb` fixed the code, so no edit.
- Every sidebar entry the guide lists for all four roles still matches
  `templates/dashboard_base.html` exactly.

### Possible bugs — not fixed here, route them somewhere

**None found.** Nothing in the current UI contradicted the guide in a way that
looked like a bug rather than a doc gap. The one thing I stopped to check —
whether `evaluation_deadline` normalizing to 23:59 (`3f6164b`) skews the
7-day evaluator grace period — is fine: `grace_end = deadline + 7 days` in
`evaluations/views.py:106`, so the evaluator gets the whole seventh day.

Caveat on coverage: this was a **code-and-template walk**, not a click-through
of the localtest3 sandbox — there's no browser in this worktree. Everything in
the table above was verified against the views, forms and templates that
implement it, and the sidebar/nav claims were diffed against
`templates/dashboard_base.html`. A human pass over the live sandbox could
still turn up copy that reads wrong in context.

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

**If you are on Windows driving WSL, that will very likely not open** — see
the section below. Use this instead:

```bash
ALLOWED_HOSTS=localhost,127.0.0.1,$(hostname -I | awk '{print $1}') \
  python manage.py runserver 0.0.0.0:8002
# then browse to http://<WSL-IP>:8002/help/user-guide/  (hostname -I)
```

`.env`, `db.sqlite3` and `media/` were copied from the `main` checkout at
creation time; `venv/` and `staticfiles/` were built here. After adding
`Markdown` to `requirements.txt`, run `pip install -r requirements.txt` in
this venv.

## WSL: `localhost:<port>` does not reach runserver on this machine

Hit while trying to eyeball the guide page on 2026-08-17. Recorded because it
cost real time, it is **not** specific to this branch, and it contradicts what
we expected from past experience on this same machine.

**Symptom.** Django running in WSL, browser on Windows. `http://localhost:8002`
and `http://127.0.0.1:8002` both fail to connect. `http://<WSL-IP>:8002` works.

**What we established, in order:**

1. Bound to `127.0.0.1:8002` (runserver's default) → nothing on Windows, as
   expected for a namespace-local bind that the relay isn't picking up.
2. Rebound to `0.0.0.0:8002`. Inside WSL, both `127.0.0.1:8002` and
   `172.26.220.46:8002` returned 200. From Windows, **still only the WSL IP
   worked.** This is what kills the obvious explanations — an
   IPv6-vs-IPv4 `localhost` resolution mismatch would have been fixed by
   binding to all interfaces, and it wasn't.
3. `netstat.exe -an` on the Windows side shows **no listener on 8002 at all**.
   WSL's localhost forwarding works by creating a `127.0.0.1:<port>` listener
   on the Windows side; there isn't one. **The relay is not running for this
   port.** That is the actual fault.
4. Ruled out — port 8002 is not inside any Windows reserved range
   (`netsh.exe interface ipv4 show excludedportrange protocol=tcp`: the
   exclusions are all ≥50000).
5. Ruled out — there is no `.wslconfig` in `%USERPROFILE%`, so
   `localhostForwarding` is at its default of **true** and networking is
   default NAT mode. Nothing is switching it off by configuration.
   WSL 2.6.1.0, kernel 6.6.87.2.

**Hypothesis for "but this always worked before."** Windows currently has a
**native** `python3.13.exe` (PID 65252 at the time of writing) listening on
`0.0.0.0:8000` — a Windows-side Python, nothing to do with WSL. If earlier
dev work used the default port 8000 and was checked at `localhost:8000` from
Windows, that would have connected to *this Windows process*, not to WSL,
and would look identical from the browser. Unverified, but it fits: 8000 has
a Windows listener, 8002 has none, and 8002 is the one that fails. Worth a
glance at what that process is — it may also collide with the `main`
checkout's runserver, which uses 8000.

**Workarounds, cheapest first:**

- Browse to `http://<WSL-IP>:8002/...` (`hostname -I`). Requires binding
  `0.0.0.0` **and** putting the WSL IP in `ALLOWED_HOSTS` — it defaults to
  `['localhost', '127.0.0.1']`, so the WSL IP returns **400**, not a
  connection error. The IP changes on every WSL restart.
- `wsl --shutdown` from Windows, then restart the distro. Standard fix for a
  wedged localhost relay; not attempted here because it would have killed the
  session mid-task.

**Not a code problem.** Nothing in the app or its settings was changed for
any of this — the bind address and the extra `ALLOWED_HOSTS` entry were
passed on the command line for the session only.
