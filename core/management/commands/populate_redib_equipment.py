"""
Management command to populate ReDIB equipment across all nodes.

This creates exactly 17 equipment items as specified in the official
REDIB-APP-application-form-coa-redib.docx form.
"""
from django.core.management.base import BaseCommand
from core.models import Node, Equipment


class Command(BaseCommand):
    help = 'Populate equipment for all ReDIB nodes (17 items across 4 nodes)'

    def handle(self, *args, **options):
        """Create equipment for all nodes"""

        # Equipment data: (node_code, name, category)
        equipment_data = [
            # BioImaC (3 items)
            ('BioImaC', 'MRI 1 T', 'mri'),
            ('BioImaC', 'Cyclotron', 'cyclotron'),
            ('BioImaC', 'Radiochemistry Lab', 'other'),

            # CIC biomaGUNE (7 items)
            ('CIC-biomaGUNE', 'MRI 7 T', 'mri'),
            ('CIC-biomaGUNE', 'MRI 11.7 T', 'mri'),
            ('CIC-biomaGUNE', 'PET-CT', 'pet_ct'),
            ('CIC-biomaGUNE', 'SPECT-CT', 'spect'),
            ('CIC-biomaGUNE', 'PET-SPECT-CT-OI', 'other'),
            ('CIC-biomaGUNE', 'Cyclotron', 'cyclotron'),
            ('CIC-biomaGUNE', 'Radiochemistry Lab', 'other'),

            # Imaging La Fe (2 items)
            ('Imaging La Fe', 'MRI 3 T', 'mri'),
            ('Imaging La Fe', 'PET-MRI', 'pet_mri'),

            # TRIMA-CNIC (5 items)
            ('TRIMA-CNIC', 'MRI 3 T', 'mri'),
            ('TRIMA-CNIC', 'MRI 7 T', 'mri'),
            ('TRIMA-CNIC', 'PET-CT', 'pet_ct'),
            ('TRIMA-CNIC', 'SPECT-CT', 'spect'),
            ('TRIMA-CNIC', 'Multidetector-CT', 'ct'),
        ]

        created_count = 0
        updated_count = 0

        for node_code, equipment_name, category in equipment_data:
            # Get or create node
            node, node_created = Node.objects.get_or_create(
                code=node_code,
                defaults={
                    'name': node_code.replace('-', ' '),
                    'location': 'TBD',  # Will be updated manually via admin
                }
            )

            if node_created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created node: {node_code}')
                )

            # Get or create equipment
            equipment, equipment_created = Equipment.objects.get_or_create(
                node=node,
                name=equipment_name,
                defaults={
                    'category': category,
                    'is_essential': True,
                    'is_active': True,
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
                # Update existing equipment to ensure correct category and flags
                equipment.category = category
                equipment.is_essential = True
                equipment.is_active = True
                equipment.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  ↻ Updated: {node_code} - {equipment_name} ({category})'
                    )
                )

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(
            self.style.SUCCESS(
                f'Equipment population complete!'
            )
        )
        self.stdout.write(f'  Created: {created_count} items')
        self.stdout.write(f'  Updated: {updated_count} items')
        self.stdout.write(f'  Total: {created_count + updated_count} equipment items across 4 nodes')
        self.stdout.write('=' * 60 + '\n')
