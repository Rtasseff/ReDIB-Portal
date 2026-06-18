# Marketing site rebuild — current status

Working summary of the rebuild of the public redib.net website inside this
Django/Wagtail portal. Lives on branch `feature/marketing-site`. Production
is untouched until cutover.

## Where to pick up (fresh session checklist)

If you're (re)starting a session on this branch and need to orient quickly:

1. **Read this doc top to bottom** — it's the canonical current state.
2. **Skim `git log --oneline main..feature/marketing-site`** — each commit message describes one phase or sub-phase.
3. **Check the open items below in "What's deferred and needs your input"** before suggesting next work. Several items are explicitly waiting on human design decisions; don't decide them in an autonomous session.
4. **The branch is dev-only.** Nothing has been merged or deployed; `main` and prod are untouched. Cutover plan (DNS, Caddy, URL strategy) is a separate conversation.
5. **The regression test in `marketing/tests.py`** asserts no `{# #}` template comment leaks slip into rendered pages — run it after any template edit (`python manage.py test marketing`).
6. **Five idempotent bootstrap commands** populate the entire site from a fresh DB. See "Bootstrap & content commands" below.

This document is the "current state" entry-point. The other files in
`docs/marketing/` are point-in-time artifacts:

- [README.md](README.md) — Phase 0 discovery summary (counts, gotchas)
- [site-inventory.md](site-inventory.md) — Phase 0 page-by-page inventory of
  the live redib.net
- [assets-manifest.md](assets-manifest.md) — Phase 0 asset URL list
- [verification-report.md](verification-report.md) — Phase 4 walk of the
  rebuilt site with HTTP audit, content spot-checks, and an issue list

Two living companion docs: [DESIGN.md](DESIGN.md) (visual language + CSS
maintainability rules) and [../CONTENT_MANAGEMENT.md](../CONTENT_MANAGEMENT.md)
(who edits what, where — the SharePoint-xlsx sync tier vs the CMS-edited
tier, and the live-query bridge between portal and marketing data).

## TL;DR

The marketing site is a faithful recreation of the live redib.net in dev,
intended as a base state to start editing from. All inventory URLs return
the expected HTTP status; bilingual switching works; the COA portal still
works at `/portal/...`.

**2026-06-01 session — base-state push (all autonomous, branch still dev-only):**
- **Real reference data loaded.** Dev DB rebuilt from `data/*.tsv` (4 real
  nodes, 14 equipment with clinical/preclinical/radiochemistry areas, 183
  orgs) + a superuser, so the equipment/node pages live-query real data
  instead of empty sandbox rows. Resolved the two data-load deferrals.
- **Homepage** now matches the live layout (3-slide imaging carousel +
  equipment teaser cards + node grid + 2 recent news).
- **Tarifas** reproduces the full live preclinical (13 rows) + clinical
  (8 rows) rate tables.
- **Governance PDFs** (7) downloaded into Wagtail Documents; /documentacion
  links repointed to local `/documents/` URLs.
- **News archive** completed to the full live breadth (67 ES posts: 12 rich
  page-1 + 55 ES-only historical). **Press** expanded to 24 items.
- **Top nav** collapsed Noticias+Prensa into an "Actualidad" dropdown (8
  items, matching live).
- EN team role labels reviewed: "Member" faithfully translates "Vocal";
  left unchanged (making them more specific would diverge from the ES
  source). 

Remaining human-input items: bilingual URL routing strategy, cutover plan,
admin CMS UX. Smaller follow-ups: full bilingual bodies for the 55 archive
news posts, 3 oldest press clippings (2014-2016), CMS-editable pricing
(structured model), and decimal-separator/translation spot-checks on the
pricing tables.

**2026-06-18 session — public-site UX polish + image-collection plan:**

*Polish committed in `8999b24` (code) on this branch — still dev-only, not
merged or deployed. Files: `static/css/marketing.css`,
`templates/home/home_page.html`, `templates/marketing/news_index_page.html`,
`.../equipment_category_page.html`, `.../node_page.html`,
`.../includes/external_links.html`, + new `.../includes/equipment_card.html`.*

- **Cards that "floated" but weren't clickable → fixed.** Hover-lift is now
  scoped to real links only (`a.mk-card` / `.mk-card--link`). News/Actualidad
  cards (home + `/noticias/`) and Enlaces de interés cards are clickable across
  their whole surface (Bootstrap `.stretched-link`); Enlaces were also unified
  to the `.mk-card` look. Equipment + team cards are static info cards (no link,
  no false lift).
- **Dead-end `…` truncation → fixed.** Equipment descriptions (all 14 are
  200–1200 chars; equipment has no detail page) now expand in place via a no-JS
  `<details>` disclosure ("Ver más" / "Read more"), shared through the new
  `equipment_card.html` include. Clamped to 4 lines when closed. Verified with
  headless Chromium (whole-card click navigates; static cards don't) +
  `manage.py test marketing` + `manage.py check` — all green.
- **Image quality → DEFERRED by owner.** The image *boxes* are correct
  (`object-fit: cover`, exact ratios); bad crops are per-image source +
  focal-point, not code. Owner expects most heroes to be **scientific
  reconstructions** (PET/MRI/CT) — square and small, so they crop badly in the
  wide `fill-1920x760` hero. New image-collection runbook in
  [../CONTENT_MANAGEMENT.md](../CONTENT_MANAGEMENT.md) ("Collecting images").
  Not-yet-built follow-ups: (a) a **letterbox-on-dark hero variant** so square
  scans show whole instead of cropped; (b) add **`pillow-heif`** for iPhone
  HEIC uploads; (c) set per-image **focal points** in `/cms/` — the real fix
  for the "badly cropped hero" complaint.

## URL layout (on this branch)

| URL prefix | What |
|---|---|
| `/` | Wagtail marketing site (Spanish, default locale) |
| `/en/` | Wagtail marketing site (English) |
| `/portal/` | The existing COA portal (calls, applications, evaluations, access, reports, newsletters, dashboard) |
| `/admin/` | Django admin |
| `/cms/` | Wagtail admin |
| `/accounts/` | django-allauth (login, signup, password) |
| `/documents/` | Wagtail document serving |

Production is unchanged (portal still at root under `portal.redib.net`).
This URL layout takes effect at cutover when `feature/marketing-site` merges
to `main` and deploys.

## Architectural decisions (locked)

1. **One repo, one Django project, multiple apps.** Marketing site lives as
   new apps (`home`, `marketing`) alongside the existing portal apps. No
   second repo, no second deployment.
2. **Wagtail at root, portal at `/portal/`.** Wagtail's catchall is mounted
   last so it doesn't shadow portal URLs.
3. **Bilingual via `wagtail-localize`, human-only translation.** No
   machine-translation backend configured. Spanish is the default locale.
4. **`i18n_patterns(prefix_default_language=False)`** — Spanish stays at
   `/`, English gets `/en/` prefix. **Deviation from the original
   "no URL prefixes" intent**; faithfully matching the current redib.net
   per-page-slug-aliases-at-root would require custom URL resolution and is
   deferred. Tradeoff documented in `redib/urls.py`.
5. **Live-query for portal-owned data, not duplicated.** `NodePage` carries
   a `related_core_node` FK; `EquipmentCategoryPage` carries an `area_key`;
   their templates read live from `core.Node` / `core.Equipment` at render.
   No equipment data lives in Wagtail.
6. **Convocatorias and access-applications are out of scope** for the
   marketing site. The portal owns them. Marketing pages that reference
   "current calls" link to `/portal/calls/`.
7. **Distinct marketing chrome** — `templates/marketing_base.html` is its own
   template, not extending the portal's `base.html`. Marketing nav has no
   Login/Register front-and-centre — just a small "Portal" link.

## Page types (Wagtail)

In `home/models.py`:
- `HomePage` — hero (image + heading + subheading) + body

In `marketing/models.py`:
- `StandardPage` — generic content (About, Legal, Enlaces de interés, etc.)
- `AccessIndexPage` — Access overview
- `NewsIndexPage` / `NewsPage`
- `PressIndexPage` / `PressItemPage` (with `external_url` for press clippings)
- `TeamPage`
- `NodeIndexPage` / `NodePage` (`related_core_node` FK)
- `EquipmentIndexPage` / `EquipmentCategoryPage` (`area_key`)
- `PricingPage` (Tarifas — currently a stub)
- `ContactPage` (no form, mailto + address)

Snippets, both with `TranslatableMixin`:
- `Person` (14 instances) — for TeamPage
- `ExternalLink` (10 instances, RESOURCE + INSTITUTIONAL) — for Enlaces de interés

## Bootstrap & content commands (all idempotent)

Run in order on a fresh dev DB. **Load the real portal reference data first**
— the NodePage / EquipmentCategoryPage live-queries return nothing without
real `core.Node` / `core.Equipment` rows (the old sandbox fixture had blank
`Equipment.area` and no Imaging La Fe node, so equipment pages rendered empty):

```bash
source venv/bin/activate
python manage.py migrate

# Real reference data (data/*.tsv) — order matters (FK deps).
python manage.py populate_redib_organizations   # 183 orgs
python manage.py populate_redib_nodes            # 4 real nodes: BioImaC, CIC-biomaGUNE, IIS-LaFe, TRIMA@CNIC
python manage.py populate_redib_users            # 21 users (default pw changeme123)
python manage.py populate_redib_equipment        # 14 equipment, area = clinical/preclinical/radiochemistry
python manage.py populate_redib_funding_agencies # 375 funding agencies
# Superuser for /cms/ + /admin/ (dev): create one if none exists.

# Marketing content
python manage.py marketing_init          # Wagtail Site + ES/EN Locales + HomePage pair
python manage.py populate_static_pages   # 11 ES + 11 EN section pages + ExternalLinks + redirects
python manage.py populate_team           # 14 people, ES + EN + photos
python manage.py populate_equipment_nodes # 4 NodePages + 4 EquipmentCategoryPages, ES + EN
python manage.py populate_news_press     # 12 news + 12 press, sample migration
```

`populate_equipment_nodes` maps each NodePage to its `core.Node` by code
(`core_node_codes` now includes the real codes `BioImaC`, `TRIMA@CNIC`,
`IIS-LaFe`, `CIC-biomaGUNE`) with an org-name fallback.

Verification report noted minor non-idempotency: `populate_static_pages`
re-writes the HomePage hero/body unconditionally; `populate_equipment_nodes`
re-writes the index pages unconditionally. Issues #8/#9 in
`verification-report.md`. Cleanup is a Phase 5 item.

## How to run locally

```bash
git checkout feature/marketing-site
source venv/bin/activate
python manage.py runserver
```

Then visit:

| URL | What |
|---|---|
| `/` | Spanish home |
| `/en/` | English home |
| `/equipo/` | Team page (14 people) |
| `/nodos/bioimac/` | Node detail with live equipment list from `core.Node` |
| `/equipamiento/imagen-clinica/` | Equipment category with live `core.Equipment` query |
| `/noticias/` | News index (67 ES / 12 EN posts, paginated) |
| `/tarifas/` | Pricing page with the full preclinical + clinical rate tables |
| `/documentacion/` | Governance docs served from local Wagtail Documents |
| `/prensa/clip-lavanguardia-la-fe-primera-icts-hospitalaria/` | External press clipping with "Read on outlet" CTA |
| `/portal/calls/` | The existing COA portal (unchanged) |
| `/cms/` | Wagtail admin (dev superuser: `admin@redib.net` / `redibadmin` — change before any real use) |

To verify the bilingual flow: visit any ES page, click the **EN** link in the
top-right language switcher, confirm you land on the matching EN translation.

## What's deferred and needs your input

| Topic | Status | Decision needed |
|---|---|---|
| Bilingual URL routing | `i18n_patterns` with `/en/` prefix | Faithfully match redib.net (per-page-slug aliases at root) would need custom URL resolution. Worth doing? |
| Cutover plan | Not started | DNS, Caddy, `redib.net` vs `portal.redib.net` URL question, third-party handoff. |
| Admin CMS UX for non-technical editors | Not started | You mentioned having specific ideas — separate conversation when you're ready. |
| CMS-editable pricing | Pricing tables are HTML in the RichText body | A structured PricingPage model would let editors maintain rates in the CMS (the rich-text editor strips tables). Build it, or keep editing via the populate command? |

(Homepage layout and the Tarifas pricing matrix — previously in this table —
were resolved in the 2026-06-01 base-state push: both now reproduce the live
content faithfully. See TL;DR.)

## What's deferred but safe to scope later (no design input needed)

- ~~Build the 3 missing inventory pages (`/documentacion/`, `/costes-de-acceso/`,
  `/politica-de-privacidad-y-cookies/`)~~ — **done in Phase 5b**. Mounted at
  root (not under AccessIndex) to match the live URLs that the Acceso body
  anchors target. EN bodies are Claude translations of the ES content
  (no EN version exists on live redib.net) and **need human review** per
  the human-only translation policy — see module-level comments above
  each EN body constant in `populate_static_pages.py`.
- ~~Install `wagtail.contrib.sitemaps` + add `robots.txt`~~ — **done in
  Phase 5b**. `/sitemap.xml` returns Wagtail's sitemap covering both
  locales; `/robots.txt` is a plain template. Both deliberately outside
  `i18n_patterns` so the URLs are canonical.
- ~~Hero images for the 4 equipment category pages~~ — **done in Phase 5b**
  (required adding `hero_image` FK + migration 0002).
- ~~Idempotency cleanups on `populate_static_pages` and
  `populate_equipment_nodes`~~ — **done in Phase 5b**. All five bootstrap
  commands now show zero rewrites on second invocation. Phase 5b also
  fixed a tug-of-war where `populate_static_pages` was overwriting
  NodeIndex/EquipmentIndex chrome owned by `populate_equipment_nodes`.
- ~~EN team role labels currently generic "Member"~~ — **reviewed, left as-is
  (2026-06-01).** "Member" faithfully translates the ES "Vocal"; making EN
  more specific (Committee/Advisory member) would diverge from the ES source
  and the live site, reducing faithfulness.
- ~~News archive beyond 12 posts~~ — **done (2026-06-01).** All 55 historical
  posts from `/noticias` pages 2-6 (2017-2025) added as ES-only `NewsPage`s
  (`ARCHIVE_NEWS` in `populate_news_press.py`) — 67 ES posts total. Each
  carries title/date/teaser + a link to the full article on redib.net; full
  bilingual bodies remain a follow-up.
- ~~Press archive beyond 12 items~~ — **mostly done (2026-06-01).** Added the
  12 page-2 external clippings (`ARCHIVE_PRESS`) → 24 items. The 3 oldest
  page-3 clippings (2014-2016) didn't crawl cleanly — small remaining gap.
- ~~The 7 governance PDFs linked from `/documentacion/` point at live
  `redib.net` URLs~~ — **done (2026-06-01).** `populate_static_pages` now
  downloads them into Wagtail Documents (`get_or_create_document`) and
  repoints the links to local `/documents/` URLs. `--skip-document-download`
  keeps tests offline.
- ~~**Top-nav has 9 items, original had 8.**~~ — **done.** Noticias +
  Prensa now render inside a single "Actualidad" (EN: "News & Press")
  top-nav dropdown, matching the live menu (8 top-level items per locale).
  **Deviation from the suggestion below:** rather than moving NewsIndex +
  PressIndex under a new parent page, the grouping is **presentation-only**
  — `marketing_tags.main_nav` collapses the two index pages into one
  dropdown node and `main_nav.html` renders a Bootstrap dropdown. The pages
  keep their root URLs (`/noticias`, `/prensa`, `/news`, `/press`), so the
  ~30 existing redirects, the sitemap, and in-content links all stay valid.
  Moving them in the tree would have repathed those URLs to
  `/actualidad/noticias` etc. — which neither the live site nor our redirects
  use. Dropdown membership is keyed by page type (`ACTUALIDAD_TYPES`); the
  label is a one-line edit (`ACTUALIDAD_LABELS`). Guarded by
  `MainNavActualidadDropdownTests` in `marketing/tests.py`.

## Post-Phase-5b polish (also done)

- **Navbar declutter** (`f52013e`) — switched `ul.navbar-nav` → `ul.nav`
  so the menu lays out horizontally without a `navbar-expand-lg`
  wrapper; dropped redundant "Inicio" item (logo already links home);
  hid Enlaces de interés + Aviso legal from the main nav and surfaced
  them in a small footer-link row alongside Política de privacidad.
- **Template-leak regression test** (`0bc20db`) — `marketing/tests.py`
  walks 30 URLs and asserts no `{#` / `#}` tokens appear in responses.
  Catches the multi-line `{# #}` comment-leak class that shipped twice.
  Run with `python manage.py test marketing` (~1s).

## Phase 5b additions to the page list

- `/documentacion/` + `/en/documentation/` — links to 7 governance PDFs
- `/costes-de-acceso/` + `/en/access-cost/` — AAC/AaD subsidy explanation
- `/politica-de-privacidad-y-cookies/` + `/en/privacy-policy-and-cookies/`

All three have `show_in_menus=False` so they don't bloat the main nav —
they're reachable via the in-content anchors on the Acceso page (and via
direct URL).

## Branch shape

20 commits on top of `main`. Each commit is one phase or sub-phase:

```
0bc20db Marketing:           regression test for stray template-syntax leaks
6f76f32 Marketing:           wrap multi-line {# #} in {% comment %} (regression)
f52013e Marketing:           declutter top nav (12 vertical → 9 horizontal)
730ef4b Marketing docs:      update REBUILD_STATUS for Phase 5b
0836929 Marketing Phase 5b:  equipment category hero images
047e96e Marketing Phase 5b:  SEO foundation — sitemap.xml + robots.txt
aedbfea Marketing Phase 5b:  build 3 deferred inventory pages + populate_static_pages idempotency
7dc6f72 Marketing docs:      REBUILD_STATUS.md + refresh CLAUDE.md branch note
d4fcb82 Marketing Phase 4.5: cheap P1/P2 fixes from verification report
efa6020 Marketing Phase 4:   verification report
55b83d2 Marketing Phase 3d:  News + Press sample migration (12 / 12)
fb7c15f Marketing Phase 3c:  Equipment + Nodes content with live-query pattern
3587d82 Marketing Phase 3b:  Team page with 14 Person snippets (ES + EN)
c78fd01 Marketing Phase 3a:  site IA, static page content, nav + language switcher
aeb4a83 Marketing Phase 2.5: switch bilingual routing to i18n_patterns
4469a2f Marketing Phase 2:   Wagtail page types + snippets + bootstrap command
b682178 Marketing Phase 1.5: fix remaining portal chrome links to use core:home
a79b49e Marketing Phase 1.5: replace hardcoded URLs with reverse()/{% url %}
7955d54 Marketing Phase 1:   Wagtail + wagtail-localize foundation, portal moves to /portal/
25996e0 Marketing Phase 0:   site inventory of redib.net
```

`main` is untouched — the rebuild has not been merged.

## Test suite status

The portal test suite was running with 17 known failures + 5 errors on
`main` at the start of the rebuild (per Phase 1.5 baseline). Phase 5b
re-baselined: `feature/marketing-site` is 17F + 5E, `main` is 16F + 6E,
the difference is one test (`test_profile_renders`) that converted from
ERROR → FAIL due to the Phase 1.5 URL refactor (different failure mode,
not a new regression). **No new test failures introduced by the
marketing-site rebuild.**

## Phase 5 work (post-merge, in priority order)

1. **Cutover plan** — separate conversation. Covers DNS, Caddy vhost, the
   `redib.net` vs `portal.redib.net` URL question that was deferred.
2. **Homepage layout decision** — biggest visible gap on day one of public
   browsing.
3. **Build the deferred-but-safe items** above.
4. **Tarifas pricing matrix** — biggest content/design task.
5. **Full news + press archive migration** — ~60 historical news + ~15 press.
6. **Admin CMS UX** for non-technical editors — Ryan's specific ideas to come.

## How to roll back if needed

The branch hasn't been merged or deployed. Rolling back is just
`git checkout main` — production hasn't seen any of this work. The local
dev DB has Wagtail tables + content; resetting is `rm db.sqlite3 &&
python manage.py migrate && python manage.py setup_localtest1_database`
then re-running the four populate commands.
