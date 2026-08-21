"""
Tests for release-gate: hold node-coordinator resolution work until ReDIB
releases a call's evaluations to the nodes as a single batch.

Covers:
- The backfill data migration grandfathers only calls with resolutions
  already sent, not every existing call.
- check_and_transition_application still transitions to 'evaluated' but
  only fires notify_coordinator_evaluations_complete when released.
- The four refusal points: get_applications_for_node_resolution,
  apply_node_resolution, node_resolution_review, and the coordinator
  dashboard's pending_resolution count.
- The "Release to nodes" action: guards, batch email fan-out, idempotence,
  and the score-spread preview with the >=5 marker.
- #16 (stretch): access_tracking's "node-accepted, awaiting applicant" filter.
- The legacy centralized-coordinator ResolutionService (a second path to the
  same evaluated -> resolved transition, found by /code-review to bypass the
  gate entirely) is gated too, via Call.ensure_resolutions_released.
"""
import importlib
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from applications.models import Application, NodeResolution, RequestedAccess
from applications.services import NodeResolutionService, ResolutionService
from calls.models import Call
from communications.models import EmailLog, EmailTemplate
from core.models import Equipment, Node, Organization, UserRole
from core.test_utils import create_complete_user
from evaluations.models import Evaluation
from evaluations.utils import check_and_transition_application

User = get_user_model()

backfill_migration = importlib.import_module(
    'calls.migrations.0004_call_resolutions_released_and_more'
)


def _make_node(code):
    org, _ = Organization.objects.get_or_create(
        name=f'{code} Host',
        defaults={'organization_type': 'pro', 'iso2': 'ES', 'country': 'Spain'},
    )
    return Node.objects.create(code=code, organization=org, location='Here')


def _seed_templates():
    for tt in ('evaluations_complete',):
        EmailTemplate.objects.get_or_create(
            template_type=tt,
            defaults={
                'subject': f'[test] {tt}',
                'html_content': '<p>{{ application_code }}</p>',
                'text_content': '{{ application_code }}',
                'is_active': True,
            },
        )


def _make_call(code, **overrides):
    defaults = dict(
        code=code, title=code,
        status='closed',
        submission_start=timezone.now() - timedelta(days=60),
        submission_end=timezone.now() - timedelta(days=30),
        evaluation_deadline=timezone.now() - timedelta(days=10),
        execution_start=timezone.now() - timedelta(days=5),
        execution_end=timezone.now() + timedelta(days=30),
    )
    defaults.update(overrides)
    return Call.objects.create(**defaults)


def _complete_evaluation(application, evaluator, total):
    """Create a completed Evaluation summing to `total` (max 12, 6x0-2)."""
    assert 0 <= total <= 12
    scores = [total // 6] * 6
    for i in range(total - sum(scores)):
        scores[i] += 1
    return Evaluation.objects.create(
        application=application,
        evaluator=evaluator,
        score_quality_originality=scores[0],
        score_methodology_design=scores[1],
        score_expected_contributions=scores[2],
        score_knowledge_advancement=scores[3],
        score_social_economic_impact=scores[4],
        score_exploitation_dissemination=scores[5],
        recommendation='approved',
    )


class BackfillMigrationTest(TestCase):
    """Unit-tests the RunPython function the 0004 migration runs."""

    def setUp(self):
        self.applicant = create_complete_user(email='backfill-applicant@rg.test')

    def test_only_calls_with_a_resolution_are_grandfathered(self):
        already_resolved = _make_call('RG-BACKFILL-DONE')
        Application.objects.create(
            applicant=self.applicant, call=already_resolved, code='RG-BACKFILL-DONE-001',
            brief_description='resolved already', status='accepted', resolution='accepted',
        )

        untouched = _make_call('RG-BACKFILL-DRAFT', status='draft')
        Application.objects.create(
            applicant=self.applicant, call=untouched, code='RG-BACKFILL-DRAFT-001',
            brief_description='no resolution yet', status='evaluated', resolution='',
        )

        no_apps_at_all = _make_call('RG-BACKFILL-EMPTY')

        from django.apps import apps as django_apps
        backfill_migration.backfill_resolutions_released(django_apps, None)

        already_resolved.refresh_from_db()
        untouched.refresh_from_db()
        no_apps_at_all.refresh_from_db()

        self.assertTrue(already_resolved.resolutions_released)
        self.assertIsNotNone(already_resolved.resolutions_released_at)
        self.assertFalse(untouched.resolutions_released)
        self.assertFalse(no_apps_at_all.resolutions_released)


class NotificationHoldTest(TestCase):
    """evaluations/utils.py:check_and_transition_application — item 2."""

    def setUp(self):
        _seed_templates()
        self.applicant = create_complete_user(email='hold-applicant@rg.test')
        self.evaluator = create_complete_user(email='hold-evaluator@rg.test')
        self.node = _make_node('RG-HOLD')
        self.equipment = Equipment.objects.create(node=self.node, name='Scanner', category='mri')
        self.nc = create_complete_user(email='hold-nc@rg.test')
        UserRole.objects.create(user=self.nc, role='node_coordinator', node=self.node, is_active=True)

    def _make_app(self, call):
        app = Application.objects.create(
            applicant=self.applicant, call=call, code=f'{call.code}-001',
            brief_description='hold test', status='under_evaluation',
        )
        RequestedAccess.objects.create(application=app, equipment=self.equipment, hours_requested=Decimal('5'))
        return app

    def test_unreleased_call_transitions_but_sends_no_email(self):
        call = _make_call('RG-HOLD-UNRELEASED', resolutions_released=False)
        app = self._make_app(call)
        _complete_evaluation(app, self.evaluator, 8)

        result = check_and_transition_application(app)
        app.refresh_from_db()

        self.assertTrue(result['transitioned'])
        self.assertEqual(app.status, 'evaluated')
        self.assertEqual(
            EmailLog.objects.filter(template__template_type='evaluations_complete').count(), 0
        )

    def test_released_call_still_sends_immediately(self):
        call = _make_call('RG-HOLD-RELEASED', resolutions_released=True)
        app = self._make_app(call)
        _complete_evaluation(app, self.evaluator, 8)

        check_and_transition_application(app)
        app.refresh_from_db()

        self.assertEqual(app.status, 'evaluated')
        self.assertEqual(
            EmailLog.objects.filter(
                template__template_type='evaluations_complete',
                related_application_id=app.id,
            ).count(),
            1,
        )


class ServiceLayerGateTest(TestCase):
    """applications/services/node_resolution.py — refusals #1 and #2."""

    def setUp(self):
        _seed_templates()
        self.applicant = create_complete_user(email='svc-applicant@rg.test')
        self.node = _make_node('RG-SVC')
        self.equipment = Equipment.objects.create(node=self.node, name='Scanner', category='mri')
        self.nc = create_complete_user(email='svc-nc@rg.test')
        UserRole.objects.create(user=self.nc, role='node_coordinator', node=self.node, is_active=True)

    def _make_app(self, call):
        app = Application.objects.create(
            applicant=self.applicant, call=call, code=f'{call.code}-001',
            brief_description='svc test', status='evaluated', final_score=Decimal('7.0'),
        )
        RequestedAccess.objects.create(application=app, equipment=self.equipment, hours_requested=Decimal('5'))
        return app

    def test_queue_excludes_unreleased_call(self):
        call = _make_call('RG-SVC-UNRELEASED', resolutions_released=False)
        self._make_app(call)

        pending = NodeResolutionService(node=self.node).get_applications_for_node_resolution()
        self.assertEqual(pending.count(), 0)

    def test_queue_includes_released_call(self):
        call = _make_call('RG-SVC-RELEASED', resolutions_released=True)
        app = self._make_app(call)

        pending = NodeResolutionService(node=self.node).get_applications_for_node_resolution()
        self.assertIn(app, pending)

    def test_apply_node_resolution_refuses_when_unreleased(self):
        call = _make_call('RG-SVC-APPLY-UNRELEASED', resolutions_released=False)
        app = self._make_app(call)

        service = NodeResolutionService(node=self.node)
        with self.assertRaises(ValidationError):
            service.apply_node_resolution(
                application=app, resolution='accept', comments='ok',
                approved_hours_dict={self.equipment.id: Decimal('5')}, user=self.nc,
            )
        self.assertFalse(NodeResolution.objects.filter(application=app).exists())

    def test_apply_node_resolution_succeeds_when_released(self):
        call = _make_call('RG-SVC-APPLY-RELEASED', resolutions_released=True)
        app = self._make_app(call)

        service = NodeResolutionService(node=self.node)
        result = service.apply_node_resolution(
            application=app, resolution='accept', comments='ok',
            approved_hours_dict={self.equipment.id: Decimal('5')}, user=self.nc,
        )
        self.assertTrue(result['success'])


class NodeResolutionReviewViewGateTest(TestCase):
    """applications/views.py:node_resolution_review — refusal #3."""

    def setUp(self):
        _seed_templates()
        self.applicant = create_complete_user(email='view-applicant@rg.test')
        self.node = _make_node('RG-VIEW')
        self.equipment = Equipment.objects.create(node=self.node, name='Scanner', category='mri')
        self.nc = create_complete_user(email='view-nc@rg.test')
        UserRole.objects.create(user=self.nc, role='node_coordinator', node=self.node, is_active=True)
        self.call = _make_call('RG-VIEW-CALL', resolutions_released=False)
        self.application = Application.objects.create(
            applicant=self.applicant, call=self.call, code='RG-VIEW-CALL-001',
            brief_description='view test', status='evaluated', final_score=Decimal('7.0'),
        )
        RequestedAccess.objects.create(application=self.application, equipment=self.equipment, hours_requested=Decimal('5'))
        self.client = Client()
        self.client.force_login(self.nc)

    def _url(self):
        return reverse('applications:node_resolution_review', kwargs={
            'application_id': self.application.id, 'node_id': self.node.id,
        })

    def test_get_refuses_with_message_not_404(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('applications:node_resolution_queue'))

    def test_post_refuses_and_creates_no_resolution(self):
        response = self.client.post(self._url(), {
            'resolution': 'accept',
            'comments': 'ok',
            f'hours_approved_{self.equipment.id}': '5',
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(NodeResolution.objects.filter(application=self.application).exists())

    def test_get_succeeds_once_released(self):
        self.call.resolutions_released = True
        self.call.save()
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)


class DashboardPendingResolutionCountTest(TestCase):
    """core/views.py dashboard — refusal #4."""

    def setUp(self):
        _seed_templates()
        self.coordinator = create_complete_user(email='dash-coord@rg.test')
        UserRole.objects.create(user=self.coordinator, role='coordinator', is_active=True)
        self.applicant = create_complete_user(email='dash-applicant@rg.test')
        self.client = Client()
        self.client.force_login(self.coordinator)

    def test_unreleased_evaluated_app_not_counted(self):
        call = _make_call('RG-DASH-UNRELEASED', resolutions_released=False)
        Application.objects.create(
            applicant=self.applicant, call=call, code='RG-DASH-UNRELEASED-001',
            brief_description='dash test', status='evaluated', resolution='',
        )
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.context['pending_resolution'], 0)

    def test_released_evaluated_app_is_counted(self):
        call = _make_call('RG-DASH-RELEASED', resolutions_released=True)
        Application.objects.create(
            applicant=self.applicant, call=call, code='RG-DASH-RELEASED-001',
            brief_description='dash test', status='evaluated', resolution='',
        )
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.context['pending_resolution'], 1)


class ReleaseActionTest(TestCase):
    """calls/views.py:call_release_resolutions — item 4 and idempotence."""

    def setUp(self):
        _seed_templates()
        self.coordinator = create_complete_user(email='release-coord@rg.test')
        UserRole.objects.create(user=self.coordinator, role='coordinator', is_active=True)
        self.applicant = create_complete_user(email='release-applicant@rg.test')
        self.node = _make_node('RG-RELEASE')
        self.equipment = Equipment.objects.create(node=self.node, name='Scanner', category='mri')
        self.nc = create_complete_user(email='release-nc@rg.test')
        UserRole.objects.create(user=self.nc, role='node_coordinator', node=self.node, is_active=True)

        self.call = _make_call('RG-RELEASE-CALL', resolutions_released=False)
        self.evaluated_app = Application.objects.create(
            applicant=self.applicant, call=self.call, code='RG-RELEASE-CALL-001',
            brief_description='release test', status='evaluated', final_score=Decimal('7.0'),
        )
        RequestedAccess.objects.create(application=self.evaluated_app, equipment=self.equipment, hours_requested=Decimal('5'))

        # A stuck application in another status must not block release.
        Application.objects.create(
            applicant=self.applicant, call=self.call, code='RG-RELEASE-CALL-002',
            brief_description='stuck app', status='rejected_feasibility',
        )

        self.client = Client()
        self.client.force_login(self.coordinator)

    def _url(self):
        return reverse('calls:release_resolutions', kwargs={'pk': self.call.pk})

    def test_get_refuses_when_no_evaluated_applications(self):
        empty_call = _make_call('RG-RELEASE-EMPTY')
        response = self.client.get(reverse('calls:release_resolutions', kwargs={'pk': empty_call.pk}))
        self.assertEqual(response.status_code, 302)

    def test_get_shows_preview_with_score_spread(self):
        evaluator_low = create_complete_user(email='release-eval-low@rg.test')
        evaluator_high = create_complete_user(email='release-eval-high@rg.test')
        _complete_evaluation(self.evaluated_app, evaluator_low, 2)
        _complete_evaluation(self.evaluated_app, evaluator_high, 9)

        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.evaluated_app.code)
        row = response.context['rows'][0]
        self.assertEqual(row['spread'], 7)
        self.assertTrue(row['high_spread'])

    def test_low_spread_not_flagged(self):
        evaluator_a = create_complete_user(email='release-eval-a@rg.test')
        evaluator_b = create_complete_user(email='release-eval-b@rg.test')
        _complete_evaluation(self.evaluated_app, evaluator_a, 6)
        _complete_evaluation(self.evaluated_app, evaluator_b, 8)

        response = self.client.get(self._url())
        row = response.context['rows'][0]
        self.assertEqual(row['spread'], 2)
        self.assertFalse(row['high_spread'])

    def test_no_spread_shown_honestly_for_single_evaluation(self):
        evaluator = create_complete_user(email='release-eval-solo@rg.test')
        _complete_evaluation(self.evaluated_app, evaluator, 8)

        response = self.client.get(self._url())
        row = response.context['rows'][0]
        self.assertIsNone(row['spread'])
        self.assertFalse(row['high_spread'])

    def test_post_releases_batch_and_sends_email(self):
        response = self.client.post(self._url())
        self.assertEqual(response.status_code, 302)

        self.call.refresh_from_db()
        self.assertTrue(self.call.resolutions_released)
        self.assertIsNotNone(self.call.resolutions_released_at)

        self.assertEqual(
            EmailLog.objects.filter(
                template__template_type='evaluations_complete',
                related_application_id=self.evaluated_app.id,
            ).count(),
            1,
        )

        # The gate now lets the node coordinator through.
        pending = NodeResolutionService(node=self.node).get_applications_for_node_resolution()
        self.assertIn(self.evaluated_app, pending)

    def test_post_twice_does_not_resend(self):
        self.client.post(self._url())
        response = self.client.post(self._url())
        self.assertEqual(response.status_code, 302)

        self.assertEqual(
            EmailLog.objects.filter(
                template__template_type='evaluations_complete',
                related_application_id=self.evaluated_app.id,
            ).count(),
            1,
        )

    def test_detail_page_shows_release_button_when_unreleased(self):
        response = self.client.get(reverse('calls:detail', kwargs={'pk': self.call.pk}))
        self.assertContains(response, 'Release to Nodes')

    def test_detail_page_hides_release_button_once_released(self):
        self.call.resolutions_released = True
        self.call.save()
        response = self.client.get(reverse('calls:detail', kwargs={'pk': self.call.pk}))
        self.assertNotContains(response, 'Release to Nodes')


class AwaitingApplicantFilterTest(TestCase):
    """#16 stretch — access_tracking's node-accepted-awaiting-applicant filter."""

    def setUp(self):
        self.node = _make_node('RG-FILTER')
        self.equipment = Equipment.objects.create(node=self.node, name='Scanner', category='mri')
        self.nc = create_complete_user(email='filter-nc@rg.test')
        UserRole.objects.create(user=self.nc, role='node_coordinator', node=self.node, is_active=True)
        self.applicant = create_complete_user(email='filter-applicant@rg.test')
        self.call = _make_call('RG-FILTER-CALL', resolutions_released=True)

        self.awaiting = Application.objects.create(
            applicant=self.applicant, call=self.call, code='RG-FILTER-CALL-001',
            brief_description='awaiting', status='accepted', accepted_by_applicant=None,
        )
        RequestedAccess.objects.create(application=self.awaiting, equipment=self.equipment, hours_requested=Decimal('5'))

        self.confirmed = Application.objects.create(
            applicant=self.applicant, call=self.call, code='RG-FILTER-CALL-002',
            brief_description='confirmed', status='accepted', accepted_by_applicant=True,
        )
        RequestedAccess.objects.create(application=self.confirmed, equipment=self.equipment, hours_requested=Decimal('5'))

        self.client = Client()
        self.client.force_login(self.nc)

    def test_unfiltered_shows_both_with_distinguishing_badges(self):
        response = self.client.get(reverse('access:access_tracking'))
        self.assertContains(response, self.awaiting.code)
        self.assertContains(response, self.confirmed.code)
        self.assertEqual(response.context['awaiting_applicant_count'], 1)
        self.assertContains(response, 'Accepted &mdash; Awaiting Applicant')

    def test_filter_shows_only_awaiting(self):
        response = self.client.get(reverse('access:access_tracking'), {'filter': 'awaiting_applicant'})
        self.assertContains(response, self.awaiting.code)
        self.assertNotContains(response, self.confirmed.code)
        self.assertTrue(response.context['show_awaiting_applicant_only'])


class LegacyResolutionServiceGateTest(TestCase):
    """applications/services/resolution.py — the centralized-coordinator
    ResolutionService is a second path to the evaluated -> resolved
    transition (reachable via the "Resolution" sidebar link every
    coordinator sees) and must respect the same gate as NodeResolutionService."""

    def setUp(self):
        self.applicant = create_complete_user(email='legacy-applicant@rg.test')

    def _make_evaluated_app(self, call, code, score='7.0'):
        return Application.objects.create(
            applicant=self.applicant, call=call, code=code,
            brief_description='legacy resolution test', status='evaluated',
            final_score=Decimal(score),
        )

    def test_apply_resolution_refuses_when_unreleased(self):
        call = _make_call('RG-LEGACY-UNRELEASED', resolutions_released=False)
        app = self._make_evaluated_app(call, 'RG-LEGACY-UNRELEASED-001')

        service = ResolutionService(call)
        with self.assertRaises(ValidationError):
            service.apply_resolution(app, 'accepted', comments='ok')
        app.refresh_from_db()
        self.assertEqual(app.status, 'evaluated')
        self.assertEqual(app.resolution, '')

    def test_apply_resolution_succeeds_when_released(self):
        call = _make_call('RG-LEGACY-RELEASED', resolutions_released=True)
        app = self._make_evaluated_app(call, 'RG-LEGACY-RELEASED-001')

        service = ResolutionService(call)
        result = service.apply_resolution(app, 'accepted', comments='ok')
        self.assertTrue(result['success'])
        app.refresh_from_db()
        self.assertEqual(app.status, 'accepted')

    def test_bulk_auto_allocate_refuses_when_unreleased(self):
        call = _make_call('RG-LEGACY-BULK-UNRELEASED', resolutions_released=False)
        self._make_evaluated_app(call, 'RG-LEGACY-BULK-UNRELEASED-001')

        service = ResolutionService(call)
        with self.assertRaises(ValidationError):
            service.bulk_auto_allocate()

    def test_finalize_resolution_refuses_when_unreleased(self):
        call = _make_call('RG-LEGACY-FINALIZE-UNRELEASED', resolutions_released=False)
        self._make_evaluated_app(call, 'RG-LEGACY-FINALIZE-UNRELEASED-001')

        service = ResolutionService(call)
        with self.assertRaises(ValidationError):
            service.finalize_resolution(user=None)
        call.refresh_from_db()
        self.assertFalse(call.is_resolution_locked)

    def test_resolution_dashboard_excludes_unreleased_calls(self):
        coordinator = create_complete_user(email='legacy-coord@rg.test')
        UserRole.objects.create(user=coordinator, role='coordinator', is_active=True)

        unreleased = _make_call('RG-LEGACY-DASH-UNRELEASED', resolutions_released=False)
        self._make_evaluated_app(unreleased, 'RG-LEGACY-DASH-UNRELEASED-001')
        released = _make_call('RG-LEGACY-DASH-RELEASED', resolutions_released=True)
        self._make_evaluated_app(released, 'RG-LEGACY-DASH-RELEASED-001')

        client = Client()
        client.force_login(coordinator)
        response = client.get(reverse('applications:resolution_dashboard'))
        calls_shown = [row['call'] for row in response.context['calls_with_stats']]
        self.assertNotIn(unreleased, calls_shown)
        self.assertIn(released, calls_shown)
