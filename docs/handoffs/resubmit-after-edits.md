# Handoff — `feature/resubmit-after-edits`

<!-- Copy of docs/developer/handoff-template.md, seeded by scripts/new-worktree.sh.
     Lives at docs/handoffs/resubmit-after-edits.md on the branch. Keep "Status" current. -->

| | |
|---|---|
| Branch | `feature/resubmit-after-edits` |
| Worktree dir | `/home/rtasseff/projects/ReDIB-Portal-wt/resubmit-after-edits` |
| Base | `main` @ `ffbaccf` |
| Created | 2026-09-30 |
| Runserver port | 8002 |
| Handoff session | `main` checkout at `~/projects/ReDIB-Portal/` |

Read this first, then `CLAUDE.md`, then `docs/README.md`. This directory is
a git worktree: it *is* this branch — do not `git checkout` another branch
here (see `docs/developer/worktrees.md`).

**Development document.** These are instructions for the agent session working
in this worktree. Once the branch merges, this file lands on `main` as a
record — on the production VPS it is history, not a task list.

## Goal

**Let an application that a node sent back for edits be resubmitted after the call's submission
deadline.** That's all. REDIB-2602 accepts submissions from 2026-10-01 to **2026-10-31**, and
feasibility review runs into November. Today, when a node picks **Request Edits** after the
deadline:
- the application goes back to `draft`
- the applicant can still edit it
- `application_submit` refuses the resubmission with "Submission deadline has passed."

It then sits in draft for good. The handoff session reproduced this on a scratch record on
2026-09-30. It happened once last call (REDIB-2601-020), and Ryan pushed it through by hand.
The ReDIB directors want these applicants to be able to resubmit.

**Ryan's condition: this must not add much.** No new status, no new field, no migration. It is
one helper, one changed condition and two template conditions, plus tests and a few doc lines.
If it starts to need more, stop and ask.

## Scope

**In:**

1. **A helper.** For example `Application.was_sent_back_for_edits`: true when the draft has at
   least one `FeasibilityReview` row. Only a real submission creates those rows, and a Request
   Edits keeps them. `calls.views.call_detail` already uses this signal to keep sent-back
   drafts on the status wall. Confirm it's reliable.
2. **`application_submit`** (`applications/views.py`, the deadline check around line 745).
   Refuse after `submission_end` **unless** the draft was sent back for edits and the call
   isn't `resolved`. **Leave a first submission's rule exactly as it is today** (deadline date
   only), so the call that opens on 10-01 behaves exactly as it does now for every new
   applicant. Everything after the guard is unchanged. The resubmission path already reuses
   the code, resets every feasibility review to pending and emails the nodes.
3. **Two template conditions**, so the applicant isn't told something false:
   - `templates/applications/my_applications.html` (around line 41): a sent-back draft gets
     **Continue**, not the disabled **Call closed** badge.
   - `templates/applications/_call_closed_banner.html`: for a sent-back draft, don't say "can
     no longer be submitted". Either no banner, or one line: "The call has closed, but a node
     asked for edits, so you can still resubmit."
4. **Tests.**
   - A sent-back draft resubmitted after the deadline goes to `under_feasibility_review`, with
     its reviews reset. Mirror the existing resubmission test.
   - The same once the call is `resolved` is refused.
   - A never-submitted draft after the deadline is still refused.
   - The badge and banner for a sent-back draft vs a never-submitted draft on a closed call.
   - The suite is at **547** on `main`; keep it green.
5. **Docs.**
   - `docs/USER_GUIDE.md`: one or two sentences each in the applicant's *If the call closes
     while you are drafting* and the node coordinator's *Feasibility review*. A node may
     Request Edits after the deadline, and the applicant can still resubmit. Keep
     `tests/test_help_guide.py` green.
   - `docs/ARCHITECTURE.md` §3.2: a note on the draft → submitted row.

**Out** (Ryan, 2026-09-30: keep it minimal):
- Checking the call's status on a first submission (ultrareview finding 4).
- The "closed" wording when an open call's start is in the future (finding 1). Both are
  filed in the backlog.
- The dedicated `edits_requested` status and a resubmission deadline (#12).
- The consult messages (#94).
- Anything else.

## Acceptance

- Full suite green, with the new tests. `check` and `makemigrations --check` clean.
- Click-through on `localtest3` (`runserver 8002`):
  - submit a draft
  - a node coordinator picks **Request Edits**
  - move the call's end date into the past (the shell is fine)
  - the applicant sees **Continue**, edits, and resubmits, and it's back in the node's
    Feasibility Reviews
  - a never-submitted draft on that call still can't submit

  Two lines in Status.
- One `/code-review` at **medium** before the PR. It is the submit path of a live call. Then
  open the PR (the review packet), quoting the new user-facing wording.

## Timing: deploy as soon as it's done, today if possible

- **Target: PR today (2026-09-30).** The handoff session reviews and merges it, and prod
  deploys it **before REDIB-2602 opens on 10-01**, while no applicant exists yet. Because a
  first submission's rule doesn't change, the deploy carries no risk for the call's new
  applicants.
- If it slips past today, it can still deploy on a quiet day in October. The first-submission
  path is unchanged, and the fix is only needed from 11-01. Not in the call's last days
  (10-28 → 10-31).

## Context & decisions already made

- Found 2026-09-30 while triaging the `/code-review ultra` findings on PR #47. The triage
  comment on that PR has the details.
- Ryan's condition: minimal. The directors want sent-back applicants able to resubmit.
- Never read `.env` (not with cat, grep, ls or Read); it holds secrets.

## Conflict watchlist

- Nothing else is in flight. `main` only gets doc commits from the handoff session.

## Status

- [ ] helper · [ ] submit guard · [ ] badge + banner · [ ] tests · [ ] docs · [ ] click-through · [ ] /code-review · [ ] PR

## Questions for the handoff session

-

## Return protocol

1. Keep this doc's **Status** current; note anything you deviated from.
2. `python manage.py check`; `python manage.py makemigrations --check`;
   full suite `python manage.py test tests reports` — record the pass/fail counts
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
cd /home/rtasseff/projects/ReDIB-Portal-wt/resubmit-after-edits
source venv/bin/activate
python manage.py runserver 8002
```

`.env`, `db.sqlite3` and `media/` were copied from the `main` checkout at
creation time. To rebuild the sandbox: `python manage.py setup_localtest3_database`
(see `docs/DEVELOPMENT.md`).
