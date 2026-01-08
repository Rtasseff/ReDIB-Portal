"""
Views for the access app - Publication submission and access tracking.
"""

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from applications.models import Application
from core.decorators import node_coordinator_required
from .models import Publication
from .forms import PublicationForm


@login_required
def publication_list(request):
    """List user's submitted publications."""
    publications = Publication.objects.filter(
        application__applicant=request.user
    ).select_related('application').order_by('-reported_at')

    context = {
        'publications': publications,
    }
    return render(request, 'access/publication_list.html', context)


@login_required
def publication_submit(request):
    """Submit a new publication."""
    if request.method == 'POST':
        form = PublicationForm(request.POST, user=request.user)
        if form.is_valid():
            publication = form.save(commit=False)
            publication.reported_by = request.user
            publication.save()

            messages.success(request, f'Publication "{publication.title}" submitted successfully!')
            return redirect('access:publication_list')
    else:
        form = PublicationForm(user=request.user)

    context = {
        'form': form,
    }
    return render(request, 'access/publication_submit.html', context)


# =============================================================================
# Phase 8: Access Scheduling & Tracking (Node Coordinator views)
# =============================================================================

@node_coordinator_required
def node_scheduling(request):
    """
    Node coordinator view of accepted applications needing scheduling.

    Shows applications where:
    - status = 'accepted'
    - accepted_by_applicant = True
    - Equipment requested is from coordinator's node(s)
    """
    from core.models import UserRole

    # Get nodes this user coordinates
    my_nodes = UserRole.objects.filter(
        user=request.user,
        role='node_coordinator',
        is_active=True
    ).values_list('node_id', flat=True)

    # Get applications with accepted access for these nodes
    applications = Application.objects.filter(
        status='accepted',
        accepted_by_applicant=True,
        requested_access__equipment__node__in=my_nodes
    ).select_related(
        'applicant', 'call'
    ).prefetch_related(
        'requested_access__equipment__node'
    ).distinct().order_by('-handoff_email_sent_at')

    context = {
        'applications': applications,
    }
    return render(request, 'access/node_scheduling.html', context)


@node_coordinator_required
def access_tracking(request):
    """
    Node coordinator view for tracking access completion status.

    Shows all applications involving coordinator's nodes, regardless of status.
    """
    from core.models import UserRole

    # Get nodes this user coordinates
    my_nodes = UserRole.objects.filter(
        user=request.user,
        role='node_coordinator',
        is_active=True
    ).values_list('node_id', flat=True)

    # Get all applications with equipment from these nodes
    applications = Application.objects.filter(
        requested_access__equipment__node__in=my_nodes
    ).exclude(
        status='draft'
    ).select_related(
        'applicant', 'call'
    ).prefetch_related(
        'requested_access__equipment__node'
    ).distinct().order_by('-submitted_at')

    context = {
        'applications': applications,
    }
    return render(request, 'access/access_tracking.html', context)
