"""
Regression tests for the rehearsal-guards branch (docs/handoffs/rehearsal-guards.md).

Silent state changes the 2026-09-08 dress rehearsal found — nothing threw, so
nothing in the suite had caught them:

- #73: Auto-Assign Evaluators closed a call that was still accepting
  applications. It may close the call only once `submission_end` has passed —
  the same condition as `calls.tasks.check_call_deadlines`.
"""
from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from applications.models import Application
from calls.models import Call
from core.models import Organization, UserRole
from core.test_utils import create_complete_user
from evaluations.models import Evaluation
from evaluations.tasks import assign_evaluators_to_call


def _make_org(name):
    return Organization.objects.create(
        name=name, organization_type='other', iso2='ES', country='Spain',
    )


class AutoAssignKeepsLiveCallOpenTest(TestCase):
    """#73 — auto-assign must not close a call inside its submission window."""

    def setUp(self):
        self.call = Call.objects.create(
            code='GUARD-73', title='Guard call',
            status='open',
            submission_start=timezone.now() - timedelta(days=10),
            submission_end=timezone.now() + timedelta(days=20),
            evaluation_deadline=timezone.now() + timedelta(days=40),
            execution_start=timezone.now() + timedelta(days=50),
            execution_end=timezone.now() + timedelta(days=200),
        )
        applicant = create_complete_user(
            email='applicant@guard.test', organization=_make_org('Applicant Org'),
        )
        self.application = Application.objects.create(
            applicant=applicant, call=self.call, code='GUARD-73-001',
            brief_description='guard', status='pending_evaluation',
        )
        self.coordinator = create_complete_user(email='coord@guard.test')
        UserRole.objects.create(user=self.coordinator, role='coordinator', is_active=True)

    def _add_evaluators(self, n=2):
        for i in range(n):
            ev = create_complete_user(
                email=f'ev{i}@guard.test', organization=_make_org(f'Evaluator Org {i}'),
            )
            UserRole.objects.create(user=ev, role='evaluator', is_active=True)

    def test_assignment_inside_window_leaves_call_open(self):
        self._add_evaluators(2)

        assign_evaluators_to_call(self.call.id, num_evaluators=2)

        self.assertEqual(Evaluation.objects.filter(application=self.application).count(), 2)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'under_evaluation')
        self.call.refresh_from_db()
        self.assertEqual(self.call.status, 'open')

    def test_assignment_after_deadline_still_closes_call(self):
        self.call.submission_end = timezone.now() - timedelta(days=1)
        self.call.save()
        self._add_evaluators(2)

        assign_evaluators_to_call(self.call.id, num_evaluators=2)

        self.call.refresh_from_db()
        self.assertEqual(self.call.status, 'closed')

    def test_empty_pool_inside_window_leaves_call_open(self):
        # No evaluators at all: the task takes its early return.
        result = assign_evaluators_to_call(self.call.id, num_evaluators=2)

        self.assertEqual(result['pool_size'], 0)
        self.call.refresh_from_db()
        self.assertEqual(self.call.status, 'open')

    def test_assignment_page_warns_while_call_is_open(self):
        client = Client()
        client.force_login(self.coordinator)
        url = reverse('evaluations:call_assignment_detail', kwargs={'call_id': self.call.id})

        resp = client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'This call is still accepting applications until')

        self.call.status = 'closed'
        self.call.save()
        resp = client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Auto-Assign Evaluators')  # the form is still there
        self.assertNotContains(resp, 'still accepting applications')
