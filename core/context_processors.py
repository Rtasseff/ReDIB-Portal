"""
Context processors for adding custom context to all templates.
"""
from django.conf import settings


def contact_email(request):
    """Expose settings.CONTACT_EMAIL to every template as `contact_email`,
    so help links in the navbar/footer share the email-template source of
    truth (overridable via the CONTACT_EMAIL env var)."""
    return {'contact_email': settings.CONTACT_EMAIL}


def user_roles(request):
    """
    Add user roles to template context.

    Makes user roles available in all templates as:
    - user_roles: List of role names
    - is_applicant, is_node_coordinator, is_evaluator, is_coordinator, is_admin: Boolean flags

    Args:
        request: The HTTP request object

    Returns:
        dict: Context dictionary with role information
    """
    if request.user.is_authenticated:
        # Get active roles for the user
        roles = list(request.user.roles.filter(is_active=True).values_list('role', flat=True))

        return {
            'user_roles': roles,
            'is_applicant': 'applicant' in roles,
            'is_node_coordinator': 'node_coordinator' in roles,
            'is_evaluator': 'evaluator' in roles,
            'is_coordinator': 'coordinator' in roles,
            'is_admin': 'admin' in roles or request.user.is_superuser,
        }

    # User not authenticated
    return {
        'user_roles': [],
        'is_applicant': False,
        'is_node_coordinator': False,
        'is_evaluator': False,
        'is_coordinator': False,
        'is_admin': False,
    }
