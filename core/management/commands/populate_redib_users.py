"""
Management command to populate ReDIB users from CSV file.

This creates core user accounts (coordinators, node coordinators, evaluators)
from a CSV file. By default, loads from data/users.csv.

Role format in CSV:
- Simple role: "coordinator" or "evaluator"
- Node-specific: "node_coordinator:CIC-biomaGUNE"
- Area-specific: "evaluator:preclinical"
- Multiple roles: "coordinator;evaluator:clinical"
"""
import csv
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth import get_user_model
from core.models import Organization, Node, UserRole

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate ReDIB users from CSV file (default: data/users.csv)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            default='data/users.csv',
            help='Path to users CSV file (default: data/users.csv)'
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Mark users not in CSV as inactive (is_active=False)'
        )

    def load_users_from_csv(self, csv_path):
        """Load user data from CSV file."""
        # Get project root directory
        project_root = Path(settings.BASE_DIR)
        csv_file = project_root / csv_path

        if not csv_file.exists():
            raise CommandError(f'CSV file not found: {csv_file}')

        users_data = []

        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
                    # Validate required fields
                    if not row.get('email') or not row.get('first_name') or not row.get('last_name'):
                        self.stdout.write(
                            self.style.WARNING(
                                f'Row {row_num}: Skipping - missing required fields (email, first_name, or last_name)'
                            )
                        )
                        continue

                    # Convert boolean fields
                    is_staff = row.get('is_staff', 'FALSE').strip().upper() in ['TRUE', '1', 'YES']
                    is_active = row.get('is_active', 'TRUE').strip().upper() in ['TRUE', '1', 'YES']

                    users_data.append({
                        'email': row['email'].strip(),
                        'first_name': row['first_name'].strip(),
                        'last_name': row['last_name'].strip(),
                        'organization_name': row.get('organization_name', '').strip(),
                        'orcid': row.get('orcid', '').strip(),
                        'phone': row.get('phone', '').strip(),
                        'position': row.get('position', '').strip(),
                        'is_staff': is_staff,
                        'is_active': is_active,
                        'roles': row.get('roles', '').strip(),
                    })

        except csv.Error as e:
            raise CommandError(f'Error reading CSV file: {e}')
        except Exception as e:
            raise CommandError(f'Unexpected error reading CSV: {e}')

        return users_data

    def parse_roles(self, roles_string):
        """
        Parse roles string into list of (role, node_code, area) tuples.

        Examples:
        - "coordinator" -> [('coordinator', None, '')]
        - "node_coordinator:CIC-biomaGUNE" -> [('node_coordinator', 'CIC-biomaGUNE', '')]
        - "evaluator:preclinical" -> [('evaluator', None, 'preclinical')]
        - "coordinator;evaluator:clinical" -> [('coordinator', None, ''), ('evaluator', None, 'clinical')]
        """
        if not roles_string:
            return []

        parsed_roles = []
        role_entries = roles_string.split(';')

        for entry in role_entries:
            entry = entry.strip()
            if not entry:
                continue

            if ':' in entry:
                role, qualifier = entry.split(':', 1)
                role = role.strip()
                qualifier = qualifier.strip()

                # Determine if qualifier is a node code or area
                # Node roles: node_coordinator
                # Area roles: evaluator
                if role == 'node_coordinator':
                    parsed_roles.append((role, qualifier, ''))
                elif role == 'evaluator':
                    # Check if qualifier is a valid area
                    valid_areas = ['preclinical', 'clinical', 'radiotracers']
                    if qualifier in valid_areas:
                        parsed_roles.append((role, None, qualifier))
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Invalid evaluator area: {qualifier}. Using empty area.'
                            )
                        )
                        parsed_roles.append((role, None, ''))
                else:
                    parsed_roles.append((role, None, ''))
            else:
                # Simple role without qualifier
                parsed_roles.append((entry, None, ''))

        return parsed_roles

    def handle(self, *args, **options):
        """Create users from CSV file"""

        csv_path = options['csv']
        sync_mode = options['sync']

        self.stdout.write(f'Loading user data from: {csv_path}')
        if sync_mode:
            self.stdout.write(self.style.WARNING('Sync mode enabled: Will mark orphaned users as inactive'))

        # Load user data from CSV
        users_data = self.load_users_from_csv(csv_path)

        created_count = 0
        updated_count = 0
        roles_created_count = 0
        processed_user_ids = set()  # Track user IDs processed from CSV

        for user_data in users_data:
            email = user_data['email']

            # Get or create organization
            organization = None
            if user_data['organization_name']:
                try:
                    organization = Organization.objects.get(name=user_data['organization_name'])
                except Organization.DoesNotExist:
                    # Create organization if it doesn't exist
                    organization = Organization.objects.create(
                        name=user_data['organization_name'],
                        organization_type='other'  # Default type
                    )
                    self.stdout.write(
                        self.style.WARNING(
                            f'  → Created organization: {user_data["organization_name"]}'
                        )
                    )

            # Get or create user
            user, user_created = User.objects.update_or_create(
                email=email,
                defaults={
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'organization': organization,
                    'orcid': user_data['orcid'],
                    'phone': user_data['phone'],
                    'position': user_data['position'],
                    'is_staff': user_data['is_staff'],
                    'is_active': user_data['is_active'],
                }
            )

            # Set password for new users only
            if user_created:
                user.set_password('changeme123')  # Default password
                user.save()
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Created: {email} ({user.get_full_name()})'
                    )
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  ↻ Updated: {email} ({user.get_full_name()})'
                    )
                )

            # Track this user as processed
            processed_user_ids.add(user.id)

            # Handle roles
            parsed_roles = self.parse_roles(user_data['roles'])
            for role_name, node_code, area in parsed_roles:
                # Get node if specified
                node = None
                if node_code:
                    try:
                        node = Node.objects.get(code=node_code)
                    except Node.DoesNotExist:
                        self.stdout.write(
                            self.style.ERROR(
                                f'    ✗ Node not found: {node_code} (skipping role {role_name})'
                            )
                        )
                        continue

                # Create or update user role
                role, role_created = UserRole.objects.update_or_create(
                    user=user,
                    role=role_name,
                    node=node,
                    defaults={
                        'area': area,
                        'is_active': True,
                    }
                )

                if role_created:
                    roles_created_count += 1
                    node_info = f" at {node.code}" if node else ""
                    area_info = f" ({area})" if area else ""
                    self.stdout.write(
                        f'    → Role: {role_name}{node_info}{area_info}'
                    )

        # Handle sync mode: Mark orphaned users as inactive
        deactivated_count = 0
        if sync_mode:
            self.stdout.write('\n' + '-' * 60)
            self.stdout.write('Checking for orphaned users (in DB but not in CSV)...')

            # Find all users not in the processed set, excluding superusers
            orphaned_users = User.objects.exclude(id__in=processed_user_ids).filter(
                is_active=True,
                is_superuser=False
            )

            for user in orphaned_users:
                user.is_active = False
                user.save()
                deactivated_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⊗ Deactivated: {user.email} ({user.get_full_name()}) (not in CSV)'
                    )
                )

            if deactivated_count == 0:
                self.stdout.write(self.style.SUCCESS('  ✓ No orphaned users found'))

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(
            self.style.SUCCESS(
                f'User population complete!'
            )
        )
        self.stdout.write(f'  Users created: {created_count}')
        self.stdout.write(f'  Users updated: {updated_count}')
        if sync_mode and deactivated_count > 0:
            self.stdout.write(f'  Users deactivated: {deactivated_count}')
        self.stdout.write(f'  Total users: {created_count + updated_count}')
        self.stdout.write(f'  Roles assigned: {roles_created_count}')
        if created_count > 0:
            self.stdout.write('\n' + self.style.WARNING('Note: New users have default password "changeme123"'))
        self.stdout.write('=' * 60 + '\n')
