"""
Django management command to populate the database with real reference data only.

Loads nodes, organizations, users, equipment, funding agencies (from TSVs)
and email templates. No fake test data (no calls, applications, or test applicants).

Use this after creating a fresh database and superuser:

    rm db.sqlite3
    python manage.py migrate
    python manage.py createsuperuser
    python manage.py setup_base_database

Or to reset an existing database (preserves superusers):

    python manage.py setup_base_database --reset --yes
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate database with real reference data only (nodes, organizations, users, equipment, funding agencies, email templates)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Clear all data (except superusers) before populating',
        )
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Skip confirmation prompt for reset',
        )

    def handle(self, *args, **options):
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('ReDIB Portal - Base Database Setup'))
        self.stdout.write('Real reference data only (no test/fake data)')
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
            self.stdout.write(self.style.SUCCESS('  Done\n'))

        # Step 1: Nodes (no dependencies; users and equipment depend on nodes)
        self.stdout.write('Step 1: Populating ReDIB nodes from data/nodes.tsv...')
        try:
            call_command('populate_redib_nodes', verbosity=0)
            self.stdout.write(self.style.SUCCESS('  Done'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  Failed: {e}'))
            return

        # Step 2: Organizations (no dependencies; users depend on organizations).
        # Run before users so user.organization can link to fully-populated org records
        # rather than relying on populate_redib_users' auto-create-stub fallback.
        self.stdout.write('Step 2: Populating organizations from data/organizations.tsv...')
        try:
            call_command('populate_redib_organizations', verbosity=0)
            self.stdout.write(self.style.SUCCESS('  Done'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  Failed: {e}'))
            return

        # Step 3: Users (depends on nodes + organizations)
        self.stdout.write('Step 3: Populating users from data/users.tsv...')
        try:
            call_command('populate_redib_users', verbosity=0)
            self.stdout.write(self.style.SUCCESS('  Done'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  Failed: {e}'))
            return

        # Step 4: Equipment (depends on nodes)
        self.stdout.write('Step 4: Populating equipment from data/equipment.tsv...')
        try:
            call_command('populate_redib_equipment', verbosity=0)
            self.stdout.write(self.style.SUCCESS('  Done'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  Failed: {e}'))
            return

        # Step 5: Funding agencies (no dependencies)
        self.stdout.write('Step 5: Populating funding agencies from data/funding_agencies.tsv...')
        try:
            call_command('populate_redib_funding_agencies', verbosity=0)
            self.stdout.write(self.style.SUCCESS('  Done'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  Failed: {e}'))
            return

        # Step 6: Email templates
        self.stdout.write('Step 6: Seeding email templates...')
        try:
            call_command('seed_email_templates', verbosity=0)
            self.stdout.write(self.style.SUCCESS('  Done'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  Failed: {e}'))
            return

        # Step 7: Configure site
        self.stdout.write('Step 7: Configuring site...')
        self.configure_site()
        self.stdout.write(self.style.SUCCESS('  Done'))

        # Summary
        self.print_summary()

    def reset_database(self):
        """Clear all data from the database except superusers."""
        from django.apps import apps
        from access.models import Publication, AccessGrant
        from evaluations.models import Evaluation
        from applications.models import (
            FeasibilityReview, RequestedAccess, Application, NodeResolution, FundingAgency
        )
        from calls.models import CallEquipmentAllocation, Call
        from core.models import Equipment, Node, Organization, UserRole
        from communications.models import EmailLog, EmailTemplate, NotificationPreference
        from allauth.account.models import EmailAddress

        self.stdout.write('  Clearing data in dependency order...')

        # Clear in reverse dependency order
        for model, label in [
            (Publication, 'publications'),
            (AccessGrant, 'access grants'),
            (NodeResolution, 'node resolutions'),
            (Evaluation, 'evaluations'),
            (FeasibilityReview, 'feasibility reviews'),
            (RequestedAccess, 'requested accesses'),
            (Application, 'applications'),
            (CallEquipmentAllocation, 'call equipment allocations'),
            (Call, 'calls'),
            (FundingAgency, 'funding agencies'),
            (Equipment, 'equipment'),
            (Node, 'nodes'),
            (UserRole, 'user roles'),
            (EmailLog, 'email logs'),
            (NotificationPreference, 'notification preferences'),
            (EmailTemplate, 'email templates'),
        ]:
            count = model.objects.all().count()
            if count:
                model.objects.all().delete()
                self.stdout.write(f'    Deleted {count} {label}')

        # Delete non-superusers and their email addresses
        non_super = User.objects.filter(is_superuser=False)
        count = non_super.count()
        if count:
            EmailAddress.objects.filter(user__in=non_super).delete()
            non_super.delete()
            self.stdout.write(f'    Deleted {count} users (kept superusers)')

        count = Organization.objects.all().count()
        if count:
            Organization.objects.all().delete()
            self.stdout.write(f'    Deleted {count} organizations')

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

    def configure_site(self):
        """Set the Django Site object. Reads SITE_DOMAIN/SITE_NAME from env
        so dev environments can point at localhost."""
        import os
        from django.contrib.sites.models import Site
        site = Site.objects.get(id=1)
        site.domain = os.environ.get('SITE_DOMAIN', 'portal.redib.net')
        site.name = os.environ.get('SITE_NAME', 'ReDIB COA Portal')
        site.save()
        self.stdout.write(f'    Site: {site.name} ({site.domain})')

    def print_summary(self):
        """Print summary of populated data."""
        from core.models import Node, Equipment, Organization, UserRole
        from applications.models import FundingAgency
        from communications.models import EmailTemplate

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('BASE DATABASE SETUP COMPLETE'))
        self.stdout.write('=' * 70)

        self.stdout.write('\nData Summary:')
        self.stdout.write(f'  Nodes:              {Node.objects.count()}')
        self.stdout.write(f'  Organizations:      {Organization.objects.count()}')
        self.stdout.write(f'  Users:              {User.objects.count()}')
        self.stdout.write(f'  Equipment:          {Equipment.objects.count()}')
        self.stdout.write(f'  Funding agencies:   {FundingAgency.objects.count()}')
        self.stdout.write(f'  Email templates:    {EmailTemplate.objects.count()}')

        self.stdout.write('\nUser Roles:')
        for role in ['coordinator', 'node_coordinator', 'evaluator']:
            count = UserRole.objects.filter(role=role, is_active=True).count()
            self.stdout.write(f'  {role:20s}: {count}')

        self.stdout.write('\nAll TSV users have:')
        self.stdout.write('  Password:           changeme123')
        self.stdout.write('  Email verified:     yes')

        self.stdout.write('\n' + '=' * 70 + '\n')
