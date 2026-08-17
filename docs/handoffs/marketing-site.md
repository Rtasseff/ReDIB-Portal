# Handoff — `feature/marketing-site` (PARKED)

| | |
|---|---|
| Branch | `feature/marketing-site` |
| Worktree dir | `~/projects/ReDIB-Portal-wt/marketing-site` |
| Base | `main` @ `5ed16a3` (2026-08-17; branch is 39 ahead / 12 behind at parking time) |
| Parked | 2026-08-17 |
| Runserver port | **8001** (main uses 8000) |
| Handoff session | `main` checkout at `~/projects/ReDIB-Portal/` |
| Status | **Parked — not for the October 2026 call. Ships next year after a cutover conversation.** |

Read this first, then `docs/marketing/REBUILD_STATUS.md` (the canonical
current state of the rebuild), then `CLAUDE.md`. This directory is a git
worktree: it *is* this branch — do not `git checkout` another branch here.
Conventions: `docs/developer/worktrees.md` on `main`
(`git show main:docs/developer/worktrees.md`).

## Why parked, and why in its own directory

`main` is entering a multi-week update for the **October 2026 call**
(new features + backlog sweep). This branch is structurally different from
`main` — the portal moves to `/portal/`, Wagtail owns `/`, and
`redib/urls.py`, `redib/settings.py`, `templates/base.html`, and most of
`tests/` are rewritten — and it won't reach production until next year.
Switching branches inside the `main` checkout had become fragile: one
shared `db.sqlite3` accumulated the Wagtail tables, and the venvs diverged
(this branch needs `wagtail` + `wagtail-localize`, `main` doesn't).

So the branch now lives here with its own `venv/`, `db.sqlite3` (a copy of
the shared dev DB as of 2026-08-17 — 150 Wagtail pages, 4 real nodes,
14 equipment already loaded), `media/` (team photos, governance PDFs) and
`staticfiles/`. `main` never needs to check this branch out again.

## What "parked" means for a session opened here

- **Fine to do:** anything listed in `REBUILD_STATUS.md` under
  "What's deferred but safe to scope later" or "Phase 5 work"; content
  edits; CSS/design polish; test hygiene on this branch.
- **Do not do without the handoff session:** the three human-input items
  in `REBUILD_STATUS.md` ("What's deferred and needs your input" —
  bilingual URL routing, cutover plan, admin CMS UX); merging into `main`;
  any change to production config (`docker-compose.prod.yml`, Caddyfile,
  `.env.production.template`).
- **Do not merge or rebase onto `main` yet** unless the handoff session
  asks. `main` will move a lot during Aug–Oct 2026; one deliberate
  rebase/merge when the October work settles is cheaper than tracking it
  continuously. When that time comes, expect conflicts in the watchlist
  below.

## Conflict watchlist (files also moving on `main`)

- `redib/urls.py` — full URL refactor here (portal under `/portal/`).
- `redib/settings.py` — Wagtail apps, `LocaleMiddleware`, i18n config.
- `templates/base.html` — links converted to `{% url %}` reverses.
- `applications/tasks.py`, `calls/views.py` — hardcoded portal paths →
  `reverse()`.
- `tests/*`, `reports/tests.py` — URL prefix changes throughout.
- `requirements.txt` — Wagtail lines appended at the end.
- Anything the October work adds under `docs/` (new files rarely
  conflict; edits to `docs/README.md` / `backlog.md` might).

`main`'s side of this list is kept in `docs/developer/backlog.md`
§ "In-flight branches"; the handoff session updates it as October work
touches those files.

## Verification (this worktree)

```bash
cd ~/projects/ReDIB-Portal-wt/marketing-site
source venv/bin/activate
python manage.py check                 # clean as of 2026-08-17
python manage.py migrate --check       # all applied as of 2026-08-17
python manage.py test marketing        # 3 tests OK as of 2026-08-17
python manage.py runserver 8001        # http://localhost:8001/ (ES), /en/, /portal/, /cms/
```

If `test marketing` errors with *Missing staticfiles manifest entry*, run
`python manage.py collectstatic --noinput` — `staticfiles/` is gitignored
and per-worktree.

The Wagtail `Site` row is `localhost:8000` but is the default site, so it
resolves on 8001 as well; leave it.

## Status

- [x] 2026-08-17 — moved to a dedicated worktree; env bootstrapped and
  verified (see Verification). No code changes since `ce8ac17`.
- [ ] Rebase/merge `main` once the October 2026 call work settles
  (handoff session will say when).
- [ ] Cutover conversation (DNS, Caddy, `redib.net` vs `portal.redib.net`,
  third-party CMS handoff) — 2027, not scoped.

## Questions for the handoff session

- None open at parking time. The three standing human-input items are
  tracked in `REBUILD_STATUS.md`, not duplicated here.

## Return protocol

1. Keep this doc's **Status** current; note anything you deviated from.
2. Run the Verification block above.
3. Push the branch. Do **not** open a PR against `main` until the handoff
   session asks for the rebase.
