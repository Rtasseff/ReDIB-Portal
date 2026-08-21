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
