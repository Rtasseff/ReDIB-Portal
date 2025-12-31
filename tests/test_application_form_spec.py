#!/usr/bin/env python
"""
Independent validation test for application form specification compliance.

Tests that the application form implementation matches the official
REDIB-APP-application-form-coa-redib.docx specification.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redib.settings')
django.setup()

from applications.models import Application
from applications.forms import ApplicationStep1Form
from django.contrib.auth import get_user_model

User = get_user_model()


class SpecValidator:
    """Validate application form against specification"""

    def __init__(self):
        self.passed = []
        self.failed = []

    def test(self, name, condition, expected, actual):
        """Record test result"""
        if condition:
            self.passed.append(name)
            print(f"✅ {name}")
        else:
            self.failed.append(name)
            print(f"❌ {name}")
            print(f"   Expected: {expected}")
            print(f"   Actual: {actual}")

    def validate_model_fields(self):
        """Validate Application model has all required fields"""
        print("\n" + "="*60)
        print("1. VALIDATING APPLICATION MODEL FIELDS")
        print("="*60)

        # Check applicant information fields exist
        required_applicant_fields = [
            'applicant_name',
            'applicant_orcid',
            'applicant_entity',
            'applicant_email',
            'applicant_phone'
        ]

        model_fields = [f.name for f in Application._meta.get_fields()]

        for field_name in required_applicant_fields:
            self.test(
                f"Model has field '{field_name}'",
                field_name in model_fields,
                f"Field '{field_name}' exists",
                f"Fields: {model_fields}"
            )

        # Check field properties
        applicant_name_field = Application._meta.get_field('applicant_name')
        self.test(
            "applicant_name allows blank",
            applicant_name_field.blank,
            "blank=True",
            f"blank={applicant_name_field.blank}"
        )

        applicant_orcid_field = Application._meta.get_field('applicant_orcid')
        self.test(
            "applicant_orcid allows blank",
            applicant_orcid_field.blank,
            "blank=True",
            f"blank={applicant_orcid_field.blank}"
        )

    def validate_project_types(self):
        """Validate PROJECT_TYPES choices match spec"""
        print("\n" + "="*60)
        print("2. VALIDATING PROJECT TYPES (MUST HAVE 7 TYPES)")
        print("="*60)

        expected_types = [
            ('national', 'National'),
            ('international_non_european', 'International, non-European'),
            ('regional', 'Regional'),
            ('european', 'European'),
            ('internal', 'Internal'),
            ('private', 'Private'),
            ('other', 'Other'),
        ]

        actual_types = Application.PROJECT_TYPES

        self.test(
            "Has exactly 7 project types",
            len(actual_types) == 7,
            "7 types",
            f"{len(actual_types)} types"
        )

        for expected_code, expected_label in expected_types:
            found = any(code == expected_code and label == expected_label
                       for code, label in actual_types)
            self.test(
                f"Has project type '{expected_code}': '{expected_label}'",
                found,
                f"({expected_code}, {expected_label})",
                f"Found: {found}"
            )

    def validate_subject_areas(self):
        """Validate SUBJECT_AREAS choices match spec"""
        print("\n" + "="*60)
        print("3. VALIDATING SUBJECT AREAS (MUST HAVE 20 AEI AREAS)")
        print("="*60)

        expected_areas = [
            ('cso', 'CSO - Social Sciences'),
            ('der', 'DER - Law'),
            ('eco', 'ECO - Economy'),
            ('mlp', 'MLP - Mind, language and thought'),
            ('fla', 'FLA - Culture: Philology, literature and art'),
            ('pha', 'PHA - Studies in history and archaeology'),
            ('edu', 'EDU - Educational Sciences'),
            ('psi', 'PSI - Psychology'),
            ('mtm', 'MTM - Mathematical Sciences'),
            ('fis', 'FIS - Physical Sciences'),
            ('pin', 'PIN - Industrial production, engineering'),
            ('tic', 'TIC - Information and communications technologies'),
            ('eyt', 'EYT - Energy and Transport'),
            ('ctq', 'CTQ - Chemical sciences and technologies'),
            ('mat', 'MAT - Materials Sciences and Technology'),
            ('ctm', 'CTM - Environmental science and technology'),
            ('caa', 'CAA - Agricultural sciences'),
            ('bio', 'BIO - Biosciences and biotechnology'),
            ('bme', 'BME - Biomedicine'),
            ('other', 'Other (specify)'),
        ]

        actual_areas = Application.SUBJECT_AREAS

        self.test(
            "Has exactly 20 subject areas",
            len(actual_areas) == 20,
            "20 areas",
            f"{len(actual_areas)} areas"
        )

        for expected_code, expected_label in expected_areas:
            found = any(code == expected_code and label == expected_label
                       for code, label in actual_areas)
            self.test(
                f"Has subject area '{expected_code}': '{expected_label}'",
                found,
                f"({expected_code}, {expected_label})",
                f"Found: {found}"
            )

    def validate_form_fields(self):
        """Validate ApplicationStep1Form has all required fields"""
        print("\n" + "="*60)
        print("4. VALIDATING APPLICATION STEP 1 FORM")
        print("="*60)

        # Create a test user for form initialization
        test_user = User(
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )

        # Initialize form with user
        form = ApplicationStep1Form(user=test_user)

        expected_fields = [
            'applicant_name',
            'applicant_orcid',
            'applicant_entity',
            'applicant_email',
            'applicant_phone',
            'brief_description'
        ]

        actual_fields = list(form.fields.keys())

        self.test(
            "Form has exactly 6 fields in Step 1",
            len(actual_fields) == 6,
            "6 fields",
            f"{len(actual_fields)} fields"
        )

        for field_name in expected_fields:
            self.test(
                f"Form has field '{field_name}'",
                field_name in actual_fields,
                f"Field '{field_name}' in form",
                f"Fields: {actual_fields}"
            )

        # Check required fields
        self.test(
            "applicant_name is required",
            form.fields['applicant_name'].required,
            "required=True",
            f"required={form.fields['applicant_name'].required}"
        )

        self.test(
            "applicant_orcid is optional",
            not form.fields['applicant_orcid'].required,
            "required=False",
            f"required={form.fields['applicant_orcid'].required}"
        )

        self.test(
            "applicant_entity is required",
            form.fields['applicant_entity'].required,
            "required=True",
            f"required={form.fields['applicant_entity'].required}"
        )

        self.test(
            "applicant_email is required",
            form.fields['applicant_email'].required,
            "required=True",
            f"required={form.fields['applicant_email'].required}"
        )

        self.test(
            "applicant_phone is required",
            form.fields['applicant_phone'].required,
            "required=True",
            f"required={form.fields['applicant_phone'].required}"
        )

    def validate_templates(self):
        """Validate templates contain required fields"""
        print("\n" + "="*60)
        print("5. VALIDATING TEMPLATES")
        print("="*60)

        # Check wizard_step1.html
        wizard_template_path = 'templates/applications/wizard_step1.html'
        with open(wizard_template_path, 'r') as f:
            wizard_content = f.read()

        applicant_fields = [
            'applicant_name',
            'applicant_orcid',
            'applicant_entity',
            'applicant_email',
            'applicant_phone'
        ]

        for field in applicant_fields:
            self.test(
                f"wizard_step1.html contains '{field}'",
                field in wizard_content,
                f"Template references {field}",
                f"Found: {field in wizard_content}"
            )

        # Check preview.html
        preview_template_path = 'templates/applications/preview.html'
        with open(preview_template_path, 'r') as f:
            preview_content = f.read()

        for field in applicant_fields:
            self.test(
                f"preview.html displays '{field}'",
                field in preview_content,
                f"Template displays {field}",
                f"Found: {field in preview_content}"
            )

        # Check detail.html
        detail_template_path = 'templates/applications/detail.html'
        with open(detail_template_path, 'r') as f:
            detail_content = f.read()

        for field in applicant_fields:
            self.test(
                f"detail.html displays '{field}'",
                field in detail_content,
                f"Template displays {field}",
                f"Found: {field in detail_content}"
            )

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"✅ Passed: {len(self.passed)} tests")
        print(f"❌ Failed: {len(self.failed)} tests")

        if self.failed:
            print("\nFailed tests:")
            for test_name in self.failed:
                print(f"  - {test_name}")
            print("\n⚠️  VALIDATION FAILED - Spec not met")
            return False
        else:
            print("\n🎉 ALL TESTS PASSED - Application form meets specification!")
            return True


def main():
    """Run all validation tests"""
    print("="*60)
    print("APPLICATION FORM SPECIFICATION VALIDATION")
    print("="*60)
    print("\nValidating against REDIB-APP-application-form-coa-redib.docx")

    validator = SpecValidator()

    # Run all validation tests
    validator.validate_model_fields()
    validator.validate_project_types()
    validator.validate_subject_areas()
    validator.validate_form_fields()
    validator.validate_templates()

    # Print summary
    success = validator.print_summary()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
