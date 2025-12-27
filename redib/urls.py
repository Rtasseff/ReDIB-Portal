"""
URL configuration for redib project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),

    # Core app (dashboard, home)
    path('', include('core.urls')),

    # Calls app
    path('calls/', include('calls.urls')),

    # Applications app (stub URLs for Phase 1 testing)
    path('applications/', include('applications.urls')),

    # Evaluations app (stub URLs for Phase 1 testing)
    path('evaluations/', include('evaluations.urls')),

    # Access app (stub URLs for Phase 1 testing)
    path('access/', include('access.urls')),

    # Reports app (stub URLs for Phase 1 testing)
    path('reports/', include('reports.urls')),
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

# Customize admin site
admin.site.site_header = 'ReDIB COA Administration'
admin.site.site_title = 'ReDIB COA Admin'
admin.site.index_title = 'Welcome to ReDIB COA Portal Administration'
