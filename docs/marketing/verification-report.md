# Marketing site — Phase 4 verification report

Verification of the rebuilt marketing site against the Phase 0 inventory
(`docs/marketing/site-inventory.md`). Conducted on the `feature/marketing-site`
branch at HEAD `55b83d2` (after Phase 3d). Local dev server (`runserver 8000`,
SQLite). All findings are observational — no code was changed.

## 1. Summary

The rebuild is in solid shape. Of **57 URLs audited** (51 marketing pages
across both locales + 4 cross-system + 2 redirects), **57 returned the expected
status** (51× 200, 4× 302/200, 2× 301). Title, nav chrome, and language
switcher render on every Wagtail-served page. All 14 team members are visible
with photos and proper group headers in both locales. All four node pages
render with hero images and addresses; three of four show live equipment lists
from `core.Node`, the fourth (Imaging La Fe) shows the graceful "Lista de
equipamiento próximamente" fallback. The two equipment categories that map to
a `core.Equipment.area` (clinical, preclinical, radiochemistry) render the
"Aún no hay equipamiento" empty-state because the dev fixture has blank
`area` — exactly as Phase 3c documented. Bilingual switching works between
every translated page pair. The `/actualidad → /noticias/` and
`/present → /en/news/` redirects both return 301.

**The headline gap:** six pages from the inventory are missing entirely —
`/documentacion/`, `/costes-de-acceso/`, `/solicitud-de-acceso/`,
`/convocatorias/`, `/calendario-de-convocatorias/`, and
`/politica-de-privacidad-y-cookies/` (and all six EN siblings). Two of those
missing pages (`/documentacion/`, `/costes-de-acceso/`) are linked from the
**Acceso index body copy that DOES ship**, producing two broken in-content
links on a high-priority page. The Tarifas pricing matrix is also a stub.

Issue counts: **0 P0 (no server errors, no broken pages)**, **4 P1 (homepage
is text-only and lacks the inventory-described carousel/grids; press items have
no language switcher fallback; missing Acceso sub-pages cause broken internal
links from /es-acceso/; Tarifas is a stub)**, **5 P2 (leaking multi-line
template comments visible on every page; no favicon/robots/sitemap; equipment
category pages have no hero image; populate_static_pages is mildly
non-idempotent on homepage and equipment/node index nodes)**, **1 P3
(populate_equipment_nodes always rewrites NodeIndexPage / EquipmentIndexPage
body)**.

## 2. Sitemap audit table

51 marketing pages + 4 cross-system + 2 redirects = 57 URLs. Nav column shows
the count of `class="nav-link"` items rendered (12 expected). Switcher column
shows the target URL of the opposite-locale link rendered in the
`Idioma / Language` switcher.

| URL | Status | Title | Nav | Switcher | Notes |
| --- | --- | --- | --- | --- | --- |
| `/` | 200 | Inicio — ReDIB | Y(12) | →/en/ | OK |
| `/quienes-somos/` | 200 | Quiénes somos — ReDIB | Y(12) | →/en/about-us/ | OK |
| `/es-acceso/` | 200 | Acceso — ReDIB | Y(12) | →/en/en-access/ | body links to /documentacion/ and /costes-de-acceso/ → both 404 |
| `/equipamiento/` | 200 | Equipamiento — ReDIB | Y(12) | →/en/equipment/ | OK (index/landing) |
| `/equipamiento/imagen-clinica/` | 200 | Imagen Clínica — ReDIB | Y(12) | →…/clinical-imaging/ | empty-state "Aún no hay equipamiento" renders (fixture area=blank) |
| `/equipamiento/imagen-preclinica/` | 200 | Imagen Preclínica — ReDIB | Y(12) | →…/preclinical-imaging/ | empty-state |
| `/equipamiento/analisis-de-imagen-clinica-y-preclinica/` | 200 | Análisis de Imagen — ReDIB | Y(12) | →…/clinical-and-preclinical-image-analytics/ | no live-equipment query (area_key='') — renders intro/body cleanly |
| `/equipamiento/radioquimica/` | 200 | Radioquímica — ReDIB | Y(12) | →…/radiochemistry/ | empty-state |
| `/equipo/` | 200 | Equipo — ReDIB | Y(12) | →/en/team/ | 14 photos, 4 H2 group headers, all names present |
| `/nodos/` | 200 | Nodos — ReDIB | Y(12) | →/en/nodes/ | OK |
| `/nodos/bioimac/` | 200 | BioImaC — ReDIB | Y(12) | →…/bioimac/ | hero + 2 equipment items from core.Node id=6 |
| `/nodos/cnic/` | 200 | TRIMA @ CNIC — ReDIB | Y(12) | →…/cnic/ | hero + equipment from core.Node id=7 |
| `/nodos/imaging-la-fe/` | 200 | Imaging La Fe — ReDIB | Y(12) | →…/imaging-la-fe/ | "Lista de equipamiento próximamente" fallback (no core.Node) — intentional |
| `/nodos/cic-biomagune/` | 200 | CIC biomaGUNE — ReDIB | Y(12) | →…/cic-biomagune/ | hero + equipment from core.Node id=5 |
| `/noticias/` | 200 | Noticias — ReDIB | Y(12) | →/en/news/ | 12 cards, no pagination shown (12 ≤ page size) |
| `/noticias/?page=2` | 200 | Noticias — ReDIB | Y(12) | →/en/news/ | identical content to page 1 — graceful out-of-range |
| `/noticias/la-primera-convocatoria…/` | 200 | La Primera Convocatoria de 2026… | Y(12) | →…/the-first-2026-call…/ | hero + body, back-link to /noticias/ |
| `/noticias/portafolio-de-servicios-de-imagen-biomedica/` | 200 | Portafolio de servicios… | Y(12) | →…/portfolio-of-biomedical-imaging-services/ | body text references "sección de Documentación" which does not exist |
| `/noticias/boletin-informativo-mes-de-abril-2025/` | 200 | Boletín informativo: abril 2025 | Y(12) | →…/april-newsletter-2025/ | OK |
| `/prensa/` | 200 | Prensa — ReDIB | Y(12) | →/en/press/ | list-group of 12 items, no pagination (12 ≤ page size) |
| `/prensa/dia-mundial-del-corazon/` | 200 | Día Mundial del Corazón | Y(12) | **N** | ES-only — switcher shows "ES" only, no EN link → user is trapped on ES |
| `/prensa/clip-lavanguardia-la-fe-primera-icts-hospitalaria/` | 200 | El Hospital La Fe… | Y(12) | **N** | external CTA "Leer en La Vanguardia" with target=_blank rendered correctly |
| `/prensa/clip-iislafe-imaging-la-fe-icts-hospitalaria/` | 200 | La Fe se convierte… | Y(12) | **N** | external CTA renders |
| `/tarifas/` | 200 | Tarifas — ReDIB | Y(12) | →/en/rates/ | **stub** — text only, no pricing matrix; body explicitly says "tabla detallada se publicará en una fase posterior" |
| `/contacto/` | 200 | Contacto — ReDIB | Y(12) | →/en/contact/ | mailto + phone + postal + node websites; no form |
| `/enlaces-de-interes/` | 200 | Enlaces de interés — ReDIB | Y(12) | →/en/links-of-interest/ | 2 sections (Recursos, Socios institucionales) with external link cards |
| `/aviso-legal/` | 200 | Aviso legal — ReDIB | Y(12) | →/en/legal-notice/ | OK |
| `/en/` | 200 | Home — ReDIB | Y(12) | →/ | text-only hero (no image) |
| `/en/about-us/` | 200 | About us — ReDIB | Y(12) | →/quienes-somos/ | distinct EN translation confirmed |
| `/en/en-access/` | 200 | Access — ReDIB | Y(12) | →/es-acceso/ | body links to /documentation/ and /access-cost/ → both 404 |
| `/en/equipment/` | 200 | Equipment — ReDIB | Y(12) | →/equipamiento/ | OK |
| `/en/equipment/clinical-imaging/` | 200 | Clinical Imaging — ReDIB | Y(12) | →…/imagen-clinica/ | empty-state |
| `/en/equipment/preclinical-imaging/` | 200 | Preclinical Imaging — ReDIB | Y(12) | →…/imagen-preclinica/ | empty-state |
| `/en/equipment/clinical-and-preclinical-image-analytics/` | 200 | Image Analytics — ReDIB | Y(12) | →…/analisis-de-imagen-clinica-y-preclinica/ | clean body, no equipment query |
| `/en/equipment/radiochemistry/` | 200 | Radiochemistry — ReDIB | Y(12) | →…/radioquimica/ | empty-state |
| `/en/team/` | 200 | Team — ReDIB | Y(12) | →/equipo/ | 14 photos, 4 H2 group headers, English labels |
| `/en/nodes/` | 200 | Nodes — ReDIB | Y(12) | →/nodos/ | OK |
| `/en/nodes/bioimac/` | 200 | BioImaC — ReDIB | Y(12) | →…/bioimac/ | equipment via core.Node id=6 |
| `/en/nodes/cnic/` | 200 | TRIMA @ CNIC — ReDIB | Y(12) | →…/cnic/ | equipment via core.Node id=7 |
| `/en/nodes/imaging-la-fe/` | 200 | Imaging La Fe — ReDIB | Y(12) | →…/imaging-la-fe/ | fallback message |
| `/en/nodes/cic-biomagune/` | 200 | CIC biomaGUNE — ReDIB | Y(12) | →…/cic-biomagune/ | equipment via core.Node id=5 |
| `/en/news/` | 200 | News — ReDIB | Y(12) | →/noticias/ | 12 cards, no pagination |
| `/en/news/?page=2` | 200 | News — ReDIB | Y(12) | →/noticias/ | identical to page 1 — graceful |
| `/en/news/the-first-2026-call-for-competitive-open-access/` | 200 | The First 2026 Call… | Y(12) | →…/la-primera-convocatoria…/ | OK |
| `/en/news/portfolio-of-biomedical-imaging-services/` | 200 | Portfolio of biomedical imaging services | Y(12) | →…/portafolio-…/ | OK |
| `/en/news/april-newsletter-2025/` | 200 | April Newsletter 2025 | Y(12) | →…/boletin-informativo-mes-de-abril-2025/ | OK |
| `/en/press/` | 200 | Press — ReDIB | Y(12) | →/prensa/ | "No press items yet" — empty (press is ES-only) |
| `/en/rates/` | 200 | Rates — ReDIB | Y(12) | →/tarifas/ | stub (EN translation of /tarifas/) |
| `/en/contact/` | 200 | Contact — ReDIB | Y(12) | →/contacto/ | mailto + phone + postal + node websites |
| `/en/links-of-interest/` | 200 | Links of interest — ReDIB | Y(12) | →/enlaces-de-interes/ | OK |
| `/en/legal-notice/` | 200 | Legal notice — ReDIB | Y(12) | →/aviso-legal/ | OK |
| `/portal/calls/` | 200 | Open Calls — ReDIB COA Portal | — | — | portal still reachable at `/portal/*` |
| `/cms/` | 302 | — | — | — | redirects to login as expected |
| `/admin/` | 302 | — | — | — | redirects to login as expected |
| `/accounts/login/` | 200 | Sign In — ReDIB Portal | — | — | OK |
| `/actualidad` | 301 | — | — | — | `Location: /noticias/` |
| `/present` | 301 | — | — | — | `Location: /en/news/` |

Summary: 51 marketing URLs audited; **51 returned 200**; title plausibly
matches inventory expectation on all 51; nav (12 items) renders on all 51;
language switcher offers an opposite-locale link on **48 of 51** (the 3
exceptions are the 3 ES-only press items audited — see issue #2).

## 3. Content spot-checks

### Homepage (ES + EN)

- Title matches inventory: "Inicio" / "Home" — OK.
- Hero present: a `<section class="marketing-hero">` with H1
  ("Red Distribuida de Imagen Biomédica" / "Distributed Biomedical Imaging
  Network") and lead text — but **no hero image** (the template supports
  `page.hero_image` but it is null on both locales). No carousel, no node
  teaser grid, no recent-news teaser. The inventory described a 6-card +
  4-node grid + 2-news teaser layout; the rebuild has none of it.
- Bilingual content distinct: ES "Servicios competitivos de acceso abierto en
  imagen molecular y funcional…" vs EN "Distributed Biomedical Imaging Network
  (ReDIB)… competitive open-access services…" — confirmed translation.

### Quiénes somos / About us

- Title matches. ES H1 "Quiénes somos", EN H1 "About us".
- No hero image (template supports it; field is null).
- Body has 4 H3 subsections in both locales; content is distinct between
  locales (real translation, not a copy).
- No broken links inside body.

### Acceso index (/es-acceso/ + /en/en-access/)

- Title matches. ES H1 "Acceso", EN H1 "Access".
- Body has real long-form content (AAC / AaD explanation in both locales).
- CTA button "Convocatorias activas" → `/portal/calls/` works.
- **In-body links to `/documentacion/` and `/costes-de-acceso/` both 404.**
  Same for EN: `/documentation/` and `/access-cost/` 404. See issue #3.

### Equipo / Team

- 14 photos, all rendering (no broken `<img src>`). Filenames include hashed
  Wagtail rendition tokens (`*.fill-200x200.jpg`).
- 4 H2 group headers in both locales — Coordinación / Coordination; Comité de
  Coordinación / Coordination Committee; Comité Asesor Científico-Técnico /
  Scientific-Technical Advisory Committee; Área de Gestión / Management.
- All 14 names confirmed: Jesús Ruiz-Cabello Osuna, José Luis Izquierdo,
  Borja Ibáñez Cabeza, Gonzalo Pizarro Sánchez, Luis Martí-Bonmatí, Noam
  Shemesh, Irene Marco Rius, Juan José Vaquero, Eduardo Fraile Moreno, Lluis
  Donoso Bach, Jeff Bulte, Ryan Tasseff, Cristina Álvarez de Lara Sánchez, Ana
  Penadés Blasco.
- Role captions: ES uses "Coordinador" / "Member" / "Member" / "Management" /
  "ReDIB Manager". EN uses identical "Member" everywhere for committee and
  advisory — that's a translation depth question, not a bug.

### Node — BioImaC (/nodos/bioimac/)

- Hero image renders (`bioimac-hero…fill-1200x400.jpg`).
- "Ubicación" card shows the inventory address (Paseo de Juan XXIII, nº 1,
  28040 Madrid).
- "Contacto" card shows phone + cai.ucm.es web link.
- "Equipamiento disponible" H2 renders 2 equipment cards pulled live from
  `core.Node id=6` (MRI 7T Scanner, Optical Imaging System) — note these are
  the dev fixture names, not the inventory's "PET-RM 9.4T Bruker BioSpec" etc.
  That's expected since the dev fixture is minimal.

### Node — Imaging La Fe (/nodos/imaging-la-fe/)

- Hero image renders.
- Equipment section shows "Lista de equipamiento próximamente." fallback —
  exactly the intended Phase 3c graceful handling for nodes without a
  `core.Node` row.

### Equipment category — Imagen Clínica (/equipamiento/imagen-clinica/)

- H1 "Imagen Clínica", lead/body present.
- Live-equipment query falls through to "Aún no hay equipamiento registrado en
  esta categoría." — empty-state shows because dev `core.Equipment.area` is
  blank. No crash.
- No hero image (template supports it; field is null).

### Equipment category — Análisis de Imagen (`area_key=''`)

- H1 + body render, no equipment query attempted, no empty-state message — the
  page reads as a static description, which is acceptable for the Analytics
  category since it doesn't map to a single `core.Equipment.area` value.

### Tarifas (/tarifas/)

- H1 "Tarifas" + H2 "Mecanismos de acceso" + AAC/AaD paragraphs.
- Body says explicitly: "La tabla de precios detallada (nodo × modalidad ×
  unidad de servicio) se publicará en una fase posterior." — stub, see issue
  #4.

### Contacto / Contact

- Both locales render full content: mailto:info@redib.net link, phone, postal
  address, "Sitios web de los nodos" / "Node websites" section. No form. This
  matches the Phase 0 decision to replace the dying CMS form with a mailto
  link.

### News article — Portafolio de servicios de imagen biomédica

- Hero image renders, date "28 mayo 2025", H1, lead, body.
- "Volver a noticias" back link works.
- Body text says "El documento completo está disponible en la sección de
  Documentación." — but there IS no Documentación page in the rebuild. This is
  a dead in-content reference but not a broken link (no `<a href>`).

### Press item — internal (Día Mundial del Corazón)

- Date "21 enero 2025 · ReDIB" rendered correctly.
- H1 + lead + body present, no external CTA (correct for an internal item).
- Back link works.
- **Switcher shows only "ES" with no link to EN site** — see issue #2.

### Press item — external (clip-lavanguardia-la-fe-primera-icts-hospitalaria)

- "Leer en La Vanguardia" CTA renders as `btn btn-primary` with
  `target="_blank" rel="noopener"` pointing at the lavanguardia.com URL — OK.
- Same caveat about no EN switcher.

## 4. Functional checks

### Language switcher

Tested by parsing the rendered `aria-label="Idioma / Language"` span and
extracting the opposite-locale link target.

- `/` → switcher offers `/en/` — OK
- `/quienes-somos/` → `/en/about-us/` — OK (translated slug)
- `/es-acceso/` → `/en/en-access/` — OK
- `/equipo/` → `/en/team/` — OK
- `/equipamiento/imagen-clinica/` → `/en/equipment/clinical-imaging/` — OK
- `/nodos/bioimac/` → `/en/nodes/bioimac/` — OK
- `/noticias/la-primera-convocatoria…/` →
  `/en/news/the-first-2026-call…/` — OK
- `/en/` → `/` — OK
- `/en/team/` → `/equipo/` — OK
- `/prensa/dia-mundial-del-corazon/` — **no opposite-locale link rendered**
  (only `<strong>ES</strong>` shown). All 3 spot-checked press items behave
  the same. This is because press items have no `wagtail-localize`
  translation and the switcher template renders nothing for the missing
  locale. See issue #2.

### Nav menu consistency

Every page renders 12 nav-link items in the same order in each locale:
Inicio / Quiénes somos / Acceso / Equipamiento / Equipo / Nodos / Noticias /
Prensa / Tarifas / Contacto / Enlaces de interés / Aviso legal (and the EN
mirror with translated labels). Confirmed by spot-checking 4 pages in each
locale. Header markup, footer markup, and the "Portal" CTA button are
identical across pages.

### Pagination (/noticias/, /en/news/)

- 12 NewsPages migrated (per `populate_news_press` summary). Page size 12.
- `/noticias/?page=1` and `/noticias/?page=2` both return 200; bodies are
  byte-different (Wagtail caches/templates inject the request, hence
  different HTML) but the 12 news URLs listed are identical — confirms the
  graceful out-of-range behaviour that Phase 3d already documented.
- The template's `{% if news_posts.has_other_pages %}` correctly hides the
  pager when there's only one page.

### External press clipping CTA

- `/prensa/clip-lavanguardia-la-fe-primera-icts-hospitalaria/` renders a
  primary button labeled "Leer en La Vanguardia" with
  `href="https://www.lavanguardia.com/local/valencia/20181113/…"`,
  `target="_blank"`, `rel="noopener"`. OK.
- Internal press item (`/prensa/dia-mundial-del-corazon/`) has no external
  CTA — also OK.

### Redirects

- `curl -I http://localhost:8000/actualidad` → `HTTP/1.1 301 Moved Permanently`,
  `Location: /noticias/` — OK.
- `curl -I http://localhost:8000/present` → `HTTP/1.1 301 Moved Permanently`,
  `Location: /en/news/` — OK.

### CMS / admin reachability

- `curl -I /cms/` → 302 (redirects to login). OK.
- `curl -I /admin/` → 302. OK.
- `/accounts/login/` → 200, page title "Sign In - ReDIB Portal". OK.

### Portal still reachable

- `/portal/calls/` → 200, H1 "Open Calls for Access". The Phase 1 move of the
  COA portal to `/portal/*` continues to work and is correctly linked from
  `/es-acceso/` and `/en/en-access/`.

### Bootstrap idempotency

- `python manage.py marketing_init` — clean idempotent.
- `python manage.py populate_team` — clean idempotent.
- `python manage.py populate_news_press` — clean idempotent (re-uses by
  translation_key + slug).
- `python manage.py populate_static_pages` — **mildly non-idempotent on first
  run after a fresh `populate_equipment_nodes` run**: equipamiento + nodos
  page bodies are "Updated" once and then stable. Also re-runs "Homepage
  hero/body refreshed (ES + EN)." unconditionally on every call. See issue
  #8.
- `python manage.py populate_equipment_nodes` — **always reports "Refreshed
  NodeIndexPage" and "Refreshed EquipmentIndexPage"** even when content is
  unchanged. See issue #9.

## 5. Inventory delta (what wasn't built)

Comparing against `docs/marketing/site-inventory.md` § Sitemap.

### Missing pages — `[GAP]` (deferred but linked from existing pages, so they break things)

- **`/documentacion/` + `/en/documentation/`** — `[GAP]`. Inventory says
  this is a `DocumentLibraryPage` listing 7 governance PDFs. **Linked from the
  body of `/es-acceso/` and `/en/en-access/`** ("Consulte también la
  documentación reguladora") → broken links on the high-priority Acceso page.
- **`/costes-de-acceso/` + `/en/access-cost/`** — `[GAP]`. Inventory says
  `StandardPage` with AAC/AaD subsidy explanation. **Linked from the body of
  `/es-acceso/` and `/en/en-access/`** → broken links.
- **`/solicitud-de-acceso/` + `/en/access-request/`** — `[GAP]`. Inventory
  says `StandardPage` explaining the access mechanisms; the live site had
  this as a long-form companion to /es-acceso/. Currently the rebuild ships
  only the Acceso index. Not currently linked from any built page (so not
  "broken" — just missing).
- **`/convocatorias/` + `/en/calls/`** — `[INTENTIONAL]` per Phase 0
  recommendation. Convocatorias data lives in the portal `Call` model and is
  reachable at `/portal/calls/`. The Wagtail `/convocatorias/` Wagtail page
  was deferred. Not currently linked from any built marketing page.
- **`/calendario-de-convocatorias/` + `/en/calendar-of-calls/`** — `[GAP]`.
  Inventory says `StandardPage` explaining submission windows. Not built and
  not linked. Low-volume page, but it was a top-level nav item on the live
  site.

### Missing pages — `[INTENTIONAL]` (per Phase 0 plan)

- **`/politica-de-privacidad-y-cookies/` + `/en/privacy-policy-and-cookies/`** —
  `[INTENTIONAL]` per Phase 0 note that legal/cookies content is deferred.
  Not built and not linked.
- **News archive content beyond 12 posts** — `[INTENTIONAL]`. Live site had
  ~72 ES news posts (2015–2026). Phase 3d migrated only the 12 most-recent;
  pagination renders the single page cleanly. Inventory expected
  `/noticias/pag-2` through `/noticias/pag-6`; rebuild uses `?page=N` and
  has only 1 page.
- **Press archive content beyond 12 items** — `[INTENTIONAL]`. Live site had
  27 press items across 3 pages. Phase 3d migrated 12. Identical structure
  to news.
- **Tarifas detailed pricing matrix** — `[INTENTIONAL]`. Body text on
  `/tarifas/` explicitly defers the pricing matrix to a later phase.
- **Hero carousel + node/news/equipment teaser grids on the homepage** —
  status unclear. The inventory described a hero carousel, 6 teaser cards
  (3 imaging-type, 1 equipment, 1 news, 1 generic) and a 4-node grid. The
  current homepage has only a hero section + a single paragraph of body
  text. Whether this was deferred to Phase 5 polish or simply missed is the
  most consequential decision for the human reviewer. Flagged as P1 issue
  #1.

### Missing pages — `[BLOCKED]`

- None observed. The only structural dependency that did NOT resolve at run
  time is the Imaging La Fe `core.Node` FK (the populate command shows
  `related_core_node = NULL`). This is correctly handled by the fallback
  template message, so it isn't blocked — it's an explicit design choice.

### Missing features

- **Sitemap.xml / robots.txt** — neither present. Phase 0 § Feature inventory
  mentioned `wagtail-sitemap` as "add in rebuild". `[GAP]` for SEO if the
  site is deployed publicly without these. P2.
- **Favicon** — `/favicon.ico` returns 404. P3.
- **Cookie consent banner** — not implemented. Phase 0 noted "Reuse with new
  consent solution". `[INTENTIONAL]` (deferred per Phase 0).
- **Wagtail search** — not implemented. Phase 0 noted "optional". `[INTENTIONAL]`.
- **RSS feed** — not implemented. `[INTENTIONAL]` per Phase 0.

## 6. Issues found

### Issue 1 — Homepage is text-only; lacks the carousel/grids the inventory described

- **Severity:** P1
- **URL:** `/` and `/en/`
- **Detail:** The live site homepage had a hero carousel (3 slides), 6 teaser
  cards (Imagen Clínica / Preclínica / Radioquímica / Equipamiento /
  Actualidad / Nodos), a 2-card recent-news teaser, and a 4-node grid. The
  rebuilt homepage has a hero section with H1 + subheading + a one-paragraph
  body and **nothing else**. No hero image is set on the page either (template
  supports `page.hero_image` but field is null).
- **Suggested fix:** Either (a) extend `templates/home/home_page.html` to
  query and render the four NodePages + the 2 most-recent NewsPages + the
  EquipmentCategoryPage children of the EquipmentIndex (similar to
  enlaces-de-interes's `external_links_for` pattern), and have
  `populate_static_pages` set `hero_image` on the HomePage, OR (b)
  consciously decide the homepage is intentionally minimalist and document
  that decision. Whoever scopes Phase 4.5 should pick (a) or (b).

### Issue 2 — Press items have no language switcher link to the EN site (and vice versa)

- **Severity:** P1
- **URL:** `/prensa/dia-mundial-del-corazon/` and all 11 other PressItemPages
  (all are ES-only).
- **Detail:** PressItemPages were migrated only in ES (`populate_news_press`
  output: "Press: 12 items — 6 internal, 6 external; 0 paired ES+EN"). The
  `Idioma / Language` switcher in `marketing_base.html` only renders a link
  for the opposite locale when a translation exists. On a press item there is
  no EN translation, so the switcher displays only `<strong>ES</strong>` with
  no clickable element — a user landing on a press item URL has no way to
  navigate to the EN site short of editing the URL. The same would presumably
  happen if a user landed on an EN-only page from the ES site.
- **Suggested fix:** When the opposite-locale translation doesn't exist, the
  switcher should fall back to the opposite-locale Press index
  (`/en/press/`) or the opposite-locale homepage, not render nothing. One-line
  fix in the marketing_base header partial.

### Issue 3 — Acceso page body has 2 broken in-content links to /documentacion/ and /costes-de-acceso/

- **Severity:** P1
- **URL:** `/es-acceso/` (body links) and `/en/en-access/` (same problem with
  `/documentation/` + `/access-cost/`).
- **Detail:** The Acceso index body, authored in `populate_static_pages`,
  contains hard-coded anchors:
  `<a href="/documentacion/">documentación reguladora</a>` and
  `<a href="/costes-de-acceso/">detalle de los costes asociados</a>`. Both
  destinations return 404 because those pages were never created. This is
  particularly bad because Acceso is one of the highest-intent landing pages
  on the marketing site.
- **Suggested fix:** Either build the two missing pages
  (`/documentacion/`, `/costes-de-acceso/`) as `StandardPage` children of the
  AccessIndex, or remove the anchors from the Acceso body in
  `populate_static_pages`. (The first is the inventory-aligned answer; the
  second is the quick fix.)

### Issue 4 — Tarifas is a stub

- **Severity:** P1 (it's a top-nav page that says "we'll publish this later")
- **URL:** `/tarifas/` and `/en/rates/`
- **Detail:** Body explicitly says "La tabla de precios detallada (nodo ×
  modalidad × unidad de servicio) se publicará en una fase posterior."
  Inventory § Tarifas describes the most data-dense page on the live site
  (full pricing matrix + radiotracer table). Currently the rebuild ships
  none of it. Marking P1 because Tarifas is a top-level nav item — a visitor
  who clicks it gets a page that essentially says "come back later".
- **Suggested fix:** Either author the pricing matrix as a StreamField table
  block (or pull from a structured model), or remove "Tarifas" from the nav
  until the table is ready. Phase 0 noted this could be a new `PricingPage`
  type with structured blocks.

### Issue 5 — Multi-line `{# … #}` template comments leak into every rendered page

- **Severity:** P2
- **URL:** every marketing page (e.g. `/`, `/equipo/`, `/enlaces-de-interes/`)
- **Detail:** Django's `{# … #}` comment syntax is single-line only. Two
  multi-line `{# … #}` comments — one in
  `templates/marketing_base.html` (the `=====` separator block at lines
  21–26) and one in `templates/marketing/standard_page.html` (the "Special
  case: /enlaces-de-interes" comment at lines 15–17) — render as literal
  text in the response body because the parser doesn't strip them. They
  are visually invisible in a browser (they appear inside whitespace before
  HTML elements) but they are sent in every response. Easy to verify with
  `curl http://localhost:8000/ | grep "{#"`.
- **Suggested fix:** Wrap multi-line comments in `{% comment %} … {% endcomment %}`
  blocks. Two-line edit across two template files.

### Issue 6 — No sitemap.xml or robots.txt

- **Severity:** P2 (for any public deploy)
- **URL:** `/sitemap.xml` → 404, `/robots.txt` → 404
- **Detail:** Phase 0 § Feature inventory explicitly flagged this as
  "Add `wagtail-sitemap`". For a public marketing site, missing sitemap +
  robots is an SEO regression vs the live site.
- **Suggested fix:** Install `wagtail.contrib.sitemaps` and wire it into
  `urls.py`. ~10-line change. (`robots.txt` can be a simple static view or
  whitenoise-served file.)

### Issue 7 — Equipment category pages have no hero image

- **Severity:** P2
- **URL:** all 4 EquipmentCategoryPages in both locales
- **Detail:** Inventory says each category page on the live site had 1 hero
  image plus 5–14 equipment photos. The rebuilt category pages have no hero
  image (the EquipmentCategoryPage model supports `hero_image` but the field
  is null on all 8 pages) and the equipment listing falls through to the
  empty-state message in dev. The category pages look very plain.
- **Suggested fix:** Add hero image assignment to `populate_equipment_nodes`
  for the 4 ES + 4 EN category pages (8 image references). Pulls from
  `media/marketing/...` per the assets manifest.

### Issue 8 — `populate_static_pages` rewrites HomePage hero/body on every run

- **Severity:** P2
- **URL:** N/A — bootstrap command
- **Detail:** Output line "Homepage hero/body refreshed (ES + EN)." prints on
  every invocation regardless of whether the homepage content is current. The
  rest of the command is correctly idempotent (uses content equality checks).
  This means re-running `populate_static_pages` will undo any manual Wagtail
  edits to the homepage hero/body. Convention noted in CLAUDE.md is that
  TSV loaders should be idempotent; this is a soft violation for the
  hardcoded HomePage block.
- **Suggested fix:** Add the same "compare-and-skip" check used for the
  StandardPage block, or document explicitly that the HomePage block is
  always-rewritten by design.

### Issue 9 — `populate_equipment_nodes` always rewrites NodeIndexPage and EquipmentIndexPage

- **Severity:** P3
- **URL:** N/A — bootstrap command
- **Detail:** Output lines "Refreshed NodeIndexPage (es) id=13" and
  "Refreshed EquipmentIndexPage (es) id=9" print on every run. Same
  non-idempotency concern as issue #8 but lower stakes since these index
  pages have minimal content.
- **Suggested fix:** Same as #8 — add equality check before write.

### Issue 10 — Coordinator role label in EN is generic "Member" for committee/advisory members

- **Severity:** P3
- **URL:** `/en/team/`
- **Detail:** The English team page shows "Member" as the role caption for
  every committee + advisory member, where the ES page shows the same
  generic Spanish role labels translated from "Member". This is consistent
  but possibly less informative than the live site's role lines (which were
  per-person affiliations like "TRIMA-CNIC rep"). Not a bug, but a content
  quality observation worth flagging for the team data review.

## 7. Recommendation

**Fix-then-ship.** The site is functionally complete (no 500s, no 404s on
audited URLs, bilingual switching works, redirects work, all chrome renders).
But two of the four P1 issues will be visible to any real visitor on
day-1: the broken in-content links on `/es-acceso/` (issue #3) and the
text-only homepage (issue #1). The leaking template comments (issue #5) are
embarrassing once anyone views source. These three are sub-day fixes.

**Suggested Phase 4.5 scope (before merge):**
- Issue #3 — either build the 2 missing Acceso sub-pages OR remove the
  anchors. (1–2 hours either way.)
- Issue #5 — wrap multi-line comments in `{% comment %}` blocks. (5 minutes.)
- Issue #2 — switcher fallback when no translation exists. (15 minutes.)

**Suggested Phase 5 / polish (post-merge):**
- Issue #1 — homepage carousel/grids. (Bigger UX/design decision.)
- Issue #4 — Tarifas pricing matrix. (Content authoring task; potentially
  weeks if structured.)
- Issue #6 — sitemap.xml + robots.txt. (1 hour.)
- Issue #7 — equipment category hero images. (1 hour, content task.)
- Issues #8, #9 — populate-command idempotency cleanup. (30 minutes.)
- Issue #10 — team role labels review. (Editorial.)

**Defer to backlog:** The remaining inventory pages (`/solicitud-de-acceso/`,
`/calendario-de-convocatorias/`, `/politica-de-privacidad-y-cookies/`,
`/convocatorias/`, news archive beyond 12 posts, press archive beyond 12
items) per the original Phase 0 plan.
