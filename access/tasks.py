"""
Celery tasks for the publication follow-up workflow.
Based on design document section 7.3 - Periodic Tasks.
"""

from celery import shared_task
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from communications.tasks import send_email_from_template


@shared_task
def send_publication_followups():
    """
    Weekly task to send publication follow-up emails.
    Runs on Mondays at 10 AM (configured in redib/celery.py).

    Based on design section 6.2: "6 months after completion → Send publication follow-up email"

    Sends follow-up to accepted applications ~6 months after handoff without publications.
    """
    from applications.models import Application

    now = timezone.now()
    six_months_ago = now - timedelta(days=180)

    # Find accepted applications from ~6 months ago without publications
    # Use handoff_email_sent_at as the "completion" timestamp
    completed_applications = Application.objects.filter(
        status__in=['accepted', 'completed'],
        accepted_by_applicant=True,  # Applicant accepted the grant
        handoff_email_sent_at__isnull=False,  # Handoff occurred
        handoff_email_sent_at__lte=six_months_ago,  # ~6 months ago
        handoff_email_sent_at__gte=six_months_ago - timedelta(days=7),  # Weekly window
        publications__isnull=True  # No publications reported yet
    ).select_related('applicant')

    followups_sent = 0

    for application in completed_applications:
        # Check if user wants reminders
        if hasattr(application.applicant, 'notification_preferences'):
            prefs = application.applicant.notification_preferences
            if not prefs.notify_application_updates:
                continue

        # Build email context
        context = {
            'applicant_name': application.applicant.get_full_name(),
            'application_code': application.code,
            'project_name': application.project_name or application.brief_description,
            'handoff_date': application.handoff_email_sent_at,
            'acknowledgment_text': 'This work acknowledges the use of ReDIB ICTS, supported by the Ministry of Science, Innovation and Universities (MICIU).',
            'publication_url': settings.SITE_URL + reverse('access:publication_submit'),
        }

        applicant_email = application.applicant_email or application.applicant.email
        send_email_from_template(
            template_type='publication_followup',
            recipient_email=applicant_email,
            context_data=context,
            recipient_user_id=application.applicant.id,
            related_application_id=application.id
        )

        followups_sent += 1

    return f"Sent {followups_sent} publication follow-up emails"
