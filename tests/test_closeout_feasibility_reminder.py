"""
Tests for closeout #45: send_feasibility_reminders dedupe + fan-out.

Covers:
- Reminder fans out to every active node coordinator of the review's node
  (not just the review's fixed `reviewer`).
- Running the task twice does not double-send (per-recipient EmailLog dedupe).
"""
import io
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from applications.models import Application, FeasibilityReview
from applications.tasks import send_feasibility_reminders
from calls.models import Call
from communications.models import EmailLog
from core.models import Node, Organization, UserRole
from core.test_utils import create_complete_user


class FeasibilityReminderFanOutTest(TestCase):
    def setUp(self):
        call_command('seed_email_templates', stdout=io.StringIO())
        self.org = Organization.objects.create(
            name='Closeout Test Org', iso2='ES', country='Spain', organization_type='other'
        )
        self.node = Node.objects.create(
            code='CLOSEOUT-NODE', organization=self.org, location='Test City'
        )
        self.coord1 = create_complete_user(email='coord1@closeout.test', organization=self.org)
        self.coord2 = create_complete_user(email='coord2@closeout.test', organization=self.org)
        for coord in (self.coord1, self.coord2):
            UserRole.objects.create(user=coord, role='node_coordinator', node=self.node, is_active=True)

        self.applicant = create_complete_user(email='applicant@closeout.test', organization=self.org)

        self.call = Call.objects.create(
            code='CLOSEOUT-2026',
            title='Closeout Test Call',
            submission_start=timezone.now() - timedelta(days=60),
            submission_end=timezone.now() - timedelta(days=30),
            evaluation_deadline=timezone.now() + timedelta(days=30),
            execution_start=timezone.now() + timedelta(days=40),
            execution_end=timezone.now() + timedelta(days=100),
        )

        self.application = Application.objects.create(
            applicant=self.applicant,
            call=self.call,
            code='CLOSEOUT-2026-001',
            brief_description='Test application',
            status='under_feasibility_review',
            submitted_at=timezone.now() - timedelta(days=6),  # older than the 5-day cutoff
        )

        self.review = FeasibilityReview.objects.create(
            application=self.application,
            node=self.node,
            reviewer=self.coord1,
            status='pending',
        )

    def test_reminder_fans_out_to_every_active_node_coordinator(self):
        result = send_feasibility_reminders()

        self.assertIn('2', result)
        sent_emails = set(
            EmailLog.objects.filter(
                template__template_type='feasibility_reminder',
                related_application_id=self.application.id,
            ).values_list('recipient_email', flat=True)
        )
        self.assertEqual(sent_emails, {self.coord1.email, self.coord2.email})

    def test_reminder_does_not_double_send_same_day(self):
        send_feasibility_reminders()
        first_count = EmailLog.objects.filter(template__template_type='feasibility_reminder').count()
        self.assertEqual(first_count, 2)

        send_feasibility_reminders()
        second_count = EmailLog.objects.filter(template__template_type='feasibility_reminder').count()
        self.assertEqual(second_count, first_count)

    def test_inactive_node_coordinator_not_emailed(self):
        UserRole.objects.filter(user=self.coord2, node=self.node).update(is_active=False)

        send_feasibility_reminders()

        sent_emails = set(
            EmailLog.objects.filter(
                template__template_type='feasibility_reminder',
            ).values_list('recipient_email', flat=True)
        )
        self.assertEqual(sent_emails, {self.coord1.email})

    def test_no_reminder_before_five_day_cutoff(self):
        self.application.submitted_at = timezone.now() - timedelta(days=2)
        self.application.save(update_fields=['submitted_at'])

        send_feasibility_reminders()

        self.assertEqual(
            EmailLog.objects.filter(template__template_type='feasibility_reminder').count(), 0
        )
