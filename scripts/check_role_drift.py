"""Read-only: report where prod's UserRole rows and data/users.tsv disagree.

Run on prod:  python manage.py shell < role_drift_check.py
Writes nothing. Everything it prints is a difference you should decide about.
"""
import csv
from pathlib import Path
from django.conf import settings
from core.models import UserRole

tsv_path = Path(settings.BASE_DIR) / 'data' / 'users.tsv'


def parse_roles(cell):
    """'evaluator;node_coordinator:CIC-biomaGUNE' -> {('evaluator', ''), ...}"""
    out = set()
    for part in (cell or '').split(';'):
        part = part.strip()
        if not part:
            continue
        name, _, node = part.partition(':')
        out.add((name.strip(), node.strip()))
    return out


tsv = {}
with open(tsv_path, encoding='utf-8', newline='') as fh:
    for row in csv.DictReader(fh, delimiter='\t'):
        tsv[row['email'].strip().lower()] = parse_roles(row.get('roles'))

db = {}
for role in UserRole.objects.filter(is_active=True).select_related('user', 'node'):
    db.setdefault(role.user.email.strip().lower(), set()).add(
        (role.role, role.node.code if role.node else '')
    )

print('=' * 68)
print('ROLE DRIFT: active UserRole rows vs data/users.tsv')
print('=' * 68)

drift = False
for email in sorted(set(tsv) | set(db)):
    in_tsv = tsv.get(email, set())
    in_db = db.get(email, set())
    only_db = in_db - in_tsv
    only_tsv = in_tsv - in_db
    if not only_db and not only_tsv:
        continue
    drift = True
    print(f'\n{email}')
    if email not in tsv:
        print('  ! not in users.tsv at all')
    for r, n in sorted(only_db):
        print(f'  DB only  : {r}{":" + n if n else ""}   <- add to the TSV, or revoke')
    for r, n in sorted(only_tsv):
        print(f'  TSV only : {r}{":" + n if n else ""}   <- loader would add this')

if not drift:
    print('\nNo drift. data/users.tsv matches the active roles in the database.')

print('\n' + '-' * 68)
print(f'active UserRole rows: {UserRole.objects.filter(is_active=True).count()}')
print(f'inactive UserRole rows: {UserRole.objects.filter(is_active=False).count()}')
print('Inactive rows are never touched by the loader and are not compared above.')
