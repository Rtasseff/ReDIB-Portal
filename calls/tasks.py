"""
Celery tasks for the calls app.
"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


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
