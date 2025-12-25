"""
Celery tasks for access grant and publication workflow automation.
Based on design document section 7.3 - Periodic Tasks.
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import AccessGrant
from communications.tasks import send_email_from_template


@shared_task
def process_acceptance_deadlines():
    """
    Daily task to process acceptance deadlines for access grants.
    Runs at 10 AM daily (configured in redib/celery.py).

    Based on design section 6.2: "10 days without acceptance → auto-decline"

    Actions:
    - Send reminder 7 days after grant
    - Auto-decline 10 days after grant if no response
    """
    now = timezone.now()

    # Find grants needing reminders (7 days old, no response)
    seven_days_ago = now - timedelta(days=7)
    reminder_grants = AccessGrant.objects.filter(
        accepted_by_user__isnull=True,
        acceptance_deadline__isnull=False,
        created_at__lte=seven_days_ago,
        created_at__gte=seven_days_ago - timedelta(hours=24)  # Only send once
    ).select_related('application', 'application__applicant', 'equipment')

    reminders_sent = 0
    for grant in reminder_grants:
        # Check if user wants reminders
        if hasattr(grant.application.applicant, 'notification_preferences'):
            prefs = grant.application.applicant.notification_preferences
            if not prefs.notify_reminders or not prefs.notify_application_updates:
                continue

        context = {
            'applicant_name': grant.application.applicant.get_full_name(),
            'application_code': grant.application.code,
            'equipment_name': grant.equipment.name,
            'hours_granted': grant.hours_granted,
            'deadline': grant.acceptance_deadline,
            'days_remaining': 3,  # 10 - 7 = 3 days remaining
        }

        send_email_from_template(
            template_type='acceptance_reminder',
            recipient_email=grant.application.applicant.email,
            context_data=context,
            recipient_user_id=grant.application.applicant.id,
            related_application_id=grant.application.id
        )

        reminders_sent += 1

    # Find grants to auto-decline (10+ days old, no response)
    ten_days_ago = now - timedelta(days=10)
    expired_grants = AccessGrant.objects.filter(
        accepted_by_user__isnull=True,
        acceptance_deadline__isnull=False,
        acceptance_deadline__lte=now,
        created_at__lte=ten_days_ago
    )

    declined_count = 0
    for grant in expired_grants:
        grant.accepted_by_user = False
        grant.save()

        # Update application status if needed
        application = grant.application
        if application.status == 'accepted':
            application.status = 'rejected'
            application.resolution = 'rejected'
            application.resolution_comments += f"\n\nAuto-declined due to no response by {now.date()}"
            application.save()

        declined_count += 1

    return f"Sent {reminders_sent} acceptance reminders, auto-declined {declined_count} grants"


@shared_task
def send_publication_followups():
    """
    Weekly task to send publication follow-up emails.
    Runs on Mondays at 10 AM (configured in redib/celery.py).

    Based on design section 6.2: "6 months after completion → Send publication follow-up email"

    Sends follow-up to completed grants without publications.
    """
    now = timezone.now()
    six_months_ago = now - timedelta(days=180)

    # Find completed grants from ~6 months ago without publications
    completed_grants = AccessGrant.objects.filter(
        completed_at__isnull=False,
        completed_at__lte=six_months_ago,
        completed_at__gte=six_months_ago - timedelta(days=7),  # Weekly window
        publications__isnull=True  # No publications reported
    ).select_related('application', 'application__applicant', 'equipment', 'equipment__node')

    followups_sent = 0

    for grant in completed_grants:
        # Check if user wants reminders
        if hasattr(grant.application.applicant, 'notification_preferences'):
            prefs = grant.application.applicant.notification_preferences
            if not prefs.notify_application_updates:
                continue

        context = {
            'applicant_name': grant.application.applicant.get_full_name(),
            'application_code': grant.application.code,
            'equipment_name': grant.equipment.name,
            'node_name': grant.equipment.node.name,
            'completed_date': grant.completed_at,
            'acknowledgment_text': grant.equipment.node.acknowledgment_text,
        }

        send_email_from_template(
            template_type='publication_followup',
            recipient_email=grant.application.applicant.email,
            context_data=context,
            recipient_user_id=grant.application.applicant.id,
            related_application_id=grant.application.id
        )

        followups_sent += 1

    return f"Sent {followups_sent} publication follow-up emails"
