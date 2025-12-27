"""
URL configuration for reports app.
Stub URLs for Phase 1 testing - full implementation in Phase 10.
"""
from django.urls import path
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

app_name = 'reports'


@login_required
def stub_view(request):
    from django.contrib import messages
    messages.info(request, "Statistics and reports coming in Phase 10!")
    return render(request, 'applications/coming_soon.html', {
        'feature': 'Statistics & Reports',
        'phase': 'Phase 10'
    })


urlpatterns = [
    path('', stub_view, name='statistics'),
]
