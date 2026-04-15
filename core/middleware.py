"""
Middleware for the core app.
"""
from django.shortcuts import redirect
from django.urls import reverse


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

    def __init__(self, get_response):
        self.get_response = get_response

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
            if path != profile_url and not any(path.startswith(p) for p in self.EXEMPT_PREFIXES):
                return redirect(profile_url)

        return self.get_response(request)
