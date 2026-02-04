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
    Check for open calls whose submission deadline has passed and close them.

    Runs daily via Celery Beat. Any call with status='open' and
    submission_end in the past will be updated to status='closed'.
    """
    from .models import Call

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
