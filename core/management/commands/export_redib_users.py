"""
Export ReDIB's people from the database in the data/users.tsv format.

The portal is the authority for people (backlog #91): change a user or a role
in the admin or shell, then run this and commit the file. data/users.tsv is
still what `setup_base_database` loads on a fresh database.

Who is written: every user holding at least one non-applicant UserRole,
active or retired, plus any `is_staff` user. Self-registered applicants are
not ReDIB-managed staff and are left out, and the applicant role is never
written: the portal grants it itself when an address is confirmed.

Columns are exactly those of data/users.tsv, in the same order, plus a
trailing `retired_roles`:
  - `roles`: the user's active roles, `node_coordinator:<NODE>` for a node role.
  - `retired_roles`: roles whose UserRole is inactive, same syntax. This is how
    the file records a former evaluator without re-granting the role (#81).
    `populate_redib_users` reads with csv.DictReader and ignores the column.
  - `areas`: from the evaluator role (the active one if any).
  - booleans: TRUE / FALSE.

Output: UTF-8 without BOM, CRLF line endings, rows sorted by email, to stdout
by default so on prod

    docker compose -f docker-compose.prod.yml exec -T web \\
        python manage.py export_redib_users > data/users.tsv

writes the host's checkout. `--output <path>` writes a file instead, and
`--format xlsx` writes a spreadsheet (the read-only copy for SharePoint).
"""
import csv
import io
import sys
from pathlib import Path

from django.conf import settings

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from core.models import UserRole

User = get_user_model()

COLUMNS = [
    'email', 'first_name', 'last_name', 'organization_name', 'orcid', 'phone',
    'position', 'is_staff', 'is_active', 'roles', 'areas', 'auto_data_consent',
    'retired_roles',
]

# Roles are listed in UserRole.ROLES order, then by node code.
ROLE_ORDER = {name: i for i, (name, _) in enumerate(UserRole.ROLES)}
STAFF_ROLES = [name for name, _ in UserRole.ROLES if name != 'applicant']


def _bool(value):
    return 'TRUE' if value else 'FALSE'


def _role_cell(roles):
    ordered = sorted(roles, key=lambda r: (ROLE_ORDER.get(r.role, 99), r.node.code if r.node else ''))
    return ';'.join(f'{r.role}:{r.node.code}' if r.node else r.role for r in ordered)


def export_rows():
    """One dict per exported user, keyed by COLUMNS, sorted by email."""
    users = (
        User.objects
        .filter(Q(roles__role__in=STAFF_ROLES) | Q(is_staff=True))
        .distinct()
        .select_related('organization')
        .prefetch_related('roles__node')
        .order_by('email')
    )
    rows = []
    for user in users:
        roles = [r for r in user.roles.all() if r.role != 'applicant']
        evaluator_roles = sorted(
            (r for r in roles if r.role == 'evaluator'), key=lambda r: not r.is_active
        )
        rows.append({
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'organization_name': user.organization.name if user.organization else '',
            'orcid': user.orcid,
            'phone': user.phone,
            'position': user.position,
            'is_staff': _bool(user.is_staff),
            'is_active': _bool(user.is_active),
            'roles': _role_cell([r for r in roles if r.is_active]),
            'areas': evaluator_roles[0].areas if evaluator_roles else '',
            'auto_data_consent': _bool(user.auto_data_consent),
            'retired_roles': _role_cell([r for r in roles if not r.is_active]),
        })
    return rows


class Command(BaseCommand):
    help = 'Export ReDIB users (non-applicant roles or staff) in the data/users.tsv format'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            help='Write to this path instead of stdout',
        )
        parser.add_argument(
            '--format',
            choices=['tsv', 'xlsx'],
            default='tsv',
            help='tsv (default) or xlsx',
        )

    def handle(self, *args, **options):
        rows = export_rows()
        self._warn_unknown_organizations(rows)
        if options['format'] == 'xlsx':
            data = self._xlsx(rows)
        else:
            data = self._tsv(rows).encode('utf-8')

        if options['output']:
            with open(options['output'], 'wb') as f:
                f.write(data)
            self.stderr.write(f'Wrote {len(rows)} users to {options["output"]}')
        elif options.get('stdout') is not None:
            # call_command(stdout=...) from a test: a text stream.
            if options['format'] == 'xlsx':
                raise CommandError('--format xlsx needs --output, or a real stdout.')
            self.stdout.write(data.decode('utf-8'), ending='')
        else:
            # Bytes, so the file is UTF-8 with CRLF whatever the locale is.
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()

    def _warn_unknown_organizations(self, rows):
        """An organization created from the profile form is in the DB but not
        in data/organizations.tsv. setup_base_database on a fresh database
        would then fail at the users step, so say so (on stderr, which the
        redirect into users.tsv doesn't catch)."""
        path = Path(settings.BASE_DIR) / 'data' / 'organizations.tsv'
        if not path.exists():
            return
        with open(path, encoding='utf-8', newline='') as f:
            known = {(r.get('name') or '').strip() for r in csv.DictReader(f, delimiter='\t')}
        missing = sorted({r['organization_name'] for r in rows} - known - {''})
        for name in missing:
            self.stderr.write(self.style.WARNING(
                f'Warning: organization "{name}" is not in data/organizations.tsv. '
                f'Add its row there too, or a fresh setup_base_database fails at the users step.'
            ))

    @staticmethod
    def _tsv(rows):
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=COLUMNS, delimiter='\t', lineterminator='\r\n')
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()

    @staticmethod
    def _xlsx(rows):
        from openpyxl import Workbook
        from openpyxl.styles import Font

        wb = Workbook()
        ws = wb.active
        ws.title = 'users'
        ws.append(COLUMNS)
        for cell in ws[1]:
            cell.font = Font(bold=True)
        for row in rows:
            ws.append([row[c] for c in COLUMNS])
        ws.freeze_panes = 'A2'
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()
