"""Populate a representative sample of News + Press content (Phase 3d).

Idempotent: safe to run repeatedly.

Scope: 12 paired ES/EN news posts (the full page-1 batch from the current
redib.net) and 12 press items (6 internal posts dated 21/01/2025 and 6
external clippings from 2018-2019). The full ~72-post historical news
archive is deferred — this phase proves the pipeline and seeds enough
content for the index pages to feel populated.

For each NEWS post:
  1. Download the hero image (when available) via the shared image helper.
  2. Find-or-create ES `NewsPage` as a child of `NewsIndexPage(es)`.
  3. Find-or-create EN `NewsPage` via `copy_for_translation(en)` and reparent
     under `NewsIndexPage(en)`.
  Dedup key: (locale, slug). The slug field on each spec is unique within
  the locale.

For each PRESS item:
  1. Find-or-create ES `PressItemPage` as a child of `PressIndexPage(es)`.
  2. External clippings: `external_url` populated; body is brief or empty;
     `outlet` set to the publishing outlet.
  3. Internal items get a normal intro/body; EN translation created where
     paired (the 21/01/2025 internal batch is ES-only on the live site).

Pre-2025 news posts are ES-only per the Phase 0 bilingual audit.
"""
from datetime import date
from html import escape
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from wagtail.images import get_image_model
from wagtail.models import Locale

from marketing.management._image_utils import get_or_create_image
from marketing.models import (
    NewsIndexPage,
    NewsPage,
    PressIndexPage,
    PressItemPage,
)


# ---------------------------------------------------------------------------
# News dataset — 12 paired ES/EN posts (the entire visible page 1 of
# /noticias on www.redib.net). Each spec carries ES + EN sides; EN may be
# None for posts that have no English counterpart on the live site (none
# in this batch, but the loader supports it for future runs).
#
# Field key:
#   date         — datetime.date for both locales
#   slug_es      — child slug under NewsIndexPage(es)
#   slug_en      — child slug under NewsIndexPage(en); None = ES-only
#   title_es / title_en
#   intro_es / intro_en
#   body_es / body_en — HTML strings (RichTextField)
#   hero_url     — original-site asset; '' to skip download
#   hero_slug    — on-disk filename hint
# ---------------------------------------------------------------------------

NEWS_POSTS = [
    {
        'date': date(2026, 4, 20),
        'slug_es': 'la-primera-convocatoria-de-2026-para-el-acceso-abierto-competitivo',
        'slug_en': 'the-first-2026-call-for-competitive-open-access',
        'title_es': (
            'La Primera Convocatoria de 2026 para el Acceso Abierto '
            'Competitivo a las ICTS de ReDIB ya está abierta'
        ),
        'title_en': (
            'The First 2026 Call for Competitive Open Access to ReDIB ICTS '
            'Is Now Open'
        ),
        'intro_es': (
            'Ya está abierta la primera convocatoria de 2026 de Acceso '
            'Abierto Competitivo. ReDIB ofrece a la comunidad científica '
            'acceso a infraestructura avanzada de imagen biomédica clínica '
            'y preclínica a través de su red de nodos.'
        ),
        'intro_en': (
            'The first 2026 Competitive Open Access call is now open. '
            'ReDIB offers the scientific community access to advanced '
            'clinical and preclinical biomedical imaging infrastructure '
            'across its network of nodes.'
        ),
        'body_es': (
            '<p>El siguiente equipamiento está disponible para estudios de '
            'investigación:</p>'
            '<p><strong>BioImaC</strong></p>'
            '<ul>'
            '<li>RM 1T Bruker ICON</li>'
            '<li>PET-RM 9.4T Bruker BioSpec con CryoProbe</li>'
            '</ul>'
            '<p><strong>CIC biomaGUNE</strong></p>'
            '<ul>'
            '<li>RM 7T Bruker BioSpec</li>'
            '<li>RM 11.7T Bruker BioSpec</li>'
            '<li>Sistema multimodal PET/SPECT/CT Molecubes</li>'
            '<li>Sistema multimodal PET/SPECT/CT/OI MILabs VECtor</li>'
            '<li>Ciclotrón IBA 9/18</li>'
            '<li>Laboratorio de Radioquímica</li>'
            '</ul>'
            '<p><strong>IIS-La Fe</strong></p>'
            '<ul>'
            '<li>RM 3T Philips Achieva TX (MultiTransmit)</li>'
            '<li>PET-RM 3T General Electric SIGNA</li>'
            '</ul>'
            '<p><strong>TRIMA-CNIC</strong></p>'
            '<ul>'
            '<li>RM 3T Philips Elition</li>'
            '<li>RM 7T Agilent-Varian</li>'
            '<li>PET-TAC Philips Vereos</li>'
            '<li>Sistema modular PET, SPECT y TAC Molecubes</li>'
            '</ul>'
            '<p>Las solicitudes pueden presentarse a través del '
            '<a href="https://portal.redib.net/calls/1/">portal de '
            'convocatorias de ReDIB para la 2601</a>.</p>'
        ),
        'body_en': (
            '<p>The following equipment is available for studies:</p>'
            '<p><strong>BioImaC</strong></p>'
            '<ul>'
            '<li>MRI 1T Bruker ICON</li>'
            '<li>PET/MRI 9.4T Bruker BioSpec with CryoProbe</li>'
            '</ul>'
            '<p><strong>CIC biomaGUNE</strong></p>'
            '<ul>'
            '<li>MRI 7T Bruker BioSpec</li>'
            '<li>MRI 11.7T Bruker BioSpec</li>'
            '<li>PET/SPECT/CT multimodal system Molecubes</li>'
            '<li>PET/SPECT/CT/OI multimodal system MILabs VECtor</li>'
            '<li>Cyclotron IBA 9/18</li>'
            '<li>Radiochemistry Laboratory</li>'
            '</ul>'
            '<p><strong>IIS-La Fe</strong></p>'
            '<ul>'
            '<li>MRI 3T Philips Achieva TX (MultiTransmit)</li>'
            '<li>PET/MRI 3T General Electric SIGNA</li>'
            '</ul>'
            '<p><strong>TRIMA-CNIC</strong></p>'
            '<ul>'
            '<li>MRI 3T Philips Elition</li>'
            '<li>MRI 7T Agilent-Varian</li>'
            '<li>PET/CT Philips Vereos</li>'
            '<li>Modular PET, SPECT and CT imaging system Molecubes</li>'
            '</ul>'
            '<p>Applications can be submitted through the '
            '<a href="https://portal.redib.net/calls/1/">ReDIB call '
            'portal for 2601</a>.</p>'
        ),
        'hero_url': '',
        'hero_slug': '',
    },
    {
        'date': date(2026, 1, 27),
        'slug_es': 'redib-se-renueva-en-el-mapa-icts-2025-2028-boletin-enero-2026',
        'slug_en': 'redib-renewed-in-the-icts-map-2025-2028-jan-2026-newsletter',
        'title_es': (
            'ReDIB se renueva en el Mapa ICTS (2025-2028) y más en el '
            'Boletín de enero de 2026'
        ),
        'title_en': (
            'ReDIB renewed in the ICTS Map (2025–2028) and more in the '
            '2026 Jan Newsletter'
        ),
        'intro_es': (
            'Nuestro boletín de enero de 2026 destaca la renovación de '
            'ReDIB en el Mapa nacional de ICTS para el periodo 2025–2028, '
            'reforzando el papel de las ICTS distribuidas en la capacidad '
            'nacional de imagen biomédica.'
        ),
        'intro_en': (
            "ReDIB's renewed inclusion in Spain's national ICTS Map for "
            "2025–2028 reinforces the role of distributed infrastructures "
            "in strengthening biomedical imaging capacity. The January "
            "2026 newsletter also covers governance updates, advisory "
            "committee expansion, and recent outreach."
        ),
        'body_es': (
            '<p>El boletín cubre además novedades de gobernanza y la '
            'ampliación del Comité Asesor Científico-Técnico, junto con '
            'hitos comunitarios y actividades de divulgación recientes.</p>'
            '<p>La versión completa del boletín está disponible para '
            'descarga desde la sección de Documentación.</p>'
        ),
        'body_en': (
            '<p>The newsletter also covers governance updates and the '
            'expansion of the Scientific-Technical Advisory Committee, '
            'alongside community milestones and recent outreach '
            'activities.</p>'
            '<p>The full newsletter PDF is available for download from '
            'the Documentation section.</p>'
        ),
        'hero_url': '',
        'hero_slug': '',
    },
    {
        'date': date(2025, 12, 22),
        'slug_es': 'redib-en-bsifs2025-puentes-ciencia-imagen-industria',
        'slug_en': 'redib-at-bsifs2025-bridges-imaging-science-industry',
        'title_es': (
            'ReDIB en BSIFS2025: fortaleciendo los puentes entre la '
            'ciencia de imagen y la industria'
        ),
        'title_en': (
            'ReDIB at BSIFS2025: strengthening bridges between imaging '
            'science and industry'
        ),
        'intro_es': (
            'ReDIB participó en el Big Science Industry Forum Spain 2025, '
            'un encuentro nacional para reforzar la conexión entre los '
            'actores científico-industriales, los grupos de investigación '
            'y las ICTS, mediante networking y una exposición industrial.'
        ),
        'intro_en': (
            'ReDIB took part in the Big Science Industry Forum Spain '
            '2025, a national meeting designed to strengthen the '
            'connection between scientific-industrial stakeholders, '
            'research groups and ICTS through networking and an '
            'industry-facing exhibition.'
        ),
        'body_es': (
            '<p>Durante el foro, celebrado el 3 y 4 de diciembre de 2025 '
            'en el Centro de Convenciones Norte de IFEMA (Madrid), ReDIB '
            'representó a la comunidad ICTS en un stand conjunto y '
            'presentó un póster destacando su papel como motor de '
            'transferencia de conocimiento científico y tecnológico en '
            'imagen biomédica.</p>'
            '<p>El póster resumió los logros del periodo 2021–2024: 178 '
            'colaboraciones científico-técnicas con 338 entidades de 27 '
            'países, 318 proyectos científico-técnicos apoyados, 215 '
            'artículos en revistas indexadas y 22 patentes o derechos '
            'de propiedad intelectual.</p>'
            '<p>La misión de ReDIB se centra en proporcionar acceso '
            'abierto competitivo a servicios de imagen biomédica que '
            'cubren desde lo molecular hasta lo clínico, a través de '
            'una red distribuida de cuatro nodos en España que funciona '
            'como ventanilla única.</p>'
        ),
        'body_en': (
            '<p>The forum was held on 3–4 December 2025 at the IFEMA '
            'Convention Center North in Madrid. ReDIB represented the '
            'ICTS community at a shared booth and presented a poster '
            'highlighting its role as a driver of scientific and '
            'technological knowledge transfer in biomedical imaging.</p>'
            '<p>The poster summarised 2021–2024 achievements: 178 '
            'scientific-technical collaborations involving 338 entities '
            'across 27 countries, 318 supported scientific-technical '
            'projects, 215 indexed-journal articles and 22 patents or '
            'IP rights.</p>'
            "<p>ReDIB's mission centres on Competitive Open Access "
            "biomedical imaging services spanning molecular through "
            "clinical applications, delivered through a distributed "
            "four-node network in Spain operating as a single-window "
            "facility.</p>"
        ),
        'hero_url': (
            'https://www.redib.net/upload/secciones-publicas/'
            'image0_12c.jpeg'
        ),
        'hero_slug': 'news-bsifs2025-hero',
    },
    {
        'date': date(2025, 10, 13),
        'slug_es': 'taller-sobre-rm-con-agentes-hiperpolarizados',
        'slug_en': 'workshop-on-mri-with-hyperpolarized-agents',
        'title_es': 'Taller sobre RM con Agentes Hiperpolarizados',
        'title_en': 'Workshop on MRI with Hyperpolarized Agents',
        'intro_es': (
            'El Workshop on MRI with Hyperpolarized Agents, celebrado el '
            '25 de septiembre de 2025 en BioImaC (Madrid), fue todo un '
            'éxito.'
        ),
        'intro_en': (
            'The Workshop on MRI with Hyperpolarized Agents, held on '
            '25 September 2025 at BioImaC (Madrid), was a great success.'
        ),
        'body_es': (
            '<p>El taller reunió a destacados expertos del ámbito '
            'académico e industrial para debatir los avances recientes '
            'en resonancia magnética con agentes hiperpolarizados y sus '
            'aplicaciones biomédicas. Los asistentes disfrutaron de '
            'ponencias inspiradoras, discusiones interactivas y '
            'oportunidades de networking para futuras colaboraciones.</p>'
            '<p>Desde ReDIB y sus nodos asociados nos enorgullece seguir '
            'fomentando la colaboración y la innovación en la comunidad '
            'de imagen biomédica. Gracias a todas las personas '
            'ponentes, participantes y colaboradoras.</p>'
        ),
        'body_en': (
            '<p>The workshop gathered leading academic and industry '
            'experts to discuss recent advances in hyperpolarized MRI '
            'and its biomedical applications. Attendees enjoyed '
            'insightful talks, interactive discussions and valuable '
            'networking opportunities for future partnerships.</p>'
            '<p>ReDIB and its affiliated nodes remain committed to '
            'advancing cooperation and innovation within the biomedical '
            'imaging community. Thanks to every speaker, participant '
            'and collaborator who made the event a success.</p>'
        ),
        'hero_url': '',
        'hero_slug': '',
    },
    {
        'date': date(2025, 8, 30),
        'slug_es': 'nejm-the-lancet-ensayo-reboot-cnic-infarto',
        'slug_en': 'nejm-the-lancet-cnic-reboot-trial-heart-attack',
        'title_es': (
            'NEJM & The Lancet: el ensayo REBOOT, liderado por el CNIC, '
            'modifica una práctica médica vigente desde hace más de 40 '
            'años en el manejo del infarto'
        ),
        'title_en': (
            'NEJM & The Lancet: CNIC-led REBOOT clinical trial '
            'challenges 40-year-old standard of care for heart attack '
            'patients'
        ),
        'intro_es': (
            'El ensayo REBOOT, un estudio clínico de referencia '
            'liderado por el CNIC, desafía una práctica vigente desde '
            'hace décadas al demostrar que los betabloqueantes pueden '
            'no ser necesarios en pacientes de infarto con función '
            'cardiaca preservada.'
        ),
        'intro_en': (
            'The REBOOT trial, a landmark clinical study led by CNIC, '
            'challenges decades-old medical practice by showing that '
            'beta-blockers may not be necessary for all heart attack '
            'patients with preserved heart function.'
        ),
        'body_es': (
            '<p>REBOOT incluyó 8.505 pacientes con fracción de eyección '
            'ventricular izquierda superior al 40% tras un infarto de '
            'miocardio, en 109 hospitales de España e Italia. Los '
            'participantes fueron asignados aleatoriamente a recibir '
            'o no betabloqueantes al alta, dentro del tratamiento '
            'estándar actual, con un seguimiento medio cercano a los '
            'cuatro años.</p>'
            '<p>Los resultados no mostraron diferencias significativas '
            'entre los dos grupos en mortalidad, reinfarto u '
            'hospitalización por insuficiencia cardiaca, lo que sugiere '
            'que los protocolos vigentes con betabloqueantes pueden '
            'requerir revisión en esta población.</p>'
            '<p>El investigador principal, Dr. Borja Ibáñez, director '
            'científico del CNIC y cardiólogo en el Hospital '
            'Universitario Fundación Jiménez Díaz, afirmó: "REBOOT '
            'cambiará la práctica clínica en todo el mundo".</p>'
        ),
        'body_en': (
            '<p>The REBOOT (Treatment with Beta-Blockers after '
            'Myocardial Infarction without Reduced Ejection Fraction) '
            'trial enrolled 8,505 patients across 109 hospitals in '
            'Spain and Italy. All participants received standard care '
            'and were monitored for an average of nearly four years; '
            'no significant differences emerged between the '
            'beta-blocker and no-beta-blocker arms in mortality, '
            'reinfarction or hospitalisation for heart failure.</p>'
            '<p>Dr. Borja Ibáñez, principal investigator and CNIC '
            'Scientific Director, notes that "REBOOT will change '
            'treatment in these cases worldwide, since until now more '
            'than 80% of patients with uncomplicated heart attacks '
            'are discharged with beta-blocker treatment." He serves '
            'as a cardiologist at Hospital Universitario Fundación '
            'Jiménez Díaz and leads a research group at CIBERCV.</p>'
        ),
        'hero_url': (
            'https://www.redib.net/upload/secciones-publicas/'
            'imagen1_1_12c.png'
        ),
        'hero_slug': 'news-reboot-hero',
    },
    {
        'date': date(2025, 8, 30),
        'slug_es': 'ehj-mujeres-betabloqueantes-peor-pronostico-infarto',
        'slug_en': 'ehj-women-worse-prognosis-beta-blockers-heart-attack',
        'title_es': (
            'EHJ: un nuevo estudio revela que, tras un infarto, las '
            'mujeres tienen un peor pronóstico cuando se tratan con '
            'betabloqueantes'
        ),
        'title_en': (
            'EHJ: New study finds that, after a heart attack, women '
            'have worse prognosis when treated with beta-blockers'
        ),
        'intro_es': (
            'Un análisis del ensayo REBOOT, coordinado por el CNIC y '
            'publicado en European Heart Journal, identifica '
            'diferencias importantes entre sexos en la respuesta a los '
            'betabloqueantes tras un infarto, con implicaciones para '
            'la práctica clínica actual.'
        ),
        'intro_en': (
            'A major analysis of the international REBOOT trial, '
            'coordinated by CNIC and published in European Heart '
            'Journal, reveals significant sex-specific differences in '
            'how beta-blockers affect heart-attack patients — '
            'challenging long-established practice.'
        ),
        'body_es': (
            '<p>El estudio examinó los resultados con betabloqueantes '
            'tras un infarto sin fracción de eyección reducida y '
            'reveló efectos contrastados por sexo: los hombres no '
            'mostraron ni beneficio ni perjuicio, mientras que las '
            'mujeres tratadas con estos fármacos presentaron un riesgo '
            'significativamente mayor de muerte, reinfarto u '
            'hospitalización por insuficiencia cardiaca.</p>'
            '<p>A lo largo del seguimiento medio de 3,7 años, las '
            'mujeres que recibieron betabloqueantes mostraron un riesgo '
            'absoluto de mortalidad 2,7% superior al de las que no los '
            'recibieron, lo que cuestiona los protocolos de tratamiento '
            'estándar en pacientes cardiacas.</p>'
        ),
        'body_en': (
            '<p>Researchers identified notable disparities between '
            'sexes in treatment outcomes following myocardial '
            'infarction without reduced ejection fraction. While men '
            'experienced neither benefit nor risk from beta-blocker '
            'treatment, women treated with these drugs showed a '
            'significantly increased risk of death, reinfarction or '
            'heart failure hospitalisation versus untreated women.</p>'
            '<p>Over the 3.7-year follow-up, women receiving '
            'beta-blockers showed a 2.7% greater absolute mortality '
            'risk than those who did not — raising questions about '
            'standard treatment protocols for female cardiac '
            'patients.</p>'
        ),
        'hero_url': (
            'https://www.redib.net/upload/secciones-publicas/'
            'esc-congress-2025_4c.jpg'
        ),
        'hero_slug': 'news-ehj-women-hero',
    },
    {
        'date': date(2025, 5, 28),
        'slug_es': 'dialogo-con-valentin-fuster-siempre-adelante',
        'slug_en': 'dialogue-with-valentin-fuster-always-forward',
        'title_es': 'Diálogo con Valentín Fuster: ¡Siempre adelante!',
        'title_en': 'Dialogue with Valentín Fuster: Always forward!',
        'intro_es': (
            'Una conversación abierta con el cardiólogo Valentín '
            'Fuster sobre el papel de la investigación cardiovascular '
            'y el futuro de la imagen biomédica en España.'
        ),
        'intro_en': (
            'An open conversation with cardiologist Valentín Fuster '
            'about the role of cardiovascular research and the future '
            'of biomedical imaging in Spain.'
        ),
        'body_es': (
            '<p>El encuentro, organizado en el marco de las actividades '
            'comunitarias de ReDIB, reunió al Prof. Valentín Fuster '
            'con investigadores e investigadoras de la red para '
            'abordar el futuro de la imagen cardiovascular y la '
            'relación entre infraestructuras singulares y formación '
            'de jóvenes científicos.</p>'
        ),
        'body_en': (
            '<p>The event, organised as part of the ReDIB community '
            "activities, brought Prof. Valentín Fuster together with "
            "the network's researchers to discuss the future of "
            'cardiovascular imaging and the relationship between '
            'singular infrastructures and the training of early-career '
            'scientists.</p>'
        ),
        'hero_url': (
            'https://www.redib.net/upload/secciones-publicas/'
            'picture2_2_6c.png'
        ),
        'hero_slug': 'news-valentin-fuster-hero',
    },
    {
        'date': date(2025, 5, 28),
        'slug_es': 'portafolio-de-servicios-de-imagen-biomedica',
        'slug_en': 'portfolio-of-biomedical-imaging-services',
        'title_es': 'Portafolio de servicios de imagen biomédica',
        'title_en': 'Portfolio of biomedical imaging services',
        'intro_es': (
            'ReDIB proporciona a la comunidad científica acceso a una '
            'cartera integral de servicios de imagen avanzada y '
            'plataformas de última generación.'
        ),
        'intro_en': (
            'ReDIB provides the scientific community with access to a '
            'comprehensive portfolio of advanced imaging services and '
            'state-of-the-art platforms.'
        ),
        'body_es': (
            '<p>El portafolio cubre imagen clínica, preclínica, '
            'radioquímica y servicios de análisis. Está pensado para '
            'que los grupos de investigación académicos e industriales '
            'puedan combinar las modalidades que mejor se ajusten a '
            'cada proyecto, con soporte experto en todas las fases.</p>'
            '<p>El documento completo está disponible en la sección '
            'de Documentación.</p>'
        ),
        'body_en': (
            '<p>The portfolio spans clinical imaging, preclinical '
            'imaging, radiochemistry and image-analysis services. It is '
            'designed so that academic and industry research groups can '
            'combine the modalities that best fit their project, with '
            'expert support across all phases.</p>'
            '<p>The full document is available in the Documentation '
            'section.</p>'
        ),
        'hero_url': (
            'https://www.redib.net/upload/secciones-publicas/'
            'service-portfolio_6c.jpg'
        ),
        'hero_slug': 'news-service-portfolio-hero',
    },
    {
        'date': date(2025, 4, 16),
        'slug_es': 'redib-una-decada-impulsando-la-investigacion-cientifica',
        'slug_en': 'redib-a-decade-promoting-scientific-research',
        'title_es': (
            'Red Distribuida de Imagen Biomédica (ReDIB): una década '
            'impulsando la investigación científica'
        ),
        'title_en': (
            'Distributed Biomedical Imaging Network (ReDIB): a decade '
            'promoting scientific research'
        ),
        'intro_es': (
            'En los últimos diez años, la Red Distribuida de Imagen '
            'Biomédica (ReDIB) ha consolidado su posición como una '
            'infraestructura esencial para la investigación biomédica '
            'en España.'
        ),
        'intro_en': (
            'Over the last ten years, the Distributed Biomedical '
            'Imaging Network (ReDIB) has consolidated its position as '
            'a vital infrastructure for biomedical research in Spain.'
        ),
        'body_es': (
            '<p>ReDIB se ha establecido como una infraestructura '
            'crítica para la investigación biomédica en España y '
            'ofrece acceso a tecnologías punteras de imagen a '
            'investigadores nacionales e internacionales.</p>'
            '<p>La red, coordinada por el CNIC y financiada como ICTS '
            'por el Ministerio de Ciencia, Innovación y Universidades, '
            'ha eliminado barreras de acceso a tecnologías costosas y '
            'especializadas, democratizando capacidades de imagen que '
            'serían inalcanzables para muchos grupos por sí solos.</p>'
            '<p>Una década después, su impacto se refleja en la '
            'producción científica, la transferencia tecnológica y la '
            'formación de personal experto a nivel español y '
            'europeo.</p>'
        ),
        'body_en': (
            '<p>ReDIB provides access to advanced biomedical imaging '
            'technologies for national and international researchers. '
            "The network is coordinated by Spain's National Centre for "
            'Cardiovascular Research (CNIC) and funded as a Unique '
            'Scientific-Technical Infrastructure (ICTS).</p>'
            '<p>By making expensive and specialised imaging equipment '
            'accessible, ReDIB has removed barriers that previously '
            'hindered scientific progress. The distributed model '
            'enables groups across multiple institutions to use '
            'cutting-edge technologies without duplicating expensive '
            'infrastructure investments.</p>'
            '<p>A decade in, the impact shows in scientific output, '
            'technology transfer and the training of expert staff at '
            'both Spanish and European levels.</p>'
        ),
        'hero_url': (
            'https://www.redib.net/upload/secciones-publicas/'
            'picture3_3_4c.png'
        ),
        'hero_slug': 'news-decade-hero',
    },
    {
        'date': date(2025, 4, 15),
        'slug_es': 'boletin-informativo-mes-de-abril-2025',
        'slug_en': 'april-newsletter-2025',
        'title_es': 'Boletín informativo: abril 2025',
        'title_en': 'April Newsletter 2025',
        'intro_es': (
            'Quinto número del boletín informativo de ReDIB, centrado '
            'en la Convocatoria de Acceso Abierto Competitivo REDIB '
            '2501.'
        ),
        'intro_en': (
            "Fifth issue of the ReDIB newsletter, focused on the "
            "Competitive Open Access Call REDIB 2501."
        ),
        'body_es': (
            '<p>El boletín de abril de 2025 recoge las novedades de la '
            'convocatoria abierta y un repaso de las actividades '
            'recientes de la red.</p>'
            '<p>Documento completo disponible para descarga (PDF) en '
            'la sección de Documentación.</p>'
        ),
        'body_en': (
            '<p>The April 2025 newsletter compiles updates on the open '
            "call and a recap of the network's recent activities.</p>"
            '<p>The full PDF is available for download in the '
            'Documentation section.</p>'
        ),
        'hero_url': (
            'https://www.redib.net/upload/secciones-publicas/'
            'picture1_7_4c.png'
        ),
        'hero_slug': 'news-newsletter-apr2025-hero',
    },
    {
        'date': date(2025, 3, 28),
        'slug_es': 'linea-temporal-convocatoria-acceso-abierto-redib-2501',
        'slug_en': 'timeline-for-redib-2501-competitive-open-access-call',
        'title_es': (
            'Línea temporal para la convocatoria de Acceso Abierto '
            'Competitivo REDIB 2501'
        ),
        'title_en': (
            'Timeline for REDIB 2501 Competitive Open Access Call'
        ),
        'intro_es': (
            'ReDIB ofrece acceso a 16 instalaciones de imagen '
            'esenciales y 49 tecnologías biomédicas. La primera '
            'convocatoria de Acceso Abierto Competitivo de 2025 '
            '(REDIB 2501) se abre el 1 de abril.'
        ),
        'intro_en': (
            'ReDIB offers access to 16 essential imaging facilities '
            'and 49 biomedical technologies. The first 2025 '
            'Competitive Open Access call (REDIB 2501) opens on '
            '1 April.'
        ),
        'body_es': (
            '<p>La convocatoria REDIB 2501 permite a investigadores '
            'nacionales e internacionales acceder a tecnologías y '
            'servicios avanzados en imagen biomédica clínica y '
            'preclínica a precios competitivos y con apoyo '
            'logístico.</p>'
            '<p>El personal experto de cada nodo proporciona '
            'acompañamiento integral en todas las fases del proyecto: '
            'diseño del estudio, adquisición de imágenes y análisis. '
            'El protocolo de acceso es sencillo y todos los estudios '
            'se realizan en instalaciones certificadas que garantizan '
            'la calidad y reproducibilidad de los datos.</p>'
        ),
        'body_en': (
            '<p>The REDIB 2501 call lets domestic and international '
            'researchers use advanced technologies and services in '
            'clinical and preclinical biomedical imaging at '
            'competitive pricing with logistical support.</p>'
            '<p>Expert staff at each node provide comprehensive '
            'guidance throughout the research process — study design, '
            'image acquisition and analysis. The access protocol is '
            'straightforward; all studies are conducted in certified '
            'facilities that ensure quality and data '
            'reproducibility.</p>'
        ),
        'hero_url': (
            'https://www.redib.net/upload/secciones-publicas/'
            'timeline-of-redib-2501_12c.png'
        ),
        'hero_slug': 'news-timeline-2501-hero',
    },
    {
        'date': date(2025, 3, 20),
        'slug_es': 'jornada-colaboracion-infraestructuras-nacionales-europeas-embrc',
        'slug_en': 'working-day-on-collaboration-national-european-infrastructures-embrc',
        'title_es': (
            'Jornada de trabajo sobre oportunidades de colaboración '
            'entre infraestructuras nacionales y europeas (EMBRC)'
        ),
        'title_en': (
            'Working Day on Opportunities for Collaboration between '
            'National and European Infrastructures (EMBRC)'
        ),
        'intro_es': (
            'Discusión y análisis sobre la sostenibilidad de las '
            'infraestructuras de investigación, las nuevas tecnologías '
            'en el campo de la imagen y las ómicas, y la colaboración '
            'con infraestructuras de investigación europeas.'
        ),
        'intro_en': (
            'Discussion and analysis on the sustainability of research '
            'infrastructures, new technologies in imaging and omics, '
            'and collaboration with European research infrastructures.'
        ),
        'body_es': (
            '<p>La jornada reunió a representantes de varias ICTS y '
            'de infraestructuras europeas (EMBRC) para identificar '
            'oportunidades concretas de colaboración y trazar un '
            'mapa común de capacidades.</p>'
        ),
        'body_en': (
            '<p>The working day brought together representatives from '
            'several Spanish ICTS and European research infrastructures '
            '(EMBRC) to identify concrete collaboration opportunities '
            'and map shared capabilities.</p>'
        ),
        'hero_url': (
            'https://www.redib.net/upload/secciones-publicas/'
            'completo_12c.png'
        ),
        'hero_slug': 'news-embrc-hero',
    },
]


# ---------------------------------------------------------------------------
# Press dataset — 12 items.
#   Items 1–6: ES-only internal posts dated 21/01/2025. Per the Phase 0
#   bilingual audit, these are not paired in the live site so we leave EN
#   empty. external_url is empty; intro/body summarise the original.
#   Items 7–12: external clippings from 2018–2019. external_url set;
#   outlet populated; body intentionally brief — the user-facing UX is
#   "read the original at <outlet>".
# ---------------------------------------------------------------------------

PRESS_ITEMS = [
    # ---- Internal posts (ES-only) -------------------------------------
    {
        'date': date(2025, 1, 21),
        'slug_es': 'jornada-abierta-imagen-medica-hospital-la-fe-valencia',
        'slug_en': None,
        'title_es': (
            'Jornada abierta de imagen médica en el Hospital La Fe, '
            'Valencia'
        ),
        'title_en': '',
        'outlet': 'ReDIB',
        'external_url': '',
        'intro_es': (
            'El nodo Imaging La Fe organiza una jornada divulgativa '
            'sobre imagen médica avanzada, abierta a la comunidad '
            'académica y hospitalaria de Valencia.'
        ),
        'intro_en': '',
        'body_es': (
            '<p>El nodo Imaging La Fe, integrado en el Hospital '
            'Universitario y Politécnico La Fe de Valencia, organiza '
            'una jornada abierta de divulgación sobre las capacidades '
            'de imagen médica avanzada disponibles en ReDIB.</p>'
        ),
        'body_en': '',
    },
    {
        'date': date(2025, 1, 21),
        'slug_es': 'dia-mundial-del-corazon',
        'slug_en': None,
        'title_es': 'Día Mundial del Corazón',
        'title_en': '',
        'outlet': 'ReDIB',
        'external_url': '',
        'intro_es': (
            'ReDIB se suma a la conmemoración del Día Mundial del '
            'Corazón con actividades de divulgación coordinadas con '
            'el nodo TRIMA @ CNIC.'
        ),
        'intro_en': '',
        'body_es': (
            '<p>Con motivo del Día Mundial del Corazón, ReDIB y su '
            'nodo TRIMA @ CNIC contribuyen a la difusión del papel '
            'de la imagen cardiovascular en la investigación y el '
            'diagnóstico.</p>'
        ),
        'body_en': '',
    },
    {
        'date': date(2025, 1, 21),
        'slug_es': 'congreso-sociedad-europea-cardiologia',
        'slug_en': None,
        'title_es': 'Congreso de la Sociedad Europea de Cardiología',
        'title_en': '',
        'outlet': 'ReDIB',
        'external_url': '',
        'intro_es': (
            'Presencia de ReDIB y su nodo TRIMA @ CNIC en el congreso '
            'anual de la Sociedad Europea de Cardiología.'
        ),
        'intro_en': '',
        'body_es': (
            '<p>ReDIB participó en el congreso anual de la Sociedad '
            'Europea de Cardiología (ESC), donde el nodo TRIMA @ CNIC '
            'presentó resultados de proyectos colaborativos en imagen '
            'cardiovascular.</p>'
        ),
        'body_en': '',
    },
    {
        'date': date(2025, 1, 21),
        'slug_es': 'servicio-rmn-3t-nodo-trima-cnic',
        'slug_en': None,
        'title_es': 'Servicio de RMN 3 T en el nodo TRIMA @ CNIC',
        'title_en': '',
        'outlet': 'ReDIB',
        'external_url': '',
        'intro_es': (
            'TRIMA @ CNIC pone en operación su servicio de RMN clínica '
            '3 T, ampliando la oferta de imagen cardiovascular del '
            'nodo madrileño.'
        ),
        'intro_en': '',
        'body_es': (
            '<p>El nodo TRIMA @ CNIC pone en marcha su servicio '
            'clínico de resonancia magnética 3 T (Philips Elition), '
            'ampliando significativamente la oferta de imagen '
            'cardiovascular en el campus madrileño y reforzando la '
            'capacidad translacional de la red.</p>'
        ),
        'body_en': '',
    },
    {
        'date': date(2025, 1, 21),
        'slug_es': 'adquision-94t-mri-bruker-biospec-9430-bioimac',
        'slug_en': None,
        'title_es': (
            'Adquisición de nuevas infraestructuras: 9.4T-MRI Bruker '
            'BIOSPEC 94/30 en el nodo BioImaC'
        ),
        'title_en': '',
        'outlet': 'ReDIB',
        'external_url': '',
        'intro_es': (
            'BioImaC incorpora un sistema PET-RM 9,4 T Bruker BioSpec '
            'con CryoProbe, reforzando la oferta de imagen molecular '
            'preclínica de alto campo de la red ReDIB.'
        ),
        'intro_en': '',
        'body_es': (
            '<p>El nodo BioImaC suma a su parque instrumental un '
            'sistema híbrido PET-RM 9,4 T Bruker BioSpec con '
            'CryoProbe. Esta adquisición refuerza la oferta de imagen '
            'molecular preclínica de alto campo a nivel nacional y '
            'amplía las capacidades disponibles para investigación '
            'académica e industrial.</p>'
        ),
        'body_en': '',
    },
    {
        'date': date(2025, 1, 21),
        'slug_es': 'actualizacion-mapa-icts-2025-2028',
        'slug_en': None,
        'title_es': 'Actualización del Mapa de ICTS 2025-2028',
        'title_en': '',
        'outlet': 'ReDIB',
        'external_url': '',
        'intro_es': (
            'ReDIB se mantiene en el Mapa nacional de Infraestructuras '
            'Científicas y Técnicas Singulares para el periodo '
            '2025–2028.'
        ),
        'intro_en': '',
        'body_es': (
            '<p>El Ministerio de Ciencia, Innovación y Universidades '
            'aprueba la actualización del Mapa de ICTS 2025-2028, '
            'que renueva la inclusión de ReDIB como infraestructura '
            'distribuida de imagen biomédica de referencia '
            'nacional.</p>'
        ),
        'body_en': '',
    },

    # ---- External clippings (no body) ---------------------------------
    {
        'date': date(2019, 2, 27),
        'slug_es': 'clip-ciencia-2019-foro-transfiere',
        'slug_en': None,
        'title_es': (
            'Un año más, las Infraestructuras Científicas y Técnicas '
            'Singulares estuvieron en el foro Transfiere'
        ),
        'title_en': '',
        'outlet': 'Ministerio de Ciencia, Innovación y Universidades',
        'external_url': (
            'http://www.ciencia.gob.es/portal/site/MICINN/'
            'menuitem.edc7f2029a2be27d7010721001432ea0/'
            '?vgnextoid=f261b28527009610VgnVCM1000001d04140aRCRD'
        ),
        'intro_es': (
            'Las ICTS, ReDIB entre ellas, vuelven a estar presentes '
            'en el foro europeo de innovación Transfiere.'
        ),
        'intro_en': '',
        'body_es': '',
        'body_en': '',
    },
    {
        'date': date(2018, 12, 18),
        'slug_es': 'clip-micinn-reunion-directores-mapa-icts',
        'slug_en': None,
        'title_es': (
            'Reunión de directores del nuevo Mapa de ICTS'
        ),
        'title_en': '',
        'outlet': 'MICINN',
        'external_url': (
            'http://www.ciencia.gob.es/portal/site/MICINN/'
            'menuitem.edc7f2029a2be27d7010721001432ea0/'
            '?vgnextoid=4ecfead4920c7610VgnVCM1000001d04140aRCRD'
        ),
        'intro_es': (
            'Encuentro de directores de las ICTS para coordinar la '
            'puesta en marcha del nuevo Mapa nacional.'
        ),
        'intro_en': '',
        'body_es': '',
        'body_en': '',
    },
    {
        'date': date(2018, 12, 3),
        'slug_es': 'clip-iislafe-imaging-la-fe-icts-hospitalaria',
        'slug_en': None,
        'title_es': (
            'La Fe se convierte en la primera infraestructura '
            'científica y técnica singular española de base '
            'hospitalaria con la iniciativa Imaging La Fe'
        ),
        'title_en': '',
        'outlet': 'Instituto de Investigación Sanitaria La Fe',
        'external_url': (
            'https://www.iislafe.es/es/actualidad/noticias/2985/'
            'la-fe-se-convierte-en-la-primera-infraestructura-'
            'cientifica-y-tecnica-singular-espanola-de-base-'
            'hospitalaria-con-la-iniciativa-imaging-la-fe'
        ),
        'intro_es': (
            'El Hospital Universitario y Politécnico La Fe pasa a ser '
            'la primera ICTS española de base hospitalaria, a través '
            'de su iniciativa Imaging La Fe integrada en ReDIB.'
        ),
        'intro_en': '',
        'body_es': '',
        'body_en': '',
    },
    {
        'date': date(2018, 12, 3),
        'slug_es': 'clip-colvema-hcv-complutense-nodo-icts',
        'slug_en': None,
        'title_es': (
            'El Servicio de Diagnóstico por Imagen del HCV '
            'Complutense, nuevo nodo de la Red nacional de ICTS'
        ),
        'title_en': '',
        'outlet': 'Colegio Oficial de Veterinarios de Madrid',
        'external_url': (
            'https://www.colvema.org/'
            'listado-noticia-detalle.asp?cod_noticia=11172'
        ),
        'intro_es': (
            'El servicio de imagen del Hospital Clínico Veterinario '
            'Complutense se incorpora a la red nacional de ICTS '
            'dentro de ReDIB.'
        ),
        'intro_en': '',
        'body_es': '',
        'body_en': '',
    },
    {
        'date': date(2018, 11, 13),
        'slug_es': 'clip-lavanguardia-la-fe-primera-icts-hospitalaria',
        'slug_en': None,
        'title_es': (
            'El Hospital La Fe de Valencia, primera ICTS española con '
            'base hospitalaria'
        ),
        'title_en': '',
        'outlet': 'La Vanguardia',
        'external_url': (
            'https://www.lavanguardia.com/local/valencia/20181113/'
            '452905294824/el-hospital-la-fe-de-valencia-primera-icts-'
            'espanola-con-base-hospitalaria.html'
        ),
        'intro_es': (
            'La Vanguardia recoge el reconocimiento del Hospital La '
            'Fe como primera ICTS española de base hospitalaria '
            'dentro de la red ReDIB.'
        ),
        'intro_en': '',
        'body_es': '',
        'body_en': '',
    },
    {
        'date': date(2018, 11, 8),
        'slug_es': 'clip-micinn-consejo-aprueba-actualizacion-icts',
        'slug_en': None,
        'title_es': (
            'El Consejo de Política Científica, Tecnológica y de '
            'Innovación aprueba la actualización del Mapa de ICTS'
        ),
        'title_en': '',
        'outlet': 'Ministerio de Ciencia, Innovación y Universidades',
        'external_url': (
            'http://www.ciencia.gob.es/portal/site/MICINN/'
            'menuitem.edc7f2029a2be27d7010721001432ea0/'
            '?vgnextoid=feeca1a0899e6610VgnVCM1000001d04140aRCRD'
        ),
        'intro_es': (
            'El Consejo aprueba la actualización del Mapa nacional de '
            'ICTS, que mantiene a ReDIB como infraestructura de '
            'referencia en imagen biomédica.'
        ),
        'intro_en': '',
        'body_es': '',
        'body_en': '',
    },
]


# ---------------------------------------------------------------------------
# Historical news archive — pages 2-6 of the live /noticias listing
# (2017-2025), the posts beyond the 12 rich page-1 items above. ES-only: the
# live EN /news index does not carry these older posts, so we do not fabricate
# EN translations (human-only translation policy). Each is migrated with its
# real date / title / listing teaser and a link to the full article on
# redib.net. Full bilingual bodies for these remain a documented follow-up.
#
# Tuple shape: (date, slug, title, teaser). Empty teaser = the live listing
# showed no teaser for that item.
# ---------------------------------------------------------------------------

ARCHIVE_NEWS = [
    (date(2025, 3, 11), 'v-workshop-de-introduccion-a-la-imagen-molecular-preclinica-y-sus-aplicaciones-en-investigacion-biomedica', 'V Workshop de Introducción a la Imagen Molecular Preclínica y sus Aplicaciones en Investigación Biomédica', 'Taller dirigido a jóvenes investigadores, médicos, veterinarios, técnicos y científicos interesados en la aplicación de la imagen molecular preclínica.'),
    (date(2025, 3, 11), 'primera-convocatoria-de-acceso-abierto-competitivo-ano-2025-redib-2501', 'Primera Convocatoria de Acceso Abierto Competitivo Año 2025: REDIB 2501', 'La convocatoria de acceso abierto competitivo es una oportunidad para impulsar su ciencia.'),
    (date(2025, 3, 6), 'evento-transfiere-2025-malaga-12-14-marzo-2025', 'Evento Transfiere 2025, Málaga, 12-14 marzo 2025', 'Transfiere es el evento líder en investigación, desarrollo e innovación en el Sur de Europa.'),
    (date(2025, 3, 6), 'jornada-de-trabajo-sobre-oportunidades-de-colaboracion-nacional-entre-infraestructuras-europeas-de-investigacion-de-los-ambitos-de-la-alimentacion-el-medioambiente-y-la-salud', 'Jornada de trabajo sobre oportunidades de colaboración nacional entre Infraestructuras Europeas de Investigación de los ámbitos de la Alimentación, el Medioambiente y la Salud', 'El objetivo de esta jornada es generar un foro de intercambio de opiniones y experiencias a nivel nacional.'),
    (date(2025, 2, 18), 'boletin-de-febrero-de-2025-breve-resumen-del-crecimiento-y-exito-de-redib-en-2024', 'Boletín de febrero de 2025. Breve resumen del crecimiento y éxito de ReDIB en 2024', ''),
    (date(2025, 2, 17), 'expo-pct-iis-la-fe-jornada-de-las-plataformas-cientifico-tecnologicas-del-iis-la-fe', 'EXPO-PCT IIS LA FE | Jornada de las plataformas científico-tecnológicas del IIS La Fe', 'El próximo martes 25 de febrero celebramos una nueva edición de EXPO-PCT IIS LA FE.'),
    (date(2025, 2, 11), 'prof-luis-marti-bonmati-en-el-evento-european-cancer-imaging-initiative', 'Prof. Luis Marti-Bonmati en el evento European Cancer Imaging Initiative', 'El profesor Luis Marti-Bonmati en el evento European Cancer Imaging Initiative, organizado por la Comisión Europea.'),
    (date(2025, 2, 11), 'nodo-imagen-la-fe-representara-a-la-icts-redib-en-el-cvi-health-day', 'Nodo Imagen La Fe representará a la ICTS ReDIB en el CV+i Health Day', 'Un encuentro que concentrará a los principales agentes del sector.'),
    (date(2025, 1, 30), 'actualizacion-y-mejora-de-las-icts-mediante-las-convocatorias-feder', 'Actualización y Mejora de las ICTS mediante las convocatorias FEDER', ''),
    (date(2025, 1, 22), 'entrega-del-plan-estrategico-2025-2028-fecha-10022025', 'Entrega del Plan Estratégico 2025-2028. Fecha: 10/02/2025', 'La Red Distribuida de Imagen Biomédica (ReDIB) es un servicio de imagen biológica y biomédica de clase mundial.'),
    (date(2024, 12, 21), 'feliz-navidad', 'Feliz Navidad', 'ReDIB les desea una feliz Navidad y un próspero año nuevo 2025.'),
    (date(2024, 12, 18), 'boletin-informativo-mes-de-noviembre-2024', 'Boletín informativo mes de Noviembre 2024', ''),
    (date(2024, 12, 18), 'boletin-informativo-mes-de-diciembre-2024', 'Boletín informativo mes de diciembre 2024', ''),
    (date(2024, 10, 1), 'boletin-informativo-mes-de-octubre-2024', 'Boletín informativo mes de octubre 2024', 'Acceso a nuestro boletín de noticias del mes de octubre 2024 con los últimos datos y servicios.'),
    (date(2024, 9, 26), 'acceso-a-estudios-de-imagen-clinica-y-preclinica-con-ventajas-logisticas', 'Acceso a estudios de imagen clínica y preclínica con ventajas logísticas', ''),
    (date(2024, 9, 23), 'convocatoria-de-acceso-abierto-competitivo-redib-2024-02', 'Convocatoria de Acceso Abierto Competitivo ReDIB 2024-02', ''),
    (date(2024, 9, 19), 'una-nueva-convocatoria-de-acceso-abierto-competitivo-llegara-pronto', '¡Una nueva Convocatoria de Acceso Abierto Competitivo llegará pronto!', ''),
    (date(2024, 9, 19), 'redib-el-futuro-en-imagenes', 'ReDIB El Futuro en Imágenes', ''),
    (date(2024, 4, 1), 'redib2401-2', 'ReDIB2401', 'Cerrada la convocatoria REDIB2401. Se han recibido un total de 28 propuestas que se encuentran en fase de evaluación.'),
    (date(2023, 3, 2), 'abierta-la-segunda-convocatoria-de-acceso-abierto-competitivo-de-2023', 'Abierta la segunda convocatoria de Acceso Abierto Competitivo de 2023', 'En este momento y hasta el 15 de abril tenemos abierta la 2ª CONVOCATORIA 2023.'),
    (date(2023, 1, 1), 'abierta-la-primera-convocatoria-de-acceso-abierto-competitivo-de-2023', 'Abierta la primera convocatoria de Acceso Abierto Competitivo de 2023', 'En este momento y hasta el 15 de febrero tenemos abierta la 1ª CONVOCATORIA 2023.'),
    (date(2022, 12, 21), 'participacion-de-bioimac-en-la-semana-de-la-ciencia-y-la-innovacion-2022-de-la-comunidad-de-madrid', 'Participación de BioImaC en la Semana de la Ciencia y la Innovación 2022 de la Comunidad de Madrid', 'Un año más BioImaC ha participado en la Semana de la Ciencia.'),
    (date(2022, 11, 2), 'la-jornada-abierta-de-imagen-medica-avanzada-jaima-hospital-politecnico-y-universitario-la-fe', 'La Jornada Abierta de Imagen Médica Avanzada (JAIMA) Hospital Politécnico y Universitario La Fe', 'Hemos elegido el 8 de Noviembre por ser el Día Internacional de la Radiología.'),
    (date(2022, 10, 16), 'actualizacion-de-la-plataforma-de-acceso-redib', 'Actualización de la plataforma de acceso ReDIB', 'Estimados usuarios, en ReDIB estamos realizando un laborioso trabajo.'),
    (date(2022, 10, 10), 'visita-al-nodo-de-cic-biomagune', 'Visita al Nodo de CIC biomaGUNE', 'Hoy hemos podido disfrutar de la visita de 24 estudiantes.'),
    (date(2022, 6, 29), 'jornada-deep-dive-de-dispositivos-medicos-y-saliud', 'Jornada Deep Dive de dispositivos Médicos y Salud', ''),
    (date(2022, 6, 20), 'tres-investigadores-del-cnic-participan-en-la-semana-de-la-administracion-abierta-2022', 'Tres investigadores del CNIC participan en la Semana de la Administración Abierta 2022', ''),
    (date(2022, 6, 20), 'las-icts-disrupcion-en-imagen-medica-al-alcance-de-todos', 'Las ICTS: Disrupción en Imagen Médica al alcance de todos', ''),
    (date(2021, 11, 22), 'el-nodo-de-redib-cic-biomagune-participa-en-el-congreso-imaginenano-2021', 'El nodo de ReDIB CIC biomaGUNE participa en el congreso ImagineNano 2021', ''),
    (date(2021, 10, 13), 'jaima-2021', 'JAIMA 2021', 'El instituto de Investigación Sanitaria La Fe celebrará el 8 de Noviembre.'),
    (date(2021, 6, 14), 'luis-liz-marzan-recibe-hoy-el-premio-fundacion-lilly-de-investigacion-biomedica-preclinica-2021', 'Luis Liz Marzán recibe hoy el Premio Fundación Lilly de Investigación Biomédica Preclínica 2021', ''),
    (date(2021, 3, 26), 'trima-amplia-sus-capacidades-en-nanoscopia-con-cofinanciacion-de-fondos-feder', 'TRIMA amplía sus capacidades en nanoscopía con cofinanciación de fondos FEDER', 'El 23 de abril de 2019 se firmó un convenio entre el entonces Ministerio de Ciencia, Innovación y Universidades.'),
    (date(2020, 2, 5), 'redib-estara-presente-en-el-proximo-congreso-del-esmi-2020-en-tesalonica-grecia', 'ReDIB estará presente en el próximo congreso del ESMI 2020 en Tesalónica, Grecia', 'Entre los días 24 a 27 de marzo se celebrará en Tesalónica, Grecia, el decimoquinto Congreso Europeo de Imagen Molecular.'),
    (date(2020, 1, 8), 'redib-exhibe-su-oferta-cientifica-en-el-nanobiomed-2019-celebrado-en-noviembre-en-barcelona', 'ReDIB exhibe su oferta científica en el NanoBio&Med 2019 celebrado en noviembre en Barcelona', 'El pasado mes de noviembre se celebró en Barcelona el congreso NanoBio&Med.'),
    (date(2019, 11, 1), 'trima-ampliara-sus-capacidades-en-nanoscopia-con-cofinanciacion-de-fondos-feder', 'TRIMA ampliará sus capacidades en nanoscopía con cofinanciación de fondos FEDER', 'El pasado 31 de octubre se constituyó la Comisión de Seguimiento del convenio firmado el 23 de abril.'),
    (date(2019, 5, 27), 'nanospain-2019-conference', 'Nanospain 2019 Conference', 'El próximo 28 de mayo se celebrará en Barcelona el evento de referencia en España en nanociencia y nanotecnología.'),
    (date(2019, 5, 10), 'ysmin-meeting-2019', 'ySMIN Meeting 2019', 'Como en cada edición, el próximo lunes 13 de Mayo, ReDIB - ICTS formará parte del evento young Spanish molecular imaging.'),
    (date(2019, 5, 9), 'v-congreso-nacional-de-cientificos-emprendedores', 'V Congreso Nacional de Científicos Emprendedores', ''),
    (date(2019, 4, 1), 'farmaforum-2019', 'FARMAFORUM 2019', 'Durante los días 28 y 29 de marzo, se celebró en Madrid la sexta edición del foro de Industria Farmacéutica y Cosmética.'),
    (date(2019, 2, 18), 'noticias-nueva-convocatoria-abierta', 'Nueva convocatoria abierta', 'Hoy, día 18 de febrero, se abre la undécima convocatoria para acceder a la Infraestructura Científico Técnica Singular.'),
    (date(2019, 2, 18), 'redib-participa-en-foro-transfiere-punto-de-encuentro-nacional-de-la-innovacion', 'ReDIB participa en Foro Transfiere, punto de encuentro nacional de la innovación', 'Durante los días 12 y 13 de febrero, ReDIB estuvo presente en la nueva edición del Foro Transfiere en Málaga.'),
    (date(2019, 2, 4), 'reunion-de-los-nodos-de-nuestra-infraestructura-redib-icts', 'Reunión de los Nodos de nuestra infraestructura ReDIB-ICTS', 'El pasado 31 de enero tuvo lugar en CNIC la reunión informativa para la incorporación de los nuevos nodos.'),
    (date(2018, 12, 3), 'la-unidad-de-bioimagen-complutense-bioimac-e-imaging-la-fe-aprobados-por-el-ministerio-para-su-incorporacion-como-dos-nuevos-nodos-de-redib', 'La Unidad de BioImagen Complutense (BIOIMAC) e Imaging La Fe aprobados por el Ministerio para su incorporación como dos nuevos nodos de ReDIB', 'El pasado 6 de noviembre, el Consejo de Política Científica, Tecnológica y de Innovación aprobó la incorporación.'),
    (date(2018, 11, 28), 'reunion-informativa-sobre-la-actualizacion-del-mapa-de-icts', 'Reunión informativa sobre la actualización del Mapa de ICTS', 'El pasado 06 de noviembre de 2018, el Consejo de Política Científica, Tecnológica y de Innovación aprobó la actualización.'),
    (date(2018, 8, 31), 'biospain-2018', 'BIOSPAIN 2018', 'ReDIB formará parte de BIOSPAIN 2018 como expositor.'),
    (date(2018, 8, 13), 'novena-convocatoria-acceso-redib', 'Novena Convocatoria Acceso ReDIB', ''),
    (date(2018, 5, 10), 'octava-convocatoria-para-el-acceso-a-redib', 'Octava Convocatoria para el Acceso a ReDIB', 'A día 10 de mayo, se abre la octava convocatoria para acceder a la Red Distribuida de Imagen Biomédica.'),
    (date(2018, 3, 5), 'farmaforum-2018', 'FARMAFORUM 2018', 'ReDIB estará presente en la quinta edición del Foro de la Industria Farmacéutica, Biofarmacéutica, Cosmética y Tecnológica.'),
    (date(2018, 2, 22), 'redib-formara-parte-una-vez-mas-del-young-spanish-molecular-imaging-meeting-ysmin', 'ReDIB formará parte una vez más del "Young Spanish Molecular Imaging Meeting (ySMIN)"', 'El próximo 26 de febrero tendrá lugar la segunda edición del evento.'),
    (date(2018, 2, 8), 'abierta-la-septima-convocatoria', 'Abierta la séptima convocatoria', 'Desde el día de hoy, 8 de febrero, queda abierta la séptima convocatoria.'),
    (date(2017, 7, 3), 'molecular-imaging-workshop-november-20th-23rd-2017', 'Molecular Imaging Workshop - November 20th-23rd 2017', 'Tras el éxito de la primera edición del Molecular Imaging Workshop (MIW) del pasado 2015.'),
    (date(2017, 5, 9), 'el-comisario-de-salud-y-seguridad-alimentaria-de-la-comision-europea-visita-el-nodo-cnic', 'El Comisario de Salud y Seguridad Alimentaria de la Comisión Europea visita el nodo CNIC', ''),
    (date(2017, 4, 3), 'nueva-convocatoria-abierta', 'Nueva convocatoria abierta', 'Hoy, día 3 de abril, se abre la cuarta convocatoria para acceder a la Infraestructura Científico Técnica Singular.'),
    (date(2017, 3, 16), 'decimo-aniversario-para-el-centro-de-investigacion-cooperativa-en-biomateriales-cic-biomagune', 'Décimo aniversario para el Centro de Investigación Cooperativa en Biomateriales-CIC biomaGUNE', ''),
    (date(2017, 2, 20), 'redib-muestra-su-potencial-en-el-foro-transfiere-punto-de-encuentro-nacional-de-la-innovacion', 'ReDIB muestra su potencial en el Foro Transfiere, punto de encuentro nacional de la innovación', 'Durante los días 15 y 16 de febrero, ReDIB estuvo presente en la sexta edición del Foro Transfiere en Málaga.'),
]


# Historical press archive — pages 2-3 of the live /prensa listing. All are
# external clippings (outbound links to ministries, nodes, and media outlets);
# ES-only, no body, like the page-1 external clippings above. The long
# MICINN/MINECO portal URLs are truncated to the canonical vgnextoid param so
# they fit URLField(max_length=200), matching the existing clippings.
#
# Tuple shape: (date, slug, outlet, title, external_url).
# NOTE: the 3 oldest items on live /prensa page 3 (2014-2016) did not render
# cleanly to the crawler and are not yet included — a small remaining gap.

ARCHIVE_PRESS = [
    (date(2018, 7, 16), 'clip-micinn-rd-estructura-ministerio-2018', 'Ministerio de Ciencia, Innovación y Universidades', 'El Gobierno aprueba el Real Decreto por el que se desarrolla la estructura del Ministerio de Ciencia, Innovación y Universidades', 'http://www.idi.mineco.gob.es/portal/site/MICINN/menuitem.edc7f2029a2be27d7010721001432ea0/?vgnextoid=1888daa6362a4610VgnVCM1000001d04140aRCRD'),
    (date(2018, 5, 4), 'clip-mineco-187-millones-equipamiento-2018', 'MINECO', 'El Consejo de Ministros aprueba 187 millones de euros para equipamiento científico-técnico', 'http://www.idi.mineco.gob.es/portal/site/MICINN/menuitem.edc7f2029a2be27d7010721001432ea0/?vgnextoid=fec2bf5839a23610VgnVCM1000001d04140aRCRD'),
    (date(2018, 4, 4), 'clip-cnic-septima-convocatoria-2018', 'CNIC', 'Séptima Convocatoria ReDIB - ICTS', 'https://www.cnic.es/es/noticias/septima-convocatoria-para-acceder-infraestructura-cientifico-tecnica-singular-icts-redib'),
    (date(2018, 4, 3), 'clip-sebbm-septima-convocatoria-2018', "SE'BBM", 'Séptima Convocatoria ReDIB - ICTS', 'http://www.sebbm.es/web/es/noticias-en-portada/sala-prensa/2611-septima-convocatoria-icts-redib'),
    (date(2018, 3, 22), 'clip-cicbiomagune-emim-san-sebastian-2018', 'CIC biomaGUNE', 'El Congreso Europeo de Imagen Molecular (EMIM) tendrá lugar en San Sebastián', 'http://www.cicbiomagune.es/news/over-600-researchers-field-molecular-imaging-will-come-together-donostia-san-sebasti%C3%A1n-european'),
    (date(2018, 3, 22), 'clip-mineco-bei-1200-millones-2018', 'MINECO', 'El BEI financiará 1.200 millones de euros para proyectos de I+D+i', 'http://www.mineco.gob.es/portal/site/mineco/menuitem.ac30f9268750bd56a0b0240e026041a0/?vgnextoid=21520bb115d42610VgnVCM1000001d04140aRCRD'),
    (date(2018, 2, 19), 'clip-mineco-icts-transfiere-2018', 'MINECO', 'Las Infraestructuras Científicas y Técnicas Singulares también estuvieron en Transfiere 2018', 'http://www.idi.mineco.gob.es/portal/site/MICINN/menuitem.edc7f2029a2be27d7010721001432ea0/?vgnextoid=989d3f77c8ea1610VgnVCM1000001d04140aRCRD'),
    (date(2017, 9, 29), 'clip-cardioquiron-pizarro-saber-vivir-2017', 'Cardio Quirón', 'El Dr. Gonzalo Pizarro, Coordinador de ReDIB - ICTS, en Saber Vivir', 'http://cardioquiron.com/noticias/saber-vivir-rtve-290917/'),
    (date(2017, 9, 15), 'clip-cnic-quinta-convocatoria-2017', 'CNIC', 'Quinta Convocatoria para el acceso a ReDIB - ICTS', 'https://www.cnic.es/es/noticias/quinta-convocatoria-para-acceder-infraestructura-cientifico-tecnica-singular-icts-redib'),
    (date(2017, 6, 27), 'clip-mineco-actualizacion-mapa-icts-2017', 'MINECO', 'Se inicia la actualización del Mapa de Infraestructuras Científicas y Técnicas Singulares', 'http://www.idi.mineco.gob.es/portal/site/MICINN/menuitem.edc7f2029a2be27d7010721001432ea0/?vgnextoid=1d244ccad48ec510VgnVCM1000001d04140aRCRD'),
    (date(2017, 4, 1), 'clip-eurekalert-cuarta-convocatoria-2017', 'EurekAlert', 'Cuarta Convocatoria para el acceso a ReDIB - ICTS', 'https://www.eurekalert.org/pub_releases_ml/2017-03/cndi-q033117.php'),
    (date(2017, 3, 15), 'clip-mineco-cicbiomagune-decimo-aniversario-2017', 'MINECO', 'CIC biomaGUNE celebra su décimo aniversario', 'http://www.idi.mineco.gob.es/portal/site/MICINN/menuitem.edc7f2029a2be27d7010721001432ea0/?vgnextoid=f86d3d339e1da510VgnVCM1000001d04140aRCRD'),
]


def _archive_press_spec(entry):
    """Turn an ARCHIVE_PRESS tuple into an ES-only external-clipping spec."""
    post_date, slug, outlet, title, url = entry
    return {
        'date': post_date,
        'slug_es': slug,
        'slug_en': None,
        'title_es': title,
        'title_en': '',
        'outlet': outlet,
        'external_url': url,
        'intro_es': '',
        'intro_en': '',
        'body_es': '',
        'body_en': '',
    }


def _archive_news_spec(entry):
    """Turn an ARCHIVE_NEWS tuple into an ES-only NewsPage spec for
    _upsert_news_es. The body is the teaser (if any) plus a link to the full
    article on the live site."""
    post_date, slug, title, teaser = entry
    source_url = f'https://www.redib.net/{slug}'
    teaser_p = f'<p>{escape(teaser)}</p>' if teaser else ''
    body = (
        f'{teaser_p}'
        f'<p><a href="{source_url}" target="_blank" rel="noopener">'
        f'Leer la noticia completa en redib.net &rarr;</a></p>'
    )
    return {
        'date': post_date,
        'slug_es': slug,
        'title_es': title,
        'intro_es': teaser,
        'body_es': body,
        'hero_url': '',
        'hero_slug': '',
    }


# ===========================================================================
# Command
# ===========================================================================

class Command(BaseCommand):
    help = (
        'Populate News (12 paired ES/EN page-1 posts + 55 ES-only archive '
        'posts from /noticias pages 2-6) and Press (12 items: 6 internal '
        'ES-only, 6 external clippings). Idempotent.'
    )

    @transaction.atomic
    def handle(self, *args, **options):
        es = Locale.objects.get(language_code='es')
        en = Locale.objects.get(language_code='en')
        image_model = get_image_model()

        news_index_es = NewsIndexPage.objects.filter(locale=es).first()
        news_index_en = NewsIndexPage.objects.filter(locale=en).first()
        press_index_es = PressIndexPage.objects.filter(locale=es).first()
        press_index_en = PressIndexPage.objects.filter(locale=en).first()
        if not all([news_index_es, news_index_en,
                    press_index_es, press_index_en]):
            self.stderr.write(
                'NewsIndexPage and/or PressIndexPage missing in one of the '
                'locales. Run `populate_static_pages` first.'
            )
            return

        download_dir = Path(settings.MEDIA_ROOT) / 'marketing' / 'news'
        download_dir.mkdir(parents=True, exist_ok=True)

        news_rows = []
        for spec in NEWS_POSTS:
            hero = None
            if spec['hero_url']:
                hero = get_or_create_image(
                    image_model,
                    download_dir,
                    spec['hero_url'],
                    title=f"News hero: {spec['title_es']}",
                    slug_hint=spec['hero_slug'],
                    stderr_write=self.stderr.write,
                )
            es_page = self._upsert_news_es(news_index_es, spec, hero)
            en_page = None
            if spec.get('slug_en'):
                en_page = self._upsert_news_en(
                    news_index_en, en, es_page, spec, hero
                )
            news_rows.append((spec['date'], es_page, en_page, hero is not None))
            self.stdout.write(
                f"  News {spec['date']:%Y-%m-%d}: ES /{es_page.slug}/"
                + (f"  EN /en/{en_page.slug}/" if en_page else "  (ES-only)")
                + ("  +hero" if hero is not None else "")
            )

        # Historical archive (ES-only, pages 2-6 of the live listing).
        archive_count = 0
        for entry in ARCHIVE_NEWS:
            spec = _archive_news_spec(entry)
            es_page = self._upsert_news_es(news_index_es, spec, None)
            news_rows.append((spec['date'], es_page, None, False))
            archive_count += 1
        self.stdout.write(
            f"  News archive: {archive_count} ES-only posts (2017-2025)."
        )

        press_rows = []
        for spec in PRESS_ITEMS:
            es_page = self._upsert_press_es(press_index_es, spec)
            en_page = None
            if spec.get('slug_en'):
                en_page = self._upsert_press_en(
                    press_index_en, en, es_page, spec
                )
            kind = 'external' if spec['external_url'] else 'internal'
            press_rows.append((spec['date'], es_page, en_page, kind))
            self.stdout.write(
                f"  Press {spec['date']:%Y-%m-%d} [{kind}]: "
                f"ES /{es_page.slug}/"
                + (f"  EN /en/{en_page.slug}/" if en_page else "")
            )

        # Historical press archive (ES-only external clippings, /prensa pg 2-3).
        press_archive_count = 0
        for entry in ARCHIVE_PRESS:
            spec = _archive_press_spec(entry)
            es_page = self._upsert_press_es(press_index_es, spec)
            press_rows.append((spec['date'], es_page, None, 'external'))
            press_archive_count += 1
        self.stdout.write(
            f"  Press archive: {press_archive_count} external clippings."
        )

        # ---- summary -------------------------------------------------
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            'populate_news_press summary'
        ))
        self.stdout.write('-' * 72)
        paired_news = sum(1 for _, _, en_p, _ in news_rows if en_p)
        es_only_news = len(news_rows) - paired_news
        with_hero = sum(1 for _, _, _, hh in news_rows if hh)
        self.stdout.write(
            f"  News: {len(news_rows)} posts — "
            f"{paired_news} paired ES+EN, {es_only_news} ES-only, "
            f"{with_hero} with hero image"
        )
        internal_press = sum(1 for _, _, _, k in press_rows if k == 'internal')
        external_press = sum(1 for _, _, _, k in press_rows if k == 'external')
        paired_press = sum(1 for _, _, en_p, _ in press_rows if en_p)
        self.stdout.write(
            f"  Press: {len(press_rows)} items — "
            f"{internal_press} internal, {external_press} external; "
            f"{paired_press} paired ES+EN"
        )
        self.stdout.write('-' * 72)

    # ------------------------------------------------------------------
    # NewsPage upsert
    # ------------------------------------------------------------------

    def _upsert_news_es(self, news_index_es, spec, hero):
        page = (
            NewsPage.objects.child_of(news_index_es)
            .filter(slug=spec['slug_es']).first()
        )
        fields = {
            'title': spec['title_es'],
            'date': spec['date'],
            'intro': spec['intro_es'],
            'body': spec['body_es'],
            'hero_image': hero,
        }
        if page is None:
            page = NewsPage(
                slug=spec['slug_es'],
                locale=news_index_es.locale,
                show_in_menus=False,
                **fields,
            )
            news_index_es.add_child(instance=page)
            page.save_revision().publish()
            page.refresh_from_db()
            return page

        changed = False
        for field, value in fields.items():
            # Don't clobber a cached hero with None if a download has since
            # started failing.
            if field == 'hero_image' and value is None and page.hero_image_id:
                continue
            if getattr(page, field) != value:
                setattr(page, field, value)
                changed = True
        if changed:
            page.save_revision().publish()
            page.refresh_from_db()
        return page

    def _upsert_news_en(self, news_index_en, en_locale, es_page, spec, hero):
        page = (
            NewsPage.objects
            .filter(translation_key=es_page.translation_key,
                    locale=en_locale)
            .first()
        )
        fields = {
            'title': spec['title_en'],
            'slug': spec['slug_en'],
            'date': spec['date'],
            'intro': spec['intro_en'],
            'body': spec['body_en'],
            'hero_image': hero,
        }
        if page is None:
            page = es_page.copy_for_translation(en_locale)
            for field, value in fields.items():
                setattr(page, field, value)
            page.save_revision().publish()
            page.refresh_from_db()
            if page.get_parent().id != news_index_en.id:
                page.move(news_index_en, pos='last-child')
                page.refresh_from_db()
            return page

        changed = False
        for field, value in fields.items():
            if field == 'hero_image' and value is None and page.hero_image_id:
                continue
            if getattr(page, field) != value:
                setattr(page, field, value)
                changed = True
        if changed:
            page.save_revision().publish()
            page.refresh_from_db()
        if page.get_parent().id != news_index_en.id:
            page.move(news_index_en, pos='last-child')
            page.refresh_from_db()
        return page

    # ------------------------------------------------------------------
    # PressItemPage upsert
    # ------------------------------------------------------------------

    def _upsert_press_es(self, press_index_es, spec):
        page = (
            PressItemPage.objects.child_of(press_index_es)
            .filter(slug=spec['slug_es']).first()
        )
        fields = {
            'title': spec['title_es'],
            'date': spec['date'],
            'outlet': spec['outlet'],
            'external_url': spec['external_url'],
            'intro': spec['intro_es'],
            'body': spec['body_es'],
        }
        if page is None:
            page = PressItemPage(
                slug=spec['slug_es'],
                locale=press_index_es.locale,
                show_in_menus=False,
                **fields,
            )
            press_index_es.add_child(instance=page)
            page.save_revision().publish()
            page.refresh_from_db()
            return page

        changed = False
        for field, value in fields.items():
            if getattr(page, field) != value:
                setattr(page, field, value)
                changed = True
        if changed:
            page.save_revision().publish()
            page.refresh_from_db()
        return page

    def _upsert_press_en(self, press_index_en, en_locale, es_page, spec):
        page = (
            PressItemPage.objects
            .filter(translation_key=es_page.translation_key,
                    locale=en_locale)
            .first()
        )
        fields = {
            'title': spec['title_en'],
            'slug': spec['slug_en'],
            'date': spec['date'],
            'outlet': spec['outlet'],
            'external_url': spec['external_url'],
            'intro': spec['intro_en'],
            'body': spec['body_en'],
        }
        if page is None:
            page = es_page.copy_for_translation(en_locale)
            for field, value in fields.items():
                setattr(page, field, value)
            page.save_revision().publish()
            page.refresh_from_db()
            if page.get_parent().id != press_index_en.id:
                page.move(press_index_en, pos='last-child')
                page.refresh_from_db()
            return page

        changed = False
        for field, value in fields.items():
            if getattr(page, field) != value:
                setattr(page, field, value)
                changed = True
        if changed:
            page.save_revision().publish()
            page.refresh_from_db()
        if page.get_parent().id != press_index_en.id:
            page.move(press_index_en, pos='last-child')
            page.refresh_from_db()
        return page
