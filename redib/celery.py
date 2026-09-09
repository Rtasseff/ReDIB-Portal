"""
Celery configuration for ReDIB COA portal.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redib.settings')

app = Celery('redib')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    'check-feasibility-reminders': {
        'task': 'applications.tasks.send_feasibility_reminders',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
    },
    'check-evaluation-reminders': {
        'task': 'evaluations.tasks.send_evaluation_reminders',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
    },
    'check-acceptance-deadlines': {
        # Reminder ladder to the applicant only — #53 removed the
        # auto-expire branch; this task writes no Application.status.
        'task': 'applications.tasks.process_acceptance_deadlines',
        'schedule': crontab(hour=10, minute=0),  # Daily at 10 AM
    },
    'send-stalled-acceptance-reminders': {
        # #53: nags the node coordinator(s) once the deadline has passed,
        # ReDIB coordinator cc'd. Computes and notifies; never transitions.
        'task': 'applications.tasks.send_stalled_acceptance_reminders',
        'schedule': crontab(hour=10, minute=15),  # Daily at 10:15 AM
    },
    'send-publication-followups': {
        'task': 'access.tasks.send_publication_followups',
        'schedule': crontab(hour=10, minute=0, day_of_week=1),  # Mondays
    },
    'check-call-deadlines': {
        'task': 'calls.tasks.check_call_deadlines',
        'schedule': crontab(hour=0, minute=15),  # Daily at 00:15
    },
    'send-draft-nudges': {
        'task': 'calls.tasks.send_draft_nudges',
        'schedule': crontab(hour=8, minute=30),  # Daily at 8:30 AM
    },
    'notify-coordinator-overdue-evaluations': {
        'task': 'evaluations.tasks.notify_coordinator_overdue_evaluations',
        'schedule': crontab(hour=9, minute=45),  # Daily at 9:45 AM
    },
    'send-waitlist-digest': {
        'task': 'applications.tasks.send_waitlist_digest',
        'schedule': crontab(hour=8, minute=0),  # Daily at 8 AM
    },
    # PAUSED 2026-09-09 (prod): the completion reminders are chasing people
    # against REDIB-2601's execution_end of 2026-10-30, which isn't a date the
    # running projects can actually hit, and the complaints are piling up. The
    # 15 open applications were handed off 63-92 days apart, so a different one
    # crosses its 60/30 checkpoint nearly every day and node coordinators get
    # the digest every second morning (the per-recipient dedupe is only 24h).
    # Commenting out the beat entry silences both the applicant email
    # ('completion_reminder') and the coordinator digest
    # ('completion_reminder_coordinator') without touching the task, which is
    # still correct and still covered by tests.
    #
    # Nothing queues up while this is off: _reminder_is_due fires only on exact
    # cadence days, so re-enabling resumes at the next checkpoint rather than
    # flushing a backlog. The one-shot post-execution_end nudge (2026-10-31 to
    # 11-06) is skipped entirely while paused.
    #
    # Restore by uncommenting once the deadline policy is fixed and the
    # cadence/dedupe rework lands. See backlog #80.
    # 'send-completion-reminders': {
    #     'task': 'applications.tasks.send_completion_reminders',
    #     'schedule': crontab(hour=8, minute=15),  # Daily at 8:15 AM
    # },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
