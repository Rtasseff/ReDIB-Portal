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
        'task': 'applications.tasks.process_acceptance_deadlines',  # Updated for Phase 7
        'schedule': crontab(hour=10, minute=0),  # Daily at 10 AM
    },
    'send-publication-followups': {
        'task': 'access.tasks.send_publication_followups',
        'schedule': crontab(hour=10, minute=0, day_of_week=1),  # Mondays
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
