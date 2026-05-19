"""
Views for the applications app - 5-step application wizard.
"""
from django.core.exceptions import ValidationError
from django.http import Http404
from django.views.decorators.http import require_POST
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
    ApplicationStep1DraftForm, ApplicationStep2DraftForm,
    ApplicationStep3DraftForm, ApplicationStep4DraftForm,
    ApplicationStep5DraftForm,
    FeasibilityReviewForm
)


DRAFT_SAVED_MSG = (
    "Draft saved. You can return any time from My Applications to continue."
)


def _is_draft_save(request):
    return request.method == 'POST' and request.POST.get('action') == 'save_draft'


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
    """View application details.

    Accessible by:
    - Applicant (owns the application)
    - ReDIB coordinator / superuser (any application)
    - Node coordinator of a node whose equipment is requested in the
      application (so they can see the full detail of applications they
      need to act on, e.g. after marking access complete)
    """
    from core.models import UserRole

    user = request.user
    user_roles = list(user.roles.filter(is_active=True).values_list('role', flat=True))
    is_coordinator = 'coordinator' in user_roles or user.is_superuser

    application = get_object_or_404(Application, pk=pk)

    if not is_coordinator and application.applicant_id != user.id:
        # Permit a node coordinator whose node has equipment in this application.
        requested_node_ids = set(
            application.requested_access.values_list('equipment__node_id', flat=True)
        )
        nc_node_ids = set(
            UserRole.objects.filter(
                user=user,
                role='node_coordinator',
                is_active=True,
            ).values_list('node_id', flat=True)
        )
        if not (requested_node_ids & nc_node_ids):
            raise Http404("Application not found.")

    requested_access = application.requested_access.select_related(
        'equipment__node'
    ).order_by('equipment__node__code')

    # Show edit-request feedback to the applicant when application is in draft after a reopen
    edit_requests = []
    if application.status == 'draft':
        edit_requests = list(application.feasibility_reviews.filter(
            status='edits_requested'
        ).select_related('node', 'reviewer'))

    context = {
        'application': application,
        'requested_access': requested_access,
        'is_coordinator': is_coordinator,
        'edit_requests': edit_requests,
        'phase_tracker': _build_phase_tracker(application),
    }

    # Add feasibility review status for coordinators
    if is_coordinator:
        feasibility_reviews = application.feasibility_reviews.select_related(
            'node', 'reviewer'
        ).order_by('node__code')

        # Build a combined view: for each requested node, show review status
        feasibility_status = []
        reviewed_node_ids = {fr.node_id: fr for fr in feasibility_reviews}

        for access in requested_access:
            node = access.equipment.node
            if node.id in reviewed_node_ids:
                review = reviewed_node_ids[node.id]
                feasibility_status.append({
                    'node': node,
                    'equipment': access.equipment,
                    'status': review.status,
                    'reviewer': review.reviewer,
                    'reviewed_at': review.reviewed_at,
                    'comments': review.comments,
                })
            else:
                feasibility_status.append({
                    'node': node,
                    'equipment': access.equipment,
                    'status': 'pending',
                    'reviewer': None,
                    'reviewed_at': None,
                    'comments': '',
                })

        # Deduplicate by node (multiple equipment from same node)
        seen_nodes = set()
        unique_feasibility = []
        for item in feasibility_status:
            if item['node'].id not in seen_nodes:
                seen_nodes.add(item['node'].id)
                unique_feasibility.append(item)

        context['feasibility_status'] = unique_feasibility

        # Evaluation summary for coordinators — per-evaluator scores,
        # average, recommendations, completion timestamps.
        completed_evals = list(
            application.evaluations.select_related('evaluator')
            .exclude(completed_at__isnull=True)
            .order_by('completed_at')
        )
        if completed_evals:
            totals = [float(e.total_score) for e in completed_evals if e.total_score is not None]
            context['evaluation_summary'] = {
                'evaluations': completed_evals,
                'count': len(completed_evals),
                'assigned': application.evaluations.count(),
                'average': round(sum(totals) / len(totals), 2) if totals else None,
                'min': min(totals) if totals else None,
                'max': max(totals) if totals else None,
            }

    return render(request, 'applications/detail.html', context)


def _build_phase_tracker(application):
    """Build a list of (label, state) tuples representing the workflow
    phases for this application.

    `state` is one of 'complete', 'current', 'pending', 'terminal-fail'.
    The tracker short-circuits on terminal-failure statuses so the UI can
    communicate "this application did not proceed past phase X".
    """
    status = application.status

    # Map every status to a position in the phase sequence.
    PHASES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('feasibility', 'Feasibility Review'),
        ('evaluation', 'Evaluation'),
        ('resolution', 'Resolution'),
        ('acceptance', 'Acceptance'),
        ('access', 'Access'),
    ]

    # Which phase is the application currently at? (keyed by phase id)
    status_phase = {
        'draft': 'draft',
        'submitted': 'submitted',
        'under_feasibility_review': 'feasibility',
        'rejected_feasibility': 'feasibility',
        'pending_evaluation': 'evaluation',
        'under_evaluation': 'evaluation',
        'evaluated': 'resolution',
        'accepted': 'acceptance',
        'pending': 'acceptance',
        'rejected': 'resolution',
        'declined_by_applicant': 'acceptance',
        'expired': 'acceptance',
        'completed': 'access',
    }.get(status, 'draft')

    # Once the applicant has accepted and the handoff email has been sent,
    # consider the 'acceptance' phase complete and highlight 'access'.
    if status == 'accepted' and application.accepted_by_applicant and application.handoff_email_sent_at:
        status_phase = 'access'
    # 'completed' is a terminal success on 'access'.
    if application.is_completed:
        status_phase = 'access'

    terminal_fail_statuses = {
        'rejected_feasibility', 'rejected',
        'declined_by_applicant', 'expired',
    }
    is_terminal_fail = status in terminal_fail_statuses
    phase_order = [p_id for p_id, _ in PHASES]

    try:
        current_idx = phase_order.index(status_phase)
    except ValueError:
        current_idx = 0

    tracker = []
    for idx, (phase_id, label) in enumerate(PHASES):
        if is_terminal_fail and idx == current_idx:
            state = 'terminal-fail'
        elif idx < current_idx:
            state = 'complete'
        elif idx == current_idx and application.is_completed:
            state = 'complete'
        elif idx == current_idx:
            state = 'current'
        else:
            state = 'pending' if not is_terminal_fail else 'pending'
        tracker.append({'id': phase_id, 'label': label, 'state': state})

    return tracker


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

            # Always overwrite profile fields from current user profile
            user = request.user
            application.applicant_name = user.get_full_name() or f"{user.first_name} {user.last_name}".strip()
            application.applicant_email = user.email
            if user.organization:
                application.applicant_entity = str(user.organization)
            if user.phone:
                application.applicant_phone = user.phone
            if user.orcid:
                application.applicant_orcid = user.orcid

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
def application_edit_step1(request, pk):
    """Edit application - Step 1: Basic Information"""
    application = get_object_or_404(
        Application,
        pk=pk,
        applicant=request.user,
        status='draft'
    )

    draft_mode = _is_draft_save(request)

    if request.method == 'POST':
        form_cls = ApplicationStep1DraftForm if draft_mode else ApplicationStep1Form
        form = form_cls(request.POST, instance=application, user=request.user)

        if form.is_valid():
            app = form.save(commit=False)
            # Overwrite profile fields from current user profile
            user = request.user
            app.applicant_name = user.get_full_name() or f"{user.first_name} {user.last_name}".strip()
            app.applicant_email = user.email
            if user.organization:
                app.applicant_entity = str(user.organization)
            if user.phone:
                app.applicant_phone = user.phone
            if user.orcid:
                app.applicant_orcid = user.orcid
            app.save()
            if draft_mode:
                messages.success(request, DRAFT_SAVED_MSG)
                return redirect('applications:my_applications')
            messages.success(request, "Step 1 saved. Continue to step 2.")
            return redirect('applications:edit_step2', pk=application.pk)
    else:
        form = ApplicationStep1Form(instance=application, user=request.user)

    context = {
        'form': form,
        'application': application,
        'call': application.call,
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

    draft_mode = _is_draft_save(request)

    if request.method == 'POST':
        form_cls = ApplicationStep2DraftForm if draft_mode else ApplicationStep2Form
        form = form_cls(request.POST, instance=application)

        if form.is_valid():
            form.save()
            if draft_mode:
                messages.success(request, DRAFT_SAVED_MSG)
                return redirect('applications:my_applications')
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

    draft_mode = _is_draft_save(request)

    if request.method == 'POST':
        # Fix INITIAL_FORMS to match forms that actually have database IDs.
        # Browser-side JS may remove existing forms and add new ones, leaving
        # INITIAL_FORMS stale and higher than the actual count of existing records.
        post_data = request.POST.copy()
        prefix = 'requested_access'
        total = int(post_data.get(f'{prefix}-TOTAL_FORMS', 0))
        actual_initial = 0
        for i in range(total):
            if post_data.get(f'{prefix}-{i}-id', ''):
                actual_initial += 1
        post_data[f'{prefix}-INITIAL_FORMS'] = str(actual_initial)

        service_form_cls = ApplicationStep3DraftForm if draft_mode else ApplicationStep3Form
        service_form = service_form_cls(post_data, instance=application)
        access_formset = RequestedAccessFormSet(
            post_data,
            instance=application,
            form_kwargs={'call': application.call}
        )

        if draft_mode:
            # Equipment rows still require both fields filled to persist, but
            # we relax the formset's "at least one row" rule so a user with
            # no equipment yet can still save their service-modality choice.
            access_formset.validate_min = False
            service_ok = service_form.is_valid()
            formset_ok = access_formset.is_valid()
            if service_ok:
                service_form.save()
            if formset_ok:
                access_formset.save()
            messages.success(request, DRAFT_SAVED_MSG)
            if not formset_ok:
                messages.warning(
                    request,
                    "Some equipment rows were incomplete and were not saved. "
                    "Complete or remove them before clicking Next."
                )
            return redirect('applications:my_applications')

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

    draft_mode = _is_draft_save(request)

    if request.method == 'POST':
        form_cls = ApplicationStep4DraftForm if draft_mode else ApplicationStep4Form
        form = form_cls(request.POST, instance=application)

        if form.is_valid():
            form.save()
            if draft_mode:
                messages.success(request, DRAFT_SAVED_MSG)
                return redirect('applications:my_applications')
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

    draft_mode = _is_draft_save(request)

    if request.method == 'POST':
        form_cls = ApplicationStep5DraftForm if draft_mode else ApplicationStep5Form
        form = form_cls(request.POST, instance=application, user=request.user)

        if form.is_valid():
            app = form.save(commit=False)
            # Ensure data_consent is set for auto-consent users
            if request.user.auto_data_consent:
                app.data_consent = True
            app.save()
            if draft_mode:
                messages.success(request, DRAFT_SAVED_MSG)
                return redirect('applications:my_applications')
            messages.success(request, "All steps complete. Review and submit.")
            return redirect('applications:preview', pk=application.pk)
    else:
        form = ApplicationStep5Form(instance=application, user=request.user)

    context = {
        'form': form,
        'application': application,
        'step': 5,
        'total_steps': 5,
        'auto_consent': request.user.auto_data_consent,
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
@require_POST
@transaction.atomic
def application_submit(request, pk):
    """Submit application"""
    application = get_object_or_404(
        Application,
        pk=pk,
        applicant=request.user,
        status='draft'
    )

    # Validate application is complete. We check the model fields directly
    # so a user who POSTs to /submit/ without walking the wizard still gets
    # bounced back to the first incomplete step instead of submitting a
    # half-filled draft.
    step_required_fields = [
        ('edit_step1', [
            'applicant_name', 'applicant_entity', 'applicant_email',
            'applicant_phone', 'project_name',
        ]),
        ('edit_step2', ['subject_area', 'brief_description']),
        ('edit_step3', ['service_modality', 'specialization_area']),
        ('edit_step4', [
            'scientific_relevance', 'methodology_description',
            'expected_contributions', 'impact_strengths',
            'socioeconomic_significance', 'opportunity_criteria',
        ]),
    ]
    for step_name, fields in step_required_fields:
        missing = [f for f in fields if not getattr(application, f, None)]
        if missing:
            messages.error(
                request,
                f"Please complete the following required fields: {', '.join(missing)}."
            )
            return redirect(f'applications:{step_name}', pk=application.pk)

    # Step 2 conditional: has_competitive_funding requires a funding agency
    if application.has_competitive_funding and not application.funding_agency_obj:
        messages.error(
            request,
            "Please select a funding agency for your competitive funding."
        )
        return redirect('applications:edit_step2', pk=application.pk)

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

    # Generate application code if not already set (resubmissions reuse the original code)
    if not application.code:
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

    # Compute the current set of nodes from requested equipment
    current_nodes = set()
    for access_request in application.requested_access.all():
        current_nodes.add(access_request.equipment.node)

    # Ensure a feasibility review exists for each current node
    # (handles both first submission and resubmission with potentially changed nodes)
    for node in current_nodes:
        coord = UserRole.objects.filter(
            node=node,
            role='node_coordinator',
            is_active=True
        ).select_related('user').first()

        if coord:
            FeasibilityReview.objects.get_or_create(
                application=application,
                node=node,
                defaults={'reviewer': coord.user}
            )

    # Reset all reviews to pending (covers both new reviews and any from a prior submission cycle)
    application.feasibility_reviews.update(
        status='pending', is_feasible=None, reviewed_at=None, comments=''
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


@login_required
@require_POST
def application_cancel(request, pk):
    """Cancel and delete a draft application."""
    application = get_object_or_404(
        Application,
        pk=pk,
        applicant=request.user,
        status='draft'
    )
    application.delete()  # Cascade deletes RequestedAccess etc.
    messages.success(request, "Application cancelled and deleted.")
    return redirect('applications:my_applications')


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
        status='pending'  # Pending review
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
@transaction.atomic
def feasibility_review(request, pk):
    """
    Review an application for feasibility.

    Node coordinators can approve, reject, or request edits.
    """
    review = get_object_or_404(
        FeasibilityReview,
        pk=pk,
        status='pending'
    )

    # Verify the current user is a coordinator for this node
    from core.models import UserRole
    if not UserRole.objects.filter(
        user=request.user,
        node=review.node,
        role='node_coordinator',
        is_active=True
    ).exists():
        raise Http404

    application = review.application

    # Get requested access for this node only
    requested_access = application.requested_access.filter(
        equipment__node=review.node
    ).select_related('equipment')

    if request.method == 'POST':
        form = FeasibilityReviewForm(request.POST, instance=review)

        if form.is_valid():
            review = form.save(commit=False)
            decision = form.cleaned_data['decision']
            review.status = decision
            review.reviewer = request.user
            review.reviewed_at = timezone.now()

            # Sync legacy field
            if decision == 'approved':
                review.is_feasible = True
            elif decision == 'rejected':
                review.is_feasible = False
            else:
                review.is_feasible = None

            review.save()

            if decision == 'edits_requested':
                # Return application to draft for editing.
                # Keep this review's status='edits_requested' and comments so the
                # applicant can see the feedback. Other reviews stay as-is.
                # On resubmission, application_submit will reset all reviews to pending.
                application.status = 'draft'
                application.submitted_at = None
                application.save()

                # Send edits-requested email
                try:
                    from communications.tasks import send_email_from_template
                    app_url = request.build_absolute_uri(
                        reverse('applications:detail', kwargs={'pk': application.pk})
                    )
                    applicant_email = application.applicant_email or application.applicant.email
                    send_email_from_template.delay(
                        template_type='feasibility_edits_requested',
                        recipient_email=applicant_email,
                        context_data={
                            'applicant_name': application.applicant.get_full_name(),
                            'application_code': application.code,
                            'node_name': review.node.name,
                            'reviewer_comments': review.comments,
                            'application_url': app_url,
                        },
                        recipient_user_id=application.applicant.id,
                        related_application_id=application.id
                    )
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Email notification failed: {e}")

                messages.success(
                    request,
                    f"Application {application.code} returned to applicant for edits."
                )
                return redirect('applications:feasibility_queue')

            # For approve/reject: check if all reviews are complete
            all_reviews = application.feasibility_reviews.all()
            pending_count = all_reviews.filter(status='pending').count()

            if pending_count == 0:
                rejected_count = all_reviews.filter(status='rejected').count()

                if rejected_count > 0:
                    application.status = 'rejected_feasibility'
                    application.save()
                    status_msg = "rejected"
                    is_approved = False
                else:
                    application.status = 'pending_evaluation'
                    application.save()
                    status_msg = "approved and ready for evaluation"
                    is_approved = True

                try:
                    from communications.tasks import send_email_from_template
                    applicant_email = application.applicant_email or application.applicant.email
                    send_email_from_template.delay(
                        template_type='feasibility_complete',
                        recipient_email=applicant_email,
                        context_data={
                            'applicant_name': application.applicant.get_full_name(),
                            'application_code': application.code,
                            'status': status_msg,
                            'is_approved': is_approved,
                        },
                        recipient_user_id=application.applicant.id,
                        related_application_id=application.id
                    )
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Email notification failed: {e}")

            messages.success(
                request,
                f"Feasibility review submitted for {application.code}. Decision: {review.get_status_display()}"
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

    # Check if already responded or wrong status. Both 'accepted' and
    # 'pending' (waitlist) let the applicant accept/decline; they differ
    # only in whether the handoff fires immediately (accepted) or waits
    # for a node coordinator to promote the app later (pending).
    is_waitlist = application.status == 'pending'
    if application.status not in ('accepted', 'pending'):
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
            # Record the applicant's acceptance. On the waitlist path the
            # handoff email is deferred until a node coordinator promotes
            # the application to accepted.
            application.accepted_by_applicant = True
            application.accepted_at = timezone.now()
            application.save()

            if is_waitlist:
                messages.success(request,
                    "You have accepted the waitlist offer. A node coordinator "
                    "will contact you if a slot becomes available."
                )
                return redirect('applications:detail', pk=application.pk)

            # Send handoff email to applicant + node coordinators. Acceptance
            # must succeed even if the email fails (missing template, SMTP
            # outage, etc.) — we log the failure and leave
            # handoff_email_sent_at unset so coordinators can retry.
            try:
                _send_handoff_email(application)
                application.handoff_email_sent_at = timezone.now()
                application.save(update_fields=['handoff_email_sent_at'])
                messages.success(request,
                    "You have accepted the access grant. Handoff email sent to node coordinators."
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).exception(
                    "Handoff email failed for application %s", application.code
                )
                messages.success(request,
                    "You have accepted the access grant. "
                    "The handoff email could not be sent automatically — a coordinator will follow up."
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
        'is_waitlist': is_waitlist,
    }
    return render(request, 'applications/acceptance_form.html', context)


@login_required
@require_POST
@transaction.atomic
def promote_waitlisted_application(request, pk):
    """Node coordinator promotes a waitlisted (pending) application into
    the accepted lifecycle.

    Requirements:
    - Application is in 'pending' status AND the applicant has already
      accepted the waitlist offer (accepted_by_applicant=True).
    - Caller is a coordinator / superuser, OR is a node_coordinator whose
      node has equipment on this application.

    Effect:
    - status: pending -> accepted
    - resolution: pending -> accepted
    - resolution_date refreshed to now; acceptance_deadline is cleared
      (applicant has already accepted — no second clock needed)
    - resolution_accepted notification + handoff email dispatched to
      applicant and node coordinators.
    """
    from core.models import UserRole

    application = get_object_or_404(Application, pk=pk)

    user = request.user
    user_roles = list(user.roles.filter(is_active=True).values_list('role', flat=True))
    is_coordinator = 'coordinator' in user_roles or user.is_superuser
    if not is_coordinator:
        requested_node_ids = set(
            application.requested_access.values_list('equipment__node_id', flat=True)
        )
        nc_node_ids = set(
            UserRole.objects.filter(
                user=user, role='node_coordinator', is_active=True,
            ).values_list('node_id', flat=True)
        )
        if not (requested_node_ids & nc_node_ids):
            messages.error(request, "You are not authorised to promote this application.")
            return redirect('access:access_tracking')

    if application.status != 'pending':
        messages.error(
            request,
            f"Cannot promote application {application.code}: status is "
            f"'{application.get_status_display()}', not Pending (Waitlist)."
        )
        return redirect('applications:detail', pk=application.pk)

    if not application.accepted_by_applicant:
        messages.error(
            request,
            f"Cannot promote {application.code}: the applicant has not yet "
            "accepted the waitlist offer."
        )
        return redirect('applications:detail', pk=application.pk)

    application.status = 'accepted'
    application.resolution = 'accepted'
    application.resolution_date = timezone.now()
    application.resolution_comments = (
        (application.resolution_comments or '')
        + f"\n\n[PROMOTED FROM WAITLIST] by {user.get_full_name() or user.email} "
          f"on {timezone.now().date()}"
    ).strip()
    application.acceptance_deadline = None  # applicant has already accepted
    application.save()

    # Fire the handoff email only — the applicant already received and
    # accepted the original resolution_pending notification, so resending
    # a resolution email on promotion is unnecessary and confusing.
    import logging
    log = logging.getLogger(__name__)
    try:
        _send_handoff_email(application)
        application.handoff_email_sent_at = timezone.now()
        application.save(update_fields=['handoff_email_sent_at'])
    except Exception:
        log.exception("Handoff email failed on promotion of %s", application.code)

    messages.success(
        request,
        f"Application {application.code} has been promoted from the waitlist. "
        "The applicant and node coordinators have been notified."
    )
    return redirect('applications:detail', pk=application.pk)


def _send_handoff_email(application):
    """Helper function to send handoff email to applicant and node coordinators."""
    from communications.tasks import send_email_from_template
    from core.models import UserRole

    # Get all nodes involved
    nodes = set()
    requested_access_list = []
    for req_access in application.requested_access.select_related('equipment__node'):
        nodes.add(req_access.equipment.node)
        hours_approved = req_access.hours_approved
        requested_access_list.append({
            'node_name': req_access.equipment.node.name,
            'equipment_name': req_access.equipment.name,
            'hours_requested': float(req_access.hours_requested),
            'hours_approved': float(hours_approved) if hours_approved is not None else None,
        })

    # Build email context
    context = {
        'applicant_name': application.applicant.get_full_name(),
        'applicant_entity': application.applicant_entity,
        'applicant_email': application.applicant.email,
        'applicant_phone': application.applicant_phone or 'Not provided',
        'application_code': application.code,
        'project_name': application.project_name,
        'brief_description': application.brief_description,
        'service_modality': application.get_service_modality_display() if application.service_modality else 'Not specified',
        'node_names': ', '.join([n.name for n in nodes]),
        'requested_access': requested_access_list,
    }

    # Collect all node coordinator emails across the involved nodes.
    # These go in CC (along with the applicant in To) so every recipient
    # sees the others' addresses and can Reply All to coordinate scheduling.
    cc_emails = []
    seen_emails = set()
    for node in nodes:
        node_coordinators = UserRole.objects.filter(
            node=node,
            role='node_coordinator',
            is_active=True
        ).select_related('user')
        for user_role in node_coordinators:
            email = user_role.user.email
            if email and email not in seen_emails:
                seen_emails.add(email)
                cc_emails.append(email)

    # Prefer the form-declared applicant_email (the stated PI contact) over
    # the submitting User's account email.
    recipient_email = application.applicant_email or application.applicant.email

    send_email_from_template(
        template_type='handoff_notification',
        recipient_email=recipient_email,
        context_data=context,
        recipient_user_id=application.applicant.id,
        related_application_id=application.id,
        cc_emails=cc_emails,
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
    from applications.forms import NodeResolutionForm
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
            has_competitive_funding=application.has_competitive_funding,
            has_evaluator_denial=application.has_any_denied_evaluation,
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
            # Surface form errors as a top-of-page banner so node coordinators
            # don't miss the inline errors buried further down the page.
            messages.error(
                request,
                "Your resolution was NOT submitted. Please correct the errors highlighted below and try again."
            )
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
            has_competitive_funding=application.has_competitive_funding,
            has_evaluator_denial=application.has_any_denied_evaluation,
        )

    # Prepare equipment data for template
    # node_equipment = the QuerySet for display
    # equipment_forms = structured data for form inputs
    equipment_forms = []
    for ra in requested_access:
        equipment_forms.append({
            'equipment_name': ra.equipment.name,
            'equipment_id': ra.equipment.id,
            'hours_requested': ra.hours_requested,
            'hours_approved': ra.hours_approved or ra.hours_requested,
        })

    # Get evaluations for display
    evaluations = application.evaluations.select_related('evaluator').all()

    # Get other nodes' resolutions (for multi-node visibility)
    other_node_resolutions = application.node_resolutions.exclude(
        node=node
    ).filter(
        resolution__in=['accept', 'waitlist', 'reject']
    ).select_related('node')

    context = {
        'form': form,
        'application': application,
        'node': node,
        'node_equipment': requested_access,  # QuerySet for display
        'equipment_forms': equipment_forms,  # List of dicts for form
        'evaluations': evaluations,
        'existing_resolution': existing_resolution,
        'other_node_resolutions': other_node_resolutions,
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
def node_confirm_equipment_done(request, application_id, requested_access_id):
    """
    Node coordinator marks equipment as completed.

    Can override actual hours if needed. The application_id in the URL is
    ignored (the application is derived from req_access.application) but
    must be present so the URL pattern resolves.
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


# =============================================================================
# PDF Signature Upload Views
# =============================================================================

@login_required
def download_application_pdf(request, pk):
    """
    Generate and download the application PDF.

    Permission scope mirrors what each role can already see in the portal:
    - Applicant: their own application (full content; bumps pdf_generated_at).
    - ReDIB coordinator / superuser: any application (full content).
    - Node coordinator: any application requesting equipment at one of
      their nodes (full content).
    - Evaluator: any application they're assigned to evaluate
      (BLIND PDF — applicant-identity sections suppressed to match the
      blind portal view in `evaluations.utils.get_blind_application_data`).

    Anyone outside those scopes gets a 404.
    """
    from django.http import HttpResponse
    from django.template.loader import render_to_string
    from weasyprint import HTML
    from core.models import UserRole
    import logging

    logger = logging.getLogger(__name__)

    application = get_object_or_404(Application, pk=pk)
    user = request.user

    user_roles = list(user.roles.filter(is_active=True).values_list('role', flat=True))
    is_coordinator = 'coordinator' in user_roles or user.is_superuser
    is_applicant = (application.applicant_id == user.id)

    is_node_coordinator = False
    if not (is_coordinator or is_applicant):
        requested_node_ids = set(
            application.requested_access.values_list('equipment__node_id', flat=True)
        )
        nc_node_ids = set(
            UserRole.objects.filter(
                user=user,
                role='node_coordinator',
                is_active=True,
            ).values_list('node_id', flat=True)
        )
        is_node_coordinator = bool(requested_node_ids & nc_node_ids)

    is_assigned_evaluator = False
    if not (is_coordinator or is_applicant or is_node_coordinator):
        is_assigned_evaluator = application.evaluations.filter(evaluator=user).exists()

    if not (is_coordinator or is_applicant or is_node_coordinator or is_assigned_evaluator):
        raise Http404("Application not found.")

    # Evaluators get the blind PDF unless they also hold a privileged role
    # on this application (in which case the privileged view wins).
    blind = is_assigned_evaluator and not (
        is_coordinator or is_applicant or is_node_coordinator
    )

    requested_access = application.requested_access.select_related(
        'equipment__node'
    ).order_by('equipment__node__code')

    html_string = render_to_string('applications/application_pdf.html', {
        'application': application,
        'requested_access': requested_access,
        'generated_at': timezone.now(),
        'blind': blind,
    })

    try:
        html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
        pdf_content = html.write_pdf()
    except Exception as e:
        logger.error(f"PDF generation failed for application {application.code}: {e}")
        messages.error(request, "Failed to generate PDF. Please try again or contact support.")
        return redirect('applications:detail', pk=pk)

    # pdf_generated_at is the applicant-side "I have a copy of my submission"
    # timestamp; reviewer downloads should not move it.
    if is_applicant:
        application.pdf_generated_at = timezone.now()
        application.save(update_fields=['pdf_generated_at'])

    response = HttpResponse(pdf_content, content_type='application/pdf')
    filename_suffix = '_blind' if blind else ''
    filename = f"{application.code}_application{filename_suffix}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


@login_required
def upload_signed_pdf(request, pk):
    """Legacy URL — redirect to preview page. PDF signature is no longer required."""
    return redirect('applications:preview', pk=pk)
