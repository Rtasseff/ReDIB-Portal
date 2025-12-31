"""
Django management command to seed email templates for Phase 4.
Usage: python manage.py seed_email_templates
"""

from django.core.management.base import BaseCommand
from communications.models import EmailTemplate


class Command(BaseCommand):
    help = 'Seed email templates for ReDIB COA portal - Phase 4'

    def handle(self, *args, **options):
        templates_data = [
            {
                'template_type': 'evaluation_assigned',
                'subject': 'ReDIB COA: Evaluation Assignment for {{ call_code }}',
                'html_content': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #2c3e50; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .button { display: inline-block; padding: 12px 24px; background-color: #3498db; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
        .info-box { background-color: #e8f4f8; border-left: 4px solid #3498db; padding: 15px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Evaluation Assignment</p>
        </div>

        <div class="content">
            <p>Dear {{ evaluator_name }},</p>

            <p>You have been assigned to evaluate an application for the ReDIB Competitive Open Access call <strong>{{ call_code }}</strong>.</p>

            <div class="info-box">
                <p><strong>Application Code:</strong> {{ application_code }}</p>
                <p><strong>Call:</strong> {{ call_code }}</p>
                <p><strong>Evaluation Deadline:</strong> {{ deadline|date:"F d, Y" }}</p>
            </div>

            <p>Please access the ReDIB COA Portal to review the application and submit your evaluation:</p>

            <p style="text-align: center;">
                <a href="{{ evaluation_url }}" class="button">View Application & Submit Evaluation</a>
            </p>

            <p><strong>Important Notes:</strong></p>
            <ul>
                <li>Evaluations are blind - applicant identity is hidden</li>
                <li>Please score the application on 5 criteria (1-5 scale)</li>
                <li>Your evaluation must be submitted by the deadline above</li>
                <li>You will receive a reminder 7 days before the deadline</li>
            </ul>

            <p>If you have any questions or conflicts of interest, please contact the ReDIB coordinator immediately.</p>

            <p>Thank you for your participation in the evaluation process.</p>

            <p>Best regards,<br>
            The ReDIB COA Team</p>
        </div>

        <div class="footer">
            <p>This is an automated message from the ReDIB COA Portal.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>
                ''',
                'text_content': '''
Dear {{ evaluator_name }},

You have been assigned to evaluate an application for the ReDIB Competitive Open Access call {{ call_code }}.

Application Details:
- Application Code: {{ application_code }}
- Call: {{ call_code }}
- Evaluation Deadline: {{ deadline|date:"F d, Y" }}

Please access the ReDIB COA Portal to review the application and submit your evaluation:
{{ evaluation_url }}

Important Notes:
- Evaluations are blind - applicant identity is hidden
- Please score the application on 5 criteria (1-5 scale)
- Your evaluation must be submitted by the deadline above
- You will receive a reminder 7 days before the deadline

If you have any questions or conflicts of interest, please contact the ReDIB coordinator immediately.

Thank you for your participation in the evaluation process.

Best regards,
The ReDIB COA Team

---
This is an automated message from the ReDIB COA Portal.
Please do not reply to this email.
                ''',
                'available_variables': '''
{
    "evaluator_name": "Full name of the evaluator",
    "application_code": "Application unique code (e.g., APP-2025-001)",
    "call_code": "Call code (e.g., COA-2025-01)",
    "deadline": "Evaluation deadline (datetime object)",
    "evaluation_url": "URL to the evaluation form"
}
                '''
            },
            {
                'template_type': 'evaluation_reminder',
                'subject': 'ReDIB COA: Evaluation Reminder for {{ application_code }}',
                'html_content': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #e74c3c; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .button { display: inline-block; padding: 12px 24px; background-color: #e74c3c; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
        .warning-box { background-color: #fef5e7; border-left: 4px solid: #f39c12; padding: 15px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Evaluation Deadline Approaching</p>
        </div>

        <div class="content">
            <p>Dear {{ evaluator_name }},</p>

            <p>This is a friendly reminder that your evaluation for application <strong>{{ application_code }}</strong> is due soon.</p>

            <div class="warning-box">
                <p><strong>Application:</strong> {{ application_code }} - {{ application_title }}</p>
                <p><strong>Call:</strong> {{ call_code }}</p>
                <p><strong>Days Remaining:</strong> {{ days_remaining }} days</p>
                <p><strong>Deadline:</strong> {{ deadline|date:"F d, Y" }}</p>
            </div>

            <p>Please submit your evaluation as soon as possible:</p>

            <p style="text-align: center;">
                <a href="{{ evaluation_url }}" class="button">Complete Evaluation</a>
            </p>

            <p>Thank you for your timely participation.</p>

            <p>Best regards,<br>
            The ReDIB COA Team</p>
        </div>

        <div class="footer">
            <p>This is an automated reminder from the ReDIB COA Portal.</p>
        </div>
    </div>
</body>
</html>
                ''',
                'text_content': '''
Dear {{ evaluator_name }},

This is a friendly reminder that your evaluation for application {{ application_code }} is due soon.

Application Details:
- Application: {{ application_code }} - {{ application_title }}
- Call: {{ call_code }}
- Days Remaining: {{ days_remaining }} days
- Deadline: {{ deadline|date:"F d, Y" }}

Please submit your evaluation as soon as possible.

Thank you for your timely participation.

Best regards,
The ReDIB COA Team

---
This is an automated reminder from the ReDIB COA Portal.
                ''',
                'available_variables': '''
{
    "evaluator_name": "Full name of the evaluator",
    "application_code": "Application unique code",
    "application_title": "Brief description of the application",
    "call_code": "Call code",
    "days_remaining": "Number of days until deadline",
    "deadline": "Evaluation deadline (datetime object)"
}
                '''
            },
            {
                'template_type': 'evaluations_complete',
                'subject': 'ReDIB COA: All Evaluations Complete for {{ application_code }}',
                'html_content': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #27ae60; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .button { display: inline-block; padding: 12px 24px; background-color: #27ae60; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
        .success-box { background-color: #d5f4e6; border-left: 4px solid #27ae60; padding: 15px; margin: 15px 0; }
        .score-display { font-size: 24px; font-weight: bold; color: #27ae60; text-align: center; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>All Evaluations Complete</p>
        </div>

        <div class="content">
            <p>Dear {{ coordinator_name }},</p>

            <p>All evaluations have been completed for application <strong>{{ application_code }}</strong> in call <strong>{{ call_code }}</strong>.</p>

            <div class="success-box">
                <p><strong>Application:</strong> {{ application_code }}</p>
                <p><strong>Applicant:</strong> {{ applicant_name }}</p>
                <p><strong>Brief Description:</strong> {{ brief_description }}</p>
                <p><strong>Call:</strong> {{ call_code }}</p>
                <p><strong>Number of Evaluations:</strong> {{ num_evaluations }}</p>
            </div>

            <div class="score-display">
                Average Score: {{ average_score }} / 5.00
            </div>

            <p>The application status has been automatically updated to <strong>EVALUATED</strong> and is now ready for your resolution.</p>

            <p style="text-align: center;">
                <a href="{{ application_url }}" class="button">Review Application & Decide</a>
            </p>

            <p><strong>Next Steps:</strong></p>
            <ul>
                <li>Review individual evaluator scores and comments</li>
                <li>Decide on resolution (Accept, Reject, or Waiting List)</li>
                <li>Notify the applicant of the decision</li>
            </ul>

            <p>Thank you for coordinating the ReDIB COA process.</p>

            <p>Best regards,<br>
            The ReDIB COA Team</p>
        </div>

        <div class="footer">
            <p>This is an automated notification from the ReDIB COA Portal.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>
                ''',
                'text_content': '''
Dear {{ coordinator_name }},

All evaluations have been completed for application {{ application_code }} in call {{ call_code }}.

Application Details:
- Application: {{ application_code }}
- Applicant: {{ applicant_name }}
- Brief Description: {{ brief_description }}
- Call: {{ call_code }}
- Number of Evaluations: {{ num_evaluations }}

AVERAGE SCORE: {{ average_score }} / 5.00

The application status has been automatically updated to EVALUATED and is now ready for your resolution.

Review Application & Decide:
{{ application_url }}

Next Steps:
- Review individual evaluator scores and comments
- Decide on resolution (Accept, Reject, or Waiting List)
- Notify the applicant of the decision

Thank you for coordinating the ReDIB COA process.

Best regards,
The ReDIB COA Team

---
This is an automated notification from the ReDIB COA Portal.
Please do not reply to this email.
                ''',
                'available_variables': '''
{
    "coordinator_name": "Full name of the coordinator",
    "application_code": "Application unique code",
    "applicant_name": "Name of the applicant",
    "brief_description": "Brief description of the application",
    "call_code": "Call code",
    "average_score": "Average score across all evaluations (rounded to 2 decimals)",
    "num_evaluations": "Number of completed evaluations",
    "application_url": "URL to view the application"
}
                '''
            },
            # Phase 6: Resolution Notifications
            {
                'template_type': 'resolution_accepted',
                'subject': 'ReDIB COA: Application {{ application_code }} Accepted',
                'html_content': '''<html><body>
<h2>Application Accepted</h2>
<p>Dear {{ applicant_name }},</p>
<p>Congratulations! Your application <strong>{{ application_code }}</strong> for call {{ call_code }} has been <strong>ACCEPTED</strong>.</p>
<p><strong>Final Score:</strong> {{ final_score }}/5.00</p>
<p><strong>Hours Granted:</strong> {{ hours_granted }} hours</p>
<p>{{ resolution_comments }}</p>
<p>Next steps will be provided soon.</p>
<p>Best regards,<br>ReDIB COA Team</p>
</body></html>''',
                'text_content': '''Application Accepted

Dear {{ applicant_name }},

Congratulations! Your application {{ application_code }} for call {{ call_code }} has been ACCEPTED.

Final Score: {{ final_score }}/5.00
Hours Granted: {{ hours_granted }} hours

{{ resolution_comments }}

Next steps will be provided soon.

Best regards,
ReDIB COA Team''',
                'available_variables': '''Variables: applicant_name, application_code, call_code, final_score, resolution, hours_granted, resolution_comments, resolution_date'''
            },
            {
                'template_type': 'resolution_pending',
                'subject': 'ReDIB COA: Application {{ application_code }} Pending',
                'html_content': '''<html><body>
<h2>Application Pending (Waiting List)</h2>
<p>Dear {{ applicant_name }},</p>
<p>Your application <strong>{{ application_code }}</strong> for call {{ call_code }} has been marked as <strong>PENDING</strong> (waiting list).</p>
<p><strong>Final Score:</strong> {{ final_score }}/5.00</p>
<p>{{ resolution_comments }}</p>
<p>You will be notified if hours become available.</p>
<p>Best regards,<br>ReDIB COA Team</p>
</body></html>''',
                'text_content': '''Application Pending (Waiting List)

Dear {{ applicant_name }},

Your application {{ application_code }} for call {{ call_code }} has been marked as PENDING (waiting list).

Final Score: {{ final_score }}/5.00

{{ resolution_comments }}

You will be notified if hours become available.

Best regards,
ReDIB COA Team''',
                'available_variables': '''Variables: applicant_name, application_code, call_code, final_score, resolution, hours_granted, resolution_comments, resolution_date'''
            },
            {
                'template_type': 'resolution_rejected',
                'subject': 'ReDIB COA: Application {{ application_code }} Resolution',
                'html_content': '''<html><body>
<h2>Application Resolution</h2>
<p>Dear {{ applicant_name }},</p>
<p>Your application <strong>{{ application_code }}</strong> for call {{ call_code }} was not accepted at this time.</p>
<p><strong>Final Score:</strong> {{ final_score }}/5.00</p>
<p>{{ resolution_comments }}</p>
<p>Thank you for your participation.</p>
<p>Best regards,<br>ReDIB COA Team</p>
</body></html>''',
                'text_content': '''Application Resolution

Dear {{ applicant_name }},

Your application {{ application_code }} for call {{ call_code }} was not accepted at this time.

Final Score: {{ final_score }}/5.00

{{ resolution_comments }}

Thank you for your participation.

Best regards,
ReDIB COA Team''',
                'available_variables': '''Variables: applicant_name, application_code, call_code, final_score, resolution, hours_granted, resolution_comments, resolution_date'''
            },
            # Phase 7: Acceptance & Handoff templates
            {
                'template_type': 'handoff_notification',
                'subject': 'ReDIB COA Access Approved - Application {{ application_code }} Ready for Scheduling',
                'html_content': '''<html><body>
<h2>ReDIB COA Access Approved - Ready for Scheduling</h2>

<p>Dear {{ applicant_name }} and {{ node_names }} Team,</p>

<p>This is to confirm that COA application <strong>{{ application_code }}</strong> has been approved by the evaluation committee and accepted by the applicant.</p>

<h3>APPLICATION DETAILS</h3>
<ul>
<li><strong>Application Code:</strong> {{ application_code }}</li>
<li><strong>Applicant:</strong> {{ applicant_name }} ({{ applicant_entity }})</li>
<li><strong>Email:</strong> {{ applicant_email }}</li>
<li><strong>Phone:</strong> {{ applicant_phone }}</li>
<li><strong>Project:</strong> {{ project_title }}</li>
<li><strong>Brief Description:</strong> {{ brief_description }}</li>
</ul>

<h3>REQUESTED ACCESS</h3>
<p><strong>Service Modality:</strong> {{ service_modality }}</p>
{% for access in requested_access %}
<p>- <strong>{{ access.node_name }}</strong> / {{ access.equipment_name }}: {{ access.hours_requested }} hours requested</p>
{% endfor %}

<h3>NEXT STEPS</h3>
<p>Please coordinate directly to schedule the access time. The applicant and node team should arrange mutually convenient dates for the requested work.</p>

<p>For questions, contact: info@redib.net</p>

<hr>
<p><small>This is an automated notification from the ReDIB COA Management System.</small></p>
</body></html>''',
                'text_content': '''ReDIB COA Access Approved - Ready for Scheduling

Dear {{ applicant_name }} and {{ node_names }} Team,

This is to confirm that COA application {{ application_code }} has been approved by the evaluation committee and accepted by the applicant.

APPLICATION DETAILS
- Application Code: {{ application_code }}
- Applicant: {{ applicant_name }} ({{ applicant_entity }})
- Email: {{ applicant_email }}
- Phone: {{ applicant_phone }}
- Project: {{ project_title }}
- Brief Description: {{ brief_description }}

REQUESTED ACCESS
Service Modality: {{ service_modality }}
{% for access in requested_access %}- {{ access.node_name }} / {{ access.equipment_name }}: {{ access.hours_requested }} hours requested
{% endfor %}

NEXT STEPS
Please coordinate directly to schedule the access time. The applicant and node team should arrange mutually convenient dates for the requested work.

For questions, contact: info@redib.net

---
This is an automated notification from the ReDIB COA Management System.''',
                'available_variables': '''Variables: applicant_name, applicant_entity, applicant_email, applicant_phone, application_code, project_title, brief_description, service_modality, node_names, requested_access (list)'''
            },
            {
                'template_type': 'acceptance_expired',
                'subject': 'Action Required: Acceptance Deadline Expired for Application {{ application_code }}',
                'html_content': '''<html><body>
<h2>Acceptance Deadline Expired</h2>

<p>Dear {{ applicant_name }},</p>

<p>This is to inform you that the acceptance deadline for your approved COA application <strong>{{ application_code }}</strong> has expired.</p>

<p><strong>Deadline was:</strong> {{ deadline }}</p>

<p>Since we did not receive your acceptance or decline response within the required 10-day period, this application has been automatically marked as expired and the access grant is no longer available.</p>

<p>If you would like to request access in the future, please apply during the next open call period.</p>

<p>If you believe this is an error, please contact us at info@redib.net</p>

<hr>
<p><small>This is an automated notification from the ReDIB COA Management System.</small></p>
</body></html>''',
                'text_content': '''Acceptance Deadline Expired

Dear {{ applicant_name }},

This is to inform you that the acceptance deadline for your approved COA application {{ application_code }} has expired.

Deadline was: {{ deadline }}

Since we did not receive your acceptance or decline response within the required 10-day period, this application has been automatically marked as expired and the access grant is no longer available.

If you would like to request access in the future, please apply during the next open call period.

If you believe this is an error, please contact us at info@redib.net

---
This is an automated notification from the ReDIB COA Management System.''',
                'available_variables': '''Variables: applicant_name, application_code, deadline'''
            }
        ]

        created_count = 0
        updated_count = 0

        for template_data in templates_data:
            template, created = EmailTemplate.objects.update_or_create(
                template_type=template_data['template_type'],
                defaults={
                    'subject': template_data['subject'],
                    'html_content': template_data['html_content'],
                    'text_content': template_data['text_content'],
                    'available_variables': template_data['available_variables'],
                    'is_active': True
                }
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created template: {template.get_template_type_display()}'
                    )
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'Updated template: {template.get_template_type_display()}'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted: {created_count} created, {updated_count} updated'
            )
        )
