"""
Celery tasks for the calls app.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)

# T-7 and T-2 before `call.submission_end`, in days.
DRAFT_NUDGE_CHECKPOINT_DAYS = (7, 2)


@shared_task
def send_draft_nudges():
    """
    Daily task (#35): nudge applicants who still hold a `draft` application
    on an `open` call as its submission deadline approaches.

    Fires at T-7 and T-2 before `call.submission_end`, each once, deduped
    per (application, offset) via EmailLog — the 24h dedupe window can't
    collide between the two offsets since they are 5 days apart. Stops at
    `submission_end`: an application still `draft` once the call has closed
    can no longer be submitted, so nudging about it is pure noise. Lives
    here rather than in `applications/tasks.py` because the anchor is
    `call.submission_end` (this file's own `check_call_deadlines` already
    owns that lifecycle boundary) and because `applications/tasks.py`
    belongs to `acceptance-repair` for the duration of this round.
    """
    from applications.models import Application
    from communications.models import EmailLog
    from communications.tasks import send_email_from_template
    from .models import Call

    now = timezone.now()
    nudges_sent = 0

    open_calls = Call.objects.filter(status='open')

    for call in open_calls:
        days_remaining = (call.submission_end.date() - now.date()).days
        if days_remaining not in DRAFT_NUDGE_CHECKPOINT_DAYS:
            continue

        drafts = Application.objects.filter(
            call=call, status='draft'
        ).select_related('applicant')

        for application in drafts:
            applicant = application.applicant
            recipient_email = application.applicant_email or applicant.email

            if hasattr(applicant, 'notification_preferences'):
                prefs = applicant.notification_preferences
                if not prefs.notify_reminders or not prefs.notify_application_updates:
                    continue

            already_sent = EmailLog.objects.filter(
                template__template_type='draft_nudge',
                recipient_email=recipient_email,
                related_application_id=application.id,
                sent_at__gte=now - timedelta(days=1),
            ).exists()
            if already_sent:
                continue

            send_email_from_template(
                template_type='draft_nudge',
                recipient_email=recipient_email,
                context_data={
                    'applicant_name': applicant.get_full_name(),
                    'application_code': application.code,
                    'call_code': call.code,
                    'call_title': call.title,
                    'days_remaining': days_remaining,
                    'submission_deadline': timezone.localtime(call.submission_end).strftime('%B %d, %Y'),
                    'application_url': settings.SITE_URL + reverse('applications:detail', kwargs={'pk': application.id}),
                },
                recipient_user_id=applicant.id,
                related_application_id=application.id,
            )
            nudges_sent += 1

    return f"Sent {nudges_sent} draft nudges"


@shared_task
def check_call_deadlines():
    """
    Move calls through the date-driven parts of their lifecycle.

    Runs daily via Celery Beat:
    - `announced` calls whose `submission_start` has arrived become `open`
      and the "Now Open" notification goes out.
    - `open` calls whose `submission_end` has passed become `closed`.

    Returns the number of calls closed (kept for backwards compatibility);
    the number opened is logged. Beat runs daily, so a view-level fallback in
    `calls/views.py` handles the same transitions between runs.
    """
    from .models import Call
    from .services import open_announced_calls

    open_announced_calls()

    now = timezone.now()
    expired_calls = Call.objects.filter(
        status='open',
        submission_end__lt=now,
    )

    count = expired_calls.count()
    if count > 0:
        codes = list(expired_calls.values_list('code', flat=True))
        expired_calls.update(status='closed')
        logger.info(
            "Auto-closed %d call(s) past submission deadline: %s",
            count, ', '.join(codes)
        )
    return count
