"""
Views for the applications app - 5-step application wizard.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from calls.models import Call
from .models import Application, RequestedAccess, FeasibilityReview
from .forms import (
    ApplicationStep1Form, ApplicationStep2Form, ApplicationStep3Form,
    ApplicationStep4Form, ApplicationStep5Form, RequestedAccessFormSet
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
        form = ApplicationStep1Form(request.POST)

        if form.is_valid():
            application = form.save(commit=False)
            application.call = call
            application.applicant = request.user
            application.status = 'draft'
            application.save()

            messages.success(request, "Application draft created. Continue to step 2.")
            return redirect('applications:edit_step2', pk=application.pk)
    else:
        form = ApplicationStep1Form()

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

    # Send confirmation email
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

    messages.success(
        request,
        f"Application {application.code} submitted successfully! You will receive confirmation by email."
    )
    return redirect('applications:detail', pk=application.pk)
