"""
Views for the applications app - 5-step application wizard.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from calls.models import Call
from core.decorators import node_coordinator_required, role_required
from .models import Application, RequestedAccess, FeasibilityReview
from .forms import (
    ApplicationStep1Form, ApplicationStep2Form, ApplicationStep3Form,
    ApplicationStep4Form, ApplicationStep5Form, RequestedAccessFormSet,
    FeasibilityReviewForm
)


@login_required
def my_applications(request):
    """Applicant's dashboard - list of their applications"""
    applications = Application.objects.filter(
        applicant=request.user
    ).select_related('call').order_by('-created_at')

    context = {
        'applications': applications,
    }
    return render(request, 'applications/my_applications.html', context)


@login_required
def application_detail(request, pk):
    """View application details (applicant view)"""
    application = get_object_or_404(
        Application,
        pk=pk,
        applicant=request.user
    )

    requested_access = application.requested_access.select_related(
        'equipment__node'
    ).order_by('equipment__node__code')

    context = {
        'application': application,
        'requested_access': requested_access,
    }
    return render(request, 'applications/detail.html', context)


@login_required
@transaction.atomic
def application_create(request, call_pk):
    """Create new application - Step 1"""
    call = get_object_or_404(Call, pk=call_pk)

    # Check if call is open
    if not call.is_open:
        messages.error(request, "This call is not currently accepting applications.")
        return redirect('calls:public_detail', pk=call_pk)

    # Check for existing draft
    existing_draft = Application.objects.filter(
        call=call,
        applicant=request.user,
        status='draft'
    ).first()

    if existing_draft:
        messages.info(request, "Continuing your existing draft application.")
        return redirect('applications:edit_step2', pk=existing_draft.pk)

    if request.method == 'POST':
        form = ApplicationStep1Form(request.POST, user=request.user)

        if form.is_valid():
            application = form.save(commit=False)
            application.call = call
            application.applicant = request.user
            application.status = 'draft'

            # Auto-populate applicant fields from user profile if not provided
            if not application.applicant_name:
                application.applicant_name = request.user.get_full_name() or f"{request.user.first_name} {request.user.last_name}".strip()
            if not application.applicant_email:
                application.applicant_email = request.user.email
            if not application.applicant_entity and hasattr(request.user, 'organization') and request.user.organization:
                application.applicant_entity = request.user.organization
            if not application.applicant_phone and hasattr(request.user, 'phone') and request.user.phone:
                application.applicant_phone = request.user.phone

            application.save()

            messages.success(request, "Application draft created. Continue to step 2.")
            return redirect('applications:edit_step2', pk=application.pk)
    else:
        form = ApplicationStep1Form(user=request.user)

    context = {
        'form': form,
        'call': call,
        'step': 1,
        'total_steps': 5,
    }
    return render(request, 'applications/wizard_step1.html', context)


@login_required
@transaction.atomic
def application_edit_step2(request, pk):
    """Edit application - Step 2: Funding"""
    application = get_object_or_404(
        Application,
        pk=pk,
        applicant=request.user,
        status='draft'
    )

    if request.method == 'POST':
        form = ApplicationStep2Form(request.POST, instance=application)

        if form.is_valid():
            form.save()
            messages.success(request, "Step 2 saved. Continue to step 3.")
            return redirect('applications:edit_step3', pk=application.pk)
    else:
        form = ApplicationStep2Form(instance=application)

    context = {
        'form': form,
        'application': application,
        'step': 2,
        'total_steps': 5,
    }
    return render(request, 'applications/wizard_step2.html', context)


@login_required
@transaction.atomic
def application_edit_step3(request, pk):
    """Edit application - Step 3: Equipment Requests"""
    application = get_object_or_404(
        Application,
        pk=pk,
        applicant=request.user,
        status='draft'
    )

    if request.method == 'POST':
        service_form = ApplicationStep3Form(request.POST, instance=application)
        access_formset = RequestedAccessFormSet(
            request.POST,
            instance=application,
            form_kwargs={'call': application.call}
        )

        if service_form.is_valid() and access_formset.is_valid():
            service_form.save()
            access_formset.save()

            messages.success(request, "Step 3 saved. Continue to step 4.")
            return redirect('applications:edit_step4', pk=application.pk)
    else:
        service_form = ApplicationStep3Form(instance=application)
        access_formset = RequestedAccessFormSet(
            instance=application,
            form_kwargs={'call': application.call}
        )

    context = {
        'service_form': service_form,
        'access_formset': access_formset,
        'application': application,
        'step': 3,
        'total_steps': 5,
    }
    return render(request, 'applications/wizard_step3.html', context)


@login_required
@transaction.atomic
def application_edit_step4(request, pk):
    """Edit application - Step 4: Scientific Content"""
    application = get_object_or_404(
        Application,
        pk=pk,
        applicant=request.user,
        status='draft'
    )

    if request.method == 'POST':
        form = ApplicationStep4Form(request.POST, instance=application)

        if form.is_valid():
            form.save()
            messages.success(request, "Step 4 saved. Continue to step 5 (final step).")
            return redirect('applications:edit_step5', pk=application.pk)
    else:
        form = ApplicationStep4Form(instance=application)

    context = {
        'form': form,
        'application': application,
        'step': 4,
        'total_steps': 5,
    }
    return render(request, 'applications/wizard_step4.html', context)


@login_required
@transaction.atomic
def application_edit_step5(request, pk):
    """Edit application - Step 5: Declarations & Preview"""
    application = get_object_or_404(
        Application,
        pk=pk,
        applicant=request.user,
        status='draft'
    )

    if request.method == 'POST':
        form = ApplicationStep5Form(request.POST, instance=application)

        if form.is_valid():
            form.save()
            messages.success(request, "All steps complete. Review and submit.")
            return redirect('applications:preview', pk=application.pk)
    else:
        form = ApplicationStep5Form(instance=application)

    context = {
        'form': form,
        'application': application,
        'step': 5,
        'total_steps': 5,
    }
    return render(request, 'applications/wizard_step5.html', context)


@login_required
def application_preview(request, pk):
    """Preview application before submission"""
    application = get_object_or_404(
        Application,
        pk=pk,
        applicant=request.user,
        status='draft'
    )

    requested_access = application.requested_access.select_related(
        'equipment__node'
    ).order_by('equipment__node__code')

    context = {
        'application': application,
        'requested_access': requested_access,
    }
    return render(request, 'applications/preview.html', context)


@login_required
@transaction.atomic
def application_submit(request, pk):
    """Submit application"""
    application = get_object_or_404(
        Application,
        pk=pk,
        applicant=request.user,
        status='draft'
    )

    # Validate application is complete
    if not application.requested_access.exists():
        messages.error(request, "You must request at least one equipment access.")
        return redirect('applications:edit_step3', pk=application.pk)

    if not application.data_consent:
        messages.error(request, "You must consent to data processing.")
        return redirect('applications:edit_step5', pk=application.pk)

    # Check call deadline
    if timezone.now() > application.call.submission_end:
        messages.error(request, "Submission deadline has passed.")
        return redirect('applications:detail', pk=application.pk)

    # Generate application code
    year = timezone.now().year
    call_code = application.call.code
    count = Application.objects.filter(
        call=application.call
    ).exclude(status='draft').count() + 1
    application.code = f"{call_code}-APP-{count:03d}"

    # Submit
    application.status = 'submitted'
    application.submitted_at = timezone.now()
    application.save()

    # Create feasibility reviews for each node
    nodes = set()
    for access_request in application.requested_access.all():
        nodes.add(access_request.equipment.node)

    for node in nodes:
        # Get node coordinator (director)
        coordinator = node.director
        if coordinator:
            FeasibilityReview.objects.create(
                application=application,
                node=node,
                reviewer=coordinator
            )

    # Update application status
    application.status = 'under_feasibility_review'
    application.save()

    # Send confirmation email (gracefully handle Celery unavailability)
    try:
        from communications.tasks import send_email_from_template
        send_email_from_template.delay(
            template_type='application_received',
            recipient_email=request.user.email,
            context_data={
                'applicant_name': request.user.get_full_name(),
                'application_code': application.code,
                'call_code': application.call.code,
            },
            recipient_user_id=request.user.id,
            related_application_id=application.id
        )

        # Send feasibility request emails
        for review in application.feasibility_reviews.all():
            send_email_from_template.delay(
                template_type='feasibility_request',
                recipient_email=review.reviewer.email,
                context_data={
                    'reviewer_name': review.reviewer.get_full_name(),
                    'application_code': application.code,
                    'node_name': review.node.name,
                },
                recipient_user_id=review.reviewer.id,
                related_application_id=application.id
            )
        email_status = "You will receive confirmation by email."
    except Exception as e:
        # Celery/Redis not available - log and continue
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Email notification failed (Celery unavailable): {e}")
        email_status = "(Email notifications disabled - Celery not running)"

    messages.success(
        request,
        f"Application {application.code} submitted successfully! {email_status}"
    )
    return redirect('applications:detail', pk=application.pk)


# ============================================================================
# Phase 3: Feasibility Review Views (Node Coordinators)
# ============================================================================

@node_coordinator_required
def feasibility_queue(request):
    """
    Node coordinator's queue of pending feasibility reviews.

    Shows all applications requiring feasibility review for nodes
    where the current user is the director.
    """
    # Get nodes where user is director
    user_nodes = request.user.directed_nodes.all()

    # Get pending reviews for these nodes
    pending_reviews = FeasibilityReview.objects.filter(
        node__in=user_nodes,
        is_feasible__isnull=True  # Pending = not yet decided
    ).select_related(
        'application__applicant',
        'application__call',
        'node'
    ).order_by('application__submitted_at')

    context = {
        'pending_reviews': pending_reviews,
        'user_nodes': user_nodes,
    }
    return render(request, 'applications/feasibility_queue.html', context)


@node_coordinator_required
def feasibility_review(request, pk):
    """
    Review an application for feasibility.

    Node coordinators can approve or reject based on technical
    feasibility and resource availability.
    """
    review = get_object_or_404(
        FeasibilityReview,
        pk=pk,
        reviewer=request.user,
        is_feasible__isnull=True  # Pending = not yet decided
    )

    application = review.application

    # Get requested access for this node only
    requested_access = application.requested_access.filter(
        equipment__node=review.node
    ).select_related('equipment')

    if request.method == 'POST':
        form = FeasibilityReviewForm(request.POST, instance=review)

        if form.is_valid():
            review = form.save(commit=False)
            review.reviewed_at = timezone.now()
            review.save()

            # Check if all reviews are complete
            all_reviews = application.feasibility_reviews.all()
            pending_count = all_reviews.filter(is_feasible__isnull=True).count()

            if pending_count == 0:
                # All reviews complete - check outcomes
                rejected_count = all_reviews.filter(is_feasible=False).count()

                if rejected_count > 0:
                    # Any rejection = application rejected (feasibility)
                    application.status = 'rejected_feasibility'
                    application.save()
                    status_msg = "rejected"
                else:
                    # All approved = move to pending evaluation
                    application.status = 'pending_evaluation'
                    application.save()
                    status_msg = "approved and ready for evaluation"

                # Send email to applicant
                try:
                    from communications.tasks import send_email_from_template
                    send_email_from_template.delay(
                        template_type='feasibility_complete',
                        recipient_email=application.applicant.email,
                        context_data={
                            'applicant_name': application.applicant.get_full_name(),
                            'application_code': application.code,
                            'status': status_msg,
                        },
                        recipient_user_id=application.applicant.id,
                        related_application_id=application.id
                    )
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Email notification failed: {e}")

            decision_text = "Approved" if review.is_feasible else "Rejected"
            messages.success(
                request,
                f"Feasibility review submitted for {application.code}. Decision: {decision_text}"
            )
            return redirect('applications:feasibility_queue')
    else:
        form = FeasibilityReviewForm(instance=review)

    context = {
        'form': form,
        'review': review,
        'application': application,
        'requested_access': requested_access,
    }
    return render(request, 'applications/feasibility_review.html', context)


# =============================================================================
# Phase 6: Resolution Views
# =============================================================================

@login_required
@role_required('coordinator')
def resolution_dashboard(request):
    """
    Resolution dashboard showing calls ready for coordinator review.

    Lists calls that have:
    - Evaluation deadline passed
    - At least one application in 'evaluated' status
    """
    from django.db.models import Count, Avg
    from django.utils import timezone
    from calls.models import Call

    now = timezone.now()

    # Get calls with evaluation deadline passed
    calls = (
        Call.objects
        .filter(evaluation_deadline__lt=now)
        .annotate(
            total_apps=Count('applications'),
            evaluated_apps=Count('applications', filter=Q(applications__status='evaluated')),
            avg_score=Avg('applications__final_score')
        )
        .filter(evaluated_apps__gt=0)  # Only calls with apps to resolve
        .order_by('-evaluation_deadline')
    )

    # Add resolution summary for each call
    from applications.services import ResolutionService
    calls_with_stats = []
    for call in calls:
        service = ResolutionService(call)
        stats = service.get_resolution_summary()
        calls_with_stats.append({
            'call': call,
            'stats': stats
        })

    context = {
        'calls_with_stats': calls_with_stats,
    }
    return render(request, 'applications/resolution/dashboard.html', context)


@login_required
@role_required('coordinator')
def call_resolution_detail(request, call_id):
    """
    Prioritized list of applications for resolution.

    Shows applications sorted by priority (score DESC, code ASC) with:
    - Hours availability per equipment
    - Current resolution status
    - Actions to set resolution
    """
    from calls.models import Call
    from applications.services import ResolutionService

    call = get_object_or_404(Call, pk=call_id)
    service = ResolutionService(call)

    # Get prioritized applications
    applications = service.get_prioritized_applications()

    # Get hours availability
    hours_availability = service.calculate_hours_availability()

    # Get resolution summary
    summary = service.get_resolution_summary()

    context = {
        'call': call,
        'applications': applications,
        'hours_availability': hours_availability,
        'summary': summary,
    }
    return render(request, 'applications/resolution/call_detail.html', context)


@login_required
@role_required('coordinator')
def application_resolution(request, application_id):
    """
    AJAX endpoint for individual application resolution.

    GET: Return application details as JSON
    POST: Apply resolution and return result
    """
    import json
    from django.http import JsonResponse
    from applications.forms import ApplicationResolutionForm
    from applications.services import ResolutionService

    application = get_object_or_404(Application, pk=application_id)
    service = ResolutionService(application.call)

    if request.method == 'GET':
        # Return application details
        can_accept, reason, details = service.can_accept_application(application)

        data = {
            'id': application.id,
            'code': application.code,
            'applicant_name': application.applicant_name,
            'brief_description': application.brief_description,
            'final_score': float(application.final_score) if application.final_score else None,
            'has_competitive_funding': application.has_competitive_funding,
            'current_resolution': application.resolution,
            'resolution_comments': application.resolution_comments,
            'can_accept': can_accept,
            'acceptance_reason': reason,
            'acceptance_details': details,
            'requested_access': [
                {
                    'equipment': ra.equipment.name,
                    'hours_requested': float(ra.hours_requested),
                    'hours_granted': float(ra.hours_granted) if ra.hours_granted else None,
                }
                for ra in application.requested_access.select_related('equipment').all()
            ]
        }
        return JsonResponse(data)

    elif request.method == 'POST':
        # Apply resolution
        form = ApplicationResolutionForm(request.POST, instance=application, application=application)

        if form.is_valid():
            resolution = form.cleaned_data['resolution']
            comments = form.cleaned_data['resolution_comments']

            try:
                result = service.apply_resolution(
                    application,
                    resolution,
                    comments,
                    request.user
                )
                return JsonResponse({
                    'success': True,
                    'message': f'Resolution applied: {resolution}',
                    'result': result
                })
            except ValidationError as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=400)
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)


@login_required
@role_required('coordinator')
def bulk_resolution(request, call_id):
    """
    AJAX endpoint for bulk auto-allocation of resolutions.

    POST: Apply bulk resolution and return summary
    """
    from django.http import JsonResponse
    from applications.forms import BulkResolutionForm
    from applications.services import ResolutionService
    from calls.models import Call

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    call = get_object_or_404(Call, pk=call_id)
    service = ResolutionService(call)

    form = BulkResolutionForm(request.POST)

    if form.is_valid():
        threshold_score = form.cleaned_data['threshold_score']
        auto_pending = form.cleaned_data['auto_pending']

        try:
            result = service.bulk_auto_allocate(
                threshold_score=threshold_score,
                auto_pending=auto_pending
            )
            return JsonResponse({
                'success': True,
                'message': f'Bulk resolution complete',
                'result': result
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    else:
        return JsonResponse({
            'success': False,
            'errors': form.errors
        }, status=400)


@login_required
@role_required('coordinator')
def finalize_resolution(request, call_id):
    """
    Finalize call resolution and trigger notifications.

    POST: Lock call and send notification emails
    """
    from calls.models import Call
    from applications.services import ResolutionService

    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
        return redirect('applications:resolution_dashboard')

    call = get_object_or_404(Call, pk=call_id)
    service = ResolutionService(call)

    try:
        result = service.finalize_resolution(request.user)
        messages.success(
            request,
            f'Resolution finalized for {call.code}. '
            f'{result["statistics"]["total"]} notifications sent.'
        )
        return redirect('applications:resolution_dashboard')
    except ValidationError as e:
        messages.error(request, str(e))
        return redirect('applications:call_resolution_detail', call_id=call.id)
