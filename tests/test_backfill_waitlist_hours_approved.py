"""
Tests for the backfill_waitlist_hours_approved management command (see
docs/handoffs/baseline.md and backlog #31): a small, idempotent, human-
supplied-figures-only tool to correct RequestedAccess.hours_approved on
applications the waitlist-promotion bug left at 0/null.
"""
import tempfile
from decimal import Decimal
from io import StringIO

from django.core.management import call_command, CommandError
from django.test import TestCase
from django.utils import timezone

from applications.models import Application, RequestedAccess
from calls.models import Call
from core.models import Equipment, Node, Organization
from core.test_utils import create_complete_user


def _write_tsv(rows):
    """rows: list of (application_code, equipment_name, hours_approved) tuples."""
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.tsv', delete=False, encoding='utf-8')
    f.write('application_code\tequipment_name\thours_approved\n')
    for row in rows:
        f.write('\t'.join(str(v) for v in row) + '\n')
    f.close()
    return f.name


class BackfillWaitlistHoursApprovedTest(TestCase):
    def setUp(self):
        self.applicant = create_complete_user(email='a@test.com')
        org, _ = Organization.objects.get_or_create(
            name='Host Org', defaults={'organization_type': 'pro', 'iso2': 'ES', 'country': 'Spain'},
        )
        self.node = Node.objects.create(code='N1', organization=org, location='Here')
        self.equipment = Equipment.objects.create(node=self.node, name='Scanner', category='mri')
        self.call = Call.objects.create(
            code='CALL-B', title='Backfill Call',
            submission_start=timezone.now(), submission_end=timezone.now(),
            evaluation_deadline=timezone.now(), execution_start=timezone.now(),
            execution_end=timezone.now(),
        )
        self.application = Application.objects.create(
            applicant=self.applicant, call=self.call, code='APP-B1',
            brief_description='backfill test', status='accepted', resolution='accepted',
        )
        self.req = RequestedAccess.objects.create(
            application=self.application, equipment=self.equipment,
            hours_requested=Decimal('100'), hours_approved=0,
        )

    def test_backfills_zero_hours(self):
        tsv = _write_tsv([('APP-B1', 'Scanner', '80.5')])
        call_command('backfill_waitlist_hours_approved', tsv=tsv, stdout=StringIO())
        self.req.refresh_from_db()
        self.assertEqual(self.req.hours_approved, Decimal('80.5'))

    def test_dry_run_does_not_write(self):
        tsv = _write_tsv([('APP-B1', 'Scanner', '80.5')])
        call_command('backfill_waitlist_hours_approved', tsv=tsv, dry_run=True, stdout=StringIO())
        self.req.refresh_from_db()
        self.assertEqual(self.req.hours_approved, Decimal('0'))

    def test_idempotent_second_run_is_noop(self):
        tsv = _write_tsv([('APP-B1', 'Scanner', '80.5')])
        call_command('backfill_waitlist_hours_approved', tsv=tsv, stdout=StringIO())
        call_command('backfill_waitlist_hours_approved', tsv=tsv, stdout=StringIO())
        self.req.refresh_from_db()
        self.assertEqual(self.req.hours_approved, Decimal('80.5'))

    def test_does_not_overwrite_existing_nonzero_hours(self):
        self.req.hours_approved = Decimal('50')
        self.req.save()
        tsv = _write_tsv([('APP-B1', 'Scanner', '80.5')])
        call_command('backfill_waitlist_hours_approved', tsv=tsv, stdout=StringIO())
        self.req.refresh_from_db()
        self.assertEqual(self.req.hours_approved, Decimal('50'))

    def test_unknown_application_code_aborts(self):
        tsv = _write_tsv([('NOT-A-REAL-CODE', 'Scanner', '80.5')])
        with self.assertRaises(CommandError):
            call_command('backfill_waitlist_hours_approved', tsv=tsv, stdout=StringIO())
        self.req.refresh_from_db()
        self.assertEqual(self.req.hours_approved, Decimal('0'))

    def test_unknown_equipment_name_aborts(self):
        tsv = _write_tsv([('APP-B1', 'Not A Real Instrument', '80.5')])
        with self.assertRaises(CommandError):
            call_command('backfill_waitlist_hours_approved', tsv=tsv, stdout=StringIO())

    def test_missing_tsv_file_aborts(self):
        with self.assertRaises(CommandError):
            call_command('backfill_waitlist_hours_approved', tsv='/no/such/file.tsv', stdout=StringIO())
