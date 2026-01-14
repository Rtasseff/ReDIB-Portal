"""
Django management command to seed multiple applicants with applications at various stages for comprehensive testing.

Usage:
    python manage.py seed_test_applicants          # Create test applicants
    python manage.py seed_test_applicants --clear  # Clear test applicants and recreate
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, datetime, time
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed multiple applicants with applications at various stages for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing test applicant data before seeding',
        )

    def handle(self, *args, **options):
        # Check prerequisites
        if not self.check_prerequisites():
            return

        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing test applicant data...'))
            self.clear_test_data()

        self.stdout.write('Creating test applicants...')
        applicants = self.create_applicants()

        self.stdout.write('Creating test applications at various stages...')
        self.create_applications(applicants)

        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('✓ Test applicants and applications created successfully!'))
        self.stdout.write(self.style.SUCCESS('='*70))
        self.print_summary(applicants)

    def check_prerequisites(self):
        """Check that required data exists."""
        from calls.models import Call
        from core.models import Node, Equipment, Organization

        # Check for calls
        if not Call.objects.exists():
            self.stdout.write(self.style.ERROR('ERROR: No calls found. Please run seed_dev_data first.'))
            return False

        # Check for nodes
        if not Node.objects.exists():
            self.stdout.write(self.style.ERROR('ERROR: No nodes found. Please run populate_redib_nodes first.'))
            return False

        # Check for equipment
        if not Equipment.objects.exists():
            self.stdout.write(self.style.ERROR('ERROR: No equipment found. Please run populate_redib_equipment first.'))
            return False

        # Check for organizations
        if not Organization.objects.exists():
            self.stdout.write(self.style.ERROR('ERROR: No organizations found. Please run seed_dev_data first.'))
            return False

        return True

    def clear_test_data(self):
        """Clear only test applicant data (users with email containing 'applicant' and not from seed_dev_data)."""
        from applications.models import Application, NodeResolution
        from core.models import UserRole

        # Find test applicants (exclude the ones from seed_dev_data)
        test_applicants = User.objects.filter(
            email__icontains='testapplicant'
        ).filter(is_superuser=False)

        # Get their applications
        test_apps = Application.objects.filter(applicant__in=test_applicants)

        # Delete node resolutions for their applications
        nr_count = NodeResolution.objects.filter(application__in=test_apps).count()
        NodeResolution.objects.filter(application__in=test_apps).delete()

        # Delete their applications
        app_count = test_apps.count()
        test_apps.delete()

        # Delete their roles
        UserRole.objects.filter(user__in=test_applicants).delete()

        # Delete the users
        user_count = test_applicants.count()
        test_applicants.delete()

        self.stdout.write(self.style.WARNING(f'  → Deleted {user_count} test applicants, {app_count} applications, {nr_count} node resolutions'))

    def create_applicants(self):
        """Create test applicants with diverse backgrounds."""
        from core.models import Organization, UserRole

        applicants = []
        password = 'testpass123'

        # Get organizations
        orgs = list(Organization.objects.all())
        if not orgs:
            self.stdout.write(self.style.ERROR('No organizations found!'))
            return []

        # Applicant data: (email, first_name, last_name, position)
        applicant_data = [
            ('testapplicant1@university.es', 'María', 'García', 'PhD Student'),
            ('testapplicant2@research.de', 'Thomas', 'Schmidt', 'Postdoctoral Researcher'),
            ('testapplicant3@hospital.fr', 'Claire', 'Dubois', 'Clinical Researcher'),
            ('testapplicant4@biotech.com', 'John', 'Williams', 'Principal Investigator'),
            ('testapplicant5@institute.it', 'Lucia', 'Rossi', 'Research Scientist'),
            ('testapplicant6@university.uk', 'David', 'Brown', 'Associate Professor'),
            ('testapplicant7@lab.ch', 'Anna', 'Mueller', 'Lab Director'),
        ]

        for i, (email, first, last, position) in enumerate(applicant_data):
            # Rotate through organizations
            org = orgs[i % len(orgs)]

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'position': position,
                    'organization': org,
                    'is_active': True,
                }
            )

            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(f'  → Created applicant: {email}')

                # Create applicant role
                UserRole.objects.get_or_create(
                    user=user,
                    role='applicant',
                    defaults={'is_active': True}
                )
            else:
                self.stdout.write(f'  → Applicant exists: {email}')

            applicants.append(user)

        return applicants

    def create_applications(self, applicants):
        """Create applications at various stages for comprehensive testing."""
        from applications.models import Application, RequestedAccess, FeasibilityReview, NodeResolution
        from evaluations.models import Evaluation
        from calls.models import Call
        from core.models import Equipment, Node, UserRole

        if not applicants:
            return

        # Get calls
        calls = list(Call.objects.all().order_by('-created_at'))
        if not calls:
            self.stdout.write(self.style.ERROR('No calls found!'))
            return

        # Prefer open call if available
        open_call = Call.objects.filter(status='open').first()
        call = open_call if open_call else calls[0]

        # Get equipment
        equipment_list = list(Equipment.objects.filter(is_active=True))
        if not equipment_list:
            self.stdout.write(self.style.ERROR('No equipment found!'))
            return

        # Get evaluators
        evaluators = list(User.objects.filter(
            roles__role='evaluator',
            roles__is_active=True
        ).distinct())

        # Get node coordinators
        node_coords = {}
        for node_role in UserRole.objects.filter(role='node_coordinator', is_active=True).select_related('node', 'user'):
            if node_role.node:
                node_coords[node_role.node.code] = node_role.user

        now = timezone.now()
        app_counter = 1

        # Helper function to set time to 23:59:59
        def aware_datetime(days_offset):
            """Create timezone-aware datetime with offset."""
            dt = now + timedelta(days=days_offset)
            date_only = dt.date()
            dt_with_time = datetime.combine(date_only, time(23, 59, 59))
            return timezone.make_aware(dt_with_time) if timezone.is_naive(dt_with_time) else dt_with_time

        # Application templates for different stages
        # Format: (status, needs_equipment, needs_feasibility, needs_evaluation, score, resolution, node_resolution_type)
        # node_resolution_type: None=no resolution, 'all_accept'=all nodes accept, 'mixed_waitlist'=accept+waitlist, 'any_reject'=one rejects
        stages = [
            # Applicant 1: Early stages
            ('draft', True, False, False, None, '', None),
            ('submitted', True, False, False, None, '', None),
            ('under_feasibility_review', True, True, False, None, '', None),

            # Applicant 2: Evaluation stages
            ('pending_evaluation', True, True, False, None, '', None),
            ('under_evaluation', True, True, True, None, '', None),  # 1 of 2 evaluations
            ('evaluated', True, True, True, Decimal('9.5'), '', None),  # Ready for node resolution

            # Applicant 3: Resolution outcomes (via node coordinator resolution)
            ('accepted', True, True, True, Decimal('10.5'), 'accepted', 'all_accept'),
            ('pending', True, True, True, Decimal('8.5'), 'pending', 'mixed_waitlist'),
            ('rejected', True, True, True, Decimal('4.0'), 'rejected', 'any_reject'),

            # Applicant 4: Acceptance workflow
            ('accepted', True, True, True, Decimal('11.0'), 'accepted', 'all_accept'),
            ('declined_by_applicant', True, True, True, Decimal('9.0'), 'accepted', 'all_accept'),

            # Applicant 5: Various scenarios
            ('rejected_feasibility', True, True, False, None, '', None),
            ('accepted', True, True, True, Decimal('10.0'), 'accepted', 'all_accept'),

            # Applicant 6: Edge cases
            ('under_evaluation', True, True, True, None, '', None),  # Both evaluations complete
            ('accepted', True, True, True, Decimal('8.0'), 'accepted', 'all_accept'),  # Below threshold but accepted

            # Applicant 7: Multi-equipment and competitive funding
            ('accepted', True, True, True, Decimal('11.5'), 'accepted', 'all_accept'),
            ('evaluated', True, True, True, Decimal('9.0'), '', None),  # Ready for node resolution (multi-node)
        ]

        for i, (status, needs_equip, needs_feas, needs_eval, score, resolution, node_res_type) in enumerate(stages):
            # Rotate through applicants
            applicant = applicants[i % len(applicants)]

            # Determine equipment (some single-node, some multi-node)
            # Multi-node for: every 5th app, OR apps that need mixed/reject node resolutions
            needs_multi_node = (i % 5 == 0) or node_res_type in ('mixed_waitlist', 'any_reject')
            if needs_multi_node and len(equipment_list) >= 2:
                # Get equipment from DIFFERENT nodes
                equip_items = []
                seen_nodes = set()
                for eq in equipment_list:
                    if eq.node.id not in seen_nodes:
                        equip_items.append(eq)
                        seen_nodes.add(eq.node.id)
                        if len(equip_items) >= 2:
                            break
                # Fallback if not enough different nodes
                if len(equip_items) < 2:
                    equip_items = equipment_list[:2]
            else:  # Single-node application
                equip_items = [equipment_list[i % len(equipment_list)]]

            # Create application
            app_code = f'TEST-APP-{app_counter:03d}'
            competitive_funding = (i % 4 == 0)  # Every 4th app has competitive funding

            # Specialization areas rotation
            spec_areas = ['preclinical', 'clinical', 'radiotracers']
            spec_area = spec_areas[i % len(spec_areas)]

            app = Application.objects.create(
                call=call,
                applicant=applicant,
                code=app_code,
                status=status,
                brief_description=f'Test application {app_code} - {status}',
                applicant_name=f'{applicant.first_name} {applicant.last_name}',
                applicant_entity=applicant.organization.name if applicant.organization else 'Test Organization',
                applicant_email=applicant.email,
                applicant_phone='+34 900 000 000',
                project_title=f'Research Project {app_counter}: {self.get_project_title(spec_area)}',
                project_code=f'PRJ-2026-{app_counter:04d}',
                funding_agency='Test Funding Agency' if competitive_funding else '',
                project_type='national',
                has_competitive_funding=competitive_funding,
                subject_area='bme',
                service_modality='full_assistance',
                specialization_area=spec_area,
                scientific_relevance=f'Test scientific relevance for {spec_area} research. High quality and original approach.',
                methodology_description=f'Test methodology for {spec_area}. Well-designed experimental protocols.',
                expected_contributions='Test expected contributions. Novel insights into the field.',
                impact_strengths='Test impact strengths. Strong potential for high-impact publications.',
                socioeconomic_significance='Test socioeconomic significance. Benefits to healthcare and research.',
                opportunity_criteria='Test opportunity criteria. Timely and addresses current research gaps.',
                technical_feasibility_confirmed=(status != 'draft'),
                data_consent=(status != 'draft'),
                final_score=score,
                resolution=resolution,
                submitted_at=aware_datetime(-10) if status != 'draft' else None,
            )

            self.stdout.write(f'  → Created {app_code}: {status}')

            # Add equipment requests
            if needs_equip:
                for equip in equip_items:
                    RequestedAccess.objects.create(
                        application=app,
                        equipment=equip,
                        hours_requested=16 + (i % 3) * 8  # 16, 24, or 32 hours
                    )

            # Add feasibility reviews
            if needs_feas:
                # Get unique nodes from equipment
                nodes_in_app = set(equip.node for equip in equip_items)
                for node in nodes_in_app:
                    if node.code in node_coords:
                        # For apps in "under_feasibility_review" status, leave reviewed_at as None
                        # For all other statuses, mark as completed
                        if status == 'under_feasibility_review':
                            # Pending review - don't set is_feasible or reviewed_at
                            FeasibilityReview.objects.create(
                                application=app,
                                node=node,
                                reviewer=node_coords[node.code],
                                is_feasible=None,
                                comments='',
                                reviewed_at=None
                            )
                        else:
                            # Completed review
                            is_feasible = (status != 'rejected_feasibility')
                            FeasibilityReview.objects.create(
                                application=app,
                                node=node,
                                reviewer=node_coords[node.code],
                                is_feasible=is_feasible,
                                comments='Test feasibility review' if is_feasible else 'Not technically feasible',
                                reviewed_at=aware_datetime(-8)
                            )

            # Add evaluations
            if needs_eval and evaluators:
                # Determine how many evaluations to create
                if status == 'under_evaluation' and i == 4:
                    # First under_evaluation: only 1 of 2 evaluations
                    num_evals = 1
                else:
                    # All others: 2 evaluations
                    num_evals = min(2, len(evaluators))

                for j in range(num_evals):
                    evaluator = evaluators[j % len(evaluators)]

                    # For 'under_evaluation' apps, leave scores as None so evaluations remain incomplete
                    # For other statuses with scores, fill them in
                    if score and status not in ['under_evaluation']:
                        # Generate individual criterion scores (0-2 scale, 6 criteria)
                        base_score = float(score) / 6
                        s1 = min(2, max(0, int(base_score) + (j % 2)))
                        s2 = min(2, max(0, int(base_score)))
                        s3 = min(2, max(0, int(base_score) + ((j+1) % 2)))
                        s4 = min(2, max(0, int(base_score)))
                        s5 = min(2, max(0, int(base_score)))
                        s6 = min(2, max(0, int(base_score)))
                        total = s1 + s2 + s3 + s4 + s5 + s6
                        recommendation = 'approved' if total >= 7 else 'denied'
                    else:
                        # Leave scores as None - evaluations are incomplete
                        s1 = s2 = s3 = s4 = s5 = s6 = None
                        total = None
                        recommendation = None

                    eval = Evaluation.objects.create(
                        application=app,
                        evaluator=evaluator,
                        score_quality_originality=s1,
                        score_methodology_design=s2,
                        score_expected_contributions=s3,
                        score_knowledge_advancement=s4,
                        score_social_economic_impact=s5,
                        score_exploitation_dissemination=s6,
                        recommendation=recommendation,
                        comments=f'Test evaluation by {evaluator.get_full_name()}',
                    )
                    # Note: Don't manually set completed_at - let the Evaluation model handle it
                    # The model auto-sets completed_at when all scores are filled in

            # Add node resolutions for applications that have gone through resolution
            if node_res_type and node_coords:
                nodes_in_app = list(set(equip.node for equip in equip_items))
                for j, node in enumerate(nodes_in_app):
                    if node.code in node_coords:
                        # Determine resolution based on node_res_type
                        if node_res_type == 'all_accept':
                            node_decision = 'accept'
                        elif node_res_type == 'mixed_waitlist':
                            # First node accepts, others waitlist
                            node_decision = 'accept' if j == 0 else 'waitlist'
                        elif node_res_type == 'any_reject':
                            # First node accepts, second rejects
                            node_decision = 'accept' if j == 0 else 'reject'
                        else:
                            node_decision = 'accept'

                        # Set hours_approved based on resolution
                        req_access_items = app.requested_access.filter(equipment__node=node)
                        for ra in req_access_items:
                            if node_decision == 'accept':
                                ra.hours_approved = ra.hours_requested
                            elif node_decision == 'waitlist':
                                ra.hours_approved = ra.hours_requested / 2  # Partial approval
                            else:
                                ra.hours_approved = Decimal('0')
                            ra.save()

                        NodeResolution.objects.create(
                            application=app,
                            node=node,
                            reviewer=node_coords[node.code],
                            resolution=node_decision,
                            comments=f'Test {node_decision} decision by {node.code}',
                            reviewed_at=aware_datetime(-5)
                        )

            app_counter += 1

    def get_project_title(self, spec_area):
        """Generate diverse project titles based on specialization area."""
        titles = {
            'preclinical': [
                'Novel MRI Techniques for Alzheimer\'s Disease Models',
                'PET Imaging of Tumor Microenvironment in Mouse Models',
                'Advanced Imaging of Neuroinflammation in Preclinical Studies',
                'Cardiac Function Assessment Using Multi-Modal Imaging',
            ],
            'clinical': [
                'Clinical Validation of New Cardiac Imaging Protocol',
                'Stroke Recovery Assessment Using Advanced MRI',
                'Oncological Response Monitoring with PET-CT',
                'Neurodegenerative Disease Progression Imaging Study',
            ],
            'radiotracers': [
                'Development of Novel PET Radiotracers for Inflammation',
                'Radiotracer Validation for Alzheimer\'s Biomarkers',
                'Synthesis and Testing of New Oncological Tracers',
                'Improved Radiotracers for Cardiac Imaging',
            ],
        }
        import random
        return random.choice(titles.get(spec_area, titles['preclinical']))

    def print_summary(self, applicants):
        """Print summary of created test data."""
        from applications.models import Application

        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('TEST APPLICANT ACCOUNTS'))
        self.stdout.write('='*70)
        self.stdout.write('All accounts use password: testpass123')
        self.stdout.write('-'*70)

        for applicant in applicants:
            app_count = Application.objects.filter(applicant=applicant).count()
            statuses = Application.objects.filter(applicant=applicant).values_list('status', flat=True)
            status_summary = ', '.join(set(statuses))
            self.stdout.write(f'  {applicant.email:35s} → {app_count} apps: {status_summary}')

        total_apps = Application.objects.filter(applicant__in=applicants).count()
        self.stdout.write('-'*70)
        self.stdout.write(f'Total applications created: {total_apps}')
        self.stdout.write('='*70)

        # Summary by status
        self.stdout.write('\nApplications by status:')
        from applications.models import Application
        from django.db.models import Count

        status_counts = Application.objects.filter(
            applicant__in=applicants
        ).values('status').annotate(count=Count('status')).order_by('-count')

        for item in status_counts:
            status_label = dict(Application.APPLICATION_STATUSES).get(item['status'], item['status'])
            self.stdout.write(f'  {status_label:30s}: {item["count"]}')

        self.stdout.write('\n' + '='*70)
        self.stdout.write('\nYou can now:')
        self.stdout.write('  1. Login as any applicant at http://localhost:8000/accounts/login/')
        self.stdout.write('  2. Test different workflow stages with different users')
        self.stdout.write('  3. View applications in various states in the admin panel')
        self.stdout.write('='*70 + '\n')
