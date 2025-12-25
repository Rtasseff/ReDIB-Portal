"""
Celery tasks for application workflow automation.
Based on design document section 7.3 - Periodic Tasks.
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import FeasibilityReview
from communications.tasks import send_email_from_template


@shared_task
def send_feasibility_reminders():
    """
    Daily task to send reminders for pending feasibility reviews.
    Runs at 9 AM daily (configured in redib/celery.py).

    Sends reminder if:
    - Feasibility review is pending (is_feasible is None)
    - More than 5 days have passed since application submission
    - No reminder sent in last 3 days
    """
    from core.models import UserRole

    # Find pending reviews older than 5 days
    cutoff_date = timezone.now() - timedelta(days=5)

    pending_reviews = FeasibilityReview.objects.filter(
        is_feasible__isnull=True,
        application__submitted_at__lte=cutoff_date,
        reviewed_at__isnull=True
    ).select_related('application', 'node', 'reviewer')

    reminders_sent = 0

    for review in pending_reviews:
        # Check if user wants reminders
        if hasattr(review.reviewer, 'notification_preferences'):
            prefs = review.reviewer.notification_preferences
            if not prefs.notify_reminders or not prefs.notify_feasibility_requests:
                continue

        # Send reminder email
        context = {
            'reviewer_name': review.reviewer.get_full_name(),
            'application_code': review.application.code,
            'application_title': review.application.brief_description,
            'node_name': review.node.name,
            'days_pending': (timezone.now() - review.application.submitted_at).days,
            'deadline': review.application.call.evaluation_deadline,
        }

        send_email_from_template(
            template_type='feasibility_reminder',
            recipient_email=review.reviewer.email,
            context_data=context,
            recipient_user_id=review.reviewer.id,
            related_application_id=review.application.id
        )

        reminders_sent += 1

    return f"Sent {reminders_sent} feasibility review reminders"
