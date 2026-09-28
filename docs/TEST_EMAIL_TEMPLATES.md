# Test Email Templates Guide

How to check workflow emails with the `send_test_emails` management command.

## Overview

`send_test_emails` creates a small set of throwaway objects, sends **15 of the
31** seeded email templates to one recipient, and can clean the objects up
afterwards. Use it to check rendering, links and styling in a real mail
client.

It sends real mail when the SMTP backend is configured (production). In dev,
with the console backend from `.env.example`, all 15 print to the terminal.

For the other 16 templates (reminders, digests, consult requests, the call
announcement, waitlist notices and so on), the dress rehearsal is the better
tool. `python scripts/rehearsal.py beat` runs every scheduled job and
`python scripts/rehearsal.py inbox --full` shows what each one sent; see
[developer/dress-rehearsal.md](developer/dress-rehearsal.md).

## Prerequisites

- Email templates seeded: `python manage.py seed_email_templates`. Every
  `setup_*_database` command and the Docker entrypoint do this already.
- At least one node. The command uses `CICBIO` if it exists, otherwise the
  first node.
- The recipient must be an existing user. The command stops with
  "User with email … not found." otherwise.

## Running It

```bash
# Local development (prints to the terminal)
python manage.py send_test_emails --to coordinator@test.redib.net

# Production (sends real mail)
docker compose -f docker-compose.prod.yml exec web python manage.py send_test_emails --to your-email@example.com
```

If `--to` is omitted, the recipient is `rtasseff@cicbiomagune.es`.

When you are done, remove the test objects:

```bash
python manage.py send_test_emails --cleanup
# Production:
docker compose -f docker-compose.prod.yml exec web python manage.py send_test_emails --cleanup
```

## What It Creates

Everything hangs off a dedicated call, **COA-EMAIL-TEST**:

| Object | Details |
|--------|---------|
| Call | `COA-EMAIL-TEST` (status `closed`, evaluation deadline 5 days ago) |
| Application | `COA-EMAIL-TEST-001`, owned by the recipient (status `accepted`, acceptance deadline 8 days ahead) |
| FeasibilityReview | For the chosen node, pending, with the recipient as reviewer |
| Evaluation | On that application, assigned to the recipient |
| UserRole | An `evaluator` role (area `preclinical`) for the recipient, if they don't already have one |
| EmailLog | One row per email sent |

`--cleanup` deletes the evaluation, the feasibility review, the application and
the call. **It does not remove the evaluator role.** On production, remove
that role by hand in the admin afterwards, or the recipient stays in the
evaluator pool for assignment.

Running the command twice reuses the existing call and application.

## Templates Sent

Subjects as rendered on 2026-09-28:

| # | Template | Subject | Link in body |
|---|----------|---------|--------------|
| 1 | feasibility_request | ReDIB COA: New Application for Equipment at [node] | Feasibility review |
| 2 | application_received | ReDIB COA: Application [code] Received | |
| 3 | feasibility_complete | ReDIB COA: Feasibility Review Complete for [code] | |
| 4 | evaluation_assigned | ReDIB COA: Evaluation Assignment for [code] | Evaluation |
| 5 | evaluation_reminder | ReDIB COA: Evaluation Reminder ([n] Pending) | **Renders broken, see below** |
| 6 | evaluation_overdue | ReDIB COA: [n] Evaluation(s) Overdue | **Renders broken, see below** |
| 7 | coordinator_overdue_evaluations | ReDIB COA: Overdue Evaluations for Call [call] | |
| 8 | coordinator_evaluations_locked | ReDIB COA: Evaluators Locked Out - Call [call] | |
| 9 | evaluations_complete | ReDIB COA: All Evaluations Complete for [code] | Application |
| 10 | resolution_accepted | ReDIB COA: Application [code] Accepted | Accept/decline |
| 11 | resolution_pending | ReDIB COA: Application [code] Placed on Waitlist | |
| 12 | resolution_rejected | ReDIB COA: Application [code] Resolution | |
| 13 | handoff_notification | ReDIB COA Access Approved - Application [code] Ready for Scheduling | |
| 14 | acceptance_expired | ReDIB COA: Application [code] has been closed | |
| 15 | publication_followup | ReDIB COA - Publication Follow-up for Application [code] | Publication form |

**Known defect.** `evaluation_reminder` and `evaluation_overdue` became
per-evaluator digests, which expect a pending count and a list of
evaluations. `send_test_emails` still passes the old single-evaluation
context, so both arrive with an empty count and no list ("Evaluation Reminder
( Pending)"). That is a fault in the test command, not in the templates. To
see them render properly, use the rehearsal harness instead.

## Verification Checklist

When reviewing the test emails:

1. **Styling**: a dark header band at the top of each HTML email.
2. **Links**: click each one and confirm it opens a real portal page. Links are
   built from `SITE_URL`, so in dev they point at your `runserver`
   (`http://127.0.0.1:8000` in `.env.example`).
3. **Consistency**: subject prefixes, closings and footer text match across
   templates.
4. **Contact email**: shows the value of `CONTACT_EMAIL` (default
   `info@redib.net`).

### Expected dead ends

The test application is `accepted`, which doesn't match what every linked
view expects:

- **Feasibility review link**: returns 404 unless the recipient is an active
  node coordinator for that node, and also once the review has been
  submitted.
- **Node resolution**: nothing to resolve, because the application is not
  `evaluated`.
- **Accept/decline link**: works, since the application is `accepted` with a
  future deadline.

These are limits of the test setup, not production bugs. In real use each
email goes out when the application is in the matching state.

## Changing a Template

Templates are defined in
`communications/management/commands/seed_email_templates.py` and written to
the database with `update_or_create`:

1. Edit the template in `seed_email_templates.py`.
2. Run `python manage.py seed_email_templates`.
3. In production, just deploy. The container entrypoint reseeds on every
   start, so a normal rebuild picks the change up.

Reseeding overwrites each template's subject and body, so edits made in the
Django admin are lost on the next deploy. A template switched off in the
admin (`is_active`) stays off.

`CONTACT_EMAIL` is injected into every template as `{{ contact_email }}`; set
it in `.env`.

## Troubleshooting

### "User with email … not found."
The recipient must already have an account. Create it or pick another `--to`.

### "No nodes exist in the database."
Load nodes first: `python manage.py setup_localtest3_database --reset --yes`
in dev, or see [SETUP_GUIDE.md](SETUP_GUIDE.md#initial-data-setup).

### Emails not arriving (production)
- Check the SMTP settings in `.env` (`EMAIL_BACKEND`, `EMAIL_HOST`, and so on).
- Check spam folders.
- Check the DNS records (SPF, DKIM, DMARC); see [DEPLOYMENT.md](DEPLOYMENT.md).
- Every attempt is recorded as an `EmailLog` row, visible in the admin.
