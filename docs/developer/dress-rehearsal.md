# Dress rehearsal — walk a whole call before the real one

> **Development document.** This runs on a local dev checkout against
> `db.sqlite3`. It is not for the production VPS and `scripts/rehearsal.py`
> refuses to run there.

The October 2026 call is the first time this portal drives a COA round from
end to end. Every phase has tests and most have been exercised in isolation,
but **no human has walked the whole sequence in one sitting**, and the things
that survive a green test suite are exactly the things a rehearsal catches:
wording that reads wrong, a button nobody would look for, an email that is
technically correct and lands badly, a screen that is empty when it should
explain why it is empty.

Budget **about 90 minutes for Part A**, which covers everything between now and
the first submitted application. Part B is the rest of the cycle and can wait
until December — it is written down so it exists, not because it is due.

## Before you start

```bash
cd ~/projects/ReDIB-Portal
source venv/bin/activate
python manage.py migrate            # the local db may be behind
python scripts/rehearsal.py seed    # wipes the sandbox, creates one draft call
python manage.py runserver
```

Then open <http://127.0.0.1:8000/>.

**Nothing you do here can reach a real person.** Three independent reasons:
`EMAIL_BACKEND` defaults to the console, so mail is printed and never sent;
`CELERY_TASK_ALWAYS_EAGER` is on whenever `DEBUG=True`, so no queue is
involved; and `scripts/rehearsal.py` exits unless `DEBUG` is on *and* the
database is SQLite. Break whatever you like — `seed` puts it all back.

### The harness

| Command | What it does |
|---|---|
| `python scripts/rehearsal.py seed` | Reset the sandbox; create `REHEARSAL-2701` as a **draft** with no applications |
| `python scripts/rehearsal.py status` | Where the call is, what its dates are, how many applications, how many emails |
| `python scripts/rehearsal.py advance 15` | Simulate 15 days passing (moves the call's dates back) |
| `python scripts/rehearsal.py beat` | Run all ten scheduled tasks once and report what each one did |
| `python scripts/rehearsal.py inbox` | Every email the sandbox logged; `--full` includes bodies |

`beat` is the one to reach for whenever you are wondering *"what would the
portal email today?"* — it answers that without waiting for tomorrow.

One caveat on `advance`: it moves the **call's** dates, not the applications'.
Reminders anchored to an application's own timestamps — the acceptance ladder,
the stalled-acceptance nag, the 6-month publication follow-up — will not come
due just because the call moved. Stage 10 sets those directly.

### Accounts

All passwords are `testpass123`, all addresses pre-verified so allauth lets you
straight in.

| Email | Role |
|---|---|
| `coordinator@test.redib.net` | ReDIB coordinator — this is you |
| `nc.cicbio@test.redib.net` | Node coordinator, CICBIO |
| `nc.cnic@test.redib.net` | Node coordinator, CNIC |
| `eval.preclinical@test.redib.net` | Evaluator, preclinical |
| `eval.clinical@test.redib.net` | Evaluator, clinical |
| `eval.radio@test.redib.net` | Evaluator, radiochemistry + clinical |
| `applicant1@…` … `applicant4@…` | Applicants (`applicant4` has a deliberately incomplete profile) |

Use **two browsers** (or one plus a private window) so you can hold the
coordinator session and an applicant session at once. Switching accounts
repeatedly in one browser is where rehearsals go to die.

---

# Part A — the next six weeks

## Stage 1 — Announce the call

The real one happens ~2026-09-15 and is the first thing anyone outside ReDIB
sees.

**Do.** As `coordinator@test.redib.net`, go to `/calls/manage/`. Find
`REHEARSAL-2701` (draft). Open it, read the detail page as if you were seeing
it for the first time, then **Announce** it.

**Expect.** It moves to `announced`. `/calls/` now shows it under *Upcoming
Calls* — visit that page **logged out**, in a private window, because that is
how every applicant will first see it.

**Also try.** Press **Publish** instead of Announce. It should be *refused*,
because `submission_start` is still in the future — that refusal is deliberate
(#27) and the message it gives you should explain the difference between
announcing and publishing without you having to know the codebase.

**Red flags.** The call appears on `/calls/` while still a draft. The
announce/publish distinction is not explained anywhere a coordinator would look.
Dates render in the wrong timezone. Any 500.

## Stage 2 — A consult request from the public

Announced calls accept `ConsultRequest`s, and this is the only pre-open path a
member of the public can use.

**Do.** Still logged out, open the call from `/calls/`, and submit a consult
request against a specific instrument. Then:

```bash
python scripts/rehearsal.py inbox --full
```

**Expect.** The node coordinator for that instrument's node is notified, and
the body reads like something a stranger would understand. Check who is on the
To line and who is CC'd.

**Red flags.** Nobody is emailed. The email goes to a person who cannot act on
it. The public form leaks anything about other applicants. The confirmation
page leaves the visitor unsure whether it worked.

## Stage 3 — The call opens on its own

The real transition happens unattended at ~2026-10-15, which is the part worth
rehearsing: nobody will be watching.

```bash
python scripts/rehearsal.py advance 15
python scripts/rehearsal.py beat
python scripts/rehearsal.py status
```

**Expect.** `status=OPEN`. The `call deadlines` line in the `beat` output is
what promoted it. **Zero emails** — announcement mail is deliberately off
(`CALL_ANNOUNCEMENT_EMAILS_ENABLED=False`); you and the node coordinators
announce by hand.

**Also try.** Re-run `beat`. It must not do anything a second time.

**Red flags.** The call is still `announced` after the beat run. Any email at
all. `/calls/` still files it under *Upcoming*.

## Stage 4 — A real application, from a standing start

This is the longest stage and the most valuable. **Register a brand-new
account** rather than using `applicant1` — a first-timer hits the profile
gate, the email verification step and an empty dashboard, and those are exactly
what a real PI meets on day one.

**Do.** In your second browser: register, complete the profile, find the call,
start an application. Then, deliberately:

1. Fill in **part** of it, save, and close the tab.
2. Come back, find the draft, and continue. *Can you actually find it again?*
3. Finish it, preview it, download the PDF.
4. Submit.

**Expect.** The wizard holds everything across the break. The preview matches
what you typed. The PDF renders. On submit, the application leaves `draft` and
the node coordinator(s) for the requested equipment are notified.

**Red flags.** Any step that loses work. A required field that isn't marked
required. A validation message that doesn't say which field. The PDF missing a
section you filled in. Submitting silently doing nothing.

> Note for this stage: watch for **#48**. If a node has no active coordinator,
> the submit path builds no feasibility review for it and says nothing — the
> application advances with a hole in it. Every node has a coordinator today,
> so you will not hit it in the sandbox unless you deactivate one on purpose.
> Worth doing once, in Django admin, to see the failure with your own eyes.

## Stage 5 — The draft nudge

Fires at T-7 and T-2 before `submission_end` for anyone still holding a draft.

**Do.** Start a *second* application and leave it as a draft. Then:

```bash
python scripts/rehearsal.py advance 38   # ~T-7
python scripts/rehearsal.py beat
python scripts/rehearsal.py inbox --full
```

**Expect.** Exactly one nudge, to the holder of the draft, naming the days
remaining. The submitted application is not nudged.

**Also try.** Run `beat` again immediately. **No second email** — the dedupe is
the whole point.

**Red flags.** The submitted application gets nudged. Two emails for one draft.
A blank deadline or a dead link in the body.

## Stage 6 — The call closes on its own

```bash
python scripts/rehearsal.py advance 10
python scripts/rehearsal.py beat
python scripts/rehearsal.py status
```

**Expect.** `status=CLOSED`. The remaining draft can no longer be submitted,
and the applicant is told *why* rather than getting a 403 or a dead button.

**Red flags.** A draft can still be submitted after close. The applicant-facing
explanation is missing. Nudges still firing for a closed call.

---

**That is Part A.** If those six stages are clean, the announce-to-close window
is rehearsed. Everything after this happens in December or later.

---

# Part B — the rest of the cycle

Worth doing before December, not before September. Same sandbox, same accounts.

## Stage 7 — Feasibility review

As `nc.cicbio@test.redib.net`, work `/applications/feasibility/`. Approve one,
request edits on another. Watch what the applicant sees in each case — note
that "edits requested" currently pushes the application back to a shared status
rather than its own (#12), so check the applicant can tell what is being asked.

## Stage 8 — Evaluation

As coordinator, auto-assign evaluators for the call, then log in as each
evaluator and submit scores. Two things to watch: whether COI exclusion keeps
an evaluator off their own organization's application, and — given **#63**,
where effective clinical coverage is 4 people — whether the assignment falls
back to a *non*-area-matched evaluator without saying so.

## Stage 9 — The release gate

The newest and least-exercised machinery. Before releasing:

- a node coordinator's resolution queue should be **empty**;
- opening a resolution URL directly should refuse **with an explanation**, not
  a 404;
- the call should not appear on the coordinator's resolution dashboard.

Then press **Release resolutions** and confirm the batch goes out once, and only
once, to the right node coordinators.

## Stage 10 — Resolution and acceptance

Resolve applications accept / waitlist / reject. Two rules to prove:

- an application with `has_competitive_funding=True` **cannot be rejected** at
  resolution unless an evaluator recorded a denial;
- a waitlisted application's hand-off email fires only when a node coordinator
  clicks *Mark as Accepted*.

Then, as an applicant, accept one offer and let another sit. To exercise the
stalled-acceptance nag you must set `acceptance_deadline` into the past
directly — `advance` will not do it:

```bash
python manage.py shell -c "
from applications.models import Application
from django.utils import timezone
from datetime import timedelta
a = Application.objects.filter(status='accepted').first()
a.acceptance_deadline = timezone.now() - timedelta(days=11); a.save()
print(a.code, 'deadline moved into the past')"
python scripts/rehearsal.py beat
python scripts/rehearsal.py inbox --full
```

The nag must go to the **node coordinator** with you CC'd, must carry a
reminder counter, and must **never** silently expire the application — only a
human writes that transition.

## Stage 11 — The resolution table

`/reports/` → *Resolution Tables* → the call. Both language tables render, the
warnings sit above them and not inside, and the CSVs download. This is the
artefact ReDIB publishes, so read the Spanish as Spanish — the column headers
are a proposal, not published wording, and this is the moment to correct them.

---

# What to do with what you find

Write each finding into [backlog.md](backlog.md) with what you clicked, what
happened, and what you expected — that is enough for a dev session to act on.

Then sort them honestly:

- **Blocks the call** → fix before ~2026-10-15.
- **Embarrassing but survivable** → fix if a window opens; the last round ran
  on scattered email and people were fine with it.
- **Noticed, not urgent** → backlog, and let it wait.

The bar for this round is not perfection. It is that nothing silently does the
wrong thing to an applicant, and that you always know what the system just
sent.
