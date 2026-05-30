"""Populate the marketing-site IA: section pages + content (Phase 3a).

Idempotent: safe to run repeatedly. Creates the section parent pages
under HomePage (ES) and their EN translations, populates static content
re-crawled from the live redib.net, creates ExternalLink snippets for
/enlaces-de-interes, and sets up the /actualidad -> /noticias redirect.

Phases 3b/c/d will populate: Team people, Equipment items, Node details,
News posts, Press items. This command leaves those pages as stubs.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from wagtail.contrib.redirects.models import Redirect
from wagtail.models import Locale, Page, Site

from home.models import HomePage
from marketing.models import (
    AccessIndexPage,
    ContactPage,
    EquipmentIndexPage,
    ExternalLink,
    NewsIndexPage,
    NodeIndexPage,
    PressIndexPage,
    PricingPage,
    StandardPage,
    TeamPage,
)


# ---------------------------------------------------------------------------
# Body content (re-crawled from redib.net 2026-05-30)
# ---------------------------------------------------------------------------

ABOUT_BODY_ES = """
<h2>Red Distribuida de Imagen Biomédica (ReDIB)</h2>
<p>ReDIB es una Infraestructura Científica y Técnica Singular (ICTS) que agrupa
centros de imagen biomédica de nivel mundial. Su propósito es ofrecer a la
comunidad científica servicios competitivos de acceso abierto en el campo de la
imagen molecular y funcional, así como capacidades avanzadas de imagen a lo
largo de todo el continuo de la investigación traslacional.</p>
<p>La infraestructura proporciona instalaciones esenciales en Resonancia
Magnética, Tomografía Computarizada, PET y SPECT, junto con combinaciones
multimodales como PET-TC y PET-RM. Es la única red con esta tecnología en
España.</p>
<h3>Estructura de cuatro nodos</h3>
<p>La red está formada por cuatro nodos estratégicamente distribuidos:</p>
<ul>
<li><strong>TRIMA @ CNIC (Madrid):</strong> Unidad de Imagen Molecular y
Funcional, Unidad de Imagen Avanzada con RM/PET y laboratorio de radioquímica,
y Unidad de Imagen de Alto Rendimiento.</li>
<li><strong>CIC biomaGUNE (San Sebastián):</strong> Plataforma de Imagen
Molecular y Funcional con ciclotrón, laboratorio de radioquímica, PET-CT,
SPECT-CT y RM de alto campo para investigación preclínica.</li>
<li><strong>Imaging La Fe (Valencia):</strong> Tres unidades dedicadas a imagen
clínica, imagen preclínica y desarrollo de biomarcadores.</li>
<li><strong>BioImaC (Universidad Complutense, Madrid):</strong> Servicios de
imagen preclínica con equipos de resonancia magnética de bajo y alto campo.</li>
</ul>
"""

ABOUT_BODY_EN = """
<h2>Distributed Biomedical Imaging Network (ReDIB)</h2>
<p>The Distributed Biomedical Imaging Network (ReDIB) is a Unique Scientific
and Technologic Infrastructure (ICTS) that consolidates premier biological and
biomedical imaging centers. The network's purpose is to deliver competitive
open-access services in the field of molecular and functional imaging,
alongside advanced imaging capabilities throughout the translational research
continuum.</p>
<p>The infrastructure provides essential facilities including MRI, CT, PET and
SPECT technologies, along with multimodal combinations such as PET-CT and
PET-MRI. It represents the only network with this technology in Spain.</p>
<h3>Operational structure</h3>
<p>The network comprises four strategically positioned nodes across Spain,
employing a centralized support model with specialized personnel who deliver
comprehensive researcher assistance throughout project execution:</p>
<ul>
<li><strong>TRIMA @ CNIC (Madrid):</strong> Advanced Infrastructure for
Translational Imaging — molecular imaging, advanced imaging with MRI/PET and
radiochemistry laboratory, and high-throughput imaging units.</li>
<li><strong>CIC biomaGUNE (San Sebastián):</strong> Molecular and Functional
Imaging Platform with a cyclotron, radiochemistry laboratory, multimodal
imaging equipment and dedicated animal research facilities.</li>
<li><strong>Imaging La Fe (Valencia):</strong> Clinical medical imaging,
preclinical animal imaging and biomarker development through specialized
research groups.</li>
<li><strong>BioImaC (Universidad Complutense, Madrid):</strong> Preclinical
imaging services using low-field and high-field MRI systems available for
competitive external access.</li>
</ul>
"""

ACCESS_BODY_ES = """
<h2>Acceso a la ICTS ReDIB</h2>
<p>ReDIB ofrece a la comunidad científica dos mecanismos de acceso a sus
instalaciones esenciales: el <strong>Acceso Abierto Competitivo (AAC)</strong>
y el <strong>Acceso a Demanda (AaD)</strong>.</p>
<h3>Acceso Abierto Competitivo (AAC)</h3>
<p>El AAC es un mecanismo de acceso subvencionado que se gestiona mediante
convocatorias públicas periódicas. Las solicitudes se evalúan por un comité
independiente conforme a criterios de viabilidad técnica, calidad científica e
impacto. Los proyectos seleccionados se benefician de tarifas reducidas, ya que
la subvención cubre los costes de operación (los solicitantes asumen únicamente
radiofármacos y consumibles).</p>
<h3>Acceso a Demanda (AaD)</h3>
<p>El AaD permite contratar servicios de imagen de ReDIB fuera del marco
competitivo, aplicando las tarifas aprobadas por cada nodo. Es el mecanismo
adecuado cuando los plazos del proyecto no encajan con el calendario de
convocatorias o cuando el solicitante prefiere una vía directa.</p>
<h3>Cómo solicitar el acceso</h3>
<p>Las solicitudes se presentan a través del portal de gestión de
convocatorias de ReDIB. Allí encontrará las convocatorias abiertas, los plazos
de presentación y toda la documentación necesaria para iniciar una solicitud.</p>
<p>Consulte también la <a href="/documentacion/">documentación reguladora</a>
(reglamento del Comité de Acceso, protocolos de acceso, planificación de
convocatorias) y el <a href="/costes-de-acceso/">detalle de los costes
asociados</a>.</p>
"""

ACCESS_BODY_EN = """
<h2>Access to the ReDIB ICTS</h2>
<p>ReDIB offers the scientific community two mechanisms for accessing its
essential facilities: <strong>Competitive Open Access (AAC)</strong> and
<strong>On-Demand Access (AaD)</strong>.</p>
<h3>Competitive Open Access (AAC)</h3>
<p>AAC is a subsidized access mechanism managed through periodic public calls.
Applications are evaluated by an independent committee on the basis of
technical feasibility, scientific quality and impact. Successful projects
benefit from reduced rates, as the subsidy covers operating costs (applicants
only pay for radiopharmaceuticals and consumables).</p>
<h3>On-Demand Access (AaD)</h3>
<p>AaD lets researchers contract ReDIB imaging services outside the
competitive framework, applying the rates approved by each node. It is the
right mechanism when project timelines do not match the call schedule or when
a direct route is preferred.</p>
<h3>How to apply</h3>
<p>Applications are submitted through the ReDIB call-management portal. There
you will find the open calls, submission deadlines and all the documentation
required to start an application.</p>
<p>See also the <a href="/en/documentation/">governing documentation</a> (rules
of procedure for the Access Committee, access protocols, call planning) and
the <a href="/en/access-cost/">access cost details</a>.</p>
"""

CONTACT_INTRO_ES = (
    "¿Tiene preguntas sobre la red o sobre cómo acceder a sus servicios? "
    "Estaremos encantados de atenderle."
)
CONTACT_INTRO_EN = (
    "Have questions about the network or about how to access its services? "
    "We will be glad to help."
)

CONTACT_DETAILS_ES = """
<p><strong>Correo electrónico:</strong>
<a href="mailto:info@redib.net">info@redib.net</a></p>
<p><strong>Teléfono:</strong> +34 943 00 53 06</p>
<p><strong>Dirección postal:</strong><br>
ReDIB<br>
Parque Científico y Tecnológico de Gipuzkoa<br>
Edificio Empresarial &quot;C&quot;, Paseo Miramón 182<br>
20014 Donostia-San Sebastián, Gipuzkoa</p>
<h3>Sitios web de los nodos</h3>
<ul>
<li><a href="https://www.cnic.es" target="_blank" rel="noopener">www.cnic.es</a> — TRIMA @ CNIC</li>
<li><a href="https://www.cicbiomagune.es" target="_blank" rel="noopener">www.cicbiomagune.es</a> — CIC biomaGUNE</li>
<li><a href="https://acim.lafe.san.gva.es/acim" target="_blank" rel="noopener">acim.lafe.san.gva.es/acim</a> — Imaging La Fe</li>
<li><a href="https://www.ucm.es" target="_blank" rel="noopener">www.ucm.es</a> — BioImaC (UCM)</li>
</ul>
"""

CONTACT_DETAILS_EN = """
<p><strong>Email:</strong>
<a href="mailto:info@redib.net">info@redib.net</a></p>
<p><strong>Phone:</strong> +34 943 00 53 06</p>
<p><strong>Postal address:</strong><br>
ReDIB<br>
Gipuzkoa Science and Technology Park<br>
Business Building &quot;C&quot;, Paseo Miramón 182<br>
20014 Donostia-San Sebastián, Gipuzkoa</p>
<h3>Node websites</h3>
<ul>
<li><a href="https://www.cnic.es" target="_blank" rel="noopener">www.cnic.es</a> — TRIMA @ CNIC</li>
<li><a href="https://www.cicbiomagune.es" target="_blank" rel="noopener">www.cicbiomagune.es</a> — CIC biomaGUNE</li>
<li><a href="https://acim.lafe.san.gva.es/acim" target="_blank" rel="noopener">acim.lafe.san.gva.es/acim</a> — Imaging La Fe</li>
<li><a href="https://www.ucm.es" target="_blank" rel="noopener">www.ucm.es</a> — BioImaC (UCM)</li>
</ul>
"""

LINKS_BODY_ES = """
<p>Recursos de interés relacionados con ReDIB y la imagen biomédica en España.</p>
<p>A continuación se enumeran los enlaces externos a páginas institucionales,
canales de difusión y plataformas asociadas.</p>
"""

LINKS_BODY_EN = """
<p>External resources of interest related to ReDIB and biomedical imaging in
Spain.</p>
<p>Below are external links to institutional pages, dissemination channels and
partner platforms.</p>
"""

PRICING_INTRO_ES = (
    "Tarifas de acceso a las instalaciones esenciales de ReDIB en los dos "
    "mecanismos disponibles: Acceso Abierto Competitivo (AAC) y Acceso a "
    "Demanda (AaD)."
)
PRICING_INTRO_EN = (
    "Rates for accessing ReDIB's essential facilities under the two available "
    "mechanisms: Competitive Open Access (AAC) and On-Demand Access (AaD)."
)

PRICING_BODY_ES = """
<h2>Mecanismos de acceso</h2>
<p><strong>Acceso Abierto Competitivo (AAC):</strong> mecanismo de acceso a las
instalaciones esenciales de ReDIB que está subvencionado, por lo que se aplican
tarifas reducidas.</p>
<p><strong>Acceso a Demanda (AaD):</strong> mecanismo de acceso a las
instalaciones esenciales de ReDIB no subvencionado, en el que se aplican las
tarifas aprobadas por cada nodo de ReDIB para sus diferentes servicios.</p>
<p><em>La tabla de precios detallada (nodo &times; modalidad &times; unidad de
servicio) se publicará en una fase posterior. Para consultar tarifas concretas,
póngase en contacto con <a href="mailto:info@redib.net">info@redib.net</a>.</em></p>
"""

PRICING_BODY_EN = """
<h2>Access mechanisms</h2>
<p><strong>Competitive Open Access (AAC):</strong> a subsidized mechanism for
accessing ReDIB's essential facilities, meaning reduced rates apply.</p>
<p><strong>On-Demand Access (AaD):</strong> a non-subsidized mechanism for
accessing ReDIB's essential facilities, in which the rates approved by each
ReDIB node for its different services apply.</p>
<p><em>The detailed pricing table (node &times; modality &times; service unit)
will be published in a follow-up phase. For specific rate information, please
contact <a href="mailto:info@redib.net">info@redib.net</a>.</em></p>
"""

LEGAL_BODY_ES = """
<h2>Datos de identificación</h2>
<p>Titular del sitio web: <strong>ReDIB</strong><br>
CIF: G20788840<br>
Domicilio: Parque Científico y Tecnológico de Gipuzkoa, Edificio Empresarial
&quot;C&quot;, Paseo Miramón 182, 20014 Donostia-San Sebastián, Gipuzkoa<br>
Dato registral: Inscrita en el Registro de Asociaciones del Gobierno Vasco con
fecha 12 de febrero de 2003 y n.&ordm; AS/G/10345/2003<br>
Teléfono: +34 943 00 53 06<br>
Correo electrónico: <a href="mailto:info@redib.net">info@redib.net</a></p>
<h2>Objeto</h2>
<p>El prestador cumple las obligaciones de la Ley 34/2002 sobre Servicios de la
Sociedad de la Información y Comercio Electrónico (LSSI-CE). El acceso al sitio
web implica sin reservas la aceptación de las presentes condiciones generales
de uso, que el usuario afirma comprender. Queda prohibido usar el sitio para
actividades contrarias a la ley. El prestador podrá interrumpir en cualquier
momento el acceso si detecta un uso ilícito.</p>
<h2>Uso del sitio web y obligaciones de los usuarios</h2>
<p>Los usuarios deben utilizar el sitio sin contravenir la legislación vigente
ni el orden público. El uso ilícito o lesivo de la web queda terminantemente
prohibido. ReDIB garantiza el respeto a la dignidad personal, la protección de
menores y la no discriminación. Los contenidos son propiedad de ReDIB o están
debidamente autorizados; queda prohibida su reproducción, distribución o
modificación sin autorización previa.</p>
<h2>Propiedad intelectual e industrial</h2>
<p>Todos los derechos de propiedad industrial e intelectual sobre los
contenidos pertenecen a ReDIB. Las reclamaciones por violación deben dirigirse
a <a href="mailto:info@redib.net">info@redib.net</a> con los datos personales y
acreditación de derechos.</p>
<h2>Enlaces</h2>
<p>ReDIB no se responsabiliza de los resultados derivados de enlaces externos.
Se requiere autorización previa para establecer dispositivos técnicos de enlace
hacia el portal. El enlace no implica relaciones entre ReDIB y el propietario
del sitio origen.</p>
<h2>Modificación unilateral y duración</h2>
<p>ReDIB se reserva el derecho de modificar, en cualquier momento y sin
necesidad de previo aviso, la presentación y configuración del sitio web, así
como este aviso legal.</p>
<h2>Exclusión de garantías y responsabilidad</h2>
<p>ReDIB no otorga garantías ni se responsabiliza por daños derivados de la
falta de disponibilidad, la existencia de virus o el uso ilícito, negligente o
fraudulento del sitio por parte de los usuarios.</p>
<h2>Tratamiento de datos personales</h2>
<p>ReDIB ha adoptado los niveles de seguridad adecuados e incorporado las
medidas técnicas a su alcance para garantizar la confidencialidad de los datos.</p>
<h2>Legislación aplicable y jurisdicción</h2>
<p>Las condiciones se rigen por la legislación española, sometidas a los
juzgados de Guipúzcoa para cualquier controversia.</p>
"""

LEGAL_BODY_EN = """
<h2>Identification data</h2>
<p>Owner of the website: <strong>ReDIB</strong><br>
CIF: G20788840<br>
Address: Gipuzkoa Science and Technology Park, Business Building &quot;C&quot;,
Paseo Miramón 182, 20014 Donostia-San Sebastián, Gipuzkoa<br>
Registry data: Registered in the Basque Government Register of Associations on
12 February 2003 under number AS/G/10345/2003<br>
Phone: +34 943 00 53 06<br>
Email: <a href="mailto:info@redib.net">info@redib.net</a></p>
<h2>Object</h2>
<p>The provider shows this document to comply with Law 34/2002 on the Services
of the Information Society and Electronic Commerce (LSSI-CE) and to inform
users about these conditions of use. Access to the website implies unreserved
acceptance of these general conditions of use, which the user claims to
understand. The user undertakes not to use the website for activities contrary
to the law. The provider may at any time interrupt access if it detects
unlawful use.</p>
<h2>Use of the website and users' obligations</h2>
<p>Users undertake to use the website without contravening current legislation,
generally accepted uses and public order. Unlawful or harmful use of the
website is strictly prohibited. ReDIB guarantees respect for human dignity,
the protection of minors and non-discrimination. Contents are the property of
ReDIB or are duly authorized; reproduction, distribution or modification is
prohibited without prior authorization.</p>
<h2>Intellectual and industrial property</h2>
<p>All industrial and intellectual property rights over the contents belong to
ReDIB. Claims regarding alleged infringement must be sent to
<a href="mailto:info@redib.net">info@redib.net</a> with the personal data and
proof of the rights.</p>
<h2>Links</h2>
<p>ReDIB is not responsible for the results derived from external links. Prior
written authorization is required to establish any technical linking device to
the portal. Establishing a link does not imply any relationship between ReDIB
and the owner of the linking site.</p>
<h2>Unilateral modification and duration</h2>
<p>ReDIB reserves the right to modify, at any time and without prior notice,
the presentation and configuration of the website, as well as this legal
notice.</p>
<h2>Exclusion of guarantees and liability</h2>
<p>ReDIB does not give any guarantee nor is it responsible for damages caused
by the lack of availability or maintenance of the website, the existence of
viruses, or the unlawful, negligent or fraudulent use of the site by users.</p>
<h2>Processing of personal data</h2>
<p>ReDIB has adopted the appropriate levels of security for the data it
processes, incorporating all means and technical measures at its disposal to
guarantee confidentiality, avoid misuse, loss, alteration, unauthorized access
and theft.</p>
<h2>Applicable law and jurisdiction</h2>
<p>These conditions will be governed by Spanish law, submitting to the courts
of Guipúzcoa for any dispute arising from access to the website.</p>
"""


# ---------------------------------------------------------------------------
# Section spec
# ---------------------------------------------------------------------------

# (es_title, es_slug, en_title, en_slug, page_class, extra_es, extra_en)
# Where extra_* is a dict of additional field assignments after construction.
# Stub pages just carry intro text; populated pages override body etc. in code.
SECTIONS = [
    {
        'es_title': 'Quiénes somos',
        'es_slug': 'quienes-somos',
        'en_title': 'About us',
        'en_slug': 'about-us',
        'page_class': StandardPage,
        'es_fields': {
            'intro': 'ReDIB es la Red Distribuida de Imagen Biomédica, una '
                     'ICTS que ofrece servicios competitivos de acceso abierto.',
            'body': ABOUT_BODY_ES,
        },
        'en_fields': {
            'intro': 'ReDIB is the Distributed Biomedical Imaging Network, a '
                     'Spanish ICTS offering competitive open-access services.',
            'body': ABOUT_BODY_EN,
        },
    },
    {
        'es_title': 'Acceso',
        'es_slug': 'es-acceso',
        'en_title': 'Access',
        'en_slug': 'en-access',
        'page_class': AccessIndexPage,
        'es_fields': {
            'intro': 'Cómo acceder a las instalaciones esenciales de ReDIB: '
                     'Acceso Abierto Competitivo (AAC) y Acceso a Demanda (AaD).',
            'body': ACCESS_BODY_ES,
        },
        'en_fields': {
            'intro': 'How to access ReDIB\'s essential facilities: Competitive '
                     'Open Access (AAC) and On-Demand Access (AaD).',
            'body': ACCESS_BODY_EN,
        },
    },
    {
        'es_title': 'Equipamiento',
        'es_slug': 'equipamiento',
        'en_title': 'Equipment',
        'en_slug': 'equipment',
        'page_class': EquipmentIndexPage,
        'es_fields': {
            'intro': 'Equipamiento de imagen biomédica disponible en los '
                     'cuatro nodos de ReDIB.',
            'body': '<p>Contenido detallado de las categorías de equipamiento '
                    '(Imagen Clínica, Imagen Preclínica, Análisis y Radioquímica) '
                    'se publicará en una fase posterior.</p>',
        },
        'en_fields': {
            'intro': 'Biomedical imaging equipment available across ReDIB\'s '
                     'four nodes.',
            'body': '<p>Detailed content for the equipment categories '
                    '(Clinical Imaging, Preclinical Imaging, Image Analytics and '
                    'Radiochemistry) will be published in a follow-up phase.</p>',
        },
    },
    {
        'es_title': 'Equipo',
        'es_slug': 'equipo',
        'en_title': 'Team',
        'en_slug': 'team',
        'page_class': TeamPage,
        'es_fields': {
            'intro': '<p>El equipo humano que hace posible ReDIB: coordinación, '
                     'comité de coordinación, comité asesor científico-técnico y '
                     'área de gestión.</p>',
        },
        'en_fields': {
            'intro': '<p>The people who make ReDIB possible: coordination, '
                     'coordination committee, scientific-technical advisory '
                     'committee and management area.</p>',
        },
    },
    {
        'es_title': 'Nodos',
        'es_slug': 'nodos',
        'en_title': 'Nodes',
        'en_slug': 'nodes',
        'page_class': NodeIndexPage,
        'es_fields': {
            'intro': 'Los cuatro nodos de ReDIB: BioImaC (Madrid), TRIMA @ CNIC '
                     '(Madrid), Imaging La Fe (Valencia) y CIC biomaGUNE '
                     '(San Sebastián).',
        },
        'en_fields': {
            'intro': 'ReDIB\'s four nodes: BioImaC (Madrid), TRIMA @ CNIC '
                     '(Madrid), Imaging La Fe (Valencia) and CIC biomaGUNE '
                     '(San Sebastián).',
        },
    },
    {
        'es_title': 'Noticias',
        'es_slug': 'noticias',
        'en_title': 'News',
        'en_slug': 'news',
        'page_class': NewsIndexPage,
        'es_fields': {
            'intro': 'Últimas noticias de la red ReDIB.',
        },
        'en_fields': {
            'intro': 'Latest news from the ReDIB network.',
        },
    },
    {
        'es_title': 'Prensa',
        'es_slug': 'prensa',
        'en_title': 'Press',
        'en_slug': 'press',
        'page_class': PressIndexPage,
        'es_fields': {
            'intro': 'ReDIB en los medios.',
        },
        'en_fields': {
            'intro': 'ReDIB in the media.',
        },
    },
    {
        'es_title': 'Tarifas',
        'es_slug': 'tarifas',
        'en_title': 'Rates',
        'en_slug': 'rates',
        'page_class': PricingPage,
        'es_fields': {
            'intro': PRICING_INTRO_ES,
            'body': PRICING_BODY_ES,
        },
        'en_fields': {
            'intro': PRICING_INTRO_EN,
            'body': PRICING_BODY_EN,
        },
    },
    {
        'es_title': 'Contacto',
        'es_slug': 'contacto',
        'en_title': 'Contact',
        'en_slug': 'contact',
        'page_class': ContactPage,
        'es_fields': {
            'intro': CONTACT_INTRO_ES,
            'contact_details': CONTACT_DETAILS_ES,
        },
        'en_fields': {
            'intro': CONTACT_INTRO_EN,
            'contact_details': CONTACT_DETAILS_EN,
        },
    },
    {
        'es_title': 'Enlaces de interés',
        'es_slug': 'enlaces-de-interes',
        'en_title': 'Links of interest',
        'en_slug': 'links-of-interest',
        'page_class': StandardPage,
        'es_fields': {
            'intro': 'Recursos externos de interés relacionados con ReDIB.',
            'body': LINKS_BODY_ES,
        },
        'en_fields': {
            'intro': 'External resources of interest related to ReDIB.',
            'body': LINKS_BODY_EN,
        },
    },
    {
        'es_title': 'Aviso legal',
        'es_slug': 'aviso-legal',
        'en_title': 'Legal notice',
        'en_slug': 'legal-notice',
        'page_class': StandardPage,
        'es_fields': {
            'intro': '',
            'body': LEGAL_BODY_ES,
        },
        'en_fields': {
            'intro': '',
            'body': LEGAL_BODY_EN,
        },
    },
]


# ---------------------------------------------------------------------------
# ExternalLink snippets for /enlaces-de-interes
# ---------------------------------------------------------------------------

# Cards on the live /enlaces-de-interes page (RESOURCE category)
RESOURCE_LINKS = [
    {
        'es_title': 'Mapa de las ICTS',
        'en_title': 'ICTS Map',
        'url': 'https://www.mapa.gob.es/es/pesca/temas/innovacion/mapa_icts',
        'es_description': 'Mapa oficial de Infraestructuras Científicas y '
                          'Técnicas Singulares del Ministerio.',
        'en_description': 'Official map of Spanish Unique Scientific and '
                          'Technical Infrastructures.',
    },
    {
        'es_title': 'Síguenos en Twitter @ICTSReDIB',
        'en_title': 'Follow us on Twitter @ICTSReDIB',
        'url': 'https://twitter.com/IctsRedib',
        'es_description': 'Canal oficial de ReDIB en Twitter / X.',
        'en_description': 'ReDIB\'s official Twitter / X channel.',
    },
    {
        'es_title': 'ReDIB como plataforma en CIC biomaGUNE',
        'en_title': 'ReDIB as a platform in CIC biomaGUNE',
        'url': 'http://www.cicbiomagune.es/org/uim',
        'es_description': 'Unidad de Imagen Molecular en el nodo CIC biomaGUNE.',
        'en_description': 'Molecular Imaging Unit at the CIC biomaGUNE node.',
    },
    {
        'es_title': 'ReDIB como plataforma en el CNIC',
        'en_title': 'ReDIB as a platform in CNIC',
        'url': 'https://www.flickr.com/photos/139407851@N06/albums/72157665630049300',
        'es_description': 'Galería de imágenes del nodo TRIMA @ CNIC.',
        'en_description': 'Image gallery for the TRIMA @ CNIC node.',
    },
    {
        'es_title': 'Síguenos en LinkedIn',
        'en_title': 'Follow us on LinkedIn',
        'url': 'https://es.linkedin.com/company/redib---icts',
        'es_description': 'Página oficial de ReDIB en LinkedIn.',
        'en_description': 'ReDIB\'s official LinkedIn page.',
    },
]

# Institutional partner links (INSTITUTIONAL category) — the host
# organizations of the four ReDIB nodes plus partner institutions.
INSTITUTIONAL_LINKS = [
    {
        'es_title': 'CNIC — Centro Nacional de Investigaciones Cardiovasculares',
        'en_title': 'CNIC — National Center for Cardiovascular Research',
        'url': 'https://www.cnic.es',
        'es_description': 'Institución anfitriona del nodo TRIMA @ CNIC.',
        'en_description': 'Host institution of the TRIMA @ CNIC node.',
    },
    {
        'es_title': 'CIC biomaGUNE',
        'en_title': 'CIC biomaGUNE',
        'url': 'https://www.cicbiomagune.es',
        'es_description': 'Institución anfitriona del nodo CIC biomaGUNE.',
        'en_description': 'Host institution of the CIC biomaGUNE node.',
    },
    {
        'es_title': 'Hospital Universitario y Politécnico La Fe',
        'en_title': 'La Fe University and Polytechnic Hospital',
        'url': 'https://acim.lafe.san.gva.es/acim',
        'es_description': 'Institución anfitriona del nodo Imaging La Fe.',
        'en_description': 'Host institution of the Imaging La Fe node.',
    },
    {
        'es_title': 'Universidad Complutense de Madrid (UCM)',
        'en_title': 'Complutense University of Madrid (UCM)',
        'url': 'https://www.ucm.es',
        'es_description': 'Institución anfitriona del nodo BioImaC.',
        'en_description': 'Host institution of the BioImaC node.',
    },
    {
        'es_title': 'Ministerio de Ciencia, Innovación y Universidades',
        'en_title': 'Ministry of Science, Innovation and Universities',
        'url': 'https://www.ciencia.gob.es',
        'es_description': 'Organismo que reconoce a ReDIB como ICTS.',
        'en_description': 'The body that recognizes ReDIB as an ICTS.',
    },
]


# ---------------------------------------------------------------------------
# Homepage refresh content
# ---------------------------------------------------------------------------

HOMEPAGE_ES = {
    'hero_heading': 'Red Distribuida de Imagen Biomédica',
    'hero_subheading': 'Servicios competitivos de acceso abierto en imagen '
                       'molecular y funcional para la comunidad científica.',
    'body': '<p>ReDIB es la Infraestructura Científica y Técnica Singular '
            '(ICTS) que agrupa cuatro centros de imagen biomédica de '
            'referencia: BioImaC, TRIMA @ CNIC, Imaging La Fe y CIC '
            'biomaGUNE. Ofrecemos acceso a tecnologías de RM, PET, SPECT, '
            'TC y radioquímica a través de convocatorias competitivas y '
            'acceso a demanda.</p>',
}

HOMEPAGE_EN = {
    'hero_heading': 'Distributed Biomedical Imaging Network',
    'hero_subheading': 'Competitive open-access services in molecular and '
                       'functional imaging for the scientific community.',
    'body': '<p>ReDIB is the Unique Scientific and Technologic Infrastructure '
            '(ICTS) that brings together four leading biomedical imaging '
            'centers: BioImaC, TRIMA @ CNIC, Imaging La Fe and CIC '
            'biomaGUNE. We provide access to MRI, PET, SPECT, CT and '
            'radiochemistry technologies through competitive calls and '
            'on-demand access.</p>',
}


class Command(BaseCommand):
    help = (
        "Populate the marketing-site IA: section pages + content, "
        "ExternalLink snippets, and /actualidad redirect. Idempotent."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        es = Locale.objects.get(language_code='es')
        en = Locale.objects.get(language_code='en')

        home_es = HomePage.objects.filter(locale=es).first()
        home_en = HomePage.objects.filter(locale=en).first()
        if home_es is None or home_en is None:
            self.stderr.write(
                "HomePage ES/EN not found — run `marketing_init` first."
            )
            return

        self._refresh_homepage(home_es, HOMEPAGE_ES)
        self._refresh_homepage(home_en, HOMEPAGE_EN)
        self.stdout.write("Homepage hero/body refreshed (ES + EN).")

        # Section pages
        for spec in SECTIONS:
            self._upsert_section(home_es, home_en, en, spec)

        # ExternalLink snippets
        self._upsert_external_links(es, en)

        # Redirects for /actualidad -> /noticias (and EN equivalent)
        self._upsert_redirects()

        self.stdout.write(self.style.SUCCESS("populate_static_pages: done."))

    # ------------------------------------------------------------------
    # Section page upsert
    # ------------------------------------------------------------------

    def _upsert_section(self, home_es, home_en, en_locale, spec):
        cls = spec['page_class']
        es_slug = spec['es_slug']
        en_slug = spec['en_slug']

        # ES side: look up by slug under home_es. Slugs are unique per parent.
        es_page = (
            cls.objects.child_of(home_es).filter(slug=es_slug).first()
        )
        if es_page is None:
            es_page = cls(
                title=spec['es_title'],
                slug=es_slug,
                locale=home_es.locale,
                show_in_menus=True,
                **spec['es_fields'],
            )
            home_es.add_child(instance=es_page)
            es_page.save_revision().publish()
            es_page.refresh_from_db()
            self.stdout.write(
                f"  Created ES page: /{es_slug}/ (id={es_page.id})"
            )
        else:
            changed = False
            if es_page.title != spec['es_title']:
                es_page.title = spec['es_title']
                changed = True
            if not es_page.show_in_menus:
                es_page.show_in_menus = True
                changed = True
            for field, value in spec['es_fields'].items():
                if getattr(es_page, field) != value:
                    setattr(es_page, field, value)
                    changed = True
            if changed:
                es_page.save_revision().publish()
                es_page.refresh_from_db()
                self.stdout.write(
                    f"  Updated ES page: /{es_slug}/ (id={es_page.id})"
                )
            else:
                self.stdout.write(
                    f"  ES page already current: /{es_slug}/ "
                    f"(id={es_page.id})"
                )

        # EN side: look up by translation_key + locale=en.
        en_page = (
            cls.objects
            .filter(translation_key=es_page.translation_key, locale=en_locale)
            .first()
        )
        if en_page is None:
            en_page = es_page.copy_for_translation(en_locale)
            en_page.title = spec['en_title']
            en_page.slug = en_slug
            en_page.show_in_menus = True
            for field, value in spec['en_fields'].items():
                setattr(en_page, field, value)
            en_page.save_revision().publish()
            en_page.refresh_from_db()
            # Re-parent under EN homepage if copy_for_translation left it at root
            if en_page.get_parent().id != home_en.id:
                en_page.move(home_en, pos='last-child')
                en_page.refresh_from_db()
            self.stdout.write(
                f"  Created EN page: /en/{en_slug}/ (id={en_page.id})"
            )
        else:
            changed = False
            if en_page.title != spec['en_title']:
                en_page.title = spec['en_title']
                changed = True
            if en_page.slug != en_slug:
                en_page.slug = en_slug
                changed = True
            if not en_page.show_in_menus:
                en_page.show_in_menus = True
                changed = True
            for field, value in spec['en_fields'].items():
                if getattr(en_page, field) != value:
                    setattr(en_page, field, value)
                    changed = True
            if changed:
                en_page.save_revision().publish()
                en_page.refresh_from_db()
                self.stdout.write(
                    f"  Updated EN page: /en/{en_slug}/ (id={en_page.id})"
                )
            else:
                self.stdout.write(
                    f"  EN page already current: /en/{en_slug}/ "
                    f"(id={en_page.id})"
                )
            # Self-heal parent
            if en_page.get_parent().id != home_en.id:
                en_page.move(home_en, pos='last-child')
                en_page.refresh_from_db()
                self.stdout.write(
                    f"  Re-parented EN page under home_en: /en/{en_slug}/"
                )

    # ------------------------------------------------------------------
    # Homepage refresh
    # ------------------------------------------------------------------

    def _refresh_homepage(self, page, fields):
        changed = False
        for field, value in fields.items():
            if getattr(page, field) != value:
                setattr(page, field, value)
                changed = True
        if changed:
            page.save_revision().publish()

    # ------------------------------------------------------------------
    # ExternalLink snippets
    # ------------------------------------------------------------------

    def _upsert_external_links(self, es_locale, en_locale):
        order_counter = {ExternalLink.RESOURCE: 0, ExternalLink.INSTITUTIONAL: 0}

        for entry in RESOURCE_LINKS:
            order_counter[ExternalLink.RESOURCE] += 1
            self._upsert_link_pair(
                es_locale, en_locale, entry,
                category=ExternalLink.RESOURCE,
                order=order_counter[ExternalLink.RESOURCE],
            )
        for entry in INSTITUTIONAL_LINKS:
            order_counter[ExternalLink.INSTITUTIONAL] += 1
            self._upsert_link_pair(
                es_locale, en_locale, entry,
                category=ExternalLink.INSTITUTIONAL,
                order=order_counter[ExternalLink.INSTITUTIONAL],
            )

    def _upsert_link_pair(self, es_locale, en_locale, entry, *, category, order):
        # Find or create ES side: match on (locale=es, url) since titles are
        # the human-readable label and may be edited; url is the stable key.
        es_link = (
            ExternalLink.objects
            .filter(locale=es_locale, url=entry['url'])
            .first()
        )
        if es_link is None:
            es_link = ExternalLink.objects.create(
                title=entry['es_title'],
                url=entry['url'],
                description=entry['es_description'],
                category=category,
                order=order,
                locale=es_locale,
            )
            self.stdout.write(
                f"  Created ES ExternalLink: {entry['es_title']}"
            )
        else:
            changed = False
            for field, value in (
                ('title', entry['es_title']),
                ('description', entry['es_description']),
                ('category', category),
                ('order', order),
            ):
                if getattr(es_link, field) != value:
                    setattr(es_link, field, value)
                    changed = True
            if changed:
                es_link.save()
                self.stdout.write(
                    f"  Updated ES ExternalLink: {entry['es_title']}"
                )

        # EN translation — look up by translation_key + locale=en
        en_link = (
            ExternalLink.objects
            .filter(translation_key=es_link.translation_key, locale=en_locale)
            .first()
        )
        if en_link is None:
            en_link = ExternalLink.objects.create(
                title=entry['en_title'],
                url=entry['url'],
                description=entry['en_description'],
                category=category,
                order=order,
                locale=en_locale,
                translation_key=es_link.translation_key,
            )
            self.stdout.write(
                f"  Created EN ExternalLink: {entry['en_title']}"
            )
        else:
            changed = False
            for field, value in (
                ('title', entry['en_title']),
                ('description', entry['en_description']),
                ('category', category),
                ('order', order),
                ('url', entry['url']),
            ):
                if getattr(en_link, field) != value:
                    setattr(en_link, field, value)
                    changed = True
            if changed:
                en_link.save()
                self.stdout.write(
                    f"  Updated EN ExternalLink: {entry['en_title']}"
                )

    # ------------------------------------------------------------------
    # Redirects
    # ------------------------------------------------------------------

    def _upsert_redirects(self):
        site = Site.objects.filter(is_default_site=True).first()
        es = Locale.objects.get(language_code='es')
        en = Locale.objects.get(language_code='en')

        noticias_es = (
            Page.objects.filter(slug='noticias', locale=es).first()
        )
        noticias_en = (
            Page.objects.filter(slug='news', locale=en).first()
        )

        # /actualidad -> /noticias/ (ES) — the EN equivalent on the live site
        # is /present (per site-inventory) but the rebuild's EN slug is /news,
        # so we map both:
        #   /actualidad  -> /noticias/  (Wagtail redirect handles raw path)
        #   /present     -> /en/news/   (the EN side)
        redirect_specs = [
            {
                'old_path': '/actualidad',
                'redirect_page': noticias_es,
                'redirect_link': '/noticias/',
            },
            {
                'old_path': '/present',
                'redirect_page': noticias_en,
                'redirect_link': '/en/news/',
            },
        ]

        for spec in redirect_specs:
            old_path = Redirect.normalise_path(spec['old_path'])
            existing = Redirect.objects.filter(
                old_path=old_path, site=site
            ).first()
            if existing is None:
                Redirect.objects.create(
                    site=site,
                    old_path=old_path,
                    redirect_page=spec['redirect_page'],
                    redirect_link=(
                        spec['redirect_link']
                        if spec['redirect_page'] is None
                        else ''
                    ),
                    is_permanent=True,
                )
                self.stdout.write(
                    f"  Created redirect: {spec['old_path']} -> "
                    f"{spec['redirect_link']}"
                )
            else:
                # Self-heal target if needed
                changed = False
                if spec['redirect_page'] is not None:
                    if existing.redirect_page_id != spec['redirect_page'].id:
                        existing.redirect_page = spec['redirect_page']
                        existing.redirect_link = ''
                        changed = True
                else:
                    if existing.redirect_link != spec['redirect_link']:
                        existing.redirect_link = spec['redirect_link']
                        existing.redirect_page = None
                        changed = True
                if not existing.is_permanent:
                    existing.is_permanent = True
                    changed = True
                if changed:
                    existing.save()
                    self.stdout.write(
                        f"  Updated redirect: {spec['old_path']}"
                    )
                else:
                    self.stdout.write(
                        f"  Redirect already current: {spec['old_path']}"
                    )
