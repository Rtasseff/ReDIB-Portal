"""
#48 — a node with no active coordinator must not be silently dropped from
feasibility review.

`application_submit` built a `FeasibilityReview` per node under
`if node_coordinators:`, so a node with zero active `node_coordinator` roles
got no row and nothing warned. Two consequences, and the second is the one
that bites: the node's equipment was never assessed, *and* the application
advanced anyway — the completion check counts pending rows over
`application.feasibility_reviews.all()`, and a row that does not exist
contributes nothing to that count. So the application reached
`pending_evaluation` with a blind spot no screen showed.

Latent on production (every node has a coordinator today), but the trigger is
a role change during call prep, which is exactly what happens in the weeks
before a call opens.

The fix mirrors the public consult path (`calls/services.py
_alert_redib_coordinators`): create the review regardless, park the
non-nullable `reviewer` FK on a ReDIB coordinator, and tell the ReDIB
coordinator(s) so a human can give the node a coordinator.

Note what the fallback does *not* do: it grants nobody the right to review.
Two gates stand in the way, and they fail differently — `@node_coordinator_required`
redirects anyone with no node_coordinator role at all (the ReDIB coordinator),
while `feasibility_review`'s own node-scoped check raises `Http404` for a node
coordinator of some other node. The row exists to hold the application, not to
be actioned by whoever the FK happens to name.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from applications.models import Application, FeasibilityReview, RequestedAccess
from calls.models import Call, CallEquipmentAllocation
from communications.models import EmailLog, EmailTemplate
from core.models import Equipment, Node, Organization, UserRole
from core.test_utils import create_complete_user

User = get_user_model()


def _make_node(code):
    org, _ = Organization.objects.get_or_create(
        name=f'{code} Host',
        defaults={'organization_type': 'pro', 'iso2': 'ES', 'country': 'Spain'},
    )
    return Node.objects.create(code=code, organization=org, location='Here')


def _seed_templates():
    for tt in ('application_received', 'feasibility_request'):
        EmailTemplate.objects.get_or_create(
            template_type=tt,
            defaults={
                'subject': f'[test] {tt}',
                'html_content': '<p>{{ application_code }} {{ node_name }}</p>',
                'text_content': '{{ application_code }} {{ node_name }}',
                'is_active': True,
            },
        )


class FeasibilityNoCoordinatorTest(TestCase):

    def setUp(self):
        _seed_templates()
        self.client = Client()

        self.org = Organization.objects.get_or_create(
            name='Applicant Org',
            defaults={'organization_type': 'hei', 'iso2': 'ES', 'country': 'Spain'},
        )[0]

        # Two nodes: one staffed, one that will lose its coordinator.
        self.staffed_node = _make_node('STAFFED')
        self.orphan_node = _make_node('ORPHAN')

        self.staffed_equipment = Equipment.objects.create(
            node=self.staffed_node, name='Staffed Scanner',
            category='mri', is_essential=True,
        )
        self.orphan_equipment = Equipment.objects.create(
            node=self.orphan_node, name='Orphan Scanner',
            category='pet', is_essential=True,
        )

        self.nc = create_complete_user('nc.staffed@example.org')
        UserRole.objects.create(
            user=self.nc, role='node_coordinator',
            node=self.staffed_node, is_active=True,
        )

        # The orphan node's coordinator exists but has been deactivated —
        # the realistic trigger, not a node that never had one.
        self.former_nc = create_complete_user('nc.former@example.org')
        self.former_role = UserRole.objects.create(
            user=self.former_nc, role='node_coordinator',
            node=self.orphan_node, is_active=False,
        )

        self.redib_coordinator = create_complete_user('coordinator@example.org')
        UserRole.objects.create(
            user=self.redib_coordinator, role='coordinator', is_active=True,
        )

        self.applicant = create_complete_user(
            'pi@example.org', organization=self.org,
        )
        UserRole.objects.create(user=self.applicant, role='applicant', is_active=True)

        now = timezone.now()
        self.call = Call.objects.create(
            code='NC48', title='No-coordinator call', status='open',
            submission_start=now - timedelta(days=5),
            submission_end=now + timedelta(days=30),
            evaluation_deadline=now + timedelta(days=60),
            execution_start=now + timedelta(days=90),
            execution_end=now + timedelta(days=180),
        )
        for eq in (self.staffed_equipment, self.orphan_equipment):
            CallEquipmentAllocation.objects.create(call=self.call, equipment=eq)

        self.client.force_login(self.applicant)

    def _draft(self, *equipment):
        """A draft complete enough to pass every guard in application_submit."""
        app = Application.objects.create(
            call=self.call, applicant=self.applicant, status='draft',
            applicant_name='Test PI', applicant_entity='Applicant Org',
            applicant_email='pi@example.org', applicant_phone='+34 900 000 000',
            project_name='A project',
            subject_area='Health', brief_description='Brief.',
            service_modality='in_person', specialization_area='preclinical',
            scientific_relevance='x', methodology_description='x',
            expected_contributions='x', impact_strengths='x',
            socioeconomic_significance='x', opportunity_criteria='x',
            data_consent=True,
        )
        for eq in equipment:
            RequestedAccess.objects.create(
                application=app, equipment=eq, hours_requested=10,
            )
        return app

    def _submit(self, app):
        return self.client.post(
            reverse('applications:submit', kwargs={'pk': app.pk}), follow=True
        )

    # ---------------------------------------------------------------- the fix

    def test_orphan_node_still_gets_a_feasibility_review(self):
        """The regression test. Before the fix this row was never created."""
        app = self._draft(self.staffed_equipment, self.orphan_equipment)
        self._submit(app)

        nodes_reviewed = set(
            app.feasibility_reviews.values_list('node__code', flat=True)
        )
        self.assertEqual(nodes_reviewed, {'STAFFED', 'ORPHAN'})

    def test_the_application_is_held_rather_than_advancing_past_the_gap(self):
        """The consequence that mattered.

        With no row for ORPHAN, approving STAFFED used to satisfy the
        completion check and move the application to `pending_evaluation` —
        past a review that never happened. It must now stay put.
        """
        app = self._draft(self.staffed_equipment, self.orphan_equipment)
        self._submit(app)
        app.refresh_from_db()
        self.assertEqual(app.status, 'under_feasibility_review')

        staffed_review = app.feasibility_reviews.get(node=self.staffed_node)
        self.client.force_login(self.nc)
        self.client.post(
            reverse('applications:feasibility_review', kwargs={'pk': staffed_review.pk}),
            {'decision': 'approved', 'comments': 'Fine here.'},
            follow=True,
        )

        app.refresh_from_db()
        self.assertEqual(app.status, 'under_feasibility_review')
        self.assertTrue(
            app.feasibility_reviews.filter(node=self.orphan_node, status='pending').exists()
        )

    def test_the_fallback_reviewer_is_a_redib_coordinator(self):
        app = self._draft(self.orphan_equipment)
        self._submit(app)

        review = app.feasibility_reviews.get(node=self.orphan_node)
        self.assertEqual(review.reviewer, self.redib_coordinator)

    def test_the_fallback_grants_no_right_to_review(self):
        """`reviewer` is a default assignee, not an authorization.

        The ReDIB coordinator named on the row still cannot open the review:
        `@node_coordinator_required` turns them away before the view runs,
        because they hold no `node_coordinator` role at all. The alert email
        says as much and links to the application instead; this pins it.
        """
        app = self._draft(self.orphan_equipment)
        self._submit(app)
        review = app.feasibility_reviews.get(node=self.orphan_node)

        url = reverse('applications:feasibility_review', kwargs={'pk': review.pk})
        self.client.force_login(self.redib_coordinator)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(response['Location'], url)

    def test_a_coordinator_of_another_node_cannot_open_the_review(self):
        """The second gate, and the reason the fallback is safe.

        A node coordinator clears the decorator but is stopped by
        `feasibility_review`'s own node-scoped check, which raises Http404.
        So the orphan node's review is reachable by exactly nobody until
        someone is given a node_coordinator role for ORPHAN.
        """
        app = self._draft(self.orphan_equipment)
        self._submit(app)
        review = app.feasibility_reviews.get(node=self.orphan_node)

        self.client.force_login(self.nc)   # coordinator of STAFFED, not ORPHAN
        response = self.client.get(
            reverse('applications:feasibility_review', kwargs={'pk': review.pk})
        )
        self.assertEqual(response.status_code, 404)

    # ------------------------------------------------------------ the warning

    def test_the_redib_coordinator_is_told(self):
        app = self._draft(self.staffed_equipment, self.orphan_equipment)
        self._submit(app)

        alert = EmailLog.objects.filter(
            template__template_type='feasibility_request',
            recipient_email='coordinator@example.org',
        )
        self.assertEqual(alert.count(), 1)

    def test_the_staffed_node_coordinator_still_gets_the_normal_request(self):
        """No regression: the working path is untouched."""
        app = self._draft(self.staffed_equipment, self.orphan_equipment)
        self._submit(app)

        self.assertTrue(
            EmailLog.objects.filter(
                template__template_type='feasibility_request',
                recipient_email='nc.staffed@example.org',
            ).exists()
        )

    def test_a_deactivated_coordinator_is_not_emailed(self):
        app = self._draft(self.orphan_equipment)
        self._submit(app)

        self.assertFalse(
            EmailLog.objects.filter(recipient_email='nc.former@example.org').exists()
        )

    def test_no_alert_when_every_node_is_staffed(self):
        """The fallback must not fire on the ordinary path."""
        app = self._draft(self.staffed_equipment)
        self._submit(app)

        self.assertFalse(
            EmailLog.objects.filter(recipient_email='coordinator@example.org').exists()
        )

    def test_reactivating_the_coordinator_restores_the_normal_path(self):
        """What the alert asks the coordinator to do, and its effect."""
        self.former_role.is_active = True
        self.former_role.save()

        app = self._draft(self.orphan_equipment)
        self._submit(app)

        review = app.feasibility_reviews.get(node=self.orphan_node)
        self.assertEqual(review.reviewer, self.former_nc)
        self.assertFalse(
            EmailLog.objects.filter(recipient_email='coordinator@example.org').exists()
        )

    # ---------------------------------------------------------- the degenerate

    def test_no_coordinator_anywhere_does_not_break_the_submission(self):
        """Nobody to hold the FK and nobody to tell.

        The application still submits — an applicant must not eat a 500 for an
        administrative gap — and the missing review is logged rather than
        silently swallowed.
        """
        UserRole.objects.filter(role='coordinator').update(is_active=False)

        app = self._draft(self.orphan_equipment)
        with self.assertLogs('applications.views', level='ERROR') as captured:
            response = self._submit(app)

        self.assertEqual(response.status_code, 200)
        app.refresh_from_db()
        self.assertEqual(app.status, 'under_feasibility_review')
        self.assertFalse(app.feasibility_reviews.filter(node=self.orphan_node).exists())
        self.assertIn('ORPHAN', ''.join(captured.output))
