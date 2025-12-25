"""
Celery tasks for email sending and communication workflows.
"""

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template import Template, Context
from django.utils import timezone
from .models import EmailTemplate, EmailLog


@shared_task
def send_email_from_template(template_type, recipient_email, context_data, recipient_user_id=None,
                             related_call_id=None, related_application_id=None, related_evaluation_id=None):
    """
    Send an email using a template.

    Args:
        template_type: Type of email template to use
        recipient_email: Email address to send to
        context_data: Dictionary of variables for template rendering
        recipient_user_id: Optional User ID for logging
        related_call_id: Optional Call ID for logging
        related_application_id: Optional Application ID for logging
        related_evaluation_id: Optional Evaluation ID for logging

    Returns:
        Boolean indicating success
    """
    try:
        # Get template
        template = EmailTemplate.objects.get(template_type=template_type, is_active=True)

        # Render subject and content
        subject_template = Template(template.subject)
        html_template = Template(template.html_content)
        text_template = Template(template.text_content)

        context = Context(context_data)
        subject = subject_template.render(context)
        html_content = html_template.render(context)
        text_content = text_template.render(context)

        # Create email log
        email_log = EmailLog.objects.create(
            template=template,
            recipient_id=recipient_user_id,
            recipient_email=recipient_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            related_call_id=related_call_id,
            related_application_id=related_application_id,
            related_evaluation_id=related_evaluation_id,
            status='queued'
        )

        # Send email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            to=[recipient_email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        # Update log
        email_log.status = 'sent'
        email_log.sent_at = timezone.now()
        email_log.save()

        return True

    except EmailTemplate.DoesNotExist:
        EmailLog.objects.create(
            recipient_email=recipient_email,
            subject=f"Template {template_type} not found",
            status='failed',
            error_message=f"Email template '{template_type}' does not exist"
        )
        return False

    except Exception as e:
        if 'email_log' in locals():
            email_log.status = 'failed'
            email_log.error_message = str(e)
            email_log.save()
        else:
            EmailLog.objects.create(
                recipient_email=recipient_email,
                subject="Email sending failed",
                status='failed',
                error_message=str(e)
            )
        return False


@shared_task
def send_bulk_email(template_type, recipients_data, context_data=None):
    """
    Send bulk emails using a template.

    Args:
        template_type: Type of email template to use
        recipients_data: List of dicts with 'email' and optionally 'user_id', 'context'
        context_data: Global context data (merged with per-recipient context)

    Returns:
        Dict with success/failure counts
    """
    results = {'success': 0, 'failed': 0}

    for recipient in recipients_data:
        # Merge global and per-recipient context
        merged_context = context_data.copy() if context_data else {}
        if 'context' in recipient:
            merged_context.update(recipient['context'])

        success = send_email_from_template(
            template_type=template_type,
            recipient_email=recipient['email'],
            context_data=merged_context,
            recipient_user_id=recipient.get('user_id')
        )

        if success:
            results['success'] += 1
        else:
            results['failed'] += 1

    return results
