"""
Tests for the nine rehearsal-polish fixes (backlog #67, #69-#71, #75-#79).

One test class per item; see docs/handoffs/rehearsal-polish.md for the
rehearsal evidence and decisions behind each fix.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from applications.models import Application, RequestedAccess
from calls.models import Call, CallEquipmentAllocation
from core.models import Organization, Node, Equipment, UserRole
from core.test_utils import create_complete_user
from evaluations.models import Evaluation

User = get_user_model()


def _make_call(**overrides):
    defaults = dict(
        code='CALL-RP1', title='Rehearsal Polish Call',
        submission_start=timezone.now() - timedelta(days=1),
        submission_end=timezone.now() + timedelta(days=30),
        evaluation_deadline=timezone.now() + timedelta(days=60),
        execution_start=timezone.now() + timedelta(days=70),
        execution_end=timezone.now() + timedelta(days=100),
        status='open',
    )
    defaults.update(overrides)
    return Call.objects.create(**defaults)


class FeasibilityQueueYourNodesTests(TestCase):
    """P1 — #77: 'Your Nodes' card should name the node, not render a bare badge."""

    def setUp(self):
        org = Organization.objects.create(
            name='CIC biomaGUNE', country='ES', organization_type='university'
        )
        self.node = Node.objects.create(code='CICBIO', organization=org, location='San Sebastián')
        self.coordinator = create_complete_user('nc@test.com')
        UserRole.objects.create(user=self.coordinator, role='node_coordinator', node=self.node, is_active=True)
        self.client = Client()
        self.client.force_login(self.coordinator)

    def test_your_nodes_card_names_the_node(self):
        resp = self.client.get(reverse('applications:feasibility_queue'))
        self.assertContains(resp, f'{self.node.code} - {self.node.name}')


class BlindEvaluationFormProjectTitleTests(TestCase):
    """P2 — #78: blind form should say the title is withheld, not print '—'."""

    def setUp(self):
        org = Organization.objects.create(
            name='Applicant Org', country='ES', organization_type='university'
        )
        self.applicant = create_complete_user('applicant@test.com', organization=org)
        self.evaluator = create_complete_user('evaluator@test.com', organization=org)
        UserRole.objects.create(user=self.evaluator, role='evaluator', is_active=True)
        self.call = _make_call(code='CALL-RP2')
        self.app = Application.objects.create(
            applicant=self.applicant, call=self.call, code='APP-RP2-1',
            status='under_evaluation', project_name='A Secret Project Title',
            brief_description='Summary text',
        )
        self.evaluation = Evaluation.objects.create(application=self.app, evaluator=self.evaluator)
        self.client = Client()
        self.client.force_login(self.evaluator)

    def test_project_title_marked_withheld_not_the_real_title(self):
        resp = self.client.get(reverse('evaluations:evaluation_detail', kwargs={'pk': self.evaluation.pk}))
        self.assertContains(resp, 'withheld for blind review')
        self.assertNotContains(resp, 'A Secret Project Title')


class CompetitiveFundingBannerTests(TestCase):
    """P4 — #75: banner wording must match the actual reject-availability rule."""

    def setUp(self):
        org = Organization.objects.create(
            name='Node Host Org', country='ES', organization_type='university'
        )
        self.node = Node.objects.create(code='CICBIO', organization=org, location='San Sebastián')
        self.coordinator = create_complete_user('nc-rp4@test.com')
        UserRole.objects.create(user=self.coordinator, role='node_coordinator', node=self.node, is_active=True)
        self.applicant = create_complete_user('applicant-rp4@test.com')
        self.evaluator = create_complete_user('evaluator-rp4@test.com')
        self.call = _make_call(code='CALL-RP4', resolutions_released=True)
        self.app = Application.objects.create(
            applicant=self.applicant, call=self.call, code='APP-RP4-1',
            status='evaluated', has_competitive_funding=True,
            brief_description='Summary text',
        )
        self.client = Client()
        self.client.force_login(self.coordinator)

    def _get(self):
        return self.client.get(reverse('applications:node_resolution_review', kwargs={
            'application_id': self.app.pk, 'node_id': self.node.pk,
        }))

    def test_no_denied_evaluation_says_cannot_reject(self):
        resp = self._get()
        self.assertContains(resp, 'cannot reject')
        self.assertNotContains(resp, 'rejection is available')

    def test_denied_evaluation_says_rejection_available(self):
        Evaluation.objects.create(
            application=self.app, evaluator=self.evaluator,
            recommendation='denied', completed_at=timezone.now(),
        )
        resp = self._get()
        self.assertContains(resp, 'rejection is available')
        self.assertNotContains(resp, 'cannot reject')


class ResolutionDashboardGatedCallsTests(TestCase):
    """P5 — #79: a gated (unreleased) call should be named, not hidden as if resolved."""

    def setUp(self):
        self.coordinator = create_complete_user('coord-rp5@test.com')
        UserRole.objects.create(user=self.coordinator, role='coordinator', is_active=True)
        self.applicant = create_complete_user('applicant-rp5@test.com')
        self.call = _make_call(code='CALL-RP5', resolutions_released=False)
        Application.objects.create(
            applicant=self.applicant, call=self.call, code='APP-RP5-1',
            status='evaluated', brief_description='Summary text',
        )
        self.client = Client()
        self.client.force_login(self.coordinator)

    def test_gated_call_named_and_linked(self):
        resp = self.client.get(reverse('applications:resolution_dashboard'))
        self.assertContains(resp, 'waiting on you to release resolutions')
        self.assertContains(resp, self.call.code)
        self.assertContains(resp, reverse('calls:detail', kwargs={'pk': self.call.pk}))
