"""
Tests for closeout #29 (execution-phase completion reminders) and its
eval-reminders #49 reshape.

Cadence: first at 60 days after handoff_email_sent_at, then every 30 days,
plus one the day after call.execution_end; stops once is_completed=True —
unchanged by #49. The applicant is still notified one email per
application. The node coordinator side is now a per-recipient digest
across every application awaiting completion at their node(s) (#49),
deduped per recipient rather than per (recipient, application).
"""
from decimal import Decimal

import io
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from applications.models import Application, RequestedAccess
from applications.tasks import send_completion_reminders
from calls.models import Call
from communications.models import EmailLog, EmailTemplate
from core.models import Equipment, Node, Organization, UserRole
from core.test_utils import create_complete_user


class CompletionReminderTest(TestCase):
    def setUp(self):
        call_command('seed_email_templates', stdout=io.StringIO())
        self.org = Organization.objects.create(
            name='Closeout Completion Org', iso2='ES', country='Spain', organization_type='other'
        )
        self.node = Node.objects.create(
            code='CLOSEOUT-COMP-NODE', organization=self.org, location='Test City'
        )
        self.coordinator = create_complete_user(email='compcoord@closeout.test', organization=self.org)
        UserRole.objects.create(user=self.coordinator, role='node_coordinator', node=self.node, is_active=True)

        self.equipment = Equipment.objects.create(
            node=self.node, name='Completion Scanner', category='mri'
        )

        self.applicant = create_complete_user(email='compapplicant@closeout.test', organization=self.org)

        self.call = Call.objects.create(
            code='CLOSEOUT-COMP-2026',
            title='Closeout Completion Call',
            submission_start=timezone.now() - timedelta(days=120),
            submission_end=timezone.now() - timedelta(days=90),
            evaluation_deadline=timezone.now() - timedelta(days=80),
            execution_start=timezone.now() - timedelta(days=60),
            execution_end=timezone.now() + timedelta(days=60),
        )

    def _make_active_application(self, handoff_sent_at, is_completed=False):
        application = Application.objects.create(
            applicant=self.applicant,
            call=self.call,
            code=f'CLOSEOUT-COMP-2026-{handoff_sent_at.timestamp():.0f}',
            brief_description='Active grant',
            status='accepted',
            resolution='accepted',
            resolution_date=handoff_sent_at,
            accepted_by_applicant=True,
            accepted_at=handoff_sent_at,
            handoff_email_sent_at=handoff_sent_at,
            is_completed=is_completed,
        )
        RequestedAccess.objects.create(
            application=application,
            equipment=self.equipment,
            hours_requested=Decimal('10.0'),
            hours_approved=Decimal('10.0'),
        )
        return application

    def test_reminder_sent_at_sixty_day_checkpoint(self):
        app = self._make_active_application(timezone.now() - timedelta(days=60))

        result = send_completion_reminders()

        self.assertIn('2', result)  # applicant + coordinator
        self.assertTrue(
            EmailLog.objects.filter(
                template__template_type='completion_reminder',
                recipient_email=self.applicant.email,
                related_application_id=app.id,
            ).exists()
        )
        self.assertTrue(
            EmailLog.objects.filter(
                template__template_type='completion_reminder_coordinator',
                recipient_email=self.coordinator.email,
            ).exists()
        )

    def test_no_reminder_before_sixty_days(self):
        self._make_active_application(timezone.now() - timedelta(days=10))

        send_completion_reminders()

        self.assertEqual(EmailLog.objects.count(), 0)

    def test_no_reminder_once_completed(self):
        self._make_active_application(timezone.now() - timedelta(days=60), is_completed=True)

        send_completion_reminders()

        self.assertEqual(EmailLog.objects.count(), 0)

    def test_reminder_does_not_double_send_same_day(self):
        self._make_active_application(timezone.now() - timedelta(days=90))  # 60 + 30 checkpoint

        send_completion_reminders()
        first_count = EmailLog.objects.count()
        self.assertEqual(first_count, 2)

        send_completion_reminders()
        second_count = EmailLog.objects.count()
        self.assertEqual(second_count, first_count)

    def test_coordinator_covering_two_nodes_gets_one_email(self):
        """A coordinator managing two of this application's nodes must get
        one email listing both, not have the first node's EmailLog row
        suppress the second node's send."""
        other_org = Organization.objects.create(
            name='Second Node Host Org', iso2='ES', country='Spain', organization_type='other'
        )
        other_node = Node.objects.create(
            code='CLOSEOUT-COMP-NODE-2', organization=other_org, location='Test City 2'
        )
        UserRole.objects.create(user=self.coordinator, role='node_coordinator', node=other_node, is_active=True)
        other_equipment = Equipment.objects.create(node=other_node, name='Second Scanner', category='ct')

        app = self._make_active_application(timezone.now() - timedelta(days=60))
        RequestedAccess.objects.create(
            application=app, equipment=other_equipment,
            hours_requested=Decimal('5.0'), hours_approved=Decimal('5.0'),
        )

        send_completion_reminders()

        coordinator_emails = EmailLog.objects.filter(
            template__template_type='completion_reminder_coordinator',
            recipient_email=self.coordinator.email,
        )
        self.assertEqual(coordinator_emails.count(), 1)
        content = coordinator_emails.first().html_content
        self.assertIn(self.node.name, content)
        self.assertIn(other_node.name, content)

    def test_coordinator_digest_lists_every_application_awaiting_completion(self):
        """A coordinator with two separate active applications at their
        node gets ONE digest listing both, not one email per application —
        the #49 reshape."""
        app1 = self._make_active_application(timezone.now() - timedelta(days=60))
        app2 = self._make_active_application(timezone.now() - timedelta(days=90))  # also a 60/90 checkpoint

        send_completion_reminders()

        coordinator_emails = EmailLog.objects.filter(
            template__template_type='completion_reminder_coordinator',
            recipient_email=self.coordinator.email,
        )
        self.assertEqual(coordinator_emails.count(), 1)
        content = coordinator_emails.first().html_content
        self.assertIn(app1.code, content)
        self.assertIn(app2.code, content)

    def test_catch_up_after_missed_execution_end_day(self):
        """A handoff far outside the 60/90 cadence, but a few days past
        execution_end, still gets nudged — an exact 'day after' check alone
        would miss this if the beat task didn't run on that exact day."""
        self.call.execution_end = timezone.now() - timedelta(days=3)
        self.call.save()
        app = self._make_active_application(timezone.now() - timedelta(days=10))  # not a 60/90 checkpoint

        result = send_completion_reminders()

        self.assertIn('2', result)
        self.assertTrue(
            EmailLog.objects.filter(
                template__template_type='completion_reminder', related_application_id=app.id
            ).exists()
        )
        self.assertTrue(
            EmailLog.objects.filter(
                template__template_type='completion_reminder_coordinator',
                recipient_email=self.coordinator.email,
            ).exists()
        )

    def test_milestone_nudge_does_not_repeat_within_catch_up_window(self):
        """Once the milestone nudge has gone out (even on a day other than
        the literal 'day after'), a later run within the catch-up window
        must not send it again."""
        self.call.execution_end = timezone.now() - timedelta(days=3)
        self.call.save()
        app = self._make_active_application(timezone.now() - timedelta(days=10))

        completion_template = EmailTemplate.objects.get(template_type='completion_reminder')
        coordinator_template = EmailTemplate.objects.get(template_type='completion_reminder_coordinator')
        EmailLog.objects.create(
            template=completion_template, recipient_email=self.applicant.email,
            subject='x', status='sent',
            sent_at=self.call.execution_end + timedelta(days=1),
            related_application_id=app.id,
        )
        EmailLog.objects.create(
            template=coordinator_template, recipient_email=self.coordinator.email,
            subject='x', status='sent',
            sent_at=self.call.execution_end + timedelta(days=1),
        )

        send_completion_reminders()

        self.assertEqual(
            EmailLog.objects.filter(
                template__template_type='completion_reminder', related_application_id=app.id
            ).count(),
            1,
        )
        self.assertEqual(
            EmailLog.objects.filter(
                template__template_type='completion_reminder_coordinator',
                recipient_email=self.coordinator.email,
            ).count(),
            1,
        )

    def test_later_milestone_not_suppressed_by_earlier_apps_already_sent_nudge(self):
        """A coordinator covering two applications whose calls have
        different execution_end dates must still get a milestone nudge for
        the later-opening one, even though the earlier one's nudge already
        went out — the dedupe must key off the latest milestone_end, not
        the earliest."""
        call_a = Call.objects.create(
            code='CLOSEOUT-COMP-MILESTONE-A',
            title='Milestone Call A',
            submission_start=timezone.now() - timedelta(days=200),
            submission_end=timezone.now() - timedelta(days=170),
            evaluation_deadline=timezone.now() - timedelta(days=160),
            execution_start=timezone.now() - timedelta(days=150),
            execution_end=timezone.now() - timedelta(days=6),  # milestone opened 6 days ago
        )
        call_b = Call.objects.create(
            code='CLOSEOUT-COMP-MILESTONE-B',
            title='Milestone Call B',
            submission_start=timezone.now() - timedelta(days=200),
            submission_end=timezone.now() - timedelta(days=170),
            evaluation_deadline=timezone.now() - timedelta(days=160),
            execution_start=timezone.now() - timedelta(days=150),
            execution_end=timezone.now() - timedelta(days=1),  # milestone opened 1 day ago
        )

        def _make_app(call, code):
            app = Application.objects.create(
                applicant=self.applicant,
                call=call,
                code=code,
                brief_description='Active grant',
                status='accepted',
                resolution='accepted',
                accepted_by_applicant=True,
                accepted_at=timezone.now() - timedelta(days=10),  # not a 60/30 cadence day
                handoff_email_sent_at=timezone.now() - timedelta(days=10),
                is_completed=False,
            )
            RequestedAccess.objects.create(
                application=app, equipment=self.equipment,
                hours_requested=Decimal('10.0'), hours_approved=Decimal('10.0'),
            )
            return app

        app_a = _make_app(call_a, 'CLOSEOUT-COMP-MILESTONE-A-001')
        app_b = _make_app(call_b, 'CLOSEOUT-COMP-MILESTONE-B-001')

        # Simulate app_a's milestone nudge already sent, right after its
        # own window opened (5 days ago) — well before call_b's window
        # opened (1 day ago).
        coordinator_template = EmailTemplate.objects.get(template_type='completion_reminder_coordinator')
        EmailLog.objects.create(
            template=coordinator_template, recipient_email=self.coordinator.email,
            subject='x', status='sent',
            sent_at=call_a.execution_end + timedelta(days=1),
        )

        send_completion_reminders()

        coordinator_emails = EmailLog.objects.filter(
            template__template_type='completion_reminder_coordinator',
            recipient_email=self.coordinator.email,
            sent_at__gte=call_b.execution_end,
        )
        self.assertEqual(coordinator_emails.count(), 1)
        self.assertIn(app_b.code, coordinator_emails.first().html_content)
