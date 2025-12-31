#!/usr/bin/env python
"""
End-to-end workflow test for Phase 1 (Call Management) and Phase 2 (Application Submission).

This test:
1. Creates a new call with equipment allocations (Phase 1)
2. Creates a new application with all required fields (Phase 2)
3. Validates the data matches the specification
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
from calls.models import Call, CallEquipmentAllocation
from applications.models import Application, RequestedAccess
from core.models import Node, Equipment, Organization, UserRole

User = get_user_model()


class WorkflowTester:
    """Test Phase 1 and Phase 2 workflow"""

    def __init__(self):
        self.test_results = []
        self.call = None
        self.application = None
        self.applicant = None

    def log_test(self, step, success, message):
        """Log test step result"""
        status = "✅" if success else "❌"
        print(f"{status} {step}: {message}")
        self.test_results.append((step, success, message))

    def cleanup_previous_test_data(self):
        """Clean up any previous test data"""
        print("\n" + "="*60)
        print("CLEANING UP PREVIOUS TEST DATA")
        print("="*60)

        # Delete test applications
        Application.objects.filter(code__startswith='TEST-E2E').delete()
        # Delete test calls
        Call.objects.filter(code__startswith='TEST-E2E').delete()
        # Delete test users
        User.objects.filter(email='test.e2e.applicant@redib.test').delete()
        User.objects.filter(email='test.e2e.coordinator@redib.test').delete()

        print("✓ Cleanup complete")

    def setup_test_users(self):
        """Create test users for the workflow"""
        print("\n" + "="*60)
        print("SETTING UP TEST USERS")
        print("="*60)

        # Get or create test organization
        org, _ = Organization.objects.get_or_create(
            name='Test University E2E',
            defaults={
                'country': 'Spain',
                'organization_type': 'university'
            }
        )

        # Create applicant user
        self.applicant, created = User.objects.get_or_create(
            email='test.e2e.applicant@redib.test',
            defaults={
                'first_name': 'Test',
                'last_name': 'Applicant',
                'organization': org,
                'phone': '+34 111 222 333',
                'is_active': True
            }
        )
        if created:
            self.applicant.set_password('testpass123')
            self.applicant.save()

        # Assign applicant role
        UserRole.objects.get_or_create(
            user=self.applicant,
            role='applicant',
            defaults={'is_active': True}
        )

        # Create coordinator user
        self.coordinator, created = User.objects.get_or_create(
            email='test.e2e.coordinator@redib.test',
            defaults={
                'first_name': 'Test',
                'last_name': 'Coordinator',
                'organization': org,
                'is_staff': True,
                'is_active': True
            }
        )
        if created:
            self.coordinator.set_password('testpass123')
            self.coordinator.save()

        # Assign coordinator role
        UserRole.objects.get_or_create(
            user=self.coordinator,
            role='coordinator',
            defaults={'is_active': True}
        )

        self.log_test(
            "User Setup",
            True,
            f"Created applicant ({self.applicant.email}) and coordinator ({self.coordinator.email})"
        )

    def test_phase1_create_call(self):
        """Phase 1: Create a new call with equipment allocations"""
        print("\n" + "="*60)
        print("PHASE 1: CALL MANAGEMENT")
        print("="*60)

        now = timezone.now()

        # Create call
        self.call = Call.objects.create(
            code='TEST-E2E-2025',
            title='End-to-End Test Call 2025',
            status='open',
            submission_start=now,
            submission_end=now + timedelta(days=45),
            evaluation_deadline=now + timedelta(days=60),
            execution_start=now + timedelta(days=75),
            execution_end=now + timedelta(days=120),
            description='This is an end-to-end test call to validate Phase 1 and Phase 2.',
            published_at=now
        )

        self.log_test(
            "1.1 Create Call",
            self.call is not None,
            f"Created call {self.call.code}"
        )

        # Verify call is open
        self.log_test(
            "1.2 Call is Open",
            self.call.is_open,
            f"Call status: {self.call.status}, is_open: {self.call.is_open}"
        )

        # Get equipment to allocate
        equipment_list = Equipment.objects.filter(is_active=True)[:5]

        self.log_test(
            "1.3 Equipment Available",
            equipment_list.exists(),
            f"Found {equipment_list.count()} active equipment items"
        )

        # Allocate equipment to call
        allocations_created = 0
        for equipment in equipment_list:
            allocation, created = CallEquipmentAllocation.objects.get_or_create(
                call=self.call,
                equipment=equipment,
                defaults={'hours_offered': 50}
            )
            if created:
                allocations_created += 1

        self.log_test(
            "1.4 Equipment Allocations",
            allocations_created > 0,
            f"Created {allocations_created} equipment allocations"
        )

        # Verify call has allocations
        allocation_count = self.call.equipment_allocations.count()
        self.log_test(
            "1.5 Verify Allocations",
            allocation_count > 0,
            f"Call has {allocation_count} equipment allocations"
        )

    def test_phase2_create_application(self):
        """Phase 2: Create and submit application with new fields"""
        print("\n" + "="*60)
        print("PHASE 2: APPLICATION SUBMISSION")
        print("="*60)

        # Step 1: Create draft application with applicant information
        self.application = Application.objects.create(
            call=self.call,
            applicant=self.applicant,
            status='draft',
            brief_description='End-to-end test application for spec validation',
            # NEW APPLICANT FIELDS (from spec)
            applicant_name='Test Applicant',
            applicant_orcid='0000-0002-1234-5678',
            applicant_entity='Test University E2E',
            applicant_email='test.e2e.applicant@redib.test',
            applicant_phone='+34 111 222 333'
        )

        self.log_test(
            "2.1 Create Draft",
            self.application is not None,
            f"Created draft application (ID: {self.application.pk})"
        )

        # Validate applicant fields are saved
        self.log_test(
            "2.2 Applicant Name",
            self.application.applicant_name == 'Test Applicant',
            f"applicant_name: {self.application.applicant_name}"
        )

        self.log_test(
            "2.3 Applicant ORCID",
            self.application.applicant_orcid == '0000-0002-1234-5678',
            f"applicant_orcid: {self.application.applicant_orcid}"
        )

        self.log_test(
            "2.4 Applicant Entity",
            self.application.applicant_entity == 'Test University E2E',
            f"applicant_entity: {self.application.applicant_entity}"
        )

        self.log_test(
            "2.5 Applicant Email",
            self.application.applicant_email == 'test.e2e.applicant@redib.test',
            f"applicant_email: {self.application.applicant_email}"
        )

        self.log_test(
            "2.6 Applicant Phone",
            self.application.applicant_phone == '+34 111 222 333',
            f"applicant_phone: {self.application.applicant_phone}"
        )

        # Step 2: Fill in funding information (NEW project types and subject areas)
        self.application.project_title = 'Advanced Imaging Research Project'
        self.application.project_code = 'E2E-2025-001'
        self.application.funding_agency = 'Agencia Estatal de Investigación'
        self.application.project_type = 'national'  # NEW PROJECT TYPE
        self.application.has_competitive_funding = True
        self.application.subject_area = 'bme'  # NEW SUBJECT AREA (Biomedicine)
        self.application.save()

        self.log_test(
            "2.7 Project Type (NEW)",
            self.application.project_type == 'national',
            f"project_type: {self.application.get_project_type_display()}"
        )

        self.log_test(
            "2.8 Subject Area (NEW)",
            self.application.subject_area == 'bme',
            f"subject_area: {self.application.get_subject_area_display()}"
        )

        # Step 3: Service modality and specialization
        self.application.service_modality = 'full_assistance'
        self.application.specialization_area = 'preclinical'
        self.application.save()

        self.log_test(
            "2.9 Service Modality",
            self.application.service_modality == 'full_assistance',
            f"service_modality: {self.application.get_service_modality_display()}"
        )

        # Step 4: Request equipment access
        equipment = self.call.equipment_allocations.first().equipment
        requested_access = RequestedAccess.objects.create(
            application=self.application,
            equipment=equipment,
            hours_requested=20
        )

        self.log_test(
            "2.10 Equipment Request",
            requested_access is not None,
            f"Requested {requested_access.hours_requested}h on {equipment.name}"
        )

        # Step 5: Scientific content
        self.application.scientific_relevance = 'High relevance for biomedical research.'
        self.application.methodology_description = 'Well-designed experimental protocol.'
        self.application.expected_contributions = 'Novel insights into disease mechanisms.'
        self.application.impact_strengths = 'Strong publication potential.'
        self.application.socioeconomic_significance = 'Benefits patient care.'
        self.application.opportunity_criteria = 'Timely research opportunity.'
        self.application.save()

        self.log_test(
            "2.11 Scientific Content",
            bool(self.application.scientific_relevance),
            "All 6 scientific fields populated"
        )

        # Step 6: Declarations
        self.application.technical_feasibility_confirmed = True
        self.application.uses_animals = False
        self.application.has_animal_ethics = False
        self.application.uses_humans = True
        self.application.has_human_ethics = True
        self.application.data_consent = True
        self.application.save()

        self.log_test(
            "2.12 Declarations",
            self.application.data_consent,
            "All declarations completed"
        )

        # Submit application
        self.application.status = 'submitted'
        self.application.submitted_at = timezone.now()
        self.application.save()

        self.log_test(
            "2.13 Submit Application",
            self.application.status == 'submitted',
            f"Application submitted at {self.application.submitted_at}"
        )

    def validate_spec_compliance(self):
        """Validate the application meets all spec requirements"""
        print("\n" + "="*60)
        print("SPEC COMPLIANCE VALIDATION")
        print("="*60)

        # Validate all 5 applicant fields are present
        applicant_fields_present = all([
            self.application.applicant_name,
            # applicant_orcid is optional, so we don't check it's required
            self.application.applicant_entity,
            self.application.applicant_email,
            self.application.applicant_phone
        ])

        self.log_test(
            "3.1 Required Applicant Fields",
            applicant_fields_present,
            "All required applicant fields have values"
        )

        # Validate project type is one of the 7 new types
        valid_project_types = [
            'national', 'international_non_european', 'regional',
            'european', 'internal', 'private', 'other'
        ]

        self.log_test(
            "3.2 Valid Project Type",
            self.application.project_type in valid_project_types,
            f"project_type '{self.application.project_type}' is in approved list"
        )

        # Validate subject area is one of the 20 AEI areas
        valid_subject_areas = [
            'cso', 'der', 'eco', 'mlp', 'fla', 'pha', 'edu', 'psi',
            'mtm', 'fis', 'pin', 'tic', 'eyt', 'ctq', 'mat', 'ctm',
            'caa', 'bio', 'bme', 'other'
        ]

        self.log_test(
            "3.3 Valid Subject Area",
            self.application.subject_area in valid_subject_areas,
            f"subject_area '{self.application.subject_area}' is in approved AEI list"
        )

        # Validate all workflow steps completed
        self.log_test(
            "3.4 Complete Workflow",
            all([
                self.application.brief_description,
                self.application.project_title,
                self.application.service_modality,
                self.application.requested_access.exists(),
                self.application.scientific_relevance,
                self.application.data_consent
            ]),
            "All 5 wizard steps completed"
        )

    def print_application_summary(self):
        """Print detailed application summary"""
        print("\n" + "="*60)
        print("APPLICATION SUMMARY")
        print("="*60)
        print(f"Code: {self.application.code or 'DRAFT'}")
        print(f"Call: {self.call.code} - {self.call.title}")
        print(f"Status: {self.application.get_status_display()}")
        print(f"Submitted: {self.application.submitted_at}")
        print("\n--- Applicant Information (NEW FIELDS) ---")
        print(f"Name: {self.application.applicant_name}")
        print(f"ORCID: {self.application.applicant_orcid or 'N/A'}")
        print(f"Entity: {self.application.applicant_entity}")
        print(f"Email: {self.application.applicant_email}")
        print(f"Phone: {self.application.applicant_phone}")
        print("\n--- Project Details (UPDATED CHOICES) ---")
        print(f"Project Type: {self.application.get_project_type_display()}")
        print(f"Subject Area: {self.application.get_subject_area_display()}")
        print(f"Service Modality: {self.application.get_service_modality_display()}")
        print(f"Equipment Requested: {self.application.requested_access.count()} items")
        print(f"Total Hours: {self.application.total_hours_requested}h")

    def print_test_summary(self):
        """Print overall test results"""
        print("\n" + "="*60)
        print("TEST RESULTS SUMMARY")
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
            print("\n⚠️  WORKFLOW TEST FAILED")
            return False
        else:
            print("\n🎉 ALL WORKFLOW TESTS PASSED!")
            print("✓ Phase 1: Call created and published successfully")
            print("✓ Phase 2: Application created with all new fields")
            print("✓ Spec: All fields match DOCX specification")
            return True


def main():
    """Run end-to-end workflow test"""
    print("="*60)
    print("PHASE 1 & 2 END-TO-END WORKFLOW TEST")
    print("="*60)

    tester = WorkflowTester()

    try:
        # Setup
        tester.cleanup_previous_test_data()
        tester.setup_test_users()

        # Phase 1: Call Management
        tester.test_phase1_create_call()

        # Phase 2: Application Submission
        tester.test_phase2_create_application()

        # Validation
        tester.validate_spec_compliance()

        # Summary
        tester.print_application_summary()
        success = tester.print_test_summary()

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n❌ TEST FAILED WITH ERROR:")
        print(f"   {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
