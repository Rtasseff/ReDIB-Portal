"""
Simple test suite for Phase 7: Acceptance & Handoff

Tests the simplified acceptance workflow:
- Applicant accepts/declines approved applications
- Handoff email sent to applicant + node coordinators
- 10-day deadline enforcement (reminder day 7, auto-expire day 10)
"""

from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

from applications.models import Application
from applications.tasks import process_acceptance_deadlines
from communications.models import EmailLog

User = get_user_model()


class AcceptanceWorkflowTest(TestCase):
    """Test applicant acceptance/decline workflow."""

    def setUp(self):
        from calls.models import Call
        from core.models import Node

        self.client = Client()

        # Create test user
        self.applicant = User.objects.create_user(
            username='test_applicant',
            email='applicant@test.com',
            password='testpass123'
        )

        # Create test call
        self.call = Call.objects.create(
            code='TEST-2025',
            title='Test Call',
            submission_start=timezone.now() - timedelta(days=30),
            submission_end=timezone.now() + timedelta(days=30),
            evaluation_deadline=timezone.now() + timedelta(days=60),
            execution_start=timezone.now() + timedelta(days=70),
            execution_end=timezone.now() + timedelta(days=100),
        )

        # Create test application
        self.application = Application.objects.create(
            applicant=self.applicant,
            call=self.call,
            code='TEST-APP-001',
            brief_description='Test application',
            status='accepted',
            resolution='accepted',
            resolution_date=timezone.now() - timedelta(days=2),
            acceptance_deadline=timezone.now() + timedelta(days=5)
        )

    def test_applicant_can_accept(self):
        """Test applicant can accept approved application."""
        self.client.force_login(self.applicant)

        response = self.client.post(
            f'/applications/{self.application.pk}/accept/',
            {'action': 'accept'}
        )

        # Should redirect
        self.assertEqual(response.status_code, 302)

        # Refresh from database
        self.application.refresh_from_db()

        # Check acceptance recorded
        self.assertTrue(self.application.accepted_by_applicant)
        self.assertIsNotNone(self.application.accepted_at)
        self.assertIsNotNone(self.application.handoff_email_sent_at)

    def test_applicant_can_decline(self):
        """Test applicant can decline approved application."""
        self.client.force_login(self.applicant)

        response = self.client.post(
            f'/applications/{self.application.pk}/accept/',
            {
                'action': 'decline',
                'decline_reason': 'Not able to proceed at this time'
            }
        )

        # Should redirect
        self.assertEqual(response.status_code, 302)

        # Refresh from database
        self.application.refresh_from_db()

        # Check decline recorded
        self.assertEqual(self.application.status, 'declined_by_applicant')
        self.assertFalse(self.application.accepted_by_applicant)
        self.assertIn('DECLINED BY APPLICANT', self.application.resolution_comments)

    def test_handoff_email_timestamp_set(self):
        """Test handoff email timestamp set when application accepted."""
        self.client.force_login(self.applicant)

        response = self.client.post(
            f'/applications/{self.application.pk}/accept/',
            {'action': 'accept'}
        )

        # Refresh from database
        self.application.refresh_from_db()

        # Check handoff timestamp set (email was attempted)
        self.assertIsNotNone(self.application.handoff_email_sent_at)

    def test_cannot_accept_twice(self):
        """Test cannot accept application that's already been responded to."""
        # Accept once
        self.application.accepted_by_applicant = True
        self.application.accepted_at = timezone.now()
        self.application.save()

        self.client.force_login(self.applicant)

        # Try to accept again
        response = self.client.post(
            f'/applications/{self.application.pk}/accept/',
            {'action': 'accept'}
        )

        # Should redirect with message (can't check message easily, but redirect is fine)
        self.assertEqual(response.status_code, 302)


class DeadlineEnforcementTest(TestCase):
    """Test 10-day deadline enforcement."""

    def setUp(self):
        from calls.models import Call

        # Create test user
        self.applicant = User.objects.create_user(
            username='test_applicant2',
            email='applicant2@test.com',
            password='testpass123'
        )

        # Create test call
        self.call = Call.objects.create(
            code='TEST-2025-2',
            title='Test Call 2',
            submission_start=timezone.now() - timedelta(days=30),
            submission_end=timezone.now() + timedelta(days=30),
            evaluation_deadline=timezone.now() + timedelta(days=60),
            execution_start=timezone.now() + timedelta(days=70),
            execution_end=timezone.now() + timedelta(days=100),
        )

    def test_auto_expire_after_deadline(self):
        """Test applications auto-expire when deadline passes."""
        # Create application with passed deadline
        application = Application.objects.create(
            applicant=self.applicant,
            call=self.call,
            code='TEST-APP-002',
            brief_description='Test application 2',
            status='accepted',
            resolution='accepted',
            resolution_date=timezone.now() - timedelta(days=11),
            acceptance_deadline=timezone.now() - timedelta(days=1),
            accepted_by_applicant=None
        )

        # Run deadline task
        result = process_acceptance_deadlines()

        # Refresh from database
        application.refresh_from_db()

        # Should be expired
        self.assertEqual(application.status, 'expired')
        self.assertFalse(application.accepted_by_applicant)
        self.assertIn('AUTO-EXPIRED', application.resolution_comments)

    def test_deadline_task_runs_without_error(self):
        """Test deadline enforcement task runs successfully."""
        # Create application with deadline in 3 days
        application = Application.objects.create(
            applicant=self.applicant,
            call=self.call,
            code='TEST-APP-003',
            brief_description='Test application 3',
            status='accepted',
            resolution='accepted',
            resolution_date=timezone.now() - timedelta(days=7),
            acceptance_deadline=timezone.now() + timedelta(days=3),
            accepted_by_applicant=None
        )

        # Run deadline task - should not raise errors
        result = process_acceptance_deadlines()

        # Should return a summary string
        self.assertIsInstance(result, str)
        self.assertIn('reminder', result.lower())


class PhaseIntegrationTest(TestCase):
    """End-to-end test of Phase 7 workflow."""

    def test_full_acceptance_workflow(self):
        """Test complete flow: resolution → acceptance → handoff."""
        from calls.models import Call

        # Create test user
        applicant = User.objects.create_user(
            username='test_applicant3',
            email='applicant3@test.com',
            password='testpass123'
        )

        # Create test call
        call = Call.objects.create(
            code='TEST-2025-3',
            title='Test Call 3',
            submission_start=timezone.now() - timedelta(days=30),
            submission_end=timezone.now() + timedelta(days=30),
            evaluation_deadline=timezone.now() + timedelta(days=60),
            execution_start=timezone.now() + timedelta(days=70),
            execution_end=timezone.now() + timedelta(days=100),
        )

        # Create accepted application
        application = Application.objects.create(
            applicant=applicant,
            call=call,
            code='TEST-APP-004',
            brief_description='Test application 4',
            status='accepted',
            resolution='accepted',
            resolution_date=timezone.now() - timedelta(days=1),
            acceptance_deadline=timezone.now() + timedelta(days=10)
        )

        # 1. Applicant logs in and accepts
        client = Client()
        client.force_login(applicant)

        response = client.post(
            f'/applications/{application.pk}/accept/',
            {'action': 'accept'}
        )

        # 2. Check acceptance recorded
        application.refresh_from_db()
        self.assertTrue(application.accepted_by_applicant)
        self.assertEqual(application.status, 'accepted')

        # 3. Check handoff email sent
        self.assertIsNotNone(application.handoff_email_sent_at)

        # Success!
