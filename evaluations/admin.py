"""
Django admin configuration for evaluations models.
"""

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Evaluation


@admin.register(Evaluation)
class EvaluationAdmin(SimpleHistoryAdmin):
    list_display = [
        'application',
        'evaluator',
        'total_score',
        'is_complete',
        'assigned_at',
        'completed_at'
    ]
    list_filter = ['completed_at', 'application__call']
    search_fields = ['application__code', 'evaluator__email']
    ordering = ['-assigned_at']
    readonly_fields = ['total_score', 'assigned_at', 'completed_at', 'updated_at']

    fieldsets = (
        ('Assignment', {
            'fields': ('application', 'evaluator', 'assigned_at')
        }),
        ('Scores', {
            'fields': (
                'score_relevance',
                'score_methodology',
                'score_contributions',
                'score_impact',
                'score_opportunity',
                'total_score'
            )
        }),
        ('Comments and Completion', {
            'fields': ('comments', 'completed_at', 'updated_at')
        }),
    )
