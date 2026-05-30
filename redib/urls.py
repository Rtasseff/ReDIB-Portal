"""
URL configuration for redib project.

Layout on `feature/marketing-site`:
- `/`              -> Wagtail (marketing site, catchall LAST)
- `/portal/`       -> existing COA portal apps (core, calls, applications, ...)
- `/admin/`        -> Django admin
- `/cms/`          -> Wagtail admin
- `/documents/`    -> Wagtail documents
- `/accounts/`     -> django-allauth
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from allauth.account.views import PasswordChangeView

from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),

    # Wagtail admin + documents (marketing site CMS)
    path('cms/', include(wagtailadmin_urls)),
    path('documents/', include(wagtaildocs_urls)),

    # Override password change to redirect to login after success
    path('accounts/password/change/', PasswordChangeView.as_view(
        success_url='/accounts/login/'
    ), name='account_change_password'),
    path('accounts/', include('allauth.urls')),

    # Existing COA portal — everything moves under /portal/
    path('portal/', include('core.urls')),
    path('portal/calls/', include('calls.urls')),
    path('portal/applications/', include('applications.urls')),
    path('portal/evaluations/', include('evaluations.urls')),
    path('portal/access/', include('access.urls')),
    path('portal/reports/', include('reports.urls')),
    path('portal/newsletters/', include('newsletters.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns

# Wagtail catchall — MUST be last so it doesn't shadow any of the above.
# Wrapped in i18n_patterns so EN pages get a `/en/` prefix (Spanish, the
# default locale, stays unprefixed). This is the standard wagtail-localize
# routing pattern; a more faithful "per-page slug aliases at root" routing
# would require custom URL resolution and is deferred.
urlpatterns += i18n_patterns(
    re_path(r'', include(wagtail_urls)),
    prefix_default_language=False,
)

# Customize admin site
admin.site.site_header = 'ReDIB COA Administration'
admin.site.site_title = 'ReDIB COA Admin'
admin.site.index_title = 'Welcome to ReDIB COA Portal Administration'
