# Content management & data ownership

How the merged redib.net site is kept up to date: which information is
mastered in **SharePoint spreadsheets** and synced into the database, which
is edited directly through an **administration UI**, and how the two halves
of the system share data without duplicating it.

## One system, two faces

This codebase is the merge of two things that used to live apart:

1. **The COA portal** (`/portal/…`) — the transactional system for
   Competitive Open Access calls, applications, feasibility review,
   evaluation, resolution, and access tracking. It has been running in
   production and working well. **Principle: minimize changes here.**
2. **The public marketing site** (`/` and `/en/…`) — the Wagtail-powered
   rebuild of redib.net: about, nodes, equipment showcase, team, news,
   press, pricing, documentation. **Principle: this is where modernization
   effort goes.**

They are managed by the same small team and overlap heavily (equipment,
nodes, calls, contact info). The design goal that follows from this:
**every fact lives in exactly one place**, and the public site reads the
portal's data live rather than keeping its own copy. The second goal:
**dead simple to maintain** — non-developers must be able to keep the
content current without touching code.

## Master table — every content type and its single source of truth

| Content | System of record | How you update it | Where it appears |
|---|---|---|---|
| Equipment catalog | SharePoint xlsx → `core.Equipment` | [Sync runbook](#the-sync-runbook) | Portal call/application forms **and** marketing `/equipamiento/…` + node pages (live query) |
| Nodes | SharePoint xlsx → `core.Node` | Sync runbook | Portal workflow **and** marketing `/nodos/…` (live query) |
| Organizations | SharePoint xlsx → `core.Organization` | Sync runbook | Portal profiles & applications |
| Users & roles | SharePoint xlsx → `core.User` / `core.UserRole` | Sync runbook — **see caveat below** | Portal access control |
| Funding agencies | SharePoint xlsx → `applications.FundingAgency` | Sync runbook | Application form step 2 |
| Calls (convocatorias) | Portal `calls` app | Portal UI (ReDIB coordinator) | `/portal/calls/`; marketing pages **link** there, never copy |
| Applications & workflow | Portal apps | Portal UI per role | Portal only |
| News posts | Wagtail `NewsPage` | `/cms/` → Pages → Noticias | `/noticias/`, homepage teaser |
| Press items | Wagtail `PressItemPage` | `/cms/` → Pages → Prensa | `/prensa/` |
| Team | Wagtail `Person` snippets | `/cms/` → Snippets → People | `/equipo/` |
| Static pages (About, Acceso, legal, …) | Wagtail pages | `/cms/` → Pages | Their URLs |
| Homepage hero / carousel images | Wagtail `HomePage` + Images | `/cms/` | `/` and `/en/` |
| Pricing (Tarifas) | Rich-text body on `PricingPage` | `/cms/` — awkward today; structured model is an open item | `/tarifas/` |
| Governance PDFs | Wagtail Documents | `/cms/` → Documents | `/documentacion/` |
| External links | Wagtail `ExternalLink` snippets | `/cms/` → Snippets | Enlaces de interés, footer |
| Newsletter archive | `newsletters.Newsletter` | `/admin/` → Newsletters (upload self-contained HTML) | `/portal/newsletters/` |
| Newsletter mailing list / dispatch | **Not built yet** — [backlog #15](developer/backlog.md) | — | — |
| Email templates (workflow mail) | DB (`communications`) | `/admin/` or `seed_email_templates` | Portal emails |

Three admin surfaces, three audiences:

- **`/cms/` (Wagtail)** — marketing editors. News, press, pages, images,
  documents, snippets, redirects, ES↔EN translations.
- **`/admin/` (Django)** — portal staff. Reference-data one-off fixes,
  newsletter archive uploads, email templates.
- **Portal UI** — coordinators running the COA workflow itself.

## Tier 1 — SharePoint-mastered reference data

**What:** equipment, nodes, organizations, users/roles, funding agencies.

**Why SharePoint:** the network already maintains these as spreadsheets,
several non-developers contribute to them, and Excel is their working tool.
The portal does not try to replace that; it ingests it. The spreadsheet on
SharePoint is the master — the database is a synced copy.

> **TODO (fill in):** links to the master xlsx files on the ReDIB
> SharePoint, one per TSV in `data/`. Until then, ask the coordinator
> which workbook is current.

### The sync runbook

1. **Edit the master xlsx on SharePoint** (or receive an updated one).
2. **Export to UTF-8 TSV.** Excel on Windows exports CP1252 — convert
   (`iconv -f cp1252 -t utf-8`) or use the planned converter tool
   ([backlog #6](developer/backlog.md)), which will also QC enum values,
   phone formats, FK references, and separators before load.
3. **Replace the file in `data/`** and commit. The git history of
   `data/*.tsv` is the audit trail of every reference-data change.
4. **Run the loader(s)** in FK order (full column reference:
   [data/README.md](../data/README.md)):

   ```bash
   python manage.py populate_redib_organizations --sync
   python manage.py populate_redib_nodes --sync
   python manage.py populate_redib_users --sync      # caveat below
   python manage.py populate_redib_equipment --sync
   python manage.py populate_redib_funding_agencies --sync
   ```

   `--sync` deactivates (`is_active=False`) DB records no longer present in
   the TSV for Node/User/Equipment; for Organization/FundingAgency it only
   *lists* orphans for manual review. Loaders hard-error on unknown enums or
   missing FK targets — no partial loads.

5. **On production:** merge to `main`, pull on the VPS, then run the same
   commands inside the web container
   (`docker compose -f docker-compose.prod.yml exec web python manage.py …`).
   Full deploy steps: [DEPLOYMENT.md](DEPLOYMENT.md).

> **⚠️ Users loader caveat.** `populate_redib_users` is currently unsafe to
> re-run on production: it resets every listed user's password and stomps
> profile edits made in the portal ([backlog #13](developer/backlog.md)).
> Until that's fixed, make one-off user changes via `/admin/` and treat the
> users TSV as initial-load only.

**Cadence:** sync on change, manually. There is **no automated
SharePoint→DB pipeline, deliberately** — an unattended sync that can
deactivate equipment or users is riskier than a two-minute manual run with
a human looking at the loader output. If the manual step ever becomes a
burden, a scheduled pull via Microsoft Graph is the natural upgrade path —
explicitly deferred for simplicity.

## Tier 2 — CMS-edited content (news, press, pages, newsletters)

**What:** everything editorial — words, images, documents. Mastered in the
database, edited in a browser, no developer involved.

- **News / press:** `/cms/` → Pages → add a child under Noticias or Prensa.
  Posts without an image automatically get a branded fallback tile.
- **Team:** `/cms/` → Snippets → People (photo, role, order).
- **Bilingual:** Spanish is authored first (default locale), then
  translated to English via wagtail-localize — **human translation only**,
  no machine backend. An untranslated page simply doesn't exist at `/en/…`.
- **Newsletter archive:** upload the issue as one self-contained HTML file
  at `/admin/` → Newsletters; tick *is published* when ready. It appears at
  `/portal/newsletters/`.
- **Newsletter dispatch (mailing list):** not built. Backlog #15 covers it:
  send path through the existing `communications` pipeline, subscribe/
  unsubscribe affordance on the public site (legally required before first
  send), seed list of 170 addresses captured at
  `docs/marketing/newsletter-initial-list.csv` (not consent-verified).

**The `populate_*` / `marketing_init` commands are bootstrap-only.** They
rebuild a dev database from scratch (see the branch note in
[CLAUDE.md](../CLAUDE.md)). After cutover, production marketing content is
mastered in the production DB + media volume, maintained through `/cms/`,
and protected by the DB backup (`scripts/backup-db.sh`). Do **not** re-run
populate commands on production expecting them to "update" content — live
edits would win/lose unpredictably against the seed data.

## Where the tiers meet — the live-query bridge

The marketing pages for nodes and equipment wrap **editorial framing**
(Wagtail-edited intro text, hero image) around **live portal data**:

- `NodePage` carries a `related_core_node` FK; its template renders the
  node's equipment list from `core.Equipment` at request time.
- `EquipmentCategoryPage` carries an `area_key`
  (clinical / preclinical / radiochemistry) and queries matching equipment
  live.

So one equipment sync (Tier 1) updates the portal's application forms
**and** the public equipment showcase in a single step, with zero CMS work.
Same pattern for calls: marketing pages link to `/portal/calls/` — current
calls are never hand-copied onto the public site (that duplication is
exactly what the old site suffered from).

## Decision rule for anything new

1. **Does the portal workflow consume it?** → it's a portal/`core` model.
   If the network maintains it as a spreadsheet → Tier 1 (SharePoint +
   loader). If it's workflow state → portal UI owns it.
2. **Is it public storytelling only (words/images)?** → Tier 2, Wagtail.
3. **Both?** → master it in `core`, live-query it from the Wagtail template
   (the bridge pattern above). Never store the same fact in two places.

## Open items affecting this model

| Item | Where tracked |
|---|---|
| xlsx → TSV converter + QC tool | [backlog #6](developer/backlog.md) |
| Safe re-run semantics for the users loader | [backlog #13](developer/backlog.md) |
| Newsletter dispatch + opt-in/out | [backlog #15](developer/backlog.md) |
| Structured (CMS-friendly) pricing model | [REBUILD_STATUS.md](marketing/REBUILD_STATUS.md) deferred table |
| Admin CMS UX pass for non-technical editors | REBUILD_STATUS deferred table |
| SharePoint master-file links in this doc | TODO above |
