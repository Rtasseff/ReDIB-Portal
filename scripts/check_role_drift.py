"""Read-only: report where prod's UserRole rows and data/users.tsv disagree.

Run on prod:  python manage.py shell < scripts/check_role_drift.py
Writes nothing. Everything it prints is a difference you should decide about.

Two things this deliberately does, both learned from the 2026-08-21 prod run:

* It compares **evaluator areas**, not just (role, node) pairs. The loader
  writes `UserRole.areas`, so a check that ignores that column can give a
  clean bill while the load would still rewrite someone's specialization —
  which is exactly what happened (backlog #61). Areas compare as a *set*:
  'clinical;preclinical' and 'preclinical;clinical' are the same grant.
  A **blank** TSV cell is not drift, because the loader no longer writes it.

* It separates self-registered applicants from the reference set. Anyone can
  sign up and get an `applicant` role; the TSV is the curated list of staff,
  coordinators and evaluators. The first run printed 38 "DB only" lines of
  which 37 were ordinary signups, each advised "add to the TSV, or revoke" —
  advice that was wrong for all 37 and buried the one line that mattered.
"""
import csv
from pathlib import Path
from django.conf import settings
from core.models import UserRole

tsv_path = Path(settings.BASE_DIR) / 'data' / 'users.tsv'

# Roles a user can acquire by ordinary use of the portal, without anyone
# granting them. Never expected in users.tsv; never a drift signal on their own.
SELF_SERVICE_ROLES = {'applicant'}


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


def parse_areas(cell):
    """'clinical;preclinical' -> {'clinical', 'preclinical'}. Order is not data."""
    return {a.strip() for a in (cell or '').split(';') if a.strip()}


tsv = {}
with open(tsv_path, encoding='utf-8', newline='') as fh:
    for row in csv.DictReader(fh, delimiter='\t'):
        email = row['email'].strip().lower()
        tsv[email] = {
            'roles': parse_roles(row.get('roles')),
            'areas': parse_areas(row.get('areas')),
            'areas_raw': (row.get('areas') or '').strip(),
        }

db = {}
db_areas = {}
for role in UserRole.objects.filter(is_active=True).select_related('user', 'node'):
    email = role.user.email.strip().lower()
    db.setdefault(email, set()).add((role.role, role.node.code if role.node else ''))
    if role.role == 'evaluator':
        db_areas[email] = role.areas or ''

print('=' * 72)
print('ROLE DRIFT: active UserRole rows vs data/users.tsv')
print('=' * 72)

# ---------------------------------------------------------------- section 1
# Accounts the TSV knows about. This is the set the loader writes to, so
# anything here is a real decision.
print('\n1. ACCOUNTS IN users.tsv  (the reference set the loader writes)\n')

drift = False
for email in sorted(tsv):
    in_tsv = tsv[email]['roles']
    in_db = db.get(email, set())
    only_db = in_db - in_tsv
    only_tsv = in_tsv - in_db

    # Areas: only a FILLED cell is authoritative, matching the loader (#61).
    area_line = None
    if tsv[email]['areas'] and email in db_areas:
        if tsv[email]['areas'] != parse_areas(db_areas[email]):
            area_line = (
                f'  areas    : DB {db_areas[email]!r} -> TSV {tsv[email]["areas_raw"]!r}'
                f'   <- the load WOULD apply this'
            )

    if not only_db and not only_tsv and not area_line:
        continue
    drift = True
    print(f'{email}')
    for r, n in sorted(only_db):
        note = ('   <- self-acquired in the portal; leave it'
                if r in SELF_SERVICE_ROLES
                else '   <- granted outside the TSV: add it, or revoke it')
        print(f'  DB only  : {r}{":" + n if n else ""}{note}')
    for r, n in sorted(only_tsv):
        print(f'  TSV only : {r}{":" + n if n else ""}   <- the load WOULD add this')
    if area_line:
        print(area_line)
    print()

if not drift:
    print('  No drift. Roles and evaluator areas match for every TSV account.\n')

# ---------------------------------------------------------------- section 2
# Accounts the TSV has never heard of. Applicant-only signups are expected and
# are summarised, not listed. Anything else was granted by hand and is real.
print('-' * 72)
print('2. ACCOUNTS NOT IN users.tsv\n')

signups = []
granted = []
for email in sorted(set(db) - set(tsv)):
    roles = db[email]
    if all(r in SELF_SERVICE_ROLES for r, _ in roles):
        signups.append(email)
    else:
        granted.append((email, roles))

print(f'  {len(signups)} self-registered applicant account(s) — expected, not listed.')
print('  (Ordinary portal signups. The TSV is the curated staff/evaluator set;')
print('   putting these in it would be a treadmill and would grant nothing new.)')

if granted:
    print(f'\n  {len(granted)} account(s) hold a granted role but are NOT in the TSV:\n')
    for email, roles in granted:
        shown = ', '.join(sorted(f'{r}{":" + n if n else ""}' for r, n in roles))
        print(f'    {email}: {shown}')
    print('\n  These were granted by hand. Mirror them into users.tsv, or revoke.')
else:
    print('\n  No account outside the TSV holds a granted role.')

print('\n' + '-' * 72)
print(f'active UserRole rows: {UserRole.objects.filter(is_active=True).count()}')
print(f'inactive UserRole rows: {UserRole.objects.filter(is_active=False).count()}')
print('Inactive rows are never touched by the loader and are not compared above.')
