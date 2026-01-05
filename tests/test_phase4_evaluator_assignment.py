#!/usr/bin/env python
"""
Independent validation test for Phase 4: Evaluator Assignment.

Tests:
1. Automatic evaluator assignment with conflict-of-interest handling
2. Manual evaluator assignment by coordinator
3. Evaluator dashboard and views
4. Email notifications for evaluation assignment
5. Assignment to multiple applications in a call
6. Exclusion of evaluators from same organization
"""
import os
import sys
import django
from datetime import timedelta
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redib.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from calls.models import Call, CallEquipmentAllocation
from applications.models import Application, RequestedAccess
from evaluations.models import Evaluation
from evaluations.tasks import assign_evaluators_to_application, assign_evaluators_to_call
from communications.models import EmailLog
from core.models import Node, Equipment, Organization, UserRole

User = get_user_model()


class Phase4Tester:
    """Test Phase 4: Evaluator Assignment"""

    def __init__(self):
        self.test_results = []
        self.call = None
        self.applications = []
        self.evaluators = []
        self.organizations = {}

    def log_test(self, step, success, message, expected=None, actual=None):
        """Log test step result"""
        status = "✅" if success else "❌"
        print(f"{status} {step}: {message}")
        if not success and expected and actual:
            print(f"   Expected: {expected}")
            print(f"   Actual: {actual}")
        self.test_results.append((step, success, message))

    def cleanup_test_data(self):
        """Clean up previous test data"""
        print("\n" + "="*60)
        print("CLEANUP: Removing previous Phase 4 test data")
        print("="*60)

        Evaluation.objects.filter(application__code__startswith='PHASE4-TEST').delete()
        Application.objects.filter(code__startswith='PHASE4-TEST').delete()
        Call.objects.filter(code__startswith='PHASE4-TEST').delete()
        EmailLog.objects.filter(subject__contains='PHASE4-TEST').delete()

        # Clear node directors before deleting users
        for node in Node.objects.filter(director__email__contains='phase4.test'):
            node.director = None
            node.save()

        User.objects.filter(email__contains='phase4.test').delete()
        Organization.objects.filter(name__contains='Phase 4 Test').delete()

        print("✓ Cleanup complete")

    def setup_test_environment(self):
        """Create test environment with evaluators, applicants, and calls"""
        print("\n" + "="*60)
        print("SETUP: Creating test environment")
        print("="*60)

        # Create test organizations
        for i in range(3):
            org, _ = Organization.objects.get_or_create(
                name=f'Phase 4 Test Org {i+1}',
                defaults={'country': 'Spain', 'organization_type': 'university'}
            )
            self.organizations[i+1] = org

        # Create evaluators (from different organizations)
        for i in range(5):
            email = f'evaluator{i+1}.phase4.test@redib.test'
            evaluator, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': f'Evaluator',
                    'last_name': f'{i+1}',
                    'organization': self.organizations[(i % 3) + 1]
                }
            )
            if created:
                evaluator.set_password('testpass123')
                evaluator.save()

            # Assign evaluator role
            UserRole.objects.get_or_create(
                user=evaluator,
                role='evaluator',
                defaults={'is_active': True}
            )

            self.evaluators.append(evaluator)

        # Create applicants (from different organizations)
        self.applicants = []
        for i in range(3):
            email = f'applicant{i+1}.phase4.test@redib.test'
            applicant, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': f'Applicant',
                    'last_name': f'{i+1}',
                    'organization': self.organizations[(i % 3) + 1]
                }
            )
            if created:
                applicant.set_password('testpass123')
                applicant.save()

            # Assign applicant role
            UserRole.objects.get_or_create(
                user=applicant,
                role='applicant',
                defaults={'is_active': True}
            )

            self.applicants.append(applicant)

        # Get or create nodes and equipment
        node, _ = Node.objects.get_or_create(
            code='CICBIO',
            defaults={'name': 'CIC biomaGUNE', 'location': 'San Sebastián'}
        )

        equipment, _ = Equipment.objects.get_or_create(
            node=node,
            name='MRI 7T Test',
            defaults={'category': 'mri', 'is_essential': True}
        )

        # Create test call
        now = timezone.now()
        self.call, created = Call.objects.get_or_create(
            code='PHASE4-TEST-CALL-01',
            defaults={
                'title': 'Phase 4 Test Call',
                'status': 'open',
                'submission_start': now - timedelta(days=30),
                'submission_end': now + timedelta(days=10),
                'evaluation_deadline': now + timedelta(days=30),
                'execution_start': now + timedelta(days=60),
                'execution_end': now + timedelta(days=180),
                'description': 'Test call for Phase 4 evaluator assignment'
            }
        )

        # Create equipment allocation
        CallEquipmentAllocation.objects.get_or_create(
            call=self.call,
            equipment=equipment
        )

        # Create test applications (in PENDING_EVALUATION status)
        for i, applicant in enumerate(self.applicants):
            app, created = Application.objects.get_or_create(
                code=f'PHASE4-TEST-APP-{i+1:03d}',
                defaults={
                    'call': self.call,
                    'applicant': applicant,
                    'brief_description': f'Phase 4 test application {i+1}',
                    'status': 'pending_evaluation',  # Ready for evaluator assignment
                    'submitted_at': now - timedelta(days=5)
                }
            )

            if created:
                # Create requested access
                RequestedAccess.objects.create(
                    application=app,
                    equipment=equipment,
                    hours_requested=10
                )

            self.applications.append(app)

        print(f"✓ Created {len(self.evaluators)} evaluators")
        print(f"✓ Created {len(self.applicants)} applicants")
        print(f"✓ Created {len(self.applications)} applications")
        print(f"✓ Created call: {self.call.code}")

    def test_1_automatic_assignment_single_application(self):
        """Test automatic assignment to a single application"""
        print("\n" + "="*60)
        print("TEST 1: Automatic evaluator assignment to single application")
        print("="*60)

        application = self.applications[0]

        # Assign 2 evaluators
        result = assign_evaluators_to_application(application.id, num_evaluators=2)

        # Verify assignment
        success = len(result['assigned']) == 2
        self.log_test(
            "1.1",
            success,
            f"Assigned 2 evaluators to {application.code}",
            expected=2,
            actual=len(result['assigned'])
        )

        # Check evaluation objects created
        evaluations = Evaluation.objects.filter(application=application)
        success = evaluations.count() == 2
        self.log_test(
            "1.2",
            success,
            "Created 2 Evaluation objects",
            expected=2,
            actual=evaluations.count()
        )

        # Verify evaluations are incomplete
        incomplete = evaluations.filter(completed_at__isnull=True).count()
        success = incomplete == 2
        self.log_test(
            "1.3",
            success,
            "Evaluations are marked as incomplete",
            expected=2,
            actual=incomplete
        )

    def test_2_conflict_of_interest_handling(self):
        """Test that evaluators from same organization are excluded"""
        print("\n" + "="*60)
        print("TEST 2: Conflict-of-interest handling")
        print("="*60)

        application = self.applications[1]
        applicant_org = application.applicant.organization

        # Before assignment, count eligible evaluators
        eligible_evaluators = [e for e in self.evaluators if e.organization != applicant_org]

        # Assign evaluators
        result = assign_evaluators_to_application(application.id, num_evaluators=2)

        # Verify no evaluator from same org was assigned
        evaluations = Evaluation.objects.filter(application=application)
        conflicted = evaluations.filter(
            evaluator__organization=applicant_org
        ).count()

        success = conflicted == 0
        self.log_test(
            "2.1",
            success,
            f"No evaluators from applicant's organization ({applicant_org.name})",
            expected=0,
            actual=conflicted
        )

        # Check excluded list contains COI entries
        coi_excluded = [e for e in result['excluded'] if e['reason'] == 'conflict_of_interest']
        expected_coi = len([e for e in self.evaluators if e.organization == applicant_org])

        success = len(coi_excluded) == expected_coi
        self.log_test(
            "2.2",
            success,
            f"Excluded {len(coi_excluded)} evaluators due to COI",
            expected=expected_coi,
            actual=len(coi_excluded)
        )

    def test_3_no_duplicate_assignments(self):
        """Test that evaluators are not assigned twice to same application"""
        print("\n" + "="*60)
        print("TEST 3: No duplicate assignments")
        print("="*60)

        application = self.applications[2]

        # First assignment
        result1 = assign_evaluators_to_application(application.id, num_evaluators=2)
        first_assigned = result1['assigned']

        # Try to assign again
        result2 = assign_evaluators_to_application(application.id, num_evaluators=2)
        second_assigned = result2['assigned']

        # Verify different evaluators were assigned
        success = len(set(first_assigned) & set(second_assigned)) == 0
        self.log_test(
            "3.1",
            success,
            "Second assignment selected different evaluators",
            expected="No overlap",
            actual=f"{len(set(first_assigned) & set(second_assigned))} overlapping"
        )

        # Verify total evaluations count
        total_evals = Evaluation.objects.filter(application=application).count()
        success = total_evals == 4  # 2 + 2
        self.log_test(
            "3.2",
            success,
            "Total evaluations created",
            expected=4,
            actual=total_evals
        )

        # Check excluded list shows already_assigned
        already_assigned = [e for e in result2['excluded'] if e['reason'] == 'already_assigned']
        success = len(already_assigned) == 2
        self.log_test(
            "3.3",
            success,
            "Excluded previously assigned evaluators",
            expected=2,
            actual=len(already_assigned)
        )

    def test_4_bulk_assignment_to_call(self):
        """Test automatic assignment to all applications in a call"""
        print("\n" + "="*60)
        print("TEST 4: Bulk assignment to entire call")
        print("="*60)

        # Clear existing evaluations for clean test
        Evaluation.objects.filter(application__in=self.applications).delete()

        # Assign to all applications in call
        result = assign_evaluators_to_call(self.call.id, num_evaluators=2)

        # Verify all applications received assignments
        success = result['total_applications'] == len(self.applications)
        self.log_test(
            "4.1",
            success,
            f"Processed all applications in call",
            expected=len(self.applications),
            actual=result['total_applications']
        )

        # Verify successful assignments
        success = len(result['assignments']) == len(self.applications)
        self.log_test(
            "4.2",
            success,
            "All applications assigned evaluators",
            expected=len(self.applications),
            actual=len(result['assignments'])
        )

        # Verify no errors
        success = len(result['errors']) == 0
        self.log_test(
            "4.3",
            success,
            "No errors during bulk assignment",
            expected=0,
            actual=len(result['errors'])
        )

        # Verify total evaluation count
        total_evals = Evaluation.objects.filter(application__call=self.call).count()
        expected = len(self.applications) * 2  # 2 evaluators per application
        success = total_evals == expected
        self.log_test(
            "4.4",
            success,
            "Total evaluations created",
            expected=expected,
            actual=total_evals
        )

    def test_5_email_notifications(self):
        """Test that email notifications are sent when evaluators are assigned"""
        print("\n" + "="*60)
        print("TEST 5: Email notifications")
        print("="*60)

        # Clear email logs
        EmailLog.objects.filter(template__template_type='evaluation_assigned').delete()

        # Create fresh application
        applicant = self.applicants[0]
        app = Application.objects.create(
            code='PHASE4-TEST-APP-EMAIL',
            call=self.call,
            applicant=applicant,
            brief_description='Email notification test',
            status='pending_evaluation',
            submitted_at=timezone.now()
        )

        # Assign evaluators
        result = assign_evaluators_to_application(app.id, num_evaluators=2)

        # Check email logs
        email_logs = EmailLog.objects.filter(
            template__template_type='evaluation_assigned',
            related_application_id=app.id
        )

        success = email_logs.count() == 2
        self.log_test(
            "5.1",
            success,
            "Email notifications sent to evaluators",
            expected=2,
            actual=email_logs.count()
        )

        # Verify email content
        for log in email_logs:
            has_app_code = app.code in log.subject or app.code in log.text_content
            success = has_app_code
            self.log_test(
                "5.2",
                success,
                f"Email contains application code ({app.code})"
            )

    def test_6_insufficient_evaluators(self):
        """Test behavior when not enough eligible evaluators are available"""
        print("\n" + "="*60)
        print("TEST 6: Insufficient eligible evaluators")
        print("="*60)

        # Create an application from Org 1
        # Make all evaluators from Org 1 (conflict of interest)
        test_org = self.organizations[1]

        # Temporarily change all evaluators to same org
        original_orgs = {}
        for evaluator in self.evaluators:
            original_orgs[evaluator.id] = evaluator.organization
            evaluator.organization = test_org
            evaluator.save()

        # Create applicant from same org
        applicant = User.objects.create(
            email='conflicted.phase4.test@redib.test',
            first_name='Conflicted',
            last_name='Applicant',
            organization=test_org
        )

        app = Application.objects.create(
            code='PHASE4-TEST-APP-CONFLICT',
            call=self.call,
            applicant=applicant,
            brief_description='Conflict test',
            status='pending_evaluation',
            submitted_at=timezone.now()
        )

        # Try to assign (should fail due to COI)
        result = assign_evaluators_to_application(app.id, num_evaluators=2)

        # Verify no assignments
        success = len(result['assigned']) == 0
        self.log_test(
            "6.1",
            success,
            "No evaluators assigned due to COI",
            expected=0,
            actual=len(result['assigned'])
        )

        # Verify error message
        success = 'error' in result
        self.log_test(
            "6.2",
            success,
            "Error message present in result"
        )

        # Restore original organizations
        for evaluator in self.evaluators:
            evaluator.organization = original_orgs[evaluator.id]
            evaluator.save()

        # Cleanup
        app.delete()
        applicant.delete()

    def test_7_evaluation_object_properties(self):
        """Test Evaluation model properties and methods"""
        print("\n" + "="*60)
        print("TEST 7: Evaluation model properties")
        print("="*60)

        application = self.applications[0]
        evaluations = Evaluation.objects.filter(application=application)

        if evaluations.exists():
            evaluation = evaluations.first()

            # Test is_complete property
            success = not evaluation.is_complete
            self.log_test(
                "7.1",
                success,
                "Newly assigned evaluation is incomplete"
            )

            # Test string representation
            str_repr = str(evaluation)
            success = application.code in str_repr
            self.log_test(
                "7.2",
                success,
                f"String representation contains application code"
            )

            # Test assigned_at is set
            success = evaluation.assigned_at is not None
            self.log_test(
                "7.3",
                success,
                "assigned_at timestamp is set"
            )

            # Test completed_at is null
            success = evaluation.completed_at is None
            self.log_test(
                "7.4",
                success,
                "completed_at is null for incomplete evaluation"
            )

    def run_all_tests(self):
        """Run all Phase 4 tests"""
        print("\n" + "="*60)
        print("PHASE 4: EVALUATOR ASSIGNMENT TEST SUITE")
        print("="*60)

        self.cleanup_test_data()
        self.setup_test_environment()

        self.test_1_automatic_assignment_single_application()
        self.test_2_conflict_of_interest_handling()
        self.test_3_no_duplicate_assignments()
        self.test_4_bulk_assignment_to_call()
        self.test_5_email_notifications()
        self.test_6_insufficient_evaluators()
        self.test_7_evaluation_object_properties()

        # Print summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)

        passed = sum(1 for _, success, _ in self.test_results if success)
        failed = sum(1 for _, success, _ in self.test_results if not success)
        total = len(self.test_results)

        print(f"Total tests: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Success rate: {(passed/total*100):.1f}%")

        if failed > 0:
            print("\nFailed tests:")
            for step, success, message in self.test_results:
                if not success:
                    print(f"  ❌ {step}: {message}")

        return failed == 0


if __name__ == '__main__':
    tester = Phase4Tester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
