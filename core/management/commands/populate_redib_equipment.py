"""
Management command to populate ReDIB equipment across all nodes.

Loads from data/equipment.tsv. Uses (`node`, `name`) as the natural key for
upserts. Hard-errors on:
  - missing node_code (run populate_redib_nodes first)
  - invalid category (must be in Equipment.EQUIPMENT_CATEGORIES)
  - invalid area (must be in Equipment.AREAS, blank allowed)
  - missing required field (node_code, name, category)

Boolean columns (is_essential, is_active) follow the strict rule used across
all loaders: blank → False, only TRUE/1/YES enables.
"""
import csv
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from core.models import Node, Equipment


class Command(BaseCommand):
    help = 'Populate equipment for all ReDIB nodes from TSV file (default: data/equipment.tsv)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tsv',
            type=str,
            default='data/equipment.tsv',
            help='Path to equipment TSV file (default: data/equipment.tsv)'
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Mark equipment not in TSV as inactive (is_active=False)'
        )

    def load_equipment_from_csv(self, csv_path):
        """Load equipment data from TSV file."""
        project_root = Path(settings.BASE_DIR)
        csv_file = project_root / csv_path

        if not csv_file.exists():
            raise CommandError(f'TSV file not found: {csv_file}')

        equipment_data = []
        valid_categories = {c for c, _ in Equipment.EQUIPMENT_CATEGORIES}
        valid_areas = {a for a, _ in Equipment.AREAS}

        try:
            with open(csv_file, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for row_num, row in enumerate(reader, start=2):
                    if not row.get('node_code') or not row.get('name') or not row.get('category'):
                        self.stdout.write(self.style.WARNING(
                            f'Row {row_num}: Skipping - missing required field '
                            f'(node_code, name, or category)'
                        ))
                        continue

                    category = row['category'].strip()
                    if category not in valid_categories:
                        raise CommandError(
                            f'Row {row_num}: invalid category "{category}". '
                            f'Must be one of: {sorted(valid_categories)}'
                        )

                    area = (row.get('area') or '').strip()
                    if area and area not in valid_areas:
                        raise CommandError(
                            f'Row {row_num}: invalid area "{area}". '
                            f'Must be one of: {sorted(valid_areas)} (or blank).'
                        )

                    equipment_data.append({
                        'node_code': row['node_code'].strip(),
                        'name': row['name'].strip(),
                        'category': category,
                        'description': (row.get('description') or '').strip(),
                        'technical_specs': (row.get('technical_specs') or '').strip(),
                        'area': area,
                        'is_essential': self._parse_bool(row.get('is_essential')),
                        'is_active': self._parse_bool(row.get('is_active')),
                    })

        except csv.Error as e:
            raise CommandError(f'Error reading TSV file: {e}')

        return equipment_data

    @staticmethod
    def _parse_bool(value):
        """Blank → False; only TRUE/1/YES (case-insensitive) flips to True."""
        return (value or '').strip().upper() in ('TRUE', '1', 'YES')

    def handle(self, *args, **options):
        """Create equipment for all nodes from TSV file"""

        csv_path = options['tsv']
        sync_mode = options['sync']

        self.stdout.write(f'Loading equipment data from: {csv_path}')
        if sync_mode:
            self.stdout.write(self.style.WARNING('Sync mode enabled: Will mark orphaned equipment as inactive'))

        # Load equipment data from TSV
        equipment_data = self.load_equipment_from_csv(csv_path)

        created_count = 0
        updated_count = 0
        processed_equipment_ids = set()  # Track equipment IDs processed from TSV

        for equip_data in equipment_data:
            node_code = equip_data['node_code']
            equipment_name = equip_data['name']
            category = equip_data['category']

            # Node must already exist (Node.organization is a required FK, so
            # we can't auto-stub one here). Run populate_redib_nodes first.
            try:
                node = Node.objects.get(code=node_code)
            except Node.DoesNotExist:
                raise CommandError(
                    f'Equipment row references unknown node_code "{node_code}". '
                    f'Run `populate_redib_nodes` first, or fix data/equipment.tsv.'
                )

            equipment, equipment_created = Equipment.objects.update_or_create(
                node=node,
                name=equipment_name,
                defaults={
                    'category': category,
                    'description': equip_data['description'],
                    'technical_specs': equip_data['technical_specs'],
                    'area': equip_data['area'],
                    'is_essential': equip_data['is_essential'],
                    'is_active': equip_data['is_active'],
                },
            )

            if equipment_created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ Created: {node_code} - {equipment_name} ({category}, {equip_data["area"] or "no area"})'
                ))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(
                    f'  ↻ Updated: {node_code} - {equipment_name} ({category}, {equip_data["area"] or "no area"})'
                ))

            # Track this equipment as processed
            processed_equipment_ids.add(equipment.id)

        # Handle sync mode: Mark orphaned equipment as inactive
        deactivated_count = 0
        if sync_mode:
            self.stdout.write('\n' + '-' * 60)
            self.stdout.write('Checking for orphaned equipment (in DB but not in TSV)...')

            # Find all equipment not in the processed set
            orphaned_equipment = Equipment.objects.exclude(id__in=processed_equipment_ids).filter(is_active=True)

            for equip in orphaned_equipment:
                equip.is_active = False
                equip.save()
                deactivated_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⊗ Deactivated: {equip.node.code} - {equip.name} (not in TSV)'
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
        self.stdout.write(f'  Equipment created: {created_count}')
        self.stdout.write(f'  Equipment updated: {updated_count}')
        if sync_mode and deactivated_count > 0:
            self.stdout.write(f'  Equipment deactivated: {deactivated_count}')
        self.stdout.write(f'  Total equipment: {created_count + updated_count} items')
        self.stdout.write('=' * 60 + '\n')
