"""
Management command to populate ReDIB nodes from TSV file.

This creates the 4 official ReDIB ICTS nodes from a TSV file.
By default, loads from data/nodes.tsv.
"""
import csv
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from core.models import Node


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
        """Load node data from TSV file."""
        # Get project root directory
        project_root = Path(settings.BASE_DIR)
        csv_file = project_root / csv_path

        if not csv_file.exists():
            raise CommandError(f'TSV file not found: {csv_file}')

        nodes_data = []

        try:
            with open(csv_file, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
                    # The TSV column is `organization_name` (the host org's name).
                    # It maps to the existing Node.name model field. A future change
                    # may add a Node.organization FK that uses this value to look up
                    # an Organization record from the organizations table.
                    org_name = (row.get('organization_name') or '').strip()
                    if not row.get('code') or not org_name:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Row {row_num}: Skipping - missing required fields (code or organization_name)'
                            )
                        )
                        continue

                    # Convert boolean field
                    is_active = row.get('is_active', 'TRUE').strip().upper() in ['TRUE', '1', 'YES']

                    nodes_data.append({
                        'code': row['code'].strip(),
                        'organization_name': org_name,
                        'location': row.get('location', '').strip(),
                        'description': row.get('description', '').strip(),
                        'acknowledgment_text': row.get('acknowledgment_text', '').strip(),
                        'contact_email': row.get('contact_email', '').strip(),
                        'contact_phone': row.get('contact_phone', '').strip(),
                        'is_active': is_active,
                    })

        except csv.Error as e:
            raise CommandError(f'Error reading TSV file: {e}')
        except Exception as e:
            raise CommandError(f'Unexpected error reading TSV: {e}')

        return nodes_data

    def handle(self, *args, **options):
        """Create nodes from TSV file"""

        csv_path = options['tsv']
        sync_mode = options['sync']

        self.stdout.write(f'Loading node data from: {csv_path}')
        if sync_mode:
            self.stdout.write(self.style.WARNING('Sync mode enabled: Will mark orphaned nodes as inactive'))

        # Load node data from TSV
        nodes_data = self.load_nodes_from_csv(csv_path)

        created_count = 0
        updated_count = 0
        processed_node_ids = set()  # Track node IDs processed from TSV

        for node_data in nodes_data:
            code = node_data['code']

            # Get or create node. The TSV `organization_name` column maps to the
            # existing Node.name model field (which holds the host org's name).
            node, node_created = Node.objects.update_or_create(
                code=code,
                defaults={
                    'name': node_data['organization_name'],
                    'location': node_data['location'],
                    'description': node_data['description'],
                    'acknowledgment_text': node_data['acknowledgment_text'],
                    'contact_email': node_data['contact_email'],
                    'contact_phone': node_data['contact_phone'],
                    'is_active': node_data['is_active'],
                }
            )

            if node_created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Created: {code} - {node_data["organization_name"]}'
                    )
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  ↻ Updated: {code} - {node_data["organization_name"]}'
                    )
                )

            # Track this node as processed
            processed_node_ids.add(node.id)

        # Handle sync mode: Mark orphaned nodes as inactive
        deactivated_count = 0
        if sync_mode:
            self.stdout.write('\n' + '-' * 60)
            self.stdout.write('Checking for orphaned nodes (in DB but not in TSV)...')

            # Find all nodes not in the processed set
            orphaned_nodes = Node.objects.exclude(id__in=processed_node_ids).filter(is_active=True)

            for node in orphaned_nodes:
                node.is_active = False
                node.save()
                deactivated_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⊗ Deactivated: {node.code} - {node.name} (not in TSV)'
                    )
                )

            if deactivated_count == 0:
                self.stdout.write(self.style.SUCCESS('  ✓ No orphaned nodes found'))

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(
            self.style.SUCCESS(
                f'Node population complete!'
            )
        )
        self.stdout.write(f'  Nodes created: {created_count}')
        self.stdout.write(f'  Nodes updated: {updated_count}')
        if sync_mode and deactivated_count > 0:
            self.stdout.write(f'  Nodes deactivated: {deactivated_count}')
        self.stdout.write(f'  Total nodes: {created_count + updated_count}')
        self.stdout.write('=' * 60 + '\n')
