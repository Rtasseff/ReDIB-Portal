# Data Directory

Tab-separated reference files for the portal's lookup tables, and the rules of the
`populate_redib_*` commands that load them. Nothing here is loaded automatically: a
deploy runs `migrate`, `collectstatic` and `seed_email_templates`, never a loader. How
to run a full load (dev or a fresh production database) is in
[docs/SETUP_GUIDE.md § Initial Data Setup](../docs/SETUP_GUIDE.md#initial-data-setup).
This file covers the formats, the rules, and the everyday edits.

**Why TSV.** Equipment descriptions and organization names contain commas. Tabs appear
in no field, so there is no quoting to get wrong. Multi-line cells (equipment
descriptions) are still quoted in the file, and Python's `csv` module reads them.

| File | Loader | Model | Natural key | Rows (2026-09-28) |
|---|---|---|---|---|
| `organizations.tsv` | `populate_redib_organizations` | `core.Organization` | `name` | 186 |
| `nodes.tsv` | `populate_redib_nodes` | `core.Node` | `code` | 4 |
| `users.tsv` | `populate_redib_users` | `core.User` + `core.UserRole` | `email` (lower-cased) | 28 |
| `equipment.tsv` | `populate_redib_equipment` | `core.Equipment` | (`node_code`, `name`) | 14 |
| `funding_agencies.tsv` | `populate_redib_funding_agencies` | `applications.FundingAgency` | `name` | 375 |
| `waitlist_hours_backfill.tsv.example` | `backfill_waitlist_hours_approved` (one-off) | `RequestedAccess` | — | example only |

Every `populate_redib_*` loader takes `--tsv <path>` (default `data/<file>.tsv`, relative to the project
root; an absolute path also works) and `--sync`. Only `populate_redib_users` has
`--dry-run` and `--update-existing`.

## Load order

1. `organizations.tsv`. No dependencies.
2. `nodes.tsv`. `organization_name` must match an existing organization.
3. `users.tsv`. `organization_name` must match an organization; `node_coordinator:CODE` must match a node.
4. `equipment.tsv`. `node_code` must match a node.
5. `funding_agencies.tsv`. No dependencies.

`seed_email_templates` has no dependencies and can run at any point.

## Rules every loader follows

- **Encoding: UTF-8 without a BOM.** CRLF line endings are fine (every file here has
  them; keep them). A Windows-1252 file (Excel's default export) crashes with a
  `UnicodeDecodeError` traceback on the first non-ASCII byte. Convert with
  `iconv -f cp1252 -t utf-8`. A UTF-8 **BOM** hides the first column header. The
  nodes, users and equipment loaders then skip *every* row with a "missing required
  field" warning and exit 0, having loaded nothing. The organizations and funding-agency
  loaders abort.
- **Booleans:** blank means False. Only `TRUE`, `1` or `YES` (any case) means True. This
  applies to every boolean column, `nodes.tsv` `is_active` included, so write `TRUE`
  explicitly.
- **Enum columns are exact.** An unknown `organization_type`, `origin_of_funds`,
  `category`, equipment `area` or evaluator `areas` value aborts the load with a
  `CommandError` naming the row.
- **A rerun updates in place, matched on the natural key.** It never deletes anything.
  The loaders don't diff, so the organizations, nodes and equipment loaders report
  `↻ Updated` for every row on every run, even when nothing changed. Users are the
  exception: see below.
- **Not validated:** role names in `users.tsv` (`evaluater` is written as a role
  nobody checks for), and ORCID and phone format. A malformed ORCID or phone loads
  fine, and the user's profile form then refuses to save until they fix it.

### When a load fails part-way

| Loader | Aborts the load (exit 1) | Skipped with a warning | Can it leave a partial load? |
|---|---|---|---|
| organizations | missing `name`, `ISO2` or `country`; `ISO2` not 2 letters; unknown `organization_type` | — | No. The whole file is checked before anything is written. |
| nodes | `organization_name` not found | row missing `code` or `organization_name` | No. The whole file is checked first. |
| funding agencies | missing `name` or `origin_of_funds`; unknown label (all errors listed together) | duplicate `name` within the file | No. The whole file is checked first. |
| users | `organization_name` not found; `node_coordinator:CODE` not a node; invalid `areas` value | row missing `email`, `first_name` or `last_name` | **Yes.** Rows are written one at a time. Rows above the bad one are already saved. For a bad `areas` cell, the user on that row has been created too, without the role. |
| equipment | invalid `category` or `area` (checked first); `node_code` not a node (checked while writing) | row missing `node_code`, `name` or `category` | **Yes**, for an unknown `node_code`. |

The recovery is the same every time: fix the file and run the loader again. Reruns are
idempotent. For users, `--dry-run` hits the same three errors without writing anything,
so a clean dry-run means the real run won't hit them.

`setup_base_database` runs the loaders in order and **stops at the first failed step
but still exits 0**. Read its output for `Failed:`.

### `--sync`: what "not in the file" does

| Loader | Rows in the DB but not in the file |
|---|---|
| nodes, equipment | set `is_active=False` |
| **users** | **every active non-superuser account not in the file is deactivated**, and that includes every self-registered applicant. On production that is ~1,200 people locked out. **Never run `populate_redib_users --sync` on production.** On dev, try it with `--dry-run` first. |
| organizations, funding agencies | listed with their reference counts, not changed (no `is_active` field) |

### What a clean rerun looks like

Observed 2026-09-28: all five loaders plus `seed_email_templates` ran into a freshly
migrated SQLite DB, then all six ran again.

| Command | First run | Second run |
|---|---|---|
| organizations | 186 created | 0 created, 186 updated |
| nodes | 4 created | 0 created, 4 updated |
| users | 28 created, 27 roles assigned | `Existing users left untouched: 28`, `Roles assigned: 0` |
| equipment | 14 created | 0 created, 14 updated |
| funding agencies | 375 created | 375 unchanged |
| `seed_email_templates` | 31 created | 31 updated |

Both runs print one warning, and it is expected:
`bioimac@ucm.es has areas='preclinical' but no evaluator role`. The row's roles were
cleared on purpose in 1acb6d1.

---

## Files

### `organizations.tsv`

Columns map 1:1 to model fields. `name`, `ISO2`, `country` and `organization_type` are
required. The loader upper-cases `ISO2`.

| Column | Notes |
|---|---|
| `name` | Natural key. **Not unique in the database.** Applicants create organizations from the profile form's "Other (create new)" option (all fields except `iso2`, which a coordinator fills in the admin). Two rows with the same name make the loader crash on that name. |
| `short_name`, `vat`, `address`, `city`, `zip` | Optional. |
| `ISO2` | Two letters, e.g. `ES`. |
| `country` | English name. |
| `organization_type` | One of the labels below. |

| `organization_type` label (in the file) | Stored code |
|---|---|
| `Technology Centre` | `technology_centre` |
| `Public Research Organisation (PRO)` | `pro` |
| `Higher Education Institution (HEI)` | `hei` |
| `SME` | `sme` |
| `Large Enterprise` | `large_enterprise` |
| `Other` | `other` |

A load overwrites every column of a matching row, blanks included. If you adopt an
organization an applicant created, copy what they typed into the row rather than
leaving cells empty (backlog #43(b)).

### `nodes.tsv`

| Column | Notes |
|---|---|
| `code` | Natural key, used in `users.tsv` and `equipment.tsv`. |
| `organization_name` | Must match an organization's `name` exactly. `Node.name` is not a field: it returns the organization's name. |
| `location`, `description`, `acknowledgment_text`, `contact_email`, `contact_phone` | Optional. `contact_email` is shown to applicants on the access hand-off page. |
| `is_active` | Blank means **False**. Write `TRUE`. |

`director` isn't in the file. Set it in the admin; loads leave it alone.

### `users.tsv`

| Column | Notes |
|---|---|
| `email` | Natural key and login. Lower-cased on load. |
| `first_name`, `last_name` | Required, or the row is skipped. |
| `organization_name` | Optional; must match an organization if filled. |
| `orcid`, `phone`, `position` | Optional, not validated by the loader (see above). No `_NNNN` phone extensions. |
| `is_staff` | `TRUE` lets the account into the Django admin (limited to its permissions) and exempts it from the profile-completion redirect. |
| `is_active` | Blank means **False on create**, so write `TRUE` for anyone who should log in. |
| `roles` | `;`-separated. See below. |
| `areas` | `;`-separated evaluator areas. See below. |
| `auto_data_consent` | Blank means False on create. |

**Roles:** `coordinator`, `evaluator`, `applicant`, and `node_coordinator:NODE_CODE`, the
only role with a `:` qualifier. Separate several with `;`, e.g.
`node_coordinator:BioImaC;evaluator`. Model role names are `applicant`,
`node_coordinator`, `evaluator`, `coordinator` and `admin`. A name outside that list is
written anyway, so check spelling.

**Areas:** `preclinical`, `clinical`, `radiochemistry`, `;`-separated, in any order
(order is not compared). They are stored on the evaluator `UserRole` row only. Other role
rows always get an empty value. Areas on a user with no evaluator role produce a warning
and are ignored. Nothing requires an evaluator to have an area: not the loader, not the
admin, not the profile form. But an evaluator with none is **skipped by area-matched
assignment**.

#### How the users loader treats an existing account

The TSV is **not** the authority for a person's own profile. `phone`, `position`,
`orcid`, `organization` and `auto_data_consent` are on the profile form, and evaluators
can change their own areas there too. So the loader is split:

- **Create-only by default (#43).** A new email is created with every column from the
  file, the password `changeme123`, and a verified primary email address. For an
  existing email, the profile fields and `is_active` are **left alone**. It reports
  `· Exists, profile untouched`. `--update-existing` brings back the old
  overwrite-everything behaviour, blanks included. Always pair it with `--dry-run` first.
- **Roles are applied in both modes.** Each role in the cell is created if missing and
  **set `is_active=True`** if it exists. That re-activates a role retired in the admin
  (#81, parked for 2027). The loader never removes or deactivates a role, so a role
  granted by mistake must be removed by hand.
- **A blank `areas` cell is never written (#61).** It means "the file isn't saying". A
  **filled** cell wins over the DB, and that includes an evaluator's own edit on the
  profile page.

`populate_redib_users --dry-run` prints what a real run would do and writes nothing:

| Line | Meaning |
|---|---|
| `+ Would create: <email>` | New account, with every field listed. |
| `= Unchanged: <email>` | Profile matches the file. |
| `· Exists, profile protected: <email>` then `field: 'db' would have become 'tsv' — not applied` | The file differs, but create-only mode won't write it. Informational. |
| `~ Would update: <email>` | Only with `--update-existing`. |
| `→ Role <role>: would create` / `would update (areas: … -> …)` / `would update (is_active: False -> True)` | **These are real changes.** Read every one. |

`scripts/check_role_drift.py` is the read-only companion. Pipe it into
`manage.py shell`. It compares active `UserRole` rows and evaluator areas with
`users.tsv` in both directions:

```bash
python manage.py shell < scripts/check_role_drift.py
```

- `TSV only : <role>   <- the load WOULD add this` means the role is missing or retired in the DB.
- `areas : DB '…' -> TSV '…'` means the load would overwrite the areas.
- `DB only : <role>` means someone granted it outside the file: mirror it into the file, or revoke it.

Self-registered applicants are counted, not listed. Its closing line, "Inactive rows are
never touched by the loader", is wrong: see #81 above.

**On production, today (2026-09):** five evaluators retired on 2026-09-15 (#81) keep
`roles=evaluator` in the file as the historical record. So every dry-run shows five
`would update (is_active: False -> True)` lines, and the drift check shows five
`TSV only : evaluator` lines. **A real `populate_redib_users` run would re-activate
them.** Production therefore makes user and role changes by hand and uses the dry-run and
the drift check only to prove the file matches (see the recipes below). If a real load is
ever needed, pass `--tsv` a file with the header plus only the rows you mean to load.
The loader touches nothing else (verified on a scratch DB, 2026-09-28).

### `equipment.tsv`

| Column | Notes |
|---|---|
| `node_code` | Must match a node `code`. |
| `name` | Part of the natural key, with `node_code`. Max 100 characters. |
| `category` | `mri`, `pet`, `ct`, `pet_ct`, `pet_mri`, `spect_pet_ct`, `spect_pet_ct_oi`, `cyclotron`, `spect`, `ultrasound`, `optical`, `other`. |
| `description` | Optional; multi-line allowed (quoted). |
| `area` | `preclinical`, `clinical`, `radiochemistry`, or blank. Drives evaluator matching. |
| `is_essential`, `is_active` | Blank means False. |

The loader also reads a `technical_specs` column if one exists. This file has none, so
**every load blanks any technical specs typed into the admin**. Add the column if you
start using them.

### `funding_agencies.tsv`

| Column | Notes |
|---|---|
| `name` | Natural key (unique in the model). A duplicate inside the file is skipped with a warning. |
| `origin_of_funds` | One of the labels below. On rerun a changed label updates the row. |

| `origin_of_funds` label (in the file) | Stored code |
|---|---|
| `Spanish Government` | `spanish_government` |
| `International / Non-EU` | `international_non_eu` |
| `Spanish Regional Government` | `spanish_regional` |
| `European Union` | `european_union` |
| `Institutional / Internal` | `institutional` |
| `Private / Philanthropic` | `private` |
| `Other` | `other` |

These rows fill the funding-agency dropdown in application Step 2. The selected agency's
origin pre-fills the application's "Origin of Funds".

---

## Recipes

**On dev:** edit the file and run its loader (for users, `--dry-run` first). **On
production** the practice (commits d7ff65a, 74609d7, c29c4fe, 794923e) is:

1. Make the change in the production DB by hand. Use the Django admin or
   `docker compose -f docker-compose.prod.yml exec web python manage.py shell`.
2. Mirror it into the TSV in the same sitting, matching the DB field for field.
3. Prove the match. Run the drift check and `populate_redib_users --dry-run` (see
   [DEPLOYMENT.md § Running Management Commands](../docs/DEPLOYMENT.md#running-management-commands)
   for running them against the edited file). The expected result is 0 to create, the
   changed row `= Unchanged`, and no role lines beyond the known retired ones (the five
   #81 evaluators, plus any role you have just retired).
4. Commit only `data/` with a subject like
   `Users: add evaluator Jane Doe (jane.doe@example.org), preclinical;clinical`. The body
   says what was changed by hand and what the dry-run and drift check showed. Push.

### Add a user, or an evaluator with areas

On production, in `manage.py shell`:

```python
from allauth.account.models import EmailAddress
from core.models import User, UserRole, Organization, Node
u = User.objects.create_user(
    'jane.doe@example.org', password=None,    # lower-case; no usable password
    first_name='Jane', last_name='Doe', is_active=True,
    organization=Organization.objects.get(name='Universidad Complutense de Madrid'),
)
EmailAddress.objects.create(user=u, email=u.email, verified=True, primary=True)
UserRole.objects.create(user=u, role='evaluator', areas='preclinical;clinical')
# node coordinator instead:  UserRole.objects.create(user=u, role='node_coordinator', node=Node.objects.get(code='BioImaC'))
```

The person sets a password with "Forgot password" on the login page. The admin's
**Add user** form insists on a password, and the loader would set `changeme123`, which is
why production uses the shell. They will be sent to `/profile/` to fill in phone and
position on first login.

Then append the row to `users.tsv`:

```
jane.doe@example.org	Jane	Doe	Universidad Complutense de Madrid				FALSE	TRUE	evaluator	preclinical;clinical	
```

This recipe was checked on a scratch DB. With that row appended, the dry-run reports
`= Unchanged: jane.doe@example.org` and 0 to create. If the organization is new, add it
first (below).

### Retire a role, or deactivate a person

In the admin, open **User Roles**, find the row and untick **Is active**. For someone
leaving altogether, also untick **Active** on the user (a Permissions field). The login
stops working. Nothing is deleted.

In `users.tsv`, set `is_active` to `FALSE` for a departing person. **Leave the `roles`
cell as it is.** The file is read as the record of who has served (Ryan's decision on
#81). The cost is the known dry-run and drift lines described above. To keep a retired
role from coming back, **don't run a real users load on production.** If one is
unavoidable, give it a file with only the new rows. Clearing the `roles` cell (1acb6d1)
also works, but it erases that history.

To reactivate, tick both boxes again and set `is_active` back to `TRUE` (74609d7).

### Add or correct equipment

Equipment, nodes and funding agencies are the coordination team's data. The file is the
authority and the loader is safe to run, including on production:

1. Edit `equipment.tsv`: `node_code`, exact `name`, `category`, `area`, `TRUE` for
   `is_active` (and `is_essential` if it is).
2. Commit and push. On production, deploy (`git pull` then `up -d --build`) so the image
   carries the new file, then run
   `docker compose -f docker-compose.prod.yml exec web python manage.py populate_redib_equipment`.
3. Check the new row in the output (`✓ Created: NODE - Name`).

**Renaming is the trap.** The key is (`node_code`, `name`), so a new name creates a
*second* row. The old one stays active and keeps its references from calls and
applications. To rename, change the name in the admin **and** in the file, then load.
To retire equipment, set `is_active` to `FALSE`. Deleting the row from the file does
nothing without `--sync`.

### Add an organization

1. Search the admin's **Organizations** first. Applicants create them, and a near-miss
   name ("Universidad Complutense" vs "Universidad Complutense de Madrid") gives two rows.
2. On production, add it in the admin (Organizations, then Add). On dev you can run the
   loader instead.
3. Append the row to `organizations.tsv` with the same values: `ISO2`, English
   `country`, and the exact `organization_type` label.
4. Commit it with the user it was added for (d7ff65a, 794923e), or on its own.

Running `populate_redib_organizations` on production isn't needed for one row. It
rewrites every listed organization from the file, which overwrites any admin edits to
those rows.

## Editing the files

- Use a text editor that shows tabs, or a spreadsheet saved as "Tab-separated text",
  UTF-8, **no BOM**. Keep the CRLF line endings: `git diff` should show only the lines you
  meant to change.
- Excel mangles a leading `+` in phone numbers (it becomes a formula) and exports
  Windows-1252. Check both.
- Keep multi-line equipment descriptions quoted as they are.
- Backlog #6 tracks an xlsx-to-TSV converter with these checks built in.
