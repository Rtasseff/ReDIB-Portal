"""
Per-call bilingual resolution table (backlog #20).

Computes the published results table ReDIB hands out once a call is
resolved: one row per non-draft application, the applicant's organization,
the node(s) it was submitted to, and the node coordinator's resolution — in
English and Spanish. No HTML, no HttpResponse; that's `reports/views.py`.

The resolution comes from `NodeResolution.resolution`, never
`Application.status` or `Application.resolution` — see
docs/handoffs/resolution-report.md decision 1.
"""

from applications.models import Application

MISSING = '—'  # em dash — missing data is shown as missing, never inferred

RESOLUTION_LABELS = {
    'en': {'accept': 'Accepted', 'waitlist': 'Wait List', 'reject': 'Rejected'},
    'es': {'accept': 'Aceptada', 'waitlist': 'En espera', 'reject': 'Rechazada'},
}

COLUMN_HEADERS = {
    'en': ['Application', 'Organization', 'Node', 'Resolution'],
    'es': ['Solicitud', 'Organización', 'Nodo', 'Resolución'],
}

# Published node display names. Not derivable from any existing field:
# Node.name is a read-only property returning organization.name, and the
# host organizations' short_names only happen to match one node out of
# four. See docs/handoffs/resolution-report.md decision 4 for why this is
# a dict here and not a model field.
NODE_PUBLIC_NAMES = {
    'BioImaC': 'BioImaC',
    'CIC-biomaGUNE': 'biomaGUNE',
    'TRIMA@CNIC': 'TRIMA',
    'IIS-LaFe': 'IIS La Fe',
}


def _node_public_name(node):
    """Look up defensively — an unknown node code must degrade, never raise."""
    return (
        NODE_PUBLIC_NAMES.get(node.code)
        or node.organization.short_name
        or node.organization.name
    )


def _organization_cell(application):
    org = application.applicant.organization
    if org is not None:
        if org.short_name and org.short_name != org.name:
            return f'{org.short_name} · {org.name}'
        return org.name
    return application.applicant_entity or ''


def _resolution_label(resolution, lang):
    if not resolution:
        return MISSING
    return RESOLUTION_LABELS[lang].get(resolution, MISSING)


def _application_has_no_organization(application):
    return application.applicant.organization_id is None


def build_resolution_table(call, lang):
    """Return {'headers': [...], 'rows': [...], 'warnings': {...}} for `call`.

    Rows are every non-draft application, ordered by code (decision 2).
    `warnings` is language-independent (same content whichever `lang` is
    passed) — the view calls this once per language and either result's
    warnings dict is equally valid for the page chrome.
    """
    applications = (
        Application.objects
        .filter(call=call)
        .exclude(status='draft')
        .select_related('applicant__organization')
        .prefetch_related('node_resolutions__node__organization')
        .order_by('code')
    )

    rows = []
    missing_resolution_codes = []
    missing_organization_codes = []

    for app in applications:
        node_resolutions = list(app.node_resolutions.all())

        if node_resolutions:
            node_lines = [_node_public_name(nr.node) for nr in node_resolutions]
            resolution_lines = [_resolution_label(nr.resolution, lang) for nr in node_resolutions]
            if any(not nr.resolution for nr in node_resolutions):
                missing_resolution_codes.append(app.code)
        else:
            node_lines = [MISSING]
            resolution_lines = [MISSING]
            missing_resolution_codes.append(app.code)

        if _application_has_no_organization(app):
            missing_organization_codes.append(app.code)

        rows.append({
            'code': app.code or 'DRAFT',
            'organization': _organization_cell(app),
            'nodes': node_lines,
            'resolutions': resolution_lines,
        })

    warnings = {
        'resolutions_released': call.resolutions_released,
        'missing_resolution_codes': missing_resolution_codes,
        'missing_organization_codes': missing_organization_codes,
    }

    return {
        'headers': COLUMN_HEADERS[lang],
        'rows': rows,
        'warnings': warnings,
    }
