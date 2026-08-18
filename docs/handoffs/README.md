# Branch handoff docs

One file per worktree branch, `<slug>.md`, created by
`scripts/new-worktree.sh` from `docs/developer/handoff-template.md` and
committed **on that branch**. It is the brief a fresh agent session reads
first when opened in the branch's worktree directory.

When a branch merges, its handoff doc lands here as a record — mark it
*Merged YYYY-MM-DD* at the top rather than deleting it.

Conventions, registry of active worktrees, and lifecycle:
[../developer/worktrees.md](../developer/worktrees.md).

Merged (kept as records):

- `public-calls.md` — `feature/public-calls`, merged 2026-08-18 (PR #33): announced calls on `/calls/` + public per-equipment consult requests.
- `help-guide.md` — `feature/help-guide`, merged 2026-08-17 (PR #32): user guide rendered live at `/help/user-guide/`.

Currently on branches (not yet on `main`):

- `marketing-site.md` — `feature/marketing-site`, parked 2026-08-17.
