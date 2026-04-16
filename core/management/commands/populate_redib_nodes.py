"""
Management command to populate ReDIB nodes from TSV file.

Loads the official ReDIB ICTS nodes from data/nodes.tsv. Uses `code` as the
natural key for upserts. The TSV's `organization_name` column must match the
`name` of an existing `Organization` row — populate `data/organizations.tsv`
first via `populate_redib_organizations`. Unmatched names abort the import.
"""
import csv
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from core.models import Node, Organization


class Command(BaseCommand):
    help = 'Populate ReDIB nodes from TSV file (default: data/nodes.tsv)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tsv',
            type=str,
            default='data/nodes.tsv',
            help='Path to nodes TSV file (default: data/nodes.tsv)'
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Mark nodes not in TSV as inactive (is_active=False)'
        )

    def load_nodes_from_csv(self, csv_path):
        """Load and validate node rows from a TSV file."""
        project_root = Path(settings.BASE_DIR)
        csv_file = project_root / csv_path

        if not csv_file.exists():
            raise CommandError(f'TSV file not found: {csv_file}')

        nodes_data = []

        try:
            with open(csv_file, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for row_num, row in enumerate(reader, start=2):
                    code = (row.get('code') or '').strip()
                    org_name = (row.get('organization_name') or '').strip()
                    if not code or not org_name:
                        self.stdout.write(self.style.WARNING(
                            f'Row {row_num}: Skipping - missing required field '
                            f'(code or organization_name)'
                        ))
                        continue

                    # FK lookup — Organization must already exist.
                    try:
                        organization = Organization.objects.get(name=org_name)
                    except Organization.DoesNotExist:
                        raise CommandError(
                            f'Row {row_num} ("{code}"): organization_name '
                            f'"{org_name}" does not match any Organization. '
                            f'Run `populate_redib_organizations` first, or fix the TSV.'
                        )

                    is_active_raw = (row.get('is_active') or 'TRUE').strip().upper()
                    is_active = is_active_raw in ('TRUE', '1', 'YES')

                    nodes_data.append({
                        'code': code,
                        'organization': organization,
                        'location': (row.get('location') or '').strip(),
                        'description': (row.get('description') or '').strip(),
                        'acknowledgment_text': (row.get('acknowledgment_text') or '').strip(),
                        'contact_email': (row.get('contact_email') or '').strip(),
                        'contact_phone': (row.get('contact_phone') or '').strip(),
                        'is_active': is_active,
                    })

        except csv.Error as e:
            raise CommandError(f'Error reading TSV file: {e}')

        return nodes_data

    def handle(self, *args, **options):
        csv_path = options['tsv']
        sync_mode = options['sync']

        self.stdout.write(f'Loading node data from: {csv_path}')
        if sync_mode:
            self.stdout.write(self.style.WARNING(
                'Sync mode enabled: Will mark orphaned nodes as inactive'
            ))

        nodes_data = self.load_nodes_from_csv(csv_path)

        created_count = 0
        updated_count = 0
        processed_node_ids = set()

        for node_data in nodes_data:
            code = node_data['code']
            org = node_data['organization']
            node, node_created = Node.objects.update_or_create(
                code=code,
                defaults={
                    'organization': org,
                    'location': node_data['location'],
                    'description': node_data['description'],
                    'acknowledgment_text': node_data['acknowledgment_text'],
                    'contact_email': node_data['contact_email'],
                    'contact_phone': node_data['contact_phone'],
                    'is_active': node_data['is_active'],
                }
            )
            processed_node_ids.add(node.id)

            if node_created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ Created: {code} - {org.name}'
                ))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(
                    f'  ↻ Updated: {code} - {org.name}'
                ))

        # Sync mode: mark orphans as inactive
        deactivated_count = 0
        if sync_mode:
            self.stdout.write('\n' + '-' * 60)
            self.stdout.write('Checking for orphaned nodes (in DB but not in TSV)...')
            orphans = Node.objects.exclude(id__in=processed_node_ids).filter(is_active=True)
            for node in orphans:
                node.is_active = False
                node.save()
                deactivated_count += 1
                self.stdout.write(self.style.WARNING(
                    f'  ⊗ Deactivated: {node.code} - {node.organization.name} (not in TSV)'
                ))
            if deactivated_count == 0:
                self.stdout.write(self.style.SUCCESS('  ✓ No orphaned nodes found'))

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('Node population complete!'))
        self.stdout.write(f'  Nodes created: {created_count}')
        self.stdout.write(f'  Nodes updated: {updated_count}')
        if sync_mode and deactivated_count > 0:
            self.stdout.write(f'  Nodes deactivated: {deactivated_count}')
        self.stdout.write(f'  Total nodes: {created_count + updated_count}')
        self.stdout.write('=' * 60 + '\n')
