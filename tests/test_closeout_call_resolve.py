"""
Tests for closeout #36: "Mark call resolved" coordinator action.

Covers:
- Only a 'closed' call can be marked resolved.
- Refused while any application is still 'evaluated'.
- Success sets status='resolved' + is_resolution_locked=True with no
  email side-effects.
"""
from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta

from applications.models import Application
from calls.models import Call
from communications.models import EmailLog
from core.models import Organization, UserRole
from core.test_utils import create_complete_user


class CallResolveTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name='Closeout Resolve Org', iso2='ES', country='Spain', organization_type='other'
        )
        self.coordinator = create_complete_user(email='redibcoord@closeout.test', organization=self.org)
        UserRole.objects.create(user=self.coordinator, role='coordinator', is_active=True)
        self.applicant = create_complete_user(email='resolveapplicant@closeout.test', organization=self.org)

        self.call = Call.objects.create(
            code='CLOSEOUT-RESOLVE-2026',
            title='Closeout Resolve Call',
            status='closed',
            submission_start=timezone.now() - timedelta(days=60),
            submission_end=timezone.now() - timedelta(days=30),
            evaluation_deadline=timezone.now() - timedelta(days=10),
            execution_start=timezone.now() - timedelta(days=5),
            execution_end=timezone.now() + timedelta(days=30),
        )

        self.client = Client()
        self.client.force_login(self.coordinator)

    def test_get_shows_confirmation_page(self):
        response = self.client.get(f'/calls/{self.call.pk}/resolve/')
        self.assertEqual(response.status_code, 200)
        self.call.refresh_from_db()
        self.assertEqual(self.call.status, 'closed')

    def test_call_detail_renders_resolve_button_when_closed(self):
        response = self.client.get(f'/calls/{self.call.pk}/detail/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mark Call Resolved')

    def test_post_marks_call_resolved_with_no_emails(self):
        response = self.client.post(f'/calls/{self.call.pk}/resolve/')
        self.assertEqual(response.status_code, 302)

        self.call.refresh_from_db()
        self.assertEqual(self.call.status, 'resolved')
        self.assertTrue(self.call.is_resolution_locked)
        self.assertEqual(EmailLog.objects.count(), 0)

    def test_refuses_when_application_still_evaluated(self):
        Application.objects.create(
            applicant=self.applicant,
            call=self.call,
            code='CLOSEOUT-RESOLVE-2026-001',
            brief_description='Still evaluated',
            status='evaluated',
        )

        response = self.client.post(f'/calls/{self.call.pk}/resolve/')
        self.assertEqual(response.status_code, 302)

        self.call.refresh_from_db()
        self.assertEqual(self.call.status, 'closed')
        self.assertFalse(self.call.is_resolution_locked)

    def test_refuses_when_call_not_closed(self):
        self.call.status = 'open'
        self.call.save()

        response = self.client.post(f'/calls/{self.call.pk}/resolve/')
        self.assertEqual(response.status_code, 302)

        self.call.refresh_from_db()
        self.assertEqual(self.call.status, 'open')
        self.assertFalse(self.call.is_resolution_locked)

    def test_refuses_second_resolve(self):
        self.client.post(f'/calls/{self.call.pk}/resolve/')
        response = self.client.post(f'/calls/{self.call.pk}/resolve/')
        self.assertEqual(response.status_code, 302)

        self.call.refresh_from_db()
        self.assertEqual(self.call.status, 'resolved')
