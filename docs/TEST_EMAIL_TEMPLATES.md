# Test Email Templates Guide

This guide describes how to verify all email templates using the `send_test_emails` management command.

## Overview

The command creates isolated test data, sends all 15 email templates to a single recipient, and optionally cleans up afterward. It is used to verify that emails render correctly with working links and consistent styling.

## Prerequisites

- Email templates must be seeded: `python manage.py seed_email_templates`
- At least one node must exist (CICBIO preferred)
- The recipient email must belong to an existing user in the system
- SMTP must be configured (emails are sent via the live email backend)

## Running the Test

### Send all templates

```bash
# Local development
python manage.py send_test_emails --to your-email@example.com

# Production (Docker)
docker compose -f docker-compose.prod.yml exec web python manage.py send_test_emails --to your-email@example.com
```

### Clean up test data

After verifying emails, remove the test objects:

```bash
# Local development
python manage.py send_test_emails --cleanup

# Production (Docker)
docker compose -f docker-compose.prod.yml exec web python manage.py send_test_emails --cleanup
```

### Default recipient

If `--to` is omitted, emails are sent to `rtasseff@cicbiomagune.es`.

## What It Creates

The command creates temporary test objects under a dedicated call **COA-EMAIL-TEST**, completely separate from real data:

| Object | Details |
|--------|---------|
| Call | `COA-EMAIL-TEST` (status: closed, evaluation deadline in the past) |
| Application | `COA-EMAIL-TEST-001` (status: accepted, acceptance deadline in the future) |
| FeasibilityReview | For the recipient's node (pending) |
| Evaluation | Assigned to the recipient |
| UserRole | Evaluator role added to recipient (if not already present) |

**Isolation:** All test objects exist under the `COA-EMAIL-TEST` call. No existing calls, applications, or evaluations are modified. The only change to existing data is temporarily adding an evaluator role to the recipient (removed on cleanup).

## Templates Sent

All 15 email templates are sent with realistic context data:

| # | Template | Subject Pattern | Has Link |
|---|----------|----------------|----------|
| 1 | feasibility_request | New Application for Equipment at [node] | Review link |
| 2 | application_received | Application [code] Received | No |
| 3 | feasibility_complete | Feasibility Review Complete for [code] | No |
| 4 | evaluation_assigned | Evaluation Assignment for [code] | Evaluation link |
| 5 | evaluation_reminder | Evaluation Reminder for [code] | Evaluation link |
| 6 | evaluation_overdue | Your Evaluation for [code] is Overdue | Evaluation link |
| 7 | coordinator_overdue_evaluations | Overdue Evaluations for Call [call] | No |
| 8 | coordinator_evaluations_locked | Evaluators Locked Out - Call [call] | No |
| 9 | evaluations_complete | All Evaluations Complete for [code] | Application link |
| 10 | resolution_accepted | Application [code] Accepted | Accept/decline link |
| 11 | resolution_pending | Application [code] Pending | No |
| 12 | resolution_rejected | Application [code] Resolution | No |
| 13 | handoff_notification | Access Approved - Application [code] Ready for Scheduling | No |
| 14 | acceptance_expired | Acceptance Deadline Expired for Application [code] | No |
| 15 | publication_followup | Publication Follow-up for Application [code] | Publication link |

## Verification Checklist

When reviewing the test emails:

1. **Styling** - All emails should have a colored header box at the top with "ReDIB COA Portal" (or similar) heading
2. **Links** - Click every link to confirm it loads a real page on the portal
3. **Consistency** - Subject lines, closings ("Best regards, ReDIB COA Team"), and footer text should be consistent
4. **Contact email** - Templates referencing the contact email should show the value from `CONTACT_EMAIL` in Django settings (default: `info@redib.net`)

### Known test limitations

Some links may return 404 or show empty pages during testing. This is expected because the test application's status (`accepted`) doesn't match what certain views require:

- **Feasibility review link**: Returns 404 if the review was already submitted in a prior test run
- **Node resolution page**: Shows no pending items because the test app is not in `evaluated` status
- **Accept/decline link**: Works correctly since the test app is in `accepted` status with a future deadline

These are test setup limitations, not production bugs. In production, each email is sent when the application is in the correct status for that workflow step.

## Contact Email Configuration

The contact email used across all templates is configured as a Django setting:

```python
# redib/settings.py
CONTACT_EMAIL = env('CONTACT_EMAIL', default='info@redib.net')
```

This value is automatically injected as `{{ contact_email }}` into every email template context. To change the contact email across all templates, update this single setting (or set `CONTACT_EMAIL` in your `.env` file).

## Modifying Templates

Email templates are defined in `communications/management/commands/seed_email_templates.py` and loaded into the database via `update_or_create`. To modify a template:

1. Edit the template in `seed_email_templates.py`
2. Run `python manage.py seed_email_templates` to update the database
3. In production, rebuild the container first: `docker compose -f docker-compose.prod.yml up -d --build web`
4. Then re-seed: `docker compose -f docker-compose.prod.yml exec web python manage.py seed_email_templates`

## Troubleshooting

### "User not found" error
The recipient email must belong to an existing user. Create the user first or use a different `--to` address.

### "No nodes exist" error
Run `python manage.py populate_redib_nodes` to load nodes.

### Emails not arriving
- Check SMTP configuration in `.env` (`EMAIL_BACKEND`, `EMAIL_HOST`, etc.)
- Check spam/junk folders
- Verify DNS records (SPF, DKIM, DMARC) per [DEPLOYMENT.md](DEPLOYMENT.md)
