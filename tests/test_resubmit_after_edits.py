"""
A draft a node sent back for edits can be resubmitted after the deadline.

Feasibility review runs past the call's `submission_end`. When a node picked
**Request Edits** after the deadline, the application went back to `draft`,
the applicant could edit it, and `application_submit` then refused it with
"Submission deadline has passed." It sat in draft for good (REDIB-2601-020
was pushed through by hand).

The exemption is `Application.can_resubmit_after_deadline`: a draft with a
`FeasibilityReview` row (only a real submission creates one, and Request
Edits keeps it), on a call that is not yet `resolved`. A first submission's
rule is unchanged: refused after the deadline.
"""
from datetime import timedelta

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from applications.models import Application, RequestedAccess
from calls.models import Call, CallEquipmentAllocation
from communications.models import EmailLog, EmailTemplate
from core.models import Equipment, Node, Organization, UserRole
from core.test_utils import create_complete_user


SENT_BACK_BANNER = 'The call has closed, but a node asked for edits, so you can still resubmit.'
CLOSED_BANNER = 'it can no longer be submitted'


def _seed_templates():
    for tt in ('application_received', 'feasibility_request', 'feasibility_edits_requested'):
        EmailTemplate.objects.get_or_create(
            template_type=tt,
            defaults={
                'subject': f'[test] {tt}',
                'html_content': '<p>{{ application_code }}</p>',
                'text_content': '{{ application_code }}',
                'is_active': True,
            },
        )


class ResubmitAfterEditsTest(TestCase):

    def setUp(self):
        _seed_templates()
        self.client = Client()

        org, _ = Organization.objects.get_or_create(
            name='Node Host',
            defaults={'organization_type': 'pro', 'iso2': 'ES', 'country': 'Spain'},
        )
        self.node = Node.objects.create(code='RSB', organization=org, location='Here')
        self.equipment = Equipment.objects.create(
            node=self.node, name='Scanner', category='mri', is_essential=True,
        )

        self.nc = create_complete_user('nc.rsb@example.org')
        UserRole.objects.create(
            user=self.nc, role='node_coordinator', node=self.node, is_active=True,
        )

        self.applicant = create_complete_user('pi.rsb@example.org')
        UserRole.objects.create(user=self.applicant, role='applicant', is_active=True)

        now = timezone.now()
        self.call = Call.objects.create(
            code='RSB1', title='Resubmit call', status='open',
            submission_start=now - timedelta(days=5),
            submission_end=now + timedelta(days=30),
            evaluation_deadline=now + timedelta(days=60),
            execution_start=now + timedelta(days=90),
            execution_end=now + timedelta(days=180),
        )
        CallEquipmentAllocation.objects.create(call=self.call, equipment=self.equipment)

    def _draft(self):
        """A draft complete enough to pass every guard in application_submit."""
        app = Application.objects.create(
            call=self.call, applicant=self.applicant, status='draft',
            applicant_name='Test PI', applicant_entity='Test Organization',
            applicant_email='pi.rsb@example.org', applicant_phone='+34 900 000 000',
            project_name='A project',
            subject_area='Health', brief_description='Brief.',
            service_modality='in_person', specialization_area='preclinical',
            scientific_relevance='x', methodology_description='x',
            expected_contributions='x', impact_strengths='x',
            socioeconomic_significance='x', opportunity_criteria='x',
            data_consent=True,
        )
        RequestedAccess.objects.create(
            application=app, equipment=self.equipment, hours_requested=10,
        )
        return app

    def _submit(self, app):
        self.client.force_login(self.applicant)
        return self.client.post(reverse('applications:submit', kwargs={'pk': app.pk}))

    def _close_call(self, status='closed'):
        """The deadline passes, as `check_call_deadlines` would record it."""
        Call.objects.filter(pk=self.call.pk).update(
            status=status, submission_end=timezone.now() - timedelta(days=1),
        )

    def _sent_back_draft(self, call_status='closed'):
        """Submitted on time, sent back by the node after the deadline."""
        app = self._draft()
        self._submit(app)
        self._close_call(call_status)

        review = app.feasibility_reviews.get()
        self.client.force_login(self.nc)
        self.client.post(
            reverse('applications:feasibility_review', kwargs={'pk': review.pk}),
            {'decision': 'edits_requested', 'comments': 'Please fix the methodology.'},
        )
        app.refresh_from_db()
        self.assertEqual(app.status, 'draft')
        return app

    def _messages(self, response):
        return [m.message for m in response.wsgi_request._messages]

    # ------------------------------------------------------------ the submit

    def test_sent_back_draft_resubmits_after_the_deadline(self):
        app = self._sent_back_draft()
        code = app.code
        EmailLog.objects.all().delete()

        response = self._submit(app)

        self.assertNotIn('Submission deadline has passed.', self._messages(response))
        app.refresh_from_db()
        self.assertEqual(app.status, 'under_feasibility_review')
        self.assertEqual(app.code, code)

        review = app.feasibility_reviews.get()
        self.assertEqual(review.status, 'pending')
        self.assertIsNone(review.is_feasible)
        self.assertIsNone(review.reviewed_at)
        self.assertEqual(review.comments, '')

        # Back in the node's queue, and the node is told.
        self.client.force_login(self.nc)
        queue = self.client.get(reverse('applications:feasibility_queue'))
        self.assertContains(queue, code)
        self.assertTrue(
            EmailLog.objects.filter(
                template__template_type='feasibility_request',
                recipient_email='nc.rsb@example.org',
            ).exists()
        )

    def test_sent_back_draft_is_refused_once_the_call_is_resolved(self):
        app = self._sent_back_draft(call_status='resolved')

        response = self._submit(app)

        self.assertIn('Submission deadline has passed.', self._messages(response))
        app.refresh_from_db()
        self.assertEqual(app.status, 'draft')
        self.assertEqual(app.feasibility_reviews.get().status, 'edits_requested')

    def test_never_submitted_draft_is_still_refused_after_the_deadline(self):
        app = self._draft()
        self._close_call()

        response = self._submit(app)

        self.assertIn('Submission deadline has passed.', self._messages(response))
        app.refresh_from_db()
        self.assertEqual(app.status, 'draft')
        self.assertFalse(app.feasibility_reviews.exists())

    # ---------------------------------------------------- what the applicant sees

    def test_my_applications_offers_continue_for_a_sent_back_draft(self):
        app = self._sent_back_draft()
        self.client.force_login(self.applicant)

        response = self.client.get(reverse('applications:my_applications'))

        self.assertContains(response, reverse('applications:edit_step2', kwargs={'pk': app.pk}))
        self.assertNotContains(response, 'Call closed')

    def test_my_applications_shows_call_closed_for_a_never_submitted_draft(self):
        app = self._draft()
        self._close_call()
        self.client.force_login(self.applicant)

        response = self.client.get(reverse('applications:my_applications'))

        self.assertContains(response, 'Call closed')
        self.assertNotContains(response, reverse('applications:edit_step2', kwargs={'pk': app.pk}))

    def test_my_applications_shows_call_closed_once_the_call_is_resolved(self):
        app = self._sent_back_draft(call_status='resolved')
        self.client.force_login(self.applicant)

        response = self.client.get(reverse('applications:my_applications'))

        self.assertContains(response, 'Call closed')
        self.assertNotContains(response, reverse('applications:edit_step2', kwargs={'pk': app.pk}))

    def test_wizard_banner_says_a_sent_back_draft_can_be_resubmitted(self):
        app = self._sent_back_draft()
        self.client.force_login(self.applicant)

        response = self.client.get(reverse('applications:edit_step2', kwargs={'pk': app.pk}))

        self.assertContains(response, SENT_BACK_BANNER)
        self.assertNotContains(response, CLOSED_BANNER)

    def test_wizard_banner_says_a_never_submitted_draft_cannot_be_submitted(self):
        app = self._draft()
        self._close_call()
        self.client.force_login(self.applicant)

        response = self.client.get(reverse('applications:edit_step2', kwargs={'pk': app.pk}))

        self.assertContains(response, CLOSED_BANNER)
        self.assertNotContains(response, SENT_BACK_BANNER)
