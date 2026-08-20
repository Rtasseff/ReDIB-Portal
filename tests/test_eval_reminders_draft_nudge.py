"""
Tests for eval-reminders #35: draft application nudge.

Nudges applicants who still hold a `draft` application on an `open` call at
T-7 and T-2 before `submission_end`, each once, EmailLog-deduped per
(application, offset). Never nudges once the call has closed.
"""
import io

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from applications.models import Application
from calls.models import Call
from calls.tasks import send_draft_nudges
from communications.models import EmailLog, NotificationPreference
from core.models import Organization
from core.test_utils import create_complete_user


class DraftNudgeTest(TestCase):
    def setUp(self):
        call_command('seed_email_templates', stdout=io.StringIO())
        self.org = Organization.objects.create(
            name='Draft Nudge Org', iso2='ES', country='Spain', organization_type='other'
        )
        self.applicant = create_complete_user(email='draft-nudge-applicant@eval.test', organization=self.org)

    def _make_call(self, submission_end, status='open'):
        return Call.objects.create(
            code=f'DRAFT-NUDGE-{submission_end.timestamp():.0f}',
            title='Draft Nudge Call',
            status=status,
            submission_start=timezone.now() - timedelta(days=30),
            submission_end=submission_end,
            evaluation_deadline=submission_end + timedelta(days=60),
            execution_start=submission_end + timedelta(days=90),
            execution_end=submission_end + timedelta(days=180),
        )

    def _make_draft(self, call, code='DRAFT-NUDGE-001'):
        return Application.objects.create(
            applicant=self.applicant,
            call=call,
            code=code,
            brief_description='Never-submitted draft',
            status='draft',
        )

    def test_nudge_sent_at_t_minus_seven(self):
        call = self._make_call(timezone.now() + timedelta(days=7))
        app = self._make_draft(call)

        result = send_draft_nudges()

        self.assertIn('1', result)
        self.assertTrue(
            EmailLog.objects.filter(
                template__template_type='draft_nudge',
                recipient_email=self.applicant.email,
                related_application_id=app.id,
            ).exists()
        )

    def test_nudge_sent_at_t_minus_two(self):
        call = self._make_call(timezone.now() + timedelta(days=2))
        self._make_draft(call)

        send_draft_nudges()

        self.assertEqual(EmailLog.objects.count(), 1)

    def test_no_nudge_between_checkpoints(self):
        call = self._make_call(timezone.now() + timedelta(days=5))
        self._make_draft(call)

        send_draft_nudges()

        self.assertEqual(EmailLog.objects.count(), 0)

    def test_no_nudge_once_call_closed(self):
        call = self._make_call(timezone.now() - timedelta(days=1), status='closed')
        self._make_draft(call)

        send_draft_nudges()

        self.assertEqual(EmailLog.objects.count(), 0)

    def test_no_nudge_for_submitted_application(self):
        call = self._make_call(timezone.now() + timedelta(days=7))
        app = self._make_draft(call)
        app.status = 'submitted'
        app.submitted_at = timezone.now()
        app.save()

        send_draft_nudges()

        self.assertEqual(EmailLog.objects.count(), 0)

    def test_does_not_double_send_same_day(self):
        call = self._make_call(timezone.now() + timedelta(days=7))
        self._make_draft(call)

        send_draft_nudges()
        first_count = EmailLog.objects.count()
        self.assertEqual(first_count, 1)

        send_draft_nudges()
        self.assertEqual(EmailLog.objects.count(), first_count)

    def test_t_minus_seven_and_t_minus_two_both_fire_independently(self):
        """Confirms the 24h dedupe window on one offset does not suppress
        the other, separate offset five days later."""
        call = self._make_call(timezone.now() + timedelta(days=7))
        app = self._make_draft(call)

        send_draft_nudges()
        self.assertEqual(EmailLog.objects.count(), 1)

        # Simulate 5 real days passing: back-date the T-7 EmailLog row (out
        # of the 24h dedupe window) and move the call to its T-2 checkpoint.
        EmailLog.objects.update(sent_at=timezone.now() - timedelta(days=5))
        call.submission_end = timezone.now() + timedelta(days=2)
        call.save()

        send_draft_nudges()
        self.assertEqual(EmailLog.objects.count(), 2)

    def test_notification_preferences_skip_nudge(self):
        call = self._make_call(timezone.now() + timedelta(days=7))
        self._make_draft(call)
        NotificationPreference.objects.create(user=self.applicant, notify_reminders=False)

        send_draft_nudges()

        self.assertEqual(EmailLog.objects.count(), 0)

    def test_multiple_drafts_same_applicant_each_nudged(self):
        call = self._make_call(timezone.now() + timedelta(days=7))
        app1 = self._make_draft(call, code='DRAFT-NUDGE-A')
        app2 = self._make_draft(call, code='DRAFT-NUDGE-B')

        result = send_draft_nudges()

        self.assertIn('2', result)
        self.assertEqual(EmailLog.objects.filter(related_application_id=app1.id).count(), 1)
        self.assertEqual(EmailLog.objects.filter(related_application_id=app2.id).count(), 1)

    def test_applicant_email_preferred_over_account_email(self):
        call = self._make_call(timezone.now() + timedelta(days=7))
        app = self._make_draft(call)
        app.applicant_email = 'declared-pi@eval.test'
        app.save()

        send_draft_nudges()

        self.assertTrue(
            EmailLog.objects.filter(
                template__template_type='draft_nudge',
                recipient_email='declared-pi@eval.test',
            ).exists()
        )
