"""
Signal receivers for the core app.
"""
from allauth.account.signals import email_confirmed
from django.dispatch import receiver

from .models import UserRole


@receiver(email_confirmed)
def assign_applicant_role_on_email_confirmed(sender, request, email_address, **kwargs):
    """Grant the applicant role once a self-registered user confirms their email.

    Not at signup: bots fill in the signup form with strangers' addresses and
    never confirm them, so granting at signup handed the role to every fake
    account (backlog #92). ACCOUNT_EMAIL_VERIFICATION is 'mandatory', so
    nobody can log in before confirming and a real applicant sees no
    difference.

    email_confirmed fires on every confirmation, including an address added
    later at /accounts/email/. So an account that already holds another role
    (coordinator, node_coordinator, evaluator: provisioned by the
    populate_redib_* / setup_* commands or by hand) is left alone. The
    submit-time get_or_create in applications.views.application_submit is
    kept as a safety net for anyone without the role.
    """
    user = email_address.user
    if user.roles.exclude(role='applicant').exists():
        return
    UserRole.objects.get_or_create(
        user=user,
        role='applicant',
        defaults={'is_active': True},
    )
