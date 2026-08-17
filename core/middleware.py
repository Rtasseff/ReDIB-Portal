"""
Middleware for the core app.
"""
from django.shortcuts import redirect
from django.urls import Resolver404, resolve, reverse


class ProfileCompletionMiddleware:
    """
    Redirect authenticated users to the profile page if their profile is incomplete.
    Exempts: login/signup/logout pages, profile page, admin, static/media files.
    """

    EXEMPT_PREFIXES = [
        '/accounts/',
        '/admin/',
        '/static/',
        '/media/',
    ]

    # Public pages that logged-in users must be able to reach even with an
    # incomplete profile — a consult request is informal contact, not an
    # application, so it must not be gated behind profile completion.
    EXEMPT_URL_NAMES = [
        'calls:public_consult',
        'calls:public_consult_thanks',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def _is_exempt_view(self, path):
        """Exempt by URL name so the check survives URL prefix changes."""
        try:
            return resolve(path).view_name in self.EXEMPT_URL_NAMES
        except Resolver404:
            return False

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and not request.user.is_superuser
            and not request.user.is_staff
            and hasattr(request.user, 'is_profile_complete')
            and not request.user.is_profile_complete
        ):
            profile_url = reverse('core:profile')
            path = request.path

            # Allow access to exempt paths and the profile page itself.
            # The profile page itself shows a `profile_incomplete` alert, so no
            # message is needed here (avoids duplicate-message accumulation).
            if (
                path != profile_url
                and not any(path.startswith(p) for p in self.EXEMPT_PREFIXES)
                and not self._is_exempt_view(path)
            ):
                return redirect(profile_url)

        return self.get_response(request)
