# Worktrees & handoffs — running parallel agent sessions

How we organise parallel work on this repo: one **handoff session** sits on
`main` in the primary checkout and coordinates; each large bucket of work
gets its own branch **and its own directory** via `git worktree`, with a
dedicated agent session working in it. The human relays between sessions.

## Layout

```
~/projects/ReDIB-Portal/                 ← main checkout, handoff session lives here
~/projects/ReDIB-Portal-wt/              ← one sub-dir per active branch
    marketing-site/                      ← feature/marketing-site (parked, see below)
    <slug>/                              ← feature/<slug>, created by scripts/new-worktree.sh
```

Why siblings under one parent, not nested inside the repo: nesting a second
full checkout under `ReDIB-Portal/` makes grep/rg, IDE indexing, Docker
build context and `find` all double-hit; loose siblings clutter
`~/projects`. One dedicated parent keeps them grouped and trivial to clean
up.

## What a worktree does and doesn't share

Shared (one `.git` object store): commits, branches, remotes, stashes.
**Not shared** (gitignored, per-checkout): `.env`, `db.sqlite3`, `media/`,
`staticfiles/`, `venv/`. `scripts/new-worktree.sh` copies/creates all of
these so a fresh worktree is runnable immediately.

Rules that follow from this:

- A branch can be checked out in **only one** worktree at a time. Never
  `git checkout <other-branch>` inside a worktree dir — that dir *is* that
  branch. Switch dirs instead.
- `git worktree list` from any checkout shows every active worktree.
- Each worktree needs its own **runserver port** when running concurrently.
  Convention: `main` = 8000, then 8001, 8002, … in creation order (see the
  registry table below). The Wagtail `Site` record on the marketing branch
  is `localhost:8000` but is the default site, so it resolves on any port.
- Claude Code auto-memory is keyed by directory, so a session started in a
  worktree begins with **no** project memory. The handoff doc is the
  intended context carrier — write it so a fresh session needs nothing
  else beyond `CLAUDE.md` and `docs/`.

## Creating a bucket

From the `main` checkout, on a clean tree:

```bash
scripts/new-worktree.sh <slug> [branch-name] [base-ref]
#   slug        dir name under ~/projects/ReDIB-Portal-wt/ (also the handoff doc name)
#   branch-name default feature/<slug>; an existing branch is checked out as-is
#   base-ref    default main; used only when the branch doesn't exist yet
```

The script: creates the worktree (and branch), copies `.env` /
`db.sqlite3` / `media/`, builds a venv from that branch's
`requirements.txt`, runs `collectstatic`, seeds
`docs/handoffs/<slug>.md` from [handoff-template.md](handoff-template.md)
if it doesn't already exist, and runs `manage.py check`.

Then the handoff session:

1. Fills in the handoff doc (goal, scope, acceptance, watch-outs) and commits
   it **on the new branch** (`cd` into the worktree to commit).
2. Adds a row to the registry table below and commits that on `main`.
3. Tells the human the dir path; they open a new agent session there.

## Handoff doc convention

Every worktree branch carries `docs/handoffs/<slug>.md`, committed on that
branch. It is the first thing an agent in that dir should read
(`CLAUDE.md` says so). Sections are in the template; the important ones:

- **Goal / scope in / scope out** — the deliverable, precisely.
- **Status** — checklist the branch agent keeps current as it works.
- **Questions for the handoff session** — anything that needs the human or
  `main`; the branch agent should not guess on these.
- **Conflict watchlist** — files also moving on `main`; rebase early.
- **Return protocol** — how the branch reports back (typically: push,
  open a PR against `main`, and summarise in the handoff doc's "Status").

After merge the doc lands on `main` under `docs/handoffs/` as a record;
mark it *Merged YYYY-MM-DD* at the top rather than deleting it.

## Finishing / removing a worktree

```bash
# from the main checkout, after the branch is merged (or abandoned)
git worktree remove ~/projects/ReDIB-Portal-wt/<slug>      # add --force if dirty
git branch -d feature/<slug>                                # -D if abandoning
git worktree prune
```

Remove the row from the registry table (or mark it merged) in the same
commit.

## Registry — active worktrees

| Dir (`~/projects/ReDIB-Portal-wt/`) | Branch | Port | Since | Status |
|---|---|---|---|---|
| `marketing-site/` | `feature/marketing-site` | 8001 | 2026-08-17 | **Parked.** Wagtail rebuild of redib.net; ships next year, not for the October 2026 call. Handoff: `docs/handoffs/marketing-site.md` on the branch. |
| `help-guide/` | `feature/help-guide` | 8002 | 2026-08-17 | **Active.** Render `docs/USER_GUIDE.md` live at `/help/user-guide/` (replaces the static PDF) + content refresh. Handoff: `docs/handoffs/help-guide.md` on the branch. |

## Marketing branch — why it is parked in a worktree

`feature/marketing-site` moves the portal from `/` to `/portal/`, adds
Wagtail apps/middleware, and rewrites `redib/urls.py`, `redib/settings.py`,
`templates/base.html` and most tests. Switching branches in the `main`
checkout for it was error-prone (shared `db.sqlite3` accumulated Wagtail
tables, venvs diverged). It now has its own directory and venv and will
stay there until its cutover conversation next year; `main` proceeds with
the October 2026 call work in the meantime. Full context:
[backlog — in-flight branches](backlog.md#in-flight-branches-not-on-main).
