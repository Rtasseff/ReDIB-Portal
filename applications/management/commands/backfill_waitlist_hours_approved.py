"""
Management command to backfill `RequestedAccess.hours_approved` for
applications caught by the waitlist-promotion bug fixed alongside this
command (see docs/handoffs/baseline.md and backlog #31): promoting a
waitlisted application never set approved hours, so the equipment lines
on some already-promoted applications are stuck at 0 (or null) hours
even though the applicant is already active.

This intentionally does NOT derive a figure from `hours_requested` —
approved hours are a human decision made by the node coordinator, not
something this command should guess. It only applies figures supplied in
a TSV, so the person running it is asserting "the node coordinator
confirmed these numbers", not "assume they wanted the full request".

Usage:
    python manage.py backfill_waitlist_hours_approved --tsv path/to/file.tsv [--dry-run]

TSV columns (tab-separated, header row required):
    application_code   Application.code (natural key)
    equipment_name      Equipment.name, must be one of the application's
                         requested_access rows
    hours_approved       Decimal hours the node coordinator confirmed

Idempotent: rows whose RequestedAccess.hours_approved already matches the
TSV value are reported as unchanged and left alone; running the command
twice with the same TSV produces the same end state.

Safety: a row is only ever updated if its current hours_approved is null
or 0 — never overwrites an already-confirmed nonzero figure. Use the
Access Tracking / application detail screens for any correction beyond
that, not this command.
"""
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from applications.models import Application, RequestedAccess


class Command(BaseCommand):
    help = (
        'Backfill RequestedAccess.hours_approved from a TSV of node-coordinator-'
        'confirmed figures, for applications left at 0 by the waitlist-promotion bug.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--tsv',
            type=str,
            required=True,
            help='Path to the backfill TSV (application_code, equipment_name, hours_approved)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report what would change without writing anything',
        )

    def _load_rows(self, tsv_path):
        project_root = Path(settings.BASE_DIR)
        tsv_file = project_root / tsv_path
        if not tsv_file.exists():
            raise CommandError(f'TSV file not found: {tsv_file}')

        rows = []
        with open(tsv_file, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row_num, row in enumerate(reader, start=2):
                app_code = (row.get('application_code') or '').strip()
                equipment_name = (row.get('equipment_name') or '').strip()
                hours_raw = (row.get('hours_approved') or '').strip()
                if not app_code or not equipment_name or not hours_raw:
                    raise CommandError(
                        f'Row {row_num}: application_code, equipment_name and '
                        'hours_approved are all required'
                    )
                try:
                    hours = Decimal(hours_raw)
                except InvalidOperation:
                    raise CommandError(
                        f'Row {row_num} ("{app_code}"): "{hours_raw}" is not a valid decimal'
                    )
                if hours < 0:
                    raise CommandError(
                        f'Row {row_num} ("{app_code}"): hours_approved must not be negative'
                    )
                rows.append({
                    'row_num': row_num,
                    'application_code': app_code,
                    'equipment_name': equipment_name,
                    'hours_approved': hours,
                })
        return rows

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        rows = self._load_rows(options['tsv'])

        updated, unchanged, skipped = 0, 0, 0

        for row in rows:
            try:
                application = Application.objects.get(code=row['application_code'])
            except Application.DoesNotExist:
                raise CommandError(
                    f"Row {row['row_num']}: no Application with code "
                    f"\"{row['application_code']}\""
                )

            matches = list(
                application.requested_access.filter(equipment__name=row['equipment_name'])
            )
            if not matches:
                raise CommandError(
                    f"Row {row['row_num']} (\"{row['application_code']}\"): no requested "
                    f"equipment named \"{row['equipment_name']}\" on this application"
                )
            if len(matches) > 1:
                raise CommandError(
                    f"Row {row['row_num']} (\"{row['application_code']}\"): "
                    f"\"{row['equipment_name']}\" matches {len(matches)} requested-access "
                    "rows on this application — ambiguous, aborting"
                )
            req_access = matches[0]

            if req_access.hours_approved == row['hours_approved']:
                unchanged += 1
                self.stdout.write(
                    f"  = {row['application_code']} / {row['equipment_name']}: "
                    f"already {row['hours_approved']}"
                )
                continue

            if req_access.hours_approved not in (None, 0):
                skipped += 1
                self.stdout.write(self.style.WARNING(
                    f"  ⊘ {row['application_code']} / {row['equipment_name']}: "
                    f"already has a nonzero hours_approved "
                    f"({req_access.hours_approved}) — not overwriting with "
                    f"{row['hours_approved']}. Correct this by hand if it's wrong."
                ))
                continue

            self.stdout.write(self.style.SUCCESS(
                f"  ✓ {row['application_code']} / {row['equipment_name']}: "
                f"{req_access.hours_approved} -> {row['hours_approved']}"
            ))
            if not dry_run:
                req_access.hours_approved = row['hours_approved']
                req_access.save(update_fields=['hours_approved'])
            updated += 1

        self.stdout.write('\n' + '=' * 60)
        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run — no changes written.'))
        self.stdout.write(f'  Would update / updated: {updated}')
        self.stdout.write(f'  Already correct: {unchanged}')
        self.stdout.write(f'  Skipped (already nonzero, needs manual review): {skipped}')
        self.stdout.write('=' * 60 + '\n')
