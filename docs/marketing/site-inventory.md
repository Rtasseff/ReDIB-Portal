# redib.net — Public Site Inventory (Phase 0)

Captured 2026-05-30 by automated crawl of the live site at https://redib.net (canonical
host: `www.redib.net`). Source CMS appears to be a custom theme — "cimagune" — built by
the Spanish agency Prisma CM (`prismacm.com`). The site is the public marketing/info portal
for the ReDIB ICTS. This document is the complete inventory used as input for the Wagtail
rebuild planning in Phase 1.

---

## Overview

ReDIB (Red Distribuida de Imagen Biomédica) is a Spanish ICTS (Infraestructura Científica
y Técnica Singular) — a distributed biomedical imaging research network with four nodes:
CIC biomaGUNE (San Sebastián), TRIMA@CNIC (Madrid), Imaging La Fe (Valencia), and BioImaC
(Madrid/UCM). The public site exists to: (1) advertise the network and its equipment to
external researchers, (2) explain the access mechanisms (Competitive Open Access AAC and
on-demand AaD), and (3) point applicants to the portal at `portal.redib.net` for actual
submissions. Audience is principally Spanish and international biomedical researchers and
their institutions. The primary CTAs across the site are "Solicitud de acceso" /
"Access request" and the live convocatoria links, both of which route to the COA portal.

There is also a private admin area at `docs.redib.net` referenced as "Área Privada" in
every footer — this is **explicitly excluded** from scope per the brief (it is the
third-party CMS admin being decommissioned).

## Bilingual URL pattern

The site is fully bilingual (Spanish + English) on a **single domain** with
**per-page slug aliases** — there is no `/es/` or `/en/` URL prefix, no query parameter,
and no cookie-based locale. Each page has two distinct slugs and a language switcher in
the header rewrites between them. There is no `<link rel="alternate" hreflang>` visible
in the HTML, but the pairing is consistent.

Three slug patterns are used in English:

1. **Translated semantic slug** — most common. e.g. `/equipo` ↔ `/team`,
   `/contacto` ↔ `/contact`, `/noticias` ↔ `/news`, `/tarifas` ↔ `/prices`.
2. **`en-` prefix** when the Spanish slug is already English-looking. e.g. `/redib` ↔
   `/en-redib`, `/es-acceso` ↔ `/en-access`. (Note that the Spanish "Access" page uses
   the `es-` prefix specifically because of this collision.)
3. **`localizacion-` prefix on nodes** — node pages have two URL forms that resolve to
   the same content: `/bioimac` (canonical) AND `/localizacion-bioimac` (English version
   AND a redundant Spanish alias). The English language switcher always points to the
   `/localizacion-*` variant.

Examples (one row per page):

| Spanish URL | English URL |
| --- | --- |
| `https://www.redib.net/` (and `/inicio`) | `https://www.redib.net/home` |
| `/redib` | `/en-redib` |
| `/localizacion` | `/location` |
| `/bioimac` | `/localizacion-bioimac` |
| `/cnic` | `/localizacion-cnic` |
| `/imaging-la-fe` | `/localizacion-imaging-la-fe` |
| `/cic-biomagune` | `/localizacion-cic-biomagune` |
| `/equipo` | `/team` |
| `/equipamiento` | `/equipment` |
| `/imagen-clinica` | `/equipamiento-clinical-imaging` |
| `/imagen-preclinica` | `/preclinical-imaging` |
| `/analisis-de-imagen-clinica-y-preclinica` | `/clinical-and-preclinical-image-analytics` |
| `/radioquimica` | `/radiochemistry` |
| `/es-acceso` | `/en-access` |
| `/documentacion` | `/documentation` |
| `/costes-de-acceso` | `/access-cost` |
| `/convocatorias` | `/calls` |
| `/solicitud-de-acceso` | `/access-request` |
| `/calendario-de-convocatorias` | `/calendar-of-calls` |
| `/tarifas` | `/prices` |
| `/actualidad` | `/present` |
| `/enlaces-de-interes` | `/links-of-interest` |
| `/prensa` | `/press` |
| `/noticias` | `/news` |
| `/contacto` | `/contact` |
| `/aviso-legal` | `/legal-advice` |
| `/politica-de-privacidad-y-cookies` | `/privacy-policy-and-cookies` |

News articles each have their own ES/EN slug pair (see Sitemap section for examples). Both
pages of each pair appear in the respective listing only — there is no automatic redirect
between them.

**Quirks worth noting:**
- The footer "Equipo" link in the English layout points to `/management-area`, which
  **returns HTTP 404**. This is a dead link in the current site.
- `/inicio` and `/` show identical homepage content (alias).
- `/equipamiento` (Spanish) and `/equipment` (English) are "section landing" URLs that
  silently fall through to **Clinical Imaging** content (the first sub-page). There is no
  standalone overview page for Equipment.
- `/es-acceso` and `/en-access` similarly fall through to **Documentation** content.
- `/actualidad` and `/present` fall through to **Enlaces de interés**.
- This "section parent defaults to first child" pattern is consistent and likely a CMS
  artifact. The Wagtail rebuild should decide whether to give these sections real
  landing pages or keep them as redirects.
- The pagination URL pattern for the news/press lists is `/<index>/pag-<n>`
  (e.g. `/noticias/pag-3`). Page 7 of `/noticias` is empty — the actual final page is 6.

## Sitemap

### Top-level navigation pages (Spanish)

| URL (slug) | Title | Proposed Wagtail page type |
| --- | --- | --- |
| `/` (and `/inicio`) | Inicio | `HomePage` |
| `/redib` | ReDiB (Red Distribuida de Imagen Biomédica) | `StandardPage` (about-the-network) |
| `/localizacion` | Localización | `NodeCatalogPage` (or a redirect to the node grid) |
| `/bioimac` | BioImaC | `NodePage` |
| `/cnic` | CNIC | `NodePage` |
| `/imaging-la-fe` | Imaging La Fe | `NodePage` |
| `/cic-biomagune` | CIC biomaGUNE | `NodePage` |
| `/equipo` | Equipo | `TeamPage` |
| `/equipamiento` | Equipamiento (section parent, falls through to Imagen Clínica) | `EquipmentIndexPage` (new — or just redirect to first child) |
| `/imagen-clinica` | Imagen Clínica | `EquipmentCategoryPage` (new) |
| `/imagen-preclinica` | Imagen Preclínica | `EquipmentCategoryPage` (new) |
| `/analisis-de-imagen-clinica-y-preclinica` | Análisis de imagen clínica y preclínica | `EquipmentCategoryPage` (new) |
| `/radioquimica` | Radioquímica | `EquipmentCategoryPage` (new) |
| `/es-acceso` | Acceso (section parent, falls through to Documentación) | `AccessIndexPage` (new — or redirect) |
| `/documentacion` | Documentación | `DocumentLibraryPage` (new — PDF-listing) |
| `/costes-de-acceso` | Costes de Acceso | `StandardPage` |
| `/convocatorias` | Convocatorias | `CallsIndexPage` (new — or pull live from portal API) |
| `/solicitud-de-acceso` | Solicitud de acceso | `StandardPage` (CTAs out to portal.redib.net) |
| `/calendario-de-convocatorias` | Calendario de convocatorias | `StandardPage` |
| `/tarifas` | Tarifas | `StandardPage` (heavy tables — possibly `PricingPage` new type) |
| `/actualidad` | Actualidad (section parent, falls through to Enlaces) | `PresentIndexPage` (new — or redirect) |
| `/enlaces-de-interes` | Enlaces de interés | `LinksPage` (new — or `StandardPage`) |
| `/prensa` | Prensa | `PressIndexPage` (new — list of mixed-internal+external items) |
| `/noticias` | Noticias | `NewsIndexPage` |
| `/contacto` | Contacto | `ContactPage` |
| `/aviso-legal` | Aviso legal | `StandardPage` |
| `/politica-de-privacidad-y-cookies` | Política de Privacidad y Cookies | `StandardPage` |

### English mirror

Every page above has an English counterpart at the slug listed in the "Bilingual URL
pattern" section. Wagtail's `wagtail-localize` (or the `i18n_patterns` + `TranslatablePage`
approach) should drive these.

### Press archive (`/prensa`) — paginated, 3 pages, ~12 items per page

Page 1 (the only page where items are internal ReDIB-hosted posts, dated 21/01/2025):
- `/jornada-abierta-de-imagen-medica-en-el-hospital-la-fe-valencia`
- `/dia-mundial-del-corazon`
- `/congreso-de-la-sociedad-europea-de-cardiologia`
- `/servicio-de-rmn-3-t-en-el-nodo-trimacnic`
- `/adquision-de-nuevas-infraestruturas-94t-mri-bruker-biospec-9430-en-el-nodo-bioimac`
- `/actualizacion-del-mapa-de-icts-2025-2028`
- Plus several 2018-era links — partly external, partly internal (`iislafe.es`, `lavanguardia.com`, etc.)

Pages 2–3 of `/prensa` are entirely **external** links (MINECO, ciencia.gob.es, eurekalert,
mineco news portal, etc.) dating 2014–2018. These are clipping-style references with no
internal landing page.

### News archive (`/noticias`) — paginated, **6 real pages**, 12 items per page, ~72 posts total

Spanning 20/04/2026 (newest) back to 09/12/2015 (oldest). The full list of titles + URLs
extracted is in the per-page tables above the inventory crawl was conducted from; for
brevity in this doc I summarize counts and sample posts. The complete URL list is in the
assets manifest (under "ReDIB news article URLs" — see also git history for the raw crawl).

Representative posts (one per year, both ES + EN slugs):

| Date | ES slug | EN slug | Note |
| --- | --- | --- | --- |
| 20/04/2026 | `/la-primera-convocatoria-de-2026-para-el-acceso-abierto-competitivo-...` | `/the-first-2026-call-for-competitive-open-access-...` | Convocatoria announcement; links to portal + PDF user guide |
| 27/01/2026 | `/redib-se-renueva-en-el-mapa-icts-2025-2028-y-mas-en-el-boletin-de-enero-de-2026` | `/redib-renewed-in-the-icts-map-20252028-and-more-in-the-2026-jan-newsletter` | Newsletter |
| 13/10/2025 | `/taller-sobre-rm-con-agentes-hiperpolarizados` | `/noticias-workshop-on-mri-with-hyperpolarized-agents` | Event |
| 28/05/2025 | `/portafolio-de-servicios-de-imagen-biomedica` | `/portfolio-of-biomedical-imaging-services` | Service catalogue |
| 16/04/2025 | `/red-distribuida-de-imagen-biomedica-redib-una-decada-impulsando-...` | `/distributed-biomedical-imaging-network-redib-a-decade-promoting-...` | Anniversary / has PDF download |
| 15/04/2025 | `/boletin-informativo-mes-de-abril-2025` | `/april-newsletter-2025` | Newsletter PDF |
| 21/12/2024 | `/feliz-navidad` | (none observed) | Holiday card |
| 18/12/2024 | `/boletin-informativo-mes-de-noviembre-2024` | (en mapping uncertain) | Newsletter |
| 20/12/2023 | `/noticias-feliz-2024` | (none observed) | Holiday card |
| 22/11/2021 | `/el-nodo-de-redib-cic-biomagune-participa-en-el-congreso-imaginenano-2021` | (uncertain) | Event |
| 05/02/2020 | `/redib-estara-presente-en-el-proximo-congreso-del-esmi-2020-en-tesalonica-grecia` | (uncertain) | Event |
| 09/12/2015 | `/biomagune-y-cnic-unen-sus-fuerzas-para-convertirse-en-una-referencia-internacional-en-imagen-biomedica` | (uncertain) | Founding news |

The full URL list per news-index page is in the crawl notes for pages 1–6 of `/noticias`
and pages 1–7 of `/news`. The English `/news` index shows ~12 articles on page 1 going back
to March 2025; ES has more total because some older posts were never translated (see
Bilingual pairing audit below).

### Convocatorias (`/convocatorias`)

Not blog posts but a flat list of call codes with date ranges. Currently visible:
- ReDIB2601 (21/04/2026 – 19/05/2026) — current
- ReDIB2502 (01/10/2025 – 07/11/2025)
- REDIB2501 (01/04/2025 – 30/04/2025)
- ReDIB2402, ReDIB2401, plus 12 historical calls back to 2016 (ReDIB-01)

In the rebuild this list **should not be authored manually in Wagtail** — it duplicates
data already in this portal's `Call` model. Recommend the Wagtail page render a live
feed from the portal DB (same Django project, same DB) instead of a static page.

---

## Pages

Each subsection below is **one logical page** (deduped across ES/EN). "Notable embeds"
are content beyond plain text; "Internal links out" lists the main outbound links that the
rebuild needs to preserve.

### Homepage

- **Title (ES):** Inicio | ReDiB - Red Distribuida de Imagen Biomédica
- **Title (EN):** Distributed Biomedical Imaging Network (ReDiB) — "Home"
- **URL (ES):** `https://www.redib.net/` (alias: `/inicio`)
- **URL (EN):** `https://www.redib.net/home`
- **Proposed Wagtail type:** `HomePage`
- **Headings:**
  - H1: Red Distribuida de Imagen Biomédica / Distributed Biomedical Imaging Network
  - H2: Imagen Clínica, Imagen Preclínica, Radioquímica, Equipamiento, Actualidad, Nodos
  - H3: One per node (CIC biomaGUNE, CNIC, Imaging La Fe, BioImaC)
- **Summary:** Hero banner, then six teaser cards: three for imaging-type sections
  (Clinical / Preclinical / Radiochemistry), an Equipment card, a recent-news block (shows
  the two most recent posts as cards with hero images), and a four-node grid linking to
  each location's detail page. Acts as an aggregator — no original long-form content.
- **Notable embeds:** Hero carousel (3 slides visible — indicator dots), two news teaser
  cards (auto-pulled from `/noticias`), four node teaser cards.
- **Internal links out:** All top-level nav, the four node pages, recent two news posts,
  Equipment, Actualidad.

### About — "ReDiB" / "en-redib"

- **Title (ES):** Red Distribuida de Imagen Biomédica (ReDIB)
- **Title (EN):** Distributed Biomedical Imaging Network (ReDIB)
- **URL (ES):** `/redib`
- **URL (EN):** `/en-redib`
- **Proposed Wagtail type:** `StandardPage`
- **Headings:** H1 "ReDiB"; H2 "Red Distribuida de Imagen Biomédica (ReDIB)"; node subsections
  H3 (TRIMA/CNIC, CIC biomaGUNE, Imaging La Fe, BioImaC)
- **Summary:** Explanatory page describing the network and its mission ("servicios
  competitivos de acceso abierto en el campo de la imagen molecular y funcional").
  Describes each of the four node-centers in 1–2 paragraphs each. EN version shows
  additional context: "Unique Scientific and Technologic Infrastructure (ICTS)" framing.
- **Notable embeds:** 4 large node imagery photos (one per node).
- **Internal links out:** Each node detail page.

### Localización (Locations index)

- **Title (ES):** Localización | (Spanish landing page, but the nav menu's "Localización"
  entry actually expands as a dropdown of the four node links — the index page itself is
  thin).
- **URL (ES):** `/localizacion`
- **URL (EN):** `/location`
- **Proposed Wagtail type:** `NodeCatalogPage` (new) — or simply a `StandardPage` that lists
  the four `NodePage` children. Could also be eliminated since the user-facing nav goes
  directly to children.
- **Headings:** Generic; little H1/H2 content.
- **Summary:** Effectively a node directory — the page lists the four locations with map
  thumbnails and small description blurbs. The English equivalent appeared to fall through
  to the same content. The site relies on the dropdown nav more than on this page.
- **Notable embeds:** Four node teaser cards with photos.
- **Internal links out:** All four nodes.

### Node: BioImaC

- **Title:** BioImaC (Centro de BioImagen Complutense)
- **URL (ES):** `/bioimac` (also accessible at `/localizacion-bioimac`)
- **URL (EN):** `/localizacion-bioimac`
- **Proposed Wagtail type:** `NodePage`
- **Headings:** H1 "BioImaC"; H2 "Equipamiento disponible"; H3 per equipment item
  ("PET-RM 9.4T Bruker BioSpec con CryoProbe", "RM 1T Bruker ICON")
- **Summary:** Node detail page for the Complutense University BioImaC center in Madrid.
  Lists the host institution, full address, phone, contact email, partner website, and an
  "Available equipment" list with photo per machine. Mentions "Ubicación en Google maps"
  but the page does not actually embed a Google Map widget.
- **Notable embeds:** 1 hero image + 2 equipment photos. "Ubicación en Google maps" is a
  text label only — no iframe present.
- **Address:** Paseo de Juan XXIII, nº 1, 28040 Madrid · 913 94 32 72 · `cai.ucm.es/bioimagen/`
- **Internal links out:** All sibling nodes, Equipment, Access pages.

### Node: CNIC (TRIMA@CNIC)

- **Title:** CNIC (Centro Nacional de Investigaciones Cardiovasculares Carlos III)
- **URL (ES):** `/cnic`
- **URL (EN):** `/localizacion-cnic`
- **Proposed Wagtail type:** `NodePage`
- **Headings:** H1 "CNIC"; "Ubicación en Google maps"; "Equipamiento disponible"; H3 per
  equipment item (Molecubes PET/SPECT/CT, RM 3T Philips Elition, RM 7T Agilent-Varian,
  PET-TAC Philips Vereos, Leica TIRF, FMT Perkin Elmer, 3D IVIS Perkin Elmer 200)
- **Summary:** Node detail page for the CNIC node in Madrid. Lists 7 imaging systems
  across clinical and preclinical types.
- **Notable embeds:** Hero + 7 equipment photos. Map reference only (no iframe).
- **Address:** C/ Melchor Fernández Almagro, 3, 28029 Madrid · 914 53 12 00 · `cnic.es`

### Node: Imaging La Fe

- **Title:** Imaging La Fe
- **URL (ES):** `/imaging-la-fe`
- **URL (EN):** `/localizacion-imaging-la-fe`
- **Proposed Wagtail type:** `NodePage`
- **Headings:** H1 "Imaging La Fe"; H2 equipment subsections; H3 per equipment item
  (TAC-MDCT Philips Brilliance iCT, RM 3T Philips Achieva TX, PET-RM 3T General Electric
  SIGNA, Laboratorio de imágenes computacionales biomédicas)
- **Summary:** Node detail page for the hospital-based La Fe node in Valencia. Highlights
  computational image-analysis lab in addition to scanners.
- **Notable embeds:** Hero + 5 equipment photos. Map reference only.
- **Address:** Avda. Fernando Abril Martorell, 106, planta -1, 46026 Valencia ·
  961 24 40 09 · `gibi230@iislafe.es` · `acim.lafe.san.gva.es/acim/`

### Node: CIC biomaGUNE

- **Title:** CIC biomaGUNE
- **URL (ES):** `/cic-biomagune`
- **URL (EN):** `/localizacion-cic-biomagune`
- **Proposed Wagtail type:** `NodePage`
- **Headings:** H1 "CIC biomaGUNE"; H2 "Equipamiento disponible"; H3 per equipment item
  (Molecubes PET-SPECT-TAC, RM 7T Bruker BioSpec, RM 11.7T Bruker BioSpec, MILabs VECtor,
  Ciclotrón IBA 9/18, Laboratorio de Radioquímica)
- **Summary:** Node detail for the San Sebastián CIC biomaGUNE center. Most equipment-rich
  node — includes a cyclotron and dedicated radiochemistry lab.
- **Notable embeds:** Hero + 6 equipment photos. Map reference only.
- **Address:** Pº Miramón, 194, 20009 Donostia-San Sebastián · 943 00 53 36 ·
  `cicbiomagune.es`

### Equipo (Team)

- **Title:** Equipo / Team
- **URL (ES):** `/equipo`
- **URL (EN):** `/team`
- **Proposed Wagtail type:** `TeamPage` (with `TeamMember` Orderable / Snippet)
- **Headings:** H1 "Equipo"; H2 Coordinador, Comité de coordinación, Comité Asesor
  Científico-Técnico, Área de Gestión
- **Summary:** Lists ~14 people organized into four sections. Each entry has a headshot
  photo and a one-line role / affiliation caption. No bios.
- **Notable embeds:** ~14 headshot images.
- **Members captured:**
  - **Coordinator:** Jesús Ruiz-Cabello Osuna (CIC biomaGUNE Director, REDIB Coordinator)
  - **Coordination Committee:** José Luis Izquierdo (BioImaC), Borja Ibáñez Cabeza (TRIMA-CNIC),
    Gonzalo Pizarro Sánchez (TRIMA-CNIC rep), Luis Martí-Bonmatí (Imaging La Fe)
  - **Scientific-Technical Advisory Committee:** Noam Shemesh (Champalimaud, Lisbon),
    Irene Marco Rius (IBEC Barcelona), Juan José Vaquero (UC3M Madrid), Eduardo Fraile
    Moreno (San Francisco de Asís Hospital), Lluis Donoso Bach (Hospital Clinic Barcelona),
    Jeff Bulte (Johns Hopkins)
  - **Management Area:** Ryan Tasseff (REDIB Manager), Cristina Álvarez de Lara Sánchez
    (BioImaC), Ana Penadés Blasco (Imagen La Fe)

### Equipamiento section (parent — falls through to Imagen Clínica)

- **URL (ES):** `/equipamiento` (URL exists but renders Imagen Clínica content)
- **URL (EN):** `/equipment` (same behaviour)
- **Proposed Wagtail type:** Either build a real overview page (`EquipmentIndexPage`) or
  alias to `/imagen-clinica`. Either is fine — current site has no dedicated landing.

### Equipment — Imagen Clínica

- **Title (ES):** Imagen Clínica | Resonancia Magnética, PET/CT y TAC
- **Title (EN):** Clinical Imaging | MRI, PET/CT & CT
- **URL (ES):** `/imagen-clinica`
- **URL (EN):** `/equipamiento-clinical-imaging`
- **Proposed Wagtail type:** `EquipmentCategoryPage` (new — or `StandardPage`)
- **Headings:** H1 "Imagen clínica"; H2 "Imagen híbrida PET-RM"; H2 "Resonancia Magnética";
  H3 per equipment item
- **Summary:** Catalogue of all clinical-imaging equipment across the network — PET-RM
  hybrid, MRI scanners, multi-detector CT, digital PET-CT — grouped by category with
  spec photos. Cross-references which node hosts each system.
- **Notable embeds:** 1 hero + 5 equipment photos.
- **Equipment items:** PET-RM 3T GE SIGNA (La Fe), TAC-MDCT Philips Brilliance iCT (La Fe),
  RM 3T Philips Achieva TX (La Fe), RM 3T Philips Elition (CNIC), PET-TAC Philips Vereos
  (CNIC).

### Equipment — Imagen Preclínica

- **Title (ES):** Imagen Preclínica | MicroPET, MicroCT y Equipos Avanzados
- **Title (EN):** Preclinical Imaging
- **URL (ES):** `/imagen-preclinica`
- **URL (EN):** `/preclinical-imaging`
- **Proposed Wagtail type:** `EquipmentCategoryPage`
- **Headings:** H1 "Imagen preclínica"; H2 Imagen híbrida PET-MR, Resonancia Magnética,
  Imagen Nuclear, Dotación/equipamiento adicional
- **Summary:** Catalogue of preclinical (small-animal) imaging equipment — high-field MRI
  (7T, 9.4T, 11.7T), PET-SPECT-CT multimodal systems, optical (Leica TIRF, FMT, 3D IVIS).
  ~14 distinct equipment listings with photos.
- **Notable embeds:** 1 hero + ~13 equipment photos.

### Equipment — Análisis de imagen (Image analytics)

- **Title (ES):** Análisis de Imagen | Software Avanzado y Estaciones de Procesamiento
- **Title (EN):** Clinical and Preclinical Image Analytics
- **URL (ES):** `/analisis-de-imagen-clinica-y-preclinica`
- **URL (EN):** `/clinical-and-preclinical-image-analytics`
- **Proposed Wagtail type:** `EquipmentCategoryPage`
- **Headings:** H1 "Análisis de imagen clínica y preclínica"; H2 Imagen Preclínica, Imagen
  Clínica, Laboratorio de imágenes computacionales biomédicas
- **Summary:** Describes the analytics / post-processing capabilities — PMOD licenses,
  MATLAB, FSL, IDL, EchoPac, QMASS, QLab-Philips, HPC servers, Tesla K-40 GPUs.
- **Notable embeds:** 3 photos (hero + 2 lab photos).

### Equipment — Radioquímica

- **Title (ES):** Acceso a Laboratorio de Radioquímica
- **Title (EN):** Radiochemistry
- **URL (ES):** `/radioquimica`
- **URL (EN):** `/radiochemistry`
- **Proposed Wagtail type:** `EquipmentCategoryPage`
- **Headings:** H1 "Radioquímica"; H2 Laboratorios, Ciclotrón IBA 9/18, Trazadores
  disponibles, Isótopos Autorizados
- **Summary:** Describes radiochemistry capabilities — lead-shielded hot cells, IBA 9/18
  cyclotron, synthesis modules, HPLC/TLC, Ga-68 generator. Includes a long list of 21+
  authorized isotopes and a list of available radiotracers (FDG, FLT, FMISO, choline,
  multiple receptor-targeting compounds).
- **Notable embeds:** 2 photos (cyclotron, lab).

### Acceso section (parent — falls through to Documentación)

- **URL (ES):** `/es-acceso` — renders Documentación content
- **URL (EN):** `/en-access` — renders Documentation content
- **Proposed Wagtail type:** Either build a real "Access overview" page or alias to
  `/solicitud-de-acceso`. The latter is more useful given that Solicitud is the actionable
  step.

### Acceso — Documentación

- **Title:** Documentación / Documentation
- **URL (ES):** `/documentacion`
- **URL (EN):** `/documentation`
- **Proposed Wagtail type:** `DocumentLibraryPage` (new) — a curated list of policy PDFs
- **Headings:** H1 "Documentación"; H2 "Menú de secciones"
- **Summary:** Lists 7 governance PDFs for download. All published under the "REDIB-XX"
  numbering scheme.
- **Notable embeds:** 7 PDF downloads (see assets manifest).
- **Documents:**
  1. REDIB-01-PDA. Reglamento del Comité de Acceso
  2. REDIB-02-PDA Protocolos de acceso
  3. REDIB-03-PDC. Planificación de convocatorias
  4. REDIB-04-SYR Gestión de reclamaciones e incidencias
  5. REDIB-05-DDP Ejercicio de derechos de datos personales
  6. Acuerdo ReDIB de corresponsabilidad para la Gestión de Datos
  7. Guía de uso del portal de convocatorias

### Acceso — Costes de Acceso

- **Title:** Costes asociados según el tipo de solicitud del acceso / Access Cost
- **URL (ES):** `/costes-de-acceso`
- **URL (EN):** `/access-cost`
- **Proposed Wagtail type:** `StandardPage`
- **Headings:** H1 "Costes de Acceso"; H2 "A instalaciones singulares de ReDIB"; H2 "A
  otras instalaciones de ReDIB"
- **Summary:** Two-section text page explaining the subsidized cost model: AAC offers
  reduced/free rates (covering only radiopharmaceuticals and consumables); AaD uses full
  standard rates. Additional non-ICTS infrastructure at the nodes uses per-node pricing.
- **Notable embeds:** None.

### Acceso — Convocatorias

- **Title:** Convocatorias / Calls
- **URL (ES):** `/convocatorias`
- **URL (EN):** `/calls`
- **Proposed Wagtail type:** `CallsIndexPage` (new) — but recommend live feed from the
  portal DB instead of a hand-maintained Wagtail page
- **Headings:** H1 "Convocatorias"; H2 "Convocatoria Actual"; H2 "Histórico"
- **Summary:** Flat list of calls with code (e.g. ReDIB2601), open date, close date.
  Currently lists one current call and ~16 historical entries going back to 2016.
- **Notable embeds:** None.

### Acceso — Solicitud de acceso

- **Title:** Solicitud de acceso la ICTS Bioimagen REDIB
- **URL (ES):** `/solicitud-de-acceso`
- **URL (EN):** `/access-request`
- **Proposed Wagtail type:** `StandardPage` — the actual submission lives at
  `portal.redib.net`, this page just explains the process and CTAs out.
- **Headings:** H1 "Solicitud de acceso"; H2 numbered sections "1. Mecanismos de Acceso a
  Infraestructuras Singulares", "2. Viabilidad", "3. Aprobación", "4. Priorización"; H3
  "Acceso Abierto Competitivo (AAC)", "Acceso a Demanda (AaD)"
- **Summary:** Long-form explanation of the two access mechanisms and the evaluation
  workflow (feasibility, approval, prioritization). Outbound CTAs go to
  `https://portal.redib.net/` and `https://portal.redib.net/calls/`.
- **Notable embeds:** None — text-heavy. Outbound links to the portal.

### Acceso — Calendario de convocatorias

- **Title:** Planificación de convocatorias / Calendar of Calls
- **URL (ES):** `/calendario-de-convocatorias`
- **URL (EN):** `/calendar-of-calls`
- **Proposed Wagtail type:** `StandardPage`
- **Headings:** H1 "Calendario de convocatorias"; H2 "Plazos de presentación", "Limitación
  de tiempos"
- **Summary:** Brief explanation that AAC submissions are only accepted electronically
  within published windows, plus a paragraph about maximum-hours-per-facility limits. **No
  actual dates are listed** on this page — it's an explanatory companion to `/convocatorias`.
- **Notable embeds:** None.

### Tarifas

- **Title:** Tarifas / Prices
- **URL (ES):** `/tarifas`
- **URL (EN):** `/prices`
- **Proposed Wagtail type:** `StandardPage` or new `PricingPage` (heavy tables)
- **Headings:** H1 "Tarifas"; H2 "Acceso Abierto Competitivo (AAC)", "Acceso a Demanda (AaD)",
  "Agentes de contraste"
- **Summary:** Large pricing matrix: rows = (node × imaging modality × service unit);
  columns = AAC price, AaD-OPIS price, AaD-Other price. Second table lists radiotracers
  grouped by isotope. This is the most data-dense page on the site.
- **Notable embeds:** None — pure HTML tables.

### Actualidad section (parent — falls through to Enlaces de interés)

- **URL (ES):** `/actualidad`
- **URL (EN):** `/present`
- **Proposed Wagtail type:** Index page or redirect to `/noticias`.

### Actualidad — Enlaces de interés

- **Title:** Enlaces de interés / Links of interest
- **URL (ES):** `/enlaces-de-interes`
- **URL (EN):** `/links-of-interest`
- **Proposed Wagtail type:** `StandardPage` (or a new `LinksPage` with `LinkBlock` items)
- **Headings:** H1 "Enlaces de interés"; H2 per link card ("Mapa de las ICTS", "Síguenos en
  Twitter @ICTSReDIB", "ReDIB como plataforma en CIC biomaGUNE", "ReDIB como plataforma en
  el CNIC", "Síguenos en LinkedIn")
- **Summary:** Five external link cards: ICTS map, Twitter, CIC biomaGUNE platform page,
  CNIC Flickr album, LinkedIn company page.
- **Notable embeds:** External link tiles only.
- **External links:** `mapa.gob.es/es/pesca/temas/innovacion/mapa_icts`,
  `twitter.com/IctsRedib`, `cicbiomagune.es/org/uim`,
  `flickr.com/photos/139407851@N06/albums/72157665630049300`,
  `es.linkedin.com/company/redib---icts`

### Actualidad — Prensa

- **Title:** Prensa / Press
- **URL (ES):** `/prensa`
- **URL (EN):** `/press`
- **Proposed Wagtail type:** `PressIndexPage` (new) — supports both internal `PressPostPage`
  children AND external "clipping" rows that are just (title, source, date, URL)
- **Headings:** H1 "Prensa"
- **Summary:** Paginated (3 pages, ~12 per page) timeline of press mentions. Page 1 is
  internal posts (mostly January 2025). Pages 2-3 are 100% external clippings — links to
  MINECO, ciencia.gob.es, eurekalert, lavanguardia.com, sebbm.es, cnic.es, etc., dating
  2014-2018.
- **Notable embeds:** Each row has a small thumbnail.

### Actualidad — Noticias (News)

- **Title:** Noticias / News
- **URL (ES):** `/noticias`
- **URL (EN):** `/news`
- **Proposed Wagtail type:** `NewsIndexPage` with `NewsPostPage` children
- **Headings:** H1 "Noticias"; UI control "Categoría — Filtrar por categoría"
- **Summary:** Paginated (6 pages, 12 per page, ~72 total ES posts) news archive
  spanning 09/12/2015 to 20/04/2026. Each post has: title, date, hero/thumbnail image, body
  HTML, **no author byline**. Some posts include PDF attachments (newsletters,
  service-portfolio docs).
- **Notable embeds:** Category filter UI exists but the category taxonomy was not visible
  in the crawl — may be empty or unused. Need to verify in Phase 1 whether categories
  are populated.
- **Pagination:** URL pattern `/noticias/pag-N` for ES, `/news/pag-N` for EN. Page 7
  exists in the pager but is empty (off-by-one bug in the source CMS).

### Sample news article — "La Primera Convocatoria de 2026..."

- **Title (ES):** La Primera Convocatoria de 2026 para el Acceso Abierto Competitivo...
- **URL (ES):** `/la-primera-convocatoria-de-2026-para-el-acceso-abierto-competitivo-a-las-infraestructuras-cientificas-y-tecnicas-singulares-icts-de-redib-ya-esta-abierta`
- **URL (EN):** `/the-first-2026-call-for-competitive-open-access-to-redibs-unique-scientific-and-technical-infrastructures-icts-is-now-open`
- **Date:** 20/04/2026 (no author byline)
- **Proposed Wagtail type:** `NewsPostPage`
- **Summary:** Announces the 2026-Q1 competitive open access call, lists key equipment per
  node, links to the portal call page and the PDF user guide.
- **Notable embeds:** PDF download (`redib-coa-portal-user-guide-20260429_1_original.pdf`),
  outbound links to `portal.redib.net/calls/1/`.

### Contacto

- **Title:** Contacto / Contact
- **URL (ES):** `/contacto`
- **URL (EN):** `/contact`
- **Proposed Wagtail type:** `ContactPage` (or `StandardPage` + Wagtail Form Builder)
- **Headings:** H1 "Formulario de contacto" / "Contact form"
- **Summary:** Contact form with fields: Empresa, Nombre (required), Apellidos, Email
  (required), Provincia (dropdown of Spanish provinces), Localidad (dropdown), Teléfono,
  Comentarios (required), data-protection checkbox (required), CAPTCHA. Submits to the
  current third-party CMS. **Per the brief this form is considered dead/replaceable** —
  the only working endpoint is `info@redib.net`. Rebuild can ship either a simpler form
  or a "mailto:" page.
- **Notable embeds:** Form + CAPTCHA. No map embed.

### Legal — Aviso legal

- **Title:** Aviso legal / Legal advice
- **URL (ES):** `/aviso-legal`
- **URL (EN):** `/legal-advice`
- **Proposed Wagtail type:** `StandardPage`
- **Headings:** H2 sections "DATOS IDENTIFICACIÓN", "OBJETO", "USO DEL SITIO WEB", "PROPIEDAD
  INTELECTUAL", "ENLACES", "MODIFICACIÓN UNILATERAL Y DURACIÓN", "EXCLUSIÓN DE GARANTÍAS",
  "TRATAMIENTO DE DATOS PERSONALES", "LEGISLACIÓN APLICABLE"
- **Summary:** Standard Spanish legal-notice text covering identification, terms of use,
  IP, liability, and applicable law. References ReDIB's registration with the Basque
  Government since 2003.

### Legal — Política de Privacidad y Cookies

- **Title:** Política de Privacidad y Cookies / Privacy Policy and Cookies
- **URL (ES):** `/politica-de-privacidad-y-cookies`
- **URL (EN):** `/privacy-policy-and-cookies`
- **Proposed Wagtail type:** `StandardPage`
- **Headings:** H2 "Política de Privacidad de ReDIB"; multiple H3 subsections (Corresponsables
  del tratamiento, Finalidad, Categoría, Base, Decisiones automatizadas, Transferencia,
  Conservación, Derechos, Información adicional); H2 "Política de cookies"; H3 "¿Qué son?",
  "¿Cuáles son las utilizadas?", "Retirar consentimiento", "Cómo deshabilitar", "Cambios"
- **Summary:** Full GDPR/LOPDGDD privacy notice with data-controller info, processing
  purposes, lawful bases, retention, and user rights. Plus cookie inventory.

---

## Bilingual pairing audit

ES has more total content than EN. Most static pages **are** paired 1:1, but the news
archive has a clear translation gap. Findings:

- **Static pages (navigation):** All 28 navigation pages have ES↔EN pairs. Verified.
- **Node pages:** All 4 node pages have ES↔EN pairs.
- **News articles (post-2025):** The 12 most-recent ES posts visible on `/noticias` page
  1 each have an EN counterpart visible on `/news` page 1. EN news index goes back to
  March 2025.
- **News articles (pre-2025):** ES pages 2–6 of `/noticias` contain ~60 additional Spanish
  posts from 2015–2024 (covering older convocatorias, events, Christmas cards, internal
  news). **EN equivalents for these older posts were not enumerated** — the English
  `/news` archive may be shorter, or the EN slugs may use a different convention. This is
  a gap worth verifying in Phase 1; the safest assumption is that the rebuild should treat
  pre-2025 posts as **ES-only** unless paired EN content is found during content migration.
- **Press archive:** Pages 2-3 of `/prensa` are essentially all outbound links — they will
  not need translation since the destination pages decide their own language.
- **Pages with translation issues found in the crawl:**
  - Footer `/management-area` (English "Equipo" link) — **404**. The actual English Team
    URL is `/team`. Bug in current site footer.
  - The English `/access-request` page title says "Priorization" (typo in source).
  - The English homepage has "Preclinical lmaging" (lowercase L typo) in an H2 — typo in
    the live site.
- **Pages confirmed to have NO bilingual divergence** (content equivalent):
  Homepage, /redib, all four nodes, /equipo, /imagen-clinica, /imagen-preclinica,
  /radioquimica, /tarifas, /documentacion, /solicitud-de-acceso, /contacto,
  /aviso-legal, /politica-de-privacidad-y-cookies.

**Unpaired / orphan pages identified:**
- `/feliz-navidad` (ES, 21/12/2024) and `/noticias-feliz-2024` (ES, 20/12/2023) — likely
  ES-only seasonal posts. Not a concern.
- The `/management-area` link target — dead.

---

## Feature inventory

Every interactive feature observed during the crawl, with the likely status in the
rebuild.

| Feature | Where | Status today | Recommendation for Wagtail rebuild |
| --- | --- | --- | --- |
| **Language switcher** | Header, every page | Working; toggles per-page ES↔EN slug | Keep — implement via `wagtail-localize` |
| **Cookie consent banner** | Every page (first load) | Working; three categories (technical, statistics, third-party) | Reuse with new consent solution (e.g. `django-cookie-consent` or a JS lib) |
| **Contact form** | `/contacto`, `/contact` | Working but backed by the dying CMS; brief says it's effectively dead | Replace with Wagtail Form Builder or simple Django form posting to `info@redib.net` |
| **News category filter** | `/noticias`, `/news` | UI present, behaviour unverified — may be empty | Verify category data exists before porting; otherwise drop |
| **News pagination** | `/noticias/pag-N`, `/news/pag-N` | Working; page 7 is empty (off-by-one) | Wagtail's `Paginator` handles this cleanly |
| **Press pagination** | `/prensa/pag-N`, `/press/pag-N` | Working; 3 pages | Keep |
| **Hero carousel on homepage** | `/`, `/home` | Working; 3 slides | Standard Wagtail StreamField with image carousel block |
| **PDF downloads** | Documentación, individual news posts | Working; PDFs hosted at `/upload/secciones-publicas/*.pdf` | Migrate as Wagtail Documents |
| **External-link cards** | `/enlaces-de-interes` | Working | Trivial to port |
| **Search box** | NOT FOUND anywhere on the public site | N/A | Optional — could add Wagtail search in rebuild |
| **RSS feed** | NOT FOUND. No `/feed`, `/rss`, `/atom.xml` advertised | N/A | Optional — Wagtail has `RssFeed` mixin if desired |
| **Newsletter signup** | NOT FOUND (newsletters are PDFs posted as news) | N/A | Skip |
| **Social media embeds** | None — only outbound link cards to Twitter / LinkedIn / Flickr | N/A | Skip embeds; keep link cards |
| **Map embeds** | Each node page has a text label "Ubicación en Google maps" but **no iframe** is actually present | Likely a broken/removed feature | Decide whether to ship real `<iframe>` Google Maps embeds or static map images |
| **"Convocatorias" data table** | `/convocatorias`, `/calls` | Static HTML list, manually maintained | Replace with live feed from `Call` model in this portal's DB |
| **Private area link** | Footer → `docs.redib.net` | Out of scope per brief — being decommissioned with this rebuild | Remove the link or repoint to Wagtail admin |
| **Footer "Equipo / Team" link** | English footer points to `/management-area` (404) | Broken | Fix the link target in rebuild |
| **Sitemap.xml / robots.txt** | Not fetched in this crawl; should verify in Phase 1 | Unknown | Add `wagtail-sitemap` |
| **CAPTCHA on contact form** | Working | Tied to dying CMS | Reimplement with `django-recaptcha` or `hcaptcha` |
| **Province / locality cascading dropdowns** | Contact form Provincia → Localidad | Working | Drop — not needed for a generic "contact us" form |

## Crawl summary

- **Distinct pages crawled**: 30 (homepage + 28 nav-level + sample news article)
- **News articles enumerated by title/URL**: 72 (full ES list across `/noticias/pag-1`
  through `/noticias/pag-6`)
- **Press items enumerated**: 27 (across 3 pages)
- **Convocatorias listed**: ~17 (one current + ~16 historical)
- **PDFs identified for migration**: 9 (7 governance + 2 newsletters + 1 anniversary doc;
  see assets manifest)
- **Headshot images identified**: 14
- **Equipment/photo images identified**: 30+
- **External institutional links to preserve**: ~10
- **Crawler errors observed**:
  - `/management-area` → HTTP 404
  - `/redib-renueva-en-el-mapa-icts...` (wrong slug guess) → HTTP 404 (recovered to correct
    slug `/redib-se-renueva-...`)
  - `/noticias/pag-7` exists in pager but is empty (off-by-one)
  - "Section parent" URLs (`/equipamiento`, `/es-acceso`, `/actualidad` and their EN
    equivalents) silently fall through to first child — not errors, but architectural smell
