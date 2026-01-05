#!/usr/bin/env python
"""
Independent validation test for Phase 6: Resolution & Prioritization.

Critical Business Rules Tested:
1. Auto-approval rule: Competitive funding apps CANNOT be rejected
2. Prioritization: PRIMARY by final_score DESC, SECONDARY by code ASC
3. Hours tracking: Track total approved hours (sum of hours_requested from accepted apps)
4. State transitions: evaluated → accepted/pending/rejected
5. Finalization: Lock call and trigger notifications
"""
import os
import sys
import django
from decimal import Decimal
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redib.settings')
django.setup()

from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from calls.models import Call, CallEquipmentAllocation
from applications.models import Application, RequestedAccess
from core.models import Node, Equipment, Organization
from applications.services import ResolutionService

User = get_user_model()


class Phase6Tester:
    """Test Phase 6: Resolution & Prioritization"""

    def __init__(self):
        self.test_results = []
        self.cleanup()
        self.setup()

    def cleanup(self):
        """Clean up previous test data"""
        print("\n" + "=" * 60)
        print("CLEANUP: Removing previous Phase 6 test data")
        print("=" * 60)

        # Delete test applications (must delete before calls due to protected FK)
        Application.objects.filter(code__startswith='PHASE6').delete()

        # Delete test call
        Call.objects.filter(code__startswith='PHASE6-TEST').delete()

        # Delete test equipment/nodes
        Equipment.objects.filter(name__startswith='Phase6-Test').delete()
        Node.objects.filter(code__startswith='PHASE6-TEST').delete()

        # Delete test users
        User.objects.filter(email__contains='phase6.test').delete()

        print("✓ Cleanup complete\n")

    def setup(self):
        """Create test environment"""
        print("=" * 60)
        print("SETUP: Creating test environment")
        print("=" * 60)

        # Create test organization
        self.org = Organization.objects.create(
            name='Phase 6 Test Organization',
            organization_type='research_center'
        )

        # Create coordinator
        self.coordinator = User.objects.create_user(
            username='coordinator.phase6.test',
            email='coordinator.phase6.test@redib.test',
            password='testpass',
            first_name='Test',
            last_name='Coordinator',
            organization=self.org
        )

        # Create applicants
        self.applicant1 = User.objects.create_user(
            username='applicant1.phase6.test',
            email='applicant1.phase6.test@redib.test',
            password='testpass',
            first_name='Applicant',
            last_name='One',
            organization=self.org
        )
        self.applicant2 = User.objects.create_user(
            username='applicant2.phase6.test',
            email='applicant2.phase6.test@redib.test',
            password='testpass',
            first_name='Applicant',
            last_name='Two',
            organization=self.org
        )

        # Create test node and equipment
        self.node = Node.objects.create(
            code='PHASE6-TEST-NODE',
            name='Phase 6 Test Node'
        )
        self.equipment = Equipment.objects.create(
            node=self.node,
            name='Phase6-Test-Equipment',
            description='Test equipment for Phase 6'
        )

        # Create test call
        now = timezone.now()
        self.call = Call.objects.create(
            code='PHASE6-TEST-CALL-01',
            title='Phase 6 Test Call',
            status='closed',
            submission_start=now - timedelta(days=60),
            submission_end=now - timedelta(days=30),
            evaluation_deadline=now - timedelta(days=1),  # Past deadline
            execution_start=now + timedelta(days=30),
            execution_end=now + timedelta(days=90),
            description='Test call for Phase 6'
        )

        # Create equipment allocation
        self.allocation = CallEquipmentAllocation.objects.create(
            call=self.call,
            equipment=self.equipment
        )

        print("✓ Created test environment\n")

    def log_test(self, test_id, passed, message):
        """Log test result"""
        result = "✅" if passed else "❌"
        status = "PASS" if passed else "FAIL"
        print(f"{result} {test_id}: {message}")
        self.test_results.append({
            'id': test_id,
            'passed': passed,
            'message': message,
            'status': status
        })
        return passed

    def test_1_auto_approval_rule(self):
        """Test 1: Auto-Approval Rule for Competitive Funding"""
        print("\n" + "=" * 60)
        print("TEST 1: Auto-Approval Rule (Competitive Funding)")
        print("=" * 60)

        # Create application with competitive funding
        app = Application.objects.create(
            call=self.call,
            applicant=self.applicant1,
            code='PHASE6-TEST-COMP-FUND',
            applicant_name='Applicant One',
            applicant_email='applicant1.phase6.test@redib.test',
            brief_description='App with competitive funding',
            status='evaluated',
            final_score=Decimal('2.5'),  # LOW score
            has_competitive_funding=True,  # CRITICAL: Has competitive funding
            submitted_at=timezone.now()
        )

        # Add equipment request
        RequestedAccess.objects.create(
            application=app,
            equipment=self.equipment,
            hours_requested=Decimal('50.0')
        )

        service = ResolutionService(self.call)

        # Test 1.1: Can accept despite low score
        can_accept, reason, details = service.can_accept_application(app)
        self.log_test("1.1", can_accept and reason == 'auto_approved_competitive_funding',
                      f"Competitive funding app can be accepted (score: {app.final_score})")

        # Test 1.2: Cannot reject (validation error expected)
        try:
            service.apply_resolution(app, 'rejected', 'Test rejection')
            self.log_test("1.2", False, "Should have raised ValidationError for rejecting competitive funding app")
        except Exception as e:
            self.log_test("1.2", 'competitive funding cannot be rejected' in str(e).lower(),
                          "Rejecting competitive funding app raises ValidationError")

        # Test 1.3: Can accept successfully
        result = service.apply_resolution(app, 'accepted', 'Auto-approved')
        self.log_test("1.3", result['success'] and app.status == 'accepted',
                      "Competitive funding app successfully accepted")

    def test_2_prioritization(self):
        """Test 2: Prioritization (Score DESC, Code ASC)"""
        print("\n" + "=" * 60)
        print("TEST 2: Prioritization Algorithm")
        print("=" * 60)

        # Create applications with varied scores
        apps_data = [
            ('PHASE6-TEST-APP-003', Decimal('4.5')),
            ('PHASE6-TEST-APP-001', Decimal('5.0')),  # Highest score
            ('PHASE6-TEST-APP-002', Decimal('5.0')),  # Same score as APP-001
            ('PHASE6-TEST-APP-004', Decimal('3.0')),
        ]

        for code, score in apps_data:
            app = Application.objects.create(
                call=self.call,
                applicant=self.applicant1,
                code=code,
                applicant_name='Test Applicant',
                applicant_email='test@redib.test',
                brief_description=f'Test app {code}',
                status='evaluated',
                final_score=score,
                submitted_at=timezone.now()
            )
            RequestedAccess.objects.create(
                application=app,
                equipment=self.equipment,
                hours_requested=Decimal('10.0')
            )

        service = ResolutionService(self.call)
        prioritized = list(service.get_prioritized_applications())

        # Test 2.1: Sorted by score DESC
        self.log_test("2.1", prioritized[0].final_score >= prioritized[1].final_score >= prioritized[2].final_score,
                      "Applications sorted by score (DESC)")

        # Test 2.2: Tie-breaking by code ASC (APP-001 before APP-002)
        app_001 = next((a for a in prioritized if a.code == 'PHASE6-TEST-APP-001'), None)
        app_002 = next((a for a in prioritized if a.code == 'PHASE6-TEST-APP-002'), None)
        idx_001 = prioritized.index(app_001) if app_001 else 999
        idx_002 = prioritized.index(app_002) if app_002 else 999
        self.log_test("2.2", idx_001 < idx_002,
                      f"Tie-breaking by code ASC (APP-001 rank {idx_001+1}, APP-002 rank {idx_002+1})")

    def test_3_hours_tracking(self):
        """Test 3: Total Approved Hours Tracking"""
        print("\n" + "=" * 60)
        print("TEST 3: Total Approved Hours Tracking")
        print("=" * 60)

        # Clean up applications from previous tests to reset hours
        Application.objects.filter(call=self.call).delete()

        service = ResolutionService(self.call)

        # Test 3.1: Initial approved hours is zero
        self.allocation.refresh_from_db()
        initial_hours = self.allocation.total_approved_hours
        self.log_test("3.1", initial_hours == 0,
                      f"Initial approved hours: {initial_hours}")

        # Create and accept application
        app = Application.objects.create(
            call=self.call,
            applicant=self.applicant2,
            code='PHASE6-TEST-HOURS-01',
            applicant_name='Hours Test',
            applicant_email='hours@test.com',
            brief_description='Hours tracking test',
            status='evaluated',
            final_score=Decimal('4.0'),
            submitted_at=timezone.now()
        )
        req = RequestedAccess.objects.create(
            application=app,
            equipment=self.equipment,
            hours_requested=Decimal('60.0')
        )

        # Apply resolution
        result = service.apply_resolution(app, 'accepted', 'Test')

        # Test 3.2: Application accepted successfully
        app.refresh_from_db()
        self.log_test("3.2", app.status == 'accepted' and app.resolution == 'accepted',
                      f"Application accepted (status: {app.status})")

        # Test 3.3: Total approved hours calculated correctly
        self.allocation.refresh_from_db()
        approved_hours = self.allocation.total_approved_hours
        self.log_test("3.3", approved_hours == Decimal('60.0'),
                      f"Total approved hours: {approved_hours}")

    def test_4_bulk_resolution(self):
        """Test 4: Bulk Auto-Allocation"""
        print("\n" + "=" * 60)
        print("TEST 4: Bulk Auto-Allocation")
        print("=" * 60)

        # Clean up applications from previous tests to reset hours
        Application.objects.filter(call=self.call).delete()

        # Create 5 apps: Apps with score >= 3.0 accepted, below pending (with auto_pending=True)
        apps_data = [
            ('PHASE6-BULK-01', Decimal('5.0'), Decimal('30.0'), False),  # Will be accepted
            ('PHASE6-BULK-02', Decimal('4.5'), Decimal('30.0'), False),  # Will be accepted
            ('PHASE6-BULK-03', Decimal('3.5'), Decimal('30.0'), False),  # Will be accepted
            ('PHASE6-BULK-04', Decimal('3.0'), Decimal('30.0'), False),  # Will be accepted (at threshold)
            ('PHASE6-BULK-05', Decimal('2.0'), Decimal('30.0'), False),  # Will get pending (below threshold)
        ]

        for code, score, hours, comp_funding in apps_data:
            app = Application.objects.create(
                call=self.call,
                applicant=self.applicant1,
                code=code,
                applicant_name='Bulk Test',
                applicant_email='bulk@test.com',
                brief_description='Bulk test',
                status='evaluated',
                final_score=score,
                has_competitive_funding=comp_funding,
                submitted_at=timezone.now()
            )
            RequestedAccess.objects.create(
                application=app,
                equipment=self.equipment,
                hours_requested=hours
            )

        service = ResolutionService(self.call)
        result = service.bulk_auto_allocate(threshold_score=Decimal('3.0'), auto_pending=True)

        # Test 4.1: Correct counts (4 accepted with score >= 3.0, 1 pending with score < 3.0)
        self.log_test("4.1", result['accepted'] == 4 and result['pending'] == 1,
                      f"Accepted: {result['accepted']}, Pending: {result['pending']}, Rejected: {result['rejected']}")

        # Test 4.2: Low score app marked as pending (with auto_pending=True)
        app_05 = Application.objects.get(code='PHASE6-BULK-05')
        self.log_test("4.2", app_05.resolution == 'pending',
                      f"Low score app set to pending (score: {app_05.final_score})")

    def test_5_finalization(self):
        """Test 5: Finalization and Locking"""
        print("\n" + "=" * 60)
        print("TEST 5: Finalization")
        print("=" * 60)

        # Ensure all apps are resolved
        for app in Application.objects.filter(call=self.call, status='evaluated'):
            app.resolution = 'accepted'
            app.status = 'accepted'
            app.save()

        service = ResolutionService(self.call)

        # Test 5.1: Finalize successfully
        try:
            result = service.finalize_resolution(self.coordinator)
            self.log_test("5.1", result['success'] and result['call_code'] == self.call.code,
                          "Finalization successful")
        except Exception as e:
            self.log_test("5.1", False, f"Finalization failed: {e}")

        # Test 5.2: Call is locked
        self.call.refresh_from_db()
        self.log_test("5.2", self.call.is_resolution_locked,
                      "Call is locked after finalization")

        # Test 5.3: Cannot finalize again
        try:
            service.finalize_resolution(self.coordinator)
            self.log_test("5.3", False, "Should have raised ValidationError for already finalized call")
        except Exception as e:
            self.log_test("5.3", 'already finalized' in str(e).lower(),
                          "Re-finalization raises ValidationError")

    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "=" * 60)
        print("PHASE 6: RESOLUTION & PRIORITIZATION TEST SUITE")
        print("=" * 60)

        self.test_1_auto_approval_rule()
        self.test_2_prioritization()
        self.test_3_hours_tracking()
        self.test_4_bulk_resolution()
        self.test_5_finalization()

        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        passed = sum(1 for r in self.test_results if r['passed'])
        total = len(self.test_results)
        success_rate = (passed / total * 100) if total > 0 else 0

        print(f"Total tests: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {total - passed} ❌")
        print(f"Success rate: {success_rate:.1f}%")

        if success_rate == 100:
            print("\n🎉 ALL TESTS PASSED! Phase 6 implementation validated successfully.")
        else:
            print("\n⚠️  Some tests failed. Review errors above.")

        return success_rate == 100


if __name__ == '__main__':
    tester = Phase6Tester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
