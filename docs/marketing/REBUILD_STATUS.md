# Marketing site rebuild — current status

Working summary of the rebuild of the public redib.net website inside this
Django/Wagtail portal. Lives on branch `feature/marketing-site`. Production
is untouched until cutover.

This document is the "current state" entry-point. The other files in
`docs/marketing/` are point-in-time artifacts:

- [README.md](README.md) — Phase 0 discovery summary (counts, gotchas)
- [site-inventory.md](site-inventory.md) — Phase 0 page-by-page inventory of
  the live redib.net
- [assets-manifest.md](assets-manifest.md) — Phase 0 asset URL list
- [verification-report.md](verification-report.md) — Phase 4 walk of the
  rebuilt site with HTTP audit, content spot-checks, and an issue list

## TL;DR

The marketing site is functionally complete in dev. All 57 URLs from the
inventory return the expected HTTP status; bilingual switching works; the
COA portal still works at `/portal/...`. Verification flagged four P1 issues
of which three (template-comment leak, dead lang-switcher on ES-only pages,
broken in-content links on Acceso) are fixed. The remaining P1 (homepage
layout) and one P1 stub (Tarifas pricing matrix) are intentional deferrals
that need human design input.

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

Run in order on a fresh dev DB:

```bash
source venv/bin/activate
python manage.py migrate
python manage.py marketing_init          # Wagtail Site + ES/EN Locales + HomePage pair
python manage.py populate_static_pages   # 11 ES + 11 EN section pages + ExternalLinks + redirects
python manage.py populate_team           # 14 people, ES + EN + photos
python manage.py populate_equipment_nodes # 4 NodePages + 4 EquipmentCategoryPages, ES + EN
python manage.py populate_news_press     # 12 news + 12 press, sample migration
```

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
| `/noticias/` | News index (12 posts, both locales) |
| `/prensa/clip-lavanguardia-la-fe-primera-icts-hospitalaria/` | External press clipping with "Read on outlet" CTA |
| `/portal/calls/` | The existing COA portal (unchanged) |
| `/cms/` | Wagtail admin (log in with the project's superuser) |

To verify the bilingual flow: visit any ES page, click the **EN** link in the
top-right language switcher, confirm you land on the matching EN translation.

## What's deferred and needs your input

| Topic | Status | Decision needed |
|---|---|---|
| Homepage layout | Text-only hero | Inventory described a carousel + 6 teaser cards + 4-node grid + 2-news teaser. Build it or ship minimalist? |
| Tarifas pricing matrix | Stub body | Structured model vs StreamField? Pricing is `(node × modality × unit) × (AAC / AaD-OPIS / AaD-Other)`. |
| Bilingual URL routing | `i18n_patterns` with `/en/` prefix | Faithfully match redib.net (per-page-slug aliases at root) would need custom URL resolution. Worth doing? |
| Imaging La Fe `core.Node` row | Missing in dev fixture | Load real data or extend fixture before merge. |
| `Equipment.area` blank in dev fixture | Category-page lists empty | Same as above — data load. |
| Cutover plan | Not started | DNS, Caddy, `redib.net` vs `portal.redib.net` URL question, third-party handoff. |
| Admin CMS UX for non-technical editors | Not started | You mentioned having specific ideas — separate conversation when you're ready. |

## What's deferred but safe to scope later (no design input needed)

- Build the 3 missing inventory pages (`/documentacion/`, `/costes-de-acceso/`,
  `/politica-de-privacidad-y-cookies/`) with content from the live site.
- Install `wagtail.contrib.sitemaps` + add `robots.txt`.
- Hero images for the 4 equipment category pages.
- Idempotency cleanups on `populate_static_pages` and `populate_equipment_nodes`.
- EN team role labels currently generic "Member" — could be more specific.
- News archive beyond 12 posts (~60 more historical posts; pre-2025 are
  likely ES-only).
- Press archive beyond 12 items.

## Branch shape

13 commits on top of `main`. Each commit is one phase or sub-phase:

```
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
`main` at the start of the rebuild (per Phase 1.5 baseline). Phase 1.5
verified no NEW failures were introduced by the URL refactor.
Re-baselining after Phases 2–4 work is a Phase 5 item.

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
