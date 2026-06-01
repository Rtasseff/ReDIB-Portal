# Marketing site — design & maintainability decisions

Companion to [REBUILD_STATUS.md](REBUILD_STATUS.md). That doc tracks *what
exists*; this one records *how the site should look and be maintained*, and
the future work that the current design is built to accommodate. Written
2026-06-01 at the start of the modernization pass.

## Goal

Make the public site look like a professional, modern home for a serious,
high-tech scientific infrastructure for researchers — clean and current, not
flashy or futuristic. Reference points the owner likes: **socib.es**
(favourite), eurobioimaging.eu, cells.es, rediris.es, home.cern. Common
threads: generous whitespace, strong typographic hierarchy, a restrained
brand-colour accent, big clear calls-to-action, photography-forward sections,
no heavy gradients or animation.

**Constraint that drives every decision: it must be dead simple to maintain.**
Content (words + images) does not change in this pass — only layout/visuals
and information architecture.

## Visual language

### Colour — traced to the logos
Sampled from the actual logo files:
- ICTS logo azure **`#137abc`** → `--brand` (primary).
- ReDiB logo deep teal **`#214f5f`** → `--ink-brand` (dark sections, headings accent, footer).

Palette (defined once as CSS custom properties in `static/css/marketing.css`):

| Token | Value | Use |
|---|---|---|
| `--brand` | `#137abc` | primary actions, links, accents |
| `--brand-dark` | `#0e5d92` | hover/active |
| `--brand-soft` | `#e8f2fa` | tinted section backgrounds, badges |
| `--ink-brand` | `#214f5f` | dark hero/footer band, deep headings |
| `--ink` | `#1d2a30` | body text |
| `--muted` | `#5b6b73` | secondary text |
| `--line` | `#e3e8eb` | borders/dividers |
| `--bg` / `--bg-soft` | `#ffffff` / `#f5f8fa` | page / alternating sections |

Keep the spirit of the logo (azure + teal on white). No new hues without a
reason; tints/shades of the two brand colours only.

### Type
**Inter** (Google Fonts) for a clean, modern, neutral feel — same family used
by many science/tech orgs. Loaded via CDN now; self-hosting is a future task
(see below). Headings: Inter 600–700, tight leading; body: Inter 400, 1.6
leading. A modular type scale lives in the tokens.

### Components
A small, reusable set, all styled in `marketing.css`: slim sticky header,
full-bleed hero, section rhythm (alternating white / `--bg-soft`), content
cards (soft shadow, hover lift), buttons (filled primary / outline / ghost),
badges/pills (for content type + "open call"), multi-column footer with the
ICTS logo. Bootstrap 5 stays as the **grid + utilities** layer; `marketing.css`
layers the brand theme on top. We do not fork Bootstrap.

## CSS & asset architecture (the maintainability rules)

1. **One stylesheet, tokens at the top.** All marketing styling lives in
   `static/css/marketing.css`. The `:root` block is the single source of truth
   for colour/type/spacing — change a token, the whole site follows. **No
   inline `<style>` blocks or `style=` attributes in templates** (the old
   inline carousel CSS moved into `marketing.css`).
2. **Static chrome vs. editorial content images are separate, by location:**
   - **Chrome/brand** (logos, icons, decorative) → `static/images/`, served
     via `{% static %}` (hashed by the manifest on `collectstatic`).
   - **Editorial content** (hero photos, team headshots, equipment, news) →
     **Wagtail media** (`media/`), managed through the populate commands / CMS
     and downloaded from source. Wagtail handles renditions/crops.
   - Rule of thumb: *if an editor will ever change it, it's content → Wagtail
     media; if a developer owns it, it's chrome → `static/`.*
3. **Templates carry structure + classes, never design values.** Spacing,
   colour, type come from CSS classes/tokens, so a redesign never means
   editing dozens of templates.

## Information architecture (this pass)

Final public top nav (ES shown; EN mirrors):

> **Quiénes somos · Equipamiento · Nodos · Equipo · Acceso · Actualidad · Contacto**
> &nbsp;&nbsp; + header CTAs: **Convocatorias** (primary) · **Acceso al portal** (login)

Changes from the faithful rebuild and **why**:

- **News + Press merged into one "Actualidad" feed.** The site needs a single
  place for external announcements, not two. `Actualidad` is one chronological
  feed combining news, press clippings, and newsletters, each tagged by type
  (Noticia / Prensa / Boletín). Newsletters are already `NewsPage`s, so they
  appear here automatically. The old two-item "Actualidad dropdown" is gone.
- **Rates removed from the top nav.** Pricing is a property of equipment, not a
  top-level destination. The `/tarifas/` page stays (URL preserved) but is
  surfaced *inside* the Equipment section, not the main menu.
- **Acceso stays public.** Access information and the governing documentation
  are the core of an ICTS's open-access mission and are public on every peer
  site (socib, eurobioimaging, cells, rediris). They live in the public
  **Acceso** section — *not* behind login — and that section foregrounds the
  open **Convocatorias** and links the governing PDFs. This is how we "move
  access into the portal experience without hiding it": Acceso is the public
  bridge from the marketing site into the portal.
- **Portal integration / Calls.** `/portal/calls/` is **public** (verified),
  while the rest of `/portal/` is behind login. So:
  - **Convocatorias / Calls** is a prominent public CTA (header + homepage
    hero + Acceso section) → `/portal/calls/`. *Future:* surface the upcoming
    calls live on the marketing site (see future tasks).
  - The login entry point is renamed from **"Portal"** to **"Acceso al
    portal" / "Portal login"** (alternatives considered: "Área privada",
    "Iniciar sesión" — easy one-line change; open to the owner's preference).

## Content corrections (this pass)

- **Team roles.** The "Comité de Coordinación" members José Luis Izquierdo,
  Borja Ibáñez Cabeza, and Luis Martí-Bonmatí are **Directors**; Gonzalo
  Pizarro Sánchez stays a member ("Vocal").
- **User-guide document label.** The portal user guide PDF is the **English**
  guide but was labelled "(Spanish)". Corrected on `/documentation/`.

## Future update architecture (deferred — designed for now)

The owner will maintain content through a mix of a dead-simple GUI and synced
Office files, with assets in synced folders. The portal and marketing site run
in **one Django project on one VPS** (agreed — maximise overlap). Reference
data is shared (`core.*`), so marketing reads it live and never duplicates it.

**Update channels (target):**

| Content | Channel | Notes |
|---|---|---|
| Equipment | synced **Excel** (≈ `data/equipment.tsv`) | importer → `core.Equipment` |
| Prices | **same Excel** as equipment (new sheet/columns) | needs a price model/fields; current equipment rows to be updated |
| Team | synced **Excel** | likely a `Person`/users-table importer; image per person |
| Node descriptions | synced **Excel** | importer → `NodePage` fields |
| Hero images | synced **folder** | mapped by page/slug |
| Equipment / team / node images | synced **folder** | mapped by stable code/slug |
| Mandatory documentation (PDFs) | synced **folder** | → Wagtail Documents |
| News / announcements | simple **GUI** (blog-like) | designated editors; Wagtail page editor or a trimmed editor group |

**Sync mechanism (target):** Office files + asset folders live on **SharePoint**,
synced to the VPS (OneDrive/SharePoint sync client or `rclone`); **Power
Automate** manages the SharePoint side. A periodic management command (cron /
Celery beat) ingests changed files into the DB / Wagtail media. The existing
`populate_redib_*` (TSV) and `populate_*` (marketing) commands are the
**seed of these importers** — they are already idempotent, which is the key
property the sync loop needs.

**What this means for the design now (so we don't repaint later):**
- Keep all editable content in DB / Wagtail fields the Excel can map to.
- Key every asset by a **stable code/slug** (equipment code, person slug, node
  code, page slug) so a synced-folder image resolves deterministically.
- Importers stay **idempotent** and **non-destructive**.
- Pricing should become a **structured model** (so Excel can drive it and
  Equipment can display it) rather than the current HTML-in-RichText table.

## Future tasks (so future sessions align)

1. **Pricing model.** Replace the HTML pricing tables with a structured
   `Price`/`EquipmentRate` model (node × modality × unit × access-type), Excel-
   importable, rendered within Equipment. Retire the RichText tables.
2. **Live calls on the marketing site.** Pull upcoming/open calls from the
   portal onto the homepage + Acceso (read-only teaser) instead of just linking.
3. **Excel importers** for equipment(+prices), team, nodes — evolved from the
   current TSV `populate_redib_*` commands; read `.xlsx`.
4. **Synced-folder ingest** for hero/team/equipment/node images and mandatory
   PDFs, keyed by stable slug/code; idempotent; cron/Celery-driven.
5. **SharePoint ↔ VPS sync** (rclone/OneDrive client + Power Automate) feeding
   #3/#4; document the operational runbook.
6. **News editor GUI** — scope a trimmed Wagtail editor role for designated
   non-technical users (blog-like create/edit of `NewsPage`).
7. **Self-host Inter** (drop the Google Fonts CDN dependency) for perf/offline.
8. **Full bilingual bodies** for the 55 archive news posts; 3 oldest press
   clippings (2014–2016).
9. **Team ↔ users table** decision: keep `Person` snippets, or unify with the
   portal `User` table so one Excel maintains both.

## How to preview while iterating

Dev server runs at `127.0.0.1:8000`. Screenshot helper for visual review:
`python scripts/dev_screenshot.py / /en/ /actualidad/` (needs `pip install
playwright` + `playwright install chromium`; PNGs land in `/tmp/redib-shots/`).
