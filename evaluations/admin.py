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
        'recommendation',
        'is_complete',
        'assigned_at',
        'completed_at'
    ]
    list_filter = ['completed_at', 'recommendation', 'application__call']
    search_fields = ['application__code', 'evaluator__email']
    ordering = ['-assigned_at']
    readonly_fields = ['total_score', 'assigned_at', 'completed_at', 'updated_at']

    fieldsets = (
        ('Assignment', {
            'fields': ('application', 'evaluator', 'assigned_at')
        }),
        ('Category 1: Scientific and Technical Relevance', {
            'fields': (
                'score_quality_originality',
                'score_methodology_design',
                'score_expected_contributions',
            )
        }),
        ('Category 2: Timeliness and Impact', {
            'fields': (
                'score_knowledge_advancement',
                'score_social_economic_impact',
                'score_exploitation_dissemination',
            )
        }),
        ('Recommendation and Total', {
            'fields': ('recommendation', 'total_score')
        }),
        ('Comments and Completion', {
            'fields': ('comments', 'completed_at', 'updated_at')
        }),
    )
