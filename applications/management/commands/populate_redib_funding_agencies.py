"""
Management command to populate funding agencies from TSV file.

Loads applications.FundingAgency records from a TSV file. By default, loads
from data/funding_agencies.tsv. Uses `name` as the natural key for upserts
(the FundingAgency.name field is unique=True at the model level).

TSV columns: name
- `name` is required and must be unique

Provides seed data for the funding agency dropdown in application Step 2.
Without seed data, applicants must use the "Other" flow to add agencies one
at a time during application submission.
"""
import csv
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from applications.models import FundingAgency


class Command(BaseCommand):
    help = 'Populate funding agencies from TSV file (default: data/funding_agencies.tsv)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tsv',
            type=str,
            default='data/funding_agencies.tsv',
            help='Path to funding agencies TSV file (default: data/funding_agencies.tsv)'
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            help='List funding agencies in DB but not in TSV (FundingAgency has no is_active field, '
                 'so orphans are reported but not modified)'
        )

    def load_funding_agencies_from_csv(self, csv_path):
        """Load funding agency data from TSV file."""
        project_root = Path(settings.BASE_DIR)
        csv_file = project_root / csv_path

        if not csv_file.exists():
            raise CommandError(f'TSV file not found: {csv_file}')

        agencies = []
        seen_names = set()

        try:
            with open(csv_file, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for row_num, row in enumerate(reader, start=2):
                    name = (row.get('name') or '').strip()
                    if not name:
                        self.stdout.write(self.style.WARNING(
                            f'Row {row_num}: Skipping - missing required field (name)'
                        ))
                        continue

                    if name in seen_names:
                        self.stdout.write(self.style.WARNING(
                            f'Row {row_num}: Skipping - duplicate name "{name}" within TSV'
                        ))
                        continue
                    seen_names.add(name)
                    agencies.append({'name': name})

        except csv.Error as e:
            raise CommandError(f'Error reading TSV file: {e}')

        return agencies

    def handle(self, *args, **options):
        csv_path = options['tsv']
        sync_mode = options['sync']

        self.stdout.write(f'Loading funding agency data from: {csv_path}')

        agencies = self.load_funding_agencies_from_csv(csv_path)

        if not agencies and not sync_mode:
            self.stdout.write(self.style.WARNING(
                'No funding agencies found in TSV (only headers, or empty file). Nothing to do.'
            ))
            return

        if not agencies:
            self.stdout.write(self.style.WARNING(
                'No funding agencies in TSV; --sync mode will list all existing agencies as orphans.'
            ))

        created_count = 0
        existed_count = 0
        processed_ids = set()

        for data in agencies:
            agency, created = FundingAgency.objects.get_or_create(name=data['name'])
            processed_ids.add(agency.id)

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created: {data["name"]}'))
            else:
                existed_count += 1
                self.stdout.write(self.style.WARNING(f'  ↻ Already exists: {data["name"]}'))

        # Sync mode: list orphans (cannot deactivate - no is_active field)
        if sync_mode:
            self.stdout.write('\n' + '-' * 60)
            self.stdout.write('Checking for orphan funding agencies (in DB but not in TSV)...')
            orphans = FundingAgency.objects.exclude(id__in=processed_ids)
            if orphans.exists():
                self.stdout.write(self.style.WARNING(
                    f'  Found {orphans.count()} orphan funding agency(ies):'
                ))
                for agency in orphans:
                    app_count = agency.applications.count()
                    self.stdout.write(
                        f'    - {agency.name} (id={agency.id}, applications referencing: {app_count})'
                    )
                self.stdout.write(self.style.WARNING(
                    '  Note: FundingAgency has no is_active field. Orphans were NOT modified. '
                    'Review and remove via Django admin if appropriate (mind FK references).'
                ))
            else:
                self.stdout.write(self.style.SUCCESS('  ✓ No orphan funding agencies found'))

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('Funding agency population complete!'))
        self.stdout.write(f'  Funding agencies created: {created_count}')
        self.stdout.write(f'  Funding agencies already existed: {existed_count}')
        self.stdout.write(f'  Total processed: {created_count + existed_count}')
        self.stdout.write('=' * 60 + '\n')
