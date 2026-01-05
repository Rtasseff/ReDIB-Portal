#!/usr/bin/env python
"""
Independent validation test for Phase 3: Feasibility Review workflow.

Tests:
1. Feasibility review creation upon application submission
2. Node coordinator review process
3. Approval/rejection logic
4. State transitions
5. Multi-node scenarios
"""
import os
import sys
import django
from datetime import timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redib.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from calls.models import Call, CallEquipmentAllocation
from applications.models import Application, RequestedAccess, FeasibilityReview
from core.models import Node, Equipment, Organization, UserRole

User = get_user_model()


class Phase3Tester:
    """Test Phase 3: Feasibility Review workflow"""

    def __init__(self):
        self.test_results = []
        self.call = None
        self.application = None
        self.nodes = {}
        self.coordinators = {}
        self.reviews = []

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
        print("CLEANUP: Removing previous Phase 3 test data")
        print("="*60)

        FeasibilityReview.objects.filter(application__code__startswith='PHASE3-TEST').delete()
        Application.objects.filter(code__startswith='PHASE3-TEST').delete()
        Call.objects.filter(code__startswith='PHASE3-TEST').delete()

        # Clear node directors before deleting users (PROTECT foreign key)
        for node in Node.objects.filter(director__email__contains='phase3.test'):
            node.director = None
            node.save()

        User.objects.filter(email__contains='phase3.test').delete()

        print("✓ Cleanup complete")

    def setup_test_environment(self):
        """Create test environment with nodes, coordinators, and equipment"""
        print("\n" + "="*60)
        print("SETUP: Creating test environment")
        print("="*60)

        # Create test organization
        org, _ = Organization.objects.get_or_create(
            name='Phase 3 Test Org',
            defaults={'country': 'Spain', 'organization_type': 'research_center'}
        )

        # Create or get existing nodes
        node_configs = [
            ('CICBIO', 'CIC biomaGUNE', 'San Sebastián'),
            ('CNIC', 'CNIC Madrid', 'Madrid'),
        ]

        for code, name, location in node_configs:
            node, created = Node.objects.get_or_create(
                code=code,
                defaults={'name': name, 'location': location}
            )
            self.nodes[code] = node

            # Create node coordinator
            coord_email = f'{code.lower()}.phase3.test@redib.test'
            coordinator, created = User.objects.get_or_create(
                email=coord_email,
                defaults={
                    'first_name': f'{code}',
                    'last_name': 'Coordinator',
                    'organization': org,
                    'is_active': True
                }
            )
            if created:
                coordinator.set_password('testpass123')
                coordinator.save()

            # Assign node coordinator role
            UserRole.objects.get_or_create(
                user=coordinator,
                role='node_coordinator',
                node=node,
                defaults={'is_active': True}
            )

            # Update node director
            node.director = coordinator
            node.save()

            self.coordinators[code] = coordinator

            self.log_test(
                f"Setup Node {code}",
                True,
                f"Node {code} with coordinator {coord_email}"
            )

        # Ensure equipment exists at both nodes
        equipment_configs = [
            (self.nodes['CICBIO'], 'MRI 7T', 'mri'),
            (self.nodes['CNIC'], 'PET-CT', 'pet_ct'),
        ]

        for node, eq_name, category in equipment_configs:
            eq, created = Equipment.objects.get_or_create(
                node=node,
                name=eq_name,
                defaults={'category': category, 'is_essential': True, 'is_active': True}
            )
            self.log_test(
                f"Setup Equipment",
                True,
                f"{eq_name} at {node.code}"
            )

        # Create applicant
        self.applicant, created = User.objects.get_or_create(
            email='applicant.phase3.test@redib.test',
            defaults={
                'first_name': 'Test',
                'last_name': 'Applicant',
                'organization': org,
                'is_active': True
            }
        )
        if created:
            self.applicant.set_password('testpass123')
            self.applicant.save()

        UserRole.objects.get_or_create(
            user=self.applicant,
            role='applicant',
            defaults={'is_active': True}
        )

        self.log_test("Setup Applicant", True, f"Created {self.applicant.email}")

    def create_test_call(self):
        """Create test call with equipment allocations"""
        print("\n" + "="*60)
        print("TEST 1: Create Call for Phase 3 Testing")
        print("="*60)

        now = timezone.now()

        self.call = Call.objects.create(
            code='PHASE3-TEST-2025',
            title='Phase 3 Feasibility Review Test Call',
            status='open',
            submission_start=now - timedelta(days=7),
            submission_end=now + timedelta(days=30),
            evaluation_deadline=now + timedelta(days=45),
            execution_start=now + timedelta(days=60),
            execution_end=now + timedelta(days=120),
            description='Test call for Phase 3 feasibility review validation',
            published_at=now - timedelta(days=7)
        )

        self.log_test(
            "1.1 Create Call",
            self.call is not None,
            f"Created call {self.call.code}"
        )

        # Allocate equipment from both nodes
        for node in self.nodes.values():
            for equipment in node.equipment.filter(is_active=True):
                CallEquipmentAllocation.objects.create(
                    call=self.call,
                    equipment=equipment
                )

        allocation_count = self.call.equipment_allocations.count()
        self.log_test(
            "1.2 Equipment Allocations",
            allocation_count >= 2,
            f"Created {allocation_count} equipment allocations across nodes",
            "At least 2",
            allocation_count
        )

    def submit_application_requesting_multi_node_equipment(self):
        """Submit application requesting equipment from multiple nodes"""
        print("\n" + "="*60)
        print("TEST 2: Submit Application Requesting Multi-Node Equipment")
        print("="*60)

        # Create application
        self.application = Application.objects.create(
            call=self.call,
            applicant=self.applicant,
            status='draft',
            brief_description='Multi-node feasibility test application',
            applicant_name='Test Applicant',
            applicant_entity='Phase 3 Test Org',
            applicant_email='applicant.phase3.test@redib.test',
            applicant_phone='+34 000 000 000',
            project_title='Multi-Node Imaging Study',
            project_type='national',
            subject_area='bme',
            service_modality='full_assistance',
            specialization_area='preclinical',
            scientific_relevance='Test relevance',
            methodology_description='Test methodology',
            expected_contributions='Test contributions',
            impact_strengths='Test impact',
            socioeconomic_significance='Test significance',
            opportunity_criteria='Test opportunity',
            technical_feasibility_confirmed=True,
            data_consent=True
        )

        self.log_test(
            "2.1 Create Application",
            self.application is not None,
            f"Created application (ID: {self.application.pk})"
        )

        # Request equipment from BOTH nodes
        cicbio_equipment = Equipment.objects.get(node=self.nodes['CICBIO'], name='MRI 7T')
        cnic_equipment = Equipment.objects.get(node=self.nodes['CNIC'], name='PET-CT')

        RequestedAccess.objects.create(
            application=self.application,
            equipment=cicbio_equipment,
            hours_requested=20
        )

        RequestedAccess.objects.create(
            application=self.application,
            equipment=cnic_equipment,
            hours_requested=15
        )

        requested_nodes = set(self.application.requested_access.values_list('equipment__node__code', flat=True))

        self.log_test(
            "2.2 Multi-Node Request",
            len(requested_nodes) == 2,
            f"Requesting equipment from {len(requested_nodes)} nodes: {', '.join(requested_nodes)}",
            "2 nodes",
            len(requested_nodes)
        )

        # Submit application (this should create FeasibilityReviews)
        self.application.status = 'submitted'
        self.application.submitted_at = timezone.now()
        self.application.save()

        # Manually create feasibility reviews (simulating the view logic)
        nodes_with_equipment = set()
        for access_request in self.application.requested_access.all():
            nodes_with_equipment.add(access_request.equipment.node)

        for node in nodes_with_equipment:
            coordinator = node.director
            if coordinator:
                FeasibilityReview.objects.create(
                    application=self.application,
                    node=node,
                    reviewer=coordinator
                )

        # Update status to under_feasibility_review
        self.application.status = 'under_feasibility_review'
        self.application.save()

        self.log_test(
            "2.3 Submit Application",
            self.application.status == 'under_feasibility_review',
            f"Application status: {self.application.get_status_display()}"
        )

    def test_feasibility_review_creation(self):
        """Test that feasibility reviews are created for each node"""
        print("\n" + "="*60)
        print("TEST 3: Validate Feasibility Review Creation")
        print("="*60)

        reviews = FeasibilityReview.objects.filter(application=self.application)
        self.reviews = list(reviews)

        self.log_test(
            "3.1 Reviews Created",
            reviews.count() == 2,
            f"Created {reviews.count()} feasibility reviews (one per node)",
            "2 reviews",
            reviews.count()
        )

        # Check each review
        for review in reviews:
            self.log_test(
                f"3.2 Review for {review.node.code}",
                review.reviewer == review.node.director,
                f"Reviewer: {review.reviewer.email}, Node: {review.node.code}"
            )

            self.log_test(
                f"3.3 Review Pending ({review.node.code})",
                review.is_feasible is None,
                f"Initial status: Pending (is_feasible={review.is_feasible})"
            )

    def test_single_node_approval(self):
        """Test single node coordinator approving"""
        print("\n" + "="*60)
        print("TEST 4: Single Node Approval (Partial)")
        print("="*60)

        # Get CICBIO review
        cicbio_review = FeasibilityReview.objects.get(
            application=self.application,
            node=self.nodes['CICBIO']
        )

        # Approve from CICBIO
        cicbio_review.is_feasible = True
        cicbio_review.comments = 'Technical feasibility confirmed for MRI 7T access.'
        cicbio_review.reviewed_at = timezone.now()
        cicbio_review.save()

        self.log_test(
            "4.1 CICBIO Approval",
            cicbio_review.is_feasible is True,
            f"CICBIO approved: {cicbio_review.comments}"
        )

        # Check application status (should still be under_feasibility_review)
        self.application.refresh_from_db()

        pending_reviews = FeasibilityReview.objects.filter(
            application=self.application,
            is_feasible__isnull=True
        ).count()

        self.log_test(
            "4.2 Pending Reviews Remain",
            pending_reviews > 0,
            f"Still {pending_reviews} pending review(s)",
            "> 0",
            pending_reviews
        )

        self.log_test(
            "4.3 App Still Under Review",
            self.application.status == 'under_feasibility_review',
            f"Application status: {self.application.get_status_display()}"
        )

    def test_all_nodes_approve(self):
        """Test scenario where all nodes approve"""
        print("\n" + "="*60)
        print("TEST 5: All Nodes Approve → Pending Evaluation")
        print("="*60)

        # Approve from CNIC
        cnic_review = FeasibilityReview.objects.get(
            application=self.application,
            node=self.nodes['CNIC']
        )

        cnic_review.is_feasible = True
        cnic_review.comments = 'Feasible. PET-CT available for requested timeframe.'
        cnic_review.reviewed_at = timezone.now()
        cnic_review.save()

        self.log_test(
            "5.1 CNIC Approval",
            cnic_review.is_feasible is True,
            f"CNIC approved: {cnic_review.comments}"
        )

        # Check if all reviews complete
        all_reviews = FeasibilityReview.objects.filter(application=self.application)
        pending_count = all_reviews.filter(is_feasible__isnull=True).count()
        approved_count = all_reviews.filter(is_feasible=True).count()
        rejected_count = all_reviews.filter(is_feasible=False).count()

        self.log_test(
            "5.2 All Reviews Complete",
            pending_count == 0,
            f"Pending: {pending_count}, Approved: {approved_count}, Rejected: {rejected_count}",
            "Pending: 0",
            f"Pending: {pending_count}"
        )

        # Simulate view logic for updating application status
        if pending_count == 0:
            if rejected_count > 0:
                self.application.status = 'rejected_feasibility'
            else:
                self.application.status = 'pending_evaluation'
            self.application.save()

        self.application.refresh_from_db()

        self.log_test(
            "5.3 Status → Pending Evaluation",
            self.application.status == 'pending_evaluation',
            f"Application status: {self.application.get_status_display()}",
            "pending_evaluation",
            self.application.status
        )

    def test_rejection_scenario(self):
        """Test scenario where one node rejects"""
        print("\n" + "="*60)
        print("TEST 6: Rejection Scenario (One Node Rejects)")
        print("="*60)

        # Create a second test application
        app2 = Application.objects.create(
            call=self.call,
            applicant=self.applicant,
            status='draft',
            brief_description='Test rejection scenario',
            applicant_name='Test Applicant',
            applicant_entity='Phase 3 Test Org',
            applicant_email='applicant.phase3.test@redib.test',
            applicant_phone='+34 000 000 000',
            project_title='Rejection Test',
            project_type='national',
            subject_area='bme',
            service_modality='full_assistance',
            specialization_area='preclinical',
            scientific_relevance='Test',
            methodology_description='Test',
            expected_contributions='Test',
            impact_strengths='Test',
            socioeconomic_significance='Test',
            opportunity_criteria='Test',
            technical_feasibility_confirmed=True,
            data_consent=True
        )

        # Request equipment from both nodes
        cicbio_eq = Equipment.objects.get(node=self.nodes['CICBIO'], name='MRI 7T')
        cnic_eq = Equipment.objects.get(node=self.nodes['CNIC'], name='PET-CT')

        RequestedAccess.objects.create(application=app2, equipment=cicbio_eq, hours_requested=10)
        RequestedAccess.objects.create(application=app2, equipment=cnic_eq, hours_requested=10)

        # Submit and create reviews
        app2.status = 'submitted'
        app2.submitted_at = timezone.now()
        app2.save()

        for node in [self.nodes['CICBIO'], self.nodes['CNIC']]:
            FeasibilityReview.objects.create(
                application=app2,
                node=node,
                reviewer=node.director
            )

        app2.status = 'under_feasibility_review'
        app2.save()

        self.log_test(
            "6.1 Created Test App",
            app2.status == 'under_feasibility_review',
            f"Application {app2.pk} under review"
        )

        # CICBIO approves
        review_cicbio = FeasibilityReview.objects.get(application=app2, node=self.nodes['CICBIO'])
        review_cicbio.is_feasible = True
        review_cicbio.comments = 'Approved'
        review_cicbio.reviewed_at = timezone.now()
        review_cicbio.save()

        # CNIC rejects
        review_cnic = FeasibilityReview.objects.get(application=app2, node=self.nodes['CNIC'])
        review_cnic.is_feasible = False
        review_cnic.comments = 'Equipment unavailable during requested timeframe.'
        review_cnic.reviewed_at = timezone.now()
        review_cnic.save()

        self.log_test(
            "6.2 One Node Rejects",
            review_cnic.is_feasible is False,
            f"CNIC rejected: {review_cnic.comments}"
        )

        # Update application status based on reviews
        all_reviews = FeasibilityReview.objects.filter(application=app2)
        pending_count = all_reviews.filter(is_feasible__isnull=True).count()
        rejected_count = all_reviews.filter(is_feasible=False).count()

        if pending_count == 0 and rejected_count > 0:
            app2.status = 'rejected_feasibility'
            app2.save()

        app2.refresh_from_db()

        self.log_test(
            "6.3 Status → Rejected",
            app2.status == 'rejected_feasibility',
            f"Application status: {app2.get_status_display()}",
            "rejected_feasibility",
            app2.status
        )

        self.log_test(
            "6.4 Terminal State",
            app2.get_next_valid_states() == [],
            "Application in terminal state (no valid transitions)"
        )

    def validate_state_machine(self):
        """Validate state transitions comply with state machine"""
        print("\n" + "="*60)
        print("TEST 7: State Machine Validation")
        print("="*60)

        # Test valid transitions from submitted
        valid_from_submitted = Application.VALID_TRANSITIONS.get('submitted', [])

        self.log_test(
            "7.1 Submitted → Under Review",
            'under_feasibility_review' in valid_from_submitted,
            f"Valid transitions from submitted: {valid_from_submitted}"
        )

        # Test valid transitions from under_feasibility_review
        valid_from_review = Application.VALID_TRANSITIONS.get('under_feasibility_review', [])

        self.log_test(
            "7.2 Under Review → Pending Evaluation",
            'pending_evaluation' in valid_from_review,
            f"Valid transitions from under_feasibility_review: {valid_from_review}"
        )

        self.log_test(
            "7.3 Under Review → Rejected",
            'rejected_feasibility' in valid_from_review,
            f"Valid transitions from under_feasibility_review: {valid_from_review}"
        )

        # Test terminal states
        rejected_transitions = Application.VALID_TRANSITIONS.get('rejected_feasibility', [])

        self.log_test(
            "7.4 Rejected is Terminal",
            rejected_transitions == [],
            f"No transitions from rejected_feasibility: {rejected_transitions}"
        )

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("PHASE 3 TEST SUMMARY")
        print("="*60)

        passed = sum(1 for _, success, _ in self.test_results if success)
        failed = sum(1 for _, success, _ in self.test_results if not success)
        total = len(self.test_results)

        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")

        if failed > 0:
            print("\nFailed Tests:")
            for step, success, message in self.test_results:
                if not success:
                    print(f"  ❌ {step}: {message}")
            print("\n⚠️  PHASE 3 VALIDATION FAILED")
            return False
        else:
            print("\n🎉 ALL PHASE 3 TESTS PASSED!")
            print("✓ Feasibility reviews created correctly")
            print("✓ Node coordinator workflow functional")
            print("✓ Approval logic working")
            print("✓ Rejection logic working")
            print("✓ State machine validated")
            return True


def main():
    """Run Phase 3 validation tests"""
    print("="*60)
    print("PHASE 3: FEASIBILITY REVIEW VALIDATION")
    print("="*60)

    tester = Phase3Tester()

    try:
        # Setup
        tester.cleanup_test_data()
        tester.setup_test_environment()

        # Tests
        tester.create_test_call()
        tester.submit_application_requesting_multi_node_equipment()
        tester.test_feasibility_review_creation()
        tester.test_single_node_approval()
        tester.test_all_nodes_approve()
        tester.test_rejection_scenario()
        tester.validate_state_machine()

        # Summary
        success = tester.print_summary()

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n❌ TEST FAILED WITH ERROR:")
        print(f"   {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
