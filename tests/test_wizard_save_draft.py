"""
Tests for the wizard's "Save Draft" action.

Regression: applicants previously lost any unsaved input when clicking a fake
"Save Draft Application" link that was just a dashboard nav (not a form
submit). The button now POSTs action=save_draft to the current step view,
which persists partial input through relaxed-validation form variants.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from applications.models import Application, RequestedAccess
from calls.models import Call, CallEquipmentAllocation
from core.models import Organization, Node, Equipment

User = get_user_model()


def _make_call():
    org = Organization.objects.create(
        name='Org', country='ES', organization_type='university'
    )
    node = Node.objects.create(code='N1', organization=org, location='Madrid')
    equipment = Equipment.objects.create(
        node=node, name='MRI 7T', category='mri', area='preclinical'
    )
    call = Call.objects.create(
        code='CALL-DRAFT', title='Draft Test',
        submission_start=timezone.now() - timedelta(days=1),
        submission_end=timezone.now() + timedelta(days=30),
        evaluation_deadline=timezone.now() + timedelta(days=60),
        execution_start=timezone.now() + timedelta(days=70),
        execution_end=timezone.now() + timedelta(days=100),
    )
    CallEquipmentAllocation.objects.create(call=call, equipment=equipment)
    return call, equipment


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage'
)
class WizardSaveDraftTests(TestCase):
    """Each step's Save Draft button persists partial input and redirects."""

    def setUp(self):
        org = Organization.objects.create(
            name='Org', country='ES', organization_type='university'
        )
        self.user = User.objects.create_user(
            username='applicant', email='a@test.com', password='x',
            first_name='Aida', last_name='Test',
            phone='+34 900 000 000',
            organization=org,
            position='Researcher',
        )
        self.call, self.equipment = _make_call()
        self.app = Application.objects.create(
            applicant=self.user, call=self.call, code='APP-DRAFT-1',
            status='draft',
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_step2_save_draft_persists_partial_input(self):
        """Brief description saves even though competitive-funding agency is missing."""
        url = reverse('applications:edit_step2', kwargs={'pk': self.app.pk})
        resp = self.client.post(url, {
            'action': 'save_draft',
            'brief_description': 'partial summary, no agency yet',
            'subject_area': '',
            'has_competitive_funding': 'on',
            'project_code': '',
            'funding_agency_obj': '__other__',
            'new_funding_agency_name': '',
            'new_funding_agency_origin_of_funds': '',
        })
        self.assertRedirects(
            resp, reverse('applications:my_applications'),
            fetch_redirect_response=False,
        )
        self.app.refresh_from_db()
        self.assertEqual(self.app.brief_description, 'partial summary, no agency yet')
        self.assertTrue(self.app.has_competitive_funding)
        self.assertIsNone(self.app.funding_agency_obj)

    def test_step2_next_still_enforces_validation(self):
        """The Next path keeps the strict validation it always had."""
        url = reverse('applications:edit_step2', kwargs={'pk': self.app.pk})
        resp = self.client.post(url, {
            'brief_description': '',
            'subject_area': '',
            'has_competitive_funding': '',
        })
        # No redirect on validation failure — page re-renders with errors.
        self.assertEqual(resp.status_code, 200)

    def test_step3_save_draft_persists_service_modality(self):
        """Service modality saves; an empty equipment formset is tolerated."""
        url = reverse('applications:edit_step3', kwargs={'pk': self.app.pk})
        resp = self.client.post(url, {
            'action': 'save_draft',
            'service_modality': 'full_assistance',
            'specialization_area': 'preclinical',
            'requested_access-TOTAL_FORMS': '0',
            'requested_access-INITIAL_FORMS': '0',
            'requested_access-MIN_NUM_FORMS': '0',
            'requested_access-MAX_NUM_FORMS': '1000',
        })
        self.assertRedirects(
            resp, reverse('applications:my_applications'),
            fetch_redirect_response=False,
        )
        self.app.refresh_from_db()
        self.assertEqual(self.app.service_modality, 'full_assistance')
        self.assertEqual(self.app.specialization_area, 'preclinical')

    def test_step3_save_draft_persists_complete_equipment_row(self):
        """A fully-filled equipment row saves alongside the service modality."""
        url = reverse('applications:edit_step3', kwargs={'pk': self.app.pk})
        resp = self.client.post(url, {
            'action': 'save_draft',
            'service_modality': 'self_service',
            'specialization_area': 'preclinical',
            'requested_access-TOTAL_FORMS': '1',
            'requested_access-INITIAL_FORMS': '0',
            'requested_access-MIN_NUM_FORMS': '0',
            'requested_access-MAX_NUM_FORMS': '1000',
            'requested_access-0-id': '',
            'requested_access-0-equipment': str(self.equipment.pk),
            'requested_access-0-hours_requested': '12',
            'requested_access-0-DELETE': '',
        })
        self.assertRedirects(
            resp, reverse('applications:my_applications'),
            fetch_redirect_response=False,
        )
        self.app.refresh_from_db()
        self.assertEqual(self.app.service_modality, 'self_service')
        self.assertEqual(self.app.requested_access.count(), 1)
        ra = self.app.requested_access.first()
        self.assertEqual(ra.equipment_id, self.equipment.pk)
        self.assertEqual(ra.hours_requested, Decimal('12'))

    def test_step4_save_draft_persists_partial_text(self):
        """A partial scientific-content textarea saves even with other fields blank."""
        url = reverse('applications:edit_step4', kwargs={'pk': self.app.pk})
        resp = self.client.post(url, {
            'action': 'save_draft',
            'scientific_relevance': 'first draft of relevance section',
            'methodology_description': '',
            'expected_contributions': '',
            'impact_strengths': '',
            'socioeconomic_significance': '',
            'opportunity_criteria': '',
        })
        self.assertRedirects(
            resp, reverse('applications:my_applications'),
            fetch_redirect_response=False,
        )
        self.app.refresh_from_db()
        self.assertEqual(
            self.app.scientific_relevance, 'first draft of relevance section'
        )
        self.assertEqual(self.app.methodology_description, '')

    def test_step5_save_draft_without_data_consent(self):
        """Step 5 normally requires data_consent — drafts don't."""
        url = reverse('applications:edit_step5', kwargs={'pk': self.app.pk})
        resp = self.client.post(url, {
            'action': 'save_draft',
            'uses_animals': 'on',
            'data_consent': '',
        })
        self.assertRedirects(
            resp, reverse('applications:my_applications'),
            fetch_redirect_response=False,
        )
        self.app.refresh_from_db()
        self.assertTrue(self.app.uses_animals)
        self.assertFalse(self.app.data_consent)

    def test_step5_next_still_requires_data_consent(self):
        """Next on step 5 still enforces the consent rule."""
        url = reverse('applications:edit_step5', kwargs={'pk': self.app.pk})
        resp = self.client.post(url, {
            'uses_animals': '',
            'data_consent': '',
        })
        self.assertEqual(resp.status_code, 200)
        self.app.refresh_from_db()
        # Status should still be draft (not advanced).
        self.assertEqual(self.app.status, 'draft')

    def test_save_draft_button_skips_html5_validation(self):
        """Save Draft must carry `formnovalidate` so the browser doesn't
        block the submit on required-but-blank fields (the regular form
        renders each input with the `required` attribute)."""
        for step_url_name in ('edit_step2', 'edit_step3', 'edit_step4', 'edit_step5'):
            url = reverse(f'applications:{step_url_name}', kwargs={'pk': self.app.pk})
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, step_url_name)
            html = resp.content.decode()
            self.assertIn('name="action" value="save_draft"', html, step_url_name)
            self.assertIn('formnovalidate', html, step_url_name)
