"""
Celery tasks for application workflow automation.
Based on design document section 7.3 - Periodic Tasks.
"""

from celery import shared_task
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from .models import FeasibilityReview
from communications.tasks import send_email_from_template


def _reminder_is_due(anchor_dt, first_days, repeat_days, now):
    """True on the day `anchor_dt` hits a recurring reminder checkpoint.

    Checkpoints land at `first_days` after `anchor_dt`, then every
    `repeat_days` after that, indefinitely. Used so a daily beat task fires
    a reminder only on its cadence day, not on every day past the first
    threshold.
    """
    if not anchor_dt:
        return False
    elapsed = (now - anchor_dt).days
    if elapsed < first_days:
        return False
    return (elapsed - first_days) % repeat_days == 0


def _milestone_window(anchor_dt, now, catchup_days=7):
    """True in the week after `anchor_dt` has passed.

    Used for the one-time "day after execution_end" nudge. A plain
    exact-day equality check would permanently lose that nudge if the beat
    task doesn't run on that exact day; this widens it to a bounded
    catch-up window. Callers must still dedupe against EmailLog scoped to
    "since `anchor_dt`" (not just the last 24 hours) so the widened window
    doesn't re-send on every day it's open — see send_completion_reminders
    and send_waitlist_digest.
    """
    if not anchor_dt:
        return False
    elapsed = (now.date() - anchor_dt.date()).days
    return 1 <= elapsed <= catchup_days


@shared_task
def send_feasibility_reminders():
    """
    Daily task to send reminders for pending feasibility reviews.
    Runs at 9 AM daily (configured in redib/celery.py).

    Sends a reminder to every active node coordinator of the review's node
    (same audience as the initial feasibility_request fan-out) if:
    - Feasibility review status is 'pending'
    - More than 5 days have passed since application submission
    - No reminder already sent to that recipient for this application in
      the last 24 hours (so the daily task cannot double-send on a restart)
    """
    from core.models import UserRole
    from communications.models import EmailLog

    now = timezone.now()

    # Find pending reviews older than 5 days
    cutoff_date = now - timedelta(days=5)

    pending_reviews = FeasibilityReview.objects.filter(
        status='pending',
        application__submitted_at__lte=cutoff_date,
        reviewed_at__isnull=True
    ).select_related('application', 'node')

    reminders_sent = 0

    for review in pending_reviews:
        node_coordinators = UserRole.objects.filter(
            node=review.node,
            role='node_coordinator',
            is_active=True
        ).select_related('user').order_by('pk')

        for coord_role in node_coordinators:
            recipient = coord_role.user

            # Check if user wants reminders
            if hasattr(recipient, 'notification_preferences'):
                prefs = recipient.notification_preferences
                if not prefs.notify_reminders or not prefs.notify_feasibility_requests:
                    continue

            # Dedupe per (review, recipient): each recipient's last-sent
            # time is tracked independently, so one coordinator being
            # emailed does not suppress the others.
            already_sent = EmailLog.objects.filter(
                template__template_type='feasibility_reminder',
                recipient_email=recipient.email,
                related_application_id=review.application.id,
                sent_at__gte=now - timedelta(days=1),
            ).exists()
            if already_sent:
                continue

            context = {
                'reviewer_name': recipient.get_full_name(),
                'application_code': review.application.code,
                'application_title': review.application.brief_description,
                'node_name': review.node.name,
                'days_pending': (now - review.application.submitted_at).days,
                'deadline': timezone.localtime(review.application.call.evaluation_deadline).strftime('%B %d, %Y'),
            }

            send_email_from_template(
                template_type='feasibility_reminder',
                recipient_email=recipient.email,
                context_data=context,
                recipient_user_id=recipient.id,
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

        # Send notification email. Prefer the form-declared applicant_email
        # (the stated PI contact) over the submitting User's account email.
        recipient_email = application.applicant_email or application.applicant.email
        try:
            send_email_from_template(
                template_type=template_type,
                recipient_email=recipient_email,
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
        'call_name': application.call.title,
        'final_score': float(application.final_score) if application.final_score else 0.0,
        'resolution': application.get_resolution_display(),
        'hours_requested': float(hours_requested),
        'hours_approved': float(hours_approved),
        'resolution_comments': application.resolution_comments or '',
        'resolution_date': application.resolution_date,
        'node_decisions': node_decisions,
        'equipment_details': equipment_details,
    }

    # Add acceptance deadline and accept URL for applications with an
    # applicant response window. Both 'accepted' and 'pending' (waitlist)
    # give the applicant the same 10-day window.
    if application.resolution in ('accepted', 'pending') and application.acceptance_deadline:
        context['acceptance_deadline'] = application.acceptance_deadline
        context['days_to_respond'] = application.days_until_acceptance_deadline
        context['accept_url'] = f'{settings.SITE_URL}/applications/{application.id}/accept/'

    # Send notification email. Prefer the form-declared applicant_email
    # (the stated PI contact) over the submitting User's account email.
    recipient_email = application.applicant_email or application.applicant.email
    try:
        send_email_from_template(
            template_type=template_type,
            recipient_email=recipient_email,
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
    Daily task that reminds approved AND waitlisted applicants to respond
    before their acceptance deadline — both 'accepted' and 'pending'
    (waitlist) applications carry the same 10-day accept/decline window
    (see NodeResolutionService and promote_waitlisted_application).

    Per REDIB-02-PDA section 6.1.6: "Applicants have 10 days to accept or reject"

    Actions:
    - Reminder ladder at 7, 3 and 1 days before `acceptance_deadline`
      (equivalently days 3, 7 and 9 of a standard 10-day window). Three
      chances spread across the window, not two crammed into the last
      three days — the stalled-acceptance nag
      (`send_stalled_acceptance_reminders`) tells the node coordinator the
      applicant "was sent several reminders", and that has to be true.

    **This task never writes an Application.status.** It used to auto-expire
    on day 10; #53 removed that. Nothing expires unless a node coordinator
    clicks Expire (`applications.views.expire_stalled_application`). Once
    the deadline passes, this task goes quiet for that application and
    `send_stalled_acceptance_reminders` takes over, nagging the node
    coordinator instead of the applicant.

    Returns:
        str: Summary of reminders sent
    """
    from django.utils import timezone
    from datetime import timedelta
    from .models import Application

    now = timezone.now()

    # Reminder ladder: 7 / 3 / 1 days before the deadline.
    #
    # Anchored on `acceptance_deadline`, not `resolution_date`, so a
    # reinstated application (#18) — which gets a fresh deadline of now +
    # 10 days while `resolution_date` stays where it was — runs the ladder
    # again on its new window. The two anchors are otherwise equivalent,
    # since acceptance_deadline is resolution_date + 10 days.
    reminder_apps = Application.objects.filter(
        status__in=['accepted', 'pending'],
        accepted_by_applicant__isnull=True,  # Not yet responded
        acceptance_deadline__gte=now,        # Deadline not yet passed
        acceptance_deadline__lte=now + timedelta(days=8),
    ).select_related('applicant')

    from communications.models import EmailLog
    reminders_sent = 0
    today = timezone.localtime(now).date()

    for app in reminder_apps:
        # Whole-day granularity: the beat runs once a day, so compare
        # calendar dates rather than raw timedeltas, which would make the
        # checkpoint depend on the time of day the resolution was recorded.
        days_remaining = (timezone.localtime(app.acceptance_deadline).date() - today).days
        if days_remaining not in (7, 3, 1):
            continue

        applicant_email = app.applicant_email or app.applicant.email

        # Belt-and-braces against a same-day re-run (beat restart, manual
        # invocation): the ladder above already fires at most once per
        # checkpoint day.
        recent_reminder = EmailLog.objects.filter(
            template__template_type='acceptance_reminder',
            recipient_email=applicant_email,
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
            'deadline': timezone.localtime(app.acceptance_deadline).strftime('%B %d, %Y'),
            'days_remaining': days_remaining,
            'acceptance_url': f'{settings.SITE_URL}/applications/{app.id}/accept/',
            'is_waitlist': app.status == 'pending',
        }

        send_email_from_template(
            template_type='acceptance_reminder',
            recipient_email=applicant_email,
            context_data=context,
            recipient_user_id=app.applicant.id,
            related_application_id=app.id
        )

        reminders_sent += 1

    return f"Sent {reminders_sent} acceptance reminders"


def _notify_freed_capacity(application, reason):
    """Notify the node coordinator(s) of equipment hours freed when an
    accepted application's grant lapses (#30c: coordinator expiry or
    applicant decline). Only meaningful for a previously-'accepted'
    application — a waitlisted (pending) application holds no allocation
    to free.

    Both call sites live in `applications/views.py` — the manual expire
    action (#53 moved it there when auto-expire was deleted) and the
    applicant decline branch — and each guards on "already responded", so
    neither fires twice for one application. It dedupes per (recipient,
    application, day) via EmailLog anyway, matching every other
    notification helper in this module — cheap insurance against a
    double-submitted form or a retry.

    Args:
        application: Application instance (already transitioned away from
            'accepted' by the caller).
        reason: 'expired' or 'declined', for the email context.
    """
    from core.models import UserRole
    from communications.models import EmailLog

    now = timezone.now()
    freed_lines_by_node = {}
    for ra in application.requested_access.select_related('equipment__node'):
        node = ra.equipment.node
        hours = ra.hours_approved if ra.hours_approved is not None else ra.hours_requested
        freed_lines_by_node.setdefault(node, []).append({
            'equipment_name': ra.equipment.name,
            'hours_freed': float(hours),
        })

    application_url = f'{settings.SITE_URL}/applications/{application.id}/'

    for node, freed_lines in freed_lines_by_node.items():
        node_coordinators = UserRole.objects.filter(
            node=node,
            role='node_coordinator',
            is_active=True
        ).select_related('user')

        for coord_role in node_coordinators:
            recipient = coord_role.user
            if hasattr(recipient, 'notification_preferences'):
                prefs = recipient.notification_preferences
                if not prefs.notify_reminders or not prefs.notify_application_updates:
                    continue

            already_sent = EmailLog.objects.filter(
                template__template_type='freed_capacity_notice',
                recipient_email=recipient.email,
                related_application_id=application.id,
                sent_at__gte=now - timedelta(days=1),
            ).exists()
            if already_sent:
                continue

            context = {
                'coordinator_name': recipient.get_full_name(),
                'application_code': application.code,
                'applicant_name': application.applicant_name,
                'node_name': node.name,
                'reason': reason,
                'freed_lines': freed_lines,
                'application_url': application_url,
                'access_tracking_url': settings.SITE_URL + reverse('access:access_tracking'),
            }

            send_email_from_template(
                template_type='freed_capacity_notice',
                recipient_email=recipient.email,
                context_data=context,
                recipient_user_id=recipient.id,
                related_application_id=application.id,
            )


@shared_task
def send_waitlist_digest():
    """
    Daily task (#30a): per-node-coordinator digest of 'pending' (waitlist)
    applications the applicant has already accepted, still dangling with no
    promotion or close-out.

    Waitlisted applicants get no recurring reminder of their own — they
    cannot act on it. Only the node coordinator, who can promote
    (`promote_waitlisted_application`) or close out
    (`close_out_waitlisted_application`), is nagged.

    Cadence per application: first at 30 days after the applicant's
    acceptance (`accepted_at`), then every 30 days, plus one nudge in the
    week after `call.execution_end` (a bounded catch-up window, not an
    exact-day check, so a beat outage on the exact day does not lose the
    nudge permanently — see `_milestone_window` below). Dedupe per
    (recipient, day) via EmailLog for the recurring cadence, and per
    (recipient, since-execution_end) for the milestone nudge, so neither a
    same-day double run nor a within-the-week catch-up double-sends.
    """
    from core.models import UserRole
    from communications.models import EmailLog
    from .models import Application

    now = timezone.now()

    pending_apps = Application.objects.filter(
        status='pending',
        accepted_by_applicant=True,
    ).select_related('call').prefetch_related('requested_access__equipment__node')

    # Group due applications by recipient so a coordinator covering several
    # nodes gets one digest, not one email per node.
    due_by_recipient = {}

    for app in pending_apps:
        cadence_due = _reminder_is_due(app.accepted_at, 30, 30, now)
        milestone_due = _milestone_window(app.call.execution_end, now)
        if not cadence_due and not milestone_due:
            continue

        nodes = {ra.equipment.node for ra in app.requested_access.all()}
        for node in nodes:
            node_coordinators = UserRole.objects.filter(
                node=node, role='node_coordinator', is_active=True
            ).select_related('user')
            for coord_role in node_coordinators:
                recipient = coord_role.user
                entry = due_by_recipient.setdefault(
                    recipient.id,
                    {'user': recipient, 'apps_by_node': {}, 'cadence_due': False, 'milestone_ends': []},
                )
                entry['apps_by_node'].setdefault(node, []).append(app)
                if cadence_due:
                    entry['cadence_due'] = True
                if milestone_due:
                    entry['milestone_ends'].append(app.call.execution_end)

    digests_sent = 0
    access_tracking_url = settings.SITE_URL + reverse('access:access_tracking')

    for entry in due_by_recipient.values():
        recipient = entry['user']

        if hasattr(recipient, 'notification_preferences'):
            prefs = recipient.notification_preferences
            if not prefs.notify_reminders or not prefs.notify_application_updates:
                continue

        recently_sent = EmailLog.objects.filter(
            template__template_type='waitlist_digest',
            recipient_email=recipient.email,
            sent_at__gte=now - timedelta(days=1),
        ).exists()

        milestone_sent = False
        if entry['milestone_ends']:
            milestone_sent = EmailLog.objects.filter(
                template__template_type='waitlist_digest',
                recipient_email=recipient.email,
                sent_at__gte=min(entry['milestone_ends']),
            ).exists()

        should_send = (
            (entry['cadence_due'] and not recently_sent)
            or (entry['milestone_ends'] and not milestone_sent)
        )
        if not should_send:
            continue

        node_summaries = []
        for node, apps in entry['apps_by_node'].items():
            node_summaries.append({
                'node_name': node.name,
                'applications': [
                    {
                        'application_code': a.code,
                        'applicant_name': a.applicant_name,
                        'days_waiting': (now - a.accepted_at).days,
                    }
                    for a in apps
                ],
            })

        send_email_from_template(
            template_type='waitlist_digest',
            recipient_email=recipient.email,
            context_data={
                'coordinator_name': recipient.get_full_name(),
                'node_summaries': node_summaries,
                'access_tracking_url': access_tracking_url,
            },
            recipient_user_id=recipient.id,
        )
        digests_sent += 1

    return f"Sent {digests_sent} waitlist digest emails"


@shared_task
def send_completion_reminders():
    """
    Daily task (#29): nudge applicants and node coordinators to log actual
    equipment hours and mark an active grant's equipment lines done.

    Applies to applications with status='accepted', accepted_by_applicant
    True, handoff_email_sent_at set, and is_completed=False.

    Cadence per application: first at 60 days after `handoff_email_sent_at`,
    then every 30 days, plus one nudge in the week after `call.execution_end`
    (a bounded catch-up window — see `_milestone_window`); stops once
    `is_completed=True`. Dedupe per (recipient, application, day) via
    EmailLog for the recurring cadence, and per (recipient, application,
    since-execution_end) for the milestone nudge — checked separately for
    the applicant and for the node coordinators as a group (one recipient
    covering two nodes on the same application gets one email, not two;
    a shared EmailLog row for one node must not suppress the other).
    """
    from core.models import UserRole
    from communications.models import EmailLog
    from .models import Application

    now = timezone.now()

    active_apps = Application.objects.filter(
        status='accepted',
        accepted_by_applicant=True,
        handoff_email_sent_at__isnull=False,
        is_completed=False,
    ).select_related('call', 'applicant').prefetch_related('requested_access__equipment__node')

    reminders_sent = 0

    for app in active_apps:
        cadence_due = _reminder_is_due(app.handoff_email_sent_at, 60, 30, now)
        milestone_due = _milestone_window(app.call.execution_end, now)
        if not cadence_due and not milestone_due:
            continue

        application_url = f'{settings.SITE_URL}/applications/{app.id}/'

        def _should_send(template_type, recipient_email):
            recently_sent = EmailLog.objects.filter(
                template__template_type=template_type,
                recipient_email=recipient_email,
                related_application_id=app.id,
                sent_at__gte=now - timedelta(days=1),
            ).exists()
            milestone_sent = milestone_due and EmailLog.objects.filter(
                template__template_type=template_type,
                recipient_email=recipient_email,
                related_application_id=app.id,
                sent_at__gte=app.call.execution_end,
            ).exists()
            return (cadence_due and not recently_sent) or (milestone_due and not milestone_sent)

        # Applicant
        applicant = app.applicant
        applicant_email = app.applicant_email or applicant.email
        send_to_applicant = True
        if hasattr(applicant, 'notification_preferences'):
            prefs = applicant.notification_preferences
            if not prefs.notify_reminders or not prefs.notify_application_updates:
                send_to_applicant = False

        if send_to_applicant and _should_send('completion_reminder', applicant_email):
            send_email_from_template(
                template_type='completion_reminder',
                recipient_email=applicant_email,
                context_data={
                    'applicant_name': applicant.get_full_name(),
                    'application_code': app.code,
                    'call_code': app.call.code,
                    'application_url': application_url,
                },
                recipient_user_id=applicant.id,
                related_application_id=app.id,
            )
            reminders_sent += 1

        # Node coordinator(s) of every node with equipment on this
        # application — grouped by recipient so a coordinator covering
        # several of this application's nodes gets one email, not one per
        # node (a per-node EmailLog dedupe check would otherwise make the
        # first node's send suppress the rest).
        nodes = {ra.equipment.node for ra in app.requested_access.all()}
        coordinators_by_recipient = {}
        for node in nodes:
            node_coordinators = UserRole.objects.filter(
                node=node, role='node_coordinator', is_active=True
            ).select_related('user')
            for coord_role in node_coordinators:
                entry = coordinators_by_recipient.setdefault(
                    coord_role.user.id, {'user': coord_role.user, 'node_names': []}
                )
                entry['node_names'].append(node.name)

        for entry in coordinators_by_recipient.values():
            recipient = entry['user']
            if hasattr(recipient, 'notification_preferences'):
                prefs = recipient.notification_preferences
                if not prefs.notify_reminders or not prefs.notify_application_updates:
                    continue

            if not _should_send('completion_reminder_coordinator', recipient.email):
                continue

            send_email_from_template(
                template_type='completion_reminder_coordinator',
                recipient_email=recipient.email,
                context_data={
                    'coordinator_name': recipient.get_full_name(),
                    'application_code': app.code,
                    'applicant_name': app.applicant_name,
                    'call_code': app.call.code,
                    'node_name': ', '.join(sorted(entry['node_names'])),
                    'application_url': application_url,
                },
                recipient_user_id=recipient.id,
                related_application_id=app.id,
            )
            reminders_sent += 1

    return f"Sent {reminders_sent} completion reminders"


@shared_task
def send_stalled_acceptance_reminders():
    """
    Daily task (#53): nag the node coordinator(s) of every application
    stalled past its acceptance deadline with no applicant response.

    Replaces the auto-expire branch deleted from
    `process_acceptance_deadlines`. **This task writes no
    Application.status** — it computes and notifies, nothing more. A
    stalled application stays exactly where it is, indefinitely, until a
    node coordinator expires it or force-accepts it
    (`applications.views.expire_stalled_application` /
    `force_accept_stalled_application`).

    Audience: every active node_coordinator of every node with equipment
    on the application, with every active ReDIB `coordinator` cc'd — CC,
    not a second To, so everyone can Reply All and the ReDIB coordinator
    can see the nag is happening without being the one asked to act.

    Cadence: first 1 day after `acceptance_deadline`, then every 3 days,
    indefinitely. Deliberately uncapped — nagging the nodes is the point.

    The body carries "this is reminder #N", counted from EmailLog by
    **distinct send day**, not row: a node with two active coordinators
    produces two rows per send, and both people must see the same number.

    Returns:
        str: Summary of nags sent
    """
    from core.models import UserRole
    from communications.models import EmailLog
    from .models import Application

    now = timezone.now()

    stalled_apps = Application.objects.filter(
        status__in=['accepted', 'pending'],
        accepted_by_applicant__isnull=True,  # Nobody has responded
        acceptance_deadline__lt=now,         # Deadline has passed
    ).select_related('applicant', 'call').prefetch_related(
        'requested_access__equipment__node'
    )

    coordinator_emails = list(
        UserRole.objects.filter(role='coordinator', is_active=True)
        .exclude(user__email='')
        .values_list('user__email', flat=True)
        .distinct()
    )

    reminders_sent = 0

    for app in stalled_apps:
        if not _reminder_is_due(app.acceptance_deadline, 1, 3, now):
            continue

        # Reminder number counts distinct days this application has been
        # nagged about, so every recipient of this send sees the same N.
        reminder_number = EmailLog.objects.filter(
            template__template_type='stalled_acceptance_reminder',
            related_application_id=app.id,
        ).values('sent_at__date').distinct().count() + 1

        is_waitlist = app.status == 'pending'
        nodes = {ra.equipment.node for ra in app.requested_access.all()}
        node_name = ', '.join(sorted(node.name for node in nodes)) or '—'

        context_base = {
            'application_code': app.code,
            'call_code': app.call.code,
            'applicant_name': app.applicant_name or app.applicant.get_full_name(),
            'applicant_email': app.applicant_email or app.applicant.email,
            'node_name': node_name,
            'status_label': app.get_status_display(),
            'deadline': timezone.localtime(app.acceptance_deadline).strftime('%B %d, %Y'),
            'reminder_number': reminder_number,
            'is_waitlist': is_waitlist,
            'application_url': f'{settings.SITE_URL}/applications/{app.id}/',
            'expire_url': settings.SITE_URL + reverse(
                'applications:expire_stalled', args=[app.id]
            ),
            'force_accept_url': settings.SITE_URL + reverse(
                'applications:force_accept_stalled', args=[app.id]
            ),
        }

        for node in nodes:
            node_coordinators = UserRole.objects.filter(
                node=node, role='node_coordinator', is_active=True
            ).select_related('user')

            for coord_role in node_coordinators:
                recipient = coord_role.user
                if hasattr(recipient, 'notification_preferences'):
                    prefs = recipient.notification_preferences
                    if not prefs.notify_reminders or not prefs.notify_application_updates:
                        continue

                # Dedupe per (recipient, application, day) so a same-day
                # re-run cannot double-send, and so a coordinator covering
                # two nodes on one application is nagged once.
                already_sent = EmailLog.objects.filter(
                    template__template_type='stalled_acceptance_reminder',
                    recipient_email=recipient.email,
                    related_application_id=app.id,
                    sent_at__gte=now - timedelta(days=1),
                ).exists()
                if already_sent:
                    continue

                send_email_from_template(
                    template_type='stalled_acceptance_reminder',
                    recipient_email=recipient.email,
                    context_data={
                        **context_base,
                        'coordinator_name': recipient.get_full_name() or recipient.email,
                    },
                    recipient_user_id=recipient.id,
                    related_application_id=app.id,
                    cc_emails=coordinator_emails,
                )
                reminders_sent += 1

    return f"Sent {reminders_sent} stalled-acceptance reminders"
