"""
populate_redib_users: the TSV is not authoritative for fields users maintain
themselves (backlog #43).

The loader is `update_or_create` over every column, and a blank cell is written
as a deliberate False/empty per the shared loader rule. That is right for
reference data and wrong for a user table: `phone`, `position`, `orcid`,
`organization` and `auto_data_consent` are all editable from the portal's own
profile form, so a stale TSV silently reverts whatever someone typed. `is_active`
is ReDIB's to set, but a blank cell there reads as "not filled in", not
"deactivate this person" — a plain load against prod on 2026-08-19 would have
switched off a serving evaluator.

So create-only is the default and `--update-existing` is the opt-in. Roles are
applied either way: they are admin-only, so there is no portal-authored value
to lose.
"""
import io
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from core.models import Node, Organization, UserRole

User = get_user_model()

HEADER = (
    'email\tfirst_name\tlast_name\torganization_name\torcid\tphone\tposition\t'
    'is_staff\tis_active\troles\tareas\tauto_data_consent'
)


def _tsv(*rows):
    """Write a temp TSV with CRLF endings, matching the real data/ files."""
    handle = tempfile.NamedTemporaryFile(
        mode='w', suffix='.tsv', delete=False, encoding='utf-8', newline=''
    )
    handle.write(HEADER + '\r\n')
    for row in rows:
        handle.write(row + '\r\n')
    handle.close()
    return handle.name


class UserLoaderCreateOnlyTest(TestCase):
    """The default run must not touch an existing user's profile fields."""

    def setUp(self):
        self.org = Organization.objects.create(name='Test Org', short_name='TO')
        self.node = Node.objects.create(
            code='TEST-NODE', organization=self.org, location='Testville'
        )

        # A user who has since filled in their own profile through the portal.
        self.existing = User.objects.create_user(
            email='serving@example.org',
            password='their-own-password',
            first_name='Serving',
            last_name='Evaluator',
            organization=self.org,
            phone='+34 600 000 000',
            position='Principal Investigator',
            orcid='0000-0002-1234-5678',
            is_active=True,
            auto_data_consent=True,
        )

        # The TSV is stale: every user-owned column is blank, which the shared
        # loader rule would write as an explicit False/empty.
        self.stale_row = (
            'serving@example.org\tServing\tEvaluator\tTest Org\t\t\t\t'
            '\t\tevaluator\tpreclinical\t'
        )

    def _run(self, *rows, **options):
        path = _tsv(*rows)
        try:
            call_command(
                'populate_redib_users', tsv=path, stdout=io.StringIO(), **options
            )
        finally:
            Path(path).unlink(missing_ok=True)

    def test_blank_cells_do_not_clear_portal_edited_fields(self):
        self._run(self.stale_row)
        self.existing.refresh_from_db()

        self.assertEqual(self.existing.phone, '+34 600 000 000')
        self.assertEqual(self.existing.position, 'Principal Investigator')
        self.assertEqual(self.existing.orcid, '0000-0002-1234-5678')
        self.assertTrue(self.existing.auto_data_consent)

    def test_blank_is_active_does_not_deactivate_a_serving_user(self):
        """The 2026-08-19 prod finding, as a regression test."""
        self._run(self.stale_row)
        self.existing.refresh_from_db()
        self.assertTrue(self.existing.is_active)

    def test_password_is_still_never_touched(self):
        self._run(self.stale_row)
        self.existing.refresh_from_db()
        self.assertTrue(self.existing.check_password('their-own-password'))

    def test_roles_are_still_applied_to_an_existing_user(self):
        """Create-only protects profile fields, not authorization. Granting an
        existing person the evaluator role is exactly what the October load
        needs to do."""
        self.assertFalse(self.existing.roles.exists())

        self._run(self.stale_row)

        role = self.existing.roles.get(role='evaluator')
        self.assertTrue(role.is_active)
        self.assertEqual(role.areas, 'preclinical')

    def test_a_node_qualified_role_is_applied_to_an_existing_user(self):
        row = (
            'serving@example.org\tServing\tEvaluator\tTest Org\t\t\t\t'
            '\t\tnode_coordinator:TEST-NODE\t\t'
        )
        self._run(row)

        role = self.existing.roles.get(role='node_coordinator')
        self.assertEqual(role.node, self.node)
        self.assertTrue(role.is_active)

    def test_new_users_are_still_created(self):
        row = (
            'newcomer@example.org\tNew\tComer\tTest Org\t\t\t\t'
            '\tTRUE\tevaluator\tclinical\tTRUE'
        )
        self._run(self.stale_row, row)

        created = User.objects.get(email='newcomer@example.org')
        self.assertTrue(created.is_active)
        self.assertTrue(created.auto_data_consent)
        self.assertTrue(created.roles.filter(role='evaluator').exists())

    def test_update_existing_restores_the_old_overwriting_behaviour(self):
        """The destructive behaviour still exists — it just has to be asked for."""
        self._run(self.stale_row, update_existing=True)
        self.existing.refresh_from_db()

        self.assertEqual(self.existing.phone, '')
        self.assertEqual(self.existing.position, '')
        self.assertFalse(self.existing.auto_data_consent)
        self.assertFalse(self.existing.is_active)

    def test_update_existing_still_leaves_the_password_alone(self):
        self._run(self.stale_row, update_existing=True)
        self.existing.refresh_from_db()
        self.assertTrue(self.existing.check_password('their-own-password'))

    def test_dry_run_writes_nothing_in_either_mode(self):
        for options in ({}, {'update_existing': True}):
            with self.subTest(options=options):
                self._run(self.stale_row, dry_run=True, **options)
                self.existing.refresh_from_db()
                self.assertTrue(self.existing.is_active)
                self.assertEqual(self.existing.phone, '+34 600 000 000')
                self.assertFalse(self.existing.roles.exists())


class UserLoaderEvaluatorAreasTest(TestCase):
    """A blank `areas` cell must not strip a serving evaluator (backlog #61).

    Create-only closed half the 2026-08-19 hazard. Roles are still applied in
    both modes by design — and `areas` rides on `UserRole`, written through the
    same `update_or_create`. So a blank cell was still an authoritative empty
    string: prod's 2026-08-21 run held back `is_active: True -> False` for a
    serving evaluator and then, on the next line, would have set her
    `areas: 'preclinical' -> ''`. `UserRole.has_area()` is False for every area
    when `areas` is blank, and area-matched assignment skips such a role
    entirely, so for the question that finding was about — can she be assigned
    a preclinical application — that is the same outcome as deactivating her.

    The rule now: a blank cell means "the TSV isn't saying" and is not written;
    a filled cell is authoritative and still wins.
    """

    def setUp(self):
        self.org = Organization.objects.create(name='Test Org', short_name='TO')
        self.node = Node.objects.create(
            code='TEST-NODE', organization=self.org, location='Testville'
        )
        self.evaluator = User.objects.create_user(
            email='serving@example.org',
            password='pw',
            first_name='Serving',
            last_name='Evaluator',
        )
        self.role = UserRole.objects.create(
            user=self.evaluator, role='evaluator', areas='preclinical', is_active=True
        )

    def _row(self, areas='', roles='evaluator'):
        return (
            f'serving@example.org\tServing\tEvaluator\t\t\t\t\t'
            f'\t\t{roles}\t{areas}\t'
        )

    def _run(self, *rows, **options):
        path = _tsv(*rows)
        out = io.StringIO()
        try:
            call_command('populate_redib_users', tsv=path, stdout=out, **options)
        finally:
            Path(path).unlink(missing_ok=True)
        return out.getvalue()

    def test_blank_areas_does_not_strip_a_serving_evaluator(self):
        """The 2026-08-21 prod finding, as a regression test."""
        self._run(self._row(areas=''))
        self.role.refresh_from_db()
        self.assertEqual(self.role.areas, 'preclinical')
        self.assertTrue(self.role.has_area('preclinical'))

    def test_blank_areas_is_protected_in_update_existing_mode_too(self):
        """`--update-existing` opts back into overwriting *profile* fields. It
        is not a licence to blank an evaluator's specialization — that value
        was never in the TSV to begin with."""
        self._run(self._row(areas=''), update_existing=True)
        self.role.refresh_from_db()
        self.assertEqual(self.role.areas, 'preclinical')

    def test_a_filled_areas_cell_still_wins(self):
        """The TSV is the reference for who evaluates what. `mangel.morcillo@`
        on prod has 'preclinical;radiochemistry' in the DB and only
        'radiochemistry' in the TSV — that narrowing still applies, and the
        pre-load drift check is what makes it visible in time to fix the TSV."""
        self._run(self._row(areas='radiochemistry'))
        self.role.refresh_from_db()
        self.assertEqual(self.role.areas, 'radiochemistry')

    def test_reordering_is_not_a_change(self):
        """'clinical;preclinical' and 'preclinical;clinical' are the same grant.
        Four of prod's six role lines were reorderings, and reporting them as
        changes buried the two that actually lost an area."""
        self.role.areas = 'clinical;preclinical'
        self.role.save()

        output = self._run(self._row(areas='preclinical;clinical'), dry_run=True)
        self.assertNotIn('areas:', output)

    def test_dry_run_does_not_report_a_phantom_change_for_a_blank_cell(self):
        """The dry-run and the write share `_role_defaults`, so a dry-run can
        never describe something the real run would not do."""
        output = self._run(self._row(areas=''), dry_run=True)
        self.assertNotIn('areas:', output)

        self.role.refresh_from_db()
        self.assertEqual(self.role.areas, 'preclinical')

    def test_a_new_evaluator_with_a_blank_cell_is_created_with_no_areas(self):
        row = (
            'fresh@example.org\tFresh\tEvaluator\t\t\t\t\t'
            '\t\tevaluator\t\t'
        )
        self._run(row)
        role = User.objects.get(email='fresh@example.org').roles.get(role='evaluator')
        self.assertEqual(role.areas, '')
        self.assertTrue(role.is_active)

    def test_a_new_evaluator_with_a_filled_cell_gets_them(self):
        row = (
            'fresh@example.org\tFresh\tEvaluator\t\t\t\t\t'
            '\t\tevaluator\tclinical;radiochemistry\t'
        )
        self._run(row)
        role = User.objects.get(email='fresh@example.org').roles.get(role='evaluator')
        self.assertEqual(set(role.area_list), {'clinical', 'radiochemistry'})

    def test_non_evaluator_rows_still_carry_no_areas(self):
        """Areas apply only to the evaluator role; that convention is unchanged."""
        stray = UserRole.objects.create(
            user=self.evaluator, role='node_coordinator', node=self.node,
            areas='clinical', is_active=True,
        )
        self._run(self._row(areas='', roles='node_coordinator:TEST-NODE'))
        stray.refresh_from_db()
        self.assertEqual(stray.areas, '')

    def test_an_inactive_role_is_still_reactivated(self):
        """Blank-areas protection must not also stop the loader reactivating a
        role — granting authorization is what the October load is for."""
        self.role.is_active = False
        self.role.save()

        self._run(self._row(areas=''))
        self.role.refresh_from_db()
        self.assertTrue(self.role.is_active)
        self.assertEqual(self.role.areas, 'preclinical')
