"""
Integration tests for fixes-batch-2 Phase 4 (batch 2-B): pending /
waitlist full lifecycle.

- Pending resolution sets an acceptance_deadline.
- Applicant can accept a pending offer via application_acceptance,
  which sets accepted_by_applicant=True but does NOT fire the handoff.
- Node coordinator can promote a pending + accepted application via
  the promote_waitlisted view; promotion flips status and resolution
  to accepted, refreshes resolution_date, clears acceptance_deadline,
  and fires the handoff email.
- Non-node-coord callers get a permission error and no state change.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from applications.models import Application, RequestedAccess
from applications.services import NodeResolutionService
from calls.models import Call
from communications.models import EmailLog, EmailTemplate
from core.models import Equipment, Node, Organization, UserRole

User = get_user_model()


def _make_complete_user(**overrides):
    """Helper: create a User whose profile passes ProfileCompletionMiddleware."""
    org, _ = Organization.objects.get_or_create(
        name='Test Org', defaults={'organization_type': 'other'},
    )
    kwargs = dict(
        username=overrides.pop('username', 'u'),
        email=overrides.pop('email', 'u@test.com'),
        password='x',
        first_name='First',
        last_name='Last',
    )
    kwargs.update(overrides)
    user = User.objects.create_user(**kwargs)
    user.phone = '+34 900 000 000'
    user.organization = org
    user.position = 'Researcher'
    user.save()
    return user


def _seed_templates():
    for tt in ('resolution_accepted', 'resolution_pending', 'resolution_rejected',
               'handoff_notification'):
        EmailTemplate.objects.get_or_create(
            template_type=tt,
            defaults={
                'subject': f'[test] {tt}',
                'html_content': '<p>{{ application_code }}</p>',
                'text_content': '{{ application_code }}',
                'is_active': True,
            },
        )


class PendingWaitlistLifecycleTest(TestCase):
    def setUp(self):
        _seed_templates()
        self.applicant = _make_complete_user(username='a1', email='a1@test.com')
        self.node = Node.objects.create(code='N1', name='Node 1', location='Here')
        self.equipment = Equipment.objects.create(
            node=self.node, name='Scanner', category='mri',
        )
        self.call = Call.objects.create(
            code='CALL-W', title='Waitlist Call',
            submission_start=timezone.now() - timedelta(days=10),
            submission_end=timezone.now() + timedelta(days=10),
            evaluation_deadline=timezone.now() + timedelta(days=30),
            execution_start=timezone.now() + timedelta(days=40),
            execution_end=timezone.now() + timedelta(days=60),
        )
        self.application = Application.objects.create(
            applicant=self.applicant, call=self.call, code='APP-W1',
            brief_description='waitlist test', status='evaluated',
            final_score=Decimal('6.0'),
            applicant_email='a1@test.com',
        )
        self.req = RequestedAccess.objects.create(
            application=self.application, equipment=self.equipment,
            hours_requested=Decimal('8'),
        )
        self.nc = _make_complete_user(username='nc1', email='nc1@test.com')
        UserRole.objects.create(
            user=self.nc, role='node_coordinator', node=self.node, is_active=True,
        )
        self.outsider = _make_complete_user(username='outsider', email='o@test.com')

    def _resolve_as_pending(self):
        """Have the node coord submit a waitlist resolution, driving
        aggregation through to application.resolution='pending'."""
        service = NodeResolutionService(node=self.node)
        service.apply_node_resolution(
            application=self.application,
            resolution='waitlist',
            comments='no immediate slot',
            user=self.nc,
            approved_hours_dict={self.equipment.id: Decimal('8')},
        )
        self.application.refresh_from_db()

    def test_pending_resolution_sets_acceptance_deadline(self):
        self._resolve_as_pending()
        self.assertEqual(self.application.resolution, 'pending')
        self.assertEqual(self.application.status, 'pending')
        self.assertIsNotNone(self.application.acceptance_deadline)

    def test_applicant_accepting_pending_does_not_fire_handoff(self):
        self._resolve_as_pending()
        c = Client()
        c.force_login(self.applicant)
        resp = c.post(reverse('applications:application_acceptance',
                              kwargs={'pk': self.application.pk}),
                      {'action': 'accept'})
        self.assertEqual(resp.status_code, 302)
        self.application.refresh_from_db()
        self.assertTrue(self.application.accepted_by_applicant)
        self.assertEqual(self.application.status, 'pending')
        self.assertIsNone(self.application.handoff_email_sent_at)
        handoff_logs = EmailLog.objects.filter(
            template__template_type='handoff_notification',
            related_application_id=self.application.id,
        )
        self.assertEqual(handoff_logs.count(), 0)

    def test_node_coord_can_promote_waitlisted_application(self):
        self._resolve_as_pending()
        # Applicant accepts the waitlist offer
        c = Client()
        c.force_login(self.applicant)
        c.post(reverse('applications:application_acceptance',
                       kwargs={'pk': self.application.pk}),
               {'action': 'accept'})
        # Node coord promotes
        EmailLog.objects.all().delete()  # clear resolution_pending row
        c2 = Client()
        c2.force_login(self.nc)
        resp = c2.post(reverse('applications:promote_waitlisted',
                               kwargs={'pk': self.application.pk}))
        self.assertEqual(resp.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'accepted')
        self.assertEqual(self.application.resolution, 'accepted')
        self.assertIsNone(self.application.acceptance_deadline)
        self.assertIsNotNone(self.application.handoff_email_sent_at)
        # resolution_accepted + handoff were dispatched
        templates_used = set(
            EmailLog.objects.filter(
                related_application_id=self.application.id
            ).values_list('template__template_type', flat=True)
        )
        self.assertIn('resolution_accepted', templates_used)
        self.assertIn('handoff_notification', templates_used)

    def test_promote_fails_when_applicant_has_not_accepted(self):
        self._resolve_as_pending()
        c = Client()
        c.force_login(self.nc)
        resp = c.post(reverse('applications:promote_waitlisted',
                              kwargs={'pk': self.application.pk}))
        self.assertEqual(resp.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'pending',
                         "Promotion must not succeed before applicant accepts")

    def test_outsider_cannot_promote(self):
        self._resolve_as_pending()
        self.application.accepted_by_applicant = True
        self.application.save()
        c = Client()
        c.force_login(self.outsider)
        resp = c.post(reverse('applications:promote_waitlisted',
                              kwargs={'pk': self.application.pk}))
        self.assertEqual(resp.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'pending')
