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

1. `organizations.tsv` (no deps)
2. `nodes.tsv` (depends on organizations — `Node.organization` is a required FK)
3. `users.tsv` (depends on organizations; node_coordinator role qualifiers depend on nodes)
4. `equipment.tsv` (depends on nodes)
5. `funding_agencies.tsv` (no deps)

## Files

### `nodes.tsv`
**Loader:** `python manage.py populate_redib_nodes [--tsv data/nodes.tsv] [--sync]`
**Model:** `core.Node`

| Column | Required | Notes |
|---|---|---|
| `code` | Yes | Unique identifier (used as natural key) |
| `organization_name` | Yes | **FK lookup:** must match `name` of an existing `Organization`. The loader resolves it to `Node.organization` and aborts the import if no match exists. Run `populate_redib_organizations` first. |
| `location` | No | Free text |
| `description` | No | |
| `acknowledgment_text` | No | Text for publication acknowledgments |
| `contact_email` | No | |
| `contact_phone` | No | |
| `is_active` | No | TRUE/FALSE/1/0/YES (default TRUE) |

**Display name.** `Node.name` is no longer a stored field — it is a property that returns `Node.organization.name`. Templates that use `{{ node.name }}` keep working unchanged. For compact display, prefer `{{ node.organization.short_name|default:node.organization.name }}`.

**Encoding:** UTF-8, same Excel-export caveat as `organizations.tsv` above.

**Not loadable from TSV:** `director` (FK to User). Set via Django admin after users are loaded.

---

### `organizations.tsv`
**Loader:** `python manage.py populate_redib_organizations [--tsv data/organizations.tsv] [--sync]`
**Model:** `core.Organization`

The TSV columns map 1:1 to model fields (this is the upstream reporting source —
keep them aligned).

| Column | Required | Notes |
|---|---|---|
| `name` | Yes | Used as natural key for lookup |
| `short_name` | No | Acronym / short display name (e.g. `CIC biomaGUNE`) |
| `vat` | No | VAT/NIF number |
| `ISO2` | Yes | ISO 3166-1 alpha-2 country code (e.g. `ES`, `FR`, `US`). Loader uppercases. |
| `country` | Yes | Country name in English |
| `organization_type` | Yes | Human-readable label, see mapping below |
| `address` | No | Street address |
| `city` | No | |
| `zip` | No | Postal code |

**`organization_type` label → code mapping** (loader translates the TSV label to the
short code stored in the DB):

| TSV label (in file) | Stored code |
|---|---|
| `Technology Centre` | `technology_centre` |
| `Public Research Organisation (PRO)` | `pro` |
| `Higher Education Institution (HEI)` | `hei` |
| `SME` | `sme` |
| `Large Enterprise` | `large_enterprise` |
| `Other` | `other` |

Unknown labels abort the import (no partial loads).

**Encoding:** the loader requires UTF-8. Excel-on-Windows exports default to
Windows-1252 / CP1252 — convert before committing (`iconv -f cp1252 -t utf-8`),
or use the planned xlsx→tsv tool (see `docs/developer/backlog.md` #6).

**Why this exists:** `populate_redib_users` will auto-create organizations as a side
effect when it encounters an unknown `organization_name`, defaulting to `type='other'`
with no country or VAT. This TSV lets you load real organization data first so users can
be linked to fully-populated org records.

**Self-service entries:** When a user picks "Other (create new)" from the
organization dropdown on `/profile/`, all model fields except `iso2` are required;
`iso2` is left blank for a coordinator to fill via Django admin afterward.

---

### `users.tsv`
**Loader:** `python manage.py populate_redib_users [--tsv data/users.tsv] [--sync] [--update-existing]`
**Model:** `core.User` + `core.UserRole`

> **This TSV is not authoritative for an existing user's profile.** Unlike every
> other file in `data/`, the rows here describe people who can edit their own
> record through the portal — `phone`, `position`, `orcid`, `organization` and
> `auto_data_consent` are all on the profile form. A blank cell would be written
> as a deliberate empty value and silently revert whatever they typed.
>
> So the loader runs **create-only by default**: new users are created, roles are
> applied to everyone, and an existing user's profile fields are left alone. The
> old overwrite-everything behaviour is still there behind `--update-existing`;
> pair it with `--dry-run` first, always.
>
> `is_active` is held back the same way. It is ReDIB's field, not the user's, but
> a blank cell reads as "not filled in" rather than "deactivate this person" — a
> plain load against production on 2026-08-19 would have switched off a serving
> evaluator whose cell happened to be empty.
>
> Roles are applied in both modes: `UserRole` has no portal editor, so there is
> no user-authored value to lose. See backlog #43 for the durable fix.
>
> **One field on the role row is held back too: `areas`.** A blank `areas` cell
> means "the TSV isn't saying", not "no areas", and is never written (backlog
> #61). Writing it would strip a serving evaluator's specialization on any
> re-run — and an evaluator with no areas is skipped by area-matched assignment
> entirely, which for the October load is the same outcome as deactivating them.
> A **filled** cell is still authoritative and still wins, so narrowing or
> changing someone's areas works exactly as before; run the drift check below
> first so a stale cell doesn't do it by accident.

| Column | Required | Notes |
|---|---|---|
| `email` | Yes | Used as natural key + login identifier |
| `first_name` | Yes | |
| `last_name` | Yes | |
| `organization_name` | No | **FK lookup:** must match `Organization.name` of an existing row. Loader aborts the import on miss. Run `populate_redib_organizations` first. |
| `orcid` | No | e.g. `0000-0002-1234-5678`. Must satisfy `ORCID_VALIDATOR` (`XXXX-XXXX-XXXX-XXXX`, last char may be `X`). |
| `phone` | No | Digits, spaces, and `+ - . ( )` only. **No underscores** (the loader does not accept extension suffixes like `+34 91 ... _5404` — strip them in the source data). |
| `position` | No | Job title |
| `is_staff` | No | `TRUE` / `1` / `YES` enables; **anything else (including blank) is False**. |
| `is_active` | No | Same rule as `is_staff` **on create**. **Default is False** — be explicit (`TRUE`) for accounts that should be able to log in. On an existing user this column is ignored unless `--update-existing` is passed. |
| `roles` | No | Semicolon `;`-separated role names. See syntax below. |
| `areas` | No | Semicolon `;`-separated specialization areas. Only meaningful for evaluators. **Invalid values abort the import** — see conventions below. |
| `auto_data_consent` | No | Same rule as `is_staff` **on create**. Default False. User-editable on the profile form, so ignored on an existing user unless `--update-existing` is passed. |

> **Roles are the TSV's to own — keep it that way.** `UserRole` has no portal
> editor, but a superuser can change roles in Django admin. The loader only ever
> adds or reactivates roles, never removes one, so an admin *grant* is not lost
> by a later load — but this file quietly stops being the record of who holds
> what. Prefer editing `users.tsv` and running the loader. If an admin change
> does happen, **mirror it into this file and commit it** in the same sitting.
>
> **"Never removes" was true of the role row and false of the areas on it** —
> that is #61, found on production 2026-08-21, and it is fixed above. Note the
> asymmetry that remains: the loader can *widen* authorization but never revoke
> it, so a role granted by mistake has to be removed by hand.
>
> **Before any load against production, run the drift check:**
>
> ```bash
> python manage.py shell < scripts/check_role_drift.py    # writes nothing
> ```
>
> It compares roles *and* evaluator areas against this file in both directions,
> and summarises self-registered applicants rather than listing them (they are
> not part of the reference set and never need mirroring here). Then
> `populate_redib_users --dry-run`, and only then the real run.

**Roles syntax** (semicolon `;`-separated):
- Simple: `coordinator`, `applicant`, `evaluator`
- Node-specific: `node_coordinator:CIC-biomaGUNE` (the `:NODE_CODE` qualifier is the
  only place a sub-delimiter is allowed inside a `roles` cell)
- Multiple roles: `coordinator;evaluator` or `node_coordinator:BioImaC;evaluator`

**Areas syntax** (semicolon `;`-separated):
- Single: `clinical`
- Multiple: `clinical;preclinical;radiochemistry`
- Allowed values: `clinical`, `preclinical`, `radiochemistry`

**Areas convention:**
- Areas are stored on the user's evaluator `UserRole` row in the database. If a user has
  multiple roles (e.g. `coordinator;evaluator`), the `areas` value applies **only to the
  evaluator role**; other role rows get an empty areas field.
- If `areas` is set but the user has no evaluator role, the loader emits a warning and
  the value is ignored.
- **If `areas` contains an unknown value, the loader aborts with `CommandError`.** Fix
  the source TSV — typos like `prelcincal` slip through silently otherwise.
- Areas are required at the **profile page** UI level (evaluators must provide at least
  one area when editing their profile in the portal). They are *not* required at the
  TSV/admin level — you can leave the cell blank if needed for testing or manual entry.

**Separator consistency:**
- The `;` character is used **everywhere** that a cell holds multiple values: between
  roles in the `roles` column, between areas in the `areas` column, and inside the
  stored `UserRole.areas` model field. The only exception is the `node_coordinator:NODE`
  qualifier, which uses `:` to separate role from node code.

**Notes:**
- All loaded users get the default password `changeme123` and a verified email address (allauth `EmailAddress`).
- Encoding: UTF-8. Same Excel-export caveat applies (see `organizations.tsv`).
- Hard-error conditions (loader aborts the entire import — no partial loads):
  - `organization_name` not found in `Organization` table
  - `roles` qualifier `node_coordinator:NODE_CODE` references a missing node
  - `areas` contains a value outside `preclinical` / `clinical` / `radiochemistry`

---

### `equipment.tsv`
**Loader:** `python manage.py populate_redib_equipment [--tsv data/equipment.tsv] [--sync]`
**Model:** `core.Equipment`

| Column | Required | Notes |
|---|---|---|
| `node_code` | Yes | **FK lookup:** must match an existing `Node.code`. Loader aborts on miss (run `populate_redib_nodes` first). |
| `name` | Yes | |
| `category` | Yes | One of: `mri`, `pet`, `ct`, `pet_ct`, `pet_mri`, `spect_pet_ct`, `spect_pet_ct_oi`, `cyclotron`, `spect`, `ultrasound`, `optical`, `other`. Loader hard-errors on invalid value. |
| `description` | No | Multi-line descriptions are supported (wrapped in quotes in the file) |
| `area` | No | Specialization area for evaluator-matching. One of: `preclinical`, `clinical`, `radiochemistry`. Blank allowed; **invalid values abort the import**. |
| `is_essential` | No | `TRUE` / `1` / `YES` enables; **anything else (including blank) is False**. |
| `is_active` | No | Same rule as `is_essential`. |

**Not loadable from TSV:** `technical_specs` (rarely used; set via admin if needed).

---

### `funding_agencies.tsv`
**Loader:** `python manage.py populate_redib_funding_agencies [--tsv data/funding_agencies.tsv] [--sync]`
**Model:** `applications.FundingAgency`

| Column | Required | Notes |
|---|---|---|
| `name` | Yes | Used as natural key (model has `unique=True`) |
| `origin_of_funds` | Yes | Human-readable label, see mapping below. Loader translates to short code. |

**`origin_of_funds` label → code mapping** (loader translates the TSV label to the short
code stored in the DB):

| TSV label (in file) | Stored code |
|---|---|
| `Spanish Government` | `spanish_government` |
| `International / Non-EU` | `international_non_eu` |
| `Spanish Regional Government` | `spanish_regional` |
| `European Union` | `european_union` |
| `Institutional / Internal` | `institutional` |
| `Private / Philanthropic` | `private` |
| `Other` | `other` |

Unknown labels abort the import (no partial loads). On re-run, existing agencies are
matched by `name`; if `origin_of_funds` has changed in the TSV, the DB record is updated
to match.

**Encoding:** UTF-8, same Excel-export caveat as `organizations.tsv`.

**Why this exists:** The `FundingAgency` model backs the funding agency dropdown in
application Step 2. Without seed data, applicants must create entries via the "Other"
flow during application submission. A seed list lets common Spanish/EU agencies appear in
the dropdown immediately (e.g. AEI, ERC, ISCIII). Each agency carries an
`origin_of_funds` classification that auto-populates the application's "Origin of Funds"
field when selected.

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

The `setup_base_database` management command runs all seven steps in the correct dependency
order with sensible defaults:

1. `populate_redib_organizations`
2. `populate_redib_nodes`
3. `populate_redib_users`
4. `populate_redib_equipment`
5. `populate_redib_funding_agencies`
6. `seed_email_templates`
7. Site config (sets `Site.domain` / `Site.name` from `SITE_DOMAIN` / `SITE_NAME` env vars)

Use `--reset --yes` to clear existing data first (preserves superusers).

## Editing TSV Files

- Most spreadsheet apps (LibreOffice Calc, Excel, Google Sheets) can open and save TSV
  with the right options. When saving, choose "Tab-separated text" / `\t` delimiter and
  UTF-8 encoding.
- Plain text editors work too — just make sure your editor inserts literal tabs (not
  spaces) when you press Tab. Most editors have a "show whitespace" mode to verify.
- Multi-line equipment descriptions are quoted in the file (e.g. `"line1\nline2"`).
  Don't unquote them manually; the loader handles them via Python's `csv` module.
