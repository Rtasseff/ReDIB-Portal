# Branch handoff docs

One file per worktree branch, `<slug>.md`, created by
`scripts/new-worktree.sh` from `docs/developer/handoff-template.md` and
committed **on that branch**. It is the brief a fresh agent session reads
first when opened in the branch's worktree directory.

When a branch merges, its handoff doc lands here as a record — mark it
*Merged YYYY-MM-DD* at the top rather than deleting it.

Conventions, registry of active worktrees, and lifecycle:
[../developer/worktrees.md](../developer/worktrees.md).

Currently on branches (not yet on `main`):

- `marketing-site.md` — `feature/marketing-site`, parked 2026-08-17.
- `help-guide.md` — `feature/help-guide`, active since 2026-08-17 (user guide as a live portal page).
- `public-calls.md` — `feature/public-calls`, active since 2026-08-17 (announced calls + public equipment consult).
