# redib.net — Assets Manifest (Phase 0)

Every binary asset (image, PDF, document) discovered during the Phase 0 crawl. Listed by
absolute URL with brief usage notes. **No assets were downloaded** during discovery — this
inventory is URL-only.

The site stores user-uploaded media under `/upload/secciones-publicas/` and theme assets
under `/temas/cimagune/`. The legacy CMS appears to auto-generate multiple cropped
variants of each image with suffixes like `_6c.jpg`, `_4c.png`, `_cr_portada.jpg`,
`_cr_4w_3h.png`, `_equipamiento.jpg`, `_foto.jpg`, etc. — these are the same source images
re-cropped for different placements. **For migration we should grab one canonical version
per image** rather than every cropped variant.

---

## Logos and chrome (theme assets)

These come from the CMS theme directory and need to be re-rendered/replaced; they are
not user content.

| URL | Usage |
| --- | --- |
| `https://www.redib.net/img/logo.png` | Main ReDIB logo, used in header (every page) |
| `https://www.redib.net/temas/cimagune/img/header/logo_EU.png` | EU funding logo in top-of-header strip |
| `https://www.redib.net/temas/cimagune/img/header/icts.png` | ICTS (Spanish ministry) logo in top-of-header strip |
| `https://www.redib.net/temas/cimagune/img/footer/ministerio-spain-economia-competitividad.jpg` | Ministerio de Ciencia e Innovación logo block in footer |

## Node hero images

| URL | Used on |
| --- | --- |
| `https://www.redib.net/upload/secciones-publicas/imagenbioimac_6c.jpg` | BioImaC node page, /redib (about) |
| `https://www.redib.net/upload/secciones-publicas/imagenbioimac_1_6c.jpg` | Homepage node grid card (BioImaC) |
| `https://www.redib.net/upload/secciones-publicas/prueba_6c.jpg` | CNIC node hero |
| `https://www.redib.net/upload/secciones-publicas/imagenlafe_6c.jpg` | Imaging La Fe node hero |
| `https://www.redib.net/upload/secciones-publicas/lafe_6c.jpg` | Homepage node grid card (Imaging La Fe) |
| `https://www.redib.net/upload/secciones-publicas/124-24433742634-o1_6c.jpg` | Used on `/redib` about page (likely CIC biomaGUNE generic) |
| `https://www.redib.net/upload/secciones-publicas/img-7655_6c.jpg` | Used on `/redib` about page (likely CNIC TRIMA) |

## Equipment photos (preclinical)

| URL | Equipment |
| --- | --- |
| `https://www.redib.net/upload/secciones-publicas/nuevo-94t_cr_portada.jpg` (also `_equipamiento.jpg`) | 9.4T Bruker BioSpec PET-RM (BioImaC) |
| `https://www.redib.net/upload/secciones-publicas/icon-nueva-foto_cr_portada.jpg` (also `_equipamiento.jpg`) | 1T Bruker ICON RM (BioImaC) |
| `https://www.redib.net/upload/secciones-publicas/pet-spcet-ct.trimacnic_cr_portada.jpg` (also `_equipamiento.jpg`) | Molecubes PET-SPECT-CT (TRIMA-CNIC) |
| `https://www.redib.net/upload/secciones-publicas/7mri-agilent_cr_portada.jpg` (also `_equipamiento.jpg`) | 7T Agilent-Varian RM (CNIC) |
| `https://www.redib.net/upload/secciones-publicas/tirf_cr_portada.jpg` (also `_equipamiento.jpg`) | Leica 3-Colour Fast TIRF DMI 6000 (CNIC) |
| `https://www.redib.net/upload/secciones-publicas/fmt-perkin_cr_portada.jpg` (also `_equipamiento.jpg`) | FMT Perkin Elmer (CNIC) |
| `https://www.redib.net/upload/secciones-publicas/3d-ivis-perkin_cr_portada.jpg` (also `_equipamiento.jpg`) | 3D IVIS Perkin Elmer 200 (CNIC) |
| `https://www.redib.net/upload/secciones-publicas/pet-01_1_cr_portada.jpeg` (also `_equipamiento.jpeg`) | PET-SPECT-TAC Molecubes (CIC biomaGUNE) |
| `https://www.redib.net/upload/secciones-publicas/mri-7t-70-30_cr_portada.jpg` (also `_equipamiento.jpg`) | 7T Bruker BioSpec (CIC biomaGUNE) |
| `https://www.redib.net/upload/secciones-publicas/mri-11.7-t_cr_portada.jpg` (also `_equipamiento.jpg`) | 11.7T Bruker BioSpec (CIC biomaGUNE) |
| `https://www.redib.net/upload/secciones-publicas/milabs03_cr_portada.jpg` (also `_equipamiento.jpg`) | MILabs VECtor PET-SPECT-OI-TAC (CIC biomaGUNE) |
| `https://www.redib.net/upload/secciones-publicas/ciclotron01_1_cr_portada.jpg` (also `_equipamiento.jpg`) | IBA 9/18 cyclotron (CIC biomaGUNE) |
| `https://www.redib.net/upload/secciones-publicas/radioquimica01_cr_portada.jpg` (also `_equipamiento.jpg`) | Radiochemistry lab (CIC biomaGUNE) |
| `https://www.redib.net/upload/secciones-publicas/preclinical-imaging-001_6c.jpg` | Preclinical imaging section hero |

## Equipment photos (clinical)

| URL | Equipment |
| --- | --- |
| `https://www.redib.net/upload/secciones-publicas/clinical-image_6c.jpg` | Clinical imaging section hero |
| `https://www.redib.net/upload/secciones-publicas/imagen-pet-rm-imaging-la-fe_cr_portada.jpg` (also `_equipamiento.jpg`) | GE SIGNA PET-RM 3T (La Fe) |
| `https://www.redib.net/upload/secciones-publicas/tomografia-computarizada_cr_portada.jpg` (also `_equipamiento.jpg`) | Philips Brilliance iCT 256-detector TAC-MDCT (La Fe) |
| `https://www.redib.net/upload/secciones-publicas/rm-de-3t-philips-achieva-tx_cr_portada.jpg` | Philips Achieva TX 3T (La Fe) — variant |
| `https://www.redib.net/upload/secciones-publicas/rm-de-3t-philips-achieva-tx-muestra-1_cr_portada.jpg` (also `_equipamiento.jpg`) | Philips Achieva TX 3T (La Fe) — primary |
| `https://www.redib.net/upload/secciones-publicas/rm-analisis-dsc-0217_cr_portada.jpg` (also `_equipamiento.jpg`) | Philips Elition 3T (CNIC) |
| `https://www.redib.net/upload/secciones-publicas/pet-tac-analisis-dsc-0348_cr_portada.jpg` (also `_equipamiento.jpg`) | Philips Vereos PET-TAC (CNIC) |
| `https://www.redib.net/upload/secciones-publicas/laboratorio-de-imagenes_cr_portada.jpg` (also `_equipamiento.jpg`) | Laboratorio de imágenes computacionales (La Fe) |

## Image analytics page

| URL | Usage |
| --- | --- |
| `https://www.redib.net/upload/secciones-publicas/imagen-web_6c.jpg` | Analytics section hero |
| `https://www.redib.net/upload/secciones-publicas/analisis-clinicos_6c.jpg` | Analytics section secondary image |

## Team headshots (~14)

| URL | Person |
| --- | --- |
| `https://www.redib.net/upload/secciones-publicas/jrc-biomagune_recorte_foto.jpeg` | Jesús Ruiz-Cabello Osuna (Coordinator) |
| `https://www.redib.net/upload/secciones-publicas/jose-luiz-izquierdo_foto.jpg` | José Luis Izquierdo (BioImaC) |
| `https://www.redib.net/upload/secciones-publicas/borja-ibanez_foto.jpg` | Borja Ibáñez Cabeza (TRIMA-CNIC) |
| `https://www.redib.net/upload/secciones-publicas/foto-gonzalo-olympia-2_foto.jpg` | Gonzalo Pizarro Sánchez (TRIMA-CNIC) |
| `https://www.redib.net/upload/secciones-publicas/luis-marti-bonmati-2_foto.jpg` | Luis Martí-Bonmatí (Imaging La Fe) |
| `https://www.redib.net/upload/secciones-publicas/noam-shemesh-squared-for-web_foto.jpg` | Noam Shemesh (Champalimaud) |
| `https://www.redib.net/upload/secciones-publicas/profile-picture-imarco-2025-cropped_foto.jpeg` | Irene Marco Rius (IBEC) |
| `https://www.redib.net/upload/secciones-publicas/juan-jose-vaquero_foto.png` | Juan José Vaquero (UC3M) |
| `https://www.redib.net/upload/secciones-publicas/foto-visado_foto.jpg` | Eduardo Fraile Moreno |
| `https://www.redib.net/upload/secciones-publicas/thumbnail-image0_foto.jpg` | Lluis Donoso Bach |
| `https://www.redib.net/upload/secciones-publicas/bulte_foto.jpg` | Jeff Bulte (Johns Hopkins) |
| `https://www.redib.net/upload/secciones-publicas/headshot-201702-small_foto.jpeg` | Ryan Tasseff (REDIB Manager) |
| `https://www.redib.net/upload/secciones-publicas/cals_foto.jpg` | Cristina Álvarez de Lara Sánchez |
| `https://www.redib.net/upload/secciones-publicas/foto-ana-penades-2_foto.jpg` | Ana Penadés Blasco |

## News article hero images / thumbnails

These are the thumbnails shown on the news index plus their per-article larger crops.
Many filenames repeat with different size suffixes — listed once per logical source.

| URL | Article |
| --- | --- |
| `https://www.redib.net/upload/secciones-publicas/image0_cr_4w_3h.jpeg` | (news index thumb) |
| `https://www.redib.net/upload/secciones-publicas/imagen1_1_cr_4w_3h.png` | (news index thumb) |
| `https://www.redib.net/upload/secciones-publicas/esc-congress-2025_cr_4w_3h.jpg` | ESC Congress 2025 article |
| `https://www.redib.net/upload/secciones-publicas/picture2_2_cr_4w_3h.png` | (news index thumb) |
| `https://www.redib.net/upload/secciones-publicas/service-portfolio_cr_4w_3h.jpg` | Portafolio article (index thumb) |
| `https://www.redib.net/upload/secciones-publicas/service-portfolio_6c.jpg` | Portafolio article (hero) |
| `https://www.redib.net/upload/secciones-publicas/picture3_3_cr_4w_3h.png` | "Una década" article (index thumb) |
| `https://www.redib.net/upload/secciones-publicas/picture3_3_4c.png` | "Una década" article (hero) |
| `https://www.redib.net/upload/secciones-publicas/picture1_7_cr_4w_3h.png` | Newsletter April 2025 (index thumb) |
| `https://www.redib.net/upload/secciones-publicas/picture1_7_4c.png` | Newsletter April 2025 (hero) |
| `https://www.redib.net/upload/secciones-publicas/timeline-of-redib-2501_cr_4w_3h.png` | Timeline REDIB 2501 article |
| `https://www.redib.net/upload/secciones-publicas/completo_cr_4w_3h.png` | (news index thumb) |

The full ~72-post archive will have additional thumbnails per post that were not
enumerated in detail during this crawl. During migration, a recursive scrape of each
post's page should be done to capture every hero image.

## PDF documents — governance (linked from `/documentacion`)

These are the live governance PDFs and need to be migrated as Wagtail Documents. The
URLs as listed in the source HTML are **filenames only** (with spaces and Spanish
characters) — they resolve under `/upload/...` paths that the crawl did not fully expose.
**Verify exact download URLs at migration time.**

| Document title | Probable code |
| --- | --- |
| REDIB-01-PDA. Reglamento del Comité de Acceso.pdf | REDIB-01 |
| REDIB-02-pda Protocolos de acceso.pdf | REDIB-02 |
| REDIB-03-PDC. Planificación de convocatorias.pdf | REDIB-03 |
| REDIB-04-SYR Gestión de reclamaciones e incidencias.pdf | REDIB-04 |
| REDIB-05-DDP Ejercicio de derechos de datos personales.pdf | REDIB-05 |
| Acuerdo ReDIB de corresponsabilidad para la Gestión de Datos.pdf | (data-sharing agreement) |
| guía de uso del portal de convocatorias.pdf | (portal user guide — Spanish) |

## PDF documents — referenced from individual news articles

| URL | Used on |
| --- | --- |
| `https://www.redib.net/upload/secciones-publicas/redib-coa-portal-user-guide-20260429_1_original.pdf` | "Primera Convocatoria 2026" news article and EN equivalent (most recent COA portal user guide) |
| `https://www.redib.net/upload/secciones-publicas/newsletter-issue-5_original.pdf` | "Boletín informativo mes de Abril 2025" / "April Newsletter 2025" |
| `red-distribuida-de-imagen-biomedica-redib-una-decada-impulsando-la-investigacion-cientifica.pdf` (URL not fully captured) | "Una década" anniversary article (16/04/2025) |

There are likely additional newsletter PDFs (boletines de octubre 2024, noviembre 2024,
diciembre 2024, febrero 2025, enero 2026, etc.) attached to their respective news posts —
these were not individually fetched but should be picked up during full post-by-post
migration.

## Fonts

No custom font files were identified at custom URLs during the crawl. The site appears
to use a standard system font stack (or Google Fonts loaded by the CMS theme — not
audited at this layer). **Recommendation for Phase 1:** audit the CSS to find any
Google Fonts / TypeKit references, then decide whether to self-host in the rebuild.

## Videos

**No videos** were embedded on any crawled page. No YouTube/Vimeo iframes, no `<video>`
tags. The cookie consent panel mentions YouTube as a third-party category — this is the
banner's standard category list, not evidence of actual YouTube embeds.

## Iframes / third-party embeds

**None observed** on public pages. Every node page references "Ubicación en Google maps"
but **no Google Maps iframe is actually present** — these are text references only.
The cookie banner's third-party categories list Google Maps, Facebook, Addthis, and
YouTube, but no actual embeds from those services were found in the markup.

## Image variants / suffix legend (for migration planning)

For each canonical source image, the CMS auto-derives multiple crops named by suffix.
These do **not** need to be migrated as separate assets — Wagtail's `wagtailimages` will
regenerate them from the original. Suffixes seen:

| Suffix | Likely purpose |
| --- | --- |
| `_6c.jpg` | Card / hero — 6-col layout variant |
| `_4c.png` | Card — 4-col variant |
| `_cr_portada.jpg` | "Cropped — front-page" thumbnail |
| `_cr_4w_3h.png` | 4:3 cropped thumbnail (news index) |
| `_equipamiento.jpg` | Equipment-page sized variant |
| `_foto.jpg` | Headshot variant |

When pulling source images for migration, fetch the **largest available** variant per
filename root and let Wagtail generate downstream renditions.
