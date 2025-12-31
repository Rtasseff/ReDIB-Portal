"""
Django admin configuration for applications models.
"""

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Application, RequestedAccess, FeasibilityReview


class RequestedAccessInline(admin.TabularInline):
    model = RequestedAccess
    extra = 1
    fields = ['equipment', 'hours_requested']


class FeasibilityReviewInline(admin.TabularInline):
    model = FeasibilityReview
    extra = 0
    fields = ['node', 'reviewer', 'is_feasible', 'comments', 'reviewed_at']
    readonly_fields = ['reviewed_at']


@admin.register(Application)
class ApplicationAdmin(SimpleHistoryAdmin):
    list_display = ['code', 'applicant_name', 'applicant_entity', 'call', 'status', 'resolution', 'final_score', 'submitted_at']
    list_filter = ['status', 'resolution', 'call', 'subject_area', 'service_modality']
    search_fields = ['code', 'brief_description', 'applicant__email', 'applicant_name', 'applicant_email', 'project_title']
    ordering = ['-submitted_at', '-created_at']
    inlines = [RequestedAccessInline, FeasibilityReviewInline]
    readonly_fields = ['code', 'final_score', 'submitted_at', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'call', 'applicant', 'status', 'brief_description', 'submitted_at')
        }),
        ('Applicant Details', {
            'fields': (
                'applicant_name', 'applicant_orcid', 'applicant_entity',
                'applicant_email', 'applicant_phone'
            ),
            'classes': ('collapse',)
        }),
        ('Funding Source', {
            'fields': (
                'project_title', 'project_code', 'funding_agency',
                'project_type', 'has_competitive_funding'
            ),
            'classes': ('collapse',)
        }),
        ('Classification', {
            'fields': ('subject_area', 'service_modality', 'specialization_area'),
            'classes': ('collapse',)
        }),
        ('Scientific Content', {
            'fields': (
                'scientific_relevance', 'methodology_description',
                'expected_contributions', 'impact_strengths',
                'socioeconomic_significance', 'opportunity_criteria'
            ),
            'classes': ('collapse',)
        }),
        ('Compliance and Ethics', {
            'fields': (
                'technical_feasibility_confirmed',
                'uses_animals', 'has_animal_ethics',
                'uses_humans', 'has_human_ethics',
                'data_consent'
            ),
            'classes': ('collapse',)
        }),
        ('Resolution', {
            'fields': ('resolution', 'final_score', 'resolution_date', 'resolution_comments')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RequestedAccess)
class RequestedAccessAdmin(SimpleHistoryAdmin):
    list_display = ['application', 'equipment', 'hours_requested']
    list_filter = ['equipment__node', 'equipment']
    search_fields = ['application__code', 'equipment__name']
    ordering = ['application', 'equipment']


@admin.register(FeasibilityReview)
class FeasibilityReviewAdmin(SimpleHistoryAdmin):
    list_display = ['application', 'node', 'reviewer', 'is_feasible', 'reviewed_at']
    list_filter = ['node', 'is_feasible']
    search_fields = ['application__code', 'reviewer__email']
    ordering = ['-reviewed_at']
    readonly_fields = ['created_at', 'updated_at']
