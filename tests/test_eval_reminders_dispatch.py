"""
Tests for eval-reminders #5: on-demand, per-call reminder dispatch.

A coordinator-only panel on the call detail page previews (GET) then sends
(POST) the same evaluator-digest and feasibility-reminder emails the daily
beat tasks send, scoped to one call and off the daily cadence/age cutoff.
"""
import io

from django.core.management import call_command
from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta

from applications.models import Application, FeasibilityReview
from calls.models import Call
from calls.services import preview_feasibility_reminders, send_feasibility_reminders_now
from communications.models import EmailLog, NotificationPreference
from core.models import Node, Organization, UserRole
from core.test_utils import create_complete_user
from evaluations.models import Evaluation
from evaluations.tasks import (
    preview_evaluation_reminders,
    send_evaluation_reminders,
    send_evaluation_reminders_now,
)


class EvaluatorDispatchTest(TestCase):
    def setUp(self):
        call_command('seed_email_templates', stdout=io.StringIO())
        self.org = Organization.objects.create(
            name='Dispatch Eval Org', iso2='ES', country='Spain', organization_type='other'
        )
        self.coordinator = create_complete_user(email='dispatch-redib@eval.test', organization=self.org)
        UserRole.objects.create(user=self.coordinator, role='coordinator', is_active=True)
        self.applicant = create_complete_user(email='dispatch-applicant@eval.test', organization=self.org)
        self.evaluator = create_complete_user(email='dispatch-evaluator@eval.test', organization=self.org)

        self.call = Call.objects.create(
            code='DISPATCH-EVAL-2026',
            title='Dispatch Eval Call',
            submission_start=timezone.now() - timedelta(days=60),
            submission_end=timezone.now() - timedelta(days=30),
            # 20 days out: not a T-7/-3/-1 checkpoint, so the daily task
            # would not fire today — the whole point of the manual button.
            evaluation_deadline=timezone.now() + timedelta(days=20),
            execution_start=timezone.now() + timedelta(days=30),
            execution_end=timezone.now() + timedelta(days=120),
        )
        self.application = Application.objects.create(
            applicant=self.applicant,
            call=self.call,
            code='DISPATCH-EVAL-2026-001',
            brief_description='Dispatch test application',
            status='under_evaluation',
        )
        Evaluation.objects.create(application=self.application, evaluator=self.evaluator)

        self.client = Client()
        self.client.force_login(self.coordinator)

    def test_preview_lists_recipient_as_will_send_off_cadence(self):
        rows = preview_evaluation_reminders(self.call)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['recipient_email'], self.evaluator.email)
        self.assertTrue(rows[0]['will_send'])

    def test_send_now_ignores_cadence_gate(self):
        sent, skipped = send_evaluation_reminders_now(self.call)
        self.assertEqual((sent, skipped), (1, 0))
        self.assertTrue(
            EmailLog.objects.filter(
                template__template_type='evaluation_reminder',
                recipient_email=self.evaluator.email,
            ).exists()
        )

    def test_second_send_same_day_is_skipped_by_default(self):
        send_evaluation_reminders_now(self.call)
        rows = preview_evaluation_reminders(self.call)
        self.assertFalse(rows[0]['will_send'])
        self.assertEqual(rows[0]['skip_reason'], 'already reminded today')

        sent, skipped = send_evaluation_reminders_now(self.call)
        self.assertEqual((sent, skipped), (0, 1))
        self.assertEqual(EmailLog.objects.count(), 1)

    def test_include_recent_override_sends_anyway(self):
        send_evaluation_reminders_now(self.call)
        sent, skipped = send_evaluation_reminders_now(self.call, include_recent=True)
        self.assertEqual((sent, skipped), (1, 0))
        self.assertEqual(EmailLog.objects.count(), 2)

    def test_override_never_bypasses_notification_preferences(self):
        NotificationPreference.objects.create(user=self.evaluator, notify_reminders=False)

        rows = preview_evaluation_reminders(self.call, include_recent=True)
        self.assertFalse(rows[0]['will_send'])
        self.assertEqual(rows[0]['skip_reason'], 'notifications disabled')

        sent, skipped = send_evaluation_reminders_now(self.call, include_recent=True)
        self.assertEqual((sent, skipped), (0, 1))

    def test_get_preview_page_renders(self):
        response = self.client.get(f'/calls/{self.call.pk}/remind/evaluators/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.evaluator.email)
        self.assertContains(response, 'Will send')

    def test_post_sends_and_redirects(self):
        response = self.client.post(f'/calls/{self.call.pk}/remind/evaluators/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(EmailLog.objects.count(), 1)

    def test_scoped_manual_dispatch_does_not_shadow_daily_digest_for_other_call(self):
        """An evaluator with pending evaluations on two different calls: a
        manual dispatch scoped to call A must not make the later, full
        daily digest (which covers both A and B) think the evaluator was
        already handled and skip call B's reminder entirely."""
        call_a = Call.objects.create(
            code='DISPATCH-EVAL-2026-A',
            title='Dispatch Eval Call A',
            submission_start=timezone.now() - timedelta(days=60),
            submission_end=timezone.now() - timedelta(days=30),
            evaluation_deadline=timezone.now() + timedelta(days=7),  # T-7 checkpoint
            execution_start=timezone.now() + timedelta(days=30),
            execution_end=timezone.now() + timedelta(days=120),
        )
        call_b = Call.objects.create(
            code='DISPATCH-EVAL-2026-B',
            title='Dispatch Eval Call B',
            submission_start=timezone.now() - timedelta(days=60),
            submission_end=timezone.now() - timedelta(days=30),
            evaluation_deadline=timezone.now() + timedelta(days=7),  # T-7 checkpoint
            execution_start=timezone.now() + timedelta(days=30),
            execution_end=timezone.now() + timedelta(days=120),
        )
        app_a = Application.objects.create(
            applicant=self.applicant, call=call_a, code='DISPATCH-EVAL-2026-A-001',
            brief_description='Call A application', status='under_evaluation',
        )
        app_b = Application.objects.create(
            applicant=self.applicant, call=call_b, code='DISPATCH-EVAL-2026-B-001',
            brief_description='Call B application', status='under_evaluation',
        )
        Evaluation.objects.create(application=app_a, evaluator=self.evaluator)
        Evaluation.objects.create(application=app_b, evaluator=self.evaluator)

        # Coordinator manually dispatches for call A only.
        sent, skipped = send_evaluation_reminders_now(call_a)
        self.assertEqual((sent, skipped), (1, 0))

        # The full daily digest, covering both calls, must still fire.
        result = send_evaluation_reminders()
        self.assertIn('1', result)

        logs = EmailLog.objects.filter(
            template__template_type='evaluation_reminder',
            recipient_email=self.evaluator.email,
        ).order_by('id')
        self.assertEqual(logs.count(), 2)
        self.assertNotIn(app_b.code, logs[0].html_content)  # scoped call-A-only send
        self.assertIn(app_a.code, logs[1].html_content)  # full daily digest covers both
        self.assertIn(app_b.code, logs[1].html_content)


class FeasibilityDispatchTest(TestCase):
    def setUp(self):
        call_command('seed_email_templates', stdout=io.StringIO())
        self.org = Organization.objects.create(
            name='Dispatch Feasibility Org', iso2='ES', country='Spain', organization_type='other'
        )
        self.node = Node.objects.create(
            code='DISPATCH-FEAS-NODE', organization=self.org, location='Test City'
        )
        self.coordinator = create_complete_user(email='dispatch-feas-redib@eval.test', organization=self.org)
        UserRole.objects.create(user=self.coordinator, role='coordinator', is_active=True)
        self.node_coord = create_complete_user(email='dispatch-feas-nodecoord@eval.test', organization=self.org)
        UserRole.objects.create(user=self.node_coord, role='node_coordinator', node=self.node, is_active=True)
        self.applicant = create_complete_user(email='dispatch-feas-applicant@eval.test', organization=self.org)

        self.call = Call.objects.create(
            code='DISPATCH-FEAS-2026',
            title='Dispatch Feasibility Call',
            submission_start=timezone.now() - timedelta(days=60),
            submission_end=timezone.now() - timedelta(days=30),
            evaluation_deadline=timezone.now() + timedelta(days=30),
            execution_start=timezone.now() + timedelta(days=40),
            execution_end=timezone.now() + timedelta(days=120),
        )
        self.application = Application.objects.create(
            applicant=self.applicant,
            call=self.call,
            code='DISPATCH-FEAS-2026-001',
            brief_description='Dispatch feasibility application',
            status='under_feasibility_review',
            # Only 1 day old: the daily task's 5-day cutoff would not fire
            # today, but the manual dispatch ignores that cutoff.
            submitted_at=timezone.now() - timedelta(days=1),
        )
        self.review = FeasibilityReview.objects.create(
            application=self.application,
            node=self.node,
            reviewer=self.node_coord,
            status='pending',
        )

        self.client = Client()
        self.client.force_login(self.coordinator)

    def test_preview_ignores_five_day_age_cutoff(self):
        rows = preview_feasibility_reminders(self.call)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['recipient_email'], self.node_coord.email)
        self.assertTrue(rows[0]['will_send'])

    def test_send_now_produces_feasibility_reminder_email(self):
        sent, skipped = send_feasibility_reminders_now(self.call)
        self.assertEqual((sent, skipped), (1, 0))
        self.assertTrue(
            EmailLog.objects.filter(
                template__template_type='feasibility_reminder',
                recipient_email=self.node_coord.email,
                related_application_id=self.application.id,
            ).exists()
        )

    def test_second_send_same_day_is_skipped_by_default(self):
        send_feasibility_reminders_now(self.call)
        sent, skipped = send_feasibility_reminders_now(self.call)
        self.assertEqual((sent, skipped), (0, 1))

    def test_include_recent_override_sends_anyway(self):
        send_feasibility_reminders_now(self.call)
        sent, skipped = send_feasibility_reminders_now(self.call, include_recent=True)
        self.assertEqual((sent, skipped), (1, 0))

    def test_get_preview_page_renders(self):
        response = self.client.get(f'/calls/{self.call.pk}/remind/feasibility/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.node_coord.email)
        self.assertContains(response, 'Will send')

    def test_post_sends_and_redirects(self):
        response = self.client.post(f'/calls/{self.call.pk}/remind/feasibility/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(EmailLog.objects.count(), 1)

    def test_no_rows_when_nothing_pending(self):
        self.review.status = 'approved'
        self.review.reviewed_at = timezone.now()
        self.review.save()

        response = self.client.get(f'/calls/{self.call.pk}/remind/feasibility/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nobody is currently due a reminder')

    def test_coordinator_covering_two_nodes_on_same_application_gets_both_reminders(self):
        """A single application can have a pending FeasibilityReview at more
        than one node; a coordinator covering both must get a reminder for
        each, not have the first node's freshly-sent EmailLog make the
        second node's review look 'already reminded' in the same run."""
        other_node = Node.objects.create(
            code='DISPATCH-FEAS-NODE-2', organization=self.org, location='Test City 2'
        )
        UserRole.objects.create(user=self.node_coord, role='node_coordinator', node=other_node, is_active=True)
        other_review = FeasibilityReview.objects.create(
            application=self.application,
            node=other_node,
            reviewer=self.node_coord,
            status='pending',
        )

        sent, skipped = send_feasibility_reminders_now(self.call)

        self.assertEqual((sent, skipped), (2, 0))
        self.assertEqual(
            EmailLog.objects.filter(
                template__template_type='feasibility_reminder',
                recipient_email=self.node_coord.email,
            ).count(),
            2,
        )
