# Worktrees & handoffs — running parallel agent sessions

> **Development document.** Worktrees are a dev device; there are none on the
> production VPS, which works directly on `main` in `/home/deploy/ReDIB-Portal/`.
> See the environment note at the top of `CLAUDE.md`.

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
  **WSL gotcha (2026-08-17):** on this machine the WSL→Windows `localhost`
  relay was not forwarding a fresh port (8002), and a Windows-native
  `python3.13.exe` was already listening on 8000. If `localhost:<port>` fails
  from the Windows browser, bind `0.0.0.0:<port>` and browse to
  `http://$(hostname -I | awk '{print $1}'):<port>/` with that IP added to
  `ALLOWED_HOSTS` for the session; or `wsl --shutdown` and restart. Full
  write-up: [../handoffs/help-guide.md](../handoffs/help-guide.md#wsl-localhostport-does-not-reach-runserver-on-this-machine).
- Claude Code auto-memory is keyed by directory, so a session started in a
  worktree begins with **no** project memory. The handoff doc is the
  intended context carrier — write it so a fresh session needs nothing
  else beyond `CLAUDE.md` and `docs/`.

## When to use a worktree at all

Not every task needs one. The handoff/worktree cycle costs a brief, a
bootstrap, and a review; it pays off when the implementation is a real
chunk of work that a fresh, cheaper session can run with. Rules of thumb:

- **Inline on `main`, in the handoff session:** backlog edits, docs/copy
  tweaks, one- or two-file fixes, anything under ~an hour. No branch, no
  brief.
- **Worktree bucket:** multi-file features, anything with a model/migration,
  anything that will take a session hours, or work you want to hand to a
  different model. One bucket = one coherent deliverable (it can have
  phases inside).

## Model split (why the briefs are as detailed as they are)

Design and the handoff brief happen on the top-tier model in the handoff
session; **branch sessions run on a cheaper model** (Opus today, Sonnet
worth trying) — switch with `/model` after opening the session in the
worktree. The brief is what makes that safe: it fixes the decisions so the
implementer never has to re-derive them. If a cheaper implementer struggles,
tighten the brief before reaching for a bigger model.

## Review policy (proportionate — never pay twice)

The branch agent already ran the suite and wrote a status log; the human
usually did a click-through. The handoff-session review adds one layer
matched to risk, not two:

| Change | Review |
|---|---|
| Docs, copy, small UI | Read the diff; run the suite. No automated review. |
| Ordinary features | Run the suite; targeted read of the risky files (permissions, queries, emails). |
| Public/anonymous surfaces, auth or permission changes, migrations that touch prod data, email fan-out, money/hours accounting | **One** `/code-review` at *medium*, ideally run **by the branch session on its own branch before opening the PR** so findings and fixes land in the PR. The handoff session then reads only what was flagged plus the security-critical paths. |

Always: `manage.py check`, `makemigrations --check`, full suite not worse
than the recorded baseline. Never run a manual full-diff read **and** an
automated review on the same PR — pick one. A completed human click-through
counts as evidence; lean lighter, not heavier, when it has been done.

### Cost control when fanning out subagents

Subagents themselves are not the expensive part — each starts with a fresh,
narrow context instead of the handoff session's accumulated one, which often
makes a focused subagent *cheaper* than doing the same read inline. What
costs is the combination: top-tier model × high effort × unbounded scope ×
several at once, running for tens of minutes. (2026-08-18: a single
`/code-review` at *high* launched from the handoff session ate roughly 20% of
the weekly budget in one afternoon.)

So set the knobs deliberately rather than avoiding the tool:

- **Model and effort explicit, not inherited.** Sonnet or Haiku at
  low/medium handles "check X in file Y" fine. Keep the session's top-tier
  model for the judgement calls you make yourself.
- **One narrow question per agent, naming the files.** "Audit this PR" is
  what turns into a ten-minute run; "does `_cache_get` fail open when Redis
  is down?" does not.
- **Bounded count and bounded scope** — a handful of targeted agents, not a
  dozen open-ended ones, unless the work genuinely is that wide.
- **Not stacked on top of a full manual read.** One layer, per the table.

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

Which bucket comes next, and why, is in
[round-october-2026.md](round-october-2026.md) — this table is only what is
live right now.

| Dir (`~/projects/ReDIB-Portal-wt/`) | Branch | Port | Since | Status |
|---|---|---|---|---|
| `eval-reminders/` | `feature/eval-reminders` | 8003 | 2026-08-20 | **Live.** One email per person, not one per item (#32, #5, #35; #49 gated on `acceptance-repair`). Merge by 2026-10-09, prod by 2026-10-13 — before evaluator assignments. Owns `evaluations/tasks.py`. Handoff: `docs/handoffs/eval-reminders.md` on the branch. |
| `marketing-site/` | `feature/marketing-site` | 8001 | 2026-08-17 | **Parked.** Wagtail rebuild of redib.net; ships next year, not for the October 2026 call. Handoff: `docs/handoffs/marketing-site.md` on the branch. |

## Marketing branch — why it is parked in a worktree

`feature/marketing-site` moves the portal from `/` to `/portal/`, adds
Wagtail apps/middleware, and rewrites `redib/urls.py`, `redib/settings.py`,
`templates/base.html` and most tests. Switching branches in the `main`
checkout for it was error-prone (shared `db.sqlite3` accumulated Wagtail
tables, venvs diverged). It now has its own directory and venv and will
stay there until its cutover conversation next year; `main` proceeds with
the October 2026 call work in the meantime. Full context:
[backlog — in-flight branches](backlog.md#in-flight-branches-not-on-main).
