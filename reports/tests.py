"""
Test suite for Phase 10: Reporting & Statistics

Tests the reporting dashboard and Excel export functionality.
"""

from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

from calls.models import Call
from applications.models import Application
from core.models import UserRole
from access.models import Publication
from .models import ReportGeneration

User = get_user_model()


class StatisticsDashboardTests(TestCase):
    """Test statistics dashboard functionality."""

    def setUp(self):
        self.client = Client()

        # Create coordinator user
        self.coordinator = User.objects.create_user(
            username='coordinator',
            email='coord@test.com',
            password='testpass123'
        )
        UserRole.objects.create(user=self.coordinator, role='coordinator')

        # Create regular user
        self.user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='testpass123'
        )

        # Create test call
        self.call = Call.objects.create(
            code='TEST-2025-01',
            title='Test Call',
            status='open',
            submission_start=timezone.now() - timedelta(days=30),
            submission_end=timezone.now() + timedelta(days=30),
            evaluation_deadline=timezone.now() + timedelta(days=60),
            execution_start=timezone.now() + timedelta(days=70),
            execution_end=timezone.now() + timedelta(days=100),
        )

        # Create test application
        self.application = Application.objects.create(
            applicant=self.user,
            call=self.call,
            code='TEST-APP-001',
            brief_description='Test application',
            status='submitted'
        )

    def test_statistics_dashboard_loads_for_coordinator(self):
        """Test that statistics dashboard loads for coordinators."""
        self.client.force_login(self.coordinator)
        response = self.client.get('/reports/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Statistics & Reports')
        self.assertContains(response, 'Total Calls')
        self.assertContains(response, 'Total Applications')

    def test_non_coordinator_denied_access(self):
        """Test that non-coordinators cannot access statistics."""
        self.client.force_login(self.user)
        response = self.client.get('/reports/')

        # Should be redirected or denied (not 200)
        self.assertNotEqual(response.status_code, 200)

    def test_dashboard_displays_correct_counts(self):
        """Test that dashboard shows correct statistics."""
        self.client.force_login(self.coordinator)
        response = self.client.get('/reports/')

        self.assertEqual(response.status_code, 200)
        # Should show at least 1 call and 1 application
        self.assertContains(response, str(Call.objects.count()))
        self.assertContains(response, str(Application.objects.count()))

    def test_publication_statistics_display(self):
        """Test that publication statistics are shown."""
        # Create a publication
        Publication.objects.create(
            application=self.application,
            title='Test Publication',
            authors='Test Author',
            journal='Test Journal',
            publication_date=timezone.now().date(),
            reported_by=self.user,
            redib_acknowledged=True
        )

        self.client.force_login(self.coordinator)
        response = self.client.get('/reports/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Publication Statistics')
        self.assertContains(response, 'Test Publication')


class ExcelExportTests(TestCase):
    """Test Excel report export functionality."""

    def setUp(self):
        self.client = Client()

        # Create coordinator user
        self.coordinator = User.objects.create_user(
            username='coordinator2',
            email='coord2@test.com',
            password='testpass123'
        )
        UserRole.objects.create(user=self.coordinator, role='coordinator')

        # Create test call
        self.call = Call.objects.create(
            code='TEST-2025-02',
            title='Test Call 2',
            status='open',
            submission_start=timezone.now() - timedelta(days=30),
            submission_end=timezone.now() + timedelta(days=30),
            evaluation_deadline=timezone.now() + timedelta(days=60),
            execution_start=timezone.now() + timedelta(days=70),
            execution_end=timezone.now() + timedelta(days=100),
        )

    def test_export_call_report_generates_excel(self):
        """Test that Excel export generates valid file."""
        self.client.force_login(self.coordinator)
        response = self.client.get(f'/reports/call/{self.call.id}/export/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        self.assertIn('call_report_', response['Content-Disposition'])
        self.assertIn(self.call.code, response['Content-Disposition'])

    def test_export_tracks_report_generation(self):
        """Test that report generation is tracked in database."""
        self.client.force_login(self.coordinator)

        # Should have no reports initially
        self.assertEqual(ReportGeneration.objects.count(), 0)

        # Generate report
        response = self.client.get(f'/reports/call/{self.call.id}/export/')
        self.assertEqual(response.status_code, 200)

        # Should now have 1 report tracked
        self.assertEqual(ReportGeneration.objects.count(), 1)

        report = ReportGeneration.objects.first()
        self.assertEqual(report.report_type, 'call_summary')
        self.assertEqual(report.call, self.call)
        self.assertEqual(report.generated_by, self.coordinator)
        self.assertEqual(report.file_format, 'xlsx')

    def test_non_coordinator_cannot_export(self):
        """Test that non-coordinators cannot export reports."""
        user = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='testpass123'
        )
        self.client.force_login(user)

        response = self.client.get(f'/reports/call/{self.call.id}/export/')
        self.assertNotEqual(response.status_code, 200)


class ReportHistoryTests(TestCase):
    """Test report history view."""

    def setUp(self):
        self.client = Client()

        # Create coordinator user
        self.coordinator = User.objects.create_user(
            username='coordinator3',
            email='coord3@test.com',
            password='testpass123'
        )
        UserRole.objects.create(user=self.coordinator, role='coordinator')

        # Create test call
        self.call = Call.objects.create(
            code='TEST-2025-03',
            title='Test Call 3',
            status='closed',
            submission_start=timezone.now() - timedelta(days=60),
            submission_end=timezone.now() - timedelta(days=30),
            evaluation_deadline=timezone.now() - timedelta(days=10),
            execution_start=timezone.now(),
            execution_end=timezone.now() + timedelta(days=30),
        )

    def test_report_history_loads(self):
        """Test that report history page loads."""
        self.client.force_login(self.coordinator)
        response = self.client.get('/reports/history/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Report History')

    def test_report_history_shows_generated_reports(self):
        """Test that generated reports appear in history."""
        # Create a report record
        ReportGeneration.objects.create(
            report_type='call_summary',
            title=f'Call Report: {self.call.code}',
            call=self.call,
            file_format='xlsx',
            generated_by=self.coordinator
        )

        self.client.force_login(self.coordinator)
        response = self.client.get('/reports/history/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.call.code)
        self.assertContains(response, 'Call Report')

    def test_empty_history_shows_message(self):
        """Test that empty history shows appropriate message."""
        self.client.force_login(self.coordinator)
        response = self.client.get('/reports/history/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No Reports Yet')


class PhaseIntegrationTest(TestCase):
    """End-to-end test of Phase 10 workflow."""

    def test_full_reporting_workflow(self):
        """Test complete flow: dashboard → export → history."""
        # Create coordinator
        coordinator = User.objects.create_user(
            username='coordinator4',
            email='coord4@test.com',
            password='testpass123'
        )
        UserRole.objects.create(user=coordinator, role='coordinator')

        # Create call with application
        call = Call.objects.create(
            code='TEST-2025-04',
            title='Integration Test Call',
            status='open',
            submission_start=timezone.now() - timedelta(days=30),
            submission_end=timezone.now() + timedelta(days=30),
            evaluation_deadline=timezone.now() + timedelta(days=60),
            execution_start=timezone.now() + timedelta(days=70),
            execution_end=timezone.now() + timedelta(days=100),
        )

        user = User.objects.create_user(
            username='applicant',
            email='applicant@test.com',
            password='testpass123'
        )

        Application.objects.create(
            applicant=user,
            call=call,
            code='INT-APP-001',
            brief_description='Integration test app',
            status='accepted',
            resolution='accepted'
        )

        client = Client()
        client.force_login(coordinator)

        # 1. View dashboard
        response = client.get('/reports/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, call.code)

        # 2. Export report
        response = client.get(f'/reports/call/{call.id}/export/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

        # 3. Check report was tracked
        self.assertEqual(ReportGeneration.objects.count(), 1)

        # 4. View history
        response = client.get('/reports/history/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, call.code)

        # Success!
