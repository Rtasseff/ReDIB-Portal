"""
Tests for eval-reminders #32: per-evaluator evaluation reminder digest.

Cadence relative to `call.evaluation_deadline`: T-7 / T-3 / T-1 pre-deadline,
then every 2 days post-deadline (day 0, 2, 4, 6) through the lockout at
deadline + GRACE_PERIOD_DAYS (see `evaluations.utils.is_evaluation_locked`).
One email per evaluator per send, listing every pending evaluation they
hold — not one email per evaluation. Folds in the former
`notify_overdue_evaluators` task.
"""
import io

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from applications.models import Application
from calls.models import Call
from communications.models import EmailLog, EmailTemplate, NotificationPreference
from core.models import Organization
from core.test_utils import create_complete_user
from evaluations.models import Evaluation
from evaluations.tasks import send_evaluation_reminders
from evaluations.utils import GRACE_PERIOD_DAYS


class EvaluationReminderDigestTest(TestCase):
    def setUp(self):
        call_command('seed_email_templates', stdout=io.StringIO())
        self.org = Organization.objects.create(
            name='Eval Digest Org', iso2='ES', country='Spain', organization_type='other'
        )
        self.applicant = create_complete_user(email='digest-applicant@eval.test', organization=self.org)
        self.evaluator = create_complete_user(email='digest-evaluator@eval.test', organization=self.org)

    def _make_call(self, deadline):
        return Call.objects.create(
            code=f'EVAL-DIGEST-{deadline.timestamp():.0f}',
            title='Evaluation Digest Call',
            submission_start=timezone.now() - timedelta(days=60),
            submission_end=timezone.now() - timedelta(days=30),
            evaluation_deadline=deadline,
            execution_start=timezone.now() + timedelta(days=30),
            execution_end=timezone.now() + timedelta(days=120),
        )

    def _make_application(self, call, code):
        return Application.objects.create(
            applicant=self.applicant,
            call=call,
            code=code,
            brief_description='Digest test application',
            status='under_evaluation',
        )

    def _assign(self, application):
        return Evaluation.objects.create(application=application, evaluator=self.evaluator)

    def test_multiple_pending_evaluations_produce_one_email_at_t_minus_seven(self):
        call = self._make_call(timezone.now() + timedelta(days=7))
        for i in range(6):
            self._assign(self._make_application(call, f'EVAL-DIGEST-T7-{i}'))

        result = send_evaluation_reminders()

        self.assertIn('1', result)
        logs = EmailLog.objects.filter(
            template__template_type='evaluation_reminder',
            recipient_email=self.evaluator.email,
        )
        self.assertEqual(logs.count(), 1)
        content = logs.first().html_content
        for i in range(6):
            self.assertIn(f'EVAL-DIGEST-T7-{i}', content)

    def test_no_digest_between_checkpoints(self):
        call = self._make_call(timezone.now() + timedelta(days=5))
        self._assign(self._make_application(call, 'EVAL-DIGEST-T5'))

        send_evaluation_reminders()

        self.assertEqual(EmailLog.objects.count(), 0)

    def test_digest_does_not_double_send_same_day(self):
        call = self._make_call(timezone.now() + timedelta(days=3))
        self._assign(self._make_application(call, 'EVAL-DIGEST-T3'))

        send_evaluation_reminders()
        first_count = EmailLog.objects.count()
        self.assertEqual(first_count, 1)

        send_evaluation_reminders()
        self.assertEqual(EmailLog.objects.count(), first_count)

    def test_overdue_evaluation_sends_overdue_template(self):
        call = self._make_call(timezone.now() - timedelta(days=2))
        self._assign(self._make_application(call, 'EVAL-DIGEST-OVERDUE'))

        result = send_evaluation_reminders()

        self.assertIn('1', result)
        self.assertTrue(
            EmailLog.objects.filter(
                template__template_type='evaluation_overdue',
                recipient_email=self.evaluator.email,
            ).exists()
        )
        self.assertFalse(
            EmailLog.objects.filter(template__template_type='evaluation_reminder').exists()
        )

    def test_no_digest_past_lockout(self):
        call = self._make_call(timezone.now() - timedelta(days=GRACE_PERIOD_DAYS + 1))
        self._assign(self._make_application(call, 'EVAL-DIGEST-LOCKED'))

        send_evaluation_reminders()

        self.assertEqual(EmailLog.objects.count(), 0)

    def test_mixed_upcoming_and_overdue_send_one_overdue_digest_listing_both(self):
        """An evaluator holding one overdue evaluation and one upcoming
        (non-checkpoint) evaluation still gets exactly one email — the
        overdue digest — and it lists both, not just the one that
        triggered the send."""
        overdue_call = self._make_call(timezone.now() - timedelta(days=2))
        upcoming_call = self._make_call(timezone.now() + timedelta(days=20))
        self._assign(self._make_application(overdue_call, 'EVAL-DIGEST-MIX-OVERDUE'))
        self._assign(self._make_application(upcoming_call, 'EVAL-DIGEST-MIX-UPCOMING'))

        send_evaluation_reminders()

        logs = EmailLog.objects.filter(recipient_email=self.evaluator.email)
        self.assertEqual(logs.count(), 1)
        log = logs.first()
        self.assertEqual(log.template.template_type, 'evaluation_overdue')
        self.assertIn('EVAL-DIGEST-MIX-OVERDUE', log.html_content)
        self.assertIn('EVAL-DIGEST-MIX-UPCOMING', log.html_content)

    def test_completed_evaluation_excluded(self):
        call = self._make_call(timezone.now() + timedelta(days=7))
        evaluation = self._assign(self._make_application(call, 'EVAL-DIGEST-DONE'))
        evaluation.completed_at = timezone.now()
        evaluation.save()

        send_evaluation_reminders()

        self.assertEqual(EmailLog.objects.count(), 0)

    def test_notification_preferences_skip_whole_digest(self):
        call = self._make_call(timezone.now() + timedelta(days=7))
        self._assign(self._make_application(call, 'EVAL-DIGEST-OPTOUT'))
        NotificationPreference.objects.create(user=self.evaluator, notify_reminders=False)

        send_evaluation_reminders()

        self.assertEqual(EmailLog.objects.count(), 0)

    def test_two_evaluators_each_get_their_own_digest(self):
        call = self._make_call(timezone.now() + timedelta(days=1))
        other_evaluator = create_complete_user(email='digest-evaluator-2@eval.test', organization=self.org)
        app_a = self._make_application(call, 'EVAL-DIGEST-A')
        app_b = self._make_application(call, 'EVAL-DIGEST-B')
        Evaluation.objects.create(application=app_a, evaluator=self.evaluator)
        Evaluation.objects.create(application=app_b, evaluator=other_evaluator)

        result = send_evaluation_reminders()

        self.assertIn('2', result)
        self.assertEqual(
            EmailLog.objects.filter(recipient_email=self.evaluator.email).count(), 1
        )
        self.assertEqual(
            EmailLog.objects.filter(recipient_email=other_evaluator.email).count(), 1
        )
