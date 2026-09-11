"""
Regression tests for the rehearsal-guards branch (docs/handoffs/rehearsal-guards.md).

Silent state changes the 2026-09-08 dress rehearsal found — nothing threw, so
nothing in the suite had caught them:

- #73: Auto-Assign Evaluators closed a call that was still accepting
  applications. It may close the call only once `submission_end` has passed —
  the same condition as `calls.tasks.check_call_deadlines`.
- #74: Promote to Accepted left the node's NodeResolution on 'waitlist', so
  the published resolution table printed Wait List for someone granted
  access. Promotion now records 'accept' on every waitlisted node row.

And the seed half of #80: `seed_email_templates` runs on every container
start, so it sets `is_active` on create only — the admin's per-template off
switch has to survive a deploy.
"""
import io
from datetime import timedelta
from decimal import Decimal

from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from applications.models import Application, NodeResolution, RequestedAccess
from applications.services import NodeResolutionService
from calls.models import Call
from communications.models import EmailTemplate
from core.models import Equipment, Node, Organization, UserRole
from core.test_utils import create_complete_user
from evaluations.models import Evaluation
from evaluations.tasks import assign_evaluators_to_call
from reports.resolution_table import build_resolution_table


def _make_org(name):
    return Organization.objects.create(
        name=name, organization_type='other', iso2='ES', country='Spain',
    )


class AutoAssignKeepsLiveCallOpenTest(TestCase):
    """#73 — auto-assign must not close a call inside its submission window."""

    def setUp(self):
        self.call = Call.objects.create(
            code='GUARD-73', title='Guard call',
            status='open',
            submission_start=timezone.now() - timedelta(days=10),
            submission_end=timezone.now() + timedelta(days=20),
            evaluation_deadline=timezone.now() + timedelta(days=40),
            execution_start=timezone.now() + timedelta(days=50),
            execution_end=timezone.now() + timedelta(days=200),
        )
        applicant = create_complete_user(
            email='applicant@guard.test', organization=_make_org('Applicant Org'),
        )
        self.application = Application.objects.create(
            applicant=applicant, call=self.call, code='GUARD-73-001',
            brief_description='guard', status='pending_evaluation',
        )
        self.coordinator = create_complete_user(email='coord@guard.test')
        UserRole.objects.create(user=self.coordinator, role='coordinator', is_active=True)

    def _add_evaluators(self, n=2):
        for i in range(n):
            ev = create_complete_user(
                email=f'ev{i}@guard.test', organization=_make_org(f'Evaluator Org {i}'),
            )
            UserRole.objects.create(user=ev, role='evaluator', is_active=True)

    def test_assignment_inside_window_leaves_call_open(self):
        self._add_evaluators(2)

        assign_evaluators_to_call(self.call.id, num_evaluators=2)

        self.assertEqual(Evaluation.objects.filter(application=self.application).count(), 2)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'under_evaluation')
        self.call.refresh_from_db()
        self.assertEqual(self.call.status, 'open')

    def test_assignment_after_deadline_still_closes_call(self):
        self.call.submission_end = timezone.now() - timedelta(days=1)
        self.call.save()
        self._add_evaluators(2)

        assign_evaluators_to_call(self.call.id, num_evaluators=2)

        self.call.refresh_from_db()
        self.assertEqual(self.call.status, 'closed')

    def test_empty_pool_inside_window_leaves_call_open(self):
        # No evaluators at all: the task takes its early return.
        result = assign_evaluators_to_call(self.call.id, num_evaluators=2)

        self.assertEqual(result['pool_size'], 0)
        self.call.refresh_from_db()
        self.assertEqual(self.call.status, 'open')

    def test_assignment_page_warns_while_call_is_open(self):
        client = Client()
        client.force_login(self.coordinator)
        url = reverse('evaluations:call_assignment_detail', kwargs={'call_id': self.call.id})

        resp = client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'This call is still accepting applications until')

        self.call.status = 'closed'
        self.call.save()
        resp = client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Auto-Assign Evaluators')  # the form is still there
        self.assertNotContains(resp, 'still accepting applications')


class PromotionRecordsNodeDecisionTest(TestCase):
    """#74 — promoting from the waitlist updates the node's NodeResolution."""

    def setUp(self):
        self.call = Call.objects.create(
            code='GUARD-74', title='Guard call',
            status='resolved',
            submission_start=timezone.now() - timedelta(days=60),
            submission_end=timezone.now() - timedelta(days=30),
            evaluation_deadline=timezone.now() - timedelta(days=10),
            execution_start=timezone.now() + timedelta(days=5),
            execution_end=timezone.now() + timedelta(days=200),
            resolutions_released=True,
        )
        self.applicant = create_complete_user(email='applicant@guard.test')
        self.application = Application.objects.create(
            applicant=self.applicant, call=self.call, code='GUARD-74-001',
            brief_description='guard', status='evaluated', final_score=Decimal('6.0'),
            applicant_email='applicant@guard.test',
        )
        self.node_a, self.eq_a, self.nc_a = self._make_node('GA')

    def _make_node(self, code):
        node = Node.objects.create(
            code=code, organization=_make_org(f'{code} Host'), location='Here',
        )
        equipment = Equipment.objects.create(node=node, name=f'{code} Scanner', category='mri')
        RequestedAccess.objects.create(
            application=self.application, equipment=equipment, hours_requested=Decimal('8'),
        )
        nc = create_complete_user(email=f'nc-{code.lower()}@guard.test')
        UserRole.objects.create(user=nc, role='node_coordinator', node=node, is_active=True)
        return node, equipment, nc

    def _resolve(self, node, equipment, nc, resolution, comments):
        NodeResolutionService(node=node).apply_node_resolution(
            application=self.application, resolution=resolution, comments=comments,
            approved_hours_dict={equipment.id: Decimal('8')}, user=nc,
        )

    def _promote(self, user):
        self.application.refresh_from_db()
        self.application.accepted_by_applicant = True
        self.application.save()
        client = Client()
        client.force_login(user)
        resp = client.post(
            reverse('applications:promote_waitlisted', kwargs={'pk': self.application.pk})
        )
        self.assertEqual(resp.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'accepted')

    def test_promotion_records_accept_on_the_node(self):
        self._resolve(self.node_a, self.eq_a, self.nc_a, 'waitlist', 'no immediate slot')
        nr = NodeResolution.objects.get(application=self.application, node=self.node_a)
        waitlisted_at = nr.reviewed_at
        # A different coordinator of the same node promotes.
        promoter = create_complete_user(
            email='promoter@guard.test', first_name='Pat', last_name='Promoter',
        )
        UserRole.objects.create(
            user=promoter, role='node_coordinator', node=self.node_a, is_active=True,
        )

        self._promote(promoter)

        nr.refresh_from_db()
        self.assertEqual(nr.resolution, 'accept')
        self.assertGreater(nr.reviewed_at, waitlisted_at)
        self.assertEqual(
            nr.comments,
            'no immediate slot\n\nPromoted from the waitlist by Pat Promoter '
            f'on {timezone.now().date().isoformat()}.',
        )
        self.assertEqual(nr.reviewer, self.nc_a)  # who made the original decision
        self.assertEqual(nr.history.first().resolution, 'accept')

    def test_resolution_table_reads_accepted_after_promotion(self):
        self._resolve(self.node_a, self.eq_a, self.nc_a, 'waitlist', '')
        self._promote(self.nc_a)

        for lang, label in (('en', 'Accepted'), ('es', 'Aceptada')):
            table = build_resolution_table(self.call, lang)
            row = next(r for r in table['rows'] if r['code'] == 'GUARD-74-001')
            self.assertEqual(row['resolutions'], [label])

    def test_every_waitlisted_node_is_promoted(self):
        node_b, eq_b, nc_b = self._make_node('GB')
        self._resolve(self.node_a, self.eq_a, self.nc_a, 'accept', 'fine by us')
        self._resolve(node_b, eq_b, nc_b, 'waitlist', 'no slot yet')
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'pending')
        row_a = NodeResolution.objects.get(application=self.application, node=self.node_a)
        a_reviewed_at = row_a.reviewed_at

        self._promote(nc_b)

        resolutions = dict(
            NodeResolution.objects.filter(application=self.application)
            .values_list('node__code', 'resolution')
        )
        self.assertEqual(resolutions, {'GA': 'accept', 'GB': 'accept'})
        row_a.refresh_from_db()
        self.assertEqual(row_a.comments, 'fine by us')
        self.assertEqual(row_a.reviewed_at, a_reviewed_at)

    def test_reject_row_is_never_touched(self):
        # Cannot arise under the aggregation (any reject -> rejected), so
        # build the rows directly: this pins the filter, not the workflow.
        node_b, _, nc_b = self._make_node('GB')
        self.application.status = 'pending'
        self.application.resolution = 'pending'
        self.application.save()
        NodeResolution.objects.create(
            application=self.application, node=self.node_a, reviewer=self.nc_a,
            resolution='reject', comments='no',
        )
        NodeResolution.objects.create(
            application=self.application, node=node_b, reviewer=nc_b, resolution='waitlist',
        )

        self._promote(nc_b)

        row_a = NodeResolution.objects.get(application=self.application, node=self.node_a)
        self.assertEqual(row_a.resolution, 'reject')
        self.assertEqual(row_a.comments, 'no')
        self.assertEqual(
            NodeResolution.objects.get(application=self.application, node=node_b).resolution,
            'accept',
        )


class SeedKeepsAdminOffSwitchTest(TestCase):
    """#80(c) — reseeding refreshes content but never reactivates a template."""

    def _seed(self):
        call_command('seed_email_templates', stdout=io.StringIO())

    def test_deactivated_template_stays_off_and_content_refreshes(self):
        self._seed()
        template = EmailTemplate.objects.get(template_type='completion_reminder_coordinator')
        seeded_subject = template.subject
        template.is_active = False
        template.subject = 'edited in the admin'
        template.save()

        self._seed()

        template.refresh_from_db()
        self.assertFalse(template.is_active)
        self.assertEqual(template.subject, seeded_subject)

    def test_missing_template_is_created_active(self):
        self._seed()
        EmailTemplate.objects.filter(template_type='completion_reminder_coordinator').delete()

        self._seed()

        template = EmailTemplate.objects.get(template_type='completion_reminder_coordinator')
        self.assertTrue(template.is_active)
        self.assertTrue(template.subject)
        self.assertTrue(template.html_content)
