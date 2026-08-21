"""
Integration tests for fixes-batch-2 Phase 1 (batch 2-A):

- #24: Rejected node resolution must zero hours_approved on that node's
  RequestedAccess rows.
- #26: Resolution, handoff, and reminder emails must prefer
  Application.applicant_email (the form-declared PI contact) over the
  submitting user's account email.
- #28: notify_coordinator_evaluations_complete must NOT email the main
  ReDIB coordinator — only node coordinators of involved nodes.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from applications.models import Application, RequestedAccess
from applications.services import NodeResolutionService
from calls.models import Call
from communications.models import EmailLog, EmailTemplate
from core.models import Equipment, Node, Organization, UserRole


def _make_node(code, location='Here'):
    """Helper: create a node + minimal host org (Node.organization is required)."""
    org, _ = Organization.objects.get_or_create(
        name=f'{code} Host',
        defaults={'organization_type': 'pro', 'iso2': 'ES', 'country': 'Spain'},
    )
    return Node.objects.create(code=code, organization=org, location=location)

User = get_user_model()


def _seed_resolution_templates():
    """Minimal stubs for the three resolution templates this test fires."""
    for tt in ('resolution_accepted', 'resolution_pending', 'resolution_rejected',
               'evaluations_complete', 'handoff_notification'):
        EmailTemplate.objects.get_or_create(
            template_type=tt,
            defaults={
                'subject': f'[test] {tt}',
                'html_content': '<p>{{ application_code }}</p>',
                'text_content': '{{ application_code }}',
                'is_active': True,
            },
        )


class NodeRejectZerosHoursTest(TestCase):
    """Issue #24 — rejecting at a node must not leave approved hours behind."""

    def setUp(self):
        _seed_resolution_templates()
        self.applicant = User.objects.create_user(
            username='a1', email='pi-account@test.com', password='x'
        )
        self.node = _make_node('N1')
        self.equipment = Equipment.objects.create(
            node=self.node, name='Scanner', category='mri'
        )
        self.call = Call.objects.create(
            code='CALL-1', title='T',
            submission_start=timezone.now() - timedelta(days=10),
            submission_end=timezone.now() + timedelta(days=10),
            evaluation_deadline=timezone.now() + timedelta(days=30),
            execution_start=timezone.now() + timedelta(days=40),
            execution_end=timezone.now() + timedelta(days=60),
            resolutions_released=True,
        )
        self.application = Application.objects.create(
            applicant=self.applicant, call=self.call, code='APP-R1',
            brief_description='reject test', status='evaluated',
            final_score=Decimal('5.0'),
        )
        self.req = RequestedAccess.objects.create(
            application=self.application, equipment=self.equipment,
            hours_requested=Decimal('10'),
        )
        self.nc = User.objects.create_user(
            username='nc1', email='nc1@test.com', password='x'
        )
        UserRole.objects.create(
            user=self.nc, role='node_coordinator', node=self.node, is_active=True
        )

    def test_reject_forces_hours_approved_to_zero(self):
        """Even if the form POSTed hours_requested (the prefilled default),
        the service must store 0 for a reject."""
        service = NodeResolutionService(node=self.node)
        service.apply_node_resolution(
            application=self.application,
            resolution='reject',
            comments='not feasible',
            user=self.nc,
            approved_hours_dict={self.equipment.id: Decimal('10')},
        )
        self.req.refresh_from_db()
        self.assertEqual(self.req.hours_approved, Decimal('0'))


class ResolutionEmailPrefersApplicantEmailTest(TestCase):
    """Issue #26 — resolution email should target applicant_email, not
    the submitting account email, when they differ."""

    def setUp(self):
        _seed_resolution_templates()
        self.submitter = User.objects.create_user(
            username='submitter', email='office@test.com', password='x'
        )
        self.node = _make_node('N2')
        self.equipment = Equipment.objects.create(
            node=self.node, name='MRI', category='mri'
        )
        self.call = Call.objects.create(
            code='CALL-2', title='T2',
            submission_start=timezone.now() - timedelta(days=10),
            submission_end=timezone.now() + timedelta(days=10),
            evaluation_deadline=timezone.now() + timedelta(days=30),
            execution_start=timezone.now() + timedelta(days=40),
            execution_end=timezone.now() + timedelta(days=60),
            resolutions_released=True,
        )
        self.application = Application.objects.create(
            applicant=self.submitter, call=self.call, code='APP-E1',
            brief_description='email target test', status='evaluated',
            final_score=Decimal('8.0'),
            # Snapshot fields: the stated PI is NOT the submitting account
            applicant_email='pi@example.org',
            applicant_name='PI Person',
        )
        RequestedAccess.objects.create(
            application=self.application, equipment=self.equipment,
            hours_requested=Decimal('10'),
        )
        self.nc = User.objects.create_user(
            username='nc2', email='nc2@test.com', password='x'
        )
        UserRole.objects.create(
            user=self.nc, role='node_coordinator', node=self.node, is_active=True
        )

    def test_accept_resolution_emails_applicant_email(self):
        service = NodeResolutionService(node=self.node)
        service.apply_node_resolution(
            application=self.application,
            resolution='accept',
            comments='ok',
            user=self.nc,
            approved_hours_dict={self.equipment.id: Decimal('10')},
        )
        log = EmailLog.objects.filter(
            template__template_type='resolution_accepted',
            related_application_id=self.application.id,
        ).order_by('-created_at').first()
        self.assertIsNotNone(log, "No resolution_accepted EmailLog row was created")
        self.assertEqual(log.recipient_email, 'pi@example.org')

    def test_resolution_falls_back_to_account_email_when_applicant_email_blank(self):
        self.application.applicant_email = ''
        self.application.save(update_fields=['applicant_email'])
        service = NodeResolutionService(node=self.node)
        service.apply_node_resolution(
            application=self.application,
            resolution='accept',
            comments='ok',
            user=self.nc,
            approved_hours_dict={self.equipment.id: Decimal('10')},
        )
        log = EmailLog.objects.filter(
            template__template_type='resolution_accepted',
            related_application_id=self.application.id,
        ).order_by('-created_at').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.recipient_email, 'office@test.com')


class EvaluationsCompleteSkipsMainCoordinatorTest(TestCase):
    """Issue #28 — the main ReDIB coordinator should not receive the
    per-application evaluations-complete email; only node coordinators
    of involved nodes should."""

    def setUp(self):
        _seed_resolution_templates()
        self.applicant = User.objects.create_user(
            username='a3', email='a3@test.com', password='x'
        )
        self.node = _make_node('N3')
        self.equipment = Equipment.objects.create(
            node=self.node, name='PET', category='pet_ct'
        )
        self.call = Call.objects.create(
            code='CALL-3', title='T3',
            submission_start=timezone.now() - timedelta(days=10),
            submission_end=timezone.now() + timedelta(days=10),
            evaluation_deadline=timezone.now() + timedelta(days=30),
            execution_start=timezone.now() + timedelta(days=40),
            execution_end=timezone.now() + timedelta(days=60),
        )
        self.application = Application.objects.create(
            applicant=self.applicant, call=self.call, code='APP-EV',
            brief_description='evals complete test', status='under_evaluation',
            applicant_name='A Three',
        )
        RequestedAccess.objects.create(
            application=self.application, equipment=self.equipment,
            hours_requested=Decimal('6'),
        )
        self.redib_coord = User.objects.create_user(
            username='rc', email='redib-coord@test.com', password='x'
        )
        UserRole.objects.create(
            user=self.redib_coord, role='coordinator', is_active=True
        )
        self.nc = User.objects.create_user(
            username='nc3', email='nc3@test.com', password='x'
        )
        UserRole.objects.create(
            user=self.nc, role='node_coordinator', node=self.node, is_active=True
        )

    def test_only_node_coordinators_receive_per_app_email(self):
        from evaluations.tasks import notify_coordinator_evaluations_complete
        notify_coordinator_evaluations_complete(self.application.id, 8.5)

        recipients = set(
            EmailLog.objects.filter(
                template__template_type='evaluations_complete',
                related_application_id=self.application.id,
            ).values_list('recipient_email', flat=True)
        )
        self.assertIn('nc3@test.com', recipients)
        self.assertNotIn(
            'redib-coord@test.com', recipients,
            "ReDIB coordinator must not receive per-app evaluations_complete",
        )
