"""
Views for the calls app.
"""
import logging

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils import timezone
from django.db.models import Sum, Count, Q
from core.decorators import coordinator_required, role_required
from .models import Call, CallEquipmentAllocation, ConsultRequest
from .forms import (
    CallForm,
    CallEquipmentFormSet,
    ConsultRequestForm,
    get_equipment_formset_for_create,
)
from .services import (
    build_call_url,
    notify_call_audience,
    open_announced_calls,
    send_consult_confirmation_email,
    send_consult_request_emails,
)

logger = logging.getLogger(__name__)

# Anti-spam limits for the public consult form (cache-backed, no captcha).
CONSULT_MAX_PER_IP_PER_HOUR = 5
CONSULT_DUPLICATE_WINDOW_SECONDS = 600


# Public Views

def _auto_close_expired_calls():
    """
    View-level fallback: close any open calls past their submission deadline.

    This ensures correct behavior even if Celery Beat is not running.
    """
    now = timezone.now()
    expired = Call.objects.filter(status__in=['open', 'announced'], submission_end__lt=now)
    count = expired.count()
    if count > 0:
        expired.update(status='closed')
    return count


def _auto_open_announced_calls(request):
    """
    View-level fallback: open announced calls whose start date has arrived.

    Celery Beat does this daily; this keeps the public pages correct in
    between (and when Beat isn't running at all). The "Now Open" email is
    attempted here too, but a dead broker only logs a warning — the status
    change is what matters and the beat task will not re-send, because the
    call is no longer `announced`.
    """
    codes, _ = open_announced_calls(request=request)
    return len(codes)


def public_call_list(request):
    """
    Public list of open and upcoming calls.

    Shows:
    - Currently open calls (status='open', within submission window)
    - Upcoming calls (status='announced' — advertised, not yet accepting)
    """
    _auto_open_announced_calls(request)
    _auto_close_expired_calls()

    now = timezone.now()

    open_calls = Call.objects.filter(
        status='open',
        submission_start__lte=now,
        submission_end__gte=now
    ).prefetch_related('equipment_allocations__equipment__node').order_by('-submission_start')

    upcoming_calls = Call.objects.filter(
        status='announced'
    ).prefetch_related(
        'equipment_allocations__equipment__node'
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
    Announced calls get an "opens on" callout instead of Apply; drafts stay
    invisible.
    """
    _auto_open_announced_calls(request)
    _auto_close_expired_calls()

    call = get_object_or_404(Call, pk=pk, status__in=Call.PUBLIC_STATUSES)

    equipment_allocations = call.equipment_allocations.select_related(
        'equipment__node__organization'
    ).order_by('equipment__node__code', 'equipment__name')

    context = {
        'call': call,
        'equipment_allocations': equipment_allocations,
        'can_apply': call.is_open and request.user.is_authenticated,
        'can_request_consult': call.accepts_consult_requests,
    }
    return render(request, 'calls/public_detail.html', context)


# Public consult requests (no login required)

def _client_ip(request):
    """Best-effort client IP.

    Behind Caddy the real peer is the *last* entry of X-Forwarded-For (Caddy
    appends the connecting address), so a client-supplied header can't be
    used to dodge the rate limit.
    """
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[-1].strip()
    return request.META.get('REMOTE_ADDR', '')


def _cache_get(key, default=None):
    """cache.get that fails open: the cache is Redis in prod (shared with the
    Celery broker); if it is down the consult form must still work."""
    try:
        return cache.get(key, default)
    except Exception:
        logger.warning("Consult rate-limit cache unavailable (get %s)", key)
        return default


def _cache_set(key, value, timeout):
    try:
        cache.set(key, value, timeout)
    except Exception:
        logger.warning("Consult rate-limit cache unavailable (set %s)", key)


def _consult_ip_throttled(ip_hash):
    """True when this IP has already submitted its hourly allowance."""
    if not ip_hash:
        return False
    key = f'consult_rl:ip:{ip_hash}'
    return (_cache_get(key) or 0) >= CONSULT_MAX_PER_IP_PER_HOUR


def _consult_record_submission(ip_hash):
    """Count one submission against the hourly allowance for this IP."""
    key = f'consult_rl:ip:{ip_hash}'
    count = _cache_get(key) or 0
    _cache_set(key, count + 1, 3600)


def _consult_duplicate_key(ip_hash, call, equipment_ids):
    signature = '-'.join(str(pk) for pk in sorted(equipment_ids))
    return f'consult_rl:dup:{ip_hash}:{call.pk}:{signature}'


def public_consult_request(request, pk):
    """
    Public "request a consult" form for equipment on an announced/open call.

    No login required. Creates a ConsultRequest row (the source of truth) and
    emails every active node coordinator of each node involved, plus a
    confirmation to the requester.
    """
    call = get_object_or_404(Call, pk=pk, status__in=Call.PUBLIC_STATUSES)

    if not call.accepts_consult_requests:
        messages.info(
            request,
            f"Call {call.code} is no longer accepting consult requests. "
            f"Please contact {settings.CONTACT_EMAIL} if you have questions."
        )
        return redirect('calls:public_detail', pk=call.pk)

    ip_hash = ConsultRequest.hash_ip(_client_ip(request))

    if request.method == 'POST':
        form = ConsultRequestForm(request.POST, call=call)

        if _consult_ip_throttled(ip_hash):
            messages.error(
                request,
                "You have sent several consult requests recently. Please wait a "
                f"little before sending another, or email {settings.CONTACT_EMAIL} "
                "directly."
            )
        elif form.is_valid():
            equipment = form.cleaned_data['equipment']
            duplicate_key = _consult_duplicate_key(ip_hash, call, [e.pk for e in equipment])

            if ip_hash and _cache_get(duplicate_key):
                messages.warning(
                    request,
                    "We already have that request — the node coordinator(s) have "
                    "been notified and will get back to you."
                )
                return redirect('calls:public_consult_thanks', pk=call.pk)

            consult = form.save(commit=False)
            consult.call = call
            consult.ip_hash = ip_hash
            if request.user.is_authenticated:
                consult.user = request.user
            consult.save()
            consult.equipment.set(equipment)

            call_url = build_call_url(call, request)
            consult_requests_url = request.build_absolute_uri(
                reverse('calls:consult_requests', kwargs={'pk': call.pk})
            )
            try:
                sent, no_coord_nodes = send_consult_request_emails(
                    consult, call_url, consult_requests_url
                )
                confirmed = send_consult_confirmation_email(consult, call_url)
                # Only stamp when something actually went out, so the
                # coordinator list can flag requests nobody was told about.
                if sent or confirmed:
                    consult.emails_sent_at = timezone.now()
                    consult.save(update_fields=['emails_sent_at'])
            except Exception:
                logger.exception(
                    "Consult request %s: email dispatch failed (Celery unavailable?)",
                    consult.pk,
                )
                no_coord_nodes = []

            if no_coord_nodes:
                messages.warning(
                    request,
                    "We have recorded your request, but "
                    + ", ".join(node.name for node in no_coord_nodes)
                    + " has no coordinator on file right now, so the ReDIB office "
                    "has been notified instead. If you would like to follow up, "
                    f"write to {settings.CONTACT_EMAIL}."
                )

            if ip_hash:
                _cache_set(duplicate_key, True, CONSULT_DUPLICATE_WINDOW_SECONDS)
                _consult_record_submission(ip_hash)

            request.session['consult_request_id'] = consult.pk
            return redirect('calls:public_consult_thanks', pk=call.pk)
    else:
        initial = {}
        preselected = request.GET.getlist('equipment')
        if preselected:
            initial['equipment'] = preselected
        if request.user.is_authenticated:
            initial.update({
                'name': f"{request.user.first_name} {request.user.last_name}".strip(),
                'email': request.user.email,
                'phone': request.user.phone,
                'organization': (
                    request.user.organization.name if request.user.organization_id else ''
                ),
            })
        form = ConsultRequestForm(initial=initial, call=call)

    context = {
        'call': call,
        'form': form,
    }
    return render(request, 'calls/consult_request.html', context)


def public_consult_thanks(request, pk):
    """Confirmation page after a consult request is submitted."""
    call = get_object_or_404(Call, pk=pk, status__in=Call.PUBLIC_STATUSES)

    consult = None
    consult_id = request.session.pop('consult_request_id', None)
    if consult_id:
        consult = ConsultRequest.objects.filter(pk=consult_id, call=call).first()

    context = {
        'call': call,
        'consult': consult,
        'nodes': list(consult.equipment_by_node()) if consult else [],
        'contact_email': settings.CONTACT_EMAIL,
    }
    return render(request, 'calls/consult_thanks.html', context)


# Coordinator Views

@coordinator_required
def coordinator_dashboard(request):
    """
    Coordinator dashboard for managing calls.

    Shows all calls with application counts and status.
    Only counts submitted applications (excludes drafts).
    """
    calls = Call.objects.all().annotate(
        application_count=Count('applications', filter=~Q(applications__status='draft'))
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

    # Hide never-submitted drafts, but keep drafts that have coordinator-
    # visible state: either a feasibility review (bounced back for edits)
    # or a pre-submission consult request.
    applications = call.applications.exclude(
        Q(status='draft')
        & Q(feasibility_reviews__isnull=True)
        & Q(consult_requested_at__isnull=True)
    ).select_related('applicant').distinct().order_by('-submitted_at')

    consult_requests = call.consult_requests.prefetch_related(
        'equipment__node__organization'
    ).select_related('user')

    context = {
        'call': call,
        'equipment_allocations': equipment_allocations,
        'applications': applications,
        'consult_requests': consult_requests,
    }
    return render(request, 'calls/detail.html', context)


@coordinator_required
def call_announce(request, pk):
    """
    Announce a call ahead of its submission window.

    The call becomes publicly visible under "Upcoming Calls" but takes no
    applications; it opens automatically on `submission_start`, which is when
    the "Now Open" email goes out.
    """
    call = get_object_or_404(Call, pk=pk)

    if call.status != 'draft':
        messages.error(
            request,
            f"Only draft calls can be announced. {call.code} is "
            f"{call.get_status_display()}."
        )
        return redirect('calls:detail', pk=call.pk)

    if not call.equipment_allocations.exists():
        messages.error(request, "Cannot announce call without equipment allocations.")
        return redirect('calls:call_edit', pk=call.pk)

    if call.submission_start <= timezone.now():
        messages.error(
            request,
            "The submission period has already started, so there is nothing to "
            "announce. Use Publish to open this call now."
        )
        return redirect('calls:detail', pk=call.pk)

    call.status = 'announced'
    call.published_at = timezone.now()
    call.save()

    # Send notification emails (async) - gracefully handle Celery unavailability
    try:
        count = notify_call_audience(
            call, 'call_announced', build_call_url(call, request)
        )
        email_status = f"Announcement emails queued for {count} users."
    except Exception as e:
        logger.warning(f"Email notification failed (Celery unavailable): {e}")
        email_status = "(Email notifications disabled - Celery not running)"

    messages.success(
        request,
        f"Call {call.code} announced. It is now listed publicly as upcoming and "
        f"will open automatically on {call.submission_start:%B %d, %Y}. "
        f"{email_status}"
    )
    return redirect('calls:detail', pk=call.pk)


@coordinator_required
def call_publish(request, pk):
    """
    Publish a call — open it for submissions now.

    Makes the call visible and sends notification emails to users.
    Validates that call has equipment allocations. Refuses calls whose
    submission window has not started yet: those should be announced, and
    they open by themselves on `submission_start`.
    """
    call = get_object_or_404(Call, pk=pk)

    if call.status not in ['draft', 'announced']:
        messages.error(
            request,
            f"Call {call.code} is {call.get_status_display()} and cannot be published."
        )
        return redirect('calls:detail', pk=call.pk)

    # Validation: must have equipment allocations
    if not call.equipment_allocations.exists():
        messages.error(request, "Cannot publish call without equipment allocations.")
        return redirect('calls:call_edit', pk=call.pk)

    if call.submission_start > timezone.now():
        messages.error(
            request,
            f"Call {call.code} does not open until "
            f"{call.submission_start:%B %d, %Y}. Use Announce to advertise it now — "
            "it opens automatically on that date."
        )
        return redirect('calls:detail', pk=call.pk)

    # Update call status
    call.status = 'open'
    call.published_at = timezone.now()
    call.save()

    # Send notification emails (async) - gracefully handle Celery unavailability
    try:
        count = notify_call_audience(
            call, 'call_published', build_call_url(call, request)
        )
        email_status = f"Notification emails queued for {count} users."
    except Exception as e:
        # Celery/Redis not available - log and continue
        logger.warning(f"Email notification failed (Celery unavailable): {e}")
        email_status = "(Email notifications disabled - Celery not running)"

    messages.success(
        request,
        f"Call {call.code} published successfully. {email_status}"
    )
    return redirect('calls:detail', pk=call.pk)


@role_required('coordinator', 'node_coordinator')
def consult_requests(request, pk):
    """
    Consult requests received for a call.

    ReDIB coordinators see every request; node coordinators see only the
    requests that involve equipment at one of their nodes (and only the
    only requests touching those nodes are listed).
    """
    call = get_object_or_404(Call, pk=pk)

    requests_qs = call.consult_requests.prefetch_related(
        'equipment__node__organization'
    ).select_related('user')

    is_redib_coordinator = (
        request.user.is_superuser
        or request.user.roles.filter(role='coordinator', is_active=True).exists()
    )
    my_node_ids = []
    if not is_redib_coordinator:
        my_node_ids = list(
            request.user.roles.filter(
                role='node_coordinator', is_active=True, node__isnull=False
            ).values_list('node_id', flat=True)
        )
        requests_qs = requests_qs.filter(
            equipment__node_id__in=my_node_ids
        ).distinct()

    context = {
        'call': call,
        'consult_requests': requests_qs,
        'is_redib_coordinator': is_redib_coordinator,
    }
    return render(request, 'calls/consult_requests.html', context)


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
