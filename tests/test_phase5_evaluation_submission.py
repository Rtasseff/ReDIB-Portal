#!/usr/bin/env python
"""
Independent validation test for Phase 5: Evaluation Submission & Completion.

Tests:
1. Evaluation form submission with valid scores
2. Automatic score calculation (average of 5 criteria)
3. Automatic completion timestamp
4. Blind evaluation (applicant identity hidden)
5. Edit permissions (before/after deadline, before/after completion)
6. State transition (under_evaluation → evaluated)
7. Coordinator notification when all evaluations complete
8. Partial completion scenarios
9. Score validation (1-5 range)
10. Form validation
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
from calls.models import Call, CallEquipmentAllocation
from applications.models import Application, RequestedAccess
from evaluations.models import Evaluation
from evaluations.forms import EvaluationForm
from evaluations.utils import (
    check_and_transition_application,
    get_blind_application_data,
    is_evaluation_locked
)
from communications.models import EmailLog
from core.models import Node, Equipment, Organization, UserRole

User = get_user_model()


class Phase5Tester:
    """Test Phase 5: Evaluation Submission & Completion"""

    def __init__(self):
        self.test_results = []
        self.call = None
        self.application = None
        self.evaluators = []
        self.evaluations = []
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
        print("CLEANUP: Removing previous Phase 5 test data")
        print("="*60)

        Evaluation.objects.filter(application__code__startswith='PHASE5-TEST').delete()
        Application.objects.filter(code__startswith='PHASE5-TEST').delete()
        Call.objects.filter(code__startswith='PHASE5-TEST').delete()
        EmailLog.objects.filter(subject__contains='PHASE5-TEST').delete()

        User.objects.filter(email__contains='phase5.test').delete()
        Organization.objects.filter(name__contains='Phase 5 Test').delete()

        print("✓ Cleanup complete")

    def setup_test_environment(self):
        """Create test environment with evaluators and applications"""
        print("\n" + "="*60)
        print("SETUP: Creating test environment")
        print("="*60)

        # Create test organizations
        for i in range(2):
            org, _ = Organization.objects.get_or_create(
                name=f'Phase 5 Test Org {i+1}',
                defaults={'country': 'Spain', 'organization_type': 'university'}
            )
            self.organizations[i+1] = org

        # Create evaluators
        for i in range(3):
            email = f'evaluator{i+1}.phase5.test@redib.test'
            evaluator, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': f'Evaluator',
                    'last_name': f'{i+1}',
                    'organization': self.organizations[1]
                }
            )
            if created:
                evaluator.set_password('testpass123')
                evaluator.save()

            UserRole.objects.get_or_create(
                user=evaluator,
                role='evaluator',
                defaults={'is_active': True}
            )

            self.evaluators.append(evaluator)

        # Create applicant
        self.applicant = User.objects.create(
            email='applicant.phase5.test@redib.test',
            first_name='Test',
            last_name='Applicant',
            organization=self.organizations[2]
        )

        # Create coordinator
        self.coordinator = User.objects.create(
            email='coordinator.phase5.test@redib.test',
            first_name='Test',
            last_name='Coordinator'
        )
        UserRole.objects.create(
            user=self.coordinator,
            role='coordinator',
            is_active=True
        )

        # Get or create node and equipment
        node, _ = Node.objects.get_or_create(
            code='CICBIO',
            defaults={'name': 'CIC biomaGUNE', 'location': 'San Sebastián'}
        )

        equipment, _ = Equipment.objects.get_or_create(
            node=node,
            name='MRI 7T Phase5',
            defaults={'category': 'mri', 'is_essential': True}
        )

        # Create test call
        now = timezone.now()
        self.call, created = Call.objects.get_or_create(
            code='PHASE5-TEST-CALL-01',
            defaults={
                'title': 'Phase 5 Test Call',
                'status': 'open',
                'submission_start': now - timedelta(days=30),
                'submission_end': now - timedelta(days=5),
                'evaluation_deadline': now + timedelta(days=10),
                'execution_start': now + timedelta(days=60),
                'execution_end': now + timedelta(days=180),
                'description': 'Test call for Phase 5'
            }
        )

        CallEquipmentAllocation.objects.get_or_create(
            call=self.call,
            equipment=equipment,
            defaults={'hours_offered': 100}
        )

        # Create test application in UNDER_EVALUATION status
        self.application, created = Application.objects.get_or_create(
            code='PHASE5-TEST-APP-001',
            defaults={
                'call': self.call,
                'applicant': self.applicant,
                'applicant_name': 'Test Applicant',
                'applicant_entity': 'Test Organization',
                'applicant_email': 'applicant@test.com',
                'brief_description': 'Phase 5 test application',
                'status': 'under_evaluation',
                'submitted_at': now - timedelta(days=5),
                'scientific_relevance': 'Test scientific relevance content',
                'methodology_description': 'Test methodology content',
                'expected_contributions': 'Test expected contributions',
                'impact_strengths': 'Test impact content',
                'opportunity_criteria': 'Test opportunity content',
            }
        )

        if created:
            RequestedAccess.objects.create(
                application=self.application,
                equipment=equipment,
                hours_requested=10
            )

        # Create evaluations (assigned but not completed)
        for i, evaluator in enumerate(self.evaluators[:2]):  # Only 2 evaluators
            evaluation, created = Evaluation.objects.get_or_create(
                application=self.application,
                evaluator=evaluator
            )
            self.evaluations.append(evaluation)

        print(f"✓ Created {len(self.evaluators)} evaluators")
        print(f"✓ Created application: {self.application.code}")
        print(f"✓ Created {len(self.evaluations)} evaluations")

    def test_1_form_validation(self):
        """Test evaluation form validation"""
        print("\n" + "="*60)
        print("TEST 1: Evaluation form validation")
        print("="*60)

        evaluation = self.evaluations[0]

        # Test valid form
        form_data = {
            'score_relevance': 4,
            'score_methodology': 5,
            'score_contributions': 3,
            'score_impact': 4,
            'score_opportunity': 5,
            'comments': 'Test evaluation comments'
        }

        form = EvaluationForm(data=form_data, instance=evaluation)
        success = form.is_valid()
        self.log_test("1.1", success, "Valid form data passes validation")

        # Test missing score
        invalid_data = form_data.copy()
        invalid_data['score_relevance'] = None
        form = EvaluationForm(data=invalid_data, instance=evaluation)
        success = not form.is_valid()
        self.log_test("1.2", success, "Form rejects missing score")

        # Test out-of-range score (should be caught by model validators)
        invalid_data = form_data.copy()
        invalid_data['score_relevance'] = 6
        form = EvaluationForm(data=invalid_data, instance=evaluation)
        success = not form.is_valid()
        self.log_test("1.3", success, "Form rejects out-of-range score (>5)")

    def test_2_score_calculation(self):
        """Test automatic score calculation"""
        print("\n" + "="*60)
        print("TEST 2: Automatic score calculation")
        print("="*60)

        evaluation = self.evaluations[0]

        # Set scores
        evaluation.score_relevance = 4
        evaluation.score_methodology = 5
        evaluation.score_contributions = 3
        evaluation.score_impact = 4
        evaluation.score_opportunity = 4
        evaluation.save()

        # Calculate expected average
        expected_avg = (4 + 5 + 3 + 4 + 4) / 5.0  # = 4.0

        success = float(evaluation.total_score) == expected_avg
        self.log_test(
            "2.1",
            success,
            "Total score calculated correctly",
            expected=expected_avg,
            actual=float(evaluation.total_score) if evaluation.total_score else None
        )

        # Test completion timestamp
        success = evaluation.completed_at is not None
        self.log_test("2.2", success, "completed_at timestamp set automatically")

        # Test is_complete property
        success = evaluation.is_complete
        self.log_test("2.3", success, "is_complete property returns True")

    def test_3_blind_evaluation(self):
        """Test blind evaluation data (applicant identity hidden)"""
        print("\n" + "="*60)
        print("TEST 3: Blind evaluation (applicant identity hidden)")
        print("="*60)

        blind_data = get_blind_application_data(self.application)

        # Check that identifying info is NOT present
        success = 'applicant_name' not in blind_data
        self.log_test("3.1", success, "Applicant name is hidden")

        success = 'applicant_entity' not in blind_data
        self.log_test("3.2", success, "Applicant entity is hidden")

        success = 'applicant_email' not in blind_data
        self.log_test("3.3", success, "Applicant email is hidden")

        # Check that scientific content IS present
        success = 'scientific_relevance' in blind_data
        self.log_test("3.4", success, "Scientific content is visible")

        success = blind_data['scientific_relevance'] == self.application.scientific_relevance
        self.log_test("3.5", success, "Scientific content matches application")

    def test_4_lock_after_completion(self):
        """Test that evaluation locks after completion"""
        print("\n" + "="*60)
        print("TEST 4: Lock evaluation after completion")
        print("="*60)

        evaluation = self.evaluations[0]

        # Evaluation is complete (from test 2)
        is_locked, reason = is_evaluation_locked(evaluation)

        success = is_locked
        self.log_test("4.1", success, "Completed evaluation is locked")

        success = reason == 'completed'
        self.log_test("4.2", success, "Lock reason is 'completed'")

    def test_5_lock_after_deadline(self):
        """Test that evaluation locks after deadline"""
        print("\n" + "="*60)
        print("TEST 5: Lock evaluation after deadline")
        print("="*60)

        # Create a call with past deadline
        past_call = Call.objects.create(
            code='PHASE5-TEST-PAST-CALL',
            title='Past deadline call',
            status='closed',
            submission_start=timezone.now() - timedelta(days=40),
            submission_end=timezone.now() - timedelta(days=30),
            evaluation_deadline=timezone.now() - timedelta(days=1),  # Past
            execution_start=timezone.now() + timedelta(days=60),
            execution_end=timezone.now() + timedelta(days=180),
            description='Past deadline test'
        )

        past_app = Application.objects.create(
            code='PHASE5-TEST-PAST-APP',
            call=past_call,
            applicant=self.applicant,
            brief_description='Past deadline test',
            status='under_evaluation',
            submitted_at=timezone.now() - timedelta(days=30)
        )

        past_eval = Evaluation.objects.create(
            application=past_app,
            evaluator=self.evaluators[0]
        )

        is_locked, reason = is_evaluation_locked(past_eval)

        success = is_locked
        self.log_test("5.1", success, "Evaluation locked after deadline")

        success = reason == 'past_deadline'
        self.log_test("5.2", success, "Lock reason is 'past_deadline'")

    def test_6_partial_completion(self):
        """Test partial evaluation completion (not all evaluators done)"""
        print("\n" + "="*60)
        print("TEST 6: Partial completion (1 of 2 evaluations complete)")
        print("="*60)

        # First evaluation is complete (from test 2)
        # Second evaluation is still pending

        result = check_and_transition_application(self.application)

        success = result['total'] == 2
        self.log_test("6.1", success, "Correct total evaluations count", expected=2, actual=result['total'])

        success = result['completed'] == 1
        self.log_test("6.2", success, "Correct completed count", expected=1, actual=result['completed'])

        success = not result['all_complete']
        self.log_test("6.3", success, "all_complete is False (partial completion)")

        success = not result['transitioned']
        self.log_test("6.4", success, "Application did NOT transition (waiting for all)")

        # Status should still be under_evaluation
        self.application.refresh_from_db()
        success = self.application.status == 'under_evaluation'
        self.log_test("6.5", success, "Application status still 'under_evaluation'")

    def test_7_full_completion_and_transition(self):
        """Test all evaluations complete and state transition"""
        print("\n" + "="*60)
        print("TEST 7: All evaluations complete → state transition")
        print("="*60)

        # Complete the second evaluation
        evaluation = self.evaluations[1]
        evaluation.score_relevance = 5
        evaluation.score_methodology = 4
        evaluation.score_contributions = 5
        evaluation.score_impact = 5
        evaluation.score_opportunity = 4
        evaluation.save()

        # Check completion
        result = check_and_transition_application(self.application)

        success = result['all_complete']
        self.log_test("7.1", success, "all_complete is True")

        success = result['transitioned']
        self.log_test("7.2", success, "Application transitioned to 'evaluated'")

        # Refresh and check status
        self.application.refresh_from_db()
        success = self.application.status == 'evaluated'
        self.log_test("7.3", success, "Application status is 'evaluated'")

        # Check average score
        expected_avg = (4.0 + 4.6) / 2  # Average of both evaluations
        actual_avg = result.get('average_score')
        success = actual_avg is not None and abs(float(actual_avg) - expected_avg) < 0.01
        self.log_test("7.4", success, f"Average score calculated: {actual_avg:.2f}")

    def test_8_coordinator_notification(self):
        """Test coordinator notification email"""
        print("\n" + "="*60)
        print("TEST 8: Coordinator notification email")
        print("="*60)

        # Clear previous email logs
        EmailLog.objects.filter(template__template_type='evaluations_complete').delete()

        # Create new application and complete all evaluations
        test_app = Application.objects.create(
            code='PHASE5-TEST-APP-EMAIL',
            call=self.call,
            applicant=self.applicant,
            applicant_name='Email Test Applicant',
            brief_description='Email test',
            status='under_evaluation',
            submitted_at=timezone.now()
        )

        # Create and complete evaluations
        for evaluator in self.evaluators[:2]:
            evaluation = Evaluation.objects.create(
                application=test_app,
                evaluator=evaluator,
                score_relevance=4,
                score_methodology=4,
                score_contributions=4,
                score_impact=4,
                score_opportunity=4
            )

        # Trigger transition (which triggers notification)
        result = check_and_transition_application(test_app)

        # Check email logs
        email_logs = EmailLog.objects.filter(
            template__template_type='evaluations_complete',
            related_application_id=test_app.id
        )

        success = email_logs.count() >= 1
        self.log_test("8.1", success, "Coordinator notification email sent", expected=">=1", actual=email_logs.count())

        if email_logs.exists():
            log = email_logs.first()
            success = test_app.code in log.subject
            self.log_test("8.2", success, "Email subject contains application code")

    def test_9_application_status_transition(self):
        """Test application status transitions in assign_evaluators_to_call"""
        print("\n" + "="*60)
        print("TEST 9: Application status transitions")
        print("="*60)

        # Create application in PENDING_EVALUATION status
        pending_app = Application.objects.create(
            code='PHASE5-TEST-PENDING-APP',
            call=self.call,
            applicant=self.applicant,
            brief_description='Pending test',
            status='pending_evaluation',  # Start state
            submitted_at=timezone.now()
        )

        # Assign evaluators (which should transition to under_evaluation)
        from evaluations.tasks import assign_evaluators_to_call
        result = assign_evaluators_to_call(self.call.id, num_evaluators=2)

        # Refresh and check status
        pending_app.refresh_from_db()
        success = pending_app.status == 'under_evaluation'
        self.log_test(
            "9.1",
            success,
            "Application transitioned to 'under_evaluation' after evaluator assignment",
            expected='under_evaluation',
            actual=pending_app.status
        )

    def run_all_tests(self):
        """Run all Phase 5 tests"""
        print("\n" + "="*60)
        print("PHASE 5: EVALUATION SUBMISSION TEST SUITE")
        print("="*60)

        self.cleanup_test_data()
        self.setup_test_environment()

        self.test_1_form_validation()
        self.test_2_score_calculation()
        self.test_3_blind_evaluation()
        self.test_4_lock_after_completion()
        self.test_5_lock_after_deadline()
        self.test_6_partial_completion()
        self.test_7_full_completion_and_transition()
        self.test_8_coordinator_notification()
        self.test_9_application_status_transition()

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
    tester = Phase5Tester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
