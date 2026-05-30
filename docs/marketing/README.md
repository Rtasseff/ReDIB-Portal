# Marketing site rebuild — Phase 0 inventory

This folder contains the Phase 0 discovery output for the rebuild of the public ReDIB
website (`redib.net`) inside this Django/Wagtail portal. Phase 0 is a **read-only
inventory** of the live third-party-hosted site. No application code was written.

## Files in this folder

- **[site-inventory.md](./site-inventory.md)** — the full structured inventory: overview,
  bilingual URL pattern, sitemap, per-page detail, ES↔EN pairing audit, and an inventory
  of every interactive feature on the site.
- **[assets-manifest.md](./assets-manifest.md)** — every image, PDF, and downloadable file
  found on the site, with absolute URLs grouped by type. URLs only — no bytes downloaded.

## Headline counts

| Thing | Count |
| --- | --- |
| Top-level navigation pages (per locale) | 28 |
| Bilingual pages confirmed paired 1:1 (static) | 28 |
| Node detail pages | 4 (BioImaC, CNIC, Imaging La Fe, CIC biomaGUNE) |
| Team members listed on `/equipo` | 14 (1 coordinator + 4 committee + 6 advisory + 3 management) |
| News posts in the ES archive (`/noticias`) | ~72, spanning 2015-12-09 → 2026-04-20, 12 per page across 6 paginator pages |
| News posts in the EN archive (`/news`) | ~12 visible on page 1 (March 2025 onward); older posts may be ES-only |
| Press archive items | 27 across 3 pages — page 1 internal, pages 2-3 external clippings |
| Convocatorias listed | ~17 (1 current + ~16 historical) |
| Equipment categories | 4 (Imagen Clínica, Imagen Preclínica, Análisis, Radioquímica) |
| Distinct equipment items pictured | ~25 across all node + category pages |
| Governance PDFs to migrate | 7 (REDIB-01 through REDIB-05 + data-sharing agreement + portal user guide) |
| Newsletter PDFs found in news posts | At least 2 (April 2025, COA portal user guide 2026); more likely on older posts |
| Team headshot images | 14 |
| External institutional partner links to preserve | ~10 (CNIC, CIC biomaGUNE, La Fe, UCM, etc.) |
| External-link cards on `/enlaces-de-interes` | 5 (ICTS map, Twitter, biomaGUNE platform, CNIC Flickr, LinkedIn) |
| Videos / iframes embedded | 0 |
| Contact forms / interactive features | 1 (contact form — destined to be replaced) |
| Broken links found | 1 (footer `/management-area` → 404) |

## Three things the rebuild team should know

1. **The "section landing" pages are smoke and mirrors.** `/equipamiento`, `/es-acceso`,
   `/actualidad`, and their English equivalents render the content of their first child
   instead of having their own page. This is consistent across the site and is probably
   a CMS routing artifact, not an authoring choice. **Decision needed in Phase 1:** do
   we build real Wagtail index pages for these sections (cleaner IA but more authoring
   work) or do we ship them as `RedirectPage` aliases to the first child? Recommend
   building real overview pages for Equipment and Access since they are linked from the
   main nav as parents — and leave Actualidad as a redirect to News.

2. **Convocatorias and the access workflow are already in this portal — do not duplicate
   them in Wagtail.** The `/convocatorias` page on the current site is a hand-maintained
   HTML list that exactly duplicates data we already have in the `Call` model. Similarly,
   `/solicitud-de-acceso` is purely informational with a CTA out to `portal.redib.net`.
   The cleanest Phase 1 architecture is for those Wagtail pages to **read live from the
   portal's database** (same Django project, same ORM) rather than be authored as static
   content. The applicant-facing flow stays on `portal.redib.net/calls/...` and the
   marketing site links to it.

3. **The bilingual coverage is uneven and the contact form is dead.** Static pages are all
   paired 1:1 in ES↔EN, but the news archive likely has a translation gap for pre-2025
   posts — the EN `/news` index is much shorter than ES `/noticias`. The migration team
   should plan for **content-by-content** triage rather than assuming every Spanish post
   has an English counterpart. The contact form is technically working but the brief
   confirms it has no useful backend — rebuild as either a simple Wagtail Form Builder
   form or replace with a "contact us at info@redib.net" page. Also note: the English
   footer link "Team" points to `/management-area`, which is a **dead 404** in the
   current site; the actual EN slug is `/team`.

## Bonus gotchas

- **News pagination has an off-by-one bug** — `/noticias/pag-7` exists in the pager
  but contains no posts (real last page is `pag-6`). Don't copy this behaviour.
- **The "Localización" parent page** (`/localizacion`) doesn't have meaningful unique
  content beyond a four-node grid that duplicates the homepage. Consider eliminating it
  and letting the menu's hover-dropdown go directly to the four `NodePage` URLs.
- **`/inicio` is just an alias for `/`** — make sure the Wagtail URL config supports both.
- **Maps are not actually embedded** anywhere on the site, despite text labels saying
  "Ubicación en Google maps" on each node page. Decision needed: real Google Maps embeds
  (privacy implications, needs cookie consent) or static map images?
- **Pricing table on `/tarifas`** is the most data-dense page — a (node × modality × unit)
  × (AAC / AaD-OPIS / AaD-Other) matrix. Consider whether this should be hand-authored in
  Wagtail StreamField or pulled from a structured model (the portal already has equipment
  and call-type data).
- **Theme is a custom build by Prisma CM** (`prismacm.com`) — the cimagune theme folder
  hints that biomaGUNE may have been the original design partner. No reusable open-source
  templates to copy from; the rebuild starts visual design from scratch (or from a
  Wagtail starter).

## What was NOT crawled (and why)

- Anything behind login at `docs.redib.net` (Área Privada — being decommissioned, out of
  scope per the brief).
- Any CMS admin URLs (none were exposed publicly).
- Asset bytes (URLs only — see `assets-manifest.md`).
- External social/partner links (LinkedIn, Twitter, etc. — they're just outbound).
- A few of the older Spanish-only news posts were enumerated by title and URL only, not
  fully content-extracted. The pre-2025 archive is large (~60 posts) and the value of
  exhaustive per-post extraction is low at the Phase 0 planning stage — pick this up in
  Phase 2 (content migration) instead.
- `sitemap.xml` and `robots.txt` were not fetched. Phase 1 should check whether the live
  site exposes a usable sitemap that could short-circuit later discovery.
