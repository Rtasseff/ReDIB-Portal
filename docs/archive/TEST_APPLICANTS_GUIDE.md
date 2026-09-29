# Test Applicants & Applications Guide

> **Archived 2026-09-29.** `seed_test_applicants`, `seed_dev_data` and
> `setup_test_database` were removed (backlog #88(b), #90). Use
> `setup_localtest3_database`. Kept as history; links below may be stale.

What `python manage.py seed_test_applicants` creates, and how to use it.

> **Most manual testing should use the localtest3 sandbox instead**
> (`python manage.py setup_localtest3_database --reset --yes`; see
> [TESTING.md](TESTING.md#the-localtest3-sandbox)). Its accounts log straight
> in and its applications carry the deadlines and flags each workflow step
> needs. Use `seed_test_applicants` when you want a spread of applications
> on top of the **real** reference data from `data/*.tsv`.

## Getting the data

```bash
python manage.py setup_test_database --reset --yes
```

This loads the real reference data, runs `seed_dev_data` (a dev call pair and
a few `@test.redib.net` accounts) and then `seed_test_applicants`. `--reset`
first deletes all data except superuser accounts.

> `seed_dev_data` currently crashes part-way, at "Creating evaluations and
> grants". `setup_test_database` reports that step as "may already exist" and
> carries on, so the run still finishes with the calls and test applicants in
> place. See the [command reference](DEVELOPMENT.md#management-command-reference).

To add or re-create only the test applicants on a database that already has a
call, nodes, equipment and organizations:

```bash
python manage.py seed_test_applicants            # adds them (fails on duplicate codes if they exist)
python manage.py seed_test_applicants --clear    # deletes the testapplicant* users and their applications first
```

`--clear` touches only users whose email contains `testapplicant`, and their
applications.

## The seven test applicants

Password for all of them: **`testpass123`**.

| Email | Name | Applications |
|-------|------|--------------|
| testapplicant1@university.es | María García | 001, 008, 015 |
| testapplicant2@research.de | Thomas Schmidt | 002, 009, 016 |
| testapplicant3@hospital.fr | Claire Dubois | 003, 010, 017 |
| testapplicant4@biotech.com | John Williams | 004, 011 |
| testapplicant5@institute.it | Lucia Rossi | 005, 012 |
| testapplicant6@university.uk | David Brown | 006, 013 |
| testapplicant7@lab.ch | Anna Mueller | 007, 014 |

Each is given an organization by cycling through the database's organization
list, so the affiliation is arbitrary.

**Logging in takes two extra steps.** These accounts are not email-verified
and have no phone number:

1. The first login stops at "confirm your email". The confirmation link prints
   in the `runserver` terminal; open it.
2. After logging in, the portal sends you to `/profile/` until you add a phone
   number (`ProfileCompletionMiddleware`).

## The 17 applications

All are in the first **open** call (`COA-TEST-02` after `setup_test_database`),
coded `TEST-APP-001` to `TEST-APP-017`.

| Code | Status | Score | Notes |
|------|--------|-------|-------|
| 001 | draft | | Competitive funding; instruments at 2 nodes |
| 002 | submitted | | No feasibility review rows, so it is in no node coordinator's queue |
| 003 | under_feasibility_review | | One pending review |
| 004 | pending_evaluation | | Ready for evaluator assignment |
| 005 | under_evaluation | | 1 evaluator assigned, not scored; competitive funding |
| 006 | evaluated | 9.5 | 2 nodes, no node resolutions yet |
| 007 | accepted | 10.5 | |
| 008 | pending (waitlist) | 8.5 | 2 nodes: one accepted, one waitlisted |
| 009 | rejected | 4.0 | 2 nodes: one accepted, one rejected. Competitive funding, but both evaluations recommend *denied*, which is what allows the rejection |
| 010 | accepted | 11.0 | |
| 011 | declined_by_applicant | 9.0 | 2 nodes |
| 012 | rejected_feasibility | | |
| 013 | accepted | 10.0 | Competitive funding |
| 014 | under_evaluation | | 2 evaluators assigned, neither scored |
| 015 | accepted | 8.0 | |
| 016 | accepted | 11.5 | 2 nodes |
| 017 | evaluated | 9.0 | Competitive funding, no node resolutions yet: the node coordinator cannot reject it |

How the spread is generated:
- **Competitive funding** is set on every 4th application (001, 005, 009,
  013, 017).
- **Two nodes**: every 5th application (001, 006, 011, 016) plus the
  waitlist and reject cases (008, 009). The rest request one instrument.
- **Specialization area** rotates preclinical, clinical, radiochemistry.
- **Hours requested** rotate 16, 24, 32 per instrument.
- Unscored evaluations stay incomplete. When an evaluator submits the form,
  the application moves to `evaluated` once all assigned evaluations are in.

**Limits of this data.** The `accepted` and `pending` applications have no
`acceptance_deadline` and no applicant answer recorded, so they are not good
for testing the 10-day accept/decline window, reminders or promotion. Use
localtest3's `LIVE-009` and `LIVE-010` for that. Node resolution on 006 and
017 is also held by the release gate: the call has to be closed and the ReDIB
coordinator has to click **Release to Nodes** on the call's page first.

## Who to log in as

| To test | Log in as | Password |
|---|---|---|
| Applicant views | a `testapplicant*` account above | `testpass123` |
| ReDIB coordinator | `coordinator@test.redib.net` (from `seed_dev_data`; needs the email confirmation step) or `coordinator@redib.net` (from `data/users.tsv`, pre-verified) | `testpass123` / `changeme123` |
| Node coordinator, real nodes (CIC-biomaGUNE, BioImaC, IIS-LaFe, TRIMA@CNIC) | the `node_coordinator` rows in `data/users.tsv` (pre-verified) | `changeme123` |
| Node coordinator, dev nodes (CICBIO, CNIC) | `cic@test.redib.net`, `cnic@test.redib.net` (need the email confirmation step) | `testpass123` |
| Evaluator | the `evaluator` rows in `data/users.tsv`. The seeded evaluations go to the first two evaluators by email address. | `changeme123` |

`setup_test_database` prints a sample of these accounts when it finishes.
Everything runs against your local database with the console email backend,
so nothing reaches the real people named in `data/users.tsv`.

## Checking what was created

```bash
python manage.py shell -c "
from applications.models import Application
from django.db.models import Count
for row in Application.objects.filter(code__startswith='TEST-APP').values('status').annotate(n=Count('id')).order_by('status'):
    print(row['status'], row['n'])
"
```
