"""
URL configuration for access app.
Stub URLs for Phase 1 testing - full implementation in Phases 7-9.
"""
from django.urls import path
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

app_name = 'access'


@login_required
def stub_view(request):
    from django.contrib import messages
    messages.info(request, "Access management coming in Phases 7-9!")
    return render(request, 'applications/coming_soon.html', {
        'feature': 'Access Management & Scheduling',
        'phase': 'Phases 7-9'
    })


urlpatterns = [
    path('scheduling/', stub_view, name='node_scheduling'),
    path('tracking/', stub_view, name='access_tracking'),
]
