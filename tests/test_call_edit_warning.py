"""#64 — editing a call's dates warns when they now disagree with its status.

The edit form cannot change `status` (#27); the warning only tells the
coordinator what the dates they just saved actually do. Also pins the Spanish
waitlist label decided 2026-09-15 ("Lista de espera", not "En espera").
"""
from datetime import timedelta

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from calls.forms import CallEquipmentFormSet
from calls.models import Call
from calls.views import _dates_vs_status_warning
from core.models import UserRole
from core.test_utils import create_complete_user
from reports.resolution_table import RESOLUTION_LABELS


def _make_call(**overrides):
    now = timezone.now()
    defaults = dict(
        code='CALL-64', title='Edit Warning Call',
        submission_start=now - timedelta(days=1),
        submission_end=now + timedelta(days=30),
        evaluation_deadline=now + timedelta(days=60),
        execution_start=now + timedelta(days=70),
        execution_end=now + timedelta(days=100),
        status='open',
    )
    defaults.update(overrides)
    return Call.objects.create(**defaults)


class DatesVsStatusWarningTests(TestCase):

    def test_consistent_open_call_gives_no_warning(self):
        self.assertIsNone(_dates_vs_status_warning(_make_call()))

    def test_open_call_with_future_start_is_flagged(self):
        call = _make_call(submission_start=timezone.now() + timedelta(days=7))
        msg = _dates_vs_status_warning(call)
        self.assertIn('marked Open', msg)
        self.assertIn('NOT accepting applications', msg)

    def test_open_call_with_past_deadline_is_flagged(self):
        call = _make_call(submission_end=timezone.now() - timedelta(hours=1))
        msg = _dates_vs_status_warning(call)
        self.assertIn('deadline is now in the past', msg)

    def test_announced_call_with_past_start_is_flagged(self):
        call = _make_call(status='announced', submission_start=timezone.now() - timedelta(hours=1))
        self.assertIn('will open automatically', _dates_vs_status_warning(call))

    def test_closed_call_with_future_deadline_does_not_reopen(self):
        call = _make_call(status='closed', submission_start=timezone.now() - timedelta(days=40),
                          submission_end=timezone.now() + timedelta(days=5))
        msg = _dates_vs_status_warning(call)
        self.assertIn('stays closed', msg)
        self.assertIn('#54', msg)

    def test_consistent_closed_call_gives_no_warning(self):
        call = _make_call(status='closed', submission_start=timezone.now() - timedelta(days=40),
                          submission_end=timezone.now() - timedelta(days=1))
        self.assertIsNone(_dates_vs_status_warning(call))


class CallEditViewWarningTests(TestCase):

    def setUp(self):
        self.coordinator = create_complete_user('coord-64@test.com')
        UserRole.objects.create(user=self.coordinator, role='coordinator', is_active=True)
        self.call = _make_call()
        self.client = Client()
        self.client.force_login(self.coordinator)

    def _post_dates(self, **dates):
        fs = CallEquipmentFormSet(instance=self.call)
        data = {f'{fs.prefix}-{k}': v for k, v in fs.management_form.initial.items()}
        fields = dict(
            code=self.call.code, title=self.call.title,
            description='Edited description', guidelines='Edited guidelines',
            submission_start=self.call.submission_start, submission_end=self.call.submission_end,
            evaluation_deadline=self.call.evaluation_deadline,
            execution_start=self.call.execution_start, execution_end=self.call.execution_end,
        )
        fields.update(dates)
        for k, v in fields.items():
            data[k] = timezone.localtime(v).strftime('%Y-%m-%d') if hasattr(v, 'strftime') else v
        return self.client.post(reverse('calls:call_edit', args=[self.call.pk]), data, follow=True)

    def test_pushing_the_start_forward_on_an_open_call_warns_and_keeps_status(self):
        resp = self._post_dates(submission_start=timezone.now() + timedelta(days=7))
        self.assertContains(resp, 'updated successfully')
        self.assertContains(resp, 'NOT accepting applications')
        self.call.refresh_from_db()
        self.assertEqual(self.call.status, 'open')
        self.assertFalse(self.call.is_open)

    def test_extending_the_deadline_on_an_open_call_does_not_warn(self):
        resp = self._post_dates(submission_end=timezone.now() + timedelta(days=45))
        self.assertContains(resp, 'updated successfully')
        self.assertNotContains(resp, 'marked Open')


class SpanishWaitlistLabelTest(TestCase):

    def test_waitlist_reads_lista_de_espera(self):
        self.assertEqual(RESOLUTION_LABELS['es']['waitlist'], 'Lista de espera')
