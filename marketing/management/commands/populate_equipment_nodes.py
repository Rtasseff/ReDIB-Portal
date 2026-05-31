"""Populate Nodes (4 NodePages) and Equipment categories (4 EquipmentCategoryPages)
in both locales — Phase 3c of the marketing-site rebuild.

Idempotent: safe to run repeatedly.

Live-query pattern:
  - NodePages link via `related_core_node` FK to the portal's `core.Node`
    rows. The page renders its equipment list live from
    `node.equipment.filter(is_active=True)`.
  - EquipmentCategoryPages filter `core.Equipment` by `area_key` (one of
    `clinical`, `preclinical`, `radiochemistry`, or `''` for Análisis which
    has no live equipment query — it is a pure editorial page).

This command does NOT create or modify `core.Node` / `core.Equipment` rows.
If a node is missing from the portal DB, the matching NodePage is still
created (with editorial chrome) but `related_core_node` is left null and
the template falls back to an "equipment list coming soon" notice.

Also refreshes the NodeIndexPage and EquipmentIndexPage intro/body so the
section landing pages render the correct copy in both locales.
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from wagtail.images import get_image_model
from wagtail.models import Locale

from core.models import Node, Equipment
from marketing.management._image_utils import get_or_create_image
from marketing.models import (
    EquipmentCategoryPage,
    EquipmentIndexPage,
    NodeIndexPage,
    NodePage,
)


# ---------------------------------------------------------------------------
# Node specs (content drawn from docs/marketing/site-inventory.md, "Node:"
# subsections). `core_node_codes` lists every code variant that may identify
# the node in the portal DB (the dev fixture uses uppercase like `BIOIMAC`;
# prod loaders may use other conventions). We try each in order.
# ---------------------------------------------------------------------------

NODE_SPECS = [
    {
        # BioImaC — Centro de BioImagen Complutense (Madrid / UCM)
        'es_title': 'BioImaC',
        'es_slug': 'bioimac',
        'en_title': 'BioImaC',
        'en_slug': 'bioimac',
        'core_node_codes': ['BIOIMAC', 'bioimac', 'BIOI'],
        'core_node_name_contains': 'BioImaC',
        'hero_url': (
            'https://www.redib.net/upload/secciones-publicas/'
            'imagenbioimac_6c.jpg'
        ),
        'hero_slug': 'bioimac-hero',
        'es_intro': (
            'Centro de BioImagen Complutense (Universidad Complutense de '
            'Madrid). Nodo de imagen molecular y multimodal con RM de campo '
            'alto y dedicación preclínica.'
        ),
        'es_body': (
            '<p>BioImaC, el Centro de BioImagen Complutense de la Universidad '
            'Complutense de Madrid, alberga el nodo madrileño de ReDIB '
            'dedicado a imagen molecular preclínica de alto campo. Su parque '
            'instrumental incluye un sistema híbrido PET-RM 9.4 T Bruker '
            'BioSpec con CryoProbe y un escáner RM 1 T Bruker ICON, junto a '
            'instalaciones de imagen óptica y soporte experimental.</p>'
            '<p>BioImaC se ofrece como infraestructura de acceso abierto a '
            'investigadores académicos y de la industria que requieran '
            'imagen de pequeño animal con la mayor sensibilidad y resolución '
            'molecular.</p>'
        ),
        'es_location': (
            'Paseo de Juan XXIII, nº 1, 28040 Madrid'
        ),
        'es_contact': (
            '<p>Teléfono: +34 913 94 32 72<br>'
            'Web: <a href="https://www.ucm.es/bioimagen/" target="_blank" '
            'rel="noopener">cai.ucm.es/bioimagen/</a></p>'
        ),
        'en_intro': (
            'Centro de BioImagen Complutense (Complutense University of '
            'Madrid). Molecular and multimodal imaging node with high-field '
            'MRI and a preclinical focus.'
        ),
        'en_body': (
            '<p>BioImaC, the Centro de BioImagen Complutense at the '
            'Complutense University of Madrid, hosts the Madrid ReDIB node '
            'dedicated to high-field preclinical molecular imaging. Its '
            'instrument park includes a hybrid 9.4 T Bruker BioSpec PET-MRI '
            'system with CryoProbe and a 1 T Bruker ICON MRI scanner, '
            'alongside optical-imaging and experimental-support '
            'facilities.</p>'
            '<p>BioImaC is offered as open-access infrastructure to '
            'academic and industry researchers requiring small-animal '
            'imaging with the highest molecular sensitivity and '
            'resolution.</p>'
        ),
        'en_location': (
            'Paseo de Juan XXIII, nº 1, 28040 Madrid, Spain'
        ),
        'en_contact': (
            '<p>Phone: +34 913 94 32 72<br>'
            'Web: <a href="https://www.ucm.es/bioimagen/" target="_blank" '
            'rel="noopener">cai.ucm.es/bioimagen/</a></p>'
        ),
    },
    {
        # CNIC / TRIMA@CNIC
        'es_title': 'TRIMA @ CNIC',
        'es_slug': 'cnic',
        'en_title': 'TRIMA @ CNIC',
        'en_slug': 'cnic',
        'core_node_codes': ['CNIC', 'cnic', 'TRIMA'],
        'core_node_name_contains': 'CNIC',
        'hero_url': (
            'https://www.redib.net/upload/secciones-publicas/'
            'prueba_6c.jpg'
        ),
        'hero_slug': 'cnic-hero',
        'es_intro': (
            'TRIMA @ CNIC — Centro Nacional de Investigaciones '
            'Cardiovasculares Carlos III. Nodo translacional con imagen '
            'clínica y preclínica en un único campus.'
        ),
        'es_body': (
            '<p>TRIMA, la unidad de Imagen Avanzada Traslacional del Centro '
            'Nacional de Investigaciones Cardiovasculares Carlos III '
            '(CNIC), opera el nodo ReDIB madrileño con una vocación '
            'translacional explícita: imagen clínica y preclínica en el '
            'mismo edificio facilitan la transferencia bidireccional de '
            'protocolos entre modelos animales y pacientes.</p>'
            '<p>El parque instrumental incluye sistemas Molecubes PET/SPECT/CT, '
            'RM 3 T Philips Elition, RM 7 T Agilent-Varian, PET-TAC Philips '
            'Vereos, microscopía TIRF Leica, tomografía de fluorescencia '
            'FMT Perkin Elmer y 3D IVIS Perkin Elmer 200.</p>'
        ),
        'es_location': (
            'C/ Melchor Fernández Almagro, 3, 28029 Madrid'
        ),
        'es_contact': (
            '<p>Teléfono: +34 914 53 12 00<br>'
            'Web: <a href="https://www.cnic.es/" target="_blank" '
            'rel="noopener">cnic.es</a></p>'
        ),
        'en_intro': (
            'TRIMA @ CNIC — Centro Nacional de Investigaciones '
            'Cardiovasculares Carlos III. Translational node with clinical '
            'and preclinical imaging on a single campus.'
        ),
        'en_body': (
            '<p>TRIMA, the Translational Advanced Imaging unit at the '
            'Spanish National Centre for Cardiovascular Research (CNIC), '
            'runs the Madrid ReDIB node with an explicitly translational '
            'remit: clinical and preclinical imaging share the same '
            'building, easing bidirectional protocol transfer between '
            'animal models and patients.</p>'
            '<p>The instrument park includes Molecubes PET/SPECT/CT '
            'systems, a 3 T Philips Elition MRI, a 7 T Agilent-Varian MRI, '
            'a Philips Vereos PET-CT, Leica TIRF microscopy, Perkin Elmer '
            'FMT fluorescence tomography and a Perkin Elmer 3D IVIS 200.</p>'
        ),
        'en_location': (
            'C/ Melchor Fernández Almagro, 3, 28029 Madrid, Spain'
        ),
        'en_contact': (
            '<p>Phone: +34 914 53 12 00<br>'
            'Web: <a href="https://www.cnic.es/" target="_blank" '
            'rel="noopener">cnic.es</a></p>'
        ),
    },
    {
        # Imaging La Fe (Valencia)
        'es_title': 'Imaging La Fe',
        'es_slug': 'imaging-la-fe',
        'en_title': 'Imaging La Fe',
        'en_slug': 'imaging-la-fe',
        'core_node_codes': ['LAFE', 'lafe', 'IMG_LAFE', 'IMAGING_LAFE'],
        'core_node_name_contains': 'La Fe',
        'hero_url': (
            'https://www.redib.net/upload/secciones-publicas/'
            'imagenlafe_6c.jpg'
        ),
        'hero_slug': 'imaging-la-fe-hero',
        'es_intro': (
            'Nodo hospitalario en el Hospital Universitario y Politécnico '
            'La Fe, Valencia. Imagen clínica de alta gama, PET-RM híbrido '
            'y un laboratorio de imágenes computacionales biomédicas.'
        ),
        'es_body': (
            '<p>Imaging La Fe es el nodo hospitalario de ReDIB, integrado '
            'en el Hospital Universitario y Politécnico La Fe de Valencia. '
            'Reúne capacidades de imagen clínica de alta gama —TAC-MDCT '
            'Philips Brilliance iCT, RM 3 T Philips Achieva TX y un '
            'PET-RM 3 T General Electric SIGNA— junto al Laboratorio de '
            'Imágenes Computacionales Biomédicas, dedicado al desarrollo '
            'y validación de algoritmos cuantitativos y de inteligencia '
            'artificial.</p>'
            '<p>Su entorno asistencial-académico permite el acceso a datos '
            'clínicos reales bajo los marcos éticos correspondientes y la '
            'traslación rápida de los desarrollos a la práctica '
            'hospitalaria.</p>'
        ),
        'es_location': (
            'Avda. Fernando Abril Martorell, 106, planta -1, '
            '46026 Valencia'
        ),
        'es_contact': (
            '<p>Teléfono: +34 961 24 40 09<br>'
            'Correo: <a href="mailto:gibi230@iislafe.es">gibi230@iislafe.es</a><br>'
            'Web: <a href="https://acim.lafe.san.gva.es/acim/" target="_blank" '
            'rel="noopener">acim.lafe.san.gva.es/acim/</a></p>'
        ),
        'en_intro': (
            'Hospital-based node at La Fe University and Polytechnic '
            'Hospital, Valencia. High-end clinical imaging, hybrid PET-MRI '
            'and a biomedical computational-imaging lab.'
        ),
        'en_body': (
            '<p>Imaging La Fe is the hospital-based ReDIB node, embedded '
            'in the La Fe University and Polytechnic Hospital in '
            'Valencia. It brings together high-end clinical imaging '
            '— a Philips Brilliance iCT TAC-MDCT, a 3 T Philips Achieva '
            'TX MRI and a 3 T GE SIGNA PET-MRI — together with the '
            'Biomedical Computational Imaging Laboratory, dedicated to '
            'developing and validating quantitative and AI-based '
            'algorithms.</p>'
            '<p>Its clinical-academic setting enables access to real '
            'clinical data under the relevant ethics frameworks and '
            'rapid translation of developments into hospital practice.</p>'
        ),
        'en_location': (
            'Avda. Fernando Abril Martorell, 106, level -1, '
            '46026 Valencia, Spain'
        ),
        'en_contact': (
            '<p>Phone: +34 961 24 40 09<br>'
            'Email: <a href="mailto:gibi230@iislafe.es">gibi230@iislafe.es</a><br>'
            'Web: <a href="https://acim.lafe.san.gva.es/acim/" target="_blank" '
            'rel="noopener">acim.lafe.san.gva.es/acim/</a></p>'
        ),
    },
    {
        # CIC biomaGUNE (San Sebastián)
        'es_title': 'CIC biomaGUNE',
        'es_slug': 'cic-biomagune',
        'en_title': 'CIC biomaGUNE',
        'en_slug': 'cic-biomagune',
        'core_node_codes': ['CICBIO', 'cicbio', 'CICBIOMAGUNE', 'BIOMAGUNE'],
        'core_node_name_contains': 'biomaGUNE',
        'hero_url': (
            'https://www.redib.net/upload/secciones-publicas/'
            '124-24433742634-o1_6c.jpg'
        ),
        'hero_slug': 'cic-biomagune-hero',
        'es_intro': (
            'Centro de Investigación Cooperativa en Biomateriales, San '
            'Sebastián. El nodo más completo de la red, con ciclotrón '
            'propio y laboratorio de radioquímica.'
        ),
        'es_body': (
            '<p>CIC biomaGUNE, el Centro de Investigación Cooperativa en '
            'Biomateriales de San Sebastián, opera el nodo donostiarra de '
            'ReDIB. Es el nodo instrumentalmente más rico de la red: '
            'integra imagen híbrida PET-SPECT-TAC Molecubes, RM 7 T '
            'Bruker BioSpec, RM 11,7 T Bruker BioSpec, sistema multimodal '
            'MILabs VECtor, ciclotrón IBA 9/18 y un Laboratorio de '
            'Radioquímica con capacidad de síntesis de radiotrazadores '
            'PET de uso interno y externo.</p>'
            '<p>La combinación de imagen molecular, química de '
            'radiotrazadores y producción de isótopos hace de CIC '
            'biomaGUNE el referente nacional en imagen molecular '
            'completa.</p>'
        ),
        'es_location': (
            'Pº Miramón, 194, 20009 Donostia – San Sebastián'
        ),
        'es_contact': (
            '<p>Teléfono: +34 943 00 53 36<br>'
            'Web: <a href="https://www.cicbiomagune.es/" target="_blank" '
            'rel="noopener">cicbiomagune.es</a></p>'
        ),
        'en_intro': (
            'Cooperative Research Centre in Biomaterials, San Sebastián. '
            'The most instrument-rich node in the network, with its own '
            'cyclotron and radiochemistry lab.'
        ),
        'en_body': (
            '<p>CIC biomaGUNE, the Cooperative Research Centre in '
            'Biomaterials in San Sebastián, runs the Donostia ReDIB '
            'node. It is the most instrument-rich node in the network: '
            'it brings together Molecubes hybrid PET-SPECT-CT, a 7 T '
            'Bruker BioSpec MRI, an 11.7 T Bruker BioSpec MRI, the '
            'MILabs VECtor multimodal system, an IBA 9/18 cyclotron and '
            'a Radiochemistry Laboratory capable of synthesising PET '
            'radiotracers for both internal and external use.</p>'
            '<p>The combination of molecular imaging, radiotracer '
            'chemistry and isotope production makes CIC biomaGUNE the '
            'Spanish reference for end-to-end molecular imaging.</p>'
        ),
        'en_location': (
            'Pº Miramón, 194, 20009 Donostia – San Sebastián, Spain'
        ),
        'en_contact': (
            '<p>Phone: +34 943 00 53 36<br>'
            'Web: <a href="https://www.cicbiomagune.es/" target="_blank" '
            'rel="noopener">cicbiomagune.es</a></p>'
        ),
    },
]


# ---------------------------------------------------------------------------
# Equipment-category specs. `area_key` matches `core.Equipment.area` values
# verified in core/models.py: 'clinical', 'preclinical', 'radiochemistry'.
# Análisis has no area mapping (it's pure analytics) — area_key='' and the
# page renders only its editorial body.
# ---------------------------------------------------------------------------

CATEGORY_SPECS = [
    {
        'es_title': 'Imagen Clínica',
        'es_slug': 'imagen-clinica',
        'en_title': 'Clinical Imaging',
        'en_slug': 'clinical-imaging',
        'area_key': 'clinical',
        'hero_url': (
            'https://www.redib.net/upload/secciones-publicas/'
            'clinical-image_6c.jpg'
        ),
        'hero_slug': 'clinical-imaging-hero',
        'es_intro': (
            'Equipamiento de imagen clínica disponible en la red ReDIB: '
            'resonancia magnética 3T, PET-RM híbrida, PET-CT digital y '
            'TAC multicorte de alta resolución.'
        ),
        'es_body': (
            '<p>La oferta de imagen clínica de ReDIB cubre las modalidades '
            'morfológicas y funcionales de mayor complejidad: PET-RM '
            'híbrida, resonancia magnética de 3 T, PET-TAC digital y TAC '
            'multidetector de última generación. La instrumentación está '
            'distribuida principalmente entre los nodos de Imaging La Fe '
            '(Valencia) y TRIMA @ CNIC (Madrid), ambos con experiencia '
            'consolidada en estudios traslacionales y multicéntricos.</p>'
            '<p>Los equipos relacionados a continuación se cargan en vivo '
            'desde el portal y reflejan el estado actual de la oferta '
            'esencial de la ICTS.</p>'
        ),
        'en_intro': (
            'Clinical imaging equipment available across the ReDIB '
            'network: 3T MRI, hybrid PET-MRI, digital PET-CT and '
            'high-resolution multi-detector CT.'
        ),
        'en_body': (
            '<p>The ReDIB clinical-imaging offering covers the most '
            'demanding morphological and functional modalities: hybrid '
            'PET-MRI, 3 T MRI, digital PET-CT and latest-generation '
            'multi-detector CT. The instrumentation sits mainly across '
            'the Imaging La Fe (Valencia) and TRIMA @ CNIC (Madrid) '
            'nodes, both with solid experience in translational and '
            'multi-centre studies.</p>'
            '<p>The equipment listed below is loaded live from the '
            'portal and reflects the current state of the ICTS '
            'essential-facility offering.</p>'
        ),
    },
    {
        'es_title': 'Imagen Preclínica',
        'es_slug': 'imagen-preclinica',
        'en_title': 'Preclinical Imaging',
        'en_slug': 'preclinical-imaging',
        'area_key': 'preclinical',
        'hero_url': (
            'https://www.redib.net/upload/secciones-publicas/'
            'preclinical-imaging-001_6c.jpg'
        ),
        'hero_slug': 'preclinical-imaging-hero',
        'es_intro': (
            'Imagen de pequeño animal con resonancia magnética de alto '
            'campo (7 T, 9.4 T, 11.7 T), sistemas PET-SPECT-CT y métodos '
            'ópticos avanzados.'
        ),
        'es_body': (
            '<p>La imagen preclínica es la base histórica de ReDIB. La '
            'red ofrece resonancia magnética de campo extremadamente '
            'alto (7 T, 9.4 T y 11.7 T), sistemas híbridos '
            'PET-SPECT-CT (Molecubes y MILabs VECtor) y técnicas '
            'ópticas avanzadas como microscopía TIRF, tomografía de '
            'fluorescencia (FMT) e imagen bioluminiscente 3D (IVIS).</p>'
            '<p>La distribución entre BioImaC, TRIMA @ CNIC y CIC '
            'biomaGUNE garantiza acceso geográfico y diversidad '
            'instrumental dentro del territorio español.</p>'
        ),
        'en_intro': (
            'Small-animal imaging with high-field MRI (7 T, 9.4 T, '
            '11.7 T), PET-SPECT-CT systems and advanced optical '
            'methods.'
        ),
        'en_body': (
            '<p>Preclinical imaging is the historical core of ReDIB. '
            'The network offers extremely high-field MRI (7 T, 9.4 T '
            'and 11.7 T), hybrid PET-SPECT-CT systems (Molecubes and '
            'MILabs VECtor) and advanced optical techniques such as '
            'TIRF microscopy, fluorescence tomography (FMT) and 3D '
            'bioluminescence imaging (IVIS).</p>'
            '<p>The distribution across BioImaC, TRIMA @ CNIC and '
            'CIC biomaGUNE ensures geographical reach and '
            'instrumental diversity within Spain.</p>'
        ),
    },
    {
        # Análisis — no live equipment query. Pure editorial.
        'es_title': 'Análisis de Imagen',
        'es_slug': 'analisis-de-imagen-clinica-y-preclinica',
        'en_title': 'Image Analytics',
        'en_slug': 'clinical-and-preclinical-image-analytics',
        'area_key': '',
        'hero_url': (
            'https://www.redib.net/upload/secciones-publicas/'
            'imagen-web_6c.jpg'
        ),
        'hero_slug': 'image-analytics-hero',
        'es_intro': (
            'Servicios de análisis de imagen clínica y preclínica: '
            'software avanzado, estaciones de procesamiento y soporte '
            'computacional de alto rendimiento.'
        ),
        'es_body': (
            '<p>Más allá de la adquisición, ReDIB ofrece servicios '
            'completos de análisis y postproceso de imagen, tanto '
            'preclínica como clínica. Las plataformas disponibles '
            'incluyen licencias PMOD, MATLAB, FSL, IDL, EchoPac, '
            'QMASS y QLab-Philips, junto a estaciones de trabajo de '
            'alto rendimiento, servidores HPC y GPUs Tesla K-40.</p>'
            '<p>El Laboratorio de Imágenes Computacionales Biomédicas '
            'del nodo Imaging La Fe coordina además el desarrollo de '
            'algoritmos cuantitativos y de inteligencia artificial '
            'para imagen médica.</p>'
            '<p>Estos servicios son transversales a todos los nodos y '
            'pueden solicitarse de forma independiente o como '
            'complemento de un proyecto de adquisición.</p>'
        ),
        'en_intro': (
            'Clinical and preclinical image-analysis services: '
            'advanced software, processing workstations and '
            'high-performance computing support.'
        ),
        'en_body': (
            '<p>Beyond acquisition, ReDIB offers full image '
            'analysis and post-processing services, both '
            'preclinical and clinical. Available platforms '
            'include PMOD, MATLAB, FSL, IDL, EchoPac, QMASS and '
            'QLab-Philips licences, alongside high-end '
            'workstations, HPC servers and Tesla K-40 GPUs.</p>'
            '<p>The Biomedical Computational Imaging Laboratory '
            'at the Imaging La Fe node also coordinates the '
            'development of quantitative and AI-based algorithms '
            'for medical imaging.</p>'
            '<p>These services are cross-cutting across all nodes '
            'and can be requested standalone or as a complement '
            'to an acquisition project.</p>'
        ),
    },
    {
        'es_title': 'Radioquímica',
        'es_slug': 'radioquimica',
        'en_title': 'Radiochemistry',
        'en_slug': 'radiochemistry',
        'area_key': 'radiochemistry',
        'hero_url': (
            'https://www.redib.net/upload/secciones-publicas/'
            'radioquimica01_cr_portada.jpg'
        ),
        'hero_slug': 'radiochemistry-hero',
        'es_intro': (
            'Laboratorio de radioquímica con ciclotrón IBA 9/18, '
            'producción de radiotrazadores PET e isótopos autorizados '
            'para investigación.'
        ),
        'es_body': (
            '<p>El nodo CIC biomaGUNE alberga la única instalación '
            'completa de radioquímica de la red ReDIB. Cuenta con un '
            'ciclotrón IBA 9/18, celdas calientes blindadas de plomo, '
            'módulos de síntesis automatizada, sistemas HPLC y TLC '
            'para control de calidad y un generador de Ga-68.</p>'
            '<p>La instalación está autorizada para la producción de '
            'un amplio panel de isótopos PET y SPECT y dispone de un '
            'catálogo de radiotrazadores listo para uso preclínico y '
            'clínico (FDG, FLT, FMISO, colina, compuestos dirigidos '
            'a receptores, entre otros).</p>'
        ),
        'en_intro': (
            'Radiochemistry lab with IBA 9/18 cyclotron, PET '
            'radiotracer production and authorised research '
            'isotopes.'
        ),
        'en_body': (
            '<p>The CIC biomaGUNE node hosts the only full '
            'radiochemistry facility in the ReDIB network. It '
            'features an IBA 9/18 cyclotron, lead-shielded hot '
            'cells, automated synthesis modules, HPLC and TLC '
            'systems for quality control and a Ga-68 generator.</p>'
            '<p>The facility is authorised to produce a broad '
            'panel of PET and SPECT isotopes and offers a '
            'radiotracer catalogue ready for preclinical and '
            'clinical use (FDG, FLT, FMISO, choline, '
            'receptor-targeted compounds and others).</p>'
        ),
    },
]


# ---------------------------------------------------------------------------
# Index-page intro/body refresh — replaces the Phase 3a stub copy with the
# proper section landing prose, in both locales.
# ---------------------------------------------------------------------------

NODE_INDEX_REFRESH = {
    'es': {
        'intro': (
            'Los cuatro nodos de ReDIB: BioImaC (Madrid), TRIMA @ CNIC '
            '(Madrid), Imaging La Fe (Valencia) y CIC biomaGUNE '
            '(San Sebastián). Cada nodo aporta una mezcla distinta de '
            'imagen clínica, preclínica y radioquímica.'
        ),
        'body': (
            '<p>ReDIB es una red distribuida: cada nodo es una '
            'instalación independiente con su propio personal, '
            'equipamiento y entorno institucional, pero opera dentro '
            'de un marco común de gestión y acceso. Los usuarios '
            'pueden solicitar acceso a cualquier combinación de nodos '
            'según las necesidades del proyecto.</p>'
            '<p>Selecciona un nodo para conocer su equipamiento, '
            'ubicación y datos de contacto.</p>'
        ),
    },
    'en': {
        'intro': (
            "ReDIB's four nodes: BioImaC (Madrid), TRIMA @ CNIC "
            "(Madrid), Imaging La Fe (Valencia) and CIC biomaGUNE "
            "(San Sebastián). Each node brings a distinct mix of "
            "clinical, preclinical and radiochemistry capabilities."
        ),
        'body': (
            '<p>ReDIB is a distributed network: each node is an '
            'independent facility with its own staff, instrumentation '
            'and institutional setting, but operates within a shared '
            'management and access framework. Users can request '
            'access to any combination of nodes that fits their '
            'project.</p>'
            '<p>Select a node to see its equipment, location and '
            'contact details.</p>'
        ),
    },
}


EQUIPMENT_INDEX_REFRESH = {
    'es': {
        'intro': (
            'Equipamiento de imagen biomédica disponible en los cuatro '
            'nodos de ReDIB, organizado en cuatro categorías: imagen '
            'clínica, imagen preclínica, análisis de imagen y '
            'radioquímica.'
        ),
        'body': (
            '<p>La red ReDIB ofrece una infraestructura instrumental '
            'amplia y complementaria. Las páginas de categoría que '
            'se enumeran a continuación describen los servicios y '
            'enumeran los equipos disponibles en tiempo real desde '
            'el portal de gestión.</p>'
            '<p>Para conocer los equipos por nodo, visita la '
            'sección <strong>Nodos</strong>.</p>'
        ),
    },
    'en': {
        'intro': (
            "Biomedical imaging equipment available across ReDIB's "
            "four nodes, organised in four categories: clinical "
            "imaging, preclinical imaging, image analytics and "
            "radiochemistry."
        ),
        'body': (
            '<p>The ReDIB network offers a broad and complementary '
            'instrument park. The category pages listed below '
            'describe the services and enumerate the equipment '
            'available live from the management portal.</p>'
            '<p>To browse equipment by node, visit the '
            '<strong>Nodes</strong> section.</p>'
        ),
    },
}


class Command(BaseCommand):
    help = (
        "Populate the Nodes (NodePage) and Equipment-category "
        "(EquipmentCategoryPage) content in both locales using the "
        "live-query pattern (Phase 3c). Idempotent."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        es = Locale.objects.get(language_code='es')
        en = Locale.objects.get(language_code='en')
        image_model = get_image_model()

        # Section parents must already exist (Phase 3a's populate_static_pages).
        node_index_es = NodeIndexPage.objects.filter(locale=es).first()
        node_index_en = NodeIndexPage.objects.filter(locale=en).first()
        eq_index_es = EquipmentIndexPage.objects.filter(locale=es).first()
        eq_index_en = EquipmentIndexPage.objects.filter(locale=en).first()
        if not all([node_index_es, node_index_en, eq_index_es, eq_index_en]):
            self.stderr.write(
                "NodeIndexPage and/or EquipmentIndexPage missing in one of "
                "the locales — run `populate_static_pages` first."
            )
            return

        download_dir = (
            Path(settings.MEDIA_ROOT) / 'marketing' / 'nodes'
        )
        download_dir.mkdir(parents=True, exist_ok=True)

        # 3.3 — refresh index-page chrome first so the section landings render
        # the right intro even if a node/category creation later fails.
        self._refresh_index_page(node_index_es, NODE_INDEX_REFRESH['es'])
        self._refresh_index_page(node_index_en, NODE_INDEX_REFRESH['en'])
        self._refresh_index_page(eq_index_es, EQUIPMENT_INDEX_REFRESH['es'])
        self._refresh_index_page(eq_index_en, EQUIPMENT_INDEX_REFRESH['en'])

        summary_rows = []  # (page_url, label, fk_status)

        # 3.1 — NodePages
        for spec in NODE_SPECS:
            core_node = self._resolve_core_node(spec)
            hero = get_or_create_image(
                image_model,
                download_dir,
                spec['hero_url'],
                title=f"Node hero: {spec['es_title']}",
                slug_hint=spec['hero_slug'],
                stderr_write=self.stderr.write,
            )
            es_page, en_page = self._upsert_node_pair(
                node_index_es, node_index_en, en, spec, hero, core_node
            )
            fk_status = (
                f"linked → core.Node id={core_node.id} ({core_node.code})"
                if core_node is not None
                else 'related_core_node = NULL (no matching core.Node)'
            )
            summary_rows.append(
                (es_page.url or f"/{es_page.slug}/",
                 f"NodePage ES — {spec['es_title']}", fk_status)
            )
            summary_rows.append(
                (en_page.url or f"/en/{en_page.slug}/",
                 f"NodePage EN — {spec['en_title']}", fk_status)
            )

        # 3.2 — EquipmentCategoryPages
        category_download_dir = (
            Path(settings.MEDIA_ROOT) / 'marketing' / 'equipment'
        )
        category_download_dir.mkdir(parents=True, exist_ok=True)

        for spec in CATEGORY_SPECS:
            hero = None
            if spec.get('hero_url'):
                hero = get_or_create_image(
                    image_model,
                    category_download_dir,
                    spec['hero_url'],
                    title=f"Equipment category hero: {spec['es_title']}",
                    slug_hint=spec['hero_slug'],
                    stderr_write=self.stderr.write,
                )
            es_page, en_page = self._upsert_category_pair(
                eq_index_es, eq_index_en, en, spec, hero
            )
            area_status = (
                f"area_key={spec['area_key']!r}"
                if spec['area_key']
                else 'area_key=\'\' (no live-equipment query)'
            )
            summary_rows.append(
                (es_page.url or f"/{es_page.slug}/",
                 f"EquipmentCategoryPage ES — {spec['es_title']}",
                 area_status)
            )
            summary_rows.append(
                (en_page.url or f"/en/{en_page.slug}/",
                 f"EquipmentCategoryPage EN — {spec['en_title']}",
                 area_status)
            )

        # 3.4 — print summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            'populate_equipment_nodes summary'
        ))
        self.stdout.write('-' * 72)
        for url, label, status in summary_rows:
            self.stdout.write(f"  {url:<48} {label}")
            self.stdout.write(f"      → {status}")
        self.stdout.write('-' * 72)
        self.stdout.write(self.style.SUCCESS(
            f"Created/refreshed {len(summary_rows)} pages."
        ))

    # ------------------------------------------------------------------
    # core.Node resolution
    # ------------------------------------------------------------------

    def _resolve_core_node(self, spec):
        """Try each code variant, then fall back to a case-insensitive
        name contains. Returns the matching Node or None."""
        for code in spec.get('core_node_codes', []):
            node = Node.objects.filter(code__iexact=code).first()
            if node is not None:
                return node
        name_needle = spec.get('core_node_name_contains')
        if name_needle:
            node = (
                Node.objects
                .filter(organization__name__icontains=name_needle)
                .first()
            )
            if node is not None:
                return node
            # The dev fixture sometimes appends " (sandbox)" to organization
            # names — try matching against Node.code or organization.short_name
            # as a last resort.
            node = (
                Node.objects
                .filter(organization__short_name__icontains=name_needle)
                .first()
            )
            if node is not None:
                return node
        return None

    # ------------------------------------------------------------------
    # NodePage upsert
    # ------------------------------------------------------------------

    def _upsert_node_pair(
        self, node_index_es, node_index_en, en_locale, spec, hero, core_node
    ):
        es_page = (
            NodePage.objects.child_of(node_index_es)
            .filter(slug=spec['es_slug']).first()
        )
        es_fields = {
            'intro': spec['es_intro'],
            'body': spec['es_body'],
            'location_text': spec['es_location'],
            'contact_info': spec['es_contact'],
            'hero_image': hero,
            'related_core_node': core_node,
        }
        if es_page is None:
            es_page = NodePage(
                title=spec['es_title'],
                slug=spec['es_slug'],
                locale=node_index_es.locale,
                show_in_menus=False,
                **es_fields,
            )
            node_index_es.add_child(instance=es_page)
            es_page.save_revision().publish()
            es_page.refresh_from_db()
            self.stdout.write(
                f"  Created ES NodePage: /{spec['es_slug']}/ "
                f"(id={es_page.id})"
            )
        else:
            changed = False
            if es_page.title != spec['es_title']:
                es_page.title = spec['es_title']
                changed = True
            for field, value in es_fields.items():
                # Don't clobber a cached hero with None if download failed
                # on a re-run.
                if field == 'hero_image' and value is None and es_page.hero_image_id:
                    continue
                if getattr(es_page, field) != value:
                    setattr(es_page, field, value)
                    changed = True
            if changed:
                es_page.save_revision().publish()
                es_page.refresh_from_db()
                self.stdout.write(
                    f"  Updated ES NodePage: /{spec['es_slug']}/ "
                    f"(id={es_page.id})"
                )
            else:
                self.stdout.write(
                    f"  ES NodePage already current: /{spec['es_slug']}/ "
                    f"(id={es_page.id})"
                )

        en_page = (
            NodePage.objects
            .filter(translation_key=es_page.translation_key,
                    locale=en_locale)
            .first()
        )
        en_fields = {
            'intro': spec['en_intro'],
            'body': spec['en_body'],
            'location_text': spec['en_location'],
            'contact_info': spec['en_contact'],
            'hero_image': hero,
            'related_core_node': core_node,
        }
        if en_page is None:
            en_page = es_page.copy_for_translation(en_locale)
            en_page.title = spec['en_title']
            en_page.slug = spec['en_slug']
            for field, value in en_fields.items():
                setattr(en_page, field, value)
            en_page.save_revision().publish()
            en_page.refresh_from_db()
            if en_page.get_parent().id != node_index_en.id:
                en_page.move(node_index_en, pos='last-child')
                en_page.refresh_from_db()
            self.stdout.write(
                f"  Created EN NodePage: /en/{spec['en_slug']}/ "
                f"(id={en_page.id})"
            )
        else:
            changed = False
            if en_page.title != spec['en_title']:
                en_page.title = spec['en_title']
                changed = True
            if en_page.slug != spec['en_slug']:
                en_page.slug = spec['en_slug']
                changed = True
            for field, value in en_fields.items():
                if field == 'hero_image' and value is None and en_page.hero_image_id:
                    continue
                if getattr(en_page, field) != value:
                    setattr(en_page, field, value)
                    changed = True
            if changed:
                en_page.save_revision().publish()
                en_page.refresh_from_db()
                self.stdout.write(
                    f"  Updated EN NodePage: /en/{spec['en_slug']}/ "
                    f"(id={en_page.id})"
                )
            else:
                self.stdout.write(
                    f"  EN NodePage already current: /en/{spec['en_slug']}/ "
                    f"(id={en_page.id})"
                )
            if en_page.get_parent().id != node_index_en.id:
                en_page.move(node_index_en, pos='last-child')
                en_page.refresh_from_db()

        return es_page, en_page

    # ------------------------------------------------------------------
    # EquipmentCategoryPage upsert
    # ------------------------------------------------------------------

    def _upsert_category_pair(
        self, eq_index_es, eq_index_en, en_locale, spec, hero
    ):
        es_page = (
            EquipmentCategoryPage.objects.child_of(eq_index_es)
            .filter(slug=spec['es_slug']).first()
        )
        es_fields = {
            'intro': spec['es_intro'],
            'body': spec['es_body'],
            'area_key': spec['area_key'],
            'hero_image': hero,
        }
        if es_page is None:
            es_page = EquipmentCategoryPage(
                title=spec['es_title'],
                slug=spec['es_slug'],
                locale=eq_index_es.locale,
                show_in_menus=False,
                **es_fields,
            )
            eq_index_es.add_child(instance=es_page)
            es_page.save_revision().publish()
            es_page.refresh_from_db()
            self.stdout.write(
                f"  Created ES EquipmentCategoryPage: /{spec['es_slug']}/ "
                f"(id={es_page.id})"
            )
        else:
            changed = False
            if es_page.title != spec['es_title']:
                es_page.title = spec['es_title']
                changed = True
            for field, value in es_fields.items():
                # Don't clobber a cached hero with None if download failed
                # on a re-run.
                if field == 'hero_image' and value is None and es_page.hero_image_id:
                    continue
                if getattr(es_page, field) != value:
                    setattr(es_page, field, value)
                    changed = True
            if changed:
                es_page.save_revision().publish()
                es_page.refresh_from_db()
                self.stdout.write(
                    f"  Updated ES EquipmentCategoryPage: /{spec['es_slug']}/ "
                    f"(id={es_page.id})"
                )
            else:
                self.stdout.write(
                    f"  ES EquipmentCategoryPage already current: "
                    f"/{spec['es_slug']}/ (id={es_page.id})"
                )

        en_page = (
            EquipmentCategoryPage.objects
            .filter(translation_key=es_page.translation_key,
                    locale=en_locale)
            .first()
        )
        en_fields = {
            'intro': spec['en_intro'],
            'body': spec['en_body'],
            'area_key': spec['area_key'],
            'hero_image': hero,
        }
        if en_page is None:
            en_page = es_page.copy_for_translation(en_locale)
            en_page.title = spec['en_title']
            en_page.slug = spec['en_slug']
            for field, value in en_fields.items():
                setattr(en_page, field, value)
            en_page.save_revision().publish()
            en_page.refresh_from_db()
            if en_page.get_parent().id != eq_index_en.id:
                en_page.move(eq_index_en, pos='last-child')
                en_page.refresh_from_db()
            self.stdout.write(
                f"  Created EN EquipmentCategoryPage: /en/{spec['en_slug']}/ "
                f"(id={en_page.id})"
            )
        else:
            changed = False
            if en_page.title != spec['en_title']:
                en_page.title = spec['en_title']
                changed = True
            if en_page.slug != spec['en_slug']:
                en_page.slug = spec['en_slug']
                changed = True
            for field, value in en_fields.items():
                if field == 'hero_image' and value is None and en_page.hero_image_id:
                    continue
                if getattr(en_page, field) != value:
                    setattr(en_page, field, value)
                    changed = True
            if changed:
                en_page.save_revision().publish()
                en_page.refresh_from_db()
                self.stdout.write(
                    f"  Updated EN EquipmentCategoryPage: "
                    f"/en/{spec['en_slug']}/ (id={en_page.id})"
                )
            else:
                self.stdout.write(
                    f"  EN EquipmentCategoryPage already current: "
                    f"/en/{spec['en_slug']}/ (id={en_page.id})"
                )
            if en_page.get_parent().id != eq_index_en.id:
                en_page.move(eq_index_en, pos='last-child')
                en_page.refresh_from_db()

        return es_page, en_page

    # ------------------------------------------------------------------
    # Index-page chrome refresh
    # ------------------------------------------------------------------

    def _refresh_index_page(self, page, fields):
        """Push intro/body onto an existing Index page. No-op if unchanged.

        NodeIndexPage doesn't currently have a `body` field — guard for it.
        """
        changed = False
        for field, value in fields.items():
            if not hasattr(page, field):
                continue
            if getattr(page, field) != value:
                setattr(page, field, value)
                changed = True
        if changed:
            page.save_revision().publish()
            page.refresh_from_db()
            self.stdout.write(
                f"  Refreshed {type(page).__name__} ({page.locale.language_code}) "
                f"id={page.id}"
            )
        else:
            self.stdout.write(
                f"  {type(page).__name__} ({page.locale.language_code}) "
                f"id={page.id} already current"
            )
