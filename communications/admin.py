"""
Django admin configuration for communications models.
"""

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import EmailTemplate, EmailLog, NotificationPreference


@admin.register(EmailTemplate)
class EmailTemplateAdmin(SimpleHistoryAdmin):
    list_display = ['template_type', 'subject', 'is_active', 'updated_at']
    list_filter = ['is_active', 'template_type']
    search_fields = ['subject', 'html_content', 'text_content']
    ordering = ['template_type']

    fieldsets = (
        ('Template Information', {
            'fields': ('template_type', 'subject', 'is_active')
        }),
        ('Content', {
            'fields': ('html_content', 'text_content', 'available_variables')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['recipient_email', 'subject', 'status', 'sent_at', 'created_at']
    list_filter = ['status', 'template', 'created_at']
    search_fields = ['recipient_email', 'subject']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'sent_at']

    fieldsets = (
        ('Recipient', {
            'fields': ('recipient', 'recipient_email')
        }),
        ('Email Content', {
            'fields': ('template', 'subject', 'html_content', 'text_content')
        }),
        ('Status', {
            'fields': ('status', 'error_message', 'sent_at')
        }),
        ('Related Objects', {
            'fields': ('related_call_id', 'related_application_id', 'related_evaluation_id'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'notify_call_published',
        'notify_application_updates',
        'notify_evaluation_assigned',
        'notify_reminders'
    ]
    list_filter = [
        'notify_call_published',
        'notify_application_updates',
        'notify_evaluation_assigned',
        'notify_feasibility_requests',
        'notify_reminders'
    ]
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    ordering = ['user']

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Notification Preferences', {
            'fields': (
                'notify_call_published',
                'notify_application_updates',
                'notify_evaluation_assigned',
                'notify_feasibility_requests',
                'notify_reminders'
            )
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']
