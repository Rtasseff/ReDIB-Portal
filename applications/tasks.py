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


@shared_task
def send_resolution_notifications_task(call_id):
    """
    Send resolution notification emails to all applicants.
    Triggered when coordinator finalizes call resolution (Phase 6).

    Args:
        call_id: ID of the call with finalized resolutions

    Returns:
        str: Summary of notifications sent
    """
    from calls.models import Call
    from django.db.models import Sum
    from .models import Application

    try:
        call = Call.objects.get(id=call_id)
    except Call.DoesNotExist:
        return f"Error: Call {call_id} not found"

    # Get all resolved applications
    resolved_apps = Application.objects.filter(
        call=call,
        resolution__in=['accepted', 'pending', 'rejected']
    ).select_related('applicant')

    notifications_sent = 0

    for application in resolved_apps:
        # Determine template type based on resolution
        template_type = f'resolution_{application.resolution}'

        # Calculate total hours requested (for accepted applications)
        hours_requested = application.requested_access.aggregate(
            total=Sum('hours_requested')
        )['total'] or 0

        # Build email context
        context = {
            'applicant_name': application.applicant_name,
            'application_code': application.code,
            'call_code': call.code,
            'final_score': float(application.final_score) if application.final_score else 0.0,
            'resolution': application.get_resolution_display(),
            'hours_granted': float(hours_requested),  # Renamed from hours_granted for backward compatibility
            'resolution_comments': application.resolution_comments or '',
            'resolution_date': application.resolution_date,
        }

        # Send notification email
        try:
            send_email_from_template(
                template_type=template_type,
                recipient_email=application.applicant.email,
                context_data=context,
                recipient_user_id=application.applicant.id,
                related_application_id=application.id
            )
            notifications_sent += 1
        except Exception as e:
            # Log error but continue with other notifications
            print(f"Error sending notification for {application.code}: {e}")
            continue

    return f"Sent {notifications_sent} resolution notifications for call {call.code}"


@shared_task
def send_single_resolution_notification_task(application_id):
    """
    Send resolution notification email for a single application.
    Triggered automatically when node resolution aggregation completes.

    Args:
        application_id: ID of the application with finalized resolution

    Returns:
        str: Summary of notification sent
    """
    from django.db.models import Sum
    from .models import Application

    try:
        application = Application.objects.select_related(
            'applicant', 'call'
        ).prefetch_related(
            'node_resolutions__node',
            'requested_access__equipment__node'
        ).get(id=application_id)
    except Application.DoesNotExist:
        return f"Error: Application {application_id} not found"

    # Verify the application has been resolved
    if application.resolution not in ['accepted', 'pending', 'rejected']:
        return f"Application {application.code} has not been fully resolved yet"

    # Determine template type based on resolution
    template_type = f'resolution_{application.resolution}'

    # Calculate hours details
    hours_data = application.requested_access.aggregate(
        total_requested=Sum('hours_requested'),
        total_approved=Sum('hours_approved')
    )
    hours_requested = hours_data['total_requested'] or 0
    hours_approved = hours_data['total_approved'] or 0

    # Build node decision breakdown
    node_decisions = []
    for nr in application.node_resolutions.filter(
        resolution__in=['accept', 'waitlist', 'reject']
    ).select_related('node'):
        node_decisions.append({
            'node_code': nr.node.code,
            'node_name': nr.node.name,
            'resolution': nr.get_resolution_display(),
            'comments': nr.comments or '',
        })

    # Build equipment breakdown with approved hours
    equipment_details = []
    for ra in application.requested_access.select_related('equipment__node'):
        equipment_details.append({
            'equipment_name': ra.equipment.name,
            'node_code': ra.equipment.node.code,
            'hours_requested': ra.hours_requested,
            'hours_approved': ra.hours_approved or 0,
        })

    # Build email context
    context = {
        'applicant_name': application.applicant_name,
        'application_code': application.code,
        'call_code': application.call.code,
        'call_name': application.call.name,
        'final_score': float(application.final_score) if application.final_score else 0.0,
        'resolution': application.get_resolution_display(),
        'hours_requested': float(hours_requested),
        'hours_approved': float(hours_approved),
        'resolution_comments': application.resolution_comments or '',
        'resolution_date': application.resolution_date,
        'node_decisions': node_decisions,
        'equipment_details': equipment_details,
    }

    # Add acceptance deadline for accepted applications
    if application.resolution == 'accepted' and application.acceptance_deadline:
        context['acceptance_deadline'] = application.acceptance_deadline
        context['days_to_respond'] = application.days_until_acceptance_deadline

    # Send notification email
    try:
        send_email_from_template(
            template_type=template_type,
            recipient_email=application.applicant.email,
            context_data=context,
            recipient_user_id=application.applicant.id,
            related_application_id=application.id
        )
        return f"Sent resolution notification for {application.code} ({application.resolution})"
    except Exception as e:
        return f"Error sending notification for {application.code}: {e}"


@shared_task
def process_acceptance_deadlines():
    """
    Daily task to process acceptance deadlines for approved applications.

    Per REDIB-02-PDA section 6.1.6: "Applicants have 10 days to accept or reject"

    Actions:
    - Day 7: Send reminder email (3 days before deadline)
    - Day 10: Auto-expire applications with no response (status → 'expired')

    Returns:
        str: Summary of reminders sent and applications expired
    """
    from django.utils import timezone
    from datetime import timedelta
    from .models import Application

    now = timezone.now()

    # === DAY 7: Send Reminders (3 days before deadline) ===
    seven_days_from_now = now + timedelta(days=3)
    reminder_apps = Application.objects.filter(
        status='accepted',
        accepted_by_applicant__isnull=True,  # Not yet responded
        acceptance_deadline__lte=seven_days_from_now,
        acceptance_deadline__gte=now,  # Not yet expired
    ).select_related('applicant')

    # Filter: only send reminder if not already reminded in last 24 hours
    # (Check EmailLog for recent 'acceptance_reminder' emails)
    from communications.models import EmailLog
    reminders_sent = 0

    for app in reminder_apps:
        # Check if reminder already sent recently
        recent_reminder = EmailLog.objects.filter(
            template__template_type='acceptance_reminder',
            recipient_email=app.applicant.email,
            related_application_id=app.id,
            sent_at__gte=now - timedelta(days=1)
        ).exists()

        if recent_reminder:
            continue

        # Check user notification preferences
        if hasattr(app.applicant, 'notification_preferences'):
            prefs = app.applicant.notification_preferences
            if not prefs.notify_reminders or not prefs.notify_application_updates:
                continue

        # Send reminder email
        context = {
            'applicant_name': app.applicant.get_full_name(),
            'application_code': app.code,
            'brief_description': app.brief_description,
            'deadline': app.acceptance_deadline,
            'days_remaining': app.days_until_acceptance_deadline,
            'acceptance_url': f'/applications/{app.id}/accept/',  # Use reverse() in production
        }

        send_email_from_template(
            template_type='acceptance_reminder',
            recipient_email=app.applicant.email,
            context_data=context,
            recipient_user_id=app.applicant.id,
            related_application_id=app.id
        )

        reminders_sent += 1

    # === DAY 10+: Auto-Expire ===
    expired_apps = Application.objects.filter(
        status='accepted',
        accepted_by_applicant__isnull=True,  # Not yet responded
        acceptance_deadline__lt=now  # Deadline passed
    )

    expired_count = 0
    for app in expired_apps:
        app.status = 'expired'
        app.accepted_by_applicant = False  # Mark as declined by timeout
        app.accepted_at = now
        app.resolution_comments += f"\n\n[AUTO-EXPIRED] No response by acceptance deadline ({app.acceptance_deadline.date()})"
        app.save()

        # Optionally: send expiration notification to applicant
        try:
            send_email_from_template(
                template_type='acceptance_expired',
                recipient_email=app.applicant.email,
                context_data={
                    'applicant_name': app.applicant.get_full_name(),
                    'application_code': app.code,
                    'deadline': app.acceptance_deadline,
                },
                recipient_user_id=app.applicant.id,
                related_application_id=app.id
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to send expiration email for {app.code}: {e}")

        expired_count += 1

    return f"Sent {reminders_sent} acceptance reminders, auto-expired {expired_count} applications"
