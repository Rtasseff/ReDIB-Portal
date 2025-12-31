"""
Email template and communication tracking models for ReDIB COA portal.
"""

from django.db import models
from django.conf import settings
from simple_history.models import HistoricalRecords


class EmailTemplate(models.Model):
    """
    Email templates for automated communications.
    Based on design document section 7.2 - 12 required email templates.
    """

    TEMPLATE_TYPES = [
        ('call_published', 'Call Published'),
        ('application_received', 'Application Received'),
        ('feasibility_request', 'Feasibility Review Request'),
        ('feasibility_reminder', 'Feasibility Review Reminder'),
        ('feasibility_rejected', 'Feasibility Rejected'),
        ('evaluation_assigned', 'Evaluation Assigned'),
        ('evaluation_reminder', 'Evaluation Reminder'),
        ('evaluations_complete', 'All Evaluations Complete'),  # Phase 5
        ('resolution_accepted', 'Resolution: Accepted'),
        ('resolution_pending', 'Resolution: Pending (Waiting List)'),
        ('resolution_rejected', 'Resolution: Rejected'),
        ('acceptance_reminder', 'Acceptance Reminder'),
        ('access_scheduled', 'Access Scheduled'),
        ('publication_followup', 'Publication Follow-up'),
    ]

    template_type = models.CharField(
        max_length=50,
        choices=TEMPLATE_TYPES,
        unique=True,
        help_text='Type of email template'
    )
    subject = models.CharField(
        max_length=200,
        help_text='Email subject line (supports template variables)'
    )
    html_content = models.TextField(
        help_text='HTML email body (supports Django template syntax)'
    )
    text_content = models.TextField(
        help_text='Plain text email body (supports Django template syntax)'
    )

    # Template variables documentation
    available_variables = models.TextField(
        blank=True,
        help_text='JSON or text describing available template variables'
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['template_type']
        verbose_name = 'Email Template'

    def __str__(self):
        return f"{self.get_template_type_display()}"


class EmailLog(models.Model):
    """
    Log of all emails sent by the system for tracking and debugging.
    """

    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
    ]

    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs'
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emails_received'
    )
    recipient_email = models.EmailField(help_text='Email address sent to')

    subject = models.CharField(max_length=200)
    html_content = models.TextField(blank=True)
    text_content = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    error_message = models.TextField(blank=True)

    # Tracking
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Related objects (optional, for context)
    related_call_id = models.IntegerField(null=True, blank=True)
    related_application_id = models.IntegerField(null=True, blank=True)
    related_evaluation_id = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Email Log'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['recipient_email']),
        ]

    def __str__(self):
        return f"{self.recipient_email} - {self.subject} ({self.status})"


class NotificationPreference(models.Model):
    """
    User preferences for email notifications.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )

    # Notification preferences by type
    notify_call_published = models.BooleanField(
        default=True,
        help_text='Receive notifications when new calls are published'
    )
    notify_application_updates = models.BooleanField(
        default=True,
        help_text='Receive updates about your applications'
    )
    notify_evaluation_assigned = models.BooleanField(
        default=True,
        help_text='Receive notifications when evaluations are assigned to you'
    )
    notify_feasibility_requests = models.BooleanField(
        default=True,
        help_text='Receive feasibility review requests (for node coordinators)'
    )
    notify_reminders = models.BooleanField(
        default=True,
        help_text='Receive reminder emails'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Notification Preference'

    def __str__(self):
        return f"{self.user.email} preferences"
