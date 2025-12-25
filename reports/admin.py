"""
Django admin configuration for reports models.
"""

from django.contrib import admin
from .models import ReportGeneration


@admin.register(ReportGeneration)
class ReportGenerationAdmin(admin.ModelAdmin):
    list_display = ['title', 'report_type', 'file_format', 'generated_by', 'generated_at']
    list_filter = ['report_type', 'file_format', 'generated_at']
    search_fields = ['title']
    ordering = ['-generated_at']
    readonly_fields = ['generated_at']

    fieldsets = (
        ('Report Information', {
            'fields': ('report_type', 'title', 'file_format')
        }),
        ('Parameters', {
            'fields': ('call', 'node', 'start_date', 'end_date', 'parameters_json')
        }),
        ('Output', {
            'fields': ('file_path',)
        }),
        ('Metadata', {
            'fields': ('generated_by', 'generated_at')
        }),
    )
