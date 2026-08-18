# Proposal — call status: one manual gate, one derived phase

> **Development document.** A proposal, not a decision to act on. Nothing here
> is implemented. On the production VPS this is background reading only.

| | |
|---|---|
| Backlog item | [40](backlog.md) (assessment); related: 27, 39, 41, GitHub #23 |
| Status | **Proposal — agreed in principle 2026-08-18, deliberately not scheduled** |
| Target window | after the Oct 2026 call closes (~2027-03) and before the next call (~2027-05) |
| Priority | Medium |

Written 2026-08-18 while the evidence was fresh, so that picking this up in
five months costs a read rather than a re-derivation.

## 1. The problem

`Call.status` has two independent owners and they are allowed to disagree.

- **Dates write it.** `check_call_deadlines` (`calls/tasks.py:12`) daily, plus
  two view-level fallbacks — `_auto_open_announced_calls` and
  `_auto_close_expired_calls` (`calls/views.py:39-64`) — which run on *every*
  public calls page hit, including anonymous ones.
- **Humans write it.** The `CallForm` dropdown, and the Announce / Publish /
  Close actions, each with its own ad-hoc guard.

The public querysets then filter on status **and** dates
(`calls/views.py:80-88`), so a call whose two owners disagree does not merely
look odd — it falls out of the site. Evidence from the 2026-08-18 prod
walkthrough (item 27):

- `open` with a future `submission_start`: in neither public list, still live
  at `/calls/<pk>/`, still taking consult requests, and it will never fire the
  "Now Open" email because that path only picks up `announced`.
- `announced` with a past `submission_end`: needed a special-case guard
  (`2ee0c7c`) to stop it auto-opening into a window that had already closed.
- Dates edited after announcement: nothing re-evaluates status at all
  (GitHub #23).

Each of these got its own patch. They are one bug.

## 2. The proposal

**One field a human sets. One value the dates compute. They cannot contradict
each other because they answer different questions** — "has a human published
this?" and "where are we in the timeline?"

### Manual: `status`, three values

| Value | Meaning | Set by |
|---|---|---|
| `draft` | Not public. `/calls/<pk>/` 404s. | Default on create |
| `active` | Published. From here the dates govern. | One coordinator action |
| `resolved` | Finished, results out. | Coordinator, manually — the model does not carry enough to automate this |

### Derived: `phase`, computed, meaningful only while `active`

| Phase | Condition | Public list | Detail page |
|---|---|---|---|
| `upcoming` | `now < submission_start` | "Upcoming Calls" | Visible, **no Apply**, consult form live |
| `open` | `submission_start <= now <= submission_end` | "Open Calls" | Visible, Apply live, consult form live |
| `closed` | `now > submission_end` | Not listed | Reachable at its URL, no Apply, **consult form off** |

Two rules above are recommendations rather than restatements of the sketch, and
should be confirmed when this is picked up: closed calls stay reachable but
unlisted (which is what happens today), and the consult form closes with the
submission window — there is nothing left to consult about.

### Two naming changes to the original sketch

1. **`upcoming`, not `pending`.** `pending` is already the waitlist
   **Application** status; reusing it would make the word mean two different
   things in two models, in templates and in conversation. `upcoming` is also
   what the public page already calls that section.
2. **`open`, not `opened`.** Matches the existing vocabulary in code, docs and
   the cheat-sheet in `CLAUDE.md`.

The manual field keeps the name `status` — renaming it costs a migration and
every call site for no behavioural gain. `phase` is the new name.

## 3. Derive it as a property, not a stored field

This is the part that actually removes the bug class, and it is worth being
explicit about because "add a `phase` column the beat task maintains" looks
equivalent and is not.

- **A stored field needs a writer, and a writer can be late.** That is today's
  bug with a new name.
- **A property cannot be stale.** The public querysets become
  `status='active'` plus a date range — which is what they already half-do.
- **Nothing needs indexing.** The call table has single-digit rows.
- **Cost:** you cannot `filter(phase=...)`. Every caller has the dates to hand,
  but add queryset helpers — `Call.objects.upcoming() / .open_now() /
  .closed()` — so the date arithmetic is written once rather than in each view.

### State is derived; events are recorded

The one thing a property cannot do is happen once. So keep timestamps for
things that occurred, separate from state that is computed:

- `activated_at` — when a human moved it out of draft.
- `open_email_sent_at` — only if the "Now Open" send ever returns (item 41);
  it is also the natural idempotency guard for that send.

Both are jobs `published_at` currently does at the same time, which is why
`templates/calls/detail.html:107-109` has to paper over which date it is
showing.

## 4. What disappears

- The `status` dropdown on `CallForm` — **already gone**, item 27, PR #34.
- Stored `announced` / `open` / `closed` → a data migration maps all three to
  `active`. Cheap: `announced` only exists as of `5e11104` (2026-08-17) and no
  real call has ever held it.
- `check_call_deadlines`'s writes and **both** view-level fallbacks. With phase
  derived there is nothing to promote — a page load computes the right answer.
  The beat task survives only if it has an email to send.
- The `2ee0c7c` guard ("never auto-open an expired call") — unreachable by
  construction.
- `PUBLIC_STATUSES` collapses to `status != 'draft'`.

## 5. What stays manual

- `draft → active`, one coordinator action, keeping the existing validation
  (must have equipment allocations).
- `→ resolved`.
- The **announce email**: an optional button, with the recipient count shown
  before the coordinator commits. Dark until item 41 is done.

### One disagreement, recorded

The sketch keeps the "Now Open" email firing automatically on the open
transition. **I would not bring that back as an automatic send.** It is the
same ~1200-message burst as the announce, with no human in the loop, and today
it can be triggered by an anonymous GET of `/calls/`. If the announce burst is
worth a confirmation screen, the open burst is worth at least the same.

Suggestion for when item 41 comes back: both sends are coordinator-pressed
buttons, and the beat task's job is to *tell the coordinator a call opened
today*, not to mail the audience on its own. That also removes the last silent
write in the app. If it stays automatic instead, it must at minimum move to
beat-only — never a web request — and be guarded by `open_email_sent_at`.

## 6. Cost, and when

Touches: a migration and a data migration, `calls/views.py` (querysets + both
fallbacks), `calls/tasks.py`, `calls/services.py`, `CallForm`,
`templates/includes/status_badge.html`, `templates/calls/detail.html`,
`templates/calls/public_list.html`, the admin, and every test asserting a
status transition. Public-facing, so it earns **one `/code-review` at medium**.

A bucket, not an inline fix. **Not this round** — it is a rework with no
failing user in front of it, and the October call can be run on the current
code now that the dropdown is gone. The window is after this call closes
(~2027-03) and before the next one (~2027-05), the same window as item 41 —
and 41 should be built **on top of** this, not before it.

## 7. What it fixes

- **40** by construction — the two owners stop overlapping.
- **27** permanently: there is no hand-settable state left to contradict.
- **GitHub #23**: editing dates simply changes the answer.
- **39** shrinks from an investigation to a two-row table.
