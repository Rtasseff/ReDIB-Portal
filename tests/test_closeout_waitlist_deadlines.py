"""
Tests for closeout #17 (process_acceptance_deadlines covers waitlisted
'pending' applications too) and #30(c) (freed-capacity notice fires only
for a previously-'accepted' application, never for an expiring 'pending'
waitlist offer, which held no allocation).
"""
from decimal import Decimal

import io
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from applications.models import Application, RequestedAccess
from applications.tasks import process_acceptance_deadlines
from calls.models import Call
from communications.models import EmailLog
from core.models import Equipment, Node, Organization, UserRole
from core.test_utils import create_complete_user


class WaitlistDeadlineTest(TestCase):
    def setUp(self):
        call_command('seed_email_templates', stdout=io.StringIO())
        self.org = Organization.objects.create(
            name='Closeout Deadline Org', iso2='ES', country='Spain', organization_type='other'
        )
        self.node = Node.objects.create(
            code='CLOSEOUT-DL-NODE', organization=self.org, location='Test City'
        )
        self.coordinator = create_complete_user(email='nodecoord@closeout.test', organization=self.org)
        UserRole.objects.create(user=self.coordinator, role='node_coordinator', node=self.node, is_active=True)

        self.equipment = Equipment.objects.create(
            node=self.node, name='Test Scanner', category='mri'
        )

        self.applicant = create_complete_user(email='waitlisted@closeout.test', organization=self.org)

        self.call = Call.objects.create(
            code='CLOSEOUT-DL-2026',
            title='Closeout Deadline Call',
            submission_start=timezone.now() - timedelta(days=60),
            submission_end=timezone.now() - timedelta(days=30),
            evaluation_deadline=timezone.now() - timedelta(days=10),
            execution_start=timezone.now() + timedelta(days=5),
            execution_end=timezone.now() + timedelta(days=100),
        )

    def _make_application(self, status, resolution, acceptance_deadline, hours_approved=None):
        application = Application.objects.create(
            applicant=self.applicant,
            call=self.call,
            code=f'CLOSEOUT-DL-{status}-{acceptance_deadline.timestamp():.0f}',
            brief_description='Test application',
            status=status,
            resolution=resolution,
            resolution_date=timezone.now() - timedelta(days=15),
            acceptance_deadline=acceptance_deadline,
            accepted_by_applicant=None,
        )
        RequestedAccess.objects.create(
            application=application,
            equipment=self.equipment,
            hours_requested=Decimal('10.0'),
            hours_approved=hours_approved,
        )
        return application

    def test_waitlisted_application_gets_day7_reminder(self):
        app = self._make_application('pending', 'pending', timezone.now() + timedelta(days=2))

        process_acceptance_deadlines()

        self.assertTrue(
            EmailLog.objects.filter(
                template__template_type='acceptance_reminder',
                related_application_id=app.id,
            ).exists()
        )

    def test_waitlisted_application_auto_expires_on_day10(self):
        app = self._make_application('pending', 'pending', timezone.now() - timedelta(days=1))

        process_acceptance_deadlines()
        app.refresh_from_db()

        self.assertEqual(app.status, 'expired')
        self.assertFalse(app.accepted_by_applicant)

    def test_expiring_waitlist_application_frees_no_capacity(self):
        """A 'pending' application never held an allocation, so its expiry
        must not fire the #30c freed-capacity notice."""
        self._make_application('pending', 'pending', timezone.now() - timedelta(days=1))

        process_acceptance_deadlines()

        self.assertEqual(
            EmailLog.objects.filter(template__template_type='freed_capacity_notice').count(), 0
        )

    def test_expiring_accepted_application_frees_capacity(self):
        """A previously-'accepted' application held a real allocation, so
        its expiry must notify the node coordinator(s)."""
        app = self._make_application(
            'accepted', 'accepted', timezone.now() - timedelta(days=1), hours_approved=Decimal('8.0')
        )

        process_acceptance_deadlines()
        app.refresh_from_db()

        self.assertEqual(app.status, 'expired')
        notice = EmailLog.objects.filter(
            template__template_type='freed_capacity_notice',
            related_application_id=app.id,
        ).first()
        self.assertIsNotNone(notice)
        self.assertEqual(notice.recipient_email, self.coordinator.email)

    def test_freed_capacity_notice_does_not_double_send(self):
        """_notify_freed_capacity dedupes per (recipient, application, day)
        like every other notification helper in this module, so a retried
        or overlapping call does not double-send."""
        from applications.tasks import _notify_freed_capacity

        app = self._make_application(
            'accepted', 'accepted', timezone.now() - timedelta(days=1), hours_approved=Decimal('8.0')
        )
        app.status = 'expired'
        app.save()

        _notify_freed_capacity(app, reason='expired')
        _notify_freed_capacity(app, reason='expired')

        self.assertEqual(
            EmailLog.objects.filter(
                template__template_type='freed_capacity_notice', related_application_id=app.id
            ).count(),
            1,
        )

    def test_both_statuses_included_in_single_run(self):
        accepted = self._make_application(
            'accepted', 'accepted', timezone.now() - timedelta(days=1), hours_approved=Decimal('5.0')
        )
        pending = self._make_application('pending', 'pending', timezone.now() - timedelta(days=1))

        process_acceptance_deadlines()
        accepted.refresh_from_db()
        pending.refresh_from_db()

        self.assertEqual(accepted.status, 'expired')
        self.assertEqual(pending.status, 'expired')
