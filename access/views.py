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


@login_required
def mark_application_complete(request, application_id):
    """
    Mark an application as complete and record actual hours used.

    Accessible by:
    - Applicant (owns the application)
    - Node coordinator (equipment belongs to their node)
    """
    from django.utils import timezone
    from django.http import JsonResponse
    from core.models import UserRole

    application = get_object_or_404(
        Application.objects.prefetch_related('requested_access__equipment__node'),
        pk=application_id
    )

    # Check permissions
    is_applicant = (request.user == application.applicant)

    # Check if node coordinator for any of the equipment
    is_node_coordinator = False
    if not is_applicant:
        my_nodes = UserRole.objects.filter(
            user=request.user,
            role='node_coordinator',
            is_active=True
        ).values_list('node_id', flat=True)

        equipment_nodes = application.requested_access.values_list(
            'equipment__node_id', flat=True
        )

        is_node_coordinator = any(node_id in my_nodes for node_id in equipment_nodes)

    if not (is_applicant or is_node_coordinator):
        messages.error(request, 'You do not have permission to mark this application as complete.')
        return redirect('applications:detail', pk=application.pk)

    # Check if already completed
    if application.is_completed:
        messages.warning(request, 'This application is already marked as complete.')
        return redirect('applications:detail', pk=application.pk)

    if request.method == 'POST':
        # Collect actual hours used for each equipment
        all_hours_recorded = True
        for req_access in application.requested_access.all():
            hours_key = f'actual_hours_{req_access.id}'
            actual_hours = request.POST.get(hours_key)

            if actual_hours:
                try:
                    req_access.actual_hours_used = float(actual_hours)
                    req_access.save()
                except (ValueError, TypeError):
                    messages.error(request, f'Invalid hours value for {req_access.equipment.name}')
                    all_hours_recorded = False
            else:
                all_hours_recorded = False

        if all_hours_recorded:
            # Mark application as complete
            application.is_completed = True
            application.completed_at = timezone.now()
            application.save()

            messages.success(
                request,
                f'Application {application.code} marked as complete. Thank you for reporting actual hours used!'
            )
            return redirect('applications:detail', pk=application.pk)
        else:
            messages.error(request, 'Please enter actual hours used for all equipment.')

    # GET: Show completion form
    requested_access = application.requested_access.select_related(
        'equipment__node'
    ).order_by('equipment__node__code')

    context = {
        'application': application,
        'requested_access': requested_access,
        'is_applicant': is_applicant,
        'is_node_coordinator': is_node_coordinator,
    }
    return render(request, 'access/mark_complete.html', context)


@login_required
def applicant_handoff_dashboard(request):
    """
    Applicant view of their accepted applications for handoff/scheduling.

    Shows applications where:
    - User is the applicant
    - Status = 'accepted' and accepted_by_applicant = True
    """
    applications = Application.objects.filter(
        applicant=request.user,
        status='accepted',
        accepted_by_applicant=True
    ).select_related('call').prefetch_related(
        'requested_access__equipment__node'
    ).order_by('-handoff_email_sent_at')

    # Also show completed applications
    completed_applications = Application.objects.filter(
        applicant=request.user,
        is_completed=True
    ).select_related('call').prefetch_related(
        'requested_access__equipment__node'
    ).order_by('-completed_at')[:10]  # Show 10 most recent

    context = {
        'applications': applications,
        'completed_applications': completed_applications,
    }
    return render(request, 'access/applicant_handoff.html', context)
