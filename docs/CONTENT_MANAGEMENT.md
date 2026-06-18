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

## Collecting images (heroes, reconstructions, photos)

Editors and node contributors supply the photography and scientific images
that fill hero banners, cards, and news posts. How the site renders them
drives what to ask for.

**How the site uses them.** Every hero is cropped to a wide banner by Wagtail's
`fill-` image operation. The largest rendition is the **homepage carousel at
1920×760**; node / section / equipment heroes render ~1200×420–500; cards use
480×300 (16:10); team headshots 220×220 (square). After uploading in `/cms/`,
**set the image's focal point** in the Wagtail image editor — `fill-` then
crops around that point instead of dead-centre. This is the single most
effective fix for a hero that crops awkwardly.

There are two kinds of source image, with different rules:

### Reconstruction / scientific images (the common case)

PET/MRI/CT renders and slices. Usually **square and small** (matrix 128–512 px),
so they do **not** fit the wide hero well — a flat slice loses its top and
bottom to the crop, and upscaling a 256-px image to a 1920-px banner looks
blocky.

- Best hero candidates: **3D renders, MIPs, fused/volume views** rendered large
  (long edge ≥ ~1500 px). Flat 2D slices are better as cards/insets. Color/
  fused images read better than grayscale slices.
- **PNG**, lossless, with the **window/level already applied** (send it looking
  as it should). No pre-cropping or enlarging — native size and shape.
- **⚠️ No patient-identifying data.** DICOM metadata is stripped on PNG/JPG
  export, but **burned-in corner text (name / ID / date / institution) stays in
  the pixels** — check it. Prefer anonymized + consented, or preclinical /
  phantom data. This is a public EU site; treat PHI accordingly.
- Open design item: a **letterbox-on-dark hero variant** (show the square scan
  whole, centred on the teal panel, instead of cropping) is proposed but not
  built — see [REBUILD_STATUS.md](marketing/REBUILD_STATUS.md).

### Photos (facility, equipment, team — the minority)

- **Landscape**, as large as possible, **JPG**, straight from the phone/camera —
  don't crop, resize, or screenshot.
- iPhone photos arrive as **HEIC**, which Wagtail won't ingest without the
  `pillow-heif` package (not yet installed) — convert on receipt, or install it.

**For both:** ask people to send the **original file** as an attachment or via
Drive/Dropbox — **never pasted inline or over WhatsApp**, which silently
downscale to ~1000 px (the #1 reason a collected image is too small to use).

### Request to forward

Spanish contributors who supply reconstructions are imaging professionals, so
the technical wording lands fine; the photo bullets are the plain-language part.

```
Estamos recopilando imágenes para la nueva web de ReDIB — imágenes de
reconstrucción/científicas y alguna foto. Consejos para que luzcan mejor:

Si es una imagen de reconstrucción / científica:
• Expórtala a la MAYOR resolución que permita tu visor. Los renders 3D, MIP y
  vistas de volumen/fusión son los mejores banners (lado largo ≥ ~1500 px).
  Los cortes 2D suelen ser pequeños — mejor como detalle que como banner.
• Guárdala en PNG, con tu window/level ya aplicado (tal como debe verse).
• No la recortes ni la amplíes; envíala en tamaño/forma original.
• SIN identificadores de paciente: nada grabado en las esquinas (nombre/ID/
  fecha); usa datos anonimizados y con consentimiento, o preclínicos/fantoma.

Si es una foto (instalación, equipamiento, equipo):
• Horizontal, lo más grande posible, en JPG, tal cual sale del móvil/cámara.

En ambos casos: envía el ARCHIVO ORIGINAL como adjunto o por Drive/Dropbox —
no pegado en el mensaje ni por WhatsApp (eso lo reduce). ¡Gracias!
```

(English equivalent: same structure — landscape JPG photos straight from the
device; reconstructions as high-res PNG renders, window/level applied, no
burned-in patient identifiers; original file as an attachment, not inline.)

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
| Hero treatment for square reconstruction images (letterbox vs crop) + `pillow-heif` for HEIC | [REBUILD_STATUS.md](marketing/REBUILD_STATUS.md) 2026-06-18 entry |
| SharePoint master-file links in this doc | TODO above |
