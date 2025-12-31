"""
Views for evaluations app - Phase 4: Evaluator Assignment
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q, Avg
from django.utils import timezone

from core.decorators import role_required
from core.models import UserRole, User
from calls.models import Call
from applications.models import Application
from .models import Evaluation
from .tasks import assign_evaluators_to_application, assign_evaluators_to_call


@login_required
@role_required('evaluator')
def evaluator_dashboard(request):
    """
    Dashboard for evaluators to see their assigned applications.
    Phase 4: View assignments
    Phase 5: Submit evaluations
    """
    # Get all evaluations assigned to this user
    evaluations = Evaluation.objects.filter(
        evaluator=request.user
    ).select_related(
        'application',
        'application__call',
        'application__applicant'
    ).order_by('-assigned_at')

    # Separate pending and completed
    pending = evaluations.filter(completed_at__isnull=True)
    completed = evaluations.filter(completed_at__isnull=False)

    # Get upcoming deadlines
    upcoming = pending.filter(
        application__call__evaluation_deadline__gte=timezone.now()
    ).order_by('application__call__evaluation_deadline')

    # Get overdue evaluations
    overdue = pending.filter(
        application__call__evaluation_deadline__lt=timezone.now()
    )

    context = {
        'pending_count': pending.count(),
        'completed_count': completed.count(),
        'overdue_count': overdue.count(),
        'upcoming': upcoming,
        'overdue': overdue,
        'completed': completed[:10],  # Show 10 most recent
    }

    return render(request, 'evaluations/evaluator_dashboard.html', context)


@login_required
@role_required('evaluator')
def evaluation_detail(request, pk):
    """
    View and submit evaluation for a specific application.
    Phase 4: View application details (read-only)
    Phase 5: Submit evaluation scores and comments
    """
    evaluation = get_object_or_404(
        Evaluation.objects.select_related(
            'application',
            'application__call',
            'application__applicant',
            'application__applicant__organization'
        ),
        pk=pk,
        evaluator=request.user
    )

    context = {
        'evaluation': evaluation,
        'application': evaluation.application,
        'is_complete': evaluation.is_complete,
        'is_past_deadline': evaluation.application.call.evaluation_deadline < timezone.now(),
    }

    return render(request, 'evaluations/evaluation_detail.html', context)


@login_required
@role_required(['coordinator', 'admin'])
def assignment_dashboard(request):
    """
    Coordinator dashboard for managing evaluator assignments.
    Shows all calls and their assignment status.
    """
    # Get all calls with assignment statistics
    calls = Call.objects.annotate(
        app_count=Count('applications'),
        pending_eval_count=Count('applications', filter=Q(applications__status='pending_evaluation')),
        under_eval_count=Count('applications', filter=Q(applications__status='under_evaluation')),
    ).order_by('-submission_end')

    # Get recent calls that need attention
    recent_calls = calls.filter(
        status__in=['open', 'closed']
    )[:5]

    context = {
        'recent_calls': recent_calls,
        'all_calls': calls,
    }

    return render(request, 'evaluations/assignment_dashboard.html', context)


@login_required
@role_required(['coordinator', 'admin'])
def call_assignment_detail(request, call_id):
    """
    Detailed view of evaluator assignments for a specific call.
    Allows manual assignment of evaluators.
    """
    call = get_object_or_404(Call, pk=call_id)

    # Get all applications for this call
    applications = Application.objects.filter(
        call=call
    ).prefetch_related(
        'evaluations',
        'evaluations__evaluator'
    ).select_related(
        'applicant',
        'applicant__organization'
    ).order_by('code')

    # Get evaluator statistics
    for app in applications:
        app.evaluator_count = app.evaluations.count()
        app.completed_evaluations = app.evaluations.filter(completed_at__isnull=False).count()

    # Get all active evaluators for manual assignment
    active_evaluators = User.objects.filter(
        roles__role='evaluator',
        roles__is_active=True
    ).select_related('organization').distinct()

    context = {
        'call': call,
        'applications': applications,
        'active_evaluators': active_evaluators,
        'can_auto_assign': applications.filter(status='pending_evaluation').exists(),
    }

    return render(request, 'evaluations/call_assignment_detail.html', context)


@login_required
@role_required(['coordinator', 'admin'])
def auto_assign_call(request, call_id):
    """
    Automatically assign evaluators to all pending applications in a call.
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('evaluations:call_assignment_detail', call_id=call_id)

    call = get_object_or_404(Call, pk=call_id)

    # Get number of evaluators from form (default: 2)
    num_evaluators = int(request.POST.get('num_evaluators', 2))

    # Trigger the Celery task
    result = assign_evaluators_to_call(call_id, num_evaluators)

    # Show results
    if result['errors']:
        messages.warning(
            request,
            f"Assignment completed with errors. "
            f"{len(result['assignments'])} applications processed, {len(result['errors'])} errors."
        )
    else:
        messages.success(
            request,
            f"Successfully assigned evaluators to {result['total_applications']} applications."
        )

    return redirect('evaluations:call_assignment_detail', call_id=call_id)


@login_required
@role_required(['coordinator', 'admin'])
def manual_assign_evaluator(request, application_id):
    """
    Manually assign a specific evaluator to an application.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    application = get_object_or_404(Application, pk=application_id)
    evaluator_id = request.POST.get('evaluator_id')

    if not evaluator_id:
        return JsonResponse({'error': 'Evaluator ID required'}, status=400)

    evaluator = get_object_or_404(User, pk=evaluator_id)

    # Check if evaluator is already assigned
    if Evaluation.objects.filter(application=application, evaluator=evaluator).exists():
        return JsonResponse({'error': 'Evaluator already assigned'}, status=400)

    # Check conflict of interest
    if application.applicant.organization and evaluator.organization:
        if application.applicant.organization == evaluator.organization:
            return JsonResponse({
                'error': f'Conflict of interest: Evaluator from same organization ({evaluator.organization.name})'
            }, status=400)

    # Create evaluation
    evaluation = Evaluation.objects.create(
        application=application,
        evaluator=evaluator
    )

    # Send notification email
    from communications.tasks import send_email_from_template
    context = {
        'evaluator_name': evaluator.get_full_name(),
        'application_code': application.code,
        'call_code': application.call.code,
        'deadline': application.call.evaluation_deadline,
        'evaluation_url': f'/evaluations/{evaluation.id}/',
    }

    send_email_from_template(
        template_type='evaluation_assigned',
        recipient_email=evaluator.email,
        context_data=context,
        recipient_user_id=evaluator.id,
        related_application_id=application.id,
        related_evaluation_id=evaluation.id
    )

    messages.success(request, f'Assigned {evaluator.get_full_name()} to {application.code}')

    return JsonResponse({
        'success': True,
        'evaluation_id': evaluation.id,
        'evaluator_name': evaluator.get_full_name()
    })


@login_required
@role_required(['coordinator', 'admin'])
def remove_evaluator_assignment(request, evaluation_id):
    """
    Remove an evaluator assignment (only if not yet completed).
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    evaluation = get_object_or_404(Evaluation, pk=evaluation_id)

    if evaluation.completed_at:
        return JsonResponse({'error': 'Cannot remove completed evaluation'}, status=400)

    application_code = evaluation.application.code
    evaluator_name = evaluation.evaluator.get_full_name()

    evaluation.delete()

    messages.success(request, f'Removed {evaluator_name} from {application_code}')

    return JsonResponse({'success': True})
