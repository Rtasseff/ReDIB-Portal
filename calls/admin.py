"""
Django admin configuration for calls models.
"""

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Call, CallEquipmentAllocation, ConsultRequest


class CallEquipmentAllocationInline(admin.TabularInline):
    model = CallEquipmentAllocation
    extra = 1
    fields = ['equipment']
    readonly_fields = ['total_approved_hours']


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
    list_display = ['call', 'equipment', 'total_approved_hours']
    list_filter = ['call', 'equipment__node']
    search_fields = ['call__code', 'equipment__name']
    ordering = ['call', 'equipment']

    readonly_fields = ['total_approved_hours']


@admin.register(ConsultRequest)
class ConsultRequestAdmin(admin.ModelAdmin):
    """Read-only audit view of public consult requests."""

    list_display = ['created_at', 'call', 'name', 'email', 'organization', 'emails_sent_at']
    list_filter = ['call', 'created_at', 'equipment__node']
    search_fields = ['name', 'email', 'organization', 'message', 'call__code']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    readonly_fields = [
        'call', 'equipment', 'user', 'name', 'email', 'phone', 'organization',
        'message', 'created_at', 'emails_sent_at', 'ip_hash',
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
