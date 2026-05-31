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
from marketing.management.commands.populate_equipment_nodes import (
    EQUIPMENT_INDEX_REFRESH,
    NODE_INDEX_REFRESH,
)
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
<p>Consulte también la
<a href="/documentacion/">documentación reguladora</a> del programa
(reglamento del Comité de Acceso, protocolos de acceso, planificación de
convocatorias) y el
<a href="/costes-de-acceso/">detalle de los costes asociados</a>.</p>
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
<p>See also the
<a href="/en/documentation/">governing documentation</a> (Access Committee
rules of procedure, access protocols, call planning) and the
<a href="/en/access-cost/">detailed access costs</a>.</p>
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
# /documentacion/ + /en/documentation/ — governance PDF index
# ---------------------------------------------------------------------------
#
# These pages list the 7 governance PDFs whose canonical filenames are
# documented in `docs/marketing/assets-manifest.md`. Until the PDFs are
# migrated into Wagtail Documents, the links here point at the live
# redib.net file URLs. Migrating the binaries themselves is a separate
# follow-up; the per-file URLs are based on the live filenames so the
# links resolve.
#
# (EN body translated from ES by Claude — no authoritative EN version
# exists on live redib.net.)

GOVERNANCE_DOCS = [
    {
        'es_title': 'REDIB-01-PDA. Reglamento del Comité de Acceso',
        'en_title': 'REDIB-01-PDA. Access Committee Rules of Procedure',
        'url': 'https://www.redib.net/upload/secciones-publicas/'
               'REDIB-01-PDA.%20Reglamento%20del%20Comit%C3%A9%20de%20Acceso.pdf',
    },
    {
        'es_title': 'REDIB-02-PDA. Protocolos de acceso',
        'en_title': 'REDIB-02-PDA. Access Protocols',
        'url': 'https://www.redib.net/upload/secciones-publicas/'
               'REDIB-02-pda%20Protocolos%20de%20acceso.pdf',
    },
    {
        'es_title': 'REDIB-03-PDC. Planificación de convocatorias',
        'en_title': 'REDIB-03-PDC. Call Planning',
        'url': 'https://www.redib.net/upload/secciones-publicas/'
               'REDIB-03-PDC.%20Planificaci%C3%B3n%20de%20convocatorias.pdf',
    },
    {
        'es_title': 'REDIB-04-SYR. Gestión de reclamaciones e incidencias',
        'en_title': 'REDIB-04-SYR. Complaint and Incident Management',
        'url': 'https://www.redib.net/upload/secciones-publicas/'
               'REDIB-04-SYR%20Gesti%C3%B3n%20de%20reclamaciones%20e%20incidencias.pdf',
    },
    {
        'es_title': 'REDIB-05-DDP. Ejercicio de derechos de datos personales',
        'en_title': 'REDIB-05-DDP. Exercise of Personal Data Rights',
        'url': 'https://www.redib.net/upload/secciones-publicas/'
               'REDIB-05-DDP%20Ejercicio%20de%20derechos%20de%20datos%20personales.pdf',
    },
    {
        'es_title': 'Acuerdo ReDIB de corresponsabilidad para la Gestión de Datos',
        'en_title': 'ReDIB Co-responsibility Agreement for Data Management',
        'url': 'https://www.redib.net/upload/secciones-publicas/'
               'Acuerdo%20ReDIB%20de%20corresponsabilidad%20para%20la%20Gesti%C3%B3n'
               '%20de%20Datos.pdf',
    },
    {
        'es_title': 'Guía de uso del portal de convocatorias',
        'en_title': 'Call portal user guide (Spanish)',
        'url': 'https://www.redib.net/upload/secciones-publicas/'
               'gu%C3%ADa%20de%20uso%20del%20portal%20de%20convocatorias.pdf',
    },
]


def _governance_docs_html(lang):
    """Build a <ul> of governance-doc links for the given language ('es' or 'en')."""
    title_key = 'es_title' if lang == 'es' else 'en_title'
    items = '\n'.join(
        f'<li><a href="{d["url"]}" target="_blank" rel="noopener">'
        f'{d[title_key]}</a></li>'
        for d in GOVERNANCE_DOCS
    )
    return f'<ul>\n{items}\n</ul>'


DOCUMENTACION_BODY_ES = f"""
<p>La gobernanza de la ICTS ReDIB y la operación del programa de acceso
abierto competitivo están reguladas por un conjunto de documentos públicos.
A continuación se enumeran los documentos vigentes; haga clic en cada
título para descargar el PDF correspondiente.</p>
<h2>Documentos reguladores</h2>
{_governance_docs_html('es')}
<p><em>Los PDFs se sirven actualmente desde el sitio anterior
(redib.net) y se migrarán a la biblioteca de documentos de este portal
en una fase posterior.</em></p>
"""

DOCUMENTACION_BODY_EN = f"""
<p>The governance of the ReDIB ICTS and the operation of the competitive
open-access programme are regulated by a set of public documents. The
current documents are listed below; click each title to download the
corresponding PDF.</p>
<h2>Governing documents</h2>
{_governance_docs_html('en')}
<p><em>The PDFs are currently served from the previous site
(redib.net) and will be migrated into this portal's document library in
a follow-up phase.</em></p>
"""

# ---------------------------------------------------------------------------
# /costes-de-acceso/ + /en/access-cost/ — access cost explainer
# ---------------------------------------------------------------------------
#
# Content faithful to the live ES page. EN translated from ES by Claude
# (no authoritative EN version exists on live redib.net).

COSTES_ACCESO_BODY_ES = """
<h2>Acceso a las instalaciones singulares de ReDIB</h2>
<p>ReDIB ofrece a la comunidad científica dos mecanismos de acceso a sus
instalaciones singulares:</p>
<h3>Acceso Abierto Competitivo (AAC)</h3>
<p>Es un mecanismo subvencionado, en el que se aplican tarifas ventajosas
que van desde la gratuidad del servicio (aplicando solo los costes de los
radiotrazadores y consumibles necesarios) hasta tarifas reducidas. El
detalle se publica en la sección <a href="/tarifas/">Tarifas</a>.</p>
<h3>Acceso a Demanda (AaD)</h3>
<p>Es un mecanismo no subvencionado, en el que se aplican las tarifas
aprobadas por cada nodo de ReDIB para sus diferentes servicios.</p>
<h2>Acceso a otras instalaciones de los nodos de ReDIB</h2>
<p>Los nodos que integran ReDIB disponen de otras infraestructuras que
permiten ofrecer servicios avanzados de imagen biológica. Estos servicios
se rigen por las tarifas aprobadas por cada uno de los nodos y se publican
en sus respectivas páginas web.</p>
<p>Para información detallada sobre tarifas específicas puede consultar la
sección <a href="/tarifas/">Tarifas</a> o contactar directamente con cada
nodo a través de la <a href="/contacto/">página de contacto</a>.</p>
"""

COSTES_ACCESO_BODY_EN = """
<h2>Access to ReDIB's essential facilities</h2>
<p>ReDIB offers the scientific community two mechanisms for accessing its
essential facilities:</p>
<h3>Competitive Open Access (AAC)</h3>
<p>A subsidized mechanism with advantageous rates ranging from free service
(applicants only cover the cost of radiotracers and consumables) to
reduced rates. Details are published in the
<a href="/en/rates/">Rates</a> section.</p>
<h3>On-Demand Access (AaD)</h3>
<p>A non-subsidized mechanism, in which the rates approved by each ReDIB
node for its different services apply.</p>
<h2>Access to other facilities of the ReDIB nodes</h2>
<p>The nodes that make up ReDIB host additional infrastructures that enable
advanced biological imaging services. These services are governed by the
rates approved by each node and are published on their respective
websites.</p>
<p>For detailed information on specific rates, see the
<a href="/en/rates/">Rates</a> section or contact each node directly via
the <a href="/en/contact/">contact page</a>.</p>
"""

# ---------------------------------------------------------------------------
# /politica-de-privacidad-y-cookies/ + /en/privacy-policy-and-cookies/
# ---------------------------------------------------------------------------
#
# Faithful Spanish content from the live page. EN translated from ES by
# Claude (no authoritative EN version exists on live redib.net) — review
# before public launch.

PRIVACY_BODY_ES = """
<h2>Política de Privacidad de ReDIB</h2>
<p>ReDIB ha adoptado las medidas necesarias para garantizar la seguridad,
integridad y confidencialidad de los datos de carácter personal recogidos
a través del sitio web <a href="https://www.redib.net/">https://www.redib.net/</a>,
conforme al artículo 13 del Reglamento General de Protección de Datos (RGPD).</p>
<h3>Corresponsables del tratamiento</h3>
<p>Los nodos de investigación que conforman la ICTS actúan como
corresponsables del tratamiento y han firmado un acuerdo de
corresponsabilidad que establece sus obligaciones respectivas en materia
de protección de datos.</p>
<h3>Finalidad del tratamiento</h3>
<p>Los datos se tratan para la evaluación de las solicitudes de acceso a
las instalaciones de la ICTS, la gestión de los servicios administrativos
y económicos asociados, y la comunicación con usuarios y potenciales
usuarios.</p>
<h3>Categorías de datos recabados</h3>
<ul>
<li>Datos identificativos: nombre, DNI/NIE, teléfono, dirección postal y
electrónica, firma.</li>
<li>Información académico-profesional: formación, titulación, experiencia.</li>
<li>Datos de empleo: empleador y puesto de trabajo.</li>
<li>Datos financieros: información bancaria para facturación.</li>
<li>Proyectos de investigación: título, código y fuente de financiación.</li>
</ul>
<h3>Base legal</h3>
<p>El tratamiento se basa en el consentimiento del usuario, prestado a
través del formulario de solicitud de acceso, conforme al artículo 6.1.a
del RGPD.</p>
<h3>Decisiones automatizadas</h3>
<p>No se realizan decisiones automatizadas con los datos personales
tratados.</p>
<h3>Cesiones de datos</h3>
<p>No se prevén cesiones de datos salvo aquellas exigidas expresamente por
los organismos públicos competentes en la evaluación de la actividad de
los nodos de la ICTS.</p>
<h3>Conservación de los datos</h3>
<p>Los datos personales incorporados al fichero automatizado USUARIOS ICTS
ReDIB se conservarán durante el tiempo necesario para cumplir con la
finalidad para la que fueron recabados, salvo que el usuario solicite su
supresión o que la normativa aplicable obligue a su bloqueo.</p>
<h3>Derechos del usuario</h3>
<p>Los usuarios pueden ejercer los derechos de acceso, rectificación,
supresión, portabilidad, limitación y oposición al tratamiento dirigiendo
su solicitud a <a href="mailto:gdpr@redib.net">gdpr@redib.net</a>, con
acreditación de identidad. El ejercicio es gratuito, salvo que las
solicitudes sean manifiestamente infundadas o repetitivas. El plazo
ordinario de respuesta es de un mes, prorrogable dos meses adicionales.
Los usuarios pueden además presentar reclamación ante la Agencia Española
de Protección de Datos.</p>

<h2>Política de Cookies</h2>
<p>ReDIB utiliza cookies para almacenar, acceder y tratar datos personales
derivados de las visitas al sitio web.</p>
<h3>¿Qué son las cookies?</h3>
<p>Las cookies son pequeños archivos de texto que se guardan en el
navegador del usuario y que facilitan la navegación por el sitio web y
permiten mejorar los servicios prestados mediante la gestión de sesiones
y la personalización del contenido.</p>
<h3>Cookies utilizadas en este sitio web</h3>
<ul>
<li><strong>Cookies técnicas propias:</strong> permiten la navegación y el
uso de los servicios del sitio web.</li>
<li><strong>Cookies analíticas de terceros:</strong> analizan el
comportamiento de los usuarios para mejorar los servicios.</li>
</ul>
<h3>Gestión de cookies</h3>
<table>
<thead>
<tr><th>Tipo</th><th>Información</th><th>Finalidad</th><th>Duración</th><th>Desactivación</th></tr>
</thead>
<tbody>
<tr><td>Propia</td><td>Estado de sesión</td><td>Gestión de sesión</td><td>Sesión</td><td>No es posible</td></tr>
<tr><td>Propia</td><td>Aceptación binaria</td><td>Registro del consentimiento de cookies</td><td>1 año</td><td>No es posible</td></tr>
<tr><td>Google Analytics</td><td>Analítica de visitas</td><td>Análisis del comportamiento del usuario</td><td>Sesión / 2 años</td><td>Configuración del navegador</td></tr>
</tbody>
</table>
<h3>Retirada del consentimiento</h3>
<p>Los usuarios pueden retirar el consentimiento al uso de cookies en
cualquier momento y eliminar las cookies almacenadas a través de la
configuración del navegador. La desactivación no impide la navegación,
pero puede limitar la funcionalidad de algunos servicios.</p>
<h3>Modificaciones</h3>
<p>Esta política puede modificarse en función de los requisitos legales o
de los cambios en los tipos de cookies utilizadas. Se recomienda revisarla
periódicamente.</p>
"""

PRIVACY_BODY_EN = """
<h2>ReDIB Privacy Policy</h2>
<p>ReDIB has adopted the measures required to guarantee the security,
integrity and confidentiality of personal data collected through the
website <a href="https://www.redib.net/">https://www.redib.net/</a>, in
accordance with Article 13 of the General Data Protection Regulation
(GDPR).</p>
<h3>Joint controllers</h3>
<p>The research nodes that make up the ICTS act as joint controllers of
the processing and have signed a co-responsibility agreement setting out
their respective data-protection obligations.</p>
<h3>Purpose of processing</h3>
<p>Data are processed for the evaluation of access requests to the ICTS
facilities, the management of the associated administrative and financial
services, and communication with users and potential users.</p>
<h3>Categories of data collected</h3>
<ul>
<li>Identification data: name, ID number, phone, postal and email
addresses, signature.</li>
<li>Academic and professional information: training, qualifications,
experience.</li>
<li>Employment data: employer and position.</li>
<li>Financial data: banking details for invoicing.</li>
<li>Research projects: title, code and funding source.</li>
</ul>
<h3>Legal basis</h3>
<p>Processing is based on the user's consent, given through the access
application form, in accordance with Article 6.1.a of the GDPR.</p>
<h3>Automated decision-making</h3>
<p>No automated decisions are taken with the personal data processed.</p>
<h3>Data transfers</h3>
<p>No transfers of data are foreseen except those expressly required by
the competent public bodies evaluating the activity of the ICTS nodes.</p>
<h3>Data retention</h3>
<p>Personal data added to the USUARIOS ICTS ReDIB automated file are kept
for as long as necessary to fulfil the purpose for which they were
collected, unless the user requests their deletion or applicable
regulations require them to be blocked.</p>
<h3>User rights</h3>
<p>Users may exercise their rights of access, rectification, deletion,
portability, limitation and opposition by sending their request to
<a href="mailto:gdpr@redib.net">gdpr@redib.net</a>, with proof of
identity. Exercising these rights is free of charge unless requests are
manifestly unfounded or repetitive. The standard response time is one
month, extendable by a further two months. Users may also lodge a
complaint with the Spanish Data Protection Authority.</p>

<h2>Cookies Policy</h2>
<p>ReDIB uses cookies to store, access and process personal data derived
from visits to the website.</p>
<h3>What are cookies?</h3>
<p>Cookies are small text files saved in the user's browser that
facilitate navigation through the website and allow services to be
improved by managing sessions and personalising content.</p>
<h3>Cookies used on this website</h3>
<ul>
<li><strong>Own technical cookies:</strong> enable navigation and use of
the website's services.</li>
<li><strong>Third-party analytical cookies:</strong> analyse user
behaviour to improve services.</li>
</ul>
<h3>Cookie management</h3>
<table>
<thead>
<tr><th>Type</th><th>Information</th><th>Purpose</th><th>Duration</th><th>Deactivation</th></tr>
</thead>
<tbody>
<tr><td>Own</td><td>Session state</td><td>Session management</td><td>Session</td><td>Not possible</td></tr>
<tr><td>Own</td><td>Binary acceptance</td><td>Cookie-consent tracking</td><td>1 year</td><td>Not possible</td></tr>
<tr><td>Google Analytics</td><td>Visit analytics</td><td>User-behaviour analysis</td><td>Session / 2 years</td><td>Browser settings</td></tr>
</tbody>
</table>
<h3>Withdrawing consent</h3>
<p>Users may withdraw consent to the use of cookies at any time and delete
stored cookies through their browser settings. Disabling cookies does not
prevent navigation but may limit the functionality of some services.</p>
<h3>Changes</h3>
<p>This policy may be amended in line with legal requirements or changes
in the types of cookies used. Users are encouraged to review it
periodically.</p>
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
        # NodeIndexPage and EquipmentIndexPage intro/body are owned by
        # populate_equipment_nodes — we reuse those constants here so both
        # commands write identical content (avoids a tug-of-war that breaks
        # idempotency). See populate_equipment_nodes.NODE_INDEX_REFRESH /
        # EQUIPMENT_INDEX_REFRESH.
        'es_title': 'Equipamiento',
        'es_slug': 'equipamiento',
        'en_title': 'Equipment',
        'en_slug': 'equipment',
        'page_class': EquipmentIndexPage,
        'es_fields': EQUIPMENT_INDEX_REFRESH['es'],
        'en_fields': EQUIPMENT_INDEX_REFRESH['en'],
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
        # NodeIndexPage intro/body owned by populate_equipment_nodes —
        # see NODE_INDEX_REFRESH. NodeIndexPage has no `body` field, so
        # _upsert_section skips any 'body' key for unknown fields below.
        'es_title': 'Nodos',
        'es_slug': 'nodos',
        'en_title': 'Nodes',
        'en_slug': 'nodes',
        'page_class': NodeIndexPage,
        'es_fields': {'intro': NODE_INDEX_REFRESH['es']['intro']},
        'en_fields': {'intro': NODE_INDEX_REFRESH['en']['intro']},
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
# Extra pages — sub-pages that live under a section parent (not under
# HomePage directly) or otherwise need show_in_menus=False. These are
# inventory-deferred pages restored in Phase 5b.
#
# Each spec adds an `es_parent_slug` (slug of the ES parent page under
# home_es; None means "directly under home_es") and `en_parent_slug`
# (same for EN). All extra pages are created with show_in_menus=False so
# they don't bloat the main nav — they're linked from body copy and the
# footer.
# ---------------------------------------------------------------------------

EXTRA_PAGES = [
    {
        # /documentacion/ + /en/documentation/  (top-level under HomePage)
        # Logically belongs to the Access section, but kept at root to match
        # the live redib.net URL and the anchor in the Acceso body. Linked
        # from there + the Documentación footer block.
        'es_title': 'Documentación',
        'es_slug': 'documentacion',
        'en_title': 'Documentation',
        'en_slug': 'documentation',
        'page_class': StandardPage,
        'es_parent_slug': None,    # under home_es
        'en_parent_slug': None,    # under home_en
        'es_fields': {
            'intro': 'Documentación reguladora de la ICTS ReDIB: reglamento '
                     'del Comité de Acceso, protocolos de acceso, planificación '
                     'de convocatorias y otros documentos públicos.',
            'body': DOCUMENTACION_BODY_ES,
        },
        'en_fields': {
            'intro': 'Governing documentation of the ReDIB ICTS: Access '
                     'Committee rules of procedure, access protocols, call '
                     'planning and other public documents.',
            'body': DOCUMENTACION_BODY_EN,
        },
    },
    {
        # /costes-de-acceso/ + /en/access-cost/  (top-level under HomePage)
        # Same rationale as /documentacion/ above: belongs to Access logically
        # but lives at root to match the live URL and the Acceso anchor.
        'es_title': 'Costes de acceso',
        'es_slug': 'costes-de-acceso',
        'en_title': 'Access cost',
        'en_slug': 'access-cost',
        'page_class': StandardPage,
        'es_parent_slug': None,    # under home_es
        'en_parent_slug': None,    # under home_en
        'es_fields': {
            'intro': 'Mecanismos de acceso a las instalaciones esenciales de '
                     'ReDIB y a otras infraestructuras de los nodos: AAC '
                     'subvencionado y AaD no subvencionado.',
            'body': COSTES_ACCESO_BODY_ES,
        },
        'en_fields': {
            'intro': 'Access mechanisms for ReDIB\'s essential facilities and '
                     'for other infrastructures at the nodes: subsidized AAC '
                     'and non-subsidized AaD.',
            'body': COSTES_ACCESO_BODY_EN,
        },
    },
    {
        # /politica-de-privacidad-y-cookies/  (top-level under home_es)
        # /en/privacy-policy-and-cookies/     (top-level under home_en)
        'es_title': 'Política de privacidad y cookies',
        'es_slug': 'politica-de-privacidad-y-cookies',
        'en_title': 'Privacy policy and cookies',
        'en_slug': 'privacy-policy-and-cookies',
        'page_class': StandardPage,
        'es_parent_slug': None,    # under home_es
        'en_parent_slug': None,    # under home_en
        'es_fields': {
            'intro': 'Información sobre el tratamiento de datos personales y '
                     'el uso de cookies en el sitio web de ReDIB conforme al '
                     'RGPD.',
            'body': PRIVACY_BODY_ES,
        },
        'en_fields': {
            'intro': 'Information on the processing of personal data and the '
                     'use of cookies on the ReDIB website under the GDPR.',
            'body': PRIVACY_BODY_EN,
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

        es_changed = self._refresh_homepage(home_es, HOMEPAGE_ES)
        en_changed = self._refresh_homepage(home_en, HOMEPAGE_EN)
        if es_changed or en_changed:
            self.stdout.write(
                f"Homepage hero/body updated ("
                f"ES: {'changed' if es_changed else 'unchanged'}, "
                f"EN: {'changed' if en_changed else 'unchanged'})."
            )
        else:
            self.stdout.write("Homepage already current (ES + EN).")

        # Section pages
        for spec in SECTIONS:
            self._upsert_section(home_es, home_en, en, spec)

        # Extra pages (sub-pages of section parents, or top-level pages with
        # show_in_menus=False — restored in Phase 5b)
        for spec in EXTRA_PAGES:
            self._upsert_extra_page(home_es, home_en, en, spec)

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
    # Extra page upsert (arbitrary parent + show_in_menus=False)
    # ------------------------------------------------------------------

    def _upsert_extra_page(self, home_es, home_en, en_locale, spec):
        """Upsert a non-section page (child of another section, or top-level
        with show_in_menus=False).

        Mirrors `_upsert_section` but resolves the parent dynamically via
        `es_parent_slug` / `en_parent_slug` (None = HomePage).
        """
        cls = spec['page_class']
        es_slug = spec['es_slug']
        en_slug = spec['en_slug']

        # Resolve ES parent
        es_parent_slug = spec.get('es_parent_slug')
        if es_parent_slug is None:
            es_parent = home_es
        else:
            es_parent = (
                Page.objects.child_of(home_es)
                .filter(slug=es_parent_slug, locale=home_es.locale)
                .specific()
                .first()
            )
            if es_parent is None:
                self.stderr.write(
                    f"  ERROR: ES parent /{es_parent_slug}/ not found for "
                    f"/{es_slug}/ — skipping"
                )
                return

        # ES side: look up by slug under es_parent.
        es_page = (
            cls.objects.child_of(es_parent).filter(slug=es_slug).first()
        )
        if es_page is None:
            es_page = cls(
                title=spec['es_title'],
                slug=es_slug,
                locale=home_es.locale,
                show_in_menus=False,
                **spec['es_fields'],
            )
            es_parent.add_child(instance=es_page)
            es_page.save_revision().publish()
            es_page.refresh_from_db()
            self.stdout.write(
                f"  Created ES extra page: {es_page.url} (id={es_page.id})"
            )
        else:
            changed = False
            if es_page.title != spec['es_title']:
                es_page.title = spec['es_title']
                changed = True
            if es_page.show_in_menus:
                es_page.show_in_menus = False
                changed = True
            for field, value in spec['es_fields'].items():
                if getattr(es_page, field) != value:
                    setattr(es_page, field, value)
                    changed = True
            if changed:
                es_page.save_revision().publish()
                es_page.refresh_from_db()
                self.stdout.write(
                    f"  Updated ES extra page: {es_page.url} (id={es_page.id})"
                )
            else:
                self.stdout.write(
                    f"  ES extra page already current: {es_page.url} "
                    f"(id={es_page.id})"
                )

        # Resolve EN parent
        en_parent_slug = spec.get('en_parent_slug')
        if en_parent_slug is None:
            en_parent = home_en
        else:
            en_parent = (
                Page.objects.child_of(home_en)
                .filter(slug=en_parent_slug, locale=en_locale)
                .specific()
                .first()
            )
            if en_parent is None:
                self.stderr.write(
                    f"  ERROR: EN parent /en/{en_parent_slug}/ not found for "
                    f"/en/{en_slug}/ — skipping"
                )
                return

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
            en_page.show_in_menus = False
            for field, value in spec['en_fields'].items():
                setattr(en_page, field, value)
            en_page.save_revision().publish()
            en_page.refresh_from_db()
            # Re-parent under en_parent if copy_for_translation placed it elsewhere
            if en_page.get_parent().id != en_parent.id:
                en_page.move(en_parent, pos='last-child')
                en_page.refresh_from_db()
            self.stdout.write(
                f"  Created EN extra page: {en_page.url} (id={en_page.id})"
            )
        else:
            changed = False
            if en_page.title != spec['en_title']:
                en_page.title = spec['en_title']
                changed = True
            if en_page.slug != en_slug:
                en_page.slug = en_slug
                changed = True
            if en_page.show_in_menus:
                en_page.show_in_menus = False
                changed = True
            for field, value in spec['en_fields'].items():
                if getattr(en_page, field) != value:
                    setattr(en_page, field, value)
                    changed = True
            if changed:
                en_page.save_revision().publish()
                en_page.refresh_from_db()
                self.stdout.write(
                    f"  Updated EN extra page: {en_page.url} (id={en_page.id})"
                )
            else:
                self.stdout.write(
                    f"  EN extra page already current: {en_page.url} "
                    f"(id={en_page.id})"
                )
            # Self-heal parent
            if en_page.get_parent().id != en_parent.id:
                en_page.move(en_parent, pos='last-child')
                en_page.refresh_from_db()
                self.stdout.write(
                    f"  Re-parented EN extra page: {en_page.url}"
                )

    # ------------------------------------------------------------------
    # Homepage refresh
    # ------------------------------------------------------------------

    def _refresh_homepage(self, page, fields):
        """Compare-and-skip write to HomePage. Returns True iff anything changed."""
        changed = False
        for field, value in fields.items():
            if getattr(page, field) != value:
                setattr(page, field, value)
                changed = True
        if changed:
            page.save_revision().publish()
        return changed

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
