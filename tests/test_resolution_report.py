"""
Tests for resolution-report (backlog #20): bilingual per-call resolution
table.

Covers:
- Row shape/order: every non-draft application, ordered by code, drafts
  excluded.
- Resolution comes from NodeResolution.resolution, not Application.status.
- Node public display names, including the defensive fallback for a node
  code not in NODE_PUBLIC_NAMES.
- Organization cell fallback chain: profile organization (short_name ·
  name, or name alone) -> applicant_entity -> empty.
- The four decision-7 edge cases: no NodeResolution at all, a blank
  ('Not Decided') NodeResolution, an applicant with no profile
  organization, and a call with zero non-draft applications.
- Multi-node application: one row, stacked node/resolution cells in a
  consistent order across both languages.
- The resolutions_released warning banner (decision 8), shown but never
  gating the render.
- Read-only: neither the page nor either CSV writes to Application,
  NodeResolution, ReportGeneration, or any Historical* table.
- Access control: coordinator-only.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from applications.models import Application, NodeResolution
from calls.models import Call
from core.models import Node, Organization, UserRole
from core.test_utils import create_complete_user
from reports.models import ReportGeneration
from reports.resolution_table import build_resolution_table, MISSING

User = get_user_model()


def _make_org(name, short_name=''):
    return Organization.objects.create(
        name=name, short_name=short_name,
        organization_type='other', iso2='ES', country='Spain',
    )


def _make_node(code, organization):
    return Node.objects.create(code=code, organization=organization, location='Testville')


def _make_call(code, **overrides):
    defaults = dict(
        code=code, title=f'{code} title',
        status='resolved',
        submission_start=timezone.now() - timedelta(days=60),
        submission_end=timezone.now() - timedelta(days=30),
        evaluation_deadline=timezone.now() - timedelta(days=10),
        execution_start=timezone.now() - timedelta(days=5),
        execution_end=timezone.now() + timedelta(days=30),
        resolutions_released=True,
    )
    defaults.update(overrides)
    return Call.objects.create(**defaults)


def _make_applicant(email, organization=None, **extra):
    return create_complete_user(email=email, organization=organization, **extra)


def _make_application(call, applicant, code, **overrides):
    defaults = dict(
        applicant=applicant, call=call, code=code,
        brief_description=f'{code} description', status='submitted',
    )
    defaults.update(overrides)
    return Application.objects.create(**defaults)


def _make_resolution(application, node, reviewer, resolution):
    return NodeResolution.objects.create(
        application=application, node=node, reviewer=reviewer, resolution=resolution,
    )


class ResolutionTableBuildTests(TestCase):
    """Unit-level tests directly against build_resolution_table."""

    def setUp(self):
        self.host_org_biomac = _make_org('Bio Imagen Complutense', short_name='BioImaC')
        self.host_org_other = _make_org('Other Host Org', short_name='OtherHost')

        self.node_biomac = _make_node('BioImaC', self.host_org_biomac)
        self.node_unknown = _make_node('UNKNOWN-NODE', self.host_org_other)

        self.reviewer = _make_applicant('reviewer@test.com')

        self.call = _make_call('RES-TEST-01')

        # Draft: must never appear as a row. Explicit code avoids colliding
        # with the auto-generated codes the other fixture rows pick up.
        self.applicant_draft = _make_applicant('draft-applicant@test.com')
        _make_application(self.call, self.applicant_draft, 'RES-TEST-01-DRAFT', status='draft')

        # Single-node accept, organization with a distinct short_name.
        self.org_a = _make_org('Universidad Ejemplo', short_name='UEX')
        self.applicant_a = _make_applicant('applicant-a@test.com', organization=self.org_a)
        self.app1 = _make_application(self.call, self.applicant_a, 'RES-TEST-01-001')
        _make_resolution(self.app1, self.node_biomac, self.reviewer, 'accept')

        # Single-node waitlist, node code unknown to NODE_PUBLIC_NAMES.
        self.org_b = _make_org('Hospital Sin Sigla', short_name='')
        self.applicant_b = _make_applicant('applicant-b@test.com', organization=self.org_b)
        self.app2 = _make_application(self.call, self.applicant_b, 'RES-TEST-01-002')
        _make_resolution(self.app2, self.node_unknown, self.reviewer, 'waitlist')

        # Single-node reject, short_name identical to name.
        self.org_c = _make_org('Instituto Igual', short_name='Instituto Igual')
        self.applicant_c = _make_applicant('applicant-c@test.com', organization=self.org_c)
        self.app3 = _make_application(self.call, self.applicant_c, 'RES-TEST-01-003')
        _make_resolution(self.app3, self.node_biomac, self.reviewer, 'reject')

        # Multi-node: accept at one node, reject at the other.
        self.applicant_multi = _make_applicant('applicant-multi@test.com', organization=self.org_a)
        self.app4 = _make_application(self.call, self.applicant_multi, 'RES-TEST-01-004')
        _make_resolution(self.app4, self.node_biomac, self.reviewer, 'accept')
        _make_resolution(self.app4, self.node_unknown, self.reviewer, 'reject')

        # No NodeResolution at all.
        self.applicant_none = _make_applicant('applicant-none@test.com', organization=self.org_a)
        self.app5 = _make_application(self.call, self.applicant_none, 'RES-TEST-01-005')

        # NodeResolution with resolution='' (Not Decided).
        self.applicant_blank = _make_applicant('applicant-blank@test.com', organization=self.org_a)
        self.app6 = _make_application(self.call, self.applicant_blank, 'RES-TEST-01-006')
        _make_resolution(self.app6, self.node_biomac, self.reviewer, '')

        # No profile organization, but applicant_entity set.
        # create_complete_user() backfills a "Test Organization" when
        # organization=None is passed (it exists to satisfy
        # ProfileCompletionMiddleware for client-driven view tests), so the
        # only way to get a genuinely org-less applicant is to null it out
        # after creation.
        self.applicant_entity_only = _make_applicant('applicant-entity@test.com')
        self.applicant_entity_only.organization = None
        self.applicant_entity_only.save()
        self.app7 = _make_application(
            self.call, self.applicant_entity_only, 'RES-TEST-01-007',
            applicant_entity='Free Text Entity',
        )
        _make_resolution(self.app7, self.node_biomac, self.reviewer, 'accept')

        # No profile organization and no applicant_entity either.
        self.applicant_nothing = _make_applicant('applicant-nothing@test.com')
        self.applicant_nothing.organization = None
        self.applicant_nothing.save()
        self.app8 = _make_application(self.call, self.applicant_nothing, 'RES-TEST-01-008')
        _make_resolution(self.app8, self.node_biomac, self.reviewer, 'accept')

    def test_drafts_excluded_rows_ordered_by_code(self):
        table = build_resolution_table(self.call, 'en')
        codes = [row['code'] for row in table['rows']]
        self.assertNotIn(None, codes)
        self.assertEqual(codes, sorted(codes))
        self.assertEqual(len(codes), 8)  # 9 applications - 1 draft

    def test_resolution_label_english_and_spanish(self):
        en = build_resolution_table(self.call, 'en')
        es = build_resolution_table(self.call, 'es')

        row_en = next(r for r in en['rows'] if r['code'] == 'RES-TEST-01-001')
        row_es = next(r for r in es['rows'] if r['code'] == 'RES-TEST-01-001')
        self.assertEqual(row_en['resolutions'], ['Accepted'])
        self.assertEqual(row_es['resolutions'], ['Aceptada'])

        # Same row count and order in both languages, differing only in labels.
        self.assertEqual(
            [r['code'] for r in en['rows']], [r['code'] for r in es['rows']]
        )

    def test_resolution_read_from_node_resolution_not_application_status(self):
        # app3 was rejected at the node but Application.status was never
        # touched by this fixture (still 'submitted') — the table must not
        # infer from status.
        self.app3.refresh_from_db()
        self.assertEqual(self.app3.status, 'submitted')

        table = build_resolution_table(self.call, 'en')
        row = next(r for r in table['rows'] if r['code'] == 'RES-TEST-01-003')
        self.assertEqual(row['resolutions'], ['Rejected'])

    def test_node_public_name_lookup_and_fallback(self):
        table = build_resolution_table(self.call, 'en')
        row1 = next(r for r in table['rows'] if r['code'] == 'RES-TEST-01-001')
        row2 = next(r for r in table['rows'] if r['code'] == 'RES-TEST-01-002')

        self.assertEqual(row1['nodes'], ['BioImaC'])
        # Unknown node code degrades to organization.short_name, never raises.
        self.assertEqual(row2['nodes'], ['OtherHost'])

    def test_organization_cell_fallback_chain(self):
        table = build_resolution_table(self.call, 'en')
        by_code = {r['code']: r for r in table['rows']}

        self.assertEqual(by_code['RES-TEST-01-001']['organization'], 'UEX · Universidad Ejemplo')
        self.assertEqual(by_code['RES-TEST-01-002']['organization'], 'Hospital Sin Sigla')
        self.assertEqual(by_code['RES-TEST-01-003']['organization'], 'Instituto Igual')
        self.assertEqual(by_code['RES-TEST-01-007']['organization'], 'Free Text Entity')
        self.assertEqual(by_code['RES-TEST-01-008']['organization'], '')

    def test_multi_node_application_one_row_stacked_cells_same_order(self):
        en = build_resolution_table(self.call, 'en')
        es = build_resolution_table(self.call, 'es')

        rows_with_code_004_en = [r for r in en['rows'] if r['code'] == 'RES-TEST-01-004']
        rows_with_code_004_es = [r for r in es['rows'] if r['code'] == 'RES-TEST-01-004']
        self.assertEqual(len(rows_with_code_004_en), 1)  # one row per application

        row_en = rows_with_code_004_en[0]
        row_es = rows_with_code_004_es[0]

        self.assertEqual(row_en['nodes'], ['BioImaC', 'OtherHost'])
        self.assertEqual(row_en['resolutions'], ['Accepted', 'Rejected'])
        self.assertEqual(row_es['nodes'], ['BioImaC', 'OtherHost'])
        self.assertEqual(row_es['resolutions'], ['Aceptada', 'Rechazada'])

    def test_missing_node_resolution_renders_missing_marker_and_warns(self):
        table = build_resolution_table(self.call, 'en')
        row = next(r for r in table['rows'] if r['code'] == 'RES-TEST-01-005')

        self.assertEqual(row['nodes'], [MISSING])
        self.assertEqual(row['resolutions'], [MISSING])
        self.assertIn('RES-TEST-01-005', table['warnings']['missing_resolution_codes'])

    def test_blank_node_resolution_renders_as_missing_and_warns(self):
        table = build_resolution_table(self.call, 'en')
        row = next(r for r in table['rows'] if r['code'] == 'RES-TEST-01-006')

        self.assertEqual(row['resolutions'], [MISSING])
        self.assertIn('RES-TEST-01-006', table['warnings']['missing_resolution_codes'])

    def test_missing_organization_flagged_in_warnings(self):
        table = build_resolution_table(self.call, 'en')
        self.assertIn('RES-TEST-01-007', table['warnings']['missing_organization_codes'])
        self.assertIn('RES-TEST-01-008', table['warnings']['missing_organization_codes'])
        self.assertNotIn('RES-TEST-01-001', table['warnings']['missing_organization_codes'])

    def test_resolutions_released_warning_reflects_call_flag(self):
        released_table = build_resolution_table(self.call, 'en')
        self.assertTrue(released_table['warnings']['resolutions_released'])

        unreleased_call = _make_call('RES-TEST-02', resolutions_released=False)
        unreleased_table = build_resolution_table(unreleased_call, 'en')
        self.assertFalse(unreleased_table['warnings']['resolutions_released'])


class ResolutionTableEmptyCallTests(TestCase):
    def test_zero_non_draft_applications_renders_empty_rows_no_exception(self):
        call = _make_call('RES-TEST-EMPTY')
        table = build_resolution_table(call, 'en')
        self.assertEqual(table['rows'], [])

        applicant = _make_applicant('draft-only@test.com')
        _make_application(call, applicant, 'RES-TEST-EMPTY-DRAFT', status='draft')

        table = build_resolution_table(call, 'en')
        self.assertEqual(table['rows'], [])


class ResolutionReportViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.coordinator = create_complete_user(email='coord-res@test.com')
        UserRole.objects.create(user=self.coordinator, role='coordinator')

        self.non_coordinator = create_complete_user(email='plain-user@test.com')

        self.org = _make_org('View Test Org', short_name='VTO')
        self.host_org = _make_org('View Test Host', short_name='VTH')
        self.node = _make_node('BioImaC', self.host_org)

        self.call = _make_call('RES-VIEW-01')
        self.applicant = _make_applicant('view-applicant@test.com', organization=self.org)
        self.app = _make_application(self.call, self.applicant, 'RES-VIEW-01-001')
        _make_resolution(self.app, self.node, self.coordinator, 'accept')

        self.empty_call = _make_call('RES-VIEW-EMPTY')

    def test_page_renders_both_language_tables(self):
        self.client.force_login(self.coordinator)
        url = reverse('reports:resolution_report', args=[self.call.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'RES-VIEW-01-001')
        self.assertContains(response, 'Accepted')
        self.assertContains(response, 'Aceptada')
        self.assertContains(response, 'BioImaC')

    def test_empty_call_shows_empty_state_message_not_exception(self):
        self.client.force_login(self.coordinator)
        url = reverse('reports:resolution_report', args=[self.empty_call.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No submitted applications for this call.')

    def test_unreleased_call_shows_provisional_banner(self):
        unreleased = _make_call('RES-VIEW-UNRELEASED', resolutions_released=False)
        self.client.force_login(self.coordinator)
        url = reverse('reports:resolution_report', args=[unreleased.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'provisional')

    def test_non_coordinator_denied(self):
        self.client.force_login(self.non_coordinator)
        url = reverse('reports:resolution_report', args=[self.call.id])
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200)

    def test_dashboard_lists_call_with_link(self):
        self.client.force_login(self.coordinator)
        response = self.client.get(reverse('reports:statistics'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, reverse('reports:resolution_report', args=[self.call.id])
        )

    def test_csv_english_download(self):
        self.client.force_login(self.coordinator)
        url = reverse('reports:resolution_report_csv', args=[self.call.id, 'en'])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        content = response.content.decode()
        self.assertIn('Application,Organization,Node,Resolution', content)
        self.assertIn('RES-VIEW-01-001', content)
        self.assertIn('Accepted', content)

    def test_csv_spanish_download(self):
        self.client.force_login(self.coordinator)
        url = reverse('reports:resolution_report_csv', args=[self.call.id, 'es'])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Solicitud,Organización,Nodo,Resolución', content)
        self.assertIn('Aceptada', content)

    def test_csv_unknown_language_404s(self):
        self.client.force_login(self.coordinator)
        url = reverse('reports:resolution_report_csv', args=[self.call.id, 'fr'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_csv_non_coordinator_denied(self):
        self.client.force_login(self.non_coordinator)
        url = reverse('reports:resolution_report_csv', args=[self.call.id, 'en'])
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200)


class ResolutionReportReadOnlyTests(TestCase):
    """Loading the page or either CSV must write nothing."""

    def setUp(self):
        self.client = Client()
        self.coordinator = create_complete_user(email='readonly-coord@test.com')
        UserRole.objects.create(user=self.coordinator, role='coordinator')

        self.org = _make_org('Read Only Org', short_name='ROO')
        self.host_org = _make_org('Read Only Host', short_name='ROH')
        self.node = _make_node('BioImaC', self.host_org)

        self.call = _make_call('RES-RO-01')
        self.applicant = _make_applicant('ro-applicant@test.com', organization=self.org)
        self.app = _make_application(self.call, self.applicant, 'RES-RO-01-001')
        _make_resolution(self.app, self.node, self.coordinator, 'accept')

        self.client.force_login(self.coordinator)

    def _counts(self):
        from simple_history.utils import get_history_model_for_model
        historical_application_count = get_history_model_for_model(Application).objects.count()
        historical_node_resolution_count = get_history_model_for_model(NodeResolution).objects.count()
        return {
            'application': Application.objects.count(),
            'node_resolution': NodeResolution.objects.count(),
            'report_generation': ReportGeneration.objects.count(),
            'historical_application': historical_application_count,
            'historical_node_resolution': historical_node_resolution_count,
        }

    def test_page_load_is_read_only(self):
        before = self._counts()
        url = reverse('reports:resolution_report', args=[self.call.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._counts(), before)

    def test_csv_downloads_are_read_only(self):
        before = self._counts()
        for lang in ('en', 'es'):
            url = reverse('reports:resolution_report_csv', args=[self.call.id, lang])
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self._counts(), before)
