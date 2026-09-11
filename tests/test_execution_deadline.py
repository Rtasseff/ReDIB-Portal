"""
Tests for execution-deadline (docs/handoffs/execution-deadline.md, backlog
#80a): each application carries its own execution end, set by the node when it
sets the approved hours, defaulting to the call's date.

- `Application.effective_execution_end` — the override, else the call's date.
- `Application.set_execution_end` — end-of-day local; the call's own date
  stores None so the call-level date stays the lever.
- The three write paths: node resolution (accept only), Promote to Accepted,
  and the detail-page edit (`applications:set_execution_end`).
- `send_completion_reminders` and `send_waitlist_digest` key their one-time
  milestone nudge off the effective date.
"""
import io
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.messages import get_messages
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from applications.models import Application, NodeResolution, RequestedAccess
from applications.tasks import send_completion_reminders, send_waitlist_digest
from calls.models import Call
from communications.models import EmailLog
from core.models import Equipment, Node, Organization, UserRole
from core.test_utils import create_complete_user


def _eod(d):
    """23:59:59 local on date `d`, the way calls/forms.py stores end dates."""
    return timezone.make_aware(datetime.combine(d, time(23, 59, 59)))


def _local_date(dt):
    return timezone.localtime(dt).date()


def _make_node(code):
    org = Organization.objects.create(
        name=f'{code} Host', organization_type='other', iso2='ES', country='Spain',
    )
    node = Node.objects.create(code=code, organization=org, location='Here')
    equipment = Equipment.objects.create(node=node, name=f'{code} Scanner', category='mri')
    nc = create_complete_user(email=f'nc-{code.lower()}@exec.test', organization=org)
    UserRole.objects.create(user=nc, role='node_coordinator', node=node, is_active=True)
    return node, equipment, nc


class ExecutionEndTestBase(TestCase):
    def setUp(self):
        call_command('seed_email_templates', stdout=io.StringIO())
        today = timezone.localdate()
        self.call = Call.objects.create(
            code='EXEC-2026', title='Execution call', status='resolved',
            submission_start=timezone.now() - timedelta(days=90),
            submission_end=timezone.now() - timedelta(days=60),
            evaluation_deadline=timezone.now() - timedelta(days=30),
            execution_start=timezone.make_aware(datetime.combine(today - timedelta(days=5), time(0, 0))),
            execution_end=_eod(today + timedelta(days=30)),
            resolutions_released=True,
        )
        self.call_end_date = _local_date(self.call.execution_end)
        self.start_date = _local_date(self.call.execution_start)
        self.applicant = create_complete_user(email='applicant@exec.test')
        self.node, self.equipment, self.nc = _make_node('EX-A')

    def _make_application(self, status, code='EXEC-2026-001', **fields):
        application = Application.objects.create(
            applicant=self.applicant, call=self.call, code=code,
            brief_description='exec test', status=status,
            applicant_email=self.applicant.email, final_score=Decimal('8.0'),
            **fields,
        )
        RequestedAccess.objects.create(
            application=application, equipment=self.equipment, hours_requested=Decimal('10'),
        )
        return application


class EffectiveExecutionEndTest(ExecutionEndTestBase):
    """Tests 1 and 2: the property and the one write rule."""

    def setUp(self):
        super().setUp()
        self.application = self._make_application('accepted', resolution='accepted')

    def test_null_field_inherits_the_calls_date(self):
        self.assertIsNone(self.application.execution_end)
        self.assertEqual(self.application.effective_execution_end, self.call.execution_end)

    def test_override_wins_when_set(self):
        override = _eod(self.call_end_date + timedelta(days=40))
        self.application.execution_end = override
        self.assertEqual(self.application.effective_execution_end, override)

    def test_calls_date_moves_every_project_without_an_override(self):
        self.call.execution_end = _eod(self.call_end_date + timedelta(days=10))
        self.call.save()
        self.application.refresh_from_db()
        self.assertEqual(self.application.effective_execution_end, self.call.execution_end)

    def test_different_date_is_stored_at_end_of_day_local(self):
        target = self.call_end_date + timedelta(days=40)
        self.application.set_execution_end(target)
        local = timezone.localtime(self.application.execution_end)
        self.assertEqual(local.date(), target)
        self.assertEqual(local.time(), time(23, 59, 59))

    def test_calls_own_date_stays_none(self):
        self.application.set_execution_end(self.call_end_date)
        self.assertIsNone(self.application.execution_end)

    def test_calls_own_date_clears_an_earlier_override(self):
        self.application.set_execution_end(self.call_end_date + timedelta(days=40))
        self.assertIsNotNone(self.application.execution_end)
        self.application.set_execution_end(self.call_end_date)
        self.assertIsNone(self.application.execution_end)

    def test_end_of_day_survives_the_october_dst_change(self):
        # Europe/Madrid leaves summer time early on Sunday 2026-10-25.
        stored = {}
        for d in (date(2026, 10, 24), date(2026, 10, 25), date(2026, 10, 26)):
            self.application.set_execution_end(d)
            local = timezone.localtime(self.application.execution_end)
            self.assertEqual(local.date(), d)
            self.assertEqual(local.time(), time(23, 59, 59))
            stored[d] = local.utcoffset()
        self.assertNotEqual(stored[date(2026, 10, 24)], stored[date(2026, 10, 26)])


class NodeResolutionExecutionEndTest(ExecutionEndTestBase):
    """Test 3: the date rides with the hours at node resolution, accept only."""

    def setUp(self):
        super().setUp()
        self.application = self._make_application('evaluated')
        self.client = Client()
        self.client.force_login(self.nc)

    def _url(self, node=None):
        return reverse('applications:node_resolution_review', kwargs={
            'application_id': self.application.id, 'node_id': (node or self.node).id,
        })

    def _post(self, resolution, execution_end, hours='7', client=None, node=None, equipment=None):
        data = {
            'resolution': resolution,
            'comments': 'decided',
            f'hours_approved_{(equipment or self.equipment).id}': hours,
        }
        if execution_end is not None:
            data['execution_end'] = execution_end
        return (client or self.client).post(self._url(node), data)

    def test_review_page_prefills_the_calls_date(self):
        resp = self.client.get(self._url())
        self.assertContains(resp, 'name="execution_end"')
        self.assertContains(resp, f'value="{self.call_end_date.isoformat()}"')

    def test_accept_with_a_date_stores_the_override(self):
        target = self.call_end_date + timedelta(days=40)
        resp = self._post('accept', target.isoformat())
        self.assertEqual(resp.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'accepted')
        self.assertEqual(_local_date(self.application.execution_end), target)
        self.assertEqual(
            RequestedAccess.objects.get(application=self.application).hours_approved, Decimal('7')
        )

    def test_accept_with_the_calls_date_stays_null(self):
        resp = self._post('accept', self.call_end_date.isoformat())
        self.assertEqual(resp.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'accepted')
        self.assertIsNone(self.application.execution_end)

    def test_accept_without_the_field_keeps_the_default(self):
        resp = self._post('accept', None)
        self.assertEqual(resp.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'accepted')
        self.assertIsNone(self.application.execution_end)

    def test_date_before_execution_start_saves_nothing(self):
        too_early = self.start_date - timedelta(days=1)
        resp = self._post('accept', too_early.isoformat())
        self.assertEqual(resp.status_code, 200)  # re-rendered, not redirected
        self.assertContains(resp, 'cannot end before')
        self.assertContains(resp, f'value="{too_early.isoformat()}"')  # what was entered
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'evaluated')
        self.assertIsNone(self.application.execution_end)
        self.assertFalse(NodeResolution.objects.filter(application=self.application).exists())
        self.assertIsNone(RequestedAccess.objects.get(application=self.application).hours_approved)

    def test_blank_date_on_accept_saves_nothing(self):
        resp = self._post('accept', '')
        self.assertEqual(resp.status_code, 200)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'evaluated')
        self.assertFalse(NodeResolution.objects.filter(application=self.application).exists())

    def test_waitlist_ignores_the_date(self):
        resp = self._post('waitlist', (self.call_end_date + timedelta(days=40)).isoformat())
        self.assertEqual(resp.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'pending')
        self.assertIsNone(self.application.execution_end)

    def test_waitlist_with_a_bad_date_still_submits(self):
        # The date is not read on waitlist, so it cannot block the decision.
        resp = self._post('waitlist', 'not-a-date')
        self.assertEqual(resp.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'pending')

    def test_multi_node_first_accept_keeps_its_date_and_last_edit_wins(self):
        node_b, equipment_b, nc_b = _make_node('EX-B')
        RequestedAccess.objects.create(
            application=self.application, equipment=equipment_b, hours_requested=Decimal('4'),
        )
        first = self.call_end_date + timedelta(days=20)
        self._post('accept', first.isoformat())
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'evaluated')  # node B still to decide
        self.assertEqual(_local_date(self.application.execution_end), first)

        client_b = Client()
        client_b.force_login(nc_b)
        second = self.call_end_date + timedelta(days=50)
        self._post('accept', second.isoformat(), hours='4', client=client_b, node=node_b, equipment=equipment_b)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'accepted')
        self.assertEqual(_local_date(self.application.execution_end), second)


class PromotionExecutionEndTest(ExecutionEndTestBase):
    """Test 4: Promote to Accepted sets the date alongside the hours."""

    def setUp(self):
        super().setUp()
        self.application = self._make_application(
            'pending', resolution='pending', accepted_by_applicant=True,
            accepted_at=timezone.now() - timedelta(days=5),
        )
        self.client = Client()
        self.client.force_login(self.nc)
        self.url = reverse('applications:promote_waitlisted', kwargs={'pk': self.application.pk})

    def test_confirm_page_prefills_the_calls_date(self):
        resp = self.client.get(self.url)
        self.assertContains(resp, 'name="execution_end"')
        self.assertContains(resp, f'value="{self.call_end_date.isoformat()}"')

    def test_promotion_with_a_date_stores_it(self):
        target = self.call_end_date + timedelta(days=40)
        resp = self.client.post(self.url, {
            f'hours_approved_{self.equipment.id}': '6', 'execution_end': target.isoformat(),
        })
        self.assertEqual(resp.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'accepted')
        self.assertEqual(_local_date(self.application.execution_end), target)

    def test_promotion_with_the_calls_date_stays_null(self):
        self.client.post(self.url, {
            f'hours_approved_{self.equipment.id}': '6', 'execution_end': self.call_end_date.isoformat(),
        })
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'accepted')
        self.assertIsNone(self.application.execution_end)

    def test_bad_date_saves_neither_date_nor_hours(self):
        resp = self.client.post(self.url, {
            f'hours_approved_{self.equipment.id}': '6',
            'execution_end': (self.start_date - timedelta(days=1)).isoformat(),
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'cannot end before')
        self.assertContains(resp, 'value="6"')  # the hours just entered survive the re-render
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'pending')
        self.assertIsNone(self.application.execution_end)
        self.assertIsNone(RequestedAccess.objects.get(application=self.application).hours_approved)


class SetExecutionEndViewTest(ExecutionEndTestBase):
    """Test 5: the later edit from the detail page, and who may make it."""

    def setUp(self):
        super().setUp()
        self.application = self._make_application(
            'accepted', resolution='accepted', accepted_by_applicant=True,
        )
        self.url = reverse('applications:set_execution_end', kwargs={'pk': self.application.pk})
        self.target = self.call_end_date + timedelta(days=40)

    def _post_as(self, user, value=None):
        client = Client()
        client.force_login(user)
        return client.post(self.url, {'execution_end': (value or self.target).isoformat()})

    def test_node_coordinator_of_the_node_can_change_it(self):
        resp = self._post_as(self.nc)
        self.assertRedirects(resp, reverse('applications:detail', kwargs={'pk': self.application.pk}),
                             fetch_redirect_response=False)
        self.application.refresh_from_db()
        self.assertEqual(_local_date(self.application.execution_end), self.target)
        msgs = [str(m) for m in get_messages(resp.wsgi_request)]
        self.assertEqual(len(msgs), 1)
        self.assertIn(self.target.strftime('%b %d, %Y'), msgs[0])

    def test_back_to_the_calls_date_clears_the_override(self):
        self._post_as(self.nc)
        self._post_as(self.nc, value=self.call_end_date)
        self.application.refresh_from_db()
        self.assertIsNone(self.application.execution_end)

    def test_redib_coordinator_can_change_it(self):
        coordinator = create_complete_user(email='coord@exec.test')
        UserRole.objects.create(user=coordinator, role='coordinator', is_active=True)
        self._post_as(coordinator)
        self.application.refresh_from_db()
        self.assertEqual(_local_date(self.application.execution_end), self.target)

    def test_node_coordinator_of_another_node_cannot(self):
        _, _, other_nc = _make_node('EX-OTHER')
        resp = self._post_as(other_nc)
        self.assertEqual(resp.status_code, 302)
        self.application.refresh_from_db()
        self.assertIsNone(self.application.execution_end)

    def test_applicant_cannot(self):
        resp = self._post_as(self.applicant)
        self.assertEqual(resp.status_code, 302)
        self.application.refresh_from_db()
        self.assertIsNone(self.application.execution_end)

    def test_date_before_execution_start_is_refused(self):
        self._post_as(self.nc, value=self.start_date - timedelta(days=1))
        self.application.refresh_from_db()
        self.assertIsNone(self.application.execution_end)

    def test_completed_project_is_refused(self):
        self.application.is_completed = True
        self.application.save()
        self._post_as(self.nc)
        self.application.refresh_from_db()
        self.assertIsNone(self.application.execution_end)

    def test_get_is_not_allowed(self):
        client = Client()
        client.force_login(self.nc)
        self.assertEqual(client.get(self.url).status_code, 405)

    def test_detail_page_shows_the_edit_to_the_node_and_the_date_to_the_applicant(self):
        self._post_as(self.nc)
        detail = reverse('applications:detail', kwargs={'pk': self.application.pk})
        shown = self.target.strftime('%b %d, %Y')

        client = Client()
        client.force_login(self.nc)
        resp = client.get(detail)
        self.assertContains(resp, shown)
        self.assertContains(resp, '(set by node)')
        self.assertContains(resp, self.url)

        client.force_login(self.applicant)
        resp = client.get(detail)
        self.assertContains(resp, shown)
        self.assertContains(resp, '(set by node)')
        self.assertNotContains(resp, self.url)

    def test_detail_page_has_no_marker_while_the_call_date_applies(self):
        client = Client()
        client.force_login(self.nc)
        resp = client.get(reverse('applications:detail', kwargs={'pk': self.application.pk}))
        self.assertContains(resp, self.call_end_date.strftime('%b %d, %Y'))
        self.assertNotContains(resp, '(set by node)')

    def test_access_tracking_shows_the_effective_date(self):
        self._post_as(self.nc)
        client = Client()
        client.force_login(self.nc)
        resp = client.get(reverse('access:access_tracking'))
        self.assertContains(resp, f"ends {self.target.strftime('%b %d, %Y')}")


class RemindersReadEffectiveEndTest(ExecutionEndTestBase):
    """Test 6: the milestone nudge follows the project's own date."""

    def _move_call_end(self, days_from_today):
        self.call.execution_start = timezone.now() - timedelta(days=150)
        self.call.execution_end = _eod(timezone.localdate() + timedelta(days=days_from_today))
        self.call.save()

    def _active_application(self):
        # Handed off 10 days ago: nowhere near the 60/30 cadence, so only the
        # milestone nudge can fire.
        ten_days_ago = timezone.now() - timedelta(days=10)
        application = self._make_application(
            'accepted', resolution='accepted', accepted_by_applicant=True,
            accepted_at=ten_days_ago, handoff_email_sent_at=ten_days_ago,
        )
        application.set_execution_end(_local_date(self.call.execution_end) + timedelta(days=40))
        application.save()
        return application

    def _waitlisted_application(self):
        application = self._make_application(
            'pending', resolution='pending', accepted_by_applicant=True,
            accepted_at=timezone.now() - timedelta(days=10),  # not a 30/30 checkpoint
        )
        application.set_execution_end(_local_date(self.call.execution_end) + timedelta(days=40))
        application.save()
        return application

    def test_completion_no_nudge_in_the_calls_window(self):
        self._move_call_end(-3)  # the call's window is open; the project's is 37 days off
        self._active_application()

        send_completion_reminders()

        self.assertFalse(EmailLog.objects.filter(
            template__template_type__in=['completion_reminder', 'completion_reminder_coordinator'],
        ).exists())

    def test_completion_nudge_in_the_projects_own_window(self):
        self._move_call_end(-43)  # the call's window closed long ago; the project's opened 3 days ago
        app = self._active_application()

        send_completion_reminders()

        self.assertTrue(EmailLog.objects.filter(
            template__template_type='completion_reminder', related_application_id=app.id,
        ).exists())
        self.assertTrue(EmailLog.objects.filter(
            template__template_type='completion_reminder_coordinator', recipient_email=self.nc.email,
        ).exists())

    def test_waitlist_digest_no_nudge_in_the_calls_window(self):
        self._move_call_end(-3)
        self._waitlisted_application()

        send_waitlist_digest()

        self.assertFalse(EmailLog.objects.filter(template__template_type='waitlist_digest').exists())

    def test_waitlist_digest_nudge_in_the_projects_own_window(self):
        self._move_call_end(-43)
        self._waitlisted_application()

        send_waitlist_digest()

        self.assertTrue(EmailLog.objects.filter(
            template__template_type='waitlist_digest', recipient_email=self.nc.email,
        ).exists())
