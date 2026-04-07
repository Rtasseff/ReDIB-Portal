# Data Directory

TSV (tab-separated values) files used to populate or sync the ReDIB portal's reference
data tables. These are loaded by Django management commands. None are auto-loaded — you
explicitly run the appropriate `populate_redib_*` command.

**Why TSV instead of CSV:** Many fields (especially equipment descriptions) contain
commas, which made the CSV format fragile and required careful quoting. Tabs do not
appear in any of our data fields, so TSV avoids the quoting headache entirely. Multi-line
fields (e.g. equipment descriptions with embedded newlines) are still wrapped in quotes
in the file, which Python's `csv` module handles correctly via `delimiter='\t'`.

## Load Order

FK dependencies require this order:

1. `nodes.tsv` (no deps)
2. `organizations.tsv` (no deps)
3. `users.tsv` (depends on nodes + organizations)
4. `equipment.tsv` (depends on nodes)
5. `funding_agencies.tsv` (no deps)

## Files

### `nodes.tsv`
**Loader:** `python manage.py populate_redib_nodes [--tsv data/nodes.tsv] [--sync]`
**Model:** `core.Node`

| Column | Required | Notes |
|---|---|---|
| `code` | Yes | Unique identifier (used as natural key) |
| `name` | Yes | Display name |
| `location` | No | Free text |
| `description` | No | |
| `acknowledgment_text` | No | Text for publication acknowledgments |
| `contact_email` | No | |
| `contact_phone` | No | |
| `is_active` | No | TRUE/FALSE/1/0/YES (default TRUE) |

**Not loadable from TSV:** `director` (FK to User). Set via Django admin after users are loaded.

---

### `organizations.tsv`
**Loader:** `python manage.py populate_redib_organizations [--tsv data/organizations.tsv] [--sync]`
**Model:** `core.Organization`

| Column | Required | Notes |
|---|---|---|
| `name` | Yes | Used as natural key for lookup |
| `vat` | No | VAT/NIF number |
| `country` | No | Default 'Spain' |
| `organization_type` | Yes | One of: `company`, `university`, `other` |
| `address` | No | |
| `website` | No | URL |

**Why this exists:** `populate_redib_users` will auto-create organizations as a side
effect when it encounters an unknown `organization_name`, defaulting to `type='other'`
with no country or VAT. This TSV lets you load real organization data first so users can
be linked to fully-populated org records.

---

### `users.tsv`
**Loader:** `python manage.py populate_redib_users [--tsv data/users.tsv] [--sync]`
**Model:** `core.User` + `core.UserRole`

| Column | Required | Notes |
|---|---|---|
| `email` | Yes | Used as natural key + login identifier |
| `first_name` | Yes | |
| `last_name` | Yes | |
| `organization_name` | No | String lookup against `Organization.name`. If not found, auto-creates with `type='other'` (warning emitted) |
| `orcid` | No | e.g. `0000-0002-1234-5678` |
| `phone` | No | |
| `position` | No | Job title |
| `is_staff` | No | TRUE/FALSE (default FALSE) |
| `is_active` | No | TRUE/FALSE (default TRUE) |
| `roles` | No | See role syntax below |
| `auto_data_consent` | No | TRUE/FALSE (default FALSE) — blanket data processing consent for applications |

**Roles syntax** (semicolon `;`-separated for multiple roles):
- Simple: `coordinator`, `applicant`
- Node-specific: `node_coordinator:CIC-biomaGUNE`
- Area-specific (single): `evaluator:preclinical`
- Area-specific (multiple): `evaluator:clinical,preclinical` — comma `,` separates multiple areas
- Multiple roles: `coordinator;evaluator:clinical,radiochemistry`

Allowed area values: `clinical`, `preclinical`, `radiochemistry`.

**Notes:**
- All loaded users get the default password `changeme123` and a verified email address (allauth `EmailAddress`).
- The `auto_data_consent` column is optional for backwards compatibility — missing values default to FALSE.
- Within the `roles` column, **comma is used as a sub-delimiter** for multi-value areas. This is the only place commas have special meaning inside a TSV cell.

---

### `equipment.tsv`
**Loader:** `python manage.py populate_redib_equipment [--tsv data/equipment.tsv] [--sync]`
**Model:** `core.Equipment`

| Column | Required | Notes |
|---|---|---|
| `node_code` | Yes | Must match an existing `Node.code` |
| `name` | Yes | |
| `category` | Yes | One of: `mri`, `pet`, `ct`, `pet_ct`, `pet_mri`, `spect_pet_ct`, `spect_pet_ct_oi`, `cyclotron`, `spect`, `ultrasound`, `optical`, `other` |
| `description` | No | Multi-line descriptions are supported (wrapped in quotes in the file) |
| `area` | No | **Currently unused by the loader.** Reserved for future use to mark which `applications.SPECIALIZATION_AREAS` an equipment belongs to. Existing values use: `clinical`, `preclinical`, `radiochemistry` |
| `is_essential` | No | TRUE/FALSE (default TRUE) |
| `is_active` | No | TRUE/FALSE (default TRUE) |

**Not loadable from TSV:** `technical_specs` (rarely used; set via admin if needed).

---

### `funding_agencies.tsv`
**Loader:** `python manage.py populate_redib_funding_agencies [--tsv data/funding_agencies.tsv] [--sync]`
**Model:** `applications.FundingAgency`

| Column | Required | Notes |
|---|---|---|
| `name` | Yes | Used as natural key (model has `unique=True`) |

**Why this exists:** The `FundingAgency` model was added in batch 1 (Issue 16). Without
seed data, applicants must create entries via the "Other" flow during application
submission. A seed list lets common Spanish/EU agencies appear in the dropdown
immediately (e.g. AEI, ERC, MCIN, ISCIII).

---

## Sync Mode

The `--sync` flag on `populate_redib_*` commands handles records that are in the database
but no longer in the TSV. Behavior depends on the model:

- **`Node`, `User`, `Equipment`**: Marks orphan records as `is_active=False`. Preserves
  history but removes them from active dropdowns and queries.
- **`Organization`, `FundingAgency`**: These models have no `is_active` field. Sync mode
  *lists* orphans (along with the count of FK references) but does not modify them. Review
  and delete via Django admin if appropriate.

## Bulk Setup

The `setup_base_database` management command runs all six steps in the correct dependency
order with sensible defaults:

1. `populate_redib_nodes`
2. `populate_redib_organizations`
3. `populate_redib_users`
4. `populate_redib_equipment`
5. `populate_redib_funding_agencies`
6. `seed_email_templates`

Use `--reset --yes` to clear existing data first (preserves superusers).

## Editing TSV Files

- Most spreadsheet apps (LibreOffice Calc, Excel, Google Sheets) can open and save TSV
  with the right options. When saving, choose "Tab-separated text" / `\t` delimiter and
  UTF-8 encoding.
- Plain text editors work too — just make sure your editor inserts literal tabs (not
  spaces) when you press Tab. Most editors have a "show whitespace" mode to verify.
- Multi-line equipment descriptions are quoted in the file (e.g. `"line1\nline2"`).
  Don't unquote them manually; the loader handles them via Python's `csv` module.
