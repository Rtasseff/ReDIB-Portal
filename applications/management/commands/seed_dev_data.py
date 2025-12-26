"""
Django management command to seed minimal development data for testing all workflows.

Usage:
    python manage.py seed_dev_data          # Add data (idempotent)
    python manage.py seed_dev_data --clear  # Clear and rebuild all test data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed minimal development data for testing all workflows'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding (WARNING: Destructive!)',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            self.clear_data()

        self.stdout.write('Creating organizations...')
        orgs = self.create_organizations()

        self.stdout.write('Creating nodes and equipment...')
        nodes, equipment = self.create_nodes_and_equipment()

        self.stdout.write('Creating users...')
        users = self.create_users(orgs, nodes)

        self.stdout.write('Creating calls...')
        calls = self.create_calls(equipment)

        self.stdout.write('Creating applications...')
        apps = self.create_applications(users, calls, equipment)

        self.stdout.write('Creating evaluations and grants...')
        self.create_evaluations(users, apps)

        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('✓ Development data seeded successfully!'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.print_summary(users)

    def clear_data(self):
        """Clear all test data in reverse dependency order."""
        from access.models import Publication, AccessGrant
        from evaluations.models import Evaluation
        from applications.models import FeasibilityReview, RequestedAccess, Application
        from calls.models import CallEquipmentAllocation, Call
        from core.models import Equipment, Node, Organization, UserRole

        # Clear in reverse dependency order to avoid foreign key errors
        Publication.objects.all().delete()
        AccessGrant.objects.all().delete()
        Evaluation.objects.all().delete()
        FeasibilityReview.objects.all().delete()
        RequestedAccess.objects.all().delete()
        Application.objects.all().delete()
        CallEquipmentAllocation.objects.all().delete()
        Call.objects.all().delete()
        Equipment.objects.all().delete()
        Node.objects.all().delete()
        UserRole.objects.all().delete()
        # Don't delete superusers
        User.objects.filter(is_superuser=False).delete()
        Organization.objects.all().delete()

        self.stdout.write(self.style.WARNING('  → All test data cleared'))

    def create_organizations(self):
        """Create test organizations."""
        from core.models import Organization

        orgs = {}
        org_data = [
            ('redib', 'ReDIB ICTS', 'Spain', 'ministry'),
            ('uni_test', 'Universidad de Pruebas', 'Spain', 'university'),
            ('ext_inst', 'External Research Institute', 'Germany', 'research_center'),
        ]

        for key, name, country, org_type in org_data:
            orgs[key], created = Organization.objects.get_or_create(
                name=name,
                defaults={'country': country, 'organization_type': org_type}
            )
            if created:
                self.stdout.write(f'  → Created organization: {name}')

        return orgs

    def create_nodes_and_equipment(self):
        """Create test nodes and equipment."""
        from core.models import Node, Equipment

        nodes = {}
        equipment = {}

        # Create nodes
        node_data = [
            ('CICBIO', 'CIC biomaGUNE', 'San Sebastián, Spain',
             'This research was supported by ReDIB ICTS at CIC biomaGUNE.'),
            ('CNIC', 'Centro Nacional de Investigaciones Cardiovasculares', 'Madrid, Spain',
             'This research was supported by ReDIB ICTS at CNIC.'),
        ]

        for code, name, location, ack in node_data:
            nodes[code], created = Node.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'location': location,
                    'acknowledgment_text': ack,
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(f'  → Created node: {code} - {name}')

        # Create equipment
        equip_data = [
            ('cic_mri7t', nodes['CICBIO'], 'MRI 7T', 'mri', True),
            ('cic_petct', nodes['CICBIO'], 'PET-CT', 'pet_ct', True),
            ('cnic_mri3t', nodes['CNIC'], 'MRI 3T', 'mri', True),
            ('cnic_petct', nodes['CNIC'], 'PET-CT', 'pet_ct', True),
        ]

        for code, node, name, category, essential in equip_data:
            equipment[code], created = Equipment.objects.get_or_create(
                node=node,
                name=name,
                defaults={
                    'category': category,
                    'is_essential': essential,
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(f'  → Created equipment: {node.code} - {name}')

        return nodes, equipment

    def create_users(self, orgs, nodes):
        """Create test users with roles."""
        from core.models import UserRole

        users = {}

        # Simple password for all test users
        password = 'testpass123'

        # (key, email, first, last, org_key, roles)
        # roles format: [(role_name, node_code_or_None, area_or_empty)]
        user_data = [
            ('admin', 'admin@test.redib.net', 'Admin', 'User', 'redib',
             [('admin', None, '')]),
            ('coordinator', 'coordinator@test.redib.net', 'Test', 'Coordinator', 'redib',
             [('coordinator', None, '')]),
            ('node_cic', 'cic@test.redib.net', 'CIC', 'NodeCoord', 'redib',
             [('node_coordinator', 'CICBIO', '')]),
            ('node_cnic', 'cnic@test.redib.net', 'CNIC', 'NodeCoord', 'redib',
             [('node_coordinator', 'CNIC', '')]),
            ('evaluator1', 'eval1@test.redib.net', 'Eva', 'Luator', 'ext_inst',
             [('evaluator', None, 'preclinical')]),
            ('evaluator2', 'eval2@test.redib.net', 'Review', 'Expert', 'ext_inst',
             [('evaluator', None, 'clinical')]),
            ('applicant1', 'applicant1@test.redib.net', 'Alice', 'Researcher', 'uni_test',
             [('applicant', None, '')]),
            ('applicant2', 'applicant2@test.redib.net', 'Bob', 'Scientist', 'ext_inst',
             [('applicant', None, '')]),
        ]

        for key, email, first, last, org_key, roles in user_data:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'organization': orgs[org_key],
                    'is_staff': key in ['admin', 'coordinator'],
                    'is_active': True,
                }
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(f'  → Created user: {email}')

            users[key] = user

            # Create user roles
            for role_data in roles:
                role_name = role_data[0]
                node_code = role_data[1]
                area = role_data[2] if len(role_data) > 2 else ''

                # Find the node if specified
                node = None
                if node_code and node_code in nodes:
                    node = nodes[node_code]

                role, role_created = UserRole.objects.update_or_create(
                    user=user,
                    role=role_name,
                    node=node,
                    defaults={'area': area, 'is_active': True}
                )
                if role_created:
                    display = f"{role_name} at {node.code}" if node else role_name
                    self.stdout.write(f'    → Assigned role: {display}')
                else:
                    # Update area if it changed
                    if role.area != area:
                        role.area = area
                        role.save()
                        self.stdout.write(f'    → Updated role area: {role_name}')

        return users

    def create_calls(self, equipment):
        """Create test calls with equipment allocations."""
        from calls.models import Call, CallEquipmentAllocation

        now = timezone.now()
        calls = {}

        # Resolved call (past)
        calls['resolved'], created = Call.objects.get_or_create(
            code='COA-TEST-01',
            defaults={
                'title': 'Test Call 01 (Resolved)',
                'status': 'resolved',
                'submission_start': now - timedelta(days=90),
                'submission_end': now - timedelta(days=60),
                'evaluation_deadline': now - timedelta(days=45),
                'execution_start': now - timedelta(days=30),
                'execution_end': now + timedelta(days=30),
                'description': 'A resolved test call for development testing.',
                'published_at': now - timedelta(days=90),
            }
        )
        if created:
            self.stdout.write(f'  → Created call: COA-TEST-01 (resolved)')

        # Open call (current)
        calls['open'], created = Call.objects.get_or_create(
            code='COA-TEST-02',
            defaults={
                'title': 'Test Call 02 (Open)',
                'status': 'open',
                'submission_start': now - timedelta(days=7),
                'submission_end': now + timedelta(days=38),
                'evaluation_deadline': now + timedelta(days=53),
                'execution_start': now + timedelta(days=60),
                'execution_end': now + timedelta(days=120),
                'description': 'An open test call for development testing.',
                'published_at': now - timedelta(days=7),
            }
        )
        if created:
            self.stdout.write(f'  → Created call: COA-TEST-02 (open)')

        # Allocate equipment hours to calls
        for call in calls.values():
            for equip in equipment.values():
                CallEquipmentAllocation.objects.get_or_create(
                    call=call,
                    equipment=equip,
                    defaults={'hours_offered': 50}
                )

        return calls

    def create_applications(self, users, calls, equipment):
        """Create test applications in various states."""
        from applications.models import Application, RequestedAccess

        apps = {}
        now = timezone.now()

        # APP-001: Completed application (full workflow done)
        apps['completed'], created = Application.objects.get_or_create(
            code='APP-TEST-001',
            defaults={
                'call': calls['resolved'],
                'applicant': users['applicant1'],
                'status': 'completed',
                'brief_description': 'MRI study of preclinical models',
                'project_title': 'Advanced MRI Techniques for Preclinical Research',
                'project_code': 'PID2024-TEST-001',
                'funding_agency': 'Agencia Estatal de Investigación',
                'project_type': 'national_public',
                'has_competitive_funding': True,
                'subject_area': 'med',
                'service_modality': 'full_assistance',
                'specialization_area': 'preclinical',
                'scientific_relevance': 'High relevance for understanding disease mechanisms.',
                'methodology_description': 'Standard MRI protocols with advanced sequences.',
                'expected_contributions': 'Novel insights into molecular imaging.',
                'impact_strengths': 'Strong potential for publication in top journals.',
                'socioeconomic_significance': 'Contributes to improved diagnostic methods.',
                'opportunity_criteria': 'Timely and addresses current research gaps.',
                'technical_feasibility_confirmed': True,
                'data_consent': True,
                'final_score': 4.2,
                'resolution': 'accepted',
                'submitted_at': now - timedelta(days=85),
            }
        )
        if created:
            self.stdout.write(f'  → Created application: APP-TEST-001 (completed)')

        # APP-002: Rejected application
        apps['rejected'], created = Application.objects.get_or_create(
            code='APP-TEST-002',
            defaults={
                'call': calls['resolved'],
                'applicant': users['applicant2'],
                'status': 'rejected',
                'brief_description': 'PET imaging proposal with limited scope',
                'project_title': 'Basic PET Imaging Study',
                'project_type': 'private',
                'has_competitive_funding': False,
                'subject_area': 'bio',
                'service_modality': 'presential',
                'specialization_area': 'preclinical',
                'scientific_relevance': 'Limited novelty and relevance.',
                'methodology_description': 'Standard protocols without innovation.',
                'expected_contributions': 'Minimal scientific contribution.',
                'impact_strengths': 'Low impact potential.',
                'socioeconomic_significance': 'Limited broader significance.',
                'opportunity_criteria': 'Not timely or compelling.',
                'technical_feasibility_confirmed': True,
                'data_consent': True,
                'final_score': 2.1,
                'resolution': 'rejected',
                'submitted_at': now - timedelta(days=84),
            }
        )
        if created:
            self.stdout.write(f'  → Created application: APP-TEST-002 (rejected)')

        # APP-003: Draft (for testing submission)
        apps['draft'], created = Application.objects.get_or_create(
            code='APP-TEST-003',
            defaults={
                'call': calls['open'],
                'applicant': users['applicant1'],
                'status': 'draft',
                'brief_description': 'Draft application for submission testing',
                'data_consent': False,
            }
        )
        if created:
            self.stdout.write(f'  → Created application: APP-TEST-003 (draft)')

        # APP-004: Under feasibility review
        apps['feasibility'], created = Application.objects.get_or_create(
            code='APP-TEST-004',
            defaults={
                'call': calls['open'],
                'applicant': users['applicant2'],
                'status': 'under_feasibility_review',
                'brief_description': 'Clinical MRI study awaiting feasibility review',
                'project_title': 'Clinical Cardiovascular Imaging Study',
                'project_type': 'international',
                'has_competitive_funding': True,
                'subject_area': 'med',
                'service_modality': 'full_assistance',
                'specialization_area': 'clinical',
                'scientific_relevance': 'Good relevance for cardiovascular research.',
                'methodology_description': 'Well-designed clinical imaging protocol.',
                'expected_contributions': 'Expected to contribute to clinical guidelines.',
                'impact_strengths': 'Moderate to high impact potential.',
                'socioeconomic_significance': 'Directly benefits patient care.',
                'opportunity_criteria': 'Timely for current clinical needs.',
                'technical_feasibility_confirmed': False,
                'data_consent': True,
                'submitted_at': now - timedelta(days=5),
            }
        )
        if created:
            self.stdout.write(f'  → Created application: APP-TEST-004 (under_feasibility_review)')

        # Add equipment requests
        RequestedAccess.objects.get_or_create(
            application=apps['completed'],
            equipment=equipment['cic_mri7t'],
            defaults={'hours_requested': 24}
        )
        RequestedAccess.objects.get_or_create(
            application=apps['rejected'],
            equipment=equipment['cic_petct'],
            defaults={'hours_requested': 16}
        )
        RequestedAccess.objects.get_or_create(
            application=apps['feasibility'],
            equipment=equipment['cnic_mri3t'],
            defaults={'hours_requested': 20}
        )

        return apps

    def create_evaluations(self, users, apps):
        """Create evaluations, access grants, and publications."""
        from evaluations.models import Evaluation
        from access.models import AccessGrant, Publication
        from core.models import Equipment

        now = timezone.now()

        # Evaluations for completed app
        Evaluation.objects.get_or_create(
            application=apps['completed'],
            evaluator=users['evaluator1'],
            defaults={
                'score_relevance': 4,
                'score_methodology': 4,
                'score_contributions': 5,
                'score_impact': 4,
                'score_opportunity': 4,
                'total_score': 4.2,
                'comments': 'Excellent proposal with strong methodology.',
                'completed_at': now - timedelta(days=50),
            }
        )

        Evaluation.objects.get_or_create(
            application=apps['completed'],
            evaluator=users['evaluator2'],
            defaults={
                'score_relevance': 4,
                'score_methodology': 5,
                'score_contributions': 4,
                'score_impact': 4,
                'score_opportunity': 4,
                'total_score': 4.2,
                'comments': 'Well-designed study with clear objectives.',
                'completed_at': now - timedelta(days=48),
            }
        )

        # Evaluations for rejected app
        Evaluation.objects.get_or_create(
            application=apps['rejected'],
            evaluator=users['evaluator1'],
            defaults={
                'score_relevance': 2,
                'score_methodology': 2,
                'score_contributions': 2,
                'score_impact': 2,
                'score_opportunity': 2,
                'total_score': 2.0,
                'comments': 'Proposal lacks novelty and scientific rigor.',
                'completed_at': now - timedelta(days=50),
            }
        )

        Evaluation.objects.get_or_create(
            application=apps['rejected'],
            evaluator=users['evaluator2'],
            defaults={
                'score_relevance': 2,
                'score_methodology': 3,
                'score_contributions': 2,
                'score_impact': 2,
                'score_opportunity': 2,
                'total_score': 2.2,
                'comments': 'Not competitive compared to other proposals.',
                'completed_at': now - timedelta(days=49),
            }
        )

        # Access grant for completed app
        equipment = Equipment.objects.get(name='MRI 7T')

        grant, created = AccessGrant.objects.get_or_create(
            application=apps['completed'],
            equipment=equipment,
            defaults={
                'hours_granted': 24,
                'scheduled_start': now.date() - timedelta(days=20),
                'scheduled_end': now.date() - timedelta(days=10),
                'accepted_by_user': True,
                'accepted_at': now - timedelta(days=25),
                'completed_at': now - timedelta(days=10),
                'actual_hours_used': 22,
            }
        )
        if created:
            self.stdout.write(f'  → Created access grant for APP-TEST-001')

        # Publication for completed app
        pub, created = Publication.objects.get_or_create(
            access_grant=grant,
            defaults={
                'title': 'Advanced MRI Techniques Reveal Novel Disease Mechanisms',
                'doi': '10.1234/test.2025.001',
                'journal': 'Journal of Molecular Imaging',
                'publication_date': now.date() - timedelta(days=5),
                'redib_acknowledged': True,
            }
        )
        if created:
            self.stdout.write(f'  → Created publication for APP-TEST-001')

    def print_summary(self, users):
        """Print login credentials for all test users."""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('TEST USER ACCOUNTS'))
        self.stdout.write('='*60)
        self.stdout.write('All accounts use password: testpass123')
        self.stdout.write('-'*60)

        for key, user in users.items():
            roles = ', '.join([r.get_role_display() for r in user.roles.all()])
            self.stdout.write(f'  {user.email:30s} → {roles}')

        self.stdout.write('='*60)
        self.stdout.write('\nYou can now:')
        self.stdout.write('  1. Login as any user at http://localhost:8000/accounts/login/')
        self.stdout.write('  2. View admin at http://localhost:8000/admin/')
        self.stdout.write('  3. Test workflows with different user roles')
        self.stdout.write('='*60 + '\n')
