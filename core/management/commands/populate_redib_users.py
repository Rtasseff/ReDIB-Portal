"""
Management command to populate ReDIB users from TSV file.

This creates core user accounts (coordinators, node coordinators, evaluators)
from a TSV file. By default, loads from data/users.tsv.

Role format in TSV:
- Simple role: "coordinator" or "evaluator"
- Node-specific: "node_coordinator:CIC-biomaGUNE"
- Area-specific: "evaluator:preclinical"
- Multiple roles: "coordinator;evaluator:clinical"
"""
import csv
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress
from core.models import Organization, Node, UserRole

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate ReDIB users from TSV file (default: data/users.tsv)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tsv',
            type=str,
            default='data/users.tsv',
            help='Path to users TSV file (default: data/users.tsv)'
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Mark users not in TSV as inactive (is_active=False)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print the per-field diff this run would apply, without writing anything'
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help=(
                'Also overwrite the profile fields of users who already exist. '
                'OFF by default: the TSV is not authoritative for fields users '
                'maintain themselves through the portal (phone, position, orcid, '
                'organization, auto_data_consent) and a blank cell would clear '
                'them. Roles are applied either way. See backlog #43.'
            )
        )

    def load_users_from_csv(self, csv_path):
        """Load user data from TSV file."""
        project_root = Path(settings.BASE_DIR)
        csv_file = project_root / csv_path

        if not csv_file.exists():
            raise CommandError(f'TSV file not found: {csv_file}')

        users_data = []

        try:
            with open(csv_file, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
                    if not row.get('email') or not row.get('first_name') or not row.get('last_name'):
                        self.stdout.write(self.style.WARNING(
                            f'Row {row_num}: Skipping - missing required field '
                            f'(email, first_name, or last_name)'
                        ))
                        continue

                    # Booleans: blank = False; only TRUE/1/YES enables.
                    is_staff = self._parse_bool(row.get('is_staff'))
                    is_active = self._parse_bool(row.get('is_active'))
                    auto_data_consent = self._parse_bool(row.get('auto_data_consent'))

                    users_data.append({
                        'row_num': row_num,
                        'email': row['email'].strip().lower(),
                        'first_name': row['first_name'].strip(),
                        'last_name': row['last_name'].strip(),
                        'organization_name': (row.get('organization_name') or '').strip(),
                        'orcid': (row.get('orcid') or '').strip(),
                        'phone': (row.get('phone') or '').strip(),
                        'position': (row.get('position') or '').strip(),
                        'is_staff': is_staff,
                        'is_active': is_active,
                        'auto_data_consent': auto_data_consent,
                        'roles': (row.get('roles') or '').strip(),
                        'areas': (row.get('areas') or '').strip(),
                    })

        except csv.Error as e:
            raise CommandError(f'Error reading TSV file: {e}')

        return users_data

    @staticmethod
    def _parse_bool(value):
        """All three boolean columns default to False when blank or missing.
        Only the literal TRUE / 1 / YES (case-insensitive) flips to True."""
        return (value or '').strip().upper() in ('TRUE', '1', 'YES')

    @staticmethod
    def _diff_fields(existing_obj, new_values):
        """Return {field: (old, new)} for fields where new_values differs
        from the current value on existing_obj."""
        diffs = {}
        for field, new_value in new_values.items():
            old_value = getattr(existing_obj, field)
            if old_value != new_value:
                diffs[field] = (old_value, new_value)
        return diffs

    @staticmethod
    def _describe_role_change(user, role_name, node, role_areas):
        """Describe what a UserRole write would do, without writing it.

        Returns None if the role already exists with matching areas/is_active.
        """
        if user is None:
            return 'would create (new user)'
        existing = UserRole.objects.filter(user=user, role=role_name, node=node).first()
        if existing is None:
            return 'would create'
        changes = []
        if existing.areas != role_areas:
            changes.append(f'areas: {existing.areas!r} -> {role_areas!r}')
        if not existing.is_active:
            changes.append('is_active: False -> True')
        return f"would update ({', '.join(changes)})" if changes else None

    def parse_roles(self, roles_string):
        """
        Parse roles string into list of (role, node_code) tuples.

        Format:
        - Roles are separated by `;`
        - Within a role, `:` separates role name from a node qualifier (only for node_coordinator)
        - Areas (for evaluators) are read from a SEPARATE `areas` column, not from this string

        Examples:
        - "coordinator" -> [('coordinator', None)]
        - "node_coordinator:CIC-biomaGUNE" -> [('node_coordinator', 'CIC-biomaGUNE')]
        - "evaluator" -> [('evaluator', None)]
        - "coordinator;evaluator" -> [('coordinator', None), ('evaluator', None)]
        - "node_coordinator:BioImaC;evaluator" -> [('node_coordinator', 'BioImaC'), ('evaluator', None)]
        """
        if not roles_string:
            return []

        parsed_roles = []
        for entry in roles_string.split(';'):
            entry = entry.strip()
            if not entry:
                continue

            if ':' in entry:
                role, qualifier = entry.split(':', 1)
                role = role.strip()
                qualifier = qualifier.strip()
                if role == 'node_coordinator':
                    parsed_roles.append((role, qualifier))
                else:
                    self.stdout.write(self.style.WARNING(
                        f'Unexpected qualifier on role "{role}": "{qualifier}". '
                        f'Only node_coordinator supports the role:qualifier syntax. '
                        f'For evaluator areas, use the separate `areas` column.'
                    ))
                    parsed_roles.append((role, None))
            else:
                parsed_roles.append((entry, None))

        return parsed_roles

    def handle(self, *args, **options):
        """Create users from TSV file"""

        csv_path = options['tsv']
        sync_mode = options['sync']
        dry_run = options['dry_run']
        update_existing = options['update_existing']

        self.stdout.write(f'Loading user data from: {csv_path}')
        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run: no changes will be written.'))
        if update_existing:
            self.stdout.write(self.style.WARNING(
                'Update mode: profile fields of EXISTING users will be overwritten '
                'from the TSV, including blanks. See backlog #43.'
            ))
        else:
            self.stdout.write(
                'Create-only mode (default): existing users keep their profile '
                'fields; new users are created and roles are applied to everyone.'
            )
        if sync_mode:
            self.stdout.write(self.style.WARNING('Sync mode enabled: Will mark orphaned users as inactive'))

        # Load user data from TSV
        users_data = self.load_users_from_csv(csv_path)
        tsv_emails = {u['email'] for u in users_data}

        created_count = 0
        updated_count = 0
        unchanged_count = 0
        protected_count = 0
        roles_created_count = 0
        roles_changed_count = 0

        for user_data in users_data:
            email = user_data['email']
            row_num = user_data['row_num']

            # Look up organization (FK). Must already exist — run
            # populate_redib_organizations first.
            organization = None
            if user_data['organization_name']:
                try:
                    organization = Organization.objects.get(name=user_data['organization_name'])
                except Organization.DoesNotExist:
                    raise CommandError(
                        f'Row {row_num} ("{email}"): organization_name '
                        f'"{user_data["organization_name"]}" does not match any '
                        f'Organization. Run `populate_redib_organizations` first, '
                        f'or fix the TSV.'
                    )

            new_field_values = {
                'first_name': user_data['first_name'],
                'last_name': user_data['last_name'],
                'organization': organization,
                'orcid': user_data['orcid'],
                'phone': user_data['phone'],
                'position': user_data['position'],
                'is_staff': user_data['is_staff'],
                'is_active': user_data['is_active'],
                'auto_data_consent': user_data['auto_data_consent'],
            }

            if dry_run:
                # Look, don't touch: diff against whatever's in the DB today.
                user = User.objects.filter(email=email).first()
                if user is None:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'  + Would create: {email}'))
                    for field, value in new_field_values.items():
                        self.stdout.write(f'      {field}: {value!r}')
                    self.stdout.write('      password: set to default (new user)')
                else:
                    diffs = self._diff_fields(user, new_field_values)
                    if diffs and not update_existing:
                        # Create-only: show what the TSV *would* have written, so
                        # the drift is visible, but make clear nothing is applied.
                        protected_count += 1
                        self.stdout.write(self.style.SUCCESS(
                            f'  · Exists, profile protected: {email}'
                        ))
                        for field, (old, new) in diffs.items():
                            self.stdout.write(
                                f'      {field}: {old!r} would have become {new!r} '
                                f'— not applied'
                            )
                    elif diffs:
                        updated_count += 1
                        self.stdout.write(self.style.WARNING(f'  ~ Would update: {email}'))
                        for field, (old, new) in diffs.items():
                            self.stdout.write(f'      {field}: {old!r} -> {new!r}')
                    else:
                        unchanged_count += 1
                        self.stdout.write(f'  = Unchanged: {email}')
                    self.stdout.write('      password: left unchanged (existing user)')
            else:
                existing = User.objects.filter(email=email).first()

                if existing is not None and not update_existing:
                    # Create-only (default). The TSV is not authoritative for
                    # fields the user maintains through their own profile —
                    # phone, position, orcid, organization, auto_data_consent —
                    # and a blank cell here would clear them. `is_active` is
                    # ReDIB's to set, but a blank cell reads as "not filled in",
                    # not "deactivate this person", so it is held back too.
                    # Roles are still applied below: they are admin-only, so
                    # there is no portal-authored value to lose. Backlog #43
                    # carries the durable fix.
                    user, user_created = existing, False
                    protected_count += 1
                else:
                    # Get or create user
                    user, user_created = User.objects.update_or_create(
                        email=email,
                        defaults=new_field_values,
                    )

                # Only set the default password for brand-new users — an
                # existing user keeps whatever password they set themselves.
                if user_created:
                    user.set_password('changeme123')
                    user.save()

                # Ensure allauth EmailAddress exists and is verified
                EmailAddress.objects.update_or_create(
                    user=user,
                    email=email,
                    defaults={'verified': True, 'primary': True},
                )

                if user_created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ Created: {email} ({user.get_full_name()})'
                        )
                    )
                elif update_existing:
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'  ↻ Updated: {email} ({user.get_full_name()})'
                        )
                    )
                else:
                    self.stdout.write(
                        f'  · Exists, profile untouched: {email} '
                        f'({user.get_full_name()})'
                    )

            # Validate areas from the separate `areas` column.
            # Convention: areas apply ONLY to the evaluator role. They are stored on
            # the evaluator UserRole row; non-evaluator UserRole rows get empty areas.
            valid_areas = ['preclinical', 'clinical', 'radiochemistry']
            raw_areas = [a.strip() for a in (user_data.get('areas') or '').split(';') if a.strip()]
            invalid_areas = [a for a in raw_areas if a not in valid_areas]
            if invalid_areas:
                raise CommandError(
                    f'Row {row_num} ("{email}"): invalid evaluator area(s) '
                    f'{invalid_areas}. Allowed: {valid_areas}.'
                )
            user_areas = ';'.join(raw_areas)

            # Handle roles
            parsed_roles = self.parse_roles(user_data['roles'])

            # Warn if areas were provided but the user has no evaluator role
            if user_areas and not any(r[0] == 'evaluator' for r in parsed_roles):
                self.stdout.write(self.style.WARNING(
                    f'  ⚠ {email} has areas={user_areas!r} but no evaluator role. '
                    f'Areas will be ignored.'
                ))

            for role_name, node_code in parsed_roles:
                # Get node if specified — must already exist
                node = None
                if node_code:
                    try:
                        node = Node.objects.get(code=node_code)
                    except Node.DoesNotExist:
                        raise CommandError(
                            f'Row {row_num} ("{email}"): role qualifier '
                            f'"{role_name}:{node_code}" references unknown node code. '
                            f'Run `populate_redib_nodes` first, or fix the TSV.'
                        )

                # Areas only apply to the evaluator role
                role_areas = user_areas if role_name == 'evaluator' else ''
                node_info = f" at {node.code}" if node else ""
                area_info = f" ({role_areas})" if role_areas else ""

                if dry_run:
                    change = self._describe_role_change(user, role_name, node, role_areas)
                    if change:
                        roles_changed_count += 1
                        self.stdout.write(
                            f'    → Role {role_name}{node_info}{area_info}: {change}'
                        )
                else:
                    # Create or update user role
                    role, role_created = UserRole.objects.update_or_create(
                        user=user,
                        role=role_name,
                        node=node,
                        defaults={
                            'areas': role_areas,
                            'is_active': True,
                        }
                    )

                    if role_created:
                        roles_created_count += 1
                        self.stdout.write(
                            f'    → Role: {role_name}{node_info}{area_info}'
                        )

        # Handle sync mode: Mark orphaned users as inactive
        deactivated_count = 0
        if sync_mode:
            self.stdout.write('\n' + '-' * 60)
            self.stdout.write('Checking for orphaned users (in DB but not in TSV)...')

            # Any active, non-superuser account whose email isn't in this TSV
            orphaned_users = User.objects.exclude(email__in=tsv_emails).filter(
                is_active=True,
                is_superuser=False
            )

            for user in orphaned_users:
                if dry_run:
                    self.stdout.write(
                        f'  - Would deactivate: {user.email} ({user.get_full_name()}) (not in TSV)'
                    )
                else:
                    user.is_active = False
                    user.save()
                    self.stdout.write(
                        self.style.WARNING(
                            f'  ⊗ Deactivated: {user.email} ({user.get_full_name()}) (not in TSV)'
                        )
                    )
                deactivated_count += 1

            if deactivated_count == 0:
                self.stdout.write(self.style.SUCCESS('  ✓ No orphaned users found'))

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(
            self.style.SUCCESS(
                'Dry run complete — nothing was written.' if dry_run else 'User population complete!'
            )
        )
        self.stdout.write(f'  Users to create: {created_count}' if dry_run else f'  Users created: {created_count}')
        self.stdout.write(f'  Users to update: {updated_count}' if dry_run else f'  Users updated: {updated_count}')
        if dry_run:
            self.stdout.write(f'  Users unchanged: {unchanged_count}')
        if protected_count:
            label = (
                'Existing users whose profile would be protected'
                if dry_run else 'Existing users left untouched'
            )
            self.stdout.write(f'  {label}: {protected_count}')
            self.stdout.write(
                '    (re-run with --update-existing to overwrite them from the TSV)'
            )
        if sync_mode and deactivated_count > 0:
            label = 'Users that would be deactivated' if dry_run else 'Users deactivated'
            self.stdout.write(f'  {label}: {deactivated_count}')
        self.stdout.write(
            f'  Total users in TSV: '
            f'{created_count + updated_count + unchanged_count + protected_count}'
        )
        if dry_run:
            self.stdout.write(f'  Roles that would change: {roles_changed_count}')
        else:
            self.stdout.write(f'  Roles assigned: {roles_created_count}')
        if created_count > 0 and not dry_run:
            self.stdout.write('\n' + self.style.WARNING('Note: New users have default password "changeme123"'))
        self.stdout.write('=' * 60 + '\n')
