"""
Django management command to set up a complete test database from scratch.

This is the MASTER seed script that:
1. Optionally resets the database (clears all data except superusers)
2. Runs all seed scripts in the correct order
3. Creates a fully populated test environment

Usage:
    python manage.py setup_test_database              # Seed without reset (may fail if data exists)
    python manage.py setup_test_database --reset      # Full reset and reseed (recommended for fresh start)
    python manage.py setup_test_database --reset --skip-applicants  # Reset but skip test applicants
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.db import connection

User = get_user_model()


class Command(BaseCommand):
    help = 'Set up a complete test database with all seed data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset database by clearing all data (except superusers) before seeding',
        )
        parser.add_argument(
            '--skip-applicants',
            action='store_true',
            help='Skip creating test applicants (useful for manual testing setup)',
        )
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Skip confirmation prompt for reset',
        )

    def handle(self, *args, **options):
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('ReDIB Portal - Test Database Setup'))
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
            self.stdout.write(self.style.SUCCESS('  ✓ Database reset complete\n'))

        # Step 1: Nodes
        self.stdout.write('Step 1: Populating ReDIB nodes...')
        try:
            call_command('populate_redib_nodes', verbosity=0)
            self.stdout.write(self.style.SUCCESS('  ✓ Nodes created'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  → Nodes may already exist: {e}'))

        # Step 2: Equipment
        self.stdout.write('Step 2: Populating equipment...')
        try:
            call_command('populate_redib_equipment', verbosity=0)
            self.stdout.write(self.style.SUCCESS('  ✓ Equipment created'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  → Equipment may already exist: {e}'))

        # Step 3: Users (coordinators, evaluators, node coordinators)
        self.stdout.write('Step 3: Populating users...')
        try:
            call_command('populate_redib_users', verbosity=0)
            self.stdout.write(self.style.SUCCESS('  ✓ Users created'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  → Users may already exist: {e}'))

        # Step 4: Development data (organizations, calls, sample applications)
        self.stdout.write('Step 4: Seeding development data...')
        try:
            call_command('seed_dev_data', verbosity=0)
            self.stdout.write(self.style.SUCCESS('  ✓ Development data created'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  → Dev data may already exist: {e}'))

        # Step 5: Email templates
        self.stdout.write('Step 5: Seeding email templates...')
        try:
            call_command('seed_email_templates', verbosity=0)
            self.stdout.write(self.style.SUCCESS('  ✓ Email templates created'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  → Email templates may already exist: {e}'))

        # Step 6: Test applicants (optional)
        if not options['skip_applicants']:
            self.stdout.write('Step 6: Seeding test applicants...')
            try:
                call_command('seed_test_applicants', verbosity=0)
                self.stdout.write(self.style.SUCCESS('  ✓ Test applicants created'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Failed to create test applicants: {e}'))
        else:
            self.stdout.write('Step 6: Skipping test applicants (--skip-applicants)')

        # Print summary
        self.print_summary()

    def reset_database(self):
        """Clear all data from the database except superusers."""
        from django.apps import apps

        # Import all models that need to be cleared
        from access.models import Publication, AccessGrant
        from evaluations.models import Evaluation
        from applications.models import (
            FeasibilityReview, RequestedAccess, Application, NodeResolution
        )
        from calls.models import CallEquipmentAllocation, Call
        from core.models import Equipment, Node, Organization, UserRole
        from communications.models import EmailLog, EmailTemplate, NotificationPreference

        self.stdout.write('  Clearing data in dependency order...')

        # Clear in reverse dependency order to avoid foreign key errors
        # Phase 9: Publications
        count = Publication.objects.all().count()
        Publication.objects.all().delete()
        if count:
            self.stdout.write(f'    → Deleted {count} publications')

        # Phase 8: Access grants
        count = AccessGrant.objects.all().count()
        AccessGrant.objects.all().delete()
        if count:
            self.stdout.write(f'    → Deleted {count} access grants')

        # Phase 6: Node Resolutions (NEW)
        count = NodeResolution.objects.all().count()
        NodeResolution.objects.all().delete()
        if count:
            self.stdout.write(f'    → Deleted {count} node resolutions')

        # Phase 5: Evaluations
        count = Evaluation.objects.all().count()
        Evaluation.objects.all().delete()
        if count:
            self.stdout.write(f'    → Deleted {count} evaluations')

        # Phase 3: Feasibility reviews
        count = FeasibilityReview.objects.all().count()
        FeasibilityReview.objects.all().delete()
        if count:
            self.stdout.write(f'    → Deleted {count} feasibility reviews')

        # Phase 2: Applications and requested access
        count = RequestedAccess.objects.all().count()
        RequestedAccess.objects.all().delete()
        if count:
            self.stdout.write(f'    → Deleted {count} requested accesses')

        count = Application.objects.all().count()
        Application.objects.all().delete()
        if count:
            self.stdout.write(f'    → Deleted {count} applications')

        # Phase 1: Calls
        count = CallEquipmentAllocation.objects.all().count()
        CallEquipmentAllocation.objects.all().delete()
        if count:
            self.stdout.write(f'    → Deleted {count} call equipment allocations')

        count = Call.objects.all().count()
        Call.objects.all().delete()
        if count:
            self.stdout.write(f'    → Deleted {count} calls')

        # Core: Equipment and Nodes
        count = Equipment.objects.all().count()
        Equipment.objects.all().delete()
        if count:
            self.stdout.write(f'    → Deleted {count} equipment')

        count = Node.objects.all().count()
        Node.objects.all().delete()
        if count:
            self.stdout.write(f'    → Deleted {count} nodes')

        # Users and roles (keep superusers)
        count = UserRole.objects.all().count()
        UserRole.objects.all().delete()
        if count:
            self.stdout.write(f'    → Deleted {count} user roles')

        count = User.objects.filter(is_superuser=False).count()
        User.objects.filter(is_superuser=False).delete()
        if count:
            self.stdout.write(f'    → Deleted {count} users (kept superusers)')

        count = Organization.objects.all().count()
        Organization.objects.all().delete()
        if count:
            self.stdout.write(f'    → Deleted {count} organizations')

        # Communications
        count = EmailLog.objects.all().count()
        EmailLog.objects.all().delete()
        if count:
            self.stdout.write(f'    → Deleted {count} email logs')

        count = NotificationPreference.objects.all().count()
        NotificationPreference.objects.all().delete()
        if count:
            self.stdout.write(f'    → Deleted {count} notification preferences')

        count = EmailTemplate.objects.all().count()
        EmailTemplate.objects.all().delete()
        if count:
            self.stdout.write(f'    → Deleted {count} email templates')

        # Clear historical records if they exist
        try:
            from simple_history.models import HistoricalRecords
            # Get all historical models
            for model in apps.get_models():
                if model._meta.model_name.startswith('historical'):
                    count = model.objects.all().count()
                    if count:
                        model.objects.all().delete()
                        self.stdout.write(f'    → Deleted {count} {model._meta.model_name} records')
        except Exception:
            pass  # Historical records cleanup is optional

    def print_summary(self):
        """Print summary of created data."""
        from core.models import Node, Equipment, Organization, UserRole
        from calls.models import Call
        from applications.models import Application, NodeResolution
        from evaluations.models import Evaluation

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('DATABASE SETUP COMPLETE'))
        self.stdout.write('=' * 70)

        self.stdout.write('\nData Summary:')
        self.stdout.write(f'  Nodes:              {Node.objects.count()}')
        self.stdout.write(f'  Equipment:          {Equipment.objects.count()}')
        self.stdout.write(f'  Organizations:      {Organization.objects.count()}')
        self.stdout.write(f'  Users:              {User.objects.count()}')
        self.stdout.write(f'  Calls:              {Call.objects.count()}')
        self.stdout.write(f'  Applications:       {Application.objects.count()}')
        self.stdout.write(f'  Node Resolutions:   {NodeResolution.objects.count()}')
        self.stdout.write(f'  Evaluations:        {Evaluation.objects.count()}')

        # Show user roles
        self.stdout.write('\nUser Roles:')
        for role in ['coordinator', 'node_coordinator', 'evaluator', 'applicant']:
            count = UserRole.objects.filter(role=role, is_active=True).count()
            self.stdout.write(f'  {role:20s}: {count}')

        # Show application statuses
        self.stdout.write('\nApplications by Status:')
        from django.db.models import Count
        status_counts = Application.objects.values('status').annotate(
            count=Count('status')
        ).order_by('-count')
        for item in status_counts:
            status_label = dict(Application.APPLICATION_STATUSES).get(item['status'], item['status'])
            self.stdout.write(f'  {status_label:30s}: {item["count"]}')

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('\nTest Accounts:')
        self.stdout.write('-' * 70)

        # Show accounts by role
        self.stdout.write('  Coordinators (password: changeme123 or testpass123):')
        for user in User.objects.filter(roles__role='coordinator', roles__is_active=True).distinct()[:3]:
            self.stdout.write(f'    {user.email}')

        self.stdout.write('  Node Coordinators (password: changeme123 or testpass123):')
        for user in User.objects.filter(roles__role='node_coordinator', roles__is_active=True).distinct()[:4]:
            self.stdout.write(f'    {user.email}')

        self.stdout.write('  Evaluators (password: changeme123 or testpass123):')
        for user in User.objects.filter(roles__role='evaluator', roles__is_active=True).distinct()[:3]:
            self.stdout.write(f'    {user.email}')

        self.stdout.write('  Test Applicants (password: testpass123):')
        for user in User.objects.filter(email__icontains='testapplicant').distinct()[:4]:
            self.stdout.write(f'    {user.email}')

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('\nTo start the development server:')
        self.stdout.write('  python manage.py runserver')
        self.stdout.write('\nTo reset and reseed the database:')
        self.stdout.write('  python manage.py setup_test_database --reset --yes')
        self.stdout.write('=' * 70 + '\n')
