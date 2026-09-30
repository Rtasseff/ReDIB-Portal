"""
Signal receivers for the core app.
"""
from allauth.account.signals import user_signed_up
from django.dispatch import receiver

from .models import UserRole


@receiver(user_signed_up)
def assign_applicant_role_on_signup(sender, request, user, **kwargs):
    """Grant the applicant role to users who self-register via the portal.

    Other roles (coordinator, node_coordinator, evaluator) are provisioned
    by admins or the populate_redib_* / setup_* management commands, which
    bypass the allauth signup flow, so this signal does not affect them.
    The submit-time get_or_create in applications.views.application_submit
    is kept as a safety net for pre-existing users without the role.
    """
    UserRole.objects.get_or_create(
        user=user,
        role='applicant',
        defaults={'is_active': True},
    )
