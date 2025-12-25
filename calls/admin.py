"""
Django admin configuration for calls models.
"""

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Call, CallEquipmentAllocation


class CallEquipmentAllocationInline(admin.TabularInline):
    model = CallEquipmentAllocation
    extra = 1
    fields = ['equipment', 'hours_offered']


@admin.register(Call)
class CallAdmin(SimpleHistoryAdmin):
    list_display = ['code', 'title', 'status', 'submission_start', 'submission_end', 'published_at']
    list_filter = ['status', 'submission_start']
    search_fields = ['code', 'title', 'description']
    ordering = ['-submission_start']
    inlines = [CallEquipmentAllocationInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'title', 'status', 'description', 'guidelines')
        }),
        ('Important Dates', {
            'fields': (
                'submission_start', 'submission_end',
                'evaluation_deadline',
                'execution_start', 'execution_end',
                'published_at'
            )
        }),
    )


@admin.register(CallEquipmentAllocation)
class CallEquipmentAllocationAdmin(SimpleHistoryAdmin):
    list_display = ['call', 'equipment', 'hours_offered', 'hours_allocated', 'hours_available']
    list_filter = ['call', 'equipment__node']
    search_fields = ['call__code', 'equipment__name']
    ordering = ['call', 'equipment']

    readonly_fields = ['hours_allocated', 'hours_available']
