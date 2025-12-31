"""
Simple test suite for Phase 9: Publication Tracking

Tests the publication submission workflow:
- Applicants submit publications linked to accepted applications
- 6-month follow-up emails sent to applicants
- Coordinator verification of publications
"""

from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

from applications.models import Application
from access.models import Publication
from access.tasks import send_publication_followups

User = get_user_model()


class PublicationSubmissionTest(TestCase):
    """Test publication submission workflow."""

    def setUp(self):
        from calls.models import Call

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
            submission_start=timezone.now() - timedelta(days=200),
            submission_end=timezone.now() - timedelta(days=150),
            evaluation_deadline=timezone.now() - timedelta(days=120),
            execution_start=timezone.now() - timedelta(days=100),
            execution_end=timezone.now() + timedelta(days=50),
        )

        # Create accepted application (6 months ago)
        self.application = Application.objects.create(
            applicant=self.applicant,
            call=self.call,
            code='TEST-APP-001',
            brief_description='Test application',
            status='accepted',
            resolution='accepted',
            accepted_by_applicant=True,
            accepted_at=timezone.now() - timedelta(days=185),
            handoff_email_sent_at=timezone.now() - timedelta(days=185)
        )

    def test_applicant_can_submit_publication(self):
        """Test applicant can submit a publication for their accepted application."""
        self.client.force_login(self.applicant)

        response = self.client.post(
            '/access/publications/submit/',
            {
                'application': self.application.pk,
                'title': 'Novel Research Findings Using ReDIB',
                'authors': 'Smith, J., Doe, A.',
                'journal': 'Journal of Test Science',
                'publication_date': '2025-01-15',
                'doi': '10.1234/test.2025.001',
                'redib_acknowledged': True,
                'acknowledgment_text': 'This work acknowledges the use of ReDIB ICTS.'
            }
        )

        # Should redirect to publication list
        self.assertEqual(response.status_code, 302)

        # Check publication created
        publication = Publication.objects.get(application=self.application)
        self.assertEqual(publication.title, 'Novel Research Findings Using ReDIB')
        self.assertEqual(publication.reported_by, self.applicant)
        self.assertTrue(publication.redib_acknowledged)
        self.assertFalse(publication.verified)  # Not yet verified by coordinator

    def test_publication_linked_to_application(self):
        """Test publication is correctly linked to application."""
        publication = Publication.objects.create(
            application=self.application,
            title='Test Publication',
            authors='Test Author',
            journal='Test Journal',
            publication_date=timezone.now().date(),
            reported_by=self.applicant,
            redib_acknowledged=True
        )

        # Check reverse relationship
        self.assertEqual(publication.application, self.application)
        self.assertEqual(self.application.publications.count(), 1)
        self.assertEqual(self.application.publications.first(), publication)

    def test_form_shows_only_accepted_applications(self):
        """Test publication form only shows user's accepted applications."""
        from access.forms import PublicationForm

        # Create another application (not accepted)
        draft_app = Application.objects.create(
            applicant=self.applicant,
            call=self.call,
            code='TEST-APP-002',
            brief_description='Draft application',
            status='draft'
        )

        # Create form with user context
        form = PublicationForm(user=self.applicant)

        # Should only show accepted application
        available_apps = list(form.fields['application'].queryset)
        self.assertEqual(len(available_apps), 1)
        self.assertEqual(available_apps[0], self.application)
        self.assertNotIn(draft_app, available_apps)

    def test_publication_list_query_filters_by_user(self):
        """Test publication list query only returns user's publications."""
        # Create publication for our user
        pub1 = Publication.objects.create(
            application=self.application,
            title='User Publication',
            authors='Test Author',
            journal='Test Journal',
            publication_date=timezone.now().date(),
            reported_by=self.applicant,
            redib_acknowledged=True
        )

        # Create another user and publication
        other_user = User.objects.create_user(
            username='other_user',
            email='other@test.com',
            password='testpass123'
        )
        other_app = Application.objects.create(
            applicant=other_user,
            call=self.call,
            code='TEST-APP-003',
            brief_description='Other application',
            status='accepted',
            accepted_by_applicant=True
        )
        pub2 = Publication.objects.create(
            application=other_app,
            title='Other Publication',
            authors='Other Author',
            journal='Other Journal',
            publication_date=timezone.now().date(),
            reported_by=other_user,
            redib_acknowledged=True
        )

        # Query publications filtered by applicant
        user_publications = Publication.objects.filter(
            application__applicant=self.applicant
        )

        # Should only return user's publication
        self.assertEqual(user_publications.count(), 1)
        self.assertEqual(user_publications.first(), pub1)
        self.assertNotIn(pub2, user_publications)

    def test_acknowledgment_field_recorded(self):
        """Test that acknowledgment field is properly recorded."""
        # Create publication with acknowledgment
        publication = Publication.objects.create(
            application=self.application,
            title='Test Publication',
            authors='Test Author',
            journal='Test Journal',
            publication_date=timezone.now().date(),
            reported_by=self.applicant,
            redib_acknowledged=True,
            acknowledgment_text='ReDIB is acknowledged.'
        )

        # Check acknowledgment recorded
        publication.refresh_from_db()
        self.assertTrue(publication.redib_acknowledged)
        self.assertEqual(publication.acknowledgment_text, 'ReDIB is acknowledged.')


class FollowupEmailTest(TestCase):
    """Test 6-month publication follow-up emails."""

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
            submission_start=timezone.now() - timedelta(days=200),
            submission_end=timezone.now() - timedelta(days=150),
            evaluation_deadline=timezone.now() - timedelta(days=120),
            execution_start=timezone.now() - timedelta(days=100),
            execution_end=timezone.now() + timedelta(days=50),
        )

    def test_followup_sent_after_6_months(self):
        """Test follow-up email sent 6 months after handoff."""
        # Create application completed ~6 months ago (within the weekly window)
        application = Application.objects.create(
            applicant=self.applicant,
            call=self.call,
            code='TEST-APP-004',
            brief_description='Test application',
            status='accepted',
            accepted_by_applicant=True,
            handoff_email_sent_at=timezone.now() - timedelta(days=182)  # ~6 months
        )

        # Run follow-up task
        result = send_publication_followups()

        # Should report sending email
        self.assertIsInstance(result, str)
        self.assertIn('1', result)  # 1 email sent
        self.assertIn('follow-up', result.lower())

    def test_no_followup_if_publication_exists(self):
        """Test no follow-up sent if publication already reported."""
        # Create application completed ~6 months ago
        application = Application.objects.create(
            applicant=self.applicant,
            call=self.call,
            code='TEST-APP-005',
            brief_description='Test application',
            status='accepted',
            accepted_by_applicant=True,
            handoff_email_sent_at=timezone.now() - timedelta(days=182)
        )

        # Add a publication
        Publication.objects.create(
            application=application,
            title='Already Reported',
            authors='Test Author',
            journal='Test Journal',
            publication_date=timezone.now().date(),
            reported_by=self.applicant,
            redib_acknowledged=True
        )

        # Run follow-up task
        result = send_publication_followups()

        # Should not send email (publication already exists)
        self.assertIn('0', result)  # 0 emails sent

    def test_no_followup_if_not_accepted(self):
        """Test no follow-up sent if application not accepted by applicant."""
        # Create application that wasn't accepted by applicant
        application = Application.objects.create(
            applicant=self.applicant,
            call=self.call,
            code='TEST-APP-006',
            brief_description='Test application',
            status='accepted',
            accepted_by_applicant=False,  # Not accepted
            handoff_email_sent_at=timezone.now() - timedelta(days=182)
        )

        # Run follow-up task
        result = send_publication_followups()

        # Should not send email
        self.assertIn('0', result)

    def test_followup_task_runs_without_error(self):
        """Test follow-up task runs successfully with no eligible applications."""
        # No applications in database

        # Run task - should not raise errors
        result = send_publication_followups()

        # Should return a summary string
        self.assertIsInstance(result, str)
        self.assertIn('0', result)


class CoordinatorVerificationTest(TestCase):
    """Test coordinator verification of publications."""

    def setUp(self):
        from calls.models import Call

        # Create test users
        self.applicant = User.objects.create_user(
            username='test_applicant3',
            email='applicant3@test.com',
            password='testpass123'
        )

        self.coordinator = User.objects.create_user(
            username='coordinator',
            email='coordinator@test.com',
            password='testpass123',
            is_staff=True
        )

        # Create test call
        self.call = Call.objects.create(
            code='TEST-2025-3',
            title='Test Call 3',
            submission_start=timezone.now() - timedelta(days=200),
            submission_end=timezone.now() - timedelta(days=150),
            evaluation_deadline=timezone.now() - timedelta(days=120),
            execution_start=timezone.now() - timedelta(days=100),
            execution_end=timezone.now() + timedelta(days=50),
        )

        # Create accepted application
        self.application = Application.objects.create(
            applicant=self.applicant,
            call=self.call,
            code='TEST-APP-007',
            brief_description='Test application',
            status='accepted',
            accepted_by_applicant=True
        )

    def test_publication_verified_by_coordinator(self):
        """Test coordinator can verify a publication."""
        publication = Publication.objects.create(
            application=self.application,
            title='Test Publication',
            authors='Test Author',
            journal='Test Journal',
            publication_date=timezone.now().date(),
            reported_by=self.applicant,
            redib_acknowledged=True,
            verified=False
        )

        # Coordinator verifies
        publication.verified = True
        publication.verified_by = self.coordinator
        publication.verified_at = timezone.now()
        publication.save()

        # Check verification recorded
        publication.refresh_from_db()
        self.assertTrue(publication.verified)
        self.assertEqual(publication.verified_by, self.coordinator)
        self.assertIsNotNone(publication.verified_at)


class PhaseIntegrationTest(TestCase):
    """End-to-end test of Phase 9 workflow."""

    def test_full_publication_workflow(self):
        """Test complete flow: acceptance → 6 months → follow-up → submission → verification."""
        from calls.models import Call

        # Create test users
        applicant = User.objects.create_user(
            username='test_applicant4',
            email='applicant4@test.com',
            password='testpass123'
        )

        coordinator = User.objects.create_user(
            username='coordinator2',
            email='coordinator2@test.com',
            password='testpass123',
            is_staff=True
        )

        # Create test call
        call = Call.objects.create(
            code='TEST-2025-4',
            title='Test Call 4',
            submission_start=timezone.now() - timedelta(days=200),
            submission_end=timezone.now() - timedelta(days=150),
            evaluation_deadline=timezone.now() - timedelta(days=120),
            execution_start=timezone.now() - timedelta(days=100),
            execution_end=timezone.now() + timedelta(days=50),
        )

        # 1. Create accepted application (6 months ago)
        application = Application.objects.create(
            applicant=applicant,
            call=call,
            code='TEST-APP-008',
            brief_description='Integration test application',
            status='accepted',
            resolution='accepted',
            accepted_by_applicant=True,
            accepted_at=timezone.now() - timedelta(days=185),
            handoff_email_sent_at=timezone.now() - timedelta(days=185)
        )

        # 2. Follow-up task runs (would send email)
        result = send_publication_followups()
        self.assertIn('1', result)  # 1 follow-up sent

        # 3. Applicant submits publication
        client = Client()
        client.force_login(applicant)

        response = client.post(
            '/access/publications/submit/',
            {
                'application': application.pk,
                'title': 'Integration Test Publication',
                'authors': 'Integration Test Author',
                'journal': 'Integration Test Journal',
                'publication_date': '2025-01-15',
                'doi': '10.1234/integration.test',
                'redib_acknowledged': True,
                'acknowledgment_text': 'ReDIB ICTS is acknowledged.'
            }
        )

        self.assertEqual(response.status_code, 302)

        # 4. Check publication created
        publication = Publication.objects.get(application=application)
        self.assertEqual(publication.title, 'Integration Test Publication')
        self.assertFalse(publication.verified)

        # 5. Coordinator verifies publication
        publication.verified = True
        publication.verified_by = coordinator
        publication.verified_at = timezone.now()
        publication.save()

        # 6. Check final state
        publication.refresh_from_db()
        self.assertTrue(publication.verified)
        self.assertEqual(publication.verified_by, coordinator)
        self.assertTrue(publication.redib_acknowledged)

        # Success!
