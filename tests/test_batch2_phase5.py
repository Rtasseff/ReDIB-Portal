"""
Integration tests for fixes-batch-2 Phase 5 (batch 2-E): applicant
form polish.

- ORCID regex validator rejects malformed ids.
- Phone validator rejects alphabetic noise.
- Step 5 accepts has_insurance and has_informed_consent; application
  saves with both False (not required), both True, or any combination.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from applications.models import Application
from calls.models import Call
from core.models import ORCID_VALIDATOR, PHONE_VALIDATOR

User = get_user_model()


class OrcidValidatorTest(TestCase):
    def test_accepts_standard_orcid(self):
        ORCID_VALIDATOR('0000-0002-1825-0097')  # no raise

    def test_accepts_orcid_ending_in_X(self):
        ORCID_VALIDATOR('0000-0002-1825-009X')

    def test_rejects_letters(self):
        with self.assertRaises(ValidationError):
            ORCID_VALIDATOR('ABCD-0002-1825-0097')

    def test_rejects_wrong_separator(self):
        with self.assertRaises(ValidationError):
            ORCID_VALIDATOR('0000 0002 1825 0097')

    def test_rejects_too_short(self):
        with self.assertRaises(ValidationError):
            ORCID_VALIDATOR('0000-0002-1825')


class PhoneValidatorTest(TestCase):
    def test_accepts_common_formats(self):
        for n in ('+34 900 000 000', '(555) 123-4567', '+1.555.123.4567', '555-1234'):
            PHONE_VALIDATOR(n)

    def test_rejects_letters(self):
        with self.assertRaises(ValidationError):
            PHONE_VALIDATOR('call-me')

    def test_rejects_too_short(self):
        with self.assertRaises(ValidationError):
            PHONE_VALIDATOR('12')


class HumanSubjectsExtraDeclarationsTest(TestCase):
    """has_insurance and has_informed_consent should be writable on an
    Application and should not be required (default False)."""

    def test_defaults_are_false_and_save_succeeds(self):
        from django.utils import timezone
        from datetime import timedelta
        user = User.objects.create_user(username='u', email='u@test.com', password='x')
        call = Call.objects.create(
            code='CALL-D', title='T',
            submission_start=timezone.now() - timedelta(days=1),
            submission_end=timezone.now() + timedelta(days=30),
            evaluation_deadline=timezone.now() + timedelta(days=60),
            execution_start=timezone.now() + timedelta(days=70),
            execution_end=timezone.now() + timedelta(days=100),
        )
        app = Application.objects.create(
            applicant=user, call=call, code='APP-D1',
            brief_description='ok',
        )
        self.assertFalse(app.has_insurance)
        self.assertFalse(app.has_informed_consent)

        # Toggle both true — should save without error.
        app.has_insurance = True
        app.has_informed_consent = True
        app.save()
        app.refresh_from_db()
        self.assertTrue(app.has_insurance)
        self.assertTrue(app.has_informed_consent)
