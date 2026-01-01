"""
Management command to populate ReDIB equipment across all nodes.

This creates equipment items from a CSV file. By default, loads from
data/equipment.csv which contains the 17 official equipment items specified
in REDIB-APP-application-form-coa-redib.docx form.
"""
import csv
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from core.models import Node, Equipment


class Command(BaseCommand):
    help = 'Populate equipment for all ReDIB nodes from CSV file (default: data/equipment.csv)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            default='data/equipment.csv',
            help='Path to equipment CSV file (default: data/equipment.csv)'
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Mark equipment not in CSV as inactive (is_active=False)'
        )

    def load_equipment_from_csv(self, csv_path):
        """Load equipment data from CSV file."""
        # Get project root directory
        project_root = Path(settings.BASE_DIR)
        csv_file = project_root / csv_path

        if not csv_file.exists():
            raise CommandError(f'CSV file not found: {csv_file}')

        equipment_data = []
        valid_categories = dict(Equipment.EQUIPMENT_CATEGORIES).keys()

        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
                    # Validate required fields
                    if not row.get('node_code') or not row.get('name') or not row.get('category'):
                        self.stdout.write(
                            self.style.WARNING(
                                f'Row {row_num}: Skipping - missing required fields (node_code, name, or category)'
                            )
                        )
                        continue

                    # Validate category
                    category = row['category'].strip()
                    if category not in valid_categories:
                        raise CommandError(
                            f'Row {row_num}: Invalid category "{category}". '
                            f'Must be one of: {", ".join(valid_categories)}'
                        )

                    # Convert boolean fields
                    is_essential = row.get('is_essential', 'TRUE').strip().upper() in ['TRUE', '1', 'YES']
                    is_active = row.get('is_active', 'TRUE').strip().upper() in ['TRUE', '1', 'YES']

                    equipment_data.append({
                        'node_code': row['node_code'].strip(),
                        'name': row['name'].strip(),
                        'category': category,
                        'description': row.get('description', '').strip(),
                        'technical_specs': row.get('technical_specs', '').strip(),
                        'is_essential': is_essential,
                        'is_active': is_active,
                    })

        except csv.Error as e:
            raise CommandError(f'Error reading CSV file: {e}')
        except Exception as e:
            raise CommandError(f'Unexpected error reading CSV: {e}')

        return equipment_data

    def handle(self, *args, **options):
        """Create equipment for all nodes from CSV file"""

        csv_path = options['csv']
        sync_mode = options['sync']

        self.stdout.write(f'Loading equipment data from: {csv_path}')
        if sync_mode:
            self.stdout.write(self.style.WARNING('Sync mode enabled: Will mark orphaned equipment as inactive'))

        # Load equipment data from CSV
        equipment_data = self.load_equipment_from_csv(csv_path)

        created_count = 0
        updated_count = 0
        node_count = 0
        processed_equipment_ids = set()  # Track equipment IDs processed from CSV

        for equip_data in equipment_data:
            node_code = equip_data['node_code']
            equipment_name = equip_data['name']
            category = equip_data['category']

            # Get or create node
            node, node_created = Node.objects.get_or_create(
                code=node_code,
                defaults={
                    'name': node_code.replace('-', ' '),
                    'location': 'TBD',  # Should be set via populate_redib_nodes command
                }
            )

            if node_created:
                node_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created node: {node_code}')
                )

            # Get or create equipment
            equipment, equipment_created = Equipment.objects.get_or_create(
                node=node,
                name=equipment_name,
                defaults={
                    'category': category,
                    'description': equip_data.get('description', ''),
                    'technical_specs': equip_data.get('technical_specs', ''),
                    'is_essential': equip_data.get('is_essential', True),
                    'is_active': equip_data.get('is_active', True),
                }
            )

            if equipment_created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Created: {node_code} - {equipment_name} ({category})'
                    )
                )
            else:
                # Update existing equipment to ensure correct values from CSV
                equipment.category = category
                equipment.description = equip_data.get('description', '')
                equipment.technical_specs = equip_data.get('technical_specs', '')
                equipment.is_essential = equip_data.get('is_essential', True)
                equipment.is_active = equip_data.get('is_active', True)
                equipment.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  ↻ Updated: {node_code} - {equipment_name} ({category})'
                    )
                )

            # Track this equipment as processed
            processed_equipment_ids.add(equipment.id)

        # Handle sync mode: Mark orphaned equipment as inactive
        deactivated_count = 0
        if sync_mode:
            self.stdout.write('\n' + '-' * 60)
            self.stdout.write('Checking for orphaned equipment (in DB but not in CSV)...')

            # Find all equipment not in the processed set
            orphaned_equipment = Equipment.objects.exclude(id__in=processed_equipment_ids).filter(is_active=True)

            for equip in orphaned_equipment:
                equip.is_active = False
                equip.save()
                deactivated_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⊗ Deactivated: {equip.node.code} - {equip.name} (not in CSV)'
                    )
                )

            if deactivated_count == 0:
                self.stdout.write(self.style.SUCCESS('  ✓ No orphaned equipment found'))

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(
            self.style.SUCCESS(
                f'Equipment population complete!'
            )
        )
        if node_count > 0:
            self.stdout.write(f'  Nodes created: {node_count}')
        self.stdout.write(f'  Equipment created: {created_count}')
        self.stdout.write(f'  Equipment updated: {updated_count}')
        if sync_mode and deactivated_count > 0:
            self.stdout.write(f'  Equipment deactivated: {deactivated_count}')
        self.stdout.write(f'  Total equipment: {created_count + updated_count} items')
        self.stdout.write('\n' + self.style.WARNING('Note: Run "python manage.py populate_redib_nodes" to set proper node details'))
        self.stdout.write('=' * 60 + '\n')
