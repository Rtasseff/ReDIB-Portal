"""
Management command to populate ReDIB nodes from CSV file.

This creates the 4 official ReDIB ICTS nodes from a CSV file.
By default, loads from data/nodes.csv.
"""
import csv
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from core.models import Node


class Command(BaseCommand):
    help = 'Populate ReDIB nodes from CSV file (default: data/nodes.csv)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            default='data/nodes.csv',
            help='Path to nodes CSV file (default: data/nodes.csv)'
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Mark nodes not in CSV as inactive (is_active=False)'
        )

    def load_nodes_from_csv(self, csv_path):
        """Load node data from CSV file."""
        # Get project root directory
        project_root = Path(settings.BASE_DIR)
        csv_file = project_root / csv_path

        if not csv_file.exists():
            raise CommandError(f'CSV file not found: {csv_file}')

        nodes_data = []

        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
                    # Validate required fields
                    if not row.get('code') or not row.get('name'):
                        self.stdout.write(
                            self.style.WARNING(
                                f'Row {row_num}: Skipping - missing required fields (code or name)'
                            )
                        )
                        continue

                    # Convert boolean field
                    is_active = row.get('is_active', 'TRUE').strip().upper() in ['TRUE', '1', 'YES']

                    nodes_data.append({
                        'code': row['code'].strip(),
                        'name': row['name'].strip(),
                        'location': row.get('location', '').strip(),
                        'description': row.get('description', '').strip(),
                        'acknowledgment_text': row.get('acknowledgment_text', '').strip(),
                        'contact_email': row.get('contact_email', '').strip(),
                        'contact_phone': row.get('contact_phone', '').strip(),
                        'is_active': is_active,
                    })

        except csv.Error as e:
            raise CommandError(f'Error reading CSV file: {e}')
        except Exception as e:
            raise CommandError(f'Unexpected error reading CSV: {e}')

        return nodes_data

    def handle(self, *args, **options):
        """Create nodes from CSV file"""

        csv_path = options['csv']
        sync_mode = options['sync']

        self.stdout.write(f'Loading node data from: {csv_path}')
        if sync_mode:
            self.stdout.write(self.style.WARNING('Sync mode enabled: Will mark orphaned nodes as inactive'))

        # Load node data from CSV
        nodes_data = self.load_nodes_from_csv(csv_path)

        created_count = 0
        updated_count = 0
        processed_node_ids = set()  # Track node IDs processed from CSV

        for node_data in nodes_data:
            code = node_data['code']

            # Get or create node
            node, node_created = Node.objects.update_or_create(
                code=code,
                defaults={
                    'name': node_data['name'],
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
                        f'  ✓ Created: {code} - {node_data["name"]}'
                    )
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  ↻ Updated: {code} - {node_data["name"]}'
                    )
                )

            # Track this node as processed
            processed_node_ids.add(node.id)

        # Handle sync mode: Mark orphaned nodes as inactive
        deactivated_count = 0
        if sync_mode:
            self.stdout.write('\n' + '-' * 60)
            self.stdout.write('Checking for orphaned nodes (in DB but not in CSV)...')

            # Find all nodes not in the processed set
            orphaned_nodes = Node.objects.exclude(id__in=processed_node_ids).filter(is_active=True)

            for node in orphaned_nodes:
                node.is_active = False
                node.save()
                deactivated_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⊗ Deactivated: {node.code} - {node.name} (not in CSV)'
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
