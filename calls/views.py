"""
Views for the calls app.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Count
from core.decorators import coordinator_required
from .models import Call, CallEquipmentAllocation
from .forms import CallForm, CallEquipmentFormSet, get_equipment_formset_for_create


# Public Views

def public_call_list(request):
    """
    Public list of open and upcoming calls.

    Shows:
    - Currently open calls (status='open', within submission window)
    - Upcoming calls (published but not yet open)
    """
    now = timezone.now()

    open_calls = Call.objects.filter(
        status='open',
        submission_start__lte=now,
        submission_end__gte=now
    ).prefetch_related('equipment_allocations__equipment__node').order_by('-submission_start')

    upcoming_calls = Call.objects.filter(
        status='open',
        submission_start__gt=now
    ).order_by('submission_start')

    context = {
        'open_calls': open_calls,
        'upcoming_calls': upcoming_calls,
    }
    return render(request, 'calls/public_list.html', context)


def public_call_detail(request, pk):
    """
    Public detail view of a call.

    Shows call information, equipment allocations, and application button.
    Only shows calls that are open, closed, or resolved (not drafts).
    """
    call = get_object_or_404(Call, pk=pk, status__in=['open', 'closed', 'resolved'])

    equipment_allocations = call.equipment_allocations.select_related(
        'equipment__node'
    ).order_by('equipment__node__code', 'equipment__name')

    context = {
        'call': call,
        'equipment_allocations': equipment_allocations,
        'can_apply': call.is_open and request.user.is_authenticated,
    }
    return render(request, 'calls/public_detail.html', context)


# Coordinator Views

@coordinator_required
def coordinator_dashboard(request):
    """
    Coordinator dashboard for managing calls.

    Shows all calls with application counts and status.
    """
    calls = Call.objects.all().annotate(
        application_count=Count('applications')
    ).order_by('-created_at')

    context = {
        'calls': calls,
    }
    return render(request, 'calls/coordinator_dashboard.html', context)


@coordinator_required
def call_create(request):
    """Create a new call."""
    from core.models import Equipment

    # Always get active equipment for display
    active_equipment = Equipment.objects.filter(is_active=True).select_related('node').order_by('node__code', 'name')
    equipment_count = active_equipment.count()

    # Get the formset factory with correct number of extra forms
    EquipmentFormSet = get_equipment_formset_for_create(equipment_count)

    if request.method == 'POST':
        form = CallForm(request.POST)
        formset = EquipmentFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            call = form.save()
            formset.instance = call
            formset.save()

            messages.success(request, f"Call {call.code} created successfully.")
            return redirect('calls:call_edit', pk=call.pk)

        # On validation error, pair equipment with formset forms
        equipment_forms = list(zip(active_equipment, formset.forms))
    else:
        form = CallForm()

        # Create initial data for the formset - one entry per equipment
        initial_data = [{'equipment': eq.id} for eq in active_equipment]
        formset = EquipmentFormSet(initial=initial_data)

        # Pair equipment objects with formset forms for template display
        equipment_forms = list(zip(active_equipment, formset.forms))

    context = {
        'form': form,
        'formset': formset,
        'equipment_forms': equipment_forms,
        'is_create': True,
    }
    return render(request, 'calls/call_form.html', context)


@coordinator_required
def call_edit(request, pk):
    """Edit an existing call."""
    call = get_object_or_404(Call, pk=pk)

    if request.method == 'POST':
        form = CallForm(request.POST, instance=call)
        formset = CallEquipmentFormSet(request.POST, instance=call)

        if form.is_valid() and formset.is_valid():
            call = form.save()
            formset.save()

            messages.success(request, f"Call {call.code} updated successfully.")
            return redirect('calls:detail', pk=call.pk)
    else:
        form = CallForm(instance=call)
        formset = CallEquipmentFormSet(instance=call)

    context = {
        'form': form,
        'formset': formset,
        'call': call,
        'is_create': False,
    }
    return render(request, 'calls/call_form.html', context)


@coordinator_required
def call_detail(request, pk):
    """
    Coordinator view of call with management options.

    Shows call details, equipment allocations, and applications.
    Includes actions to publish, close, etc.
    """
    call = get_object_or_404(Call, pk=pk)

    equipment_allocations = call.equipment_allocations.select_related(
        'equipment__node'
    ).order_by('equipment__node__code')

    applications = call.applications.exclude(status='draft').select_related(
        'applicant'
    ).order_by('-submitted_at')

    context = {
        'call': call,
        'equipment_allocations': equipment_allocations,
        'applications': applications,
    }
    return render(request, 'calls/detail.html', context)


@coordinator_required
def call_publish(request, pk):
    """
    Publish a call.

    Makes the call visible and sends notification emails to users.
    Validates that call has equipment allocations.
    """
    call = get_object_or_404(Call, pk=pk)

    # Validation: must have equipment allocations
    if not call.equipment_allocations.exists():
        messages.error(request, "Cannot publish call without equipment allocations.")
        return redirect('calls:call_edit', pk=call.pk)

    # Update call status
    call.status = 'open'
    call.published_at = timezone.now()
    call.save()

    # Send notification emails (async) - gracefully handle Celery unavailability
    try:
        from communications.tasks import send_email_from_template
        from core.models import User

        # Get all users who want call notifications
        recipients = User.objects.filter(
            receive_call_notifications=True
        ).values_list('email', 'id')

        # Queue email for each recipient
        for email, user_id in recipients:
            context_data = {
                'call_code': call.code,
                'call_title': call.title,
                'submission_end': call.submission_end,
                'call_url': request.build_absolute_uri(f'/calls/{call.pk}/'),
            }

            send_email_from_template.delay(
                template_type='call_published',
                recipient_email=email,
                context_data=context_data,
                recipient_user_id=user_id
            )
        email_status = f"Notification emails queued for {recipients.count()} users."
    except Exception as e:
        # Celery/Redis not available - log and continue
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Email notification failed (Celery unavailable): {e}")
        email_status = "(Email notifications disabled - Celery not running)"

    messages.success(
        request,
        f"Call {call.code} published successfully. {email_status}"
    )
    return redirect('calls:detail', pk=call.pk)


@coordinator_required
def call_close(request, pk):
    """
    Close call for submissions.

    Changes status to 'closed', preventing new applications.
    Ready for evaluator assignment.
    """
    call = get_object_or_404(Call, pk=pk)

    call.status = 'closed'
    call.save()

    messages.success(request, f"Call {call.code} closed for submissions. Ready for evaluator assignment.")
    return redirect('calls:detail', pk=call.pk)


@coordinator_required
def call_delete(request, pk):
    """
    Delete a draft call.

    Only allows deletion of draft calls (not published).
    Permanently removes the call and all associated equipment allocations.
    """
    call = get_object_or_404(Call, pk=pk)

    # Only allow deletion of draft calls
    if call.status != 'draft':
        messages.error(request, f"Cannot delete call {call.code}. Only draft calls can be deleted.")
        return redirect('calls:detail', pk=call.pk)

    # Check if call has any applications
    if call.applications.exists():
        messages.error(
            request,
            f"Cannot delete call {call.code}. It has {call.applications.count()} associated application(s)."
        )
        return redirect('calls:detail', pk=call.pk)

    # Store call code for message before deletion
    call_code = call.code

    # Delete the call (CASCADE will delete CallEquipmentAllocations)
    call.delete()

    messages.success(request, f"Call {call_code} has been permanently deleted.")
    return redirect('calls:coordinator_dashboard')
