"""
Management command to populate organizations from TSV file.

Loads core.Organization records from a TSV file. By default, loads from
data/organizations.tsv. Uses `name` as the natural key for upserts.

TSV columns: name, vat, country, organization_type, address, website
- `name` is required and must be unique
- `organization_type` must be one of: company, university, other
- `country` defaults to 'Spain' if blank

Run before populate_redib_users so users can link to fully-populated org records
instead of relying on the loader's auto-create-with-defaults fallback.
"""
import csv
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from core.models import Organization


class Command(BaseCommand):
    help = 'Populate organizations from TSV file (default: data/organizations.tsv)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tsv',
            type=str,
            default='data/organizations.tsv',
            help='Path to organizations TSV file (default: data/organizations.tsv)'
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            help='List organizations in DB but not in TSV (Organization has no is_active field, '
                 'so orphans are reported but not modified)'
        )

    def load_organizations_from_csv(self, csv_path):
        """Load organization data from TSV file."""
        project_root = Path(settings.BASE_DIR)
        csv_file = project_root / csv_path

        if not csv_file.exists():
            raise CommandError(f'TSV file not found: {csv_file}')

        valid_types = {choice[0] for choice in Organization.ORG_TYPES}
        orgs_data = []

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

                    org_type = (row.get('organization_type') or '').strip()
                    if org_type and org_type not in valid_types:
                        self.stdout.write(self.style.WARNING(
                            f'Row {row_num}: Invalid organization_type "{org_type}" for "{name}". '
                            f'Must be one of: {", ".join(sorted(valid_types))}. Defaulting to "other".'
                        ))
                        org_type = 'other'
                    elif not org_type:
                        org_type = 'other'

                    country = (row.get('country') or '').strip() or 'Spain'

                    orgs_data.append({
                        'name': name,
                        'vat': (row.get('vat') or '').strip(),
                        'country': country,
                        'organization_type': org_type,
                        'address': (row.get('address') or '').strip(),
                        'website': (row.get('website') or '').strip(),
                    })

        except csv.Error as e:
            raise CommandError(f'Error reading TSV file: {e}')

        return orgs_data

    def handle(self, *args, **options):
        csv_path = options['tsv']
        sync_mode = options['sync']

        self.stdout.write(f'Loading organization data from: {csv_path}')

        orgs_data = self.load_organizations_from_csv(csv_path)

        if not orgs_data and not sync_mode:
            self.stdout.write(self.style.WARNING(
                'No organizations found in TSV (only headers, or empty file). Nothing to do.'
            ))
            return

        if not orgs_data:
            self.stdout.write(self.style.WARNING(
                'No organizations in TSV; --sync mode will list all existing organizations as orphans.'
            ))

        created_count = 0
        updated_count = 0
        processed_org_ids = set()

        for data in orgs_data:
            name = data['name']
            org, created = Organization.objects.update_or_create(
                name=name,
                defaults={
                    'vat': data['vat'],
                    'country': data['country'],
                    'organization_type': data['organization_type'],
                    'address': data['address'],
                    'website': data['website'],
                },
            )
            processed_org_ids.add(org.id)

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ Created: {name} ({data["organization_type"]})'
                ))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(
                    f'  ↻ Updated: {name} ({data["organization_type"]})'
                ))

        # Sync mode: list orphans (cannot deactivate - no is_active field)
        if sync_mode:
            self.stdout.write('\n' + '-' * 60)
            self.stdout.write('Checking for orphan organizations (in DB but not in TSV)...')
            orphans = Organization.objects.exclude(id__in=processed_org_ids)
            if orphans.exists():
                self.stdout.write(self.style.WARNING(
                    f'  Found {orphans.count()} orphan organization(s):'
                ))
                for org in orphans:
                    user_count = org.users.count()
                    self.stdout.write(
                        f'    - {org.name} (id={org.id}, users referencing this org: {user_count})'
                    )
                self.stdout.write(self.style.WARNING(
                    '  Note: Organization has no is_active field. Orphans were NOT modified. '
                    'Review and remove via Django admin if appropriate (mind FK references).'
                ))
            else:
                self.stdout.write(self.style.SUCCESS('  ✓ No orphan organizations found'))

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('Organization population complete!'))
        self.stdout.write(f'  Organizations created: {created_count}')
        self.stdout.write(f'  Organizations updated: {updated_count}')
        self.stdout.write(f'  Total organizations: {created_count + updated_count}')
        self.stdout.write('=' * 60 + '\n')
