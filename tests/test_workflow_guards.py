"""
Tests for feature/workflow-guards (backlog #84-#87).

- #84: the legacy ReDIB-coordinator resolution tools (Decide, Apply Bulk
  Resolution, Finalize) are gone; the Resolution page is read-only.
- #85: Announce / Publish / Close are POST-only and refuse the wrong
  starting status; a GET changes nothing. The beat task and the page
  fallback close expired calls through one shared function that saves each
  call, so django-simple-history records it.
- #86: removing the last outstanding evaluator moves the application on;
  Mark Complete refuses an application that is not accepted and confirmed.
- #87 (a): the "Publish Call" confirmation on the edit page matches
  CALL_ANNOUNCEMENT_EMAILS_ENABLED. The consult fan-out (f) is covered in
  tests/test_wizard_step5_consult.py.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from applications.models import Application, RequestedAccess
from calls.models import Call, CallEquipmentAllocation
from calls.services import close_expired_calls
from calls.tasks import check_call_deadlines
from core.models import Equipment, Node, Organization, UserRole
from core.test_utils import create_complete_user
from evaluations.models import Evaluation

User = get_user_model()


def _make_call(code, status='draft', starts_in_days=10, ends_in_days=40, with_equipment=True):
    now = timezone.now()
    call = Call.objects.create(
        code=code, title=code, status=status,
        submission_start=now + timedelta(days=starts_in_days),
        submission_end=now + timedelta(days=ends_in_days),
        evaluation_deadline=now + timedelta(days=ends_in_days + 30),
        execution_start=now + timedelta(days=ends_in_days + 40),
        execution_end=now + timedelta(days=ends_in_days + 100),
    )
    if with_equipment:
        org = Organization.objects.create(
            name=f'Org {code}', country='ES', organization_type='university',
        )
        node = Node.objects.create(code=f'N-{code}', organization=org, location='Madrid')
        equipment = Equipment.objects.create(
            node=node, name=f'MRI {code}', category='mri', area='preclinical',
        )
        CallEquipmentAllocation.objects.create(call=call, equipment=equipment)
    return call


def _coordinator_client(email='coord@wg.test'):
    user = create_complete_user(email=email)
    UserRole.objects.create(user=user, role='coordinator', is_active=True)
    client = Client()
    client.force_login(user)
    return client, user


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage'
)
class LegacyResolutionToolsRemovedTest(TestCase):
    """#84: the Resolution page is a read-only watch list."""

    def test_legacy_urls_are_gone(self):
        for name, kwargs in [
            ('applications:application_resolution', {'application_id': 1}),
            ('applications:bulk_resolution', {'call_id': 1}),
            ('applications:finalize_resolution', {'call_id': 1}),
        ]:
            with self.assertRaises(NoReverseMatch):
                reverse(name, kwargs=kwargs)

    def test_call_resolution_page_has_no_write_actions(self):
        client, _ = _coordinator_client()
        call = _make_call('WG-RES', status='closed', starts_in_days=-60, ends_in_days=-30)
        call.resolutions_released = True
        call.save()
        applicant = create_complete_user(email='app@wg.test')
        Application.objects.create(
            applicant=applicant, call=call, code='WG-RES-001',
            status='evaluated', final_score=Decimal('8.0'),
        )

        response = client.get(reverse('applications:call_resolution_detail', args=[call.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'WG-RES-001')
        for gone in ('Decide', 'Apply Bulk Resolution', 'Finalize Resolution'):
            self.assertNotContains(response, gone)

        dashboard = client.get(reverse('applications:resolution_dashboard'))
        self.assertNotContains(dashboard, 'make final decisions')
        self.assertNotContains(dashboard, 'Release Resolutions')


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage',
    CALL_ANNOUNCEMENT_EMAILS_ENABLED=False,
)
class CallActionGuardTest(TestCase):
    """#85: call actions are POST-only and refuse the wrong starting status."""

    def setUp(self):
        self.client, _ = _coordinator_client()

    def _post(self, action, call):
        return self.client.post(reverse(f'calls:{action}', args=[call.pk]), follow=True)

    def test_get_changes_nothing(self):
        cases = [
            ('announce', 'draft'),
            ('publish', 'draft'),
            ('close', 'open'),
        ]
        for action, status in cases:
            with self.subTest(action=action):
                call = _make_call(f'WG-GET-{action}', status=status, starts_in_days=-1)
                response = self.client.get(reverse(f'calls:{action}', args=[call.pk]))
                self.assertEqual(response.status_code, 405)
                call.refresh_from_db()
                self.assertEqual(call.status, status)

    def test_get_close_on_resolved_call_does_not_reopen_it(self):
        """Regression: an old GET link used to set a resolved call back to closed."""
        call = _make_call('WG-RESOLVED', status='resolved', starts_in_days=-60, ends_in_days=-30)
        self.client.get(reverse('calls:close', args=[call.pk]))
        call.refresh_from_db()
        self.assertEqual(call.status, 'resolved')

    def test_close_refuses_non_open(self):
        for status in ('draft', 'announced', 'closed', 'resolved'):
            with self.subTest(status=status):
                call = _make_call(f'WG-CLOSE-{status}', status=status)
                response = self._post('close', call)
                call.refresh_from_db()
                self.assertEqual(call.status, status)
                self.assertContains(response, 'Only open calls can be closed')

    def test_close_open_call(self):
        call = _make_call('WG-CLOSE-OK', status='open', starts_in_days=-1)
        self._post('close', call)
        call.refresh_from_db()
        self.assertEqual(call.status, 'closed')

    def test_announce_refuses_non_draft(self):
        for status in ('announced', 'open', 'closed', 'resolved'):
            with self.subTest(status=status):
                call = _make_call(f'WG-ANN-{status}', status=status)
                response = self._post('announce', call)
                call.refresh_from_db()
                self.assertEqual(call.status, status)
                self.assertContains(response, 'Only draft calls can be announced')

    def test_announce_draft(self):
        call = _make_call('WG-ANN-OK')
        self._post('announce', call)
        call.refresh_from_db()
        self.assertEqual(call.status, 'announced')

    def test_publish_refuses_open_closed_resolved(self):
        for status in ('open', 'closed', 'resolved'):
            with self.subTest(status=status):
                call = _make_call(f'WG-PUB-{status}', status=status, starts_in_days=-1)
                response = self._post('publish', call)
                call.refresh_from_db()
                self.assertEqual(call.status, status)
                self.assertContains(response, 'cannot be published')

    def test_publish_from_draft_and_announced(self):
        for status in ('draft', 'announced'):
            with self.subTest(status=status):
                call = _make_call(f'WG-PUB-OK-{status}', status=status, starts_in_days=-1)
                self._post('publish', call)
                call.refresh_from_db()
                self.assertEqual(call.status, 'open')

    def test_buttons_are_post_forms(self):
        call = _make_call('WG-BTN')
        detail = self.client.get(reverse('calls:detail', args=[call.pk])).content.decode()
        self.assertIn('id="call-action-form" method="post"', detail)
        self.assertIn(f'formaction="{reverse("calls:announce", args=[call.pk])}"', detail)
        self.assertNotIn(f'href="{reverse("calls:announce", args=[call.pk])}"', detail)
        self.assertNotIn(f'href="{reverse("calls:publish", args=[call.pk])}"', detail)


class AutoCloseTest(TestCase):
    """#85: one shared auto-close, with a history row for each call."""

    def test_open_past_end_closes_with_history_row(self):
        call = _make_call('WG-AC-OPEN', status='open', starts_in_days=-30, ends_in_days=-1)
        before = call.history.count()

        result = check_call_deadlines()

        call.refresh_from_db()
        self.assertEqual(call.status, 'closed')
        self.assertEqual(result, 'Opened 0, closed 1')
        self.assertEqual(call.history.count(), before + 1)
        self.assertEqual(call.history.first().status, 'closed')

    def test_announced_whose_window_passed_closes(self):
        call = _make_call('WG-AC-ANN', status='announced', starts_in_days=-30, ends_in_days=-1)
        self.assertEqual(close_expired_calls(), ['WG-AC-ANN'])
        call.refresh_from_db()
        self.assertEqual(call.status, 'closed')

    def test_beat_and_page_fallback_agree(self):
        """Both paths close the same calls: an announced call past its window
        used to be closed by the page fallback but not by the beat task."""
        _make_call('WG-AC-B', status='announced', starts_in_days=-30, ends_in_days=-1)
        check_call_deadlines()
        self.assertEqual(Call.objects.get(code='WG-AC-B').status, 'closed')

        _make_call('WG-AC-P', status='announced', starts_in_days=-30, ends_in_days=-1)
        self.client.get(reverse('calls:public_list'))
        self.assertEqual(Call.objects.get(code='WG-AC-P').status, 'closed')

    def test_future_and_current_calls_untouched(self):
        _make_call('WG-AC-FUT', status='open', starts_in_days=-1, ends_in_days=10)
        _make_call('WG-AC-DRAFT', status='draft', starts_in_days=-30, ends_in_days=-1)
        self.assertEqual(close_expired_calls(), [])


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage'
)
class RemoveEvaluatorTransitionTest(TestCase):
    """#86 (a): removing the last outstanding evaluator moves the application on."""

    def setUp(self):
        self.client, _ = _coordinator_client()
        self.call = _make_call('WG-EV', status='closed', starts_in_days=-60, ends_in_days=-30)
        applicant = create_complete_user(email='app-ev@wg.test')
        self.app = Application.objects.create(
            applicant=applicant, call=self.call, code='WG-EV-001',
            status='under_evaluation',
        )
        self.ev1 = create_complete_user(email='ev1@wg.test')
        self.ev2 = create_complete_user(email='ev2@wg.test')

    def _complete(self, evaluator):
        return Evaluation.objects.create(
            application=self.app, evaluator=evaluator,
            score_quality_originality=2, score_methodology_design=2,
            score_expected_contributions=1, score_knowledge_advancement=1,
            score_social_economic_impact=1, score_exploitation_dissemination=1,
            recommendation='approved',
        )

    def _remove(self, evaluation):
        return self.client.post(
            reverse('evaluations:remove_evaluator_assignment', args=[evaluation.pk])
        )

    def test_removing_last_outstanding_moves_to_evaluated(self):
        self._complete(self.ev1)
        pending = Evaluation.objects.create(application=self.app, evaluator=self.ev2)

        self._remove(pending)

        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'evaluated')
        self.assertEqual(self.app.final_score, Decimal('8'))

    def test_removing_only_evaluation_leaves_status(self):
        only = Evaluation.objects.create(application=self.app, evaluator=self.ev1)

        self._remove(only)

        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'under_evaluation')

    def test_removing_one_of_two_outstanding_leaves_status(self):
        Evaluation.objects.create(application=self.app, evaluator=self.ev1)
        second = Evaluation.objects.create(application=self.app, evaluator=self.ev2)

        self._remove(second)

        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'under_evaluation')


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage'
)
class MarkCompleteGuardTest(TestCase):
    """#86 (b): Mark Complete refuses unless accepted and confirmed; no 500."""

    def setUp(self):
        self.call = _make_call('WG-MC', status='closed', starts_in_days=-60, ends_in_days=-30)
        self.applicant = create_complete_user(email='app-mc@wg.test')
        self.client = Client()
        self.client.force_login(self.applicant)
        self.equipment = CallEquipmentAllocation.objects.get(call=self.call).equipment

    def _app(self, code, status, accepted_by_applicant):
        app = Application.objects.create(
            applicant=self.applicant, call=self.call, code=code,
            status=status, accepted_by_applicant=accepted_by_applicant,
        )
        RequestedAccess.objects.create(
            application=app, equipment=self.equipment, hours_requested=8,
        )
        return app

    def test_refuses_wrong_state(self):
        cases = [
            ('WG-MC-EVAL', 'evaluated', None),
            ('WG-MC-PEND', 'pending', True),
            ('WG-MC-UNCONF', 'accepted', None),
            ('WG-MC-REJ', 'rejected', None),
        ]
        for code, status, accepted in cases:
            with self.subTest(code=code):
                app = self._app(code, status, accepted)
                url = reverse('access:mark_complete', args=[app.pk])
                for method in (self.client.get, self.client.post):
                    response = method(url, follow=True)
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, 'cannot be marked complete')
                app.refresh_from_db()
                self.assertEqual(app.status, status)
                self.assertFalse(app.is_completed)

    def test_accepted_and_confirmed_can_complete(self):
        app = self._app('WG-MC-OK', 'accepted', True)
        url = reverse('access:mark_complete', args=[app.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        ra = app.requested_access.get()
        self.client.post(url, {f'actual_hours_{ra.pk}': '6'})
        app.refresh_from_db()
        self.assertEqual(app.status, 'completed')


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage'
)
class PublishConfirmWordingTest(TestCase):
    """#87 (a): the edit page's Publish confirmation follows the email switch."""

    def setUp(self):
        self.client, _ = _coordinator_client()
        self.call = _make_call('WG-PC')
        self.url = reverse('calls:call_edit', args=[self.call.pk])

    @override_settings(CALL_ANNOUNCEMENT_EMAILS_ENABLED=True)
    def test_emails_on(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Notification emails go out to users.')
        self.assertNotContains(response, 'No email is sent')

    @override_settings(CALL_ANNOUNCEMENT_EMAILS_ENABLED=False)
    def test_emails_off(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'No email is sent')
        self.assertNotContains(response, 'Notification emails go out to users.')
        self.assertNotContains(response, 'This will send notification emails')
