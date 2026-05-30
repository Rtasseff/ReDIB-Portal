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


# ===========================================================================
# Command
# ===========================================================================

class Command(BaseCommand):
    help = (
        'Populate a representative sample of News (12 paired ES/EN) and '
        'Press (12 items: 6 internal ES-only, 6 external clippings) '
        'content. Idempotent.'
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
