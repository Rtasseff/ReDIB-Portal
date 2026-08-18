"""
Service helpers for the calls app.

Email fan-out lives here so the request cycle (`calls/views.py`) and the
Celery beat task (`calls/tasks.py`) share one implementation.
"""
import logging

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)


def build_call_url(call, request=None):
    """Absolute URL of the public call page.

    Uses the request when there is one (dev hosts, alternate ports) and falls
    back to `SITE_URL` for background tasks.
    """
    path = reverse('calls:public_detail', kwargs={'pk': call.pk})
    if request is not None:
        return request.build_absolute_uri(path)
    return f"{settings.SITE_URL.rstrip('/')}{path}"


def notify_call_audience(call, template_type, call_url):
    """Queue `template_type` to every user who opted in to call notifications.

    Used for both `call_announced` (call becomes visible) and `call_published`
    (call actually opens). Returns the number of recipients queued. Callers
    are responsible for surviving an unavailable broker.

    Returns 0 without sending anything while
    `settings.CALL_ANNOUNCEMENT_EMAILS_ENABLED` is False, which is the
    default — see backlog #41 for what has to be true before it goes back on.
    """
    from communications.tasks import send_email_from_template
    from core.models import User

    recipients = list(
        User.objects.filter(receive_call_notifications=True, is_active=True)
        .values_list('email', 'id')
    )

    if not settings.CALL_ANNOUNCEMENT_EMAILS_ENABLED:
        logger.info(
            "Call announcement emails are off (CALL_ANNOUNCEMENT_EMAILS_ENABLED"
            "=False): skipped %s for call %s — %d recipient(s) not mailed.",
            template_type, call.code, len(recipients),
        )
        return 0

    # Dates are pre-formatted: Celery's JSON serializer turns datetimes into
    # raw ISO strings, so passing the objects through renders differently in
    # eager (dev) and brokered (prod) execution.
    context_data = {
        'call_code': call.code,
        'call_title': call.title,
        'submission_start': timezone.localtime(call.submission_start).strftime('%B %d, %Y'),
        'submission_end': timezone.localtime(call.submission_end).strftime('%B %d, %Y'),
        'call_url': call_url,
    }

    for email, user_id in recipients:
        send_email_from_template.delay(
            template_type=template_type,
            recipient_email=email,
            context_data=context_data,
            recipient_user_id=user_id,
        )

    return len(recipients)


def open_announced_calls(request=None, send_emails=True):
    """Promote announced calls whose submission window has started.

    Returns (codes_opened, emails_sent). When `send_emails` is False the
    calls are still opened — the DB state is what matters — and the "Now
    Open" notification is simply skipped (used by the view-level fallback
    when the broker is down).
    """
    from .models import Call

    now = timezone.now()
    # Only calls whose window is *currently* open. An announced call whose end
    # date has already passed (e.g. status edited by hand) must not fire the
    # 'Now Open' email; _auto_close_expired_calls / check_call_deadlines close it.
    due = list(Call.objects.filter(
        status='announced', submission_start__lte=now, submission_end__gt=now,
    ))
    if not due:
        return [], 0

    codes = []
    emails_sent = 0
    for call in due:
        call.status = 'open'
        if call.published_at is None:
            call.published_at = now
        call.save(update_fields=['status', 'published_at', 'updated_at'])
        codes.append(call.code)

        if not send_emails:
            continue
        try:
            emails_sent += notify_call_audience(
                call, 'call_published', build_call_url(call, request)
            )
        except Exception as exc:
            logger.warning(
                "Auto-open notification failed for call %s (Celery unavailable?): %s",
                call.code, exc,
            )

    logger.info("Auto-opened %d announced call(s): %s", len(codes), ', '.join(codes))
    return codes, emails_sent


def send_consult_request_emails(consult, call_url, consult_requests_url):
    """Notify every active node coordinator of each node in `consult`.

    Deliberately emails *all* active coordinators of a node, not just the
    first one. Returns (sent_count, nodes_without_coordinator). Each send is
    wrapped individually so one bad address doesn't strand the rest; the
    caller wraps the whole call again to survive an unavailable broker.
    """
    from communications.tasks import send_email_from_template
    from core.models import UserRole

    sent = 0
    nodes_without_coord = []

    for node, equipment_items in consult.equipment_by_node().items():
        equipment_list = ', '.join(item.name for item in equipment_items)
        coordinators = list(
            UserRole.objects
            .filter(node=node, role='node_coordinator', is_active=True)
            .select_related('user')
        )
        if not coordinators:
            nodes_without_coord.append(node)
            logger.warning(
                "Consult request %s: node %s has no active coordinator",
                consult.pk, node.code,
            )
            continue

        for role in coordinators:
            try:
                send_email_from_template.delay(
                    template_type='equipment_consult_request',
                    recipient_email=role.user.email,
                    context_data={
                        'coordinator_name': role.user.get_full_name() or role.user.email,
                        'requester_name': consult.name,
                        'requester_email': consult.email,
                        'requester_phone': consult.phone,
                        'requester_organization': consult.organization,
                        'call_code': consult.call.code,
                        'call_title': consult.call.title,
                        'call_status': consult.call.get_status_display(),
                        'node_name': node.name,
                        'equipment_list': equipment_list,
                        'message': consult.message,
                        'submission_start': timezone.localtime(consult.call.submission_start).strftime('%B %d, %Y'),
                        'submission_end': timezone.localtime(consult.call.submission_end).strftime('%B %d, %Y'),
                        'call_url': call_url,
                        'consult_requests_url': consult_requests_url,
                    },
                    recipient_user_id=role.user.id,
                )
                sent += 1
            except Exception:
                logger.exception(
                    "Consult request %s: email failed for node %s coordinator %s",
                    consult.pk, node.code, role.user.email,
                )

    if nodes_without_coord:
        _alert_redib_coordinators(
            consult, nodes_without_coord, call_url, consult_requests_url
        )

    return sent, nodes_without_coord


def _alert_redib_coordinators(consult, nodes, call_url, consult_requests_url):
    """Fall back to the ReDIB coordinator(s) for nodes with no coordinator."""
    from communications.tasks import send_email_from_template
    from core.models import UserRole

    grouped = consult.equipment_by_node()
    node_names = ', '.join(node.name for node in nodes)
    equipment_list = ', '.join(
        item.name for node in nodes for item in grouped.get(node, [])
    )

    for role in UserRole.objects.filter(
        role='coordinator', is_active=True
    ).select_related('user'):
        try:
            send_email_from_template.delay(
                template_type='equipment_consult_request',
                recipient_email=role.user.email,
                context_data={
                    'coordinator_name': role.user.get_full_name() or role.user.email,
                    'requester_name': consult.name,
                    'requester_email': consult.email,
                    'requester_phone': consult.phone,
                    'requester_organization': consult.organization,
                    'call_code': consult.call.code,
                    'call_title': consult.call.title,
                    'call_status': consult.call.get_status_display(),
                    'node_name': node_names,
                    'equipment_list': equipment_list,
                    'message': consult.message,
                    'submission_start': timezone.localtime(consult.call.submission_start).strftime('%B %d, %Y'),
                    'submission_end': timezone.localtime(consult.call.submission_end).strftime('%B %d, %Y'),
                    'call_url': call_url,
                    'consult_requests_url': consult_requests_url,
                    'no_node_coordinator': True,
                },
                recipient_user_id=role.user.id,
            )
        except Exception:
            logger.exception(
                "Consult request %s: fallback email to ReDIB coordinator %s failed",
                consult.pk, role.user.email,
            )


def send_consult_confirmation_email(consult, call_url):
    """Confirm receipt to the requester. Returns True when queued."""
    from communications.tasks import send_email_from_template

    node_names = ', '.join(node.name for node in consult.equipment_by_node())
    equipment_list = ', '.join(
        f"{item.name} ({item.node.organization.short_name or item.node.name})"
        for items in consult.equipment_by_node().values()
        for item in items
    )
    try:
        send_email_from_template.delay(
            template_type='equipment_consult_confirmation',
            recipient_email=consult.email,
            context_data={
                'requester_name': consult.name,
                'call_code': consult.call.code,
                'call_title': consult.call.title,
                'node_names': node_names,
                'equipment_list': equipment_list,
                'message': consult.message,
                'submission_start': timezone.localtime(consult.call.submission_start).strftime('%B %d, %Y'),
                'submission_end': timezone.localtime(consult.call.submission_end).strftime('%B %d, %Y'),
                'call_url': call_url,
                'contact_email': settings.CONTACT_EMAIL,
            },
            recipient_user_id=consult.user_id,
        )
        return True
    except Exception:
        logger.exception(
            "Consult request %s: confirmation email to %s failed",
            consult.pk, consult.email,
        )
        return False
