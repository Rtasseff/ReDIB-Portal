"""
Django admin configuration for access models.
"""

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import AccessGrant, Publication


class PublicationInline(admin.TabularInline):
    model = Publication
    extra = 0
    fields = ['title', 'journal', 'publication_date', 'redib_acknowledged', 'verified']


@admin.register(AccessGrant)
class AccessGrantAdmin(SimpleHistoryAdmin):
    list_display = [
        'application',
        'equipment',
        'hours_granted',
        'actual_hours_used',
        'hours_utilization_rate',
        'is_accepted',
        'is_completed'
    ]
    list_filter = ['equipment__node', 'accepted_by_user', 'completed_at']
    search_fields = ['application__code', 'equipment__name']
    ordering = ['-created_at']
    inlines = [PublicationInline]
    readonly_fields = ['created_at', 'updated_at', 'hours_utilization_rate']

    fieldsets = (
        ('Grant Information', {
            'fields': ('application', 'equipment', 'hours_granted', 'actual_hours_used', 'hours_utilization_rate')
        }),
        ('Scheduling', {
            'fields': ('scheduled_start', 'scheduled_end')
        }),
        ('Acceptance', {
            'fields': ('accepted_by_user', 'accepted_at', 'acceptance_deadline')
        }),
        ('Completion', {
            'fields': ('completed_at',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Publication)
class PublicationAdmin(SimpleHistoryAdmin):
    list_display = [
        'title',
        'publication_year',
        'journal',
        'redib_acknowledged',
        'verified',
        'reported_at'
    ]
    list_filter = ['publication_year', 'redib_acknowledged', 'verified']
    search_fields = ['title', 'authors', 'doi', 'journal']
    ordering = ['-publication_date', '-reported_at']
    readonly_fields = ['publication_year', 'reported_at', 'created_at', 'updated_at']

    fieldsets = (
        ('Publication Information', {
            'fields': (
                'access_grant',
                'title',
                'authors',
                'journal',
                'doi',
                'publication_date',
                'publication_year'
            )
        }),
        ('ReDIB Acknowledgment', {
            'fields': ('redib_acknowledged', 'acknowledgment_text')
        }),
        ('Metrics', {
            'fields': ('citations', 'impact_factor'),
            'classes': ('collapse',)
        }),
        ('Reporting', {
            'fields': ('reported_by', 'reported_at', 'verified')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
