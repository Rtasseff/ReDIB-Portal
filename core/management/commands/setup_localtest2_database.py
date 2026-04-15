"""
Django management command to set up Local Test 2 database scenario.

This creates a complete test environment for manual testing with:
- 3 nodes: CIC biomaGUNE, BioImaC, CNIC
- 2 equipment items per node (6 total)
- 2 organizations
- 6 funding agencies (with origin_of_funds)
- 10 users: 1 coordinator, 3 node coordinators, 3 evaluators, 3 applicants
- 2 calls: 1 resolved (past), 1 open (current)
- 3 sample applications at different workflow states
- Email templates

All passwords are set to 'testpass123' and emails are pre-verified.
Applicant3 (Carmen Jimenez) is left with an incomplete profile for testing.

Does NOT depend on any TSV data files.

Usage:
    python manage.py setup_localtest2_database              # Setup (fails if data exists)
    python manage.py setup_localtest2_database --reset      # Full reset and setup
    python manage.py setup_localtest2_database --reset --yes  # Skip confirmation
"""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

User = get_user_model()

TEST_PASSWORD = 'testpass123'


class Command(BaseCommand):
    help = 'Set up Local Test 2 database: full manual testing environment (no TSV dependency)'

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
        self.stdout.write(self.style.SUCCESS('ReDIB Portal - Local Test 2 Database Setup'))
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
            self.stdout.write('Step 1: Creating nodes...')
            nodes = self.create_nodes()
            self.stdout.write(self.style.SUCCESS(f'  Created {len(nodes)} nodes'))

            self.stdout.write('Step 2: Creating equipment...')
            equipment_count = self.create_equipment(nodes)
            self.stdout.write(self.style.SUCCESS(f'  Created {equipment_count} equipment items'))

            self.stdout.write('Step 3: Creating organizations...')
            orgs = self.create_organizations()
            self.stdout.write(self.style.SUCCESS(f'  Created {len(orgs)} organizations'))

            self.stdout.write('Step 4: Creating users...')
            users = self.create_users(nodes, orgs)
            self.stdout.write(self.style.SUCCESS(f'  Created {len(users)} users'))

            self.stdout.write('Step 5: Configuring site...')
            self.configure_site()
            self.stdout.write(self.style.SUCCESS('  Site configured'))

            self.stdout.write('Step 6: Seeding email templates...')
            try:
                from django.core.management import call_command
                call_command('seed_email_templates', verbosity=0)
                self.stdout.write(self.style.SUCCESS('  Email templates created'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  Email templates may already exist: {e}'))

            self.stdout.write('Step 7: Creating funding agencies...')
            agencies = self.create_funding_agencies()
            self.stdout.write(self.style.SUCCESS(f'  Created {len(agencies)} funding agencies'))

            self.stdout.write('Step 8: Creating calls...')
            calls = self.create_calls(nodes)
            self.stdout.write(self.style.SUCCESS(f'  Created {len(calls)} calls'))

            self.stdout.write('Step 9: Creating sample applications...')
            apps = self.create_sample_applications(users, calls, nodes, agencies)
            self.stdout.write(self.style.SUCCESS(f'  Created {len(apps)} applications'))

        self.print_summary(users, calls, apps)

    def reset_database(self):
        """Clear all data from the database except superusers."""
        from django.apps import apps
        from access.models import Publication, AccessGrant
        from evaluations.models import Evaluation
        from applications.models import (
            FeasibilityReview, RequestedAccess, Application, NodeResolution,
            FundingAgency,
        )
        from calls.models import CallEquipmentAllocation, Call
        from core.models import Equipment, Node, Organization, UserRole
        from communications.models import EmailLog, EmailTemplate, NotificationPreference
        from allauth.account.models import EmailAddress

        self.stdout.write('  Clearing data in dependency order...')

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
                self.stdout.write(f'    Deleted {count} {name}')

        # Only delete EmailAddress records for non-superuser accounts so the
        # superuser's allauth verification state survives a reset.
        non_super_emails = EmailAddress.objects.filter(user__is_superuser=False)
        count = non_super_emails.count()
        if count:
            non_super_emails.delete()
            self.stdout.write(f'    Deleted {count} email addresses (kept superuser)')

        count = User.objects.filter(is_superuser=False).count()
        if count:
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(f'    Deleted {count} users (kept superusers)')

        try:
            for model in apps.get_models():
                if model._meta.model_name.startswith('historical'):
                    count = model.objects.all().count()
                    if count:
                        model.objects.all().delete()
                        self.stdout.write(f'    Deleted {count} {model._meta.model_name} records')
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Step 1: Nodes
    # -------------------------------------------------------------------------
    def create_nodes(self):
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
            node, created = Node.objects.get_or_create(code=data['code'], defaults=data)
            nodes.append(node)
            status = 'Created' if created else 'Exists'
            self.stdout.write(f'    {status}: {node.name} ({node.code})')
        return nodes

    # -------------------------------------------------------------------------
    # Step 2: Equipment
    # -------------------------------------------------------------------------
    def create_equipment(self, nodes):
        from core.models import Equipment

        equipment_data = {
            'CICBIO': [
                {'name': 'MRI 3T Scanner', 'category': 'mri', 'description': '3 Tesla MRI for preclinical imaging'},
                {'name': 'PET-CT Scanner', 'category': 'pet_ct', 'description': 'Combined PET-CT for molecular imaging'},
            ],
            'BIOIMAC': [
                {'name': 'MRI 7T Scanner', 'category': 'mri', 'description': '7 Tesla ultra-high field MRI'},
                {'name': 'Optical Imaging System', 'category': 'optical', 'description': 'Fluorescence and bioluminescence imaging'},
            ],
            'CNIC': [
                {'name': 'Cardiac MRI', 'category': 'mri', 'description': 'Specialized cardiac MRI system'},
                {'name': 'Micro-CT Scanner', 'category': 'ct', 'description': 'High-resolution micro-CT for small animals'},
            ],
        }

        count = 0
        for node in nodes:
            for item in equipment_data.get(node.code, []):
                equip, created = Equipment.objects.get_or_create(
                    name=item['name'], node=node,
                    defaults={
                        'category': item.get('category', 'other'),
                        'description': item['description'],
                        'is_active': True,
                    }
                )
                count += 1 if created else 0
                status = 'Created' if created else 'Exists'
                self.stdout.write(f'    {status}: {equip.name} @ {node.code}')
        return count

    # -------------------------------------------------------------------------
    # Step 3: Organizations
    # -------------------------------------------------------------------------
    def configure_site(self):
        """Set the Django Site object. Reads SITE_DOMAIN/SITE_NAME from env so
        dev environments can point at localhost while production uses
        portal.redib.net."""
        import os
        from django.contrib.sites.models import Site
        site = Site.objects.get(id=1)
        site.domain = os.environ.get('SITE_DOMAIN', 'portal.redib.net')
        site.name = os.environ.get('SITE_NAME', 'ReDIB COA Portal')
        site.save()
        self.stdout.write(f'    Site: {site.name} ({site.domain})')

    # -------------------------------------------------------------------------
    def create_organizations(self):
        from core.models import Organization

        orgs_data = [
            {
                'name': 'Universidad de Barcelona',
                'organization_type': 'university',
                'country': 'Spain',
            },
            {
                'name': 'Instituto de Investigacion Sanitaria',
                'organization_type': 'other',
                'country': 'Spain',
            },
        ]

        orgs = []
        for data in orgs_data:
            org, created = Organization.objects.get_or_create(
                name=data['name'], defaults=data
            )
            orgs.append(org)
            status = 'Created' if created else 'Exists'
            self.stdout.write(f'    {status}: {org.name}')
        return orgs

    # -------------------------------------------------------------------------
    # Step 4: Users
    # -------------------------------------------------------------------------
    def create_users(self, nodes, orgs):
        from core.models import UserRole
        from allauth.account.models import EmailAddress

        uni = orgs[0]   # Universidad de Barcelona
        inst = orgs[1]  # Instituto de Investigacion Sanitaria

        users_data = [
            # ReDIB Coordinator
            {
                'email': 'coordinator@test.redib.net',
                'first_name': 'Carlos',
                'last_name': 'Martinez',
                'position': 'ReDIB Coordinator',
                'phone': '+34 900 000 001',
                'organization': inst,
                'role': 'coordinator',
                'node_code': None,
                'area': '',
            },
            # Node Coordinators
            {
                'email': 'nc.cicbio@test.redib.net',
                'first_name': 'Elena',
                'last_name': 'Fernandez',
                'position': 'Node Coordinator',
                'phone': '+34 900 000 002',
                'organization': inst,
                'role': 'node_coordinator',
                'node_code': 'CICBIO',
                'area': '',
            },
            {
                'email': 'nc.bioimac@test.redib.net',
                'first_name': 'Miguel',
                'last_name': 'Santos',
                'position': 'Node Coordinator',
                'phone': '+34 900 000 003',
                'organization': inst,
                'role': 'node_coordinator',
                'node_code': 'BIOIMAC',
                'area': '',
            },
            {
                'email': 'nc.cnic@test.redib.net',
                'first_name': 'Isabel',
                'last_name': 'Lopez',
                'position': 'Node Coordinator',
                'phone': '+34 900 000 004',
                'organization': inst,
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
                'phone': '+34 900 000 005',
                'organization': inst,
                'role': 'evaluator',
                'node_code': None,
                'area': 'preclinical',
            },
            {
                'email': 'eval.clinical@test.redib.net',
                'first_name': 'Pedro',
                'last_name': 'Gonzalez',
                'position': 'Clinical Professor',
                'phone': '+34 900 000 006',
                'organization': inst,
                'role': 'evaluator',
                'node_code': None,
                'area': 'clinical',
            },
            {
                'email': 'eval.radiochemistry@test.redib.net',
                'first_name': 'Laura',
                'last_name': 'Navarro',
                'position': 'Radiochemist',
                'phone': '+34 900 000 007',
                'organization': inst,
                'role': 'evaluator',
                'node_code': None,
                'area': 'radiochemistry',
            },
            # Applicant 1 - complete profile
            {
                'email': 'applicant1@test.redib.net',
                'first_name': 'Sofia',
                'last_name': 'Ruiz',
                'position': 'PhD Student',
                'phone': '+34 900 000 008',
                'organization': uni,
                'auto_data_consent': True,
                'role': 'applicant',
                'node_code': None,
                'area': '',
            },
            # Applicant 2 - complete profile
            {
                'email': 'applicant2@test.redib.net',
                'first_name': 'Diego',
                'last_name': 'Moreno',
                'position': 'Postdoctoral Researcher',
                'phone': '+34 900 000 009',
                'organization': uni,
                'auto_data_consent': True,
                'role': 'applicant',
                'node_code': None,
                'area': '',
            },
            # Applicant 3 - INCOMPLETE profile (no phone, no org) for Scenario 1 testing
            {
                'email': 'applicant3@test.redib.net',
                'first_name': '',
                'last_name': '',
                'position': '',
                'phone': '',
                'organization': None,
                'role': 'applicant',
                'node_code': None,
                'area': '',
            },
        ]

        node_lookup = {n.code: n for n in nodes}
        users_created = []

        for data in users_data:
            user, created = User.objects.get_or_create(
                email=data['email'],
                defaults={
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'position': data.get('position', ''),
                    'phone': data.get('phone', ''),
                    'organization': data.get('organization'),
                    'auto_data_consent': data.get('auto_data_consent', False),
                    'is_active': True,
                }
            )

            if created:
                user.set_password(TEST_PASSWORD)
                user.save()
                EmailAddress.objects.create(
                    user=user, email=user.email, verified=True, primary=True
                )
                self.stdout.write(f'    Created: {user.email} ({data["role"]})')
            else:
                user.set_password(TEST_PASSWORD)
                user.save()
                email_addr, _ = EmailAddress.objects.get_or_create(
                    user=user, email=user.email,
                    defaults={'verified': True, 'primary': True}
                )
                if not email_addr.verified:
                    email_addr.verified = True
                    email_addr.primary = True
                    email_addr.save()
                self.stdout.write(f'    Exists (password reset): {user.email} ({data["role"]})')

            role_kwargs = {'user': user, 'role': data['role']}
            if data['node_code']:
                role_kwargs['node'] = node_lookup[data['node_code']]

            role, _ = UserRole.objects.get_or_create(
                **role_kwargs,
                defaults={'is_active': True, 'areas': data.get('area') or ''}
            )
            if data.get('area') and not role.areas:
                role.areas = data['area']
                role.save()

            users_created.append({
                'user': user,
                'role': data['role'],
                'node_code': data.get('node_code'),
                'area': data.get('area'),
            })

        return users_created

    # -------------------------------------------------------------------------
    # Step 6: Funding Agencies
    # -------------------------------------------------------------------------
    def create_funding_agencies(self):
        from applications.models import FundingAgency

        agencies_data = [
            ('Agencia Estatal de Investigacion (AEI)', 'spanish_government'),
            ('Instituto de Salud Carlos III (ISCIII)', 'spanish_government'),
            ('Ministerio de Ciencia, Innovacion y Universidades (MICIU)', 'spanish_government'),
            ('European Research Council (ERC)', 'european_union'),
            ('European Commission - Horizon Europe', 'european_union'),
            ('National Institutes of Health (NIH)', 'international_non_eu'),
            ('Fundacion La Caixa', 'private'),
        ]

        agencies = []
        for name, origin in agencies_data:
            agency, created = FundingAgency.objects.get_or_create(
                name=name, defaults={'origin_of_funds': origin}
            )
            agencies.append(agency)
            status = 'Created' if created else 'Exists'
            self.stdout.write(f'    {status}: {name} ({origin})')
        return agencies

    # -------------------------------------------------------------------------
    # Step 7: Calls
    # -------------------------------------------------------------------------
    def create_calls(self, nodes):
        from calls.models import Call, CallEquipmentAllocation
        from core.models import Equipment

        now = timezone.now()

        def end_of_day(dt):
            date_only = dt.date()
            dt_with_time = datetime.combine(date_only, time(23, 59, 59))
            return timezone.make_aware(dt_with_time) if timezone.is_naive(dt_with_time) else dt_with_time

        calls = {}

        # Resolved call (past) — for evaluated/completed applications
        calls['resolved'], created = Call.objects.get_or_create(
            code='COA-TEST-01',
            defaults={
                'title': 'Test Call 01 (Resolved)',
                'status': 'resolved',
                'submission_start': end_of_day(now - timedelta(days=90)),
                'submission_end': end_of_day(now - timedelta(days=60)),
                'evaluation_deadline': end_of_day(now - timedelta(days=45)),
                'execution_start': end_of_day(now - timedelta(days=30)),
                'execution_end': end_of_day(now + timedelta(days=30)),
                'description': 'A resolved test call for viewing past workflow data.',
                'published_at': now - timedelta(days=90),
            }
        )
        if created:
            self.stdout.write(f'    Created: COA-TEST-01 (resolved)')

        # Open call (current) — for new applications
        calls['open'], created = Call.objects.get_or_create(
            code='COA-TEST-02',
            defaults={
                'title': 'Test Call 02 (Open for Applications)',
                'status': 'open',
                'submission_start': end_of_day(now - timedelta(days=7)),
                'submission_end': end_of_day(now + timedelta(days=38)),
                'evaluation_deadline': end_of_day(now + timedelta(days=53)),
                'execution_start': end_of_day(now + timedelta(days=60)),
                'execution_end': end_of_day(now + timedelta(days=120)),
                'description': 'An open test call for submitting new applications.',
                'published_at': now - timedelta(days=7),
            }
        )
        if created:
            self.stdout.write(f'    Created: COA-TEST-02 (open)')

        # Allocate all equipment to both calls
        all_equipment = Equipment.objects.filter(node__in=nodes)
        for call in calls.values():
            for equip in all_equipment:
                CallEquipmentAllocation.objects.get_or_create(
                    call=call, equipment=equip
                )

        return calls

    # -------------------------------------------------------------------------
    # Step 8: Sample Applications
    # -------------------------------------------------------------------------
    def create_sample_applications(self, users, calls, nodes, agencies):
        from applications.models import Application, RequestedAccess, FeasibilityReview
        from evaluations.models import Evaluation
        from core.models import Equipment

        now = timezone.now()
        user_lookup = {u['user'].email: u['user'] for u in users}
        node_lookup = {n.code: n for n in nodes}

        applicant1 = user_lookup['applicant1@test.redib.net']
        applicant2 = user_lookup['applicant2@test.redib.net']
        eval1 = user_lookup['eval.preclinical@test.redib.net']
        eval2 = user_lookup['eval.clinical@test.redib.net']
        nc_cicbio = user_lookup['nc.cicbio@test.redib.net']
        nc_cnic = user_lookup['nc.cnic@test.redib.net']
        aei = agencies[0]  # Agencia Estatal de Investigacion (AEI)

        apps = {}

        # APP-TEST-001: Under feasibility review (Scenario 3)
        apps['feasibility'], created = Application.objects.get_or_create(
            code='APP-TEST-001',
            defaults={
                'call': calls['open'],
                'applicant': applicant1,
                'status': 'under_feasibility_review',
                'project_name': 'Preclinical MRI Study of Neurodegeneration',
                'brief_description': 'MRI study of neurodegeneration biomarkers',
                'applicant_name': f'{applicant1.first_name} {applicant1.last_name}',
                'applicant_entity': applicant1.organization.name if applicant1.organization else '',
                'applicant_email': applicant1.email,
                'applicant_phone': applicant1.phone,
                'project_title': 'Advanced MRI Biomarkers for Neurodegeneration',
                'project_code': 'PID2026-TEST-001',
                'funding_agency_obj': aei,
                'project_type': 'spanish_government',
                'has_competitive_funding': True,
                'subject_area': 'bme',
                'service_modality': 'full_assistance',
                'specialization_area': 'preclinical',
                'scientific_relevance': 'High relevance for understanding neurodegeneration mechanisms using advanced MRI.',
                'methodology_description': 'Standard MRI protocols with advanced diffusion and perfusion sequences.',
                'expected_contributions': 'Novel biomarker identification for early neurodegeneration detection.',
                'impact_strengths': 'Strong potential for publication in top neuroscience journals.',
                'socioeconomic_significance': 'Contributes to improved early diagnostic methods.',
                'opportunity_criteria': 'Timely research addressing current gaps in neurodegeneration imaging.',
                'technical_feasibility_confirmed': True,
                'data_consent': True,
                'submitted_at': now - timedelta(days=3),
            }
        )
        if created:
            # Request equipment from CICBIO
            cicbio_equip = Equipment.objects.filter(node=node_lookup['CICBIO'])
            for equip in cicbio_equip:
                RequestedAccess.objects.get_or_create(
                    application=apps['feasibility'], equipment=equip,
                    defaults={'hours_requested': Decimal('16')}
                )
            # Create pending feasibility review for the node
            FeasibilityReview.objects.get_or_create(
                application=apps['feasibility'], node=node_lookup['CICBIO'],
                defaults={'reviewer': nc_cicbio, 'is_feasible': None}
            )
            self.stdout.write(f'    Created: APP-TEST-001 (under_feasibility_review)')

        # APP-TEST-002: Draft (Scenarios 4, 5 — cancel, back nav)
        apps['draft'], created = Application.objects.get_or_create(
            code='APP-TEST-002',
            defaults={
                'call': calls['open'],
                'applicant': applicant2,
                'status': 'draft',
                'project_name': 'PET Imaging for Cardiac Function',
                'brief_description': 'PET imaging study of cardiac metabolism',
                'applicant_name': f'{applicant2.first_name} {applicant2.last_name}',
                'applicant_entity': applicant2.organization.name if applicant2.organization else '',
                'applicant_email': applicant2.email,
                'applicant_phone': applicant2.phone,
                'subject_area': 'bme',
                'service_modality': 'presential',
                'specialization_area': 'clinical',
            }
        )
        if created:
            # Request equipment from CNIC
            cnic_equip = Equipment.objects.filter(node=node_lookup['CNIC'])
            for equip in cnic_equip:
                RequestedAccess.objects.get_or_create(
                    application=apps['draft'], equipment=equip,
                    defaults={'hours_requested': Decimal('24')}
                )
            self.stdout.write(f'    Created: APP-TEST-002 (draft)')

        # APP-TEST-003: Evaluated on resolved call (test resolution views)
        apps['evaluated'], created = Application.objects.get_or_create(
            code='APP-TEST-003',
            defaults={
                'call': calls['resolved'],
                'applicant': applicant1,
                'status': 'evaluated',
                'project_name': 'Multi-Modal Imaging of Cardiovascular Disease',
                'brief_description': 'Combined MRI/PET cardiovascular imaging study',
                'applicant_name': f'{applicant1.first_name} {applicant1.last_name}',
                'applicant_entity': applicant1.organization.name if applicant1.organization else '',
                'applicant_email': applicant1.email,
                'applicant_phone': applicant1.phone,
                'project_title': 'Multi-Modal Cardiovascular Imaging',
                'project_code': 'PID2026-TEST-003',
                'funding_agency_obj': aei,
                'project_type': 'spanish_government',
                'has_competitive_funding': True,
                'subject_area': 'bme',
                'service_modality': 'full_assistance',
                'specialization_area': 'clinical',
                'scientific_relevance': 'Important cardiovascular imaging research.',
                'methodology_description': 'Combined MRI and PET protocols for cardiac assessment.',
                'expected_contributions': 'Improved cardiac imaging workflow.',
                'impact_strengths': 'High clinical impact potential.',
                'socioeconomic_significance': 'Advances cardiovascular diagnostics.',
                'opportunity_criteria': 'Addresses critical gap in multi-modal cardiac imaging.',
                'technical_feasibility_confirmed': True,
                'data_consent': True,
                'submitted_at': now - timedelta(days=70),
                'final_score': Decimal('9.5'),
            }
        )
        if created:
            # Request equipment from CNIC and CICBIO (multi-node)
            for node_code in ['CNIC', 'CICBIO']:
                node_equip = Equipment.objects.filter(node=node_lookup[node_code])
                for equip in node_equip:
                    RequestedAccess.objects.get_or_create(
                        application=apps['evaluated'], equipment=equip,
                        defaults={'hours_requested': Decimal('16')}
                    )

            # Feasibility reviews (all feasible)
            nc_for_node = {'CNIC': nc_cnic, 'CICBIO': nc_cicbio}
            for node_code in ['CNIC', 'CICBIO']:
                FeasibilityReview.objects.get_or_create(
                    application=apps['evaluated'], node=node_lookup[node_code],
                    defaults={
                        'reviewer': nc_for_node[node_code],
                        'is_feasible': True,
                        'status': 'approved',
                        'reviewed_at': now - timedelta(days=60),
                        'comments': 'Equipment available, schedule confirmed.',
                    }
                )

            # Two completed evaluations
            for i, evaluator in enumerate([eval1, eval2], start=1):
                Evaluation.objects.get_or_create(
                    application=apps['evaluated'], evaluator=evaluator,
                    defaults={
                        'score_quality_originality': 2,
                        'score_methodology_design': 2 if i == 1 else 1,
                        'score_expected_contributions': 2 if i == 1 else 1,
                        'score_knowledge_advancement': 2 if i == 1 else 2,
                        'score_social_economic_impact': 1 if i == 1 else 2,
                        'score_exploitation_dissemination': 1 if i == 1 else 2,
                        'recommendation': 'approved',
                        'comments': f'Evaluation by evaluator {i}. Strong application.',
                        'completed_at': now - timedelta(days=50 - i),
                    }
                )

            self.stdout.write(f'    Created: APP-TEST-003 (evaluated, score=9.5)')

        return apps

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    def print_summary(self, users, calls, apps):
        from core.models import Node, Equipment, Organization
        from applications.models import Application, FundingAgency

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('LOCAL TEST 2 DATABASE SETUP COMPLETE'))
        self.stdout.write('=' * 70)

        self.stdout.write('\nData Summary:')
        self.stdout.write(f'  Nodes:              {Node.objects.count()}')
        self.stdout.write(f'  Equipment:          {Equipment.objects.count()}')
        self.stdout.write(f'  Organizations:      {Organization.objects.count()}')
        self.stdout.write(f'  Funding Agencies:   {FundingAgency.objects.count()}')
        self.stdout.write(f'  Users (non-super):  {User.objects.filter(is_superuser=False).count()}')
        self.stdout.write(f'  Calls:              {len(calls)}')
        self.stdout.write(f'  Applications:       {Application.objects.count()}')

        # Users table
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('USER ACCOUNTS (All passwords: testpass123)')
        self.stdout.write('=' * 70)
        self.stdout.write('')
        self.stdout.write(f'{"Email":<38} {"Name":<22} {"Role":<18} {"Node/Spec"}')
        self.stdout.write('-' * 95)

        for u in users:
            user = u['user']
            name = f"{user.first_name} {user.last_name}".strip() or '(incomplete)'
            extra = u.get('node_code') or u.get('area') or '-'
            self.stdout.write(f'{user.email:<38} {name:<22} {u["role"]:<18} {extra}')

        # Calls table
        self.stdout.write('\n' + '-' * 70)
        self.stdout.write('CALLS:')
        self.stdout.write('-' * 70)
        for key, call in calls.items():
            self.stdout.write(
                f'  {call.code} — {call.title} (status: {call.status})'
            )
            self.stdout.write(
                f'    Submission: {call.submission_start.strftime("%Y-%m-%d")} to '
                f'{call.submission_end.strftime("%Y-%m-%d")}'
            )

        # Applications table
        self.stdout.write('\n' + '-' * 70)
        self.stdout.write('APPLICATIONS:')
        self.stdout.write('-' * 70)
        for app in Application.objects.all().select_related('applicant', 'call'):
            self.stdout.write(
                f'  {app.code} — {app.status} (call: {app.call.code}, '
                f'applicant: {app.applicant.email})'
            )

        # Nodes and equipment
        self.stdout.write('\n' + '-' * 70)
        self.stdout.write('NODES AND EQUIPMENT:')
        self.stdout.write('-' * 70)
        for node in Node.objects.all():
            self.stdout.write(f'\n  {node.name} ({node.code}) - {node.location}')
            for equip in Equipment.objects.filter(node=node):
                self.stdout.write(f'    - {equip.name}')

        # Testing hints
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('TESTING NOTES:')
        self.stdout.write('  applicant3@test.redib.net has an INCOMPLETE profile')
        self.stdout.write('  (no name/phone/org) — use for Scenario 1 testing.')
        self.stdout.write('')
        self.stdout.write('  COA-TEST-02 is OPEN — use for new application testing.')
        self.stdout.write('')
        self.stdout.write('To start the development server:')
        self.stdout.write('  python manage.py runserver')
        self.stdout.write('=' * 70 + '\n')
