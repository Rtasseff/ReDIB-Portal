"""
Views for the applications app - 5-step application wizard.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
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
    """View application details (applicant or coordinator view)"""
    # Check if user is coordinator/superuser or the applicant
    user = request.user
    user_roles = list(user.roles.filter(is_active=True).values_list('role', flat=True))
    is_coordinator = 'coordinator' in user_roles or user.is_superuser

    if is_coordinator:
        # Coordinators can view any application
        application = get_object_or_404(Application, pk=pk)
    else:
        # Regular users can only view their own applications
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

    # Ensure user has applicant role
    from core.models import UserRole
    UserRole.objects.get_or_create(
        user=request.user,
        role='applicant',
        defaults={'is_active': True}
    )

    # Submit
    application.status = 'submitted'
    application.submitted_at = timezone.now()
    application.save()

    # Create feasibility reviews for each node
    nodes = set()
    for access_request in application.requested_access.all():
        nodes.add(access_request.equipment.node)

    for node in nodes:
        # Get node coordinators via UserRole
        node_coordinators = UserRole.objects.filter(
            node=node,
            role='node_coordinator',
            is_active=True
        ).select_related('user')

        # Create a feasibility review for each coordinator
        # (typically one per node, but handle multiple if needed)
        for user_role in node_coordinators:
            FeasibilityReview.objects.create(
                application=application,
                node=node,
                reviewer=user_role.user
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
            # Build absolute URL for the review
            review_url = request.build_absolute_uri(
                reverse('applications:feasibility_review', kwargs={'pk': review.pk})
            )

            send_email_from_template.delay(
                template_type='feasibility_request',
                recipient_email=review.reviewer.email,
                context_data={
                    'reviewer_name': review.reviewer.get_full_name(),
                    'application_code': application.code,
                    'node_name': review.node.name,
                    'review_url': review_url,
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
    where the current user is a node coordinator (via UserRole).
    """
    from core.models import UserRole

    # Get nodes where user is coordinator (via UserRole)
    my_nodes = UserRole.objects.filter(
        user=request.user,
        role='node_coordinator',
        is_active=True
    ).values_list('node_id', flat=True)

    # Get pending reviews for these nodes
    pending_reviews = FeasibilityReview.objects.filter(
        node_id__in=my_nodes,
        is_feasible__isnull=True  # Pending = not yet decided
    ).select_related(
        'application__applicant',
        'application__call',
        'node'
    ).order_by('application__submitted_at')

    context = {
        'pending_reviews': pending_reviews,
        'user_nodes': my_nodes,
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
@role_required('coordinator', 'admin')
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

    # Get all calls with evaluated applications (ready for resolution)
    # Note: Coordinator can start resolving before deadline if all evaluations are complete
    calls = (
        Call.objects
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

    # Get resolution summary
    summary = service.get_resolution_summary()

    context = {
        'call': call,
        'applications': applications,
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


# =============================================================================
# Phase 7: Acceptance & Handoff Views
# =============================================================================

@login_required
def application_acceptance(request, pk):
    """
    View for applicant to accept or decline approved application.

    GET: Show application details and accept/decline form
    POST: Process acceptance or decline action

    Permission: Must be the applicant
    """
    from communications.tasks import send_email_from_template

    # Get application - must be applicant
    application = get_object_or_404(
        Application,
        pk=pk,
        applicant=request.user
    )

    # Check if already responded or wrong status
    if application.status != 'accepted':
        messages.warning(request,
            f"This application is in '{application.get_status_display()}' status and cannot be accepted/declined."
        )
        return redirect('applications:detail', pk=application.pk)

    if application.accepted_by_applicant is not None:
        status_msg = "accepted" if application.accepted_by_applicant else "declined"
        messages.info(request, f"You have already {status_msg} this application.")
        return redirect('applications:detail', pk=application.pk)

    # Check if deadline passed
    if application.acceptance_deadline_passed:
        messages.error(request,
            f"The acceptance deadline ({application.acceptance_deadline.date()}) has passed. "
            "This application will be marked as expired."
        )
        return redirect('applications:detail', pk=application.pk)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'accept':
            # Accept application and send handoff email
            application.accepted_by_applicant = True
            application.accepted_at = timezone.now()
            application.save()

            # Send handoff email to applicant + node coordinators
            _send_handoff_email(application)
            application.handoff_email_sent_at = timezone.now()
            application.save()

            messages.success(request,
                "You have accepted the access grant. Handoff email sent to node coordinators."
            )
            return redirect('applications:detail', pk=application.pk)

        elif action == 'decline':
            # Decline application
            decline_reason = request.POST.get('decline_reason', '')
            application.status = 'declined_by_applicant'
            application.accepted_by_applicant = False
            application.accepted_at = timezone.now()
            if decline_reason:
                application.resolution_comments += f"\n\n[DECLINED BY APPLICANT]\n{decline_reason}"
            application.save()

            messages.info(request, "You have declined this access grant.")
            return redirect('applications:detail', pk=application.pk)

    # GET: Show acceptance form
    requested_access = application.requested_access.select_related(
        'equipment__node'
    ).order_by('equipment__node__code')

    context = {
        'application': application,
        'requested_access': requested_access,
        'days_remaining': application.days_until_acceptance_deadline,
        'deadline': application.acceptance_deadline,
    }
    return render(request, 'applications/acceptance_form.html', context)


def _send_handoff_email(application):
    """Helper function to send handoff email to applicant and node coordinators."""
    from communications.tasks import send_email_from_template
    from core.models import UserRole

    # Get all nodes involved
    nodes = set()
    requested_access_list = []
    for req_access in application.requested_access.select_related('equipment__node'):
        nodes.add(req_access.equipment.node)
        requested_access_list.append({
            'node': req_access.equipment.node.name,
            'equipment': req_access.equipment.name,
            'hours': float(req_access.hours_requested),
        })

    # Build email context
    context = {
        'applicant_name': application.applicant.get_full_name(),
        'applicant_entity': application.applicant_entity,
        'applicant_email': application.applicant.email,
        'applicant_phone': application.applicant_phone or 'Not provided',
        'application_code': application.code,
        'project_title': application.project_title,
        'brief_description': application.brief_description,
        'service_modality': application.get_service_modality_display() if application.service_modality else 'Not specified',
        'node_names': ', '.join([n.name for n in nodes]),
        'requested_access': requested_access_list,
    }

    # Send to applicant
    send_email_from_template(
        template_type='handoff_notification',
        recipient_email=application.applicant.email,
        context_data=context,
        recipient_user_id=application.applicant.id,
        related_application_id=application.id
    )

    # Send to node directors
    for node in nodes:
        node_directors = UserRole.objects.filter(
            node=node,
            role='node_director'
        ).select_related('user')

        for user_role in node_directors:
            send_email_from_template(
                template_type='handoff_notification',
                recipient_email=user_role.user.email,
                context_data=context,
                recipient_user_id=user_role.user.id,
                related_application_id=application.id
            )


@login_required
@role_required('coordinator')
def handoff_dashboard(request):
    """
    Coordinator view of applications that have been handed off to nodes.

    Shows applications where:
    - accepted_by_applicant=True
    - handoff_email_sent_at is not None

    Allows filtering by completion status.
    """
    from django.db.models import Prefetch

    # Get all accepted and handed-off applications
    handed_off_apps = (
        Application.objects
        .filter(
            status='accepted',
            accepted_by_applicant=True,
            handoff_email_sent_at__isnull=False
        )
        .select_related('applicant', 'call')
        .prefetch_related(
            Prefetch(
                'requested_access',
                queryset=RequestedAccess.objects.select_related('equipment__node')
            )
        )
        .order_by('-handoff_email_sent_at')
    )

    # Optional: Filter by completion status
    show_completed = request.GET.get('show_completed', 'all')
    if show_completed == 'incomplete':
        handed_off_apps = handed_off_apps.filter(is_completed=False)
    elif show_completed == 'complete':
        handed_off_apps = handed_off_apps.filter(is_completed=True)

    context = {
        'applications': handed_off_apps,
        'show_completed': show_completed,
    }
    return render(request, 'applications/handoff_dashboard.html', context)


@login_required
@role_required('coordinator')
@transaction.atomic
def mark_completed(request, pk):
    """
    Optional: Mark application as completed for reporting purposes.

    POST only: Set is_completed=True, completed_at=now
    """
    if request.method != 'POST':
        return redirect('applications:handoff_dashboard')

    application = get_object_or_404(
        Application,
        pk=pk,
        status='accepted',
        accepted_by_applicant=True
    )

    if not application.is_completed:
        application.is_completed = True
        application.completed_at = timezone.now()
        application.save()
        messages.success(request, f"Application {application.code} marked as completed.")
    else:
        messages.info(request, f"Application {application.code} is already marked as completed.")

    return redirect('applications:handoff_dashboard')


# =============================================================================
# Phase 6: Node Coordinator Resolution Views (Multi-Node Coordination)
# =============================================================================

@node_coordinator_required
def node_resolution_queue(request):
    """
    Node coordinator's queue of applications awaiting resolution.

    Shows applications in 'evaluated' status that request equipment
    from nodes where the current user is a node coordinator.
    """
    from core.models import UserRole
    from applications.services import NodeResolutionService
    from applications.models import Application, NodeResolution

    # Get nodes where user is coordinator
    my_node_roles = UserRole.objects.filter(
        user=request.user,
        role='node_coordinator',
        is_active=True
    ).select_related('node')

    user_nodes = [role.node for role in my_node_roles]

    if not user_nodes:
        context = {
            'user_nodes': [],
            'pending_applications': [],
            'resolved_applications': [],
            'summary': {'total': 0, 'awaiting_decision': 0, 'node_accepted': 0, 'fully_resolved': 0},
        }
        return render(request, 'applications/node_resolution/queue.html', context)

    # Collect pending and resolved applications across all user's nodes
    # Use dict to track which node each pending app is for (app can appear once per node)
    pending_items = []  # List of (application, node) tuples
    resolved_applications = set()

    for node in user_nodes:
        service = NodeResolutionService(node=node)
        # Get applications awaiting this node's decision
        pending_apps = service.get_applications_for_node_resolution()
        for app in pending_apps:
            pending_items.append({'application': app, 'node': node})

        # Get applications where this node has already decided
        resolved_by_node = Application.objects.filter(
            requested_access__equipment__node=node,
            node_resolutions__node=node,
            node_resolutions__resolution__in=['accept', 'waitlist', 'reject']
        ).distinct().prefetch_related('node_resolutions', 'node_resolutions__node')
        resolved_applications.update(resolved_by_node)

    # Sort pending items by final_score descending, then by code
    pending_items = sorted(
        pending_items,
        key=lambda x: (-(x['application'].final_score or 0), x['application'].code)
    )
    resolved_applications = sorted(
        resolved_applications,
        key=lambda x: (-(x.final_score or 0), x.code)
    )

    # Build summary stats
    summary = {
        'total': len(pending_items) + len(resolved_applications),
        'awaiting_decision': len(pending_items),
        'node_accepted': sum(
            1 for app in resolved_applications
            if any(
                nr.resolution == 'accept' and nr.node in user_nodes
                for nr in app.node_resolutions.all()
            )
        ),
        'fully_resolved': sum(
            1 for app in resolved_applications
            if app.resolution in ['accepted', 'pending', 'rejected']
        ),
    }

    context = {
        'user_nodes': user_nodes,
        'pending_items': pending_items,  # List of {'application': app, 'node': node}
        'resolved_applications': resolved_applications,
        'summary': summary,
    }
    return render(request, 'applications/node_resolution/queue.html', context)


@node_coordinator_required
@transaction.atomic
def node_resolution_review(request, application_id, node_id):
    """
    Node coordinator reviews and resolves an application for their node.

    Allows setting:
    - Node-level resolution (accept/waitlist/reject)
    - Hours approved per equipment item
    - Comments
    """
    from core.models import UserRole, Node
    from applications.services import NodeResolutionService
    from applications.forms import NodeResolutionForm, NodeResolutionEquipmentForm
    from decimal import Decimal

    application = get_object_or_404(Application, pk=application_id)
    node = get_object_or_404(Node, pk=node_id)

    # Verify user is node coordinator for this node
    if not UserRole.objects.filter(
        user=request.user,
        role='node_coordinator',
        node=node,
        is_active=True
    ).exists():
        messages.error(request, "You are not authorized to review applications for this node.")
        return redirect('applications:node_resolution_queue')

    # Verify application is in evaluated status
    if application.status != 'evaluated':
        messages.error(request, f"Application {application.code} is not awaiting resolution (status: {application.status}).")
        return redirect('applications:node_resolution_queue')

    service = NodeResolutionService(node=node)

    # Get equipment requested from this node
    requested_access = service.get_equipment_for_node(application)

    # Get existing node resolution if any
    existing_resolution = service.get_node_resolution_for_application(application)

    # Check if already resolved by this node
    if existing_resolution and existing_resolution.resolution:
        messages.info(request, f"You have already resolved application {application.code} for {node.code}.")
        return redirect('applications:node_resolution_queue')

    if request.method == 'POST':
        form = NodeResolutionForm(
            request.POST,
            has_competitive_funding=application.has_competitive_funding
        )

        # Build approved hours dict from POST data
        approved_hours = {}
        for ra in requested_access:
            field_name = f'hours_approved_{ra.equipment.id}'
            try:
                hours = Decimal(request.POST.get(field_name, ra.hours_requested))
                approved_hours[ra.equipment.id] = hours
            except (ValueError, TypeError):
                approved_hours[ra.equipment.id] = ra.hours_requested

        if form.is_valid():
            try:
                result = service.apply_node_resolution(
                    application=application,
                    resolution=form.cleaned_data['resolution'],
                    comments=form.cleaned_data['comments'],
                    approved_hours_dict=approved_hours,
                    user=request.user
                )

                # Success message
                if result['aggregated']:
                    messages.success(
                        request,
                        f"Resolution submitted for {application.code}. "
                        f"All nodes have decided - Final resolution: {result['final_resolution'].upper()}"
                    )
                else:
                    messages.success(
                        request,
                        f"Resolution submitted for {application.code}. "
                        f"Waiting for other nodes to complete their reviews."
                    )

                return redirect('applications:node_resolution_queue')

            except Exception as e:
                messages.error(request, str(e))
    else:
        # Prepopulate form if existing resolution
        initial = {}
        if existing_resolution:
            initial = {
                'resolution': existing_resolution.resolution,
                'comments': existing_resolution.comments,
            }
        form = NodeResolutionForm(
            initial=initial,
            has_competitive_funding=application.has_competitive_funding
        )

    # Prepare equipment data for template
    equipment_data = []
    for ra in requested_access:
        equipment_data.append({
            'requested_access': ra,
            'equipment': ra.equipment,
            'hours_requested': ra.hours_requested,
            'hours_approved': ra.hours_approved or ra.hours_requested,
        })

    # Get evaluations for display
    evaluations = application.evaluations.select_related('evaluator').all()

    context = {
        'form': form,
        'application': application,
        'node': node,
        'equipment_data': equipment_data,
        'evaluations': evaluations,
        'existing_resolution': existing_resolution,
    }
    return render(request, 'applications/node_resolution/review.html', context)


# =============================================================================
# Equipment Completion Views (Applicants and Node Coordinators)
# =============================================================================

@login_required
@transaction.atomic
def mark_equipment_done(request, application_id, requested_access_id):
    """
    Applicant marks an equipment item as completed and reports actual hours.
    """
    from applications.forms import EquipmentCompletionForm

    # Verify applicant owns this application
    application = get_object_or_404(
        Application,
        pk=application_id,
        applicant=request.user,
        status='accepted',
        accepted_by_applicant=True
    )

    req_access = get_object_or_404(
        RequestedAccess,
        pk=requested_access_id,
        application=application
    )

    # Check if already completed
    if req_access.is_completed:
        messages.info(request, f"Equipment {req_access.equipment.name} is already marked as completed.")
        return redirect('applications:detail', pk=application.id)

    if request.method == 'POST':
        form = EquipmentCompletionForm(
            request.POST,
            hours_approved=req_access.hours_approved
        )

        if form.is_valid():
            req_access.is_completed = True
            req_access.completed_by = request.user
            req_access.completed_at = timezone.now()
            req_access.actual_hours_used = form.cleaned_data['actual_hours_used']
            req_access.save()

            messages.success(
                request,
                f"Marked {req_access.equipment.name} as complete. "
                f"Actual hours used: {req_access.actual_hours_used}"
            )
            return redirect('applications:detail', pk=application.id)
    else:
        form = EquipmentCompletionForm(hours_approved=req_access.hours_approved)

    context = {
        'form': form,
        'application': application,
        'requested_access': req_access,
    }
    return render(request, 'applications/equipment_completion.html', context)


@node_coordinator_required
@transaction.atomic
def node_confirm_equipment_done(request, requested_access_id):
    """
    Node coordinator marks equipment as completed.

    Can override actual hours if needed.
    """
    from core.models import UserRole
    from applications.forms import EquipmentCompletionForm

    req_access = get_object_or_404(
        RequestedAccess.objects.select_related('equipment__node', 'application'),
        pk=requested_access_id
    )

    # Verify user is node coordinator for this equipment's node
    if not UserRole.objects.filter(
        user=request.user,
        role='node_coordinator',
        node=req_access.equipment.node,
        is_active=True
    ).exists():
        messages.error(request, "You are not authorized to complete equipment for this node.")
        return redirect('applications:node_resolution_queue')

    application = req_access.application

    # Check if already completed
    if req_access.is_completed:
        messages.info(request, f"Equipment {req_access.equipment.name} is already marked as completed.")
        return redirect('applications:detail', pk=application.id)

    if request.method == 'POST':
        form = EquipmentCompletionForm(
            request.POST,
            hours_approved=req_access.hours_approved
        )

        if form.is_valid():
            req_access.is_completed = True
            req_access.completed_by = request.user
            req_access.completed_at = timezone.now()
            req_access.actual_hours_used = form.cleaned_data['actual_hours_used']
            req_access.save()

            messages.success(
                request,
                f"Marked {req_access.equipment.name} as complete for {application.code}. "
                f"Actual hours used: {req_access.actual_hours_used}"
            )
            return redirect('applications:detail', pk=application.id)
    else:
        form = EquipmentCompletionForm(hours_approved=req_access.hours_approved)

    context = {
        'form': form,
        'application': application,
        'requested_access': req_access,
    }
    return render(request, 'applications/equipment_completion.html', context)
