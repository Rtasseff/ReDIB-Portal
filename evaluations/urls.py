"""
URL configuration for evaluations app.
Stub URLs for Phase 1 testing - full implementation in Phase 5.
"""
from django.urls import path
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

app_name = 'evaluations'


@login_required
def stub_view(request):
    from django.contrib import messages
    messages.info(request, "Evaluations coming in Phase 5!")
    return render(request, 'applications/coming_soon.html', {
        'feature': 'Evaluation System',
        'phase': 'Phase 5'
    })


urlpatterns = [
    path('', stub_view, name='my_evaluations'),
    path('<int:pk>/', stub_view, name='evaluate'),
    path('assign/', stub_view, name='assignment_dashboard'),
]
