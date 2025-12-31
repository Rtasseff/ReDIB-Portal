"""
Views for reports app - Phase 10: Reporting & Statistics.
"""

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.db.models import Count, Avg, Sum, Q
from tempfile import NamedTemporaryFile

from core.decorators import coordinator_required
from calls.models import Call
from applications.models import Application
from access.models import Publication
from evaluations.models import Evaluation
from .models import ReportGeneration
from .utils import generate_call_report_excel


@coordinator_required
def statistics_dashboard(request):
    """
    Main statistics dashboard for coordinators.
    Shows overall system stats and current call metrics.
    """
    # Overall statistics
    total_calls = Call.objects.count()
    total_applications = Application.objects.count()
    total_publications = Publication.objects.count()

    # Status breakdown
    status_breakdown = Application.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')

    # Current call (most recent open or closed)
    current_call = Call.objects.filter(
        status__in=['open', 'closed']
    ).order_by('-submission_start').first()

    current_call_stats = None
    if current_call:
        apps = Application.objects.filter(call=current_call)
        total_apps = apps.count()

        current_call_stats = {
            'call': current_call,
            'total_apps': total_apps,
            'by_status': apps.values('status').annotate(count=Count('id')),
            'avg_score': apps.aggregate(avg=Avg('final_score'))['avg'],
            'acceptance_rate': (apps.filter(resolution='accepted').count() / total_apps * 100) if total_apps > 0 else 0,
        }

    # Recent activity
    recent_apps = Application.objects.select_related(
        'call', 'applicant'
    ).order_by('-submitted_at')[:10]

    pending_evaluations = Evaluation.objects.filter(
        completed_at__isnull=True
    ).count()

    # Publication statistics
    pub_stats = {
        'total': total_publications,
        'acknowledged': Publication.objects.filter(redib_acknowledged=True).count(),
        'ack_rate': (Publication.objects.filter(redib_acknowledged=True).count() / total_publications * 100) if total_publications > 0 else 0,
    }

    # Recent publications
    recent_publications = Publication.objects.select_related(
        'application', 'application__call', 'reported_by'
    ).order_by('-reported_at')[:5]

    context = {
        'total_calls': total_calls,
        'total_applications': total_applications,
        'total_publications': total_publications,
        'status_breakdown': status_breakdown,
        'current_call_stats': current_call_stats,
        'recent_apps': recent_apps,
        'pending_evaluations': pending_evaluations,
        'pub_stats': pub_stats,
        'recent_publications': recent_publications,
    }

    return render(request, 'reports/statistics_dashboard.html', context)


@coordinator_required
def export_call_report(request, call_id):
    """
    Export call summary report as Excel file.
    Generates 3-sheet workbook with call statistics.
    """
    call = get_object_or_404(Call, pk=call_id)

    # Generate Excel file
    wb = generate_call_report_excel(call)

    # Save to response using NamedTemporaryFile pattern (from Context7/openpyxl docs)
    with NamedTemporaryFile() as tmp:
        wb.save(tmp.name)
        tmp.seek(0)
        response = HttpResponse(
            tmp.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="call_report_{call.code}.xlsx"'

        # Track in ReportGeneration model
        ReportGeneration.objects.create(
            report_type='call_summary',
            title=f'Call Report: {call.code}',
            call=call,
            file_format='xlsx',
            generated_by=request.user,
            parameters_json={'call_id': call_id}
        )

        return response


@coordinator_required
def report_history(request):
    """
    List of previously generated reports.
    Shows last 50 reports with download links.
    """
    reports = ReportGeneration.objects.select_related(
        'call', 'generated_by'
    ).order_by('-generated_at')[:50]

    context = {
        'reports': reports,
    }

    return render(request, 'reports/report_list.html', context)
