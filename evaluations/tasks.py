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
    Randomly assign evaluators to an application with conflict-of-interest handling.
    Based on design document section 6.2 - Auto-assign evaluators (random 2 per app).

    Conflict-of-interest rules:
    - Evaluators cannot review applications from their own organization
    - Evaluators already assigned to the application are skipped

    Args:
        application_id: ID of the application
        num_evaluators: Number of evaluators to assign (default: 2)

    Returns:
        dict with assigned evaluator IDs and exclusion reasons
    """
    from applications.models import Application
    from core.models import UserRole, User
    import random

    application = Application.objects.select_related(
        'call',
        'applicant',
        'applicant__organization'
    ).get(id=application_id)

    # Get pool of active evaluators
    evaluator_roles = UserRole.objects.filter(
        role='evaluator',
        is_active=True
    ).select_related('user', 'user__organization')

    # Optionally filter by area matching
    if hasattr(application, 'specialization_area') and application.specialization_area:
        area_evaluators = evaluator_roles.filter(area=application.specialization_area)
        if area_evaluators.exists():
            evaluator_roles = area_evaluators

    # Get user objects
    available_evaluators = [role.user for role in evaluator_roles]

    # Track exclusion reasons for logging
    excluded = []

    # Remove evaluators who already have this application
    existing_evaluator_ids = set(Evaluation.objects.filter(
        application=application
    ).values_list('evaluator_id', flat=True))

    # Remove evaluators with conflict of interest
    # (same organization as applicant)
    applicant_org_id = application.applicant.organization_id if application.applicant.organization else None

    filtered_evaluators = []
    for evaluator in available_evaluators:
        if evaluator.id in existing_evaluator_ids:
            excluded.append({
                'evaluator_id': evaluator.id,
                'evaluator_email': evaluator.email,
                'reason': 'already_assigned'
            })
            continue

        if applicant_org_id and evaluator.organization_id == applicant_org_id:
            excluded.append({
                'evaluator_id': evaluator.id,
                'evaluator_email': evaluator.email,
                'reason': 'conflict_of_interest',
                'detail': f'Same organization as applicant ({evaluator.organization.name})'
            })
            continue

        filtered_evaluators.append(evaluator)

    # Randomly select evaluators
    num_to_assign = min(num_evaluators, len(filtered_evaluators))

    if num_to_assign == 0:
        return {
            'assigned': [],
            'excluded': excluded,
            'error': 'No eligible evaluators available'
        }

    selected_evaluators = random.sample(filtered_evaluators, num_to_assign)

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
            'evaluation_url': f'/evaluations/{evaluation.id}/',
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

    return {
        'assigned': assigned_ids,
        'excluded': excluded,
        'warning': f'Assigned {len(assigned_ids)} of {num_evaluators} requested evaluators' if len(assigned_ids) < num_evaluators else None
    }


@shared_task
def assign_evaluators_to_call(call_id, num_evaluators=2):
    """
    Automatically assign evaluators to all eligible applications in a call.
    Triggered when call submission period closes.

    Only assigns to applications in PENDING_EVALUATION status.

    Args:
        call_id: ID of the call
        num_evaluators: Number of evaluators per application (default: 2)

    Returns:
        dict with assignment summary
    """
    from calls.models import Call
    from applications.models import Application

    call = Call.objects.get(id=call_id)

    # Get all applications in PENDING_EVALUATION status
    eligible_applications = Application.objects.filter(
        call=call,
        status='pending_evaluation'
    )

    results = {
        'call_code': call.code,
        'total_applications': eligible_applications.count(),
        'assignments': [],
        'errors': []
    }

    for application in eligible_applications:
        try:
            result = assign_evaluators_to_application(
                application_id=application.id,
                num_evaluators=num_evaluators
            )

            results['assignments'].append({
                'application_code': application.code,
                'application_id': application.id,
                'assigned_count': len(result['assigned']),
                'assigned_evaluators': result['assigned'],
                'excluded_count': len(result['excluded']),
                'warning': result.get('warning'),
                'error': result.get('error')
            })

        except Exception as e:
            results['errors'].append({
                'application_code': application.code,
                'application_id': application.id,
                'error': str(e)
            })

    # Transition call to 'closed' status if not already
    if call.status == 'open':
        call.status = 'closed'
        call.save()

    return results
