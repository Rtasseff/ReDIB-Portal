# Handoff — `{{BRANCH}}`

<!-- Copy of docs/developer/handoff-template.md, seeded by scripts/new-worktree.sh.
     Lives at docs/handoffs/{{SLUG}}.md on the branch. Keep "Status" current. -->

| | |
|---|---|
| Branch | `{{BRANCH}}` |
| Worktree dir | `{{DIR}}` |
| Base | `{{BASE_REF}}` @ `{{BASE_SHA}}` |
| Created | {{DATE}} |
| Runserver port | {{PORT}} |
| Handoff session | `main` checkout at `~/projects/ReDIB-Portal/` |

Read this first, then `CLAUDE.md`, then `docs/README.md`. This directory is
a git worktree: it *is* this branch — do not `git checkout` another branch
here (see `docs/developer/worktrees.md`).

## Goal

<!-- One paragraph: what this branch delivers and why now. -->

## Scope

**In:**
-

**Out** (do not do here — belongs on `main` or another bucket):
-

## Acceptance

<!-- How we know it's done. Tests to pass, pages to render, commands to run. -->
-

## Context & decisions already made

<!-- Links into docs/, backlog item numbers, prior decisions the branch agent must not re-open. -->
-

## Conflict watchlist

<!-- Files also changing on main; rebase early if you touch them. -->
-

## Status

<!-- Branch agent keeps this current. Checklist + short dated notes. -->
- [ ]

## Questions for the handoff session

<!-- Anything needing the human or main. Don't guess — park it here and continue with what doesn't depend on it. -->
-

## Return protocol

1. Keep this doc's **Status** current; note anything you deviated from.
2. `python manage.py check`; `python manage.py makemigrations --check`;
   full suite `python manage.py test tests` — record the pass/fail counts
   against the baseline you took before starting (do not make it worse).
3. Push the branch and open a PR against `main`. PR body = the review
   packet: what changed and why, deviations from this brief, the test
   counts, anything user-facing (email wording, guide copy) quoted for
   review, and any pre-existing bug you noticed but did not fix.
4. The handoff session reviews proportionately to risk (see
   `docs/developer/worktrees.md` § Review policy), merges, and updates the
   registry.

## Running locally (this worktree)

```bash
cd {{DIR}}
source venv/bin/activate
python manage.py runserver {{PORT}}
```

`.env`, `db.sqlite3` and `media/` were copied from the `main` checkout at
creation time. To rebuild the sandbox: `python manage.py setup_localtest3_database`
(see `docs/DEVELOPMENT.md`).
