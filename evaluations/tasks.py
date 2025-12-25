"""
Celery tasks for evaluation workflow automation.
Based on design document section 7.3 - Periodic Tasks.
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Evaluation
from communications.tasks import send_email_from_template


@shared_task
def send_evaluation_reminders():
    """
    Daily task to send reminders for pending evaluations.
    Runs at 9 AM daily (configured in redib/celery.py).

    Sends reminder if:
    - Evaluation is incomplete (completed_at is None)
    - Less than 7 days until evaluation deadline
    """
    # Find incomplete evaluations approaching deadline
    now = timezone.now()
    seven_days = now + timedelta(days=7)

    pending_evaluations = Evaluation.objects.filter(
        completed_at__isnull=True,
        application__call__evaluation_deadline__lte=seven_days,
        application__call__evaluation_deadline__gte=now
    ).select_related('application', 'application__call', 'evaluator')

    reminders_sent = 0

    for evaluation in pending_evaluations:
        # Check if user wants reminders
        if hasattr(evaluation.evaluator, 'notification_preferences'):
            prefs = evaluation.evaluator.notification_preferences
            if not prefs.notify_reminders or not prefs.notify_evaluation_assigned:
                continue

        # Calculate days remaining
        days_remaining = (evaluation.application.call.evaluation_deadline - now).days

        # Send reminder email
        context = {
            'evaluator_name': evaluation.evaluator.get_full_name(),
            'application_code': evaluation.application.code,
            'application_title': evaluation.application.brief_description,
            'call_code': evaluation.application.call.code,
            'days_remaining': days_remaining,
            'deadline': evaluation.application.call.evaluation_deadline,
        }

        send_email_from_template(
            template_type='evaluation_reminder',
            recipient_email=evaluation.evaluator.email,
            context_data=context,
            recipient_user_id=evaluation.evaluator.id,
            related_application_id=evaluation.application.id,
            related_evaluation_id=evaluation.id
        )

        reminders_sent += 1

    return f"Sent {reminders_sent} evaluation reminders"


@shared_task
def assign_evaluators_to_application(application_id, num_evaluators=2):
    """
    Randomly assign evaluators to an application.
    Based on design document section 6.2 - Auto-assign evaluators (random 2 per app).

    Args:
        application_id: ID of the application
        num_evaluators: Number of evaluators to assign (default: 2)

    Returns:
        List of assigned evaluator IDs
    """
    from applications.models import Application
    from core.models import UserRole, User
    import random

    application = Application.objects.get(id=application_id)

    # Get pool of active evaluators
    # Filter by specialization area if possible
    evaluator_roles = UserRole.objects.filter(
        role='evaluator',
        is_active=True
    ).select_related('user')

    # Optionally filter by area matching
    if application.specialization_area:
        area_evaluators = evaluator_roles.filter(area=application.specialization_area)
        if area_evaluators.exists():
            evaluator_roles = area_evaluators

    # Get user IDs
    available_evaluators = [role.user for role in evaluator_roles]

    # Remove evaluators who already have this application
    existing_evaluators = Evaluation.objects.filter(
        application=application
    ).values_list('evaluator_id', flat=True)

    available_evaluators = [
        e for e in available_evaluators
        if e.id not in existing_evaluators
    ]

    # Randomly select evaluators
    num_to_assign = min(num_evaluators, len(available_evaluators))
    selected_evaluators = random.sample(available_evaluators, num_to_assign)

    # Create evaluation records
    assigned_ids = []
    for evaluator in selected_evaluators:
        evaluation = Evaluation.objects.create(
            application=application,
            evaluator=evaluator
        )

        # Send notification email
        context = {
            'evaluator_name': evaluator.get_full_name(),
            'application_code': application.code,
            'call_code': application.call.code,
            'deadline': application.call.evaluation_deadline,
        }

        send_email_from_template(
            template_type='evaluation_assigned',
            recipient_email=evaluator.email,
            context_data=context,
            recipient_user_id=evaluator.id,
            related_application_id=application.id,
            related_evaluation_id=evaluation.id
        )

        assigned_ids.append(evaluator.id)

    return assigned_ids
