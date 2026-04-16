"""
Django management command: setup_livetest_small_database

Seeds a *minimal* subset of real data for a sanity-check pass on the live
production server, before opening it up to real applicants.

Contents:
- 4 organizations:
    * Asociación de Investigación Cooperativa en Biomateriales (real, host of CIC biomaGUNE)
    * Red Distribuida de Imagen Biomédica                      (real, ReDIB ICTS)
    * Test Hospital Alpha (livetest)                           (made-up — for org-dropdown variety)
    * Test University Beta (livetest)                          (made-up — for org-dropdown variety)
- 1 node:        CIC biomaGUNE (from data/nodes.tsv)
- All equipment under that node (from data/equipment.tsv)
- 3 users (all password 'testpass123', emails pre-verified):
    * rtasseff@cicbiomagune.es   — node coordinator for CIC-biomaGUNE  (from data/users.tsv)
    * coordinator@redib.net      — ReDIB coordinator                   (from data/users.tsv)
    * info@redib.net             — evaluator (preclinical)             (made-up)
- No calls, no applications. Email templates and the Site record are seeded.

The two TSV-sourced orgs are required to satisfy FK constraints (CIC biomaGUNE
node + rtasseff link to Biomateriales; coordinator and the made-up evaluator
both belong to Red Distribuida).

Usage:
    python manage.py setup_livetest_small_database --reset --yes

Run with --reset on the live server to wipe existing data (preserves
superusers) before seeding.
"""
import csv
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

User = get_user_model()

TEST_PASSWORD = 'testpass123'

# Real-data lookups — anchor names live in the TSVs and must not drift.
HOST_ORG_NAME = 'Asociación de Investigación Cooperativa en Biomateriales'
REDIB_ORG_NAME = 'Red Distribuida de Imagen Biomédica'
NODE_CODE = 'CIC-biomaGUNE'
RTASSEFF_EMAIL = 'rtasseff@cicbiomagune.es'
COORDINATOR_EMAIL = 'coordinator@redib.net'
EVALUATOR_EMAIL = 'info@redib.net'


class Command(BaseCommand):
    help = (
        'Seed a small live-test sandbox: CIC biomaGUNE node only, 3 users '
        '(node-coord + ReDIB coord + preclinical evaluator), no calls/apps.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='Wipe all data (except superusers) before seeding.',
        )
        parser.add_argument(
            '--yes', action='store_true',
            help='Skip the interactive confirmation prompt for --reset.',
        )

    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('ReDIB Portal — Livetest Small Sandbox'))
        self.stdout.write('=' * 70 + '\n')

        if options['reset']:
            if not options['yes']:
                self.stdout.write(self.style.WARNING(
                    'WARNING: This will DELETE all data except superuser accounts.'
                ))
                if input('Are you sure? [y/N]: ').strip().lower() != 'y':
                    self.stdout.write(self.style.ERROR('Aborted.'))
                    return

            self.stdout.write(self.style.WARNING('\nStep 0: Resetting database...'))
            self.reset_database()
            self.stdout.write(self.style.SUCCESS('  Done.\n'))

        with transaction.atomic():
            self.stdout.write('Step 1: Creating organizations...')
            orgs = self.create_organizations()
            self.stdout.write(self.style.SUCCESS(f'  Total: {len(orgs)} organizations'))

            self.stdout.write('Step 2: Creating CIC biomaGUNE node...')
            node = self.create_node(orgs[HOST_ORG_NAME])
            self.stdout.write(self.style.SUCCESS(f'  Node: {node.code}'))

            self.stdout.write('Step 3: Creating equipment for CIC biomaGUNE...')
            equip_count = self.create_equipment(node)
            self.stdout.write(self.style.SUCCESS(f'  Equipment items: {equip_count}'))

            self.stdout.write('Step 4: Creating users + roles...')
            users = self.create_users(orgs, node)
            self.stdout.write(self.style.SUCCESS(f'  Users: {len(users)}'))

            self.stdout.write('Step 5: Configuring site...')
            self.configure_site()
            self.stdout.write(self.style.SUCCESS('  Done.'))

            self.stdout.write('Step 6: Seeding email templates...')
            try:
                call_command('seed_email_templates', verbosity=0)
                self.stdout.write(self.style.SUCCESS('  Done.'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f'  Templates may already exist: {e}'
                ))

        self.print_summary(orgs, node, equip_count, users)

    # ------------------------------------------------------------------
    # Reset — same dependency-order pattern as setup_localtest3_database.
    # ------------------------------------------------------------------
    def reset_database(self):
        from django.apps import apps
        from access.models import Publication, AccessGrant
        from evaluations.models import Evaluation
        from applications.models import (
            FeasibilityReview, RequestedAccess, Application, NodeResolution,
            FundingAgency,
        )
        from calls.models import CallEquipmentAllocation, Call
        from core.models import Equipment, Node, Organization, UserRole
        from communications.models import (
            EmailLog, EmailTemplate, NotificationPreference,
        )
        from allauth.account.models import EmailAddress

        self.stdout.write('  Clearing data in dependency order...')
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
            (Equipment, 'equipment'),
            (Node, 'nodes'),
            (FundingAgency, 'funding agencies'),
            (UserRole, 'user roles'),
            (Organization, 'organizations'),
            (EmailLog, 'email logs'),
            (NotificationPreference, 'notification preferences'),
            (EmailTemplate, 'email templates'),
        ]:
            count = model.objects.all().count()
            if count:
                model.objects.all().delete()
                self.stdout.write(f'    Deleted {count} {label}')

        non_super_emails = EmailAddress.objects.filter(user__is_superuser=False)
        n = non_super_emails.count()
        if n:
            non_super_emails.delete()
            self.stdout.write(f'    Deleted {n} email addresses (kept superuser)')

        n = User.objects.filter(is_superuser=False).count()
        if n:
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(f'    Deleted {n} users (kept superusers)')

        # Wipe simple_history audit rows so we start clean.
        try:
            for model in apps.get_models():
                if model._meta.model_name.startswith('historical'):
                    n = model.objects.all().count()
                    if n:
                        model.objects.all().delete()
                        self.stdout.write(f'    Deleted {n} {model._meta.model_name} records')
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _tsv_path(name):
        return Path(settings.BASE_DIR) / 'data' / name

    def _read_tsv_row(self, filename, key_field, key_value):
        """Return one row from a TSV by exact match on key_field=key_value.
        Errors loudly if the TSV is missing or the row isn't found —
        livetest data must come from the real reference TSVs."""
        path = self._tsv_path(filename)
        if not path.exists():
            raise CommandError(f'TSV not found: {path}')
        with open(path, 'r', encoding='utf-8', newline='') as f:
            for row in csv.DictReader(f, delimiter='\t'):
                if (row.get(key_field) or '').strip() == key_value:
                    return {k: ((v or '').strip()) for k, v in row.items()}
        raise CommandError(
            f'{filename}: no row found with {key_field}={key_value!r}'
        )

    @staticmethod
    def _parse_bool(value):
        return (value or '').strip().upper() in ('TRUE', '1', 'YES')

    # ------------------------------------------------------------------
    # Step 1 — Organizations
    # ------------------------------------------------------------------
    def create_organizations(self):
        from core.models import Organization
        from core.management.commands.populate_redib_organizations import (
            ORG_TYPE_LABEL_MAP,
        )

        orgs = {}

        # Two real orgs, copied verbatim from data/organizations.tsv so
        # metadata stays in sync with the source of truth.
        for name in (HOST_ORG_NAME, REDIB_ORG_NAME):
            row = self._read_tsv_row('organizations.tsv', 'name', name)
            type_label = row['organization_type']
            if type_label not in ORG_TYPE_LABEL_MAP:
                raise CommandError(
                    f'organizations.tsv row for "{name}" has unknown type '
                    f'{type_label!r}'
                )
            org, _ = Organization.objects.update_or_create(
                name=name,
                defaults={
                    'short_name': row.get('short_name', ''),
                    'vat': row.get('vat', ''),
                    'iso2': (row.get('ISO2') or '').upper(),
                    'country': row.get('country', ''),
                    'organization_type': ORG_TYPE_LABEL_MAP[type_label],
                    'address': row.get('address', ''),
                    'city': row.get('city', ''),
                    'zip': row.get('zip', ''),
                },
            )
            orgs[name] = org
            self.stdout.write(f'    Real:    {name}')

        # Two made-up orgs — useful so the org dropdown isn't single-option,
        # and so a tester can exercise the org-picker UI. The "(livetest)"
        # suffix marks them as test-only data.
        for fake in (
            {
                'name': 'Test Hospital Alpha (livetest)',
                'short_name': 'THA',
                'vat': 'ESTEST00001',
                'iso2': 'ES',
                'country': 'Spain',
                'organization_type': 'pro',
                'address': 'Calle Pruebas 1',
                'city': 'Madrid',
                'zip': '28001',
            },
            {
                'name': 'Test University Beta (livetest)',
                'short_name': 'TUB',
                'vat': 'ESTEST00002',
                'iso2': 'ES',
                'country': 'Spain',
                'organization_type': 'hei',
                'address': 'Avenida Pruebas 2',
                'city': 'Barcelona',
                'zip': '08001',
            },
        ):
            org, _ = Organization.objects.update_or_create(
                name=fake['name'], defaults=fake,
            )
            orgs[fake['name']] = org
            self.stdout.write(f'    Made-up: {fake["name"]}')

        return orgs

    # ------------------------------------------------------------------
    # Step 2 — Node (CIC biomaGUNE)
    # ------------------------------------------------------------------
    def create_node(self, host_org):
        from core.models import Node

        row = self._read_tsv_row('nodes.tsv', 'code', NODE_CODE)
        node, _ = Node.objects.update_or_create(
            code=row['code'],
            defaults={
                'organization': host_org,
                'location': row.get('location', ''),
                'description': row.get('description', ''),
                'acknowledgment_text': row.get('acknowledgment_text', ''),
                'contact_email': row.get('contact_email', ''),
                'contact_phone': row.get('contact_phone', ''),
                'is_active': self._parse_bool(row.get('is_active')),
            },
        )
        return node

    # ------------------------------------------------------------------
    # Step 3 — Equipment for that node
    # ------------------------------------------------------------------
    def create_equipment(self, node):
        from core.models import Equipment

        valid_categories = {c for c, _ in Equipment.EQUIPMENT_CATEGORIES}
        valid_areas = {a for a, _ in Equipment.AREAS}

        path = self._tsv_path('equipment.tsv')
        if not path.exists():
            raise CommandError(f'TSV not found: {path}')

        count = 0
        with open(path, 'r', encoding='utf-8', newline='') as f:
            for row_num, row in enumerate(csv.DictReader(f, delimiter='\t'), start=2):
                if (row.get('node_code') or '').strip() != node.code:
                    continue
                category = (row.get('category') or '').strip()
                if category not in valid_categories:
                    raise CommandError(
                        f'equipment.tsv row {row_num}: invalid category {category!r}'
                    )
                area = (row.get('area') or '').strip()
                if area and area not in valid_areas:
                    raise CommandError(
                        f'equipment.tsv row {row_num}: invalid area {area!r}'
                    )
                Equipment.objects.update_or_create(
                    node=node,
                    name=(row.get('name') or '').strip(),
                    defaults={
                        'category': category,
                        'description': (row.get('description') or '').strip(),
                        'area': area,
                        'is_essential': self._parse_bool(row.get('is_essential')),
                        'is_active': self._parse_bool(row.get('is_active')),
                    },
                )
                count += 1
        if count == 0:
            raise CommandError(
                f'equipment.tsv has no rows for node {node.code!r}.'
            )
        return count

    # ------------------------------------------------------------------
    # Step 4 — Users (3) + roles
    # ------------------------------------------------------------------
    def create_users(self, orgs, node):
        from core.models import UserRole
        from allauth.account.models import EmailAddress

        # rtasseff and coordinator both have empty `phone` in users.tsv, but
        # the profile-completion middleware requires it for non-superusers.
        # Provide a placeholder for testing — override via admin/profile UI.
        FALLBACK_PHONE = '+34 900 000 000'

        rt = self._read_tsv_row('users.tsv', 'email', RTASSEFF_EMAIL)
        co = self._read_tsv_row('users.tsv', 'email', COORDINATOR_EMAIL)

        user_specs = [
            {
                # rtasseff — node coordinator for CIC-biomaGUNE
                'email': rt['email'],
                'first_name': rt['first_name'],
                'last_name': rt['last_name'],
                'phone': rt.get('phone') or FALLBACK_PHONE,
                'position': rt.get('position') or 'Node Coordinator',
                'orcid': rt.get('orcid', ''),
                'organization': orgs[HOST_ORG_NAME],
                'is_staff': True,
                'is_active': True,
                'auto_data_consent': True,
                'role': ('node_coordinator', node, ''),
            },
            {
                # ReDIB coordinator
                'email': co['email'],
                'first_name': co['first_name'],
                'last_name': co['last_name'],
                'phone': co.get('phone') or FALLBACK_PHONE,
                'position': co.get('position') or 'ReDIB Coordinator',
                'orcid': co.get('orcid', ''),
                'organization': orgs[REDIB_ORG_NAME],
                'is_staff': True,
                'is_active': True,
                'auto_data_consent': True,
                'role': ('coordinator', None, ''),
            },
            {
                # Made-up evaluator on the ReDIB info inbox.
                'email': EVALUATOR_EMAIL,
                'first_name': 'ReDIB',
                'last_name': 'Info Evaluator',
                'phone': '+34 900 000 001',
                'position': 'Preclinical Evaluator (livetest)',
                'orcid': '',
                'organization': orgs[REDIB_ORG_NAME],
                'is_staff': False,
                'is_active': True,
                'auto_data_consent': True,
                'role': ('evaluator', None, 'preclinical'),
            },
        ]

        users = []
        for spec in user_specs:
            user, _ = User.objects.update_or_create(
                email=spec['email'],
                defaults={
                    'username': spec['email'],
                    'first_name': spec['first_name'],
                    'last_name': spec['last_name'],
                    'phone': spec['phone'],
                    'position': spec['position'],
                    'orcid': spec['orcid'],
                    'organization': spec['organization'],
                    'is_staff': spec['is_staff'],
                    'is_active': spec['is_active'],
                    'auto_data_consent': spec['auto_data_consent'],
                },
            )
            user.set_password(TEST_PASSWORD)
            user.save()

            # Mark email verified + primary so allauth lets the user log in
            # without a confirmation step.
            EmailAddress.objects.update_or_create(
                user=user, email=spec['email'],
                defaults={'verified': True, 'primary': True},
            )

            role_name, role_node, role_areas = spec['role']
            UserRole.objects.update_or_create(
                user=user, role=role_name, node=role_node,
                defaults={'areas': role_areas, 'is_active': True},
            )
            users.append(user)
            node_str = f' @ {role_node.code}' if role_node else ''
            area_str = f' [{role_areas}]' if role_areas else ''
            self.stdout.write(
                f'    {spec["email"]} → {role_name}{node_str}{area_str}'
            )
        return users

    # ------------------------------------------------------------------
    # Step 5 — Site config (reads SITE_DOMAIN/SITE_NAME from env)
    # ------------------------------------------------------------------
    def configure_site(self):
        import os
        from django.contrib.sites.models import Site
        site = Site.objects.get(id=1)
        site.domain = os.environ.get('SITE_DOMAIN', 'portal.redib.net')
        site.name = os.environ.get('SITE_NAME', 'ReDIB COA Portal')
        site.save()
        Site.objects.clear_cache()
        self.stdout.write(f'    Site: {site.name} ({site.domain})')

    # ------------------------------------------------------------------
    def print_summary(self, orgs, node, equip_count, users):
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('LIVETEST SMALL SANDBOX READY'))
        self.stdout.write('=' * 70)
        self.stdout.write('')
        self.stdout.write('Reference data:')
        self.stdout.write(f'  Organizations:    {len(orgs)} (2 real + 2 made-up)')
        self.stdout.write(f'  Nodes:            1  ({node.code})')
        self.stdout.write(f'  Equipment items:  {equip_count}')
        self.stdout.write(f'  Calls / apps:     0 / 0  (intentionally empty)')
        self.stdout.write('')
        self.stdout.write(f'Test users (password = {TEST_PASSWORD!r}, emails pre-verified):')
        for u in users:
            roles = ', '.join(
                f'{r.role}{f"@{r.node.code}" if r.node else ""}'
                f'{f" [{r.areas}]" if r.areas else ""}'
                for r in u.roles.filter(is_active=True)
            )
            self.stdout.write(f'  {u.email:32s} → {roles}')
        self.stdout.write('')
        self.stdout.write('=' * 70 + '\n')
