"""Shared test helpers for the ReDIB portal test suite.

core.middleware.ProfileCompletionMiddleware redirects any authenticated,
non-staff user with an incomplete profile (missing name/phone/organization/
position — see User.is_profile_complete) to /profile/ before the requested
view runs. Tests that drive real views through the Django test client need a
user that clears that check, or they silently exercise the redirect instead
of the view under test.
"""
from core.models import Organization


def create_complete_user(email, password='testpass123', organization=None, **extra_fields):
    """Create a User with every ProfileCompletionMiddleware-required field set."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    if organization is None:
        organization, _ = Organization.objects.get_or_create(
            name='Test Organization',
            defaults={'organization_type': 'other', 'iso2': 'ES', 'country': 'Spain'},
        )

    extra_fields.setdefault('username', email)
    extra_fields.setdefault('first_name', 'Test')
    extra_fields.setdefault('last_name', 'User')
    extra_fields.setdefault('phone', '+34 900 000 000')
    extra_fields.setdefault('position', 'Researcher')
    extra_fields.setdefault('organization', organization)

    return User.objects.create_user(email=email, password=password, **extra_fields)
