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

**Let an application that a node sends back for edits be resubmitted after the call's
submission deadline.** REDIB-2602 accepts submissions from 2026-10-01 to **2026-10-31**, and
feasibility review runs into November. Today, when a node picks **Request Edits** after 10-31:
- the application goes back to `draft`
- the applicant can still edit it (**Edit Application** on the detail page)
- `application_submit` refuses the resubmission with "Submission deadline has passed."

The application then sits in draft for good, which is a rejection nobody decided. The handoff
session reproduced this on a scratch record on 2026-09-30. It already happened in the last
call: REDIB-2601-020 came back 20 days after `submission_end` (backlog #12). The only way
through today is for someone to extend the closed call's end date. That works only because
`application_submit` never checks the call's status (ultrareview finding 4, PR #47), and it
would let every other unsubmitted draft through too.

Keep it small. This runs **during the live call**, on the submission path, the most important
code in the portal. The branch is **held, not merged**, until submissions have closed (see
Timing).

## Scope

**In:**

1. **`application_submit`** (`applications/views.py`):
   - A **sent-back draft** may be resubmitted after `submission_end`, as long as the call is
     `open` or `closed` (not `resolved`). A sent-back draft is one that has at least one
     `FeasibilityReview` row, since only a real submission creates them and a Request Edits
     keeps them. `calls.views.call_detail` already uses this signal to keep sent-back drafts
     on the status wall. Confirm it's reliable, and put the test in one small helper (an
     `Application` property or a function) so the views and templates share it.
   - A **first submission** needs `call.is_open` (status `open` *and* inside the window). So a
     call a coordinator closed early no longer accepts new submissions (finding 4). Refuse
     with a message that says which case applies: "This call closed on …" or "This call is
     not accepting submissions". Keep the check ahead of the completeness checks, as #67 put it.
   - Everything after the guard is unchanged. In particular the resubmission path (code
     reused, every feasibility review reset to pending, the emails) stays exactly as it is.
2. **The wording the applicant sees** must be right in all three cases:
   - a sent-back draft on a closed call: they can resubmit
   - the deadline has passed: "closed on …"
   - the call is not accepting submissions for another reason (closed early, or `open` with
     a start in the future, which is finding 1)

   That is:
   - `templates/applications/my_applications.html`: the **Call closed** badge vs **Continue**.
     A sent-back draft gets **Continue**.
   - `templates/applications/_call_closed_banner.html`, used on every wizard step: for a
     sent-back draft, either no banner or one saying "A node asked for edits; you can
     resubmit after the call's deadline".
   - The preview page's submit button, if it gates on the call.
3. **Tests.** The suite is at **547** on `main`. Add tests for:
   - sent-back draft resubmitted after the deadline → `under_feasibility_review` and the
     reviews reset (mirror the existing resubmission test)
   - the same once the call is `resolved` → refused
   - first submission after the deadline → refused
   - first submission on a call closed early (end date in the future) → refused (finding 4)
   - the My Applications badge and the banner, for each case
   - the existing behaviour inside the window, unchanged
4. **Docs.**
   - `docs/USER_GUIDE.md`: the applicant sections *If the call closes while you are drafting*
     and *What happens after you submit*, and the node coordinator's *Feasibility review*.
     A node may Request Edits after the deadline, and the applicant can still resubmit.
     Keep `tests/test_help_guide.py` green.
   - `docs/ARCHITECTURE.md` §3.2: the draft → submitted row.
   - `docs/developer/backlog.md`: nothing. The handoff session updates #12 at merge.

**Out:**
- The dedicated `edits_requested` status and a per-application resubmission deadline
  (backlog #12). They are structural and deferred.
- The consult messages (#94).
- The duplicated promote-form code and the copied hidden form (ultrareview findings 2 and 3).
  They are style only.
- Anything else.

## Acceptance

- The full suite (`python manage.py test tests reports`) is green, with the new tests.
  `check` and `makemigrations --check` are clean. **No migration**: if the helper seems to
  need a field, stop and ask.
- Click-through on `localtest3` (`runserver 8002`):
  - submit a draft
  - a node coordinator picks **Request Edits**
  - move the call's end date into the past (the edit form or the shell)
  - the applicant sees **Continue**, edits, and resubmits
  - the node sees it back in Feasibility Reviews
  - a never-submitted draft on the same call still can't submit

  Record the steps and results in Status.
- One `/code-review` at **medium** before the PR. It changes the submit guard on a live call.
- PR body: the review packet (see the return protocol), with the exact new user-facing
  wording quoted.

## Timing: held until submissions close

- PR ready by **2026-10-16**.
- **The handoff session merges it on 2026-11-02 (Monday)** and prod deploys that day. That is
  the first working day after REDIB-2602's submissions close (10-31, 23:59). Merging to
  `main` is deploying, and the posture during the window is "only what is actively broken".
  This fix only matters from 11-01, so it must not reach prod while submissions are open.
- A node that sends an application back on 11-01, before the deploy, loses nothing. The
  applicant can resubmit once it's out.
- If `main` moves in October (an emergency fix), rebase before the PR is merged.

## Context & decisions already made

- Found 2026-09-30 while triaging the `/code-review ultra` findings on PR #47. The triage
  comment on that PR has the reasoning. Ryan asked for changes to go through a worktree.
- Why not "just check `call.status`" (finding 4 alone): with no other change, it would close
  the only workaround for sent-back drafts. Both halves ship together.
- Never read `.env` (not with cat, grep, ls or Read); it holds secrets.

## Conflict watchlist

- Nothing else is in flight. `main` is frozen for the call except emergency fixes.

## Status

- [ ] helper · [ ] submit guard · [ ] badge/banner wording · [ ] tests · [ ] docs · [ ] click-through · [ ] /code-review · [ ] PR (do not merge)

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
