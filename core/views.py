"""
Core application views.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone


@login_required
def dashboard(request):
    """
    Role-based dashboard showing relevant information for each user type.

    Shows different content based on user roles:
    - Applicants: Recent applications, draft count
    - Node Coordinators: Pending feasibility reviews
    - Evaluators: Pending evaluations
    - Coordinators: Active calls, recent applications, pending resolutions
    """
    user = request.user
    context = {
        'user': user,
    }

    # Get user roles
    user_roles = list(user.roles.filter(is_active=True).values_list('role', flat=True))

    # Applicant dashboard
    if 'applicant' in user_roles:
        from applications.models import Application
        context['my_applications'] = Application.objects.filter(
            applicant=user
        ).select_related('call').order_by('-created_at')[:5]
        context['draft_count'] = Application.objects.filter(
            applicant=user, status='draft'
        ).count()

    # Node Coordinator dashboard
    if 'node_coordinator' in user_roles:
        from applications.models import FeasibilityReview
        from core.models import UserRole

        # Get nodes this user coordinates
        my_nodes = UserRole.objects.filter(
            user=user, role='node_coordinator', is_active=True
        ).values_list('node_id', flat=True)

        context['pending_feasibility'] = FeasibilityReview.objects.filter(
            node_id__in=my_nodes,
            is_feasible__isnull=True
        ).select_related('application', 'node').order_by('created_at')[:10]

        context['feasibility_count'] = FeasibilityReview.objects.filter(
            node_id__in=my_nodes,
            is_feasible__isnull=True
        ).count()

    # Evaluator dashboard
    if 'evaluator' in user_roles:
        from evaluations.models import Evaluation
        context['my_evaluations'] = Evaluation.objects.filter(
            evaluator=user,
            completed_at__isnull=True
        ).select_related('application__call').order_by('assigned_at')[:10]

        context['pending_evaluations_count'] = Evaluation.objects.filter(
            evaluator=user,
            completed_at__isnull=True
        ).count()

    # Coordinator dashboard
    if 'coordinator' in user_roles or user.is_superuser:
        from calls.models import Call
        from applications.models import Application

        context['active_calls'] = Call.objects.filter(
            status__in=['open', 'closed']
        ).order_by('-submission_start')[:5]

        context['recent_applications'] = Application.objects.exclude(
            status='draft'
        ).select_related('call', 'applicant').order_by('-submitted_at')[:10]

        context['pending_resolution'] = Application.objects.filter(
            status='evaluated',
            resolution=''
        ).count()

    return render(request, 'core/dashboard.html', context)
