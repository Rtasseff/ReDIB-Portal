"""
Django management command to set up Local Test 1 database scenario.

This creates a minimal test environment with:
- 3 nodes: CIC biomaGUNE, BioImaC, CNIC
- 2 equipment items per node (6 total)
- 10 users: 1 coordinator, 3 node coordinators, 3 evaluators, 3 applicants
- Zero calls, zero applications

All passwords are set to 'testpass123' and emails are pre-verified.

Usage:
    python manage.py setup_localtest1_database              # Setup (fails if data exists)
    python manage.py setup_localtest1_database --reset      # Full reset and setup
    python manage.py setup_localtest1_database --reset --yes  # Skip confirmation
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

# Standard password for all test users
TEST_PASSWORD = 'testpass123'


class Command(BaseCommand):
    help = 'Set up Local Test 1 database with 3 nodes, 6 equipment, 10 users, no calls/applications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset database by clearing all data (except superusers) before setup',
        )
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Skip confirmation prompt for reset',
        )

    def handle(self, *args, **options):
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('ReDIB Portal - Local Test 1 Database Setup'))
        self.stdout.write('=' * 70 + '\n')

        if options['reset']:
            if not options['yes']:
                self.stdout.write(self.style.WARNING(
                    'WARNING: This will DELETE all data except superuser accounts!'
                ))
                confirm = input('Are you sure you want to continue? [y/N]: ')
                if confirm.lower() != 'y':
                    self.stdout.write(self.style.ERROR('Aborted.'))
                    return

            self.stdout.write(self.style.WARNING('\nStep 0: Resetting database...'))
            self.reset_database()
            self.stdout.write(self.style.SUCCESS('  Database reset complete\n'))

        with transaction.atomic():
            # Step 1: Create nodes
            self.stdout.write('Step 1: Creating nodes...')
            nodes = self.create_nodes()
            self.stdout.write(self.style.SUCCESS(f'  Created {len(nodes)} nodes'))

            # Step 2: Create equipment
            self.stdout.write('Step 2: Creating equipment...')
            equipment_count = self.create_equipment(nodes)
            self.stdout.write(self.style.SUCCESS(f'  Created {equipment_count} equipment items'))

            # Step 3: Create users
            self.stdout.write('Step 3: Creating users...')
            users = self.create_users(nodes)
            self.stdout.write(self.style.SUCCESS(f'  Created {len(users)} users'))

            # Step 4: Seed email templates
            self.stdout.write('Step 4: Seeding email templates...')
            try:
                from django.core.management import call_command
                call_command('seed_email_templates', verbosity=0)
                self.stdout.write(self.style.SUCCESS('  Email templates created'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  Email templates may already exist: {e}'))

        # Print summary
        self.print_summary(users)

    def reset_database(self):
        """Clear all data from the database except superusers."""
        from django.apps import apps
        from access.models import Publication, AccessGrant
        from evaluations.models import Evaluation
        from applications.models import (
            FeasibilityReview, RequestedAccess, Application, NodeResolution
        )
        from calls.models import CallEquipmentAllocation, Call
        from core.models import Equipment, Node, Organization, UserRole
        from communications.models import EmailLog, EmailTemplate, NotificationPreference
        from allauth.account.models import EmailAddress

        self.stdout.write('  Clearing data in dependency order...')

        # Clear in reverse dependency order
        for model, name in [
            (Publication, 'publications'),
            (AccessGrant, 'access grants'),
            (NodeResolution, 'node resolutions'),
            (Evaluation, 'evaluations'),
            (FeasibilityReview, 'feasibility reviews'),
            (RequestedAccess, 'requested accesses'),
            (Application, 'applications'),
            (CallEquipmentAllocation, 'call equipment allocations'),
            (Call, 'calls'),
            (Equipment, 'equipment'),
            (Node, 'nodes'),
            (UserRole, 'user roles'),
            (EmailAddress, 'email addresses'),
            (Organization, 'organizations'),
            (EmailLog, 'email logs'),
            (NotificationPreference, 'notification preferences'),
            (EmailTemplate, 'email templates'),
        ]:
            count = model.objects.all().count()
            if count:
                model.objects.all().delete()
                self.stdout.write(f'    Deleted {count} {name}')

        # Delete non-superusers
        count = User.objects.filter(is_superuser=False).count()
        if count:
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(f'    Deleted {count} users (kept superusers)')

        # Clear historical records
        try:
            for model in apps.get_models():
                if model._meta.model_name.startswith('historical'):
                    count = model.objects.all().count()
                    if count:
                        model.objects.all().delete()
                        self.stdout.write(f'    Deleted {count} {model._meta.model_name} records')
        except Exception:
            pass

    def create_nodes(self):
        """Create the 3 test nodes."""
        from core.models import Node

        nodes_data = [
            {
                'code': 'CICBIO',
                'name': 'CIC biomaGUNE',
                'location': 'San Sebastian, Spain',
                'description': 'Center for Cooperative Research in Biomaterials',
                'contact_email': 'cicbio@test.redib.net',
            },
            {
                'code': 'BIOIMAC',
                'name': 'BioImaC',
                'location': 'Murcia, Spain',
                'description': 'Biomedical Imaging Center of Murcia',
                'contact_email': 'bioimac@test.redib.net',
            },
            {
                'code': 'CNIC',
                'name': 'CNIC',
                'location': 'Madrid, Spain',
                'description': 'Centro Nacional de Investigaciones Cardiovasculares',
                'contact_email': 'cnic@test.redib.net',
            },
        ]

        nodes = []
        for data in nodes_data:
            node, created = Node.objects.get_or_create(
                code=data['code'],
                defaults=data
            )
            nodes.append(node)
            status = 'Created' if created else 'Exists'
            self.stdout.write(f'    {status}: {node.name} ({node.code})')

        return nodes

    def create_equipment(self, nodes):
        """Create 2 equipment items per node."""
        from core.models import Equipment

        equipment_data = {
            'CICBIO': [
                {'name': 'MRI 3T Scanner', 'description': '3 Tesla MRI for preclinical imaging'},
                {'name': 'PET-CT Scanner', 'description': 'Combined PET-CT for molecular imaging'},
            ],
            'BIOIMAC': [
                {'name': 'MRI 7T Scanner', 'description': '7 Tesla ultra-high field MRI'},
                {'name': 'Optical Imaging System', 'description': 'Fluorescence and bioluminescence imaging'},
            ],
            'CNIC': [
                {'name': 'Cardiac MRI', 'description': 'Specialized cardiac MRI system'},
                {'name': 'Micro-CT Scanner', 'description': 'High-resolution micro-CT for small animals'},
            ],
        }

        count = 0
        for node in nodes:
            items = equipment_data.get(node.code, [])
            for item in items:
                equip, created = Equipment.objects.get_or_create(
                    name=item['name'],
                    node=node,
                    defaults={
                        'description': item['description'],
                        'is_active': True,
                    }
                )
                count += 1 if created else 0
                status = 'Created' if created else 'Exists'
                self.stdout.write(f'    {status}: {equip.name} @ {node.code}')

        return count

    def create_users(self, nodes):
        """Create all test users with verified emails."""
        from core.models import UserRole
        from allauth.account.models import EmailAddress

        users_created = []

        # User definitions: (email, first_name, last_name, role, node_code, area)
        users_data = [
            # ReDIB Coordinator
            {
                'email': 'coordinator@test.redib.net',
                'first_name': 'Carlos',
                'last_name': 'Martinez',
                'position': 'ReDIB Coordinator',
                'role': 'coordinator',
                'node_code': None,
                'area': '',
            },
            # Node Coordinators (one per node)
            {
                'email': 'nc.cicbio@test.redib.net',
                'first_name': 'Elena',
                'last_name': 'Fernandez',
                'position': 'Node Coordinator',
                'role': 'node_coordinator',
                'node_code': 'CICBIO',
                'area': '',
            },
            {
                'email': 'nc.bioimac@test.redib.net',
                'first_name': 'Miguel',
                'last_name': 'Santos',
                'position': 'Node Coordinator',
                'role': 'node_coordinator',
                'node_code': 'BIOIMAC',
                'area': '',
            },
            {
                'email': 'nc.cnic@test.redib.net',
                'first_name': 'Isabel',
                'last_name': 'Lopez',
                'position': 'Node Coordinator',
                'role': 'node_coordinator',
                'node_code': 'CNIC',
                'area': '',
            },
            # Evaluators
            {
                'email': 'eval.preclinical@test.redib.net',
                'first_name': 'Ana',
                'last_name': 'Rodriguez',
                'position': 'Senior Researcher',
                'role': 'evaluator',
                'node_code': None,
                'area': 'preclinical',
            },
            {
                'email': 'eval.clinical@test.redib.net',
                'first_name': 'Pedro',
                'last_name': 'Gonzalez',
                'position': 'Clinical Professor',
                'role': 'evaluator',
                'node_code': None,
                'area': 'clinical',
            },
            {
                'email': 'eval.radiotracers@test.redib.net',
                'first_name': 'Laura',
                'last_name': 'Navarro',
                'position': 'Radiochemist',
                'role': 'evaluator',
                'node_code': None,
                'area': 'radiotracers',
            },
            # Applicants
            {
                'email': 'applicant1@test.redib.net',
                'first_name': 'Sofia',
                'last_name': 'Ruiz',
                'position': 'PhD Student',
                'role': 'applicant',
                'node_code': None,
                'area': '',
            },
            {
                'email': 'applicant2@test.redib.net',
                'first_name': 'Diego',
                'last_name': 'Moreno',
                'position': 'Postdoctoral Researcher',
                'role': 'applicant',
                'node_code': None,
                'area': '',
            },
            {
                'email': 'applicant3@test.redib.net',
                'first_name': 'Carmen',
                'last_name': 'Jimenez',
                'position': 'Principal Investigator',
                'role': 'applicant',
                'node_code': None,
                'area': '',
            },
        ]

        # Build node lookup
        node_lookup = {n.code: n for n in nodes}

        for data in users_data:
            # Create user
            user, created = User.objects.get_or_create(
                email=data['email'],
                defaults={
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'position': data.get('position', ''),
                    'is_active': True,
                }
            )

            if created:
                # Set password
                user.set_password(TEST_PASSWORD)
                user.save()

                # Create verified email address (django-allauth)
                EmailAddress.objects.create(
                    user=user,
                    email=user.email,
                    verified=True,
                    primary=True
                )

                self.stdout.write(f'    Created: {user.email} ({data["role"]})')
            else:
                # Ensure password is set correctly for existing users
                user.set_password(TEST_PASSWORD)
                user.save()

                # Ensure email is verified
                email_addr, _ = EmailAddress.objects.get_or_create(
                    user=user,
                    email=user.email,
                    defaults={'verified': True, 'primary': True}
                )
                if not email_addr.verified:
                    email_addr.verified = True
                    email_addr.primary = True
                    email_addr.save()

                self.stdout.write(f'    Exists (password reset): {user.email} ({data["role"]})')

            # Create role assignment
            role_kwargs = {
                'user': user,
                'role': data['role'],
            }

            # Add node for node_coordinator role
            if data['node_code']:
                role_kwargs['node'] = node_lookup[data['node_code']]

            role, role_created = UserRole.objects.get_or_create(
                **role_kwargs,
                defaults={
                    'is_active': True,
                    'area': data.get('area') or '',
                }
            )

            # Update area if it exists
            if data.get('area') and not role.area:
                role.area = data['area']
                role.save()

            users_created.append({
                'user': user,
                'role': data['role'],
                'node_code': data.get('node_code'),
                'area': data.get('area'),
            })

        return users_created

    def print_summary(self, users):
        """Print summary of created data."""
        from core.models import Node, Equipment, UserRole
        from calls.models import Call
        from applications.models import Application

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('LOCAL TEST 1 DATABASE SETUP COMPLETE'))
        self.stdout.write('=' * 70)

        self.stdout.write('\nData Summary:')
        self.stdout.write(f'  Nodes:              {Node.objects.count()}')
        self.stdout.write(f'  Equipment:          {Equipment.objects.count()}')
        self.stdout.write(f'  Users (non-super):  {User.objects.filter(is_superuser=False).count()}')
        self.stdout.write(f'  Calls:              {Call.objects.count()}')
        self.stdout.write(f'  Applications:       {Application.objects.count()}')

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('USER ACCOUNTS (All passwords: testpass123)')
        self.stdout.write('=' * 70)
        self.stdout.write('')
        self.stdout.write(f'{"Email":<35} {"Name":<25} {"Role":<18} {"Node/Spec"}')
        self.stdout.write('-' * 95)

        for u in users:
            user = u['user']
            name = f"{user.first_name} {user.last_name}"
            extra = u.get('node_code') or u.get('area') or '-'
            self.stdout.write(f'{user.email:<35} {name:<25} {u["role"]:<18} {extra}')

        self.stdout.write('-' * 95)
        self.stdout.write('')
        self.stdout.write('NODES AND EQUIPMENT:')
        self.stdout.write('-' * 70)

        for node in Node.objects.all():
            self.stdout.write(f'\n  {node.name} ({node.code}) - {node.location}')
            for equip in Equipment.objects.filter(node=node):
                self.stdout.write(f'    - {equip.name}')

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('\nTo start the development server:')
        self.stdout.write('  python manage.py runserver')
        self.stdout.write('\nTo reset this test database:')
        self.stdout.write('  python manage.py setup_localtest1_database --reset --yes')
        self.stdout.write('=' * 70 + '\n')
