"""
Tests for the step 5 feasibility consult request flow.

When an applicant clicks Next on step 5, a Bootstrap modal asks whether
they have actually confirmed feasibility with the relevant node(s). If
they answer "no" (or had never ticked the checkbox), they can request a
pre-submission consult, which:

- Force-resets `Application.technical_feasibility_confirmed` to False.
- Stamps `Application.consult_requested_at`.
- Treats the form as a lenient draft save.
- Dispatches one `feasibility_consult_request` email per node that has
  requested equipment, to the first active node coordinator of that node.
- Redirects to My Applications.

The Bootstrap JS chain (confirmedModal → unconfirmedModal) is client-side
and not exercised here; we test the server contract that backs both modal
paths plus a HTML render-check that the modals + hidden submit are present.
"""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from applications.models import Application, RequestedAccess
from calls.models import Call, CallEquipmentAllocation
from core.models import Organization, Node, Equipment, UserRole

User = get_user_model()


def _make_call_with_equipment(num_nodes=1, with_coordinators=True):
    """Build a Call + Organization + N Nodes + one Equipment per node, with
    optional NodeCoordinator UserRoles. Returns (call, [equipment_list],
    [coordinator_user_list])."""
    org = Organization.objects.create(
        name='Org', country='ES', organization_type='university'
    )
    call = Call.objects.create(
        code='CALL-C', title='Consult Test',
        submission_start=timezone.now() - timedelta(days=1),
        submission_end=timezone.now() + timedelta(days=30),
        evaluation_deadline=timezone.now() + timedelta(days=60),
        execution_start=timezone.now() + timedelta(days=70),
        execution_end=timezone.now() + timedelta(days=100),
    )
    equipment_list = []
    coord_list = []
    for i in range(num_nodes):
        node = Node.objects.create(
            code=f'NODE{i}', organization=org, location='Madrid',
        )
        equipment = Equipment.objects.create(
            node=node, name=f'MRI {i}', category='mri', area='preclinical',
        )
        CallEquipmentAllocation.objects.create(call=call, equipment=equipment)
        if with_coordinators:
            coord = User.objects.create_user(
                username=f'nc{i}', email=f'nc{i}@test.com', password='x',
                first_name='Nodey', last_name=f'Coord{i}',
                phone='+34 900 000 001',
                organization=org,
                position='Coordinator',
            )
            UserRole.objects.create(
                user=coord, role='node_coordinator', node=node, is_active=True
            )
            coord_list.append(coord)
        equipment_list.append(equipment)
    return call, equipment_list, coord_list


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage'
)
class Step5ConsultRequestTests(TestCase):

    def setUp(self):
        self.org = Organization.objects.create(
            name='ApplicantOrg', country='ES', organization_type='university'
        )
        self.applicant = User.objects.create_user(
            username='applicant', email='applicant@test.com', password='x',
            first_name='Aida', last_name='Applicant',
            phone='+34 900 000 000',
            organization=self.org,
            position='Researcher',
        )
        self.client = Client()
        self.client.force_login(self.applicant)

    def _make_app(self, num_equipment_nodes=1, with_coordinators=True):
        call, equipment_list, coord_list = _make_call_with_equipment(
            num_nodes=num_equipment_nodes, with_coordinators=with_coordinators
        )
        app = Application.objects.create(
            applicant=self.applicant, call=call, code='APP-CONSULT-1',
            status='draft',
            applicant_email='applicant@test.com',
            applicant_phone='+34 900 000 000',
            applicant_name='Aida Applicant',
        )
        for eq in equipment_list:
            RequestedAccess.objects.create(
                application=app, equipment=eq, hours_requested=8
            )
        return app, coord_list

    @patch('communications.tasks.send_email_from_template')
    def test_consult_force_resets_feasibility_checkbox(self, mock_send):
        """Even if POST sends technical_feasibility_confirmed=on, the
        consult path forces it back to False so we never persist a
        consult+confirmed combination."""
        app, _ = self._make_app(num_equipment_nodes=1, with_coordinators=True)
        url = reverse('applications:edit_step5', kwargs={'pk': app.pk})
        resp = self.client.post(url, {
            'action': 'request_consult',
            'technical_feasibility_confirmed': 'on',
            'data_consent': '',
        })
        self.assertRedirects(
            resp, reverse('applications:my_applications'),
            fetch_redirect_response=False,
        )
        app.refresh_from_db()
        self.assertFalse(app.technical_feasibility_confirmed)
        self.assertIsNotNone(app.consult_requested_at)

    @patch('communications.tasks.send_email_from_template')
    def test_consult_emails_single_node_coordinator(self, mock_send):
        app, coords = self._make_app(num_equipment_nodes=1, with_coordinators=True)
        url = reverse('applications:edit_step5', kwargs={'pk': app.pk})
        self.client.post(url, {'action': 'request_consult'})
        mock_send.delay.assert_called_once()
        call_kwargs = mock_send.delay.call_args.kwargs
        self.assertEqual(call_kwargs['template_type'], 'feasibility_consult_request')
        self.assertEqual(call_kwargs['recipient_email'], coords[0].email)
        ctx = call_kwargs['context_data']
        self.assertEqual(ctx['applicant_email'], 'applicant@test.com')
        self.assertEqual(ctx['applicant_phone'], '+34 900 000 000')
        self.assertEqual(ctx['application_code'], 'APP-CONSULT-1')
        self.assertIn('http', ctx['application_url'])

    @patch('communications.tasks.send_email_from_template')
    def test_consult_emails_one_per_node(self, mock_send):
        """Two distinct nodes with two distinct NCs → two emails."""
        app, coords = self._make_app(num_equipment_nodes=2, with_coordinators=True)
        url = reverse('applications:edit_step5', kwargs={'pk': app.pk})
        self.client.post(url, {'action': 'request_consult'})
        self.assertEqual(mock_send.delay.call_count, 2)
        recipients = {c.kwargs['recipient_email'] for c in mock_send.delay.call_args_list}
        self.assertEqual(recipients, {coords[0].email, coords[1].email})

    @patch('communications.tasks.send_email_from_template')
    def test_consult_soft_path_no_equipment(self, mock_send):
        """With zero requested equipment, no emails fire but timestamp is
        still set and the redirect succeeds."""
        # Build an application with NO requested_access rows.
        call, _eq, _coords = _make_call_with_equipment(num_nodes=0)
        app = Application.objects.create(
            applicant=self.applicant, call=call, code='APP-CONSULT-EMPTY',
            status='draft',
        )
        url = reverse('applications:edit_step5', kwargs={'pk': app.pk})
        resp = self.client.post(url, {'action': 'request_consult'})
        self.assertRedirects(
            resp, reverse('applications:my_applications'),
            fetch_redirect_response=False,
        )
        mock_send.delay.assert_not_called()
        app.refresh_from_db()
        self.assertIsNotNone(app.consult_requested_at)

    @patch('communications.tasks.send_email_from_template')
    def test_consult_skips_lenient_data_consent_check(self, mock_send):
        """The normal step 5 form requires data_consent. The consult path
        uses the draft form variant, so it tolerates a missing consent."""
        app, _ = self._make_app(num_equipment_nodes=1)
        url = reverse('applications:edit_step5', kwargs={'pk': app.pk})
        resp = self.client.post(url, {
            'action': 'request_consult',
            'data_consent': '',
        })
        self.assertRedirects(
            resp, reverse('applications:my_applications'),
            fetch_redirect_response=False,
        )

    @patch('communications.tasks.send_email_from_template')
    def test_consult_repeated_overwrites_timestamp(self, mock_send):
        """Last-write-wins. Repeat consults are fine and update the
        timestamp; no duplicate-prevention required."""
        app, _ = self._make_app(num_equipment_nodes=1)
        url = reverse('applications:edit_step5', kwargs={'pk': app.pk})
        self.client.post(url, {'action': 'request_consult'})
        app.refresh_from_db()
        first = app.consult_requested_at
        self.assertIsNotNone(first)
        # Second request — verify timestamp advances.
        import time
        time.sleep(0.01)
        self.client.post(url, {'action': 'request_consult'})
        app.refresh_from_db()
        self.assertGreater(app.consult_requested_at, first)

    def test_step5_renders_modals_and_hidden_consult_submit(self):
        """Sanity check that the rendered page contains both modal blocks
        and a hidden, formnovalidate consult submit button."""
        app, _ = self._make_app(num_equipment_nodes=1)
        url = reverse('applications:edit_step5', kwargs={'pk': app.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('id="confirmedModal"', html)
        self.assertIn('id="unconfirmedModal"', html)
        self.assertIn('id="consultSubmit"', html)
        # Hidden + formnovalidate on the consult submit button.
        self.assertIn('name="action" value="request_consult"', html)
        # Ensure formnovalidate is on the consult submit (not just save_draft).
        consult_idx = html.find('id="consultSubmit"')
        self.assertNotEqual(consult_idx, -1)
        # Look for formnovalidate within the same tag.
        tag_end = html.find('>', consult_idx)
        self.assertIn('formnovalidate', html[consult_idx:tag_end])

    @patch('communications.tasks.send_email_from_template')
    def test_next_path_without_consult_still_redirects_to_preview(self, mock_send):
        """The plain Next path (no action) is unchanged: normal full-validation
        form, redirects to preview when valid."""
        app, _ = self._make_app(num_equipment_nodes=1)
        url = reverse('applications:edit_step5', kwargs={'pk': app.pk})
        resp = self.client.post(url, {
            'technical_feasibility_confirmed': 'on',
            'data_consent': 'on',
        })
        self.assertRedirects(
            resp, reverse('applications:preview', kwargs={'pk': app.pk}),
            fetch_redirect_response=False,
        )
        app.refresh_from_db()
        self.assertTrue(app.technical_feasibility_confirmed)
        self.assertIsNone(app.consult_requested_at)
        mock_send.delay.assert_not_called()
