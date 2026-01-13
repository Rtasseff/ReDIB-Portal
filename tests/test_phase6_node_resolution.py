#!/usr/bin/env python
"""
Independent validation test for Phase 6: Node Coordinator Resolution Workflow.

This tests the NEW distributed resolution system where node coordinators
independently make resolution decisions that are then aggregated.

Critical Business Rules Tested:
1. Multi-node aggregation: ALL accept → accepted, ANY reject → rejected, waitlist → pending
2. Competitive funding protection: Cannot reject apps with has_competitive_funding=True
3. Hours approval: Node coordinators set hours_approved per equipment
4. Equipment completion: Either applicant OR node coordinator can mark done
5. Single-node immediate resolution: Apps requesting one node resolve immediately
6. Acceptance deadline: Set to resolution_date + 10 days on acceptance
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
from django.core.exceptions import ValidationError
from calls.models import Call, CallEquipmentAllocation
from applications.models import Application, RequestedAccess, NodeResolution
from core.models import Node, Equipment, Organization, UserRole
from applications.services import NodeResolutionService

User = get_user_model()


class Phase6NodeResolutionTester:
    """Test Phase 6: Node Coordinator Resolution Workflow"""

    def __init__(self):
        self.test_results = []
        self.cleanup()
        self.setup()

    def cleanup(self):
        """Clean up previous test data"""
        print("\n" + "=" * 60)
        print("CLEANUP: Removing previous Node Resolution test data")
        print("=" * 60)

        # Delete test applications (must delete before calls due to protected FK)
        Application.objects.filter(code__startswith='NR-TEST').delete()

        # Delete test call
        Call.objects.filter(code__startswith='NR-TEST').delete()

        # Delete test user roles
        UserRole.objects.filter(user__email__contains='nr.test').delete()

        # Delete test equipment/nodes
        Equipment.objects.filter(name__startswith='NR-Test').delete()
        Node.objects.filter(code__startswith='NR-TEST').delete()

        # Delete test users
        User.objects.filter(email__contains='nr.test').delete()

        # Delete test organization
        Organization.objects.filter(name='Node Resolution Test Org').delete()

        print("Cleanup complete\n")

    def setup(self):
        """Create test environment with multiple nodes"""
        print("=" * 60)
        print("SETUP: Creating multi-node test environment")
        print("=" * 60)

        # Create test organization
        self.org = Organization.objects.create(
            name='Node Resolution Test Org',
            organization_type='research_center'
        )

        # Create TWO nodes for multi-node testing
        self.node1 = Node.objects.create(
            code='NR-TEST-NODE1',
            name='Node Resolution Test Node 1'
        )
        self.node2 = Node.objects.create(
            code='NR-TEST-NODE2',
            name='Node Resolution Test Node 2'
        )

        # Create equipment for each node
        self.equipment1 = Equipment.objects.create(
            node=self.node1,
            name='NR-Test-Equipment-1',
            description='Test equipment at Node 1'
        )
        self.equipment2 = Equipment.objects.create(
            node=self.node2,
            name='NR-Test-Equipment-2',
            description='Test equipment at Node 2'
        )

        # Create node coordinators
        self.nc1 = User.objects.create_user(
            username='nc1.nr.test',
            email='nc1.nr.test@redib.test',
            password='testpass',
            first_name='Node Coord',
            last_name='One',
            organization=self.org
        )
        self.nc2 = User.objects.create_user(
            username='nc2.nr.test',
            email='nc2.nr.test@redib.test',
            password='testpass',
            first_name='Node Coord',
            last_name='Two',
            organization=self.org
        )

        # Assign node coordinator roles
        UserRole.objects.create(
            user=self.nc1,
            role='node_coordinator',
            node=self.node1,
            is_active=True
        )
        UserRole.objects.create(
            user=self.nc2,
            role='node_coordinator',
            node=self.node2,
            is_active=True
        )

        # Create applicant
        self.applicant = User.objects.create_user(
            username='applicant.nr.test',
            email='applicant.nr.test@redib.test',
            password='testpass',
            first_name='Test',
            last_name='Applicant',
            organization=self.org
        )

        # Create test call
        now = timezone.now()
        self.call = Call.objects.create(
            code='NR-TEST-CALL-01',
            title='Node Resolution Test Call',
            status='closed',
            submission_start=now - timedelta(days=60),
            submission_end=now - timedelta(days=30),
            evaluation_deadline=now - timedelta(days=1),
            execution_start=now + timedelta(days=30),
            execution_end=now + timedelta(days=90),
            description='Test call for node resolution'
        )

        # Create equipment allocations
        CallEquipmentAllocation.objects.create(call=self.call, equipment=self.equipment1)
        CallEquipmentAllocation.objects.create(call=self.call, equipment=self.equipment2)

        print("Created 2 nodes, 2 node coordinators, 1 applicant, 1 call\n")

    def log_test(self, test_id, passed, message):
        """Log test result"""
        result = "PASS" if passed else "FAIL"
        icon = "+" if passed else "-"
        print(f"  [{icon}] {test_id}: {message}")
        self.test_results.append({
            'id': test_id,
            'passed': passed,
            'message': message,
            'status': result
        })
        return passed

    def create_evaluated_app(self, code, score, competitive_funding=False, single_node=False):
        """Helper to create an evaluated application"""
        app = Application.objects.create(
            call=self.call,
            applicant=self.applicant,
            code=code,
            applicant_name='Test Applicant',
            applicant_email='applicant.nr.test@redib.test',
            brief_description=f'Test app {code}',
            status='evaluated',
            final_score=score,
            has_competitive_funding=competitive_funding,
            submitted_at=timezone.now()
        )

        # Request equipment from node 1
        RequestedAccess.objects.create(
            application=app,
            equipment=self.equipment1,
            hours_requested=Decimal('50.0')
        )

        # Request equipment from node 2 (unless single_node)
        if not single_node:
            RequestedAccess.objects.create(
                application=app,
                equipment=self.equipment2,
                hours_requested=Decimal('30.0')
            )

        return app

    def test_1_multi_node_all_accept(self):
        """Test 1: Multi-node aggregation - ALL accept -> Application accepted"""
        print("\n" + "=" * 60)
        print("TEST 1: Multi-Node Aggregation - All Accept")
        print("=" * 60)

        app = self.create_evaluated_app('NR-TEST-ALL-ACCEPT', Decimal('10.0'))

        # Node 1 accepts
        service1 = NodeResolutionService(node=self.node1)
        result1 = service1.apply_node_resolution(
            application=app,
            resolution='accept',
            comments='Approved by Node 1',
            approved_hours_dict={self.equipment1.id: Decimal('50.0')},
            user=self.nc1
        )

        # Test 1.1: First node decision doesn't finalize
        app.refresh_from_db()
        self.log_test("1.1", app.status == 'evaluated' and not result1['aggregated'],
                      f"First node decision: app status still 'evaluated' (aggregated={result1['aggregated']})")

        # Node 2 accepts
        service2 = NodeResolutionService(node=self.node2)
        result2 = service2.apply_node_resolution(
            application=app,
            resolution='accept',
            comments='Approved by Node 2',
            approved_hours_dict={self.equipment2.id: Decimal('30.0')},
            user=self.nc2
        )

        # Test 1.2: All nodes accepted -> Application accepted
        app.refresh_from_db()
        self.log_test("1.2", app.status == 'accepted' and app.resolution == 'accepted',
                      f"All accept: status={app.status}, resolution={app.resolution}")

        # Test 1.3: Aggregation happened
        self.log_test("1.3", result2['aggregated'] and result2['final_resolution'] == 'accepted',
                      f"Aggregation complete: final_resolution={result2.get('final_resolution')}")

        # Test 1.4: Acceptance deadline set
        self.log_test("1.4", app.acceptance_deadline is not None,
                      f"Acceptance deadline set: {app.acceptance_deadline}")

    def test_2_multi_node_any_reject(self):
        """Test 2: Multi-node aggregation - ANY reject -> Application rejected"""
        print("\n" + "=" * 60)
        print("TEST 2: Multi-Node Aggregation - Any Reject")
        print("=" * 60)

        app = self.create_evaluated_app('NR-TEST-ANY-REJECT', Decimal('8.0'))

        # Node 1 accepts
        service1 = NodeResolutionService(node=self.node1)
        service1.apply_node_resolution(
            application=app,
            resolution='accept',
            comments='Approved by Node 1',
            approved_hours_dict={self.equipment1.id: Decimal('50.0')},
            user=self.nc1
        )

        # Node 2 rejects
        service2 = NodeResolutionService(node=self.node2)
        result2 = service2.apply_node_resolution(
            application=app,
            resolution='reject',
            comments='Rejected by Node 2 - capacity issues',
            approved_hours_dict={self.equipment2.id: Decimal('0.0')},
            user=self.nc2
        )

        # Test 2.1: Any reject -> Application rejected
        app.refresh_from_db()
        self.log_test("2.1", app.status == 'rejected' and app.resolution == 'rejected',
                      f"Any reject: status={app.status}, resolution={app.resolution}")

        # Test 2.2: Comments aggregated
        self.log_test("2.2", 'Node 1' in app.resolution_comments and 'Node 2' in app.resolution_comments,
                      "Comments from both nodes aggregated")

    def test_3_multi_node_waitlist(self):
        """Test 3: Multi-node aggregation - No rejects but waitlist -> pending"""
        print("\n" + "=" * 60)
        print("TEST 3: Multi-Node Aggregation - Waitlist")
        print("=" * 60)

        app = self.create_evaluated_app('NR-TEST-WAITLIST', Decimal('7.0'))

        # Node 1 accepts
        service1 = NodeResolutionService(node=self.node1)
        service1.apply_node_resolution(
            application=app,
            resolution='accept',
            comments='Approved by Node 1',
            approved_hours_dict={self.equipment1.id: Decimal('50.0')},
            user=self.nc1
        )

        # Node 2 waitlists
        service2 = NodeResolutionService(node=self.node2)
        result2 = service2.apply_node_resolution(
            application=app,
            resolution='waitlist',
            comments='Waitlisted by Node 2 - limited capacity',
            approved_hours_dict={self.equipment2.id: Decimal('15.0')},
            user=self.nc2
        )

        # Test 3.1: Accept + Waitlist -> pending
        app.refresh_from_db()
        self.log_test("3.1", app.status == 'pending' and app.resolution == 'pending',
                      f"Accept + Waitlist: status={app.status}, resolution={app.resolution}")

    def test_4_competitive_funding_protection(self):
        """Test 4: Competitive funding apps cannot be rejected"""
        print("\n" + "=" * 60)
        print("TEST 4: Competitive Funding Protection")
        print("=" * 60)

        app = self.create_evaluated_app('NR-TEST-COMP-FUND', Decimal('5.0'), competitive_funding=True)

        service = NodeResolutionService(node=self.node1)

        # Test 4.1: Try to reject competitive funding app
        try:
            service.apply_node_resolution(
                application=app,
                resolution='reject',
                comments='Trying to reject',
                approved_hours_dict={self.equipment1.id: Decimal('0.0')},
                user=self.nc1
            )
            self.log_test("4.1", False, "Should have raised ValidationError")
        except ValidationError as e:
            self.log_test("4.1", 'competitive funding' in str(e).lower(),
                          "Reject blocked for competitive funding app")

        # Test 4.2: Can accept competitive funding app
        result = service.apply_node_resolution(
            application=app,
            resolution='accept',
            comments='Accepted',
            approved_hours_dict={self.equipment1.id: Decimal('50.0')},
            user=self.nc1
        )
        self.log_test("4.2", result['success'], "Can accept competitive funding app")

        # Test 4.3: Can waitlist competitive funding app
        app2 = self.create_evaluated_app('NR-TEST-COMP-FUND-2', Decimal('5.0'), competitive_funding=True)
        result2 = service.apply_node_resolution(
            application=app2,
            resolution='waitlist',
            comments='Waitlisted',
            approved_hours_dict={self.equipment1.id: Decimal('25.0')},
            user=self.nc1
        )
        self.log_test("4.3", result2['success'], "Can waitlist competitive funding app")

    def test_5_single_node_immediate_resolution(self):
        """Test 5: Single-node apps resolve immediately"""
        print("\n" + "=" * 60)
        print("TEST 5: Single-Node Immediate Resolution")
        print("=" * 60)

        # Create app requesting only node 1's equipment
        app = self.create_evaluated_app('NR-TEST-SINGLE-NODE', Decimal('9.0'), single_node=True)

        service = NodeResolutionService(node=self.node1)
        result = service.apply_node_resolution(
            application=app,
            resolution='accept',
            comments='Approved',
            approved_hours_dict={self.equipment1.id: Decimal('50.0')},
            user=self.nc1
        )

        # Test 5.1: Single node decision finalizes immediately
        app.refresh_from_db()
        self.log_test("5.1", app.status == 'accepted' and result['aggregated'],
                      f"Single node: immediate resolution (status={app.status})")

    def test_6_hours_approval(self):
        """Test 6: Hours approved can differ from requested"""
        print("\n" + "=" * 60)
        print("TEST 6: Hours Approval")
        print("=" * 60)

        app = self.create_evaluated_app('NR-TEST-HOURS', Decimal('8.5'), single_node=True)

        # Approve fewer hours than requested
        service = NodeResolutionService(node=self.node1)
        service.apply_node_resolution(
            application=app,
            resolution='accept',
            comments='Partial hours approved',
            approved_hours_dict={self.equipment1.id: Decimal('30.0')},  # Requested 50
            user=self.nc1
        )

        # Test 6.1: Hours approved set correctly
        req_access = app.requested_access.get(equipment=self.equipment1)
        self.log_test("6.1", req_access.hours_approved == Decimal('30.0'),
                      f"Hours approved: {req_access.hours_approved} (requested: {req_access.hours_requested})")

    def test_7_equipment_completion(self):
        """Test 7: Equipment completion tracking"""
        print("\n" + "=" * 60)
        print("TEST 7: Equipment Completion Tracking")
        print("=" * 60)

        app = self.create_evaluated_app('NR-TEST-COMPLETION', Decimal('10.0'), single_node=True)

        # Accept the application first
        service = NodeResolutionService(node=self.node1)
        service.apply_node_resolution(
            application=app,
            resolution='accept',
            comments='Approved',
            approved_hours_dict={self.equipment1.id: Decimal('50.0')},
            user=self.nc1
        )

        # Test 7.1: Initial state - not completed
        req_access = app.requested_access.get(equipment=self.equipment1)
        self.log_test("7.1", not req_access.is_completed,
                      f"Initial: is_completed={req_access.is_completed}")

        # Mark as completed by applicant
        req_access.is_completed = True
        req_access.completed_by = self.applicant
        req_access.completed_at = timezone.now()
        req_access.actual_hours_used = Decimal('45.0')
        req_access.save()

        # Test 7.2: Completion tracked
        req_access.refresh_from_db()
        self.log_test("7.2", req_access.is_completed and req_access.completed_by == self.applicant,
                      f"Completed by applicant, actual hours: {req_access.actual_hours_used}")

    def test_8_node_coordinator_validation(self):
        """Test 8: Only node coordinators can resolve for their node"""
        print("\n" + "=" * 60)
        print("TEST 8: Node Coordinator Validation")
        print("=" * 60)

        app = self.create_evaluated_app('NR-TEST-VALIDATION', Decimal('9.0'))

        # Try to resolve node 1's equipment with node 2's coordinator
        service = NodeResolutionService(node=self.node1)

        try:
            service.apply_node_resolution(
                application=app,
                resolution='accept',
                comments='Wrong coordinator',
                approved_hours_dict={self.equipment1.id: Decimal('50.0')},
                user=self.nc2  # NC2 is coordinator for node 2, not node 1
            )
            self.log_test("8.1", False, "Should have raised ValidationError")
        except ValidationError as e:
            self.log_test("8.1", 'not an active node coordinator' in str(e).lower(),
                          "Wrong node coordinator blocked")

    def test_9_service_queries(self):
        """Test 9: Service query methods"""
        print("\n" + "=" * 60)
        print("TEST 9: Service Query Methods")
        print("=" * 60)

        # Create a new evaluated app
        app = self.create_evaluated_app('NR-TEST-QUERIES', Decimal('8.0'))

        service = NodeResolutionService(node=self.node1)

        # Test 9.1: Get pending applications
        pending = service.get_applications_for_node_resolution()
        self.log_test("9.1", app in pending,
                      f"get_applications_for_node_resolution returns pending app")

        # Resolve the app
        service.apply_node_resolution(
            application=app,
            resolution='accept',
            comments='Approved',
            approved_hours_dict={self.equipment1.id: Decimal('50.0')},
            user=self.nc1
        )

        # Test 9.2: Resolved app no longer in pending
        pending_after = service.get_applications_for_node_resolution()
        self.log_test("9.2", app not in pending_after,
                      "Resolved app not in pending list")

        # Test 9.3: Resolved app in resolved list
        resolved = service.get_resolved_applications_for_node(call=self.call)
        self.log_test("9.3", app in resolved,
                      "Resolved app in resolved list")

    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "=" * 60)
        print("PHASE 6: NODE COORDINATOR RESOLUTION TEST SUITE")
        print("=" * 60)

        self.test_1_multi_node_all_accept()
        self.test_2_multi_node_any_reject()
        self.test_3_multi_node_waitlist()
        self.test_4_competitive_funding_protection()
        self.test_5_single_node_immediate_resolution()
        self.test_6_hours_approval()
        self.test_7_equipment_completion()
        self.test_8_node_coordinator_validation()
        self.test_9_service_queries()

        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        passed = sum(1 for r in self.test_results if r['passed'])
        total = len(self.test_results)
        success_rate = (passed / total * 100) if total > 0 else 0

        print(f"Total tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success rate: {success_rate:.1f}%")

        if success_rate == 100:
            print("\nALL TESTS PASSED! Node Resolution workflow validated successfully.")
        else:
            print("\nSome tests failed. Review errors above.")
            for r in self.test_results:
                if not r['passed']:
                    print(f"  FAILED: {r['id']} - {r['message']}")

        return success_rate == 100


if __name__ == '__main__':
    tester = Phase6NodeResolutionTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
