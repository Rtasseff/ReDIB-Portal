"""
Django management command to set up Local Test 3 database — one-shot manual-test sandbox.

Creates a self-contained environment with every workflow phase exercisable
in a single pass. No TSV dependencies; every record is created inline.

Contents:
- 3 nodes (CICbiomaGUNE = Node A, BioImaC = spare, CNIC = Node B)
- 6 equipment (2 per node)
- 2 organizations (Universidad de Barcelona, Instituto de Investigacion Sanitaria)
- 7 funding agencies
- 10 users: 1 coordinator, 2 node coordinators (A, B), 3 evaluators, 4 applicants
    * applicant4 has an incomplete profile for middleware testing
    * eval.preclinical is co-located with uni-applicants to exercise COI
- 2 calls: COA-LIVE-2026 (open, live workflow) and COA-PAST-2025 (resolved, terminal states)
- 10 LIVE-* applications spanning every live status
- 6 PAST-* applications spanning terminal + post-resolution states

All accounts use password 'testpass123' with pre-verified email addresses
so django-allauth lets them log in without a confirmation step.

Usage:
    python manage.py setup_localtest3_database              # Setup (fails if data exists)
    python manage.py setup_localtest3_database --reset      # Full reset and setup
    python manage.py setup_localtest3_database --reset --yes  # Skip confirmation
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
    help = 'Set up Local Test 3: comprehensive manual-test sandbox covering every workflow phase'

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
        self.stdout.write(self.style.SUCCESS('ReDIB Portal — Local Test 3 Sandbox Setup'))
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

            self.stdout.write('Step 9: Creating LIVE applications (open call)...')
            live_apps = self.create_live_applications(users, calls, nodes, agencies)
            self.stdout.write(self.style.SUCCESS(f'  Created {len(live_apps)} LIVE applications'))

            self.stdout.write('Step 10: Creating PAST applications (resolved call)...')
            past_apps = self.create_past_applications(users, calls, nodes, agencies)
            self.stdout.write(self.style.SUCCESS(f'  Created {len(past_apps)} PAST applications'))

        self.print_cheatsheet(users, calls, live_apps, past_apps)

    # -------------------------------------------------------------------------
    # Reset
    # -------------------------------------------------------------------------
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
                'description': 'Center for Cooperative Research in Biomaterials (Node A)',
                'contact_email': 'cicbio@test.redib.net',
            },
            {
                'code': 'BIOIMAC',
                'name': 'BioImaC',
                'location': 'Murcia, Spain',
                'description': 'Biomedical Imaging Center of Murcia (spare / unmanned in sandbox)',
                'contact_email': 'bioimac@test.redib.net',
            },
            {
                'code': 'CNIC',
                'name': 'CNIC',
                'location': 'Madrid, Spain',
                'description': 'Centro Nacional de Investigaciones Cardiovasculares (Node B)',
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
        import os
        from django.contrib.sites.models import Site
        site = Site.objects.get(id=1)
        site.domain = os.environ.get('SITE_DOMAIN', 'portal.redib.net')
        site.name = os.environ.get('SITE_NAME', 'ReDIB COA Portal')
        site.save()
        Site.objects.clear_cache()
        self.stdout.write(f'    Site: {site.name} ({site.domain})')

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

        # eval.preclinical sits at uni intentionally so LIVE-004 (applicant3
        # at uni) demonstrates the coordinator's COI filter during auto-assign.
        users_data = [
            {
                'email': 'coordinator@test.redib.net',
                'first_name': 'Carlos', 'last_name': 'Martinez',
                'position': 'ReDIB Coordinator',
                'phone': '+34 900 000 001',
                'organization': inst,
                'role': 'coordinator', 'node_code': None, 'area': '',
            },
            {
                'email': 'nc.cicbio@test.redib.net',
                'first_name': 'Elena', 'last_name': 'Fernandez',
                'position': 'Node Coordinator',
                'phone': '+34 900 000 002',
                'organization': inst,
                'role': 'node_coordinator', 'node_code': 'CICBIO', 'area': '',
            },
            {
                'email': 'nc.cnic@test.redib.net',
                'first_name': 'Isabel', 'last_name': 'Lopez',
                'position': 'Node Coordinator',
                'phone': '+34 900 000 004',
                'organization': inst,
                'role': 'node_coordinator', 'node_code': 'CNIC', 'area': '',
            },
            {
                'email': 'eval.preclinical@test.redib.net',
                'first_name': 'Ana', 'last_name': 'Rodriguez',
                'position': 'Senior Researcher',
                'phone': '+34 900 000 005',
                'organization': uni,
                'role': 'evaluator', 'node_code': None, 'area': 'preclinical',
            },
            {
                'email': 'eval.clinical@test.redib.net',
                'first_name': 'Pedro', 'last_name': 'Gonzalez',
                'position': 'Clinical Professor',
                'phone': '+34 900 000 006',
                'organization': inst,
                'role': 'evaluator', 'node_code': None, 'area': 'clinical',
            },
            {
                'email': 'eval.radio@test.redib.net',
                'first_name': 'Laura', 'last_name': 'Navarro',
                'position': 'Radiochemist',
                'phone': '+34 900 000 007',
                'organization': inst,
                'role': 'evaluator', 'node_code': None, 'area': 'radiochemistry;clinical',
            },
            {
                'email': 'applicant1@test.redib.net',
                'first_name': 'Sofia', 'last_name': 'Ruiz',
                'position': 'PhD Student',
                'phone': '+34 900 000 008',
                'organization': uni,
                'auto_data_consent': True,
                'role': 'applicant', 'node_code': None, 'area': '',
            },
            {
                'email': 'applicant2@test.redib.net',
                'first_name': 'Diego', 'last_name': 'Moreno',
                'position': 'Postdoctoral Researcher',
                'phone': '+34 900 000 009',
                'organization': inst,
                'auto_data_consent': True,
                'role': 'applicant', 'node_code': None, 'area': '',
            },
            {
                'email': 'applicant3@test.redib.net',
                'first_name': 'Marta', 'last_name': 'Serrano',
                'position': 'Research Scientist',
                'phone': '+34 900 000 010',
                'organization': uni,
                'auto_data_consent': True,
                'role': 'applicant', 'node_code': None, 'area': '',
            },
            # Applicant 4 — incomplete profile (no phone/org) on purpose
            {
                'email': 'applicant4@test.redib.net',
                'first_name': '', 'last_name': '',
                'position': '', 'phone': '',
                'organization': None,
                'role': 'applicant', 'node_code': None, 'area': '',
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

            user.set_password(TEST_PASSWORD)
            user.save()

            EmailAddress.objects.update_or_create(
                user=user, email=user.email,
                defaults={'verified': True, 'primary': True}
            )

            status = 'Created' if created else 'Exists (password reset)'
            self.stdout.write(f'    {status}: {user.email} ({data["role"]})')

            role_kwargs = {'user': user, 'role': data['role']}
            if data['node_code']:
                role_kwargs['node'] = node_lookup[data['node_code']]

            role, _ = UserRole.objects.get_or_create(
                **role_kwargs,
                defaults={'is_active': True, 'areas': data.get('area') or ''}
            )
            if data.get('area') and role.areas != data['area']:
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

        calls['resolved'], created = Call.objects.get_or_create(
            code='COA-PAST-2025',
            defaults={
                'title': 'ReDIB COA 2025 (Resolved)',
                'status': 'resolved',
                'submission_start': end_of_day(now - timedelta(days=120)),
                'submission_end': end_of_day(now - timedelta(days=90)),
                'evaluation_deadline': end_of_day(now - timedelta(days=60)),
                'execution_start': end_of_day(now - timedelta(days=45)),
                'execution_end': end_of_day(now + timedelta(days=30)),
                'description': 'Previous call: terminal states + active access tracking + completed access.',
                'published_at': now - timedelta(days=120),
            }
        )
        if created:
            self.stdout.write(f'    Created: COA-PAST-2025 (resolved)')

        calls['open'], created = Call.objects.get_or_create(
            code='COA-LIVE-2026',
            defaults={
                'title': 'ReDIB COA 2026 (Open for Applications)',
                'status': 'open',
                'submission_start': end_of_day(now - timedelta(days=7)),
                'submission_end': end_of_day(now + timedelta(days=30)),
                'evaluation_deadline': end_of_day(now + timedelta(days=45)),
                'execution_start': end_of_day(now + timedelta(days=60)),
                'execution_end': end_of_day(now + timedelta(days=150)),
                'description': 'Current call: applications in every live workflow stage.',
                'published_at': now - timedelta(days=7),
            }
        )
        if created:
            self.stdout.write(f'    Created: COA-LIVE-2026 (open)')

        all_equipment = Equipment.objects.filter(node__in=nodes)
        for call in calls.values():
            for equip in all_equipment:
                CallEquipmentAllocation.objects.get_or_create(
                    call=call, equipment=equip
                )

        return calls

    # -------------------------------------------------------------------------
    # Application helpers
    # -------------------------------------------------------------------------
    def _base_application_fields(self, applicant, project_name, spec_area, agency,
                                  submitted_offset_days=-7):
        """Return the field dict shared by all seeded applications.

        Invariant enforced here: an application has a `funding_agency_obj`
        IF AND ONLY IF `has_competitive_funding=True`. Pass ``agency=None`` to
        seed a non-competitive application (no agency, project_type defaults
        to institutional, project_code blank).
        """
        now = timezone.now()
        applicant_entity = applicant.organization.name if applicant.organization else 'Test Organization'
        applicant_phone = applicant.phone or '+34 900 000 000'
        is_competitive = agency is not None
        return {
            'project_name': project_name,
            'brief_description': f'{spec_area.capitalize()} imaging study',
            'applicant_name': f'{applicant.first_name} {applicant.last_name}'.strip() or applicant.email,
            'applicant_entity': applicant_entity,
            'applicant_email': applicant.email,
            'applicant_phone': applicant_phone,
            'project_code': f'PID2026-TEST-{project_name[:4].upper()}' if is_competitive else '',
            'funding_agency_obj': agency,
            'project_type': agency.origin_of_funds if is_competitive else 'institutional',
            'has_competitive_funding': is_competitive,
            'subject_area': 'bme',
            'service_modality': 'full_assistance',
            'specialization_area': spec_area,
            'scientific_relevance': (
                f'This {spec_area} study addresses current gaps in biomedical imaging '
                f'through a novel, high-impact research program.'
            ),
            'methodology_description': (
                f'Standard {spec_area} imaging protocols combined with advanced acquisition '
                f'sequences and rigorous statistical analysis plan.'
            ),
            'expected_contributions': (
                'Novel biomarker characterisation, improved diagnostic precision, and open '
                'publication of protocols for community use.'
            ),
            'impact_strengths': (
                'Strong potential for high-impact publications, collaborative partnerships, '
                'and translation into clinical practice.'
            ),
            'socioeconomic_significance': (
                'Supports improved early-diagnostic methods and long-term cost savings '
                'for the health system.'
            ),
            'opportunity_criteria': (
                'Timely research addressing gaps identified in recent literature and '
                'aligned with ReDIB strategic priorities.'
            ),
            'technical_feasibility_confirmed': True,
            'data_consent': True,
            'submitted_at': now + timedelta(days=submitted_offset_days),
        }

    def _add_requested_access(self, app, equipment_list, hours=Decimal('24'),
                               hours_approved=None, is_completed=False,
                               actual_hours=None, completed_by=None, completed_at=None):
        from applications.models import RequestedAccess
        for equip in equipment_list:
            RequestedAccess.objects.create(
                application=app, equipment=equip,
                hours_requested=hours,
                hours_approved=hours_approved,
                actual_hours_used=actual_hours,
                is_completed=is_completed,
                completed_by=completed_by,
                completed_at=completed_at,
            )

    def _add_feasibility(self, app, node, reviewer, status, comments='', reviewed_offset=None):
        """Create a feasibility review in the requested state."""
        from applications.models import FeasibilityReview
        now = timezone.now()
        is_feasible = {
            'pending': None,
            'approved': True,
            'rejected': False,
            'edits_requested': None,
        }.get(status)
        reviewed_at = (now + timedelta(days=reviewed_offset)) if reviewed_offset is not None else None
        FeasibilityReview.objects.create(
            application=app,
            node=node,
            reviewer=reviewer,
            is_feasible=is_feasible,
            status=status,
            comments=comments,
            reviewed_at=reviewed_at,
        )

    def _add_evaluation(self, app, evaluator, scores=None, comments='',
                        completed_offset=None):
        """Create one Evaluation. scores=None leaves it incomplete.

        Incomplete evaluations get empty comments so the evaluator opens a
        clean textarea; only completed seed evaluations carry a marker string.
        """
        from evaluations.models import Evaluation
        if scores is None:
            seeded_comments = comments
        else:
            seeded_comments = comments or f'Seed evaluation by {evaluator.email}'
        kwargs = {
            'application': app,
            'evaluator': evaluator,
            'comments': seeded_comments,
        }
        if scores is not None:
            assert len(scores) == 6
            kwargs.update({
                'score_quality_originality': scores[0],
                'score_methodology_design': scores[1],
                'score_expected_contributions': scores[2],
                'score_knowledge_advancement': scores[3],
                'score_social_economic_impact': scores[4],
                'score_exploitation_dissemination': scores[5],
                'recommendation': 'approved' if sum(scores) >= 7 else 'denied',
            })
        ev = Evaluation.objects.create(**kwargs)
        if scores is not None and completed_offset is not None:
            # Override auto-set completed_at so historical evaluations don't
            # show today's timestamp.
            now = timezone.now()
            Evaluation.objects.filter(pk=ev.pk).update(
                completed_at=now + timedelta(days=completed_offset)
            )
        return ev

    def _add_node_resolution(self, app, node, reviewer, resolution,
                              approved_hours_each=None, reviewed_offset=-2):
        """Create NodeResolution and set hours_approved accordingly."""
        from applications.models import NodeResolution
        now = timezone.now()
        NodeResolution.objects.create(
            application=app, node=node, reviewer=reviewer,
            resolution=resolution,
            comments=f'Seed {resolution} decision for {node.code}',
            reviewed_at=now + timedelta(days=reviewed_offset),
        )
        for ra in app.requested_access.filter(equipment__node=node):
            if resolution == 'accept':
                ra.hours_approved = approved_hours_each or ra.hours_requested
            elif resolution == 'waitlist':
                ra.hours_approved = approved_hours_each or (ra.hours_requested / 2)
            else:
                ra.hours_approved = Decimal('0')
            ra.save()

    # -------------------------------------------------------------------------
    # Step 9: LIVE applications (open call)
    # -------------------------------------------------------------------------
    def create_live_applications(self, users, calls, nodes, agencies):
        from applications.models import Application
        from core.models import Equipment

        now = timezone.now()
        u = {u['user'].email: u['user'] for u in users}
        node_lookup = {n.code: n for n in nodes}

        applicant1 = u['applicant1@test.redib.net']  # uni
        applicant2 = u['applicant2@test.redib.net']  # inst
        applicant3 = u['applicant3@test.redib.net']  # uni
        nc_a = u['nc.cicbio@test.redib.net']
        nc_b = u['nc.cnic@test.redib.net']
        ev_pre = u['eval.preclinical@test.redib.net']  # uni
        ev_clin = u['eval.clinical@test.redib.net']    # inst
        ev_radio = u['eval.radio@test.redib.net']      # inst

        node_a = node_lookup['CICBIO']
        node_b = node_lookup['CNIC']
        equip_a = list(Equipment.objects.filter(node=node_a))
        equip_b = list(Equipment.objects.filter(node=node_b))

        aei = agencies[0]
        erc = agencies[3]
        open_call = calls['open']

        created_apps = []

        # LIVE-001: draft — wizard partially filled
        app = Application.objects.create(
            code='LIVE-001', call=open_call, applicant=applicant1, status='draft',
            project_name='Draft: Preclinical MRI Study',
            brief_description='Preclinical MRI draft',
            applicant_name=f'{applicant1.first_name} {applicant1.last_name}',
            applicant_entity=applicant1.organization.name,
            applicant_email=applicant1.email,
            applicant_phone=applicant1.phone,
            funding_agency_obj=aei,
            project_type='spanish_government',
            subject_area='bme',
            service_modality='full_assistance',
            specialization_area='preclinical',
        )
        self._add_requested_access(app, [equip_a[0]], hours=Decimal('16'))
        created_apps.append(('LIVE-001', app, 'Resume draft, finish & submit'))

        # LIVE-002: under_feasibility_review — single-node, pending
        app = Application.objects.create(
            code='LIVE-002', call=open_call, applicant=applicant1,
            status='under_feasibility_review',
            **self._base_application_fields(
                applicant1, 'Preclinical Neuroinflammation Imaging',
                'preclinical', aei, submitted_offset_days=-3),
        )
        self._add_requested_access(app, equip_a, hours=Decimal('20'))
        self._add_feasibility(app, node_a, nc_a, 'pending')
        created_apps.append(('LIVE-002', app,
                             'Single-node feasibility approve → pending_evaluation'))

        # LIVE-003: under_feasibility_review — multi-node, A approved, B pending
        app = Application.objects.create(
            code='LIVE-003', call=open_call, applicant=applicant2,
            status='under_feasibility_review',
            **self._base_application_fields(
                applicant2, 'Multi-node Cardiac-Neuro Imaging',
                'clinical', erc, submitted_offset_days=-5),
        )
        self._add_requested_access(app, [equip_a[1], equip_b[0]], hours=Decimal('18'))
        self._add_feasibility(app, node_a, nc_a, 'approved',
                              comments='Equipment available.', reviewed_offset=-2)
        self._add_feasibility(app, node_b, nc_b, 'pending')
        created_apps.append(('LIVE-003', app,
                             'Multi-node: Node B decides → aggregation'))

        # LIVE-004: pending_evaluation — no evaluators yet
        # applicant3 is at uni → eval.preclinical is at uni → COI filter will
        # exclude eval.preclinical during coordinator auto-assign.
        app = Application.objects.create(
            code='LIVE-004', call=open_call, applicant=applicant3,
            status='pending_evaluation',
            **self._base_application_fields(
                applicant3, 'Preclinical Oncology Imaging Pipeline',
                'preclinical', aei, submitted_offset_days=-10),
        )
        self._add_requested_access(app, [equip_a[0]], hours=Decimal('24'))
        self._add_feasibility(app, node_a, nc_a, 'approved',
                              comments='Feasible', reviewed_offset=-7)
        created_apps.append(('LIVE-004', app,
                             'Coordinator assigns evaluators (COI filter excludes eval.preclinical)'))

        # LIVE-005: under_evaluation — 2 evaluators assigned, 0 scores
        app = Application.objects.create(
            code='LIVE-005', call=open_call, applicant=applicant1,
            status='under_evaluation',
            **self._base_application_fields(
                applicant1, 'Radiotracer Validation Study',
                'radiochemistry', erc, submitted_offset_days=-14),
        )
        self._add_requested_access(app, [equip_a[1]], hours=Decimal('30'))
        self._add_feasibility(app, node_a, nc_a, 'approved',
                              comments='Feasible', reviewed_offset=-10)
        self._add_evaluation(app, ev_clin, scores=None)
        self._add_evaluation(app, ev_radio, scores=None)
        created_apps.append(('LIVE-005', app,
                             'Both evaluators submit scores → auto-transitions to evaluated'))

        # LIVE-006: under_evaluation — 1 of 2 done
        app = Application.objects.create(
            code='LIVE-006', call=open_call, applicant=applicant3,
            status='under_evaluation',
            **self._base_application_fields(
                applicant3, 'Clinical Stroke Recovery MRI',
                'clinical', aei, submitted_offset_days=-14),
        )
        self._add_requested_access(app, [equip_a[0]], hours=Decimal('24'))
        self._add_feasibility(app, node_a, nc_a, 'approved',
                              comments='Feasible', reviewed_offset=-11)
        self._add_evaluation(app, ev_clin, scores=[1, 2, 1, 2, 1, 1],
                             completed_offset=-4)  # sum=8
        self._add_evaluation(app, ev_radio, scores=None)
        created_apps.append(('LIVE-006', app,
                             'Second evaluator submits → auto-transitions to evaluated'))

        # LIVE-007: evaluated, high score, multi-node
        app = Application.objects.create(
            code='LIVE-007', call=open_call, applicant=applicant3,
            status='evaluated',
            final_score=Decimal('10.5'),
            **self._base_application_fields(
                applicant3, 'Advanced Multi-Modal Cardiac Imaging',
                'clinical', erc, submitted_offset_days=-21),
        )
        self._add_requested_access(app, [equip_a[0], equip_b[0]], hours=Decimal('16'))
        self._add_feasibility(app, node_a, nc_a, 'approved',
                              comments='Feasible', reviewed_offset=-18)
        self._add_feasibility(app, node_b, nc_b, 'approved',
                              comments='Feasible', reviewed_offset=-18)
        self._add_evaluation(app, ev_clin,  scores=[2, 2, 2, 2, 1, 2], completed_offset=-8)  # 11
        self._add_evaluation(app, ev_radio, scores=[2, 2, 2, 1, 2, 1], completed_offset=-7)  # 10
        created_apps.append(('LIVE-007', app,
                             'Node coordinators submit per-node resolutions (try mixed / waitlist)'))

        # LIVE-008: evaluated, LOW score, competitive funding (reject-protected)
        app = Application.objects.create(
            code='LIVE-008', call=open_call, applicant=applicant1,
            status='evaluated',
            final_score=Decimal('4.0'),
            **self._base_application_fields(
                applicant1, 'Exploratory Micro-CT Protocol',
                'preclinical', aei, submitted_offset_days=-21),
        )
        self._add_requested_access(app, [equip_a[1]], hours=Decimal('16'))
        self._add_feasibility(app, node_a, nc_a, 'approved',
                              comments='Feasible', reviewed_offset=-18)
        self._add_evaluation(app, ev_clin,  scores=[1, 1, 0, 1, 1, 0], completed_offset=-8)  # 4
        self._add_evaluation(app, ev_radio, scores=[1, 0, 1, 1, 0, 1], completed_offset=-7)  # 4
        created_apps.append(('LIVE-008', app,
                             'Competitive funding: Reject action is blocked for NC'))

        # LIVE-009: accepted — awaiting applicant acceptance
        app = Application.objects.create(
            code='LIVE-009', call=open_call, applicant=applicant2,
            status='accepted',
            final_score=Decimal('10.0'),
            resolution='accepted',
            resolution_date=now - timedelta(days=2),
            acceptance_deadline=now + timedelta(days=8),
            accepted_by_applicant=None,
            **self._base_application_fields(
                applicant2, 'Clinical PET Metabolism Study',
                'clinical', erc, submitted_offset_days=-28),
        )
        self._add_requested_access(app, [equip_a[1]], hours=Decimal('20'),
                                    hours_approved=Decimal('20'))
        self._add_feasibility(app, node_a, nc_a, 'approved',
                              comments='Feasible', reviewed_offset=-25)
        self._add_evaluation(app, ev_pre,   scores=[2, 2, 2, 1, 2, 1], completed_offset=-10)  # 10
        self._add_evaluation(app, ev_radio, scores=[2, 2, 1, 2, 2, 1], completed_offset=-9)   # 10
        self._add_node_resolution(app, node_a, nc_a, 'accept', reviewed_offset=-2)
        created_apps.append(('LIVE-009', app,
                             'Applicant accepts/declines within 10-day window; handoff email fires on accept'))

        # LIVE-010: pending (waitlist) — awaiting applicant acceptance
        app = Application.objects.create(
            code='LIVE-010', call=open_call, applicant=applicant3,
            status='pending',
            final_score=Decimal('8.5'),
            resolution='pending',
            resolution_date=now - timedelta(days=2),
            acceptance_deadline=now + timedelta(days=8),
            accepted_by_applicant=None,
            **self._base_application_fields(
                applicant3, 'Clinical Brain Connectivity Study',
                'clinical', aei, submitted_offset_days=-28),
        )
        self._add_requested_access(app, [equip_a[0]], hours=Decimal('24'),
                                    hours_approved=Decimal('12'))
        self._add_feasibility(app, node_a, nc_a, 'approved',
                              comments='Feasible', reviewed_offset=-25)
        self._add_evaluation(app, ev_clin,  scores=[2, 1, 2, 1, 1, 2], completed_offset=-10)  # 9
        self._add_evaluation(app, ev_radio, scores=[1, 2, 1, 2, 1, 1], completed_offset=-9)   # 8
        self._add_node_resolution(app, node_a, nc_a, 'waitlist', reviewed_offset=-2)
        created_apps.append(('LIVE-010', app,
                             'Applicant accepts waitlist → NC promotes via Access Tracking'))

        for code, app, _purpose in created_apps:
            self.stdout.write(f'    Created: {code} ({app.status})')

        return created_apps

    # -------------------------------------------------------------------------
    # Step 10: PAST applications (resolved call, terminal / post-resolution)
    # -------------------------------------------------------------------------
    def create_past_applications(self, users, calls, nodes, agencies):
        from applications.models import Application
        from access.models import Publication
        from core.models import Equipment

        now = timezone.now()
        u = {u['user'].email: u['user'] for u in users}
        node_lookup = {n.code: n for n in nodes}

        applicant1 = u['applicant1@test.redib.net']
        applicant2 = u['applicant2@test.redib.net']
        applicant3 = u['applicant3@test.redib.net']
        nc_a = u['nc.cicbio@test.redib.net']
        ev_clin = u['eval.clinical@test.redib.net']
        ev_radio = u['eval.radio@test.redib.net']
        ev_pre = u['eval.preclinical@test.redib.net']

        node_a = node_lookup['CICBIO']
        equip_a = list(Equipment.objects.filter(node=node_a))

        aei = agencies[0]
        erc = agencies[3]
        resolved_call = calls['resolved']

        created_apps = []

        # PAST-001: accepted, active access tracking, no hours used yet
        app = Application.objects.create(
            code='PAST-001', call=resolved_call, applicant=applicant1,
            status='accepted',
            final_score=Decimal('10.0'),
            resolution='accepted',
            resolution_date=now - timedelta(days=40),
            acceptance_deadline=now - timedelta(days=30),
            accepted_by_applicant=True,
            accepted_at=now - timedelta(days=30),
            handoff_email_sent_at=now - timedelta(days=30),
            **self._base_application_fields(
                applicant1, 'Active MRI Access Program',
                'preclinical', aei, submitted_offset_days=-100),
        )
        self._add_requested_access(app, [equip_a[0]], hours=Decimal('24'),
                                    hours_approved=Decimal('24'))
        self._add_feasibility(app, node_a, nc_a, 'approved',
                              comments='Feasible', reviewed_offset=-90)
        self._add_evaluation(app, ev_clin,  scores=[2, 2, 2, 2, 1, 1], completed_offset=-70)
        self._add_evaluation(app, ev_radio, scores=[2, 2, 2, 1, 2, 1], completed_offset=-69)
        self._add_node_resolution(app, node_a, nc_a, 'accept', reviewed_offset=-40)
        created_apps.append(('PAST-001', app,
                             'Access tracking: mark equipment complete, log actual hours'))

        # PAST-002: completed with publication
        app = Application.objects.create(
            code='PAST-002', call=resolved_call, applicant=applicant2,
            status='completed',
            final_score=Decimal('10.5'),
            resolution='accepted',
            resolution_date=now - timedelta(days=60),
            acceptance_deadline=now - timedelta(days=50),
            accepted_by_applicant=True,
            accepted_at=now - timedelta(days=50),
            handoff_email_sent_at=now - timedelta(days=50),
            is_completed=True,
            completed_at=now - timedelta(days=10),
            **self._base_application_fields(
                applicant2, 'Completed Clinical PET Study',
                'clinical', erc, submitted_offset_days=-110),
        )
        self._add_requested_access(
            app, [equip_a[1]], hours=Decimal('20'),
            hours_approved=Decimal('20'),
            actual_hours=Decimal('18'),
            is_completed=True,
            completed_by=applicant2,
            completed_at=now - timedelta(days=10),
        )
        self._add_feasibility(app, node_a, nc_a, 'approved',
                              comments='Feasible', reviewed_offset=-100)
        self._add_evaluation(app, ev_pre,   scores=[2, 2, 2, 2, 1, 2], completed_offset=-80)
        self._add_evaluation(app, ev_radio, scores=[2, 2, 2, 1, 2, 1], completed_offset=-79)
        self._add_node_resolution(app, node_a, nc_a, 'accept', reviewed_offset=-60)
        Publication.objects.create(
            application=app,
            title='Advanced Clinical PET Imaging: Results from a ReDIB Access Study',
            authors='Moreno D, Rodriguez A, Navarro L',
            doi='10.1234/test.2025.001',
            journal='Journal of Biomedical Imaging',
            publication_date=(now - timedelta(days=5)).date(),
            redib_acknowledged=True,
            acknowledgment_text='This study was conducted with access provided by the ReDIB Network.',
            reported_by=applicant2,
        )
        created_apps.append(('PAST-002', app,
                             'View existing publication; add a new publication'))

        # PAST-003: declined_by_applicant
        app = Application.objects.create(
            code='PAST-003', call=resolved_call, applicant=applicant3,
            status='declined_by_applicant',
            final_score=Decimal('9.0'),
            resolution='accepted',
            resolution_date=now - timedelta(days=50),
            acceptance_deadline=now - timedelta(days=40),
            accepted_by_applicant=False,
            accepted_at=now - timedelta(days=42),
            **self._base_application_fields(
                applicant3, 'Declined Access Study',
                'preclinical', None, submitted_offset_days=-105),
        )
        self._add_requested_access(app, [equip_a[0]], hours=Decimal('16'),
                                    hours_approved=Decimal('16'))
        self._add_feasibility(app, node_a, nc_a, 'approved',
                              comments='Feasible', reviewed_offset=-95)
        self._add_evaluation(app, ev_clin,  scores=[2, 2, 1, 1, 2, 1], completed_offset=-75)
        self._add_evaluation(app, ev_radio, scores=[2, 1, 2, 2, 1, 1], completed_offset=-74)
        self._add_node_resolution(app, node_a, nc_a, 'accept', reviewed_offset=-50)
        created_apps.append(('PAST-003', app, 'Terminal state: applicant declined access'))

        # PAST-004: rejected (low score)
        app = Application.objects.create(
            code='PAST-004', call=resolved_call, applicant=applicant2,
            status='rejected',
            final_score=Decimal('3.5'),
            resolution='rejected',
            resolution_date=now - timedelta(days=50),
            **self._base_application_fields(
                applicant2, 'Rejected Low-Score Study',
                'radiochemistry', aei, submitted_offset_days=-105),
        )
        self._add_requested_access(app, [equip_a[0]], hours=Decimal('16'),
                                    hours_approved=Decimal('0'))
        self._add_feasibility(app, node_a, nc_a, 'approved',
                              comments='Feasible', reviewed_offset=-95)
        self._add_evaluation(app, ev_pre,   scores=[1, 0, 1, 0, 1, 0], completed_offset=-75)  # 3
        self._add_evaluation(app, ev_radio, scores=[1, 1, 0, 1, 0, 1], completed_offset=-74)  # 4
        self._add_node_resolution(app, node_a, nc_a, 'reject', reviewed_offset=-50)
        created_apps.append(('PAST-004', app, 'Terminal state: rejected (low score)'))

        # PAST-005: rejected_feasibility
        app = Application.objects.create(
            code='PAST-005', call=resolved_call, applicant=applicant1,
            status='rejected_feasibility',
            **self._base_application_fields(
                applicant1, 'Rejected Feasibility Study',
                'preclinical', None, submitted_offset_days=-100),
        )
        self._add_requested_access(app, [equip_a[1]], hours=Decimal('40'))
        self._add_feasibility(app, node_a, nc_a, 'rejected',
                              comments='Equipment cannot support these parameters.',
                              reviewed_offset=-90)
        created_apps.append(('PAST-005', app,
                             'Terminal state: rejected during feasibility review'))

        # PAST-006: expired — applicant never responded within 10 days
        app = Application.objects.create(
            code='PAST-006', call=resolved_call, applicant=applicant3,
            status='expired',
            final_score=Decimal('9.5'),
            resolution='accepted',
            resolution_date=now - timedelta(days=12),
            acceptance_deadline=now - timedelta(days=2),
            accepted_by_applicant=None,
            **self._base_application_fields(
                applicant3, 'Expired Acceptance Study',
                'clinical', None, submitted_offset_days=-70),
        )
        self._add_requested_access(app, [equip_a[0]], hours=Decimal('20'),
                                    hours_approved=Decimal('20'))
        self._add_feasibility(app, node_a, nc_a, 'approved',
                              comments='Feasible', reviewed_offset=-60)
        self._add_evaluation(app, ev_clin,  scores=[2, 2, 2, 1, 1, 2], completed_offset=-40)
        self._add_evaluation(app, ev_radio, scores=[2, 2, 1, 2, 1, 1], completed_offset=-39)
        self._add_node_resolution(app, node_a, nc_a, 'accept', reviewed_offset=-12)
        created_apps.append(('PAST-006', app,
                             'Terminal state: applicant did not respond within 10 days'))

        for code, app, _purpose in created_apps:
            self.stdout.write(f'    Created: {code} ({app.status})')

        return created_apps

    # -------------------------------------------------------------------------
    # Summary cheat-sheet
    # -------------------------------------------------------------------------
    def print_cheatsheet(self, users, calls, live_apps, past_apps):
        from core.models import Node, Equipment, Organization
        from applications.models import Application, FundingAgency

        self.stdout.write('\n' + '=' * 78)
        self.stdout.write(self.style.SUCCESS('LOCAL TEST 3 SANDBOX — READY'))
        self.stdout.write('=' * 78)

        self.stdout.write(self.style.WARNING('\n── Data summary ──'))
        self.stdout.write(f'  Nodes:              {Node.objects.count()}')
        self.stdout.write(f'  Equipment:          {Equipment.objects.count()}')
        self.stdout.write(f'  Organizations:      {Organization.objects.count()}')
        self.stdout.write(f'  Funding Agencies:   {FundingAgency.objects.count()}')
        self.stdout.write(f'  Users (non-super):  {User.objects.filter(is_superuser=False).count()}')
        self.stdout.write(f'  Calls:              {len(calls)}')
        self.stdout.write(f'  Applications:       {Application.objects.count()} '
                          f'({len(live_apps)} LIVE + {len(past_apps)} PAST)')

        # Login table
        self.stdout.write(self.style.WARNING('\n── Login table (password: testpass123) ──'))
        self.stdout.write(f'  {"Email":<40} {"Role":<17} {"Node / Areas"}')
        self.stdout.write(f'  {"-" * 40} {"-" * 17} {"-" * 20}')
        for entry in users:
            u = entry['user']
            extra = entry.get('node_code') or entry.get('area') or '-'
            self.stdout.write(f'  {u.email:<40} {entry["role"]:<17} {extra}')

        # Calls
        self.stdout.write(self.style.WARNING('\n── Calls ──'))
        for key, call in calls.items():
            self.stdout.write(
                f'  {call.code:<16} status={call.status:<10} '
                f'submission {call.submission_start.strftime("%Y-%m-%d")} → '
                f'{call.submission_end.strftime("%Y-%m-%d")}'
            )

        # Live apps
        self.stdout.write(self.style.WARNING(
            '\n── LIVE applications (COA-LIVE-2026) — step through phases 1–8 ──'))
        self.stdout.write(f'  {"Code":<10} {"Status":<26} {"Applicant":<32} What to test')
        self.stdout.write(f'  {"-" * 10} {"-" * 26} {"-" * 32} {"-" * 50}')
        for code, app, purpose in live_apps:
            self.stdout.write(
                f'  {code:<10} {app.status:<26} {app.applicant.email:<32} {purpose}'
            )

        # Past apps
        self.stdout.write(self.style.WARNING(
            '\n── PAST applications (COA-PAST-2025) — terminal / access / publication ──'))
        self.stdout.write(f'  {"Code":<10} {"Status":<26} {"Applicant":<32} What to test')
        self.stdout.write(f'  {"-" * 10} {"-" * 26} {"-" * 32} {"-" * 50}')
        for code, app, purpose in past_apps:
            self.stdout.write(
                f'  {code:<10} {app.status:<26} {app.applicant.email:<32} {purpose}'
            )

        # Quick-start hint
        self.stdout.write(self.style.SUCCESS('\n── Quick start ──'))
        self.stdout.write('  python manage.py runserver')
        self.stdout.write('  Open http://127.0.0.1:8000/ and log in.')
        self.stdout.write('  Manual-test walkthrough: docs/developer/localtest3-database-plan.md')
        self.stdout.write('=' * 78 + '\n')
