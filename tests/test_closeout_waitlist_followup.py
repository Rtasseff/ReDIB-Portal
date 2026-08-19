"""
Tests for closeout #30: waitlist follow-up.

(a) send_waitlist_digest — per-node-coordinator digest of accepted-waitlist
    applications, on a 30/30-day cadence, deduped per (recipient, day).
(b) close_out_waitlisted_application — "Not Reached This Call" terminal
    close-out action, with a required reason and a single applicant email.
(c) _notify_freed_capacity fires when an *accepted* (not waitlist)
    application is declined by the applicant.
"""
from decimal import Decimal

import io
from django.core.management import call_command
from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta

from applications.models import Application, RequestedAccess
from applications.tasks import send_waitlist_digest
from calls.models import Call
from communications.models import EmailLog
from core.models import Equipment, Node, Organization, UserRole
from core.test_utils import create_complete_user


class WaitlistFollowUpTestBase(TestCase):
    def setUp(self):
        call_command('seed_email_templates', stdout=io.StringIO())
        self.org = Organization.objects.create(
            name='Closeout Followup Org', iso2='ES', country='Spain', organization_type='other'
        )
        self.node = Node.objects.create(
            code='CLOSEOUT-FU-NODE', organization=self.org, location='Test City'
        )
        self.coordinator = create_complete_user(email='fucoord@closeout.test', organization=self.org)
        UserRole.objects.create(user=self.coordinator, role='node_coordinator', node=self.node, is_active=True)

        self.equipment = Equipment.objects.create(
            node=self.node, name='Followup Scanner', category='mri'
        )

        self.applicant = create_complete_user(email='fuapplicant@closeout.test', organization=self.org)

        self.call = Call.objects.create(
            code='CLOSEOUT-FU-2026',
            title='Closeout Followup Call',
            submission_start=timezone.now() - timedelta(days=90),
            submission_end=timezone.now() - timedelta(days=60),
            evaluation_deadline=timezone.now() - timedelta(days=40),
            execution_start=timezone.now() - timedelta(days=20),
            execution_end=timezone.now() + timedelta(days=60),
        )

    def _make_pending_application(self, accepted_at, code_suffix='001'):
        application = Application.objects.create(
            applicant=self.applicant,
            call=self.call,
            code=f'CLOSEOUT-FU-2026-{code_suffix}',
            brief_description='Waitlisted application',
            status='pending',
            resolution='pending',
            resolution_date=timezone.now() - timedelta(days=45),
            accepted_by_applicant=True,
            accepted_at=accepted_at,
        )
        RequestedAccess.objects.create(
            application=application,
            equipment=self.equipment,
            hours_requested=Decimal('10.0'),
        )
        return application


class WaitlistDigestTest(WaitlistFollowUpTestBase):
    def test_digest_sent_at_thirty_day_checkpoint(self):
        self._make_pending_application(timezone.now() - timedelta(days=30))

        result = send_waitlist_digest()

        self.assertIn('1', result)
        self.assertTrue(
            EmailLog.objects.filter(
                template__template_type='waitlist_digest',
                recipient_email=self.coordinator.email,
            ).exists()
        )

    def test_no_digest_before_checkpoint(self):
        self._make_pending_application(timezone.now() - timedelta(days=15))

        send_waitlist_digest()

        self.assertEqual(EmailLog.objects.filter(template__template_type='waitlist_digest').count(), 0)

    def test_digest_does_not_double_send_same_day(self):
        self._make_pending_application(timezone.now() - timedelta(days=60))  # second 30-day checkpoint

        send_waitlist_digest()
        first_count = EmailLog.objects.filter(template__template_type='waitlist_digest').count()
        self.assertEqual(first_count, 1)

        send_waitlist_digest()
        second_count = EmailLog.objects.filter(template__template_type='waitlist_digest').count()
        self.assertEqual(second_count, 1)

    def test_no_digest_for_application_applicant_has_not_accepted(self):
        app = self._make_pending_application(timezone.now() - timedelta(days=30))
        app.accepted_by_applicant = None
        app.save(update_fields=['accepted_by_applicant'])

        send_waitlist_digest()

        self.assertEqual(EmailLog.objects.filter(template__template_type='waitlist_digest').count(), 0)

    def test_catch_up_after_missed_execution_end_day(self):
        """A checkpoint far outside the 30/30 cadence, but a few days past
        execution_end, still gets a digest — an exact 'day after' check
        alone would miss this if the beat task didn't run that exact day."""
        self.call.execution_end = timezone.now() - timedelta(days=3)
        self.call.save()
        self._make_pending_application(timezone.now() - timedelta(days=10))  # not a 30/60 checkpoint

        send_waitlist_digest()

        self.assertTrue(
            EmailLog.objects.filter(
                template__template_type='waitlist_digest', recipient_email=self.coordinator.email
            ).exists()
        )

    def test_milestone_digest_does_not_repeat_within_catch_up_window(self):
        from communications.models import EmailTemplate

        self.call.execution_end = timezone.now() - timedelta(days=3)
        self.call.save()
        self._make_pending_application(timezone.now() - timedelta(days=10))

        template = EmailTemplate.objects.get(template_type='waitlist_digest')
        EmailLog.objects.create(
            template=template, recipient_email=self.coordinator.email,
            subject='x', status='sent',
            sent_at=self.call.execution_end + timedelta(days=1),
        )

        send_waitlist_digest()

        self.assertEqual(
            EmailLog.objects.filter(
                template__template_type='waitlist_digest', recipient_email=self.coordinator.email
            ).count(),
            1,
        )


class WaitlistCloseOutTest(WaitlistFollowUpTestBase):
    def setUp(self):
        super().setUp()
        self.application = self._make_pending_application(timezone.now() - timedelta(days=30))
        self.client = Client()

    def test_get_renders_confirmation_page(self):
        self.client.force_login(self.coordinator)
        response = self.client.get(f'/applications/{self.application.pk}/waitlist-close-out/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.application.code)

    def test_access_tracking_renders_close_out_button(self):
        self.client.force_login(self.coordinator)
        response = self.client.get('/access/tracking/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Not Reached This Call')

    def test_access_tracking_hides_close_out_button_before_applicant_response(self):
        self.application.accepted_by_applicant = None
        self.application.accepted_at = None
        self.application.save()

        self.client.force_login(self.coordinator)
        response = self.client.get('/access/tracking/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Not Reached This Call')

    def test_node_coordinator_can_close_out_with_reason(self):
        self.client.force_login(self.coordinator)

        response = self.client.post(
            f'/applications/{self.application.pk}/waitlist-close-out/',
            {'reason': 'No slot opened before the call closed.'},
        )
        self.assertEqual(response.status_code, 302)

        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'not_reached')
        self.assertIn('NOT REACHED THIS CALL', self.application.resolution_comments)
        self.assertIn('No slot opened', self.application.resolution_comments)

        notices = EmailLog.objects.filter(
            template__template_type='waitlist_not_reached',
            related_application_id=self.application.id,
        )
        self.assertEqual(notices.count(), 1)
        self.assertEqual(notices.first().recipient_email, self.applicant.email)

    def test_reason_is_required(self):
        self.client.force_login(self.coordinator)

        response = self.client.post(f'/applications/{self.application.pk}/waitlist-close-out/', {'reason': ''})
        self.assertEqual(response.status_code, 302)

        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'pending')

    def test_cannot_close_out_before_applicant_has_responded(self):
        """An unanswered waitlist offer still has its own 10-day response
        window (#17) — closing it out early would preempt that."""
        self.application.accepted_by_applicant = None
        self.application.accepted_at = None
        self.application.save()

        self.client.force_login(self.coordinator)
        response = self.client.post(
            f'/applications/{self.application.pk}/waitlist-close-out/',
            {'reason': 'Jumping the gun'},
        )
        self.assertEqual(response.status_code, 302)

        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'pending')
        self.assertEqual(
            EmailLog.objects.filter(template__template_type='waitlist_not_reached').count(), 0
        )

    def test_unrelated_node_coordinator_cannot_close_out(self):
        other_org = Organization.objects.create(
            name='Other Org', iso2='ES', country='Spain', organization_type='other'
        )
        other_node = Node.objects.create(code='OTHER-NODE', organization=other_org, location='Elsewhere')
        other_coord = create_complete_user(email='othercoord@closeout.test', organization=other_org)
        UserRole.objects.create(user=other_coord, role='node_coordinator', node=other_node, is_active=True)

        self.client.force_login(other_coord)
        response = self.client.post(
            f'/applications/{self.application.pk}/waitlist-close-out/',
            {'reason': 'Not my node'},
        )
        self.assertEqual(response.status_code, 302)

        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'pending')

    def test_cannot_close_out_non_pending_application(self):
        self.application.status = 'accepted'
        self.application.save()

        self.client.force_login(self.coordinator)
        response = self.client.post(
            f'/applications/{self.application.pk}/waitlist-close-out/',
            {'reason': 'Should not apply'},
        )
        self.assertEqual(response.status_code, 302)

        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'accepted')


class FreedCapacityOnDeclineTest(WaitlistFollowUpTestBase):
    def test_declining_accepted_application_notifies_node_coordinator(self):
        application = Application.objects.create(
            applicant=self.applicant,
            call=self.call,
            code='CLOSEOUT-FU-2026-ACC',
            brief_description='Accepted application',
            status='accepted',
            resolution='accepted',
            resolution_date=timezone.now() - timedelta(days=2),
            acceptance_deadline=timezone.now() + timedelta(days=5),
        )
        RequestedAccess.objects.create(
            application=application,
            equipment=self.equipment,
            hours_requested=Decimal('10.0'),
            hours_approved=Decimal('10.0'),
        )

        client = Client()
        client.force_login(self.applicant)
        response = client.post(
            f'/applications/{application.pk}/accept/',
            {'action': 'decline', 'decline_reason': 'Change of plans'},
        )
        self.assertEqual(response.status_code, 302)

        notice = EmailLog.objects.filter(
            template__template_type='freed_capacity_notice',
            related_application_id=application.id,
        ).first()
        self.assertIsNotNone(notice)
        self.assertEqual(notice.recipient_email, self.coordinator.email)

    def test_declining_waitlist_offer_notifies_nobody(self):
        application = self._make_pending_application(timezone.now() - timedelta(days=5), code_suffix='WL')
        application.acceptance_deadline = timezone.now() + timedelta(days=5)
        # Reset acceptance so the applicant can respond through the view.
        application.accepted_by_applicant = None
        application.accepted_at = None
        application.save()

        client = Client()
        client.force_login(self.applicant)
        response = client.post(
            f'/applications/{application.pk}/accept/',
            {'action': 'decline', 'decline_reason': 'Not interested anymore'},
        )
        self.assertEqual(response.status_code, 302)

        self.assertEqual(
            EmailLog.objects.filter(template__template_type='freed_capacity_notice').count(), 0
        )
