"""
Send a one-off plain-text operational alert via the portal's SMTP config.

Intended for shell scripts (backups, health checks, cron jobs) that need to
notify an operator when something goes wrong. Uses django.core.mail.send_mail
synchronously — NOT the Celery task — so:

  * alerts still go out if Redis/Celery is down
  * SMTP failures surface as a non-zero exit code to the caller
  * no database template is required

Usage:
    python manage.py send_ops_alert \\
        --recipient coordinator@redib.net \\
        --subject "[ReDIB backup] FAILED on host01" \\
        --body "Backup script exited 1 at ..."

Sender defaults to settings.DEFAULT_FROM_EMAIL (noreply@redib.net).
"""

from django.core.management.base import BaseCommand
from django.core.mail import send_mail


class Command(BaseCommand):
    help = "Send a plain-text ops alert email via the portal's SMTP config."

    def add_arguments(self, parser):
        parser.add_argument('--recipient', required=True,
                            help='Single email address to notify.')
        parser.add_argument('--subject', required=True)
        parser.add_argument('--body', required=True)

    def handle(self, *args, **opts):
        send_mail(
            subject=opts['subject'],
            message=opts['body'],
            from_email=None,  # DEFAULT_FROM_EMAIL
            recipient_list=[opts['recipient']],
            fail_silently=False,
        )
        self.stdout.write(self.style.SUCCESS(
            f"Alert sent to {opts['recipient']}"
        ))
