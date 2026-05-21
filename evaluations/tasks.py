"""
Celery tasks for evaluation workflow automation.
Based on design document section 7.3 - Periodic Tasks.
"""

from celery import shared_task
from django.conf import settings
from django.urls import reverse
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
            'evaluation_url': settings.SITE_URL + reverse('evaluations:evaluation_detail', kwargs={'pk': evaluation.id}),
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
def notify_overdue_evaluators():
    """
    Daily task to notify evaluators whose evaluations are overdue.

    Sends a notification on the first day past the evaluation deadline.
    Only sends once per evaluation (checks if email was already sent via EmailLog).
    """
    import logging
    from communications.models import EmailLog

    logger = logging.getLogger(__name__)
    now = timezone.now()

    # Find incomplete evaluations where deadline has just passed (within last 24 hours)
    overdue_evaluations = Evaluation.objects.filter(
        completed_at__isnull=True,
        application__call__evaluation_deadline__lt=now,
        application__call__evaluation_deadline__gte=now - timedelta(hours=25),
    ).select_related('application', 'application__call', 'evaluator')

    notifications_sent = 0

    for evaluation in overdue_evaluations:
        # Check if we already sent an overdue notice for this evaluation
        already_sent = EmailLog.objects.filter(
            related_evaluation_id=evaluation.id,
            subject__icontains='overdue',
            status='sent',
        ).exists()

        if already_sent:
            continue

        context = {
            'evaluator_name': evaluation.evaluator.get_full_name(),
            'application_code': evaluation.application.code,
            'call_code': evaluation.application.call.code,
            'deadline': evaluation.application.call.evaluation_deadline,
            'evaluation_url': settings.SITE_URL + reverse('evaluations:evaluation_detail', kwargs={'pk': evaluation.id}),
        }

        send_email_from_template(
            template_type='evaluation_overdue',
            recipient_email=evaluation.evaluator.email,
            context_data=context,
            recipient_user_id=evaluation.evaluator.id,
            related_application_id=evaluation.application.id,
            related_evaluation_id=evaluation.id
        )

        notifications_sent += 1

    logger.info("Sent %d overdue evaluation notifications to evaluators", notifications_sent)
    return f"Sent {notifications_sent} overdue evaluator notifications"


@shared_task
def notify_coordinator_overdue_evaluations():
    """
    Daily task to notify coordinators about overdue evaluations.

    Trigger 1: Sent when evaluation deadline passes and there are pending evaluations.
    Trigger 2: Sent 1 week after deadline if evaluations are still pending (lockout notification).
    """
    import logging
    from calls.models import Call
    from core.models import User

    logger = logging.getLogger(__name__)
    now = timezone.now()

    # Find calls with overdue evaluations
    calls_with_overdue = Call.objects.filter(
        status='closed',
        evaluation_deadline__lt=now,
    )

    if not calls_with_overdue.exists():
        return "No calls with overdue evaluations"

    # Get all active coordinators
    coordinators = User.objects.filter(
        roles__role='coordinator',
        roles__is_active=True
    ).distinct()

    if not coordinators.exists():
        return "No active coordinators to notify"

    notifications_sent = 0

    for call in calls_with_overdue:
        pending_evals = Evaluation.objects.filter(
            application__call=call,
            completed_at__isnull=True,
        ).select_related('evaluator', 'application')

        if not pending_evals.exists():
            continue

        days_overdue = (now - call.evaluation_deadline).days
        is_lockout = days_overdue >= 7

        # Only send on day 0 (deadline just passed) or day 7 (lockout)
        # Allow a 25-hour window for the daily check
        deadline_just_passed = (0 <= days_overdue <= 1 and
            (now - call.evaluation_deadline).total_seconds() < 25 * 3600)
        lockout_just_happened = (7 <= days_overdue <= 8 and
            (now - (call.evaluation_deadline + timedelta(days=7))).total_seconds() < 25 * 3600)

        if not deadline_just_passed and not lockout_just_happened:
            continue

        # Build list of pending evaluations for context
        pending_list = []
        for ev in pending_evals:
            pending_list.append(
                f"{ev.application.code} - Evaluator: {ev.evaluator.get_full_name()} ({ev.evaluator.email})"
            )

        template_type = 'coordinator_evaluations_locked' if is_lockout else 'coordinator_overdue_evaluations'

        for coordinator in coordinators:
            context = {
                'coordinator_name': coordinator.get_full_name(),
                'call_code': call.code,
                'call_title': call.title,
                'deadline': call.evaluation_deadline,
                'days_overdue': days_overdue,
                'pending_count': pending_evals.count(),
                'pending_evaluations': '\n'.join(pending_list),
                'is_lockout': is_lockout,
            }

            send_email_from_template(
                template_type=template_type,
                recipient_email=coordinator.email,
                context_data=context,
                recipient_user_id=coordinator.id,
                related_call_id=call.id,
            )

            notifications_sent += 1

    logger.info("Sent %d coordinator overdue evaluation notifications", notifications_sent)
    return f"Sent {notifications_sent} coordinator notifications"


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

    # Get pool of active evaluators. Both the evaluator role AND the user account
    # itself must be active — a deactivated user account cannot log in to evaluate.
    evaluator_roles = UserRole.objects.filter(
        role='evaluator',
        is_active=True,
        user__is_active=True,
    ).select_related('user', 'user__organization')

    # Get all user objects
    all_evaluators = [role.user for role in evaluator_roles]

    # Track exclusion reasons for logging
    excluded = []

    # Remove evaluators who already have this application
    existing_evaluator_ids = set(Evaluation.objects.filter(
        application=application
    ).values_list('evaluator_id', flat=True))

    # Remove evaluators with conflict of interest (compare application's declared entity with evaluator's org)
    applicant_org_name = application.applicant_entity or (
        application.applicant.organization.name if application.applicant.organization else None
    )
    applicant_org_name_lower = applicant_org_name.strip().lower() if applicant_org_name else None

    # Build filtered list, separating by area match preference
    area_matched_evaluators = []
    other_evaluators = []

    for evaluator in all_evaluators:
        # Skip if already assigned
        if evaluator.id in existing_evaluator_ids:
            excluded.append({
                'evaluator_id': evaluator.id,
                'evaluator_email': evaluator.email,
                'reason': 'already_assigned'
            })
            continue

        # Skip if conflict of interest
        evaluator_org_name = evaluator.organization.name if evaluator.organization else None
        if applicant_org_name_lower and evaluator_org_name and evaluator_org_name.strip().lower() == applicant_org_name_lower:
            excluded.append({
                'evaluator_id': evaluator.id,
                'evaluator_email': evaluator.email,
                'reason': 'conflict_of_interest',
                'detail': f'Same organization as applicant ({evaluator_org_name})'
            })
            continue

        # Check if any of the evaluator's areas matches the application's specialization
        evaluator_role = evaluator_roles.filter(user=evaluator).first()
        if (hasattr(application, 'specialization_area') and
            application.specialization_area and
            evaluator_role and
            evaluator_role.has_area(application.specialization_area)):
            area_matched_evaluators.append(evaluator)
        else:
            other_evaluators.append(evaluator)

    # Prefer area-matched evaluators, but fall back to others if needed
    # This implements "best effort" area matching rather than hard requirement
    total_available = len(area_matched_evaluators) + len(other_evaluators)
    num_to_assign = min(num_evaluators, total_available)

    if num_to_assign == 0:
        return {
            'assigned': [],
            'excluded': excluded,
            'error': 'No eligible evaluators available'
        }

    # Select area-matched evaluators first (randomly from that pool)
    selected_evaluators = []
    remaining_needed = num_to_assign

    if area_matched_evaluators:
        num_from_matched = min(remaining_needed, len(area_matched_evaluators))
        selected_evaluators.extend(random.sample(area_matched_evaluators, num_from_matched))
        remaining_needed -= num_from_matched

    # If we still need more evaluators, select from other evaluators
    if remaining_needed > 0 and other_evaluators:
        num_from_others = min(remaining_needed, len(other_evaluators))
        selected_evaluators.extend(random.sample(other_evaluators, num_from_others))

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
            'evaluation_url': settings.SITE_URL + reverse('evaluations:evaluation_detail', kwargs={'pk': evaluation.id}),
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
    Automatically assign evaluators across all eligible applications in a call,
    balancing load with a hard per-evaluator cap and a COI-first ordering.

    Cap: floor(total_slots / pool_size) + 1, where total_slots = num_apps * num_evaluators.
    With pool=9 and 23 apps x 2, this is floor(46/9)+1 = 6 assignments per evaluator max.

    Hard rules (never violated):
      - Conflict of interest: evaluator cannot share applicant's organization.
      - Cap: no evaluator exceeds max_per_evaluator (counting pre-existing Evaluations).
      - No duplicate (evaluator, application) pairs.

    Soft rule:
      - Specialty area match is preferred. If the area-matched pool is empty or fully
        capped for an application, fall back to any eligible evaluator.

    Algorithm: split apps into (has-any-COI) vs (no-COI) piles. Run num_evaluators passes;
    each pass shuffles both piles and walks the COI pile first, then the no-COI pile,
    attempting to add one evaluator per app per pass. Apps that cannot be filled surface
    in results['unfilled'] for a warning banner in the view.

    Only assigns to applications in PENDING_EVALUATION status. Apps that receive >= 1
    evaluator transition to UNDER_EVALUATION; apps that get zero remain pending so the
    coordinator can intervene.

    Args:
        call_id: ID of the call
        num_evaluators: Number of evaluators per application (default: 2)

    Returns:
        dict with keys: call_code, total_applications, assignments, errors,
        max_per_evaluator, pool_size, unfilled.
    """
    from calls.models import Call
    from applications.models import Application
    from core.models import UserRole
    import random

    call = Call.objects.get(id=call_id)

    eligible_applications = list(
        Application.objects.filter(call=call, status='pending_evaluation')
        .select_related('applicant', 'applicant__organization')
    )

    evaluator_roles = (
        UserRole.objects
        .filter(role='evaluator', is_active=True, user__is_active=True)
        .select_related('user', 'user__organization')
    )
    role_by_user_id = {r.user_id: r for r in evaluator_roles}
    pool = list(role_by_user_id.values())  # UserRole objects; use r.user for the User
    pool_size = len(pool)

    results = {
        'call_code': call.code,
        'total_applications': len(eligible_applications),
        'pool_size': pool_size,
        'max_per_evaluator': 0,
        'assignments': [],
        'errors': [],
        'unfilled': [],
    }

    if not eligible_applications or pool_size == 0:
        # Nothing to do — but still record every app as unfilled when pool is empty so
        # the coordinator sees the gap.
        for application in eligible_applications:
            results['unfilled'].append({
                'application_code': application.code,
                'application_id': application.id,
                'assigned': 0,
                'requested': num_evaluators,
                'shortfall': num_evaluators,
            })
            results['assignments'].append({
                'application_code': application.code,
                'application_id': application.id,
                'assigned_count': 0,
                'assigned_evaluators': [],
                'excluded_count': 0,
                'warning': f'Assigned 0 of {num_evaluators} requested evaluators',
                'error': 'No eligible evaluators available' if pool_size == 0 else None,
            })
        if call.status == 'open':
            call.status = 'closed'
            call.save()
        return results

    total_slots = len(eligible_applications) * num_evaluators
    max_per_evaluator = (total_slots // pool_size) + 1
    results['max_per_evaluator'] = max_per_evaluator

    # Per-app static state: COI set + pre-existing assignments.
    app_state = {}
    coi_apps = []
    clear_apps = []
    for application in eligible_applications:
        applicant_org = application.applicant_entity or (
            application.applicant.organization.name
            if application.applicant.organization else None
        )
        applicant_org_l = applicant_org.strip().lower() if applicant_org else None
        coi_ids = set()
        for role in pool:
            ev_org = role.user.organization.name if role.user.organization else None
            if applicant_org_l and ev_org and ev_org.strip().lower() == applicant_org_l:
                coi_ids.add(role.user_id)
        already_ids = set(
            Evaluation.objects.filter(application=application)
            .values_list('evaluator_id', flat=True)
        )
        app_state[application.id] = {
            'application': application,
            'coi_ids': coi_ids,
            'already_ids': already_ids,
            'batch_picks': [],  # list of User objects added by this run
        }
        (coi_apps if coi_ids else clear_apps).append(application)

    # Cumulative load — pre-existing Evaluations consume capacity too.
    load = {role.user_id: 0 for role in pool}
    for state in app_state.values():
        for ev_id in state['already_ids']:
            if ev_id in load:
                load[ev_id] += 1

    def _eligible(application, *, require_area_match):
        state = app_state[application.id]
        taken_for_app = state['already_ids'] | {u.id for u in state['batch_picks']}
        spec = getattr(application, 'specialization_area', None) or None
        out = []
        for role in pool:
            uid = role.user_id
            if uid in state['coi_ids']:
                continue
            if uid in taken_for_app:
                continue
            if load[uid] >= max_per_evaluator:
                continue
            if require_area_match:
                if not spec or not role.has_area(spec):
                    continue
            out.append(role.user)
        return out

    # Multi-pass allocator. Shuffle each pass so retries explore the space.
    for _pass in range(num_evaluators):
        random.shuffle(coi_apps)
        random.shuffle(clear_apps)
        for application in coi_apps + clear_apps:
            state = app_state[application.id]
            total_for_app = len(state['already_ids']) + len(state['batch_picks'])
            if total_for_app >= num_evaluators:
                continue

            candidates = _eligible(application, require_area_match=True)
            if not candidates:
                candidates = _eligible(application, require_area_match=False)
            if not candidates:
                continue

            pick = random.choice(candidates)
            state['batch_picks'].append(pick)
            load[pick.id] += 1

    # Materialize Evaluation rows, send notification emails, build the result rows.
    for application in eligible_applications:
        state = app_state[application.id]
        picks = state['batch_picks']
        for evaluator in picks:
            evaluation = Evaluation.objects.create(
                application=application,
                evaluator=evaluator,
            )
            context = {
                'evaluator_name': evaluator.get_full_name(),
                'application_code': application.code,
                'call_code': application.call.code,
                'deadline': application.call.evaluation_deadline,
                'evaluation_url': settings.SITE_URL + reverse(
                    'evaluations:evaluation_detail', kwargs={'pk': evaluation.id}
                ),
            }
            send_email_from_template(
                template_type='evaluation_assigned',
                recipient_email=evaluator.email,
                context_data=context,
                recipient_user_id=evaluator.id,
                related_application_id=application.id,
                related_evaluation_id=evaluation.id,
            )

        total_for_app = len(state['already_ids']) + len(picks)
        # excluded_count = pool members blocked by COI, the cap, or already-assigned.
        excluded_count = (
            len(state['coi_ids'])
            + sum(
                1 for role in pool
                if role.user_id not in state['coi_ids']
                and (load[role.user_id] >= max_per_evaluator
                     or role.user_id in state['already_ids'])
            )
        )
        warning = (
            f'Assigned {total_for_app} of {num_evaluators} requested evaluators'
            if total_for_app < num_evaluators else None
        )
        error = 'No eligible evaluators available' if total_for_app == 0 else None
        results['assignments'].append({
            'application_code': application.code,
            'application_id': application.id,
            'assigned_count': len(picks),
            'assigned_evaluators': [u.id for u in picks],
            'excluded_count': excluded_count,
            'warning': warning,
            'error': error,
        })
        if total_for_app < num_evaluators:
            results['unfilled'].append({
                'application_code': application.code,
                'application_id': application.id,
                'assigned': total_for_app,
                'requested': num_evaluators,
                'shortfall': num_evaluators - total_for_app,
            })

    # Transition call to 'closed' status if not already.
    if call.status == 'open':
        call.status = 'closed'
        call.save()

    # Apps that received at least one evaluator move to under_evaluation. Apps that got
    # zero stay pending_evaluation so the coordinator can retry or assign manually.
    for application in eligible_applications:
        state = app_state[application.id]
        total_for_app = len(state['already_ids']) + len(state['batch_picks'])
        if total_for_app >= 1 and application.status == 'pending_evaluation':
            application.status = 'under_evaluation'
            application.save()

    return results


@shared_task
def notify_coordinator_evaluations_complete(application_id, average_score):
    """
    Notify coordinator(s) when all evaluations for an application are complete.
    Triggered automatically when the last evaluation is submitted.

    Args:
        application_id: ID of the application
        average_score: Average score across all evaluations

    Returns:
        Number of notifications sent
    """
    from applications.models import Application
    from core.models import User, UserRole

    application = Application.objects.select_related('call', 'applicant').get(id=application_id)

    # Find node(s) involved in this application (have requested equipment)
    involved_node_ids = list(
        application.requested_access.values_list('equipment__node_id', flat=True).distinct()
    )

    # Only node coordinators receive the per-application evaluations-complete
    # email — they are the ones who need to take the next action (resolution).
    # ReDIB coordinators are covered by notify_coordinator_overdue_evaluations
    # (daily at 09:45) and coordinator_evaluations_locked once the window
    # closes, so they don't need a per-app notification here.
    nc_roles = UserRole.objects.filter(
        role='node_coordinator',
        node_id__in=involved_node_ids,
        is_active=True,
    ).values('user_id', 'node_id')

    # Build a map {user_id: [node_id, ...]} so each recipient gets a direct
    # link to the correct per-node resolution page (or their queue if they
    # coordinate multiple involved nodes).
    node_coord_map = {}
    for role in nc_roles:
        node_coord_map.setdefault(role['user_id'], []).append(role['node_id'])

    # Pre-build queue URL used when a node coord handles multiple involved nodes
    nc_queue_url = settings.SITE_URL + reverse('applications:node_resolution_queue')

    recipients = User.objects.filter(id__in=node_coord_map.keys())

    notifications_sent = 0
    for coordinator in recipients:
        # Check notification preferences
        if hasattr(coordinator, 'notification_preferences'):
            prefs = coordinator.notification_preferences
            if not prefs.notify_application_updates:
                continue

        # Link directly to the per-node review page if there's exactly one
        # involved node for this recipient; otherwise to the queue so they
        # can handle each node separately.
        node_ids = node_coord_map.get(coordinator.id, [])
        if len(node_ids) == 1:
            application_url = settings.SITE_URL + reverse(
                'applications:node_resolution_review',
                kwargs={'application_id': application.id, 'node_id': node_ids[0]},
            )
        else:
            application_url = nc_queue_url

        context = {
            'coordinator_name': coordinator.get_full_name(),
            'application_code': application.code,
            'applicant_name': application.applicant_name,
            'call_code': application.call.code,
            'average_score': round(average_score, 2),
            'num_evaluations': application.evaluations.count(),
            'application_url': application_url,
            'brief_description': application.brief_description,
        }

        send_email_from_template(
            template_type='evaluations_complete',
            recipient_email=coordinator.email,
            context_data=context,
            recipient_user_id=coordinator.id,
            related_application_id=application.id
        )

        notifications_sent += 1

    return notifications_sent
