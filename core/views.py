"""
Core application views.
"""
import markdown
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.safestring import mark_safe

# Source of truth for the end-user guide. Rendered to HTML at request time by
# `user_guide` below so the markdown in docs/ stays the only copy.
USER_GUIDE_PATH = settings.BASE_DIR / 'docs' / 'USER_GUIDE.md'

# Rendered-guide cache, keyed by the source file's mtime. In production the
# file never changes within a container's lifetime, so this renders once per
# process; in dev, editing the markdown invalidates it on the next request.
_user_guide_cache = {}


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

    # Add role flags to context for template
    context['is_applicant'] = 'applicant' in user_roles
    context['is_node_coordinator'] = 'node_coordinator' in user_roles
    context['is_evaluator'] = 'evaluator' in user_roles
    context['is_coordinator'] = 'coordinator' in user_roles or user.is_superuser

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
        from applications.services import NodeResolutionService
        from core.models import UserRole, Node

        # Get nodes this user coordinates
        my_node_roles = UserRole.objects.filter(
            user=user, role='node_coordinator', is_active=True
        ).select_related('node')
        my_nodes = [role.node_id for role in my_node_roles]

        context['pending_feasibility'] = FeasibilityReview.objects.filter(
            node_id__in=my_nodes,
            status='pending'
        ).select_related('application', 'node').order_by('created_at')[:10]

        context['feasibility_count'] = FeasibilityReview.objects.filter(
            node_id__in=my_nodes,
            status='pending'
        ).count()

        # Get pending resolutions for node coordinators
        pending_resolution_items = []
        resolution_count = 0
        for role in my_node_roles:
            service = NodeResolutionService(node=role.node)
            pending_apps = service.get_applications_for_node_resolution()
            for app in pending_apps[:5]:  # Limit per node
                pending_resolution_items.append({
                    'application': app,
                    'node': role.node
                })
            resolution_count += pending_apps.count()

        # Sort by final_score descending and limit total
        pending_resolution_items.sort(
            key=lambda x: -(x['application'].final_score or 0)
        )
        context['pending_resolutions'] = pending_resolution_items[:10]
        context['resolution_count'] = resolution_count

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


@login_required
def profile(request):
    """User profile view - display and edit personal information."""
    from .forms import ProfileForm

    user = request.user

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            form.save_evaluator_areas()
            messages.success(request, 'Profile updated successfully.')
            return redirect('core:dashboard')
    else:
        form = ProfileForm(instance=user)

    # Get user roles for display
    user_roles = user.roles.filter(is_active=True).select_related('node')

    context = {
        'form': form,
        'user_roles': user_roles,
        'profile_incomplete': not user.is_profile_complete,
    }
    return render(request, 'core/profile.html', context)


def _render_user_guide():
    """
    Render docs/USER_GUIDE.md, caching the result against the file's mtime.

    Returns a dict with `html` (the guide body), `toc` (Python-Markdown's
    nested `<div class="toc">` list) and `title` (the markdown's H1).
    """
    mtime = USER_GUIDE_PATH.stat().st_mtime

    if _user_guide_cache.get('mtime') != mtime:
        text = USER_GUIDE_PATH.read_text(encoding='utf-8')
        md = markdown.Markdown(
            extensions=['tables', 'toc', 'fenced_code', 'sane_lists'],
            # Sidebar TOC stays navigable: h2/h3 only. All headings, h4
            # included, still get an id so in-page anchors keep working.
            extension_configs={'toc': {'toc_depth': '2-3'}},
        )
        html = md.convert(text)

        # The markdown's H1 renders in the body; reuse its text for <title>.
        # Skip over the leading HTML comment that heads the file.
        title = 'User Guide'
        for line in text.splitlines():
            if line.startswith('# '):
                title = line[2:].strip()
                break

        _user_guide_cache.update({
            'mtime': mtime,
            'html': mark_safe(html),
            'toc': mark_safe(md.toc),
            'title': title,
        })

    return _user_guide_cache


def user_guide(request):
    """
    Public end-user guide, rendered from docs/USER_GUIDE.md at request time.

    Deliberately not `login_required`: the guide it replaced was a public
    static PDF, and first-time evaluators are pointed at it before they have
    an account. `/help/` is exempt from ProfileCompletionMiddleware so users
    with an incomplete profile can still read it.
    """
    guide = _render_user_guide()

    context = {
        'guide_html': guide['html'],
        'guide_toc': guide['toc'],
        'guide_title': guide['title'],
    }
    return render(request, 'help/user_guide.html', context)
