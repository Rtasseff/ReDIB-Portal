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
                'template_type': 'feasibility_request',
                'subject': 'ReDIB COA: New Application for Equipment at {{ node_name }}',
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
            <p>New Application - Feasibility Review Required</p>
        </div>

        <div class="content">
            <p>Dear {{ reviewer_name }},</p>

            <p>A new application has been submitted requesting equipment at <strong>{{ node_name }}</strong>.</p>

            <div class="info-box">
                <p><strong>Application Code:</strong> {{ application_code }}</p>
                <p><strong>Your Node:</strong> {{ node_name }}</p>
            </div>

            <p>As the node coordinator, please review this application to assess the technical feasibility of providing the requested equipment access.</p>

            <p style="text-align: center;">
                <a href="{{ review_url }}" class="button">Review Application</a>
            </p>

            <p><strong>Next Steps:</strong></p>
            <ul>
                <li>Review the application details and requested equipment</li>
                <li>Assess technical feasibility at your node</li>
                <li>Approve or reject the feasibility request with comments</li>
            </ul>

            <p>Your timely response helps ensure applications progress smoothly through the evaluation process.</p>

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
Dear {{ reviewer_name }},

A new application has been submitted requesting equipment at {{ node_name }}.

Application Details:
- Application Code: {{ application_code }}
- Your Node: {{ node_name }}

As the node coordinator, please review this application to assess the technical feasibility of providing the requested equipment access.

Review Application:
{{ review_url }}

Next Steps:
- Review the application details and requested equipment
- Assess technical feasibility at your node
- Approve or reject the feasibility request with comments

Your timely response helps ensure applications progress smoothly through the evaluation process.

Best regards,
The ReDIB COA Team

---
This is an automated message from the ReDIB COA Portal.
Please do not reply to this email.
                ''',
                'available_variables': '''
{
    "reviewer_name": "Full name of the node coordinator",
    "application_code": "Application unique code (e.g., COA-2025-01-APP-001)",
    "node_name": "Name of the node (e.g., CIC biomaGUNE)",
    "review_url": "URL to the feasibility review page"
}
                '''
            },
            {
                'template_type': 'application_received',
                'subject': 'ReDIB COA: Application {{ application_code }} Received',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #27ae60; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
        .info-box { background-color: #d5f4e6; border-left: 4px solid #27ae60; padding: 15px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Application Received</p>
        </div>

        <div class="content">
            <p>Dear {{ applicant_name }},</p>

            <p>Your application has been successfully submitted to the ReDIB Competitive Open Access programme.</p>

            <div class="info-box">
                <p><strong>Application Code:</strong> {{ application_code }}</p>
                <p><strong>Call:</strong> {{ call_code }}</p>
            </div>

            <p><strong>What happens next:</strong></p>
            <ul>
                <li>Your application will be reviewed for technical feasibility by the relevant node coordinator(s)</li>
                <li>Once approved, it will proceed to scientific evaluation by independent reviewers</li>
                <li>You will be notified of the outcome at each stage</li>
            </ul>

            <p>Thank you for your submission. If you have any questions, please contact {{ contact_email }}.</p>

            <p>Best regards,<br>
            The ReDIB COA Team</p>
        </div>

        <div class="footer">
            <p>This is an automated message from the ReDIB COA Portal.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''Dear {{ applicant_name }},

Your application has been successfully submitted to the ReDIB Competitive Open Access programme.

Application Details:
- Application Code: {{ application_code }}
- Call: {{ call_code }}

What happens next:
- Your application will be reviewed for technical feasibility by the relevant node coordinator(s)
- Once approved, it will proceed to scientific evaluation by independent reviewers
- You will be notified of the outcome at each stage

Thank you for your submission. If you have any questions, please contact {{ contact_email }}.

Best regards,
The ReDIB COA Team

---
This is an automated message from the ReDIB COA Portal.
Please do not reply to this email.''',
                'available_variables': '''
{
    "applicant_name": "Full name of the applicant",
    "application_code": "Application unique code (e.g., COA-2026-01-APP-001)",
    "call_code": "Call code (e.g., COA-2026-01)"
}
                '''
            },
            {
                'template_type': 'feasibility_complete',
                'subject': 'ReDIB COA: Feasibility Review Complete for {{ application_code }}',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #2c3e50; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
        .info-box { background-color: #e8f4f8; border-left: 4px solid #3498db; padding: 15px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Feasibility Review Complete</p>
        </div>

        <div class="content">
            <p>Dear {{ applicant_name }},</p>

            <p>The technical feasibility review for your application <strong>{{ application_code }}</strong> has been completed.</p>

            <div class="info-box">
                <p><strong>Application Code:</strong> {{ application_code }}</p>
                <p><strong>Status:</strong> {{ status }}</p>
            </div>

            {% if is_approved %}
            <p>You will receive further updates as your application progresses through the evaluation process.</p>
            {% else %}
            <p>Unfortunately, your application did not pass the technical feasibility review and will not proceed to evaluation.</p>
            {% endif %}

            <p>If you have any questions, please contact {{ contact_email }}.</p>

            <p>Best regards,<br>
            The ReDIB COA Team</p>
        </div>

        <div class="footer">
            <p>This is an automated message from the ReDIB COA Portal.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''Dear {{ applicant_name }},

The technical feasibility review for your application {{ application_code }} has been completed.

Application Code: {{ application_code }}
Status: {{ status }}

{% if is_approved %}You will receive further updates as your application progresses through the evaluation process.{% else %}Unfortunately, your application did not pass the technical feasibility review and will not proceed to evaluation.{% endif %}

If you have any questions, please contact {{ contact_email }}.

Best regards,
The ReDIB COA Team

---
This is an automated message from the ReDIB COA Portal.
Please do not reply to this email.''',
                'available_variables': '''
{
    "applicant_name": "Full name of the applicant",
    "application_code": "Application unique code",
    "status": "Feasibility outcome (e.g., approved and ready for evaluation, or rejected)",
    "is_approved": "Boolean — True if approved, False if rejected. Used to gate next-steps language."
}
                '''
            },
            {
                'template_type': 'feasibility_edits_requested',
                'subject': 'ReDIB COA: Edits Requested for {{ application_code }}',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #f39c12; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
        .info-box { background-color: #fef9e7; border-left: 4px solid #f39c12; padding: 15px; margin: 15px 0; }
        .btn { display: inline-block; background-color: #3498db; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Edits Requested</p>
        </div>

        <div class="content">
            <p>Dear {{ applicant_name }},</p>

            <p>A node coordinator has reviewed your application <strong>{{ application_code }}</strong> and is requesting revisions before it can proceed.</p>

            <div class="info-box">
                <p><strong>Application Code:</strong> {{ application_code }}</p>
                <p><strong>Node:</strong> {{ node_name }}</p>
                <p><strong>Reviewer Comments:</strong></p>
                <p>{{ reviewer_comments }}</p>
            </div>

            <p>Please review the comments above, edit your application accordingly, and resubmit.</p>

            <p style="text-align: center; margin: 20px 0;">
                <a href="{{ application_url }}" class="btn">View Your Application</a>
            </p>

            <p>Best regards,<br>
            The ReDIB COA Team</p>
        </div>

        <div class="footer">
            <p>This is an automated message from the ReDIB COA Portal.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''Dear {{ applicant_name }},

A node coordinator has reviewed your application {{ application_code }} and is requesting revisions.

Application Code: {{ application_code }}
Node: {{ node_name }}
Reviewer Comments: {{ reviewer_comments }}

Please review the comments above, edit your application accordingly, and resubmit.

View your application: {{ application_url }}

Best regards,
The ReDIB COA Team

---
This is an automated message from the ReDIB COA Portal.
Please do not reply to this email.''',
                'available_variables': '''
{
    "applicant_name": "Full name of the applicant",
    "application_code": "Application unique code",
    "node_name": "Name of the reviewing node",
    "reviewer_comments": "Comments from the coordinator",
    "application_url": "Direct URL to the application"
}
                '''
            },
            {
                'template_type': 'evaluation_assigned',
                'subject': 'ReDIB COA: Evaluation Assignment for {{ application_code }}',
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
                <li>Please score the application on 6 criteria (0-2 scale)</li>
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
- Please score the application on 6 criteria (0-2 scale)
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

Please submit your evaluation as soon as possible:
{{ evaluation_url }}

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
    "deadline": "Evaluation deadline (datetime object)",
    "evaluation_url": "URL to the evaluation form"
}
                '''
            },
            # Overdue evaluation notifications (Issue #11)
            {
                'template_type': 'evaluation_overdue',
                'subject': 'ReDIB COA: Your Evaluation for {{ application_code }} is Overdue',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #c0392b; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .button { display: inline-block; padding: 12px 24px; background-color: #c0392b; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
        .warning-box { background-color: #fdedec; border-left: 4px solid #c0392b; padding: 15px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Evaluation Overdue</p>
        </div>
        <div class="content">
            <p>Dear {{ evaluator_name }},</p>
            <p>Your evaluation for application <strong>{{ application_code }}</strong> (call {{ call_code }}) is now <strong>overdue</strong>.</p>
            <div class="warning-box">
                <p><strong>Evaluation Deadline:</strong> {{ deadline|date:"F d, Y" }}</p>
                <p><strong>Grace Period:</strong> You have <strong>1 week</strong> from the deadline to submit your evaluation before the form is locked.</p>
            </div>
            <p>Please submit your evaluation as soon as possible:</p>
            <p style="text-align: center;">
                <a href="{{ evaluation_url }}" class="button">Submit Evaluation Now</a>
            </p>
            <p>If you are unable to complete the evaluation, please contact the ReDIB coordinator immediately.</p>
            <p>Best regards,<br>The ReDIB COA Team</p>
        </div>
        <div class="footer">
            <p>This is an automated message from the ReDIB COA Portal.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''Dear {{ evaluator_name }},

Your evaluation for application {{ application_code }} (call {{ call_code }}) is now OVERDUE.

Evaluation Deadline: {{ deadline|date:"F d, Y" }}
Grace Period: You have 1 week from the deadline to submit your evaluation before the form is locked.

Please submit your evaluation as soon as possible:
{{ evaluation_url }}

If you are unable to complete the evaluation, please contact the ReDIB coordinator immediately.

Best regards,
The ReDIB COA Team

---
This is an automated message from the ReDIB COA Portal.''',
                'available_variables': '''
{
    "evaluator_name": "Full name of the evaluator",
    "application_code": "Application unique code",
    "call_code": "Call code",
    "deadline": "Evaluation deadline (datetime object)",
    "evaluation_url": "URL to the evaluation form"
}
                '''
            },
            {
                'template_type': 'coordinator_overdue_evaluations',
                'subject': 'ReDIB COA: Overdue Evaluations for Call {{ call_code }}',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #e67e22; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
        .info-box { background-color: #fef5e7; border-left: 4px solid #e67e22; padding: 15px; margin: 15px 0; }
        pre { background-color: #f0f0f0; padding: 10px; border-radius: 4px; white-space: pre-wrap; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Overdue Evaluations Notification</p>
        </div>
        <div class="content">
            <p>Dear {{ coordinator_name }},</p>
            <p>The evaluation deadline for call <strong>{{ call_code }}</strong> ({{ call_title }}) has passed and there are <strong>{{ pending_count }}</strong> evaluation(s) still pending.</p>
            <div class="info-box">
                <p><strong>Evaluation Deadline:</strong> {{ deadline|date:"F d, Y" }}</p>
                <p><strong>Pending Evaluations:</strong> {{ pending_count }}</p>
            </div>
            <p><strong>Pending evaluations:</strong></p>
            <pre>{{ pending_evaluations }}</pre>
            <p><strong>What has been done:</strong></p>
            <ul>
                <li>The evaluators listed above have been notified that their evaluations are overdue</li>
                <li>Evaluators have a <strong>1-week grace period</strong> to submit their evaluations</li>
                <li>After the grace period, the evaluation forms will be automatically locked</li>
            </ul>
            <p><strong>What you can do:</strong></p>
            <ul>
                <li>Contact overdue evaluators directly if needed</li>
                <li>If you need to extend the deadline, edit the call dates from <strong>Dashboard &gt; Manage Call</strong>. Extending the evaluation deadline automatically resets the grace period for all evaluators.</li>
            </ul>
            <p>Best regards,<br>The ReDIB COA Team</p>
        </div>
        <div class="footer">
            <p>This is an automated notification from the ReDIB COA Portal.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''Dear {{ coordinator_name }},

The evaluation deadline for call {{ call_code }} ({{ call_title }}) has passed and there are {{ pending_count }} evaluation(s) still pending.

Evaluation Deadline: {{ deadline|date:"F d, Y" }}
Pending Evaluations: {{ pending_count }}

Pending evaluations:
{{ pending_evaluations }}

What has been done:
- The evaluators listed above have been notified that their evaluations are overdue
- Evaluators have a 1-week grace period to submit their evaluations
- After the grace period, the evaluation forms will be automatically locked

What you can do:
- Contact overdue evaluators directly if needed
- If you need to extend the deadline, edit the call dates from Dashboard > Manage Call. Extending the evaluation deadline automatically resets the grace period for all evaluators.

Best regards,
The ReDIB COA Team

---
This is an automated notification from the ReDIB COA Portal.''',
                'available_variables': '''
{
    "coordinator_name": "Full name of the coordinator",
    "call_code": "Call code",
    "call_title": "Call title",
    "deadline": "Evaluation deadline (datetime object)",
    "pending_count": "Number of pending evaluations",
    "pending_evaluations": "Formatted list of pending evaluations with evaluator info"
}
                '''
            },
            {
                'template_type': 'coordinator_evaluations_locked',
                'subject': 'ReDIB COA: Evaluators Locked Out - Call {{ call_code }}',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #c0392b; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
        .danger-box { background-color: #fdedec; border-left: 4px solid #c0392b; padding: 15px; margin: 15px 0; }
        pre { background-color: #f0f0f0; padding: 10px; border-radius: 4px; white-space: pre-wrap; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Evaluator Lockout - Action Required</p>
        </div>
        <div class="content">
            <p>Dear {{ coordinator_name }},</p>
            <p>The 1-week grace period for overdue evaluations in call <strong>{{ call_code }}</strong> ({{ call_title }}) has expired. <strong>{{ pending_count }}</strong> evaluation(s) remain incomplete and the evaluators have been <strong>locked out</strong>.</p>
            <div class="danger-box">
                <p><strong>Evaluation Deadline:</strong> {{ deadline|date:"F d, Y" }}</p>
                <p><strong>Grace Period Expired:</strong> {{ days_overdue }} days past deadline</p>
                <p><strong>Locked Evaluations:</strong> {{ pending_count }}</p>
            </div>
            <p><strong>Still pending evaluations:</strong></p>
            <pre>{{ pending_evaluations }}</pre>
            <p><strong>Action Required:</strong></p>
            <ul>
                <li>The evaluators above can no longer submit their evaluations</li>
                <li>To unlock evaluators, extend the evaluation deadline by editing the call from <strong>Dashboard &gt; Manage Call</strong></li>
                <li>Extending the deadline will automatically reset the grace period</li>
                <li>Alternatively, you may proceed with only the completed evaluations</li>
            </ul>
            <p>Best regards,<br>The ReDIB COA Team</p>
        </div>
        <div class="footer">
            <p>This is an automated notification from the ReDIB COA Portal.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''Dear {{ coordinator_name }},

The 1-week grace period for overdue evaluations in call {{ call_code }} ({{ call_title }}) has expired. {{ pending_count }} evaluation(s) remain incomplete and the evaluators have been LOCKED OUT.

Evaluation Deadline: {{ deadline|date:"F d, Y" }}
Grace Period Expired: {{ days_overdue }} days past deadline
Locked Evaluations: {{ pending_count }}

Still pending evaluations:
{{ pending_evaluations }}

Action Required:
- The evaluators above can no longer submit their evaluations
- To unlock evaluators, extend the evaluation deadline by editing the call from Dashboard > Manage Call
- Extending the deadline will automatically reset the grace period
- Alternatively, you may proceed with only the completed evaluations

Best regards,
The ReDIB COA Team

---
This is an automated notification from the ReDIB COA Portal.''',
                'available_variables': '''
{
    "coordinator_name": "Full name of the coordinator",
    "call_code": "Call code",
    "call_title": "Call title",
    "deadline": "Evaluation deadline (datetime object)",
    "days_overdue": "Number of days past the deadline",
    "pending_count": "Number of pending evaluations",
    "pending_evaluations": "Formatted list of pending evaluations with evaluator info"
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
                Average Score: {{ average_score }} / 12.00
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

AVERAGE SCORE: {{ average_score }} / 12.00

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
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #27ae60; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
        .info-box { background-color: #d5f4e6; border-left: 4px solid #27ae60; padding: 15px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Application Accepted</p>
        </div>

        <div class="content">
            <p>Dear {{ applicant_name }},</p>

            <p>Congratulations! Your application <strong>{{ application_code }}</strong> for call {{ call_code }} has been <strong>ACCEPTED</strong>.</p>

            <div class="info-box">
                <p><strong>Final Score:</strong> {{ final_score }}/12.00</p>
                <p><strong>Hours Approved:</strong> {{ hours_approved }} hours</p>
            </div>

            {% if resolution_comments %}<p>{{ resolution_comments }}</p>{% endif %}

            {% if acceptance_deadline %}
            <h3>Next Step: Accept or Decline Access</h3>
            <p>You have until <strong>{{ acceptance_deadline|date:"F d, Y" }}</strong> to respond.</p>

            <p style="text-align: center;">
                <a href="{{ accept_url }}" style="display:inline-block;padding:12px 24px;background-color:#198754;color:#ffffff;text-decoration:none;border-radius:6px;font-weight:bold;">Accept or Decline Access</a>
            </p>

            <p><small>Or copy this link into your browser: {{ accept_url }}</small></p>

            <p><em>If you do not respond by the deadline, your access will expire automatically.</em></p>
            {% else %}
            <p>You have already accepted this access, so there is nothing further
            to confirm. Your node coordinator will be in touch to arrange dates —
            see the separate hand-off email for the equipment and contact details.</p>
            {% endif %}

            <p>Best regards,<br>
            ReDIB COA Team</p>
        </div>

        <div class="footer">
            <p>This is an automated message from the ReDIB COA Portal.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''Application Accepted

Dear {{ applicant_name }},

Congratulations! Your application {{ application_code }} for call {{ call_code }} has been ACCEPTED.

Final Score: {{ final_score }}/12.00
Hours Approved: {{ hours_approved }} hours

{{ resolution_comments }}

{% if acceptance_deadline %}Next Step: Accept or Decline Access
You have until {{ acceptance_deadline|date:"F d, Y" }} to respond.

Please visit the following link to accept or decline:
{{ accept_url }}

If you do not respond by the deadline, your access will expire automatically.
{% else %}You have already accepted this access, so there is nothing further to
confirm. Your node coordinator will be in touch to arrange dates - see the
separate hand-off email for the equipment and contact details.
{% endif %}

Best regards,
ReDIB COA Team''',
                'available_variables': '''Variables: applicant_name, application_code, call_code, final_score, resolution, hours_approved, resolution_comments, resolution_date, acceptance_deadline, days_to_respond, accept_url'''
            },
            {
                'template_type': 'resolution_pending',
                'subject': 'ReDIB COA: Application {{ application_code }} Placed on Waitlist',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #f39c12; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .button { display: inline-block; padding: 12px 24px; background-color: #f39c12; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .info-box { background-color: #fef5e7; border-left: 4px solid #f39c12; padding: 15px; margin: 15px 0; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Application Placed on Waitlist</p>
        </div>

        <div class="content">
            <p>Dear {{ applicant_name }},</p>

            <p>Your application <strong>{{ application_code }}</strong> for call {{ call_code }} has been placed on the <strong>waitlist</strong>. You will be notified by the node coordinator if time becomes available.</p>

            <div class="info-box">
                <p><strong>Final Score:</strong> {{ final_score }}/12.00</p>
                {% if acceptance_deadline %}
                <p><strong>Response deadline:</strong> {{ acceptance_deadline|date:"F d, Y" }} ({{ days_to_respond }} days remaining)</p>
                {% endif %}
            </div>

            {% if resolution_comments %}<p>{{ resolution_comments }}</p>{% endif %}

            <p>Please confirm whether you would like to stay on the waitlist or decline. If you accept, no action is required now — a node coordinator will contact you directly if a slot opens. If you decline, your spot will be released to the next applicant.</p>

            {% if accept_url %}
            <p style="text-align: center;">
                <a href="{{ accept_url }}" class="button">Accept or Decline Waitlist Offer</a>
            </p>
            {% endif %}

            <p>If you do not respond by the deadline, your waitlist offer will expire automatically.</p>

            <p>Best regards,<br>
            ReDIB COA Team</p>
        </div>

        <div class="footer">
            <p>This is an automated message from the ReDIB COA Portal.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''Application Placed on Waitlist

Dear {{ applicant_name }},

Your application {{ application_code }} for call {{ call_code }} has been placed on the waitlist. You will be notified by the node coordinator if time becomes available.

Final Score: {{ final_score }}/12.00
{% if acceptance_deadline %}Response deadline: {{ acceptance_deadline|date:"F d, Y" }} ({{ days_to_respond }} days remaining){% endif %}

{% if resolution_comments %}{{ resolution_comments }}{% endif %}

Please confirm whether you would like to stay on the waitlist or decline. If you accept, no action is required now — a node coordinator will contact you directly if a slot opens. If you decline, your spot will be released to the next applicant.

{% if accept_url %}Accept or Decline Waitlist Offer: {{ accept_url }}{% endif %}

If you do not respond by the deadline, your waitlist offer will expire automatically.

Best regards,
ReDIB COA Team

---
This is an automated message from the ReDIB COA Portal.
Please do not reply to this email.''',
                'available_variables': '''Variables: applicant_name, application_code, call_code, final_score, resolution, hours_granted, resolution_comments, resolution_date, acceptance_deadline, days_to_respond, accept_url'''
            },
            {
                'template_type': 'resolution_rejected',
                'subject': 'ReDIB COA: Application {{ application_code }} Resolution',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #c0392b; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
        .info-box { background-color: #fdedec; border-left: 4px solid #c0392b; padding: 15px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Application Resolution</p>
        </div>

        <div class="content">
            <p>Dear {{ applicant_name }},</p>

            <p>Your application <strong>{{ application_code }}</strong> for call {{ call_code }} was not accepted at this time.</p>

            <div class="info-box">
                <p><strong>Final Score:</strong> {{ final_score }}/12.00</p>
            </div>

            {% if resolution_comments %}<p><strong>Reviewer Comments:</strong> {{ resolution_comments }}</p>{% endif %}

            <p>Thank you for your participation. However the evaluation score was below the threshold for this call period. We encourage you to watch for future calls on our website at redib.net and to apply again if possible. If you have further questions please email {{ contact_email }}.</p>

            <p>Best regards,<br>
            ReDIB COA Team</p>
        </div>

        <div class="footer">
            <p>This is an automated message from the ReDIB COA Portal.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''Application Resolution

Dear {{ applicant_name }},

Your application {{ application_code }} for call {{ call_code }} was not accepted at this time.

Final Score: {{ final_score }}/12.00

{% if resolution_comments %}Reviewer Comments: {{ resolution_comments }}{% endif %}

Thank you for your participation. However the evaluation score was below the threshold for this call period. We encourage you to watch for future calls on our website at redib.net and to apply again if possible. If you have further questions please email {{ contact_email }}.

Best regards,
ReDIB COA Team''',
                'available_variables': '''Variables: applicant_name, application_code, call_code, final_score, resolution, hours_granted, resolution_comments, resolution_date'''
            },
            # Phase 7: Acceptance & Handoff templates
            {
                'template_type': 'handoff_notification',
                'subject': 'ReDIB COA Access Approved - Application {{ application_code }} Ready for Scheduling',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #27ae60; color: white; padding: 20px; text-align: center; }
        .header h1 { margin-bottom: 5px; }
        .header p { margin-top: 0; font-size: 16px; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
        .info-box { background-color: #d5f4e6; border-left: 4px solid #27ae60; padding: 15px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Access Approved</h1>
            <p>Ready for Scheduling</p>
        </div>

        <div class="content">
            <p>Dear {{ applicant_name }} and {{ node_names }} Team,</p>

            <p>This is to confirm that COA application <strong>{{ application_code }}</strong> has been approved by the evaluation committee and accepted by the applicant.</p>

            <h3>APPLICATION DETAILS</h3>
            <ul>
                <li><strong>Application Code:</strong> {{ application_code }}</li>
                <li><strong>Applicant:</strong> {{ applicant_name }} ({{ applicant_entity }})</li>
                <li><strong>Email:</strong> {{ applicant_email }}</li>
                <li><strong>Phone:</strong> {{ applicant_phone }}</li>
                <li><strong>Project:</strong> {{ project_name }}</li>
                <li><strong>Brief Description:</strong> {{ brief_description }}</li>
            </ul>

            <h3>APPROVED ACCESS</h3>
            <p><strong>Service Modality:</strong> {{ service_modality }}</p>
            {% for access in requested_access %}
            <p>- <strong>{{ access.node_name }}</strong> / {{ access.equipment_name }}: requested {{ access.hours_requested }} h, approved {{ access.hours_approved|default:"—" }} h</p>
            {% endfor %}

            <h3>NEXT STEPS</h3>
            <p>Please coordinate directly to schedule the access time. The applicant and node team should arrange mutually convenient dates for the requested work.</p>

            <p>For questions, contact: {{ contact_email }}</p>

            <p>Best regards,<br>
            ReDIB COA Team</p>
        </div>

        <div class="footer">
            <p>This is an automated notification from the ReDIB COA Portal.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''ReDIB COA Access Approved - Ready for Scheduling

Dear {{ applicant_name }} and {{ node_names }} Team,

This is to confirm that COA application {{ application_code }} has been approved by the evaluation committee and accepted by the applicant.

APPLICATION DETAILS
- Application Code: {{ application_code }}
- Applicant: {{ applicant_name }} ({{ applicant_entity }})
- Email: {{ applicant_email }}
- Phone: {{ applicant_phone }}
- Project: {{ project_name }}
- Brief Description: {{ brief_description }}

APPROVED ACCESS
Service Modality: {{ service_modality }}
{% for access in requested_access %}- {{ access.node_name }} / {{ access.equipment_name }}: requested {{ access.hours_requested }} h, approved {{ access.hours_approved|default:"—" }} h
{% endfor %}

NEXT STEPS
Please coordinate directly to schedule the access time. The applicant and node team should arrange mutually convenient dates for the requested work.

For questions, contact: {{ contact_email }}

Best regards,
ReDIB COA Team

---
This is an automated notification from the ReDIB COA Portal.
Please do not reply to this email.''',
                'available_variables': '''Variables: applicant_name, applicant_entity, applicant_email, applicant_phone, application_code, project_name, brief_description, service_modality, node_names, requested_access (list)'''
            },
            {
                'template_type': 'acceptance_expired',
                'subject': 'ReDIB COA: Application {{ application_code }} has been closed',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #c0392b; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
        .warning-box { background-color: #fdedec; border-left: 4px solid #c0392b; padding: 15px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Application Closed</p>
        </div>

        <div class="content">
            <p>Dear {{ applicant_name }},</p>

            {% if is_waitlist %}
            <p>Your COA application <strong>{{ application_code }}</strong> has been closed. It was on the waiting list, and we did not hear back from you before the response deadline.</p>
            {% else %}
            <p>Your COA application <strong>{{ application_code }}</strong> has been closed. Access was offered to you, and we did not hear back from you before the response deadline.</p>
            {% endif %}

            <div class="warning-box">
                <p><strong>Deadline was:</strong> {{ deadline }}</p>
            </div>

            <p>Your node coordinator has reviewed the application and marked it as expired. {% if is_waitlist %}You are no longer on the waiting list for this call.{% else %}The hours reserved for your project have been released.{% endif %}</p>

            <p>If you would like to request access in the future, please apply during the next open call period.</p>

            <p>If this is not what you expected &mdash; for instance if you did reply and it did not reach us &mdash; please get in touch at {{ contact_email }}. This can be put right.</p>

            <p>Best regards,<br>
            ReDIB COA Team</p>
        </div>

        <div class="footer">
            <p>This is an automated message from the ReDIB COA Portal.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''Application Closed - Response Deadline Passed

Dear {{ applicant_name }},

{% if is_waitlist %}Your COA application {{ application_code }} has been closed. It was on the waiting list, and we did not hear back from you before the response deadline.{% else %}Your COA application {{ application_code }} has been closed. Access was offered to you, and we did not hear back from you before the response deadline.{% endif %}

Deadline was: {{ deadline }}

Your node coordinator has reviewed the application and marked it as expired. {% if is_waitlist %}You are no longer on the waiting list for this call.{% else %}The hours reserved for your project have been released.{% endif %}

If you would like to request access in the future, please apply during the next open call period.

If this is not what you expected - for instance if you did reply and it did not reach us - please get in touch at {{ contact_email }}. This can be put right.

Best regards,
ReDIB COA Team

---
This message was sent from the ReDIB COA Portal.
Please do not reply to this email.''',
                'available_variables': '''Variables: applicant_name, application_code, deadline, is_waitlist (True for a waitlisted 'pending' application)'''
            },
            {
                'template_type': 'publication_followup',
                'subject': 'ReDIB COA - Publication Follow-up for Application {{ application_code }}',
                'text_content': '''Dear {{ applicant_name }},

We hope your research using ReDIB COA resources was successful!

It has been approximately 6 months since your access was granted for application {{ application_code }} - "{{ project_name }}".

We would greatly appreciate it if you could report any publications that have resulted from your use of ReDIB equipment. This information helps us demonstrate the impact of ReDIB resources and secure continued funding.

If your work has resulted in publications, please log in to the ReDIB portal and submit publication details:

{{ publication_url }}

IMPORTANT REMINDER:
Per regulatory requirements, all publications must acknowledge ReDIB support with the following text:

"{{ acknowledgment_text }}"

If you have not yet published results or if your research is still ongoing, you can disregard this message for now. We may follow up again in the future.

Thank you for using ReDIB COA resources and for helping us track the impact of our services!

Best regards,
The ReDIB COA Team

---
This is an automated reminder from the ReDIB COA Management System.''',
                'html_content': '''<html><body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">

<h2 style="color: #2c5282;">ReDIB COA - Publication Follow-up</h2>

<p>Dear <strong>{{ applicant_name }}</strong>,</p>

<p>We hope your research using ReDIB COA resources was successful!</p>

<p>It has been approximately <strong>6 months</strong> since your access was granted for application <strong>{{ application_code }}</strong> - "{{ project_name }}".</p>

<p>We would greatly appreciate it if you could <strong>report any publications</strong> that have resulted from your use of ReDIB equipment. This information helps us demonstrate the impact of ReDIB resources and secure continued funding.</p>

<p>If your work has resulted in publications, please <a href="{{ publication_url }}" style="color: #2c5282; text-decoration: underline;">log in to the ReDIB portal and submit publication details</a>.</p>

<div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0;">
    <h3 style="margin-top: 0; color: #92400e;">IMPORTANT REMINDER:</h3>
    <p style="margin-bottom: 0;">Per regulatory requirements, all publications must acknowledge ReDIB support with the following text:</p>
    <p style="font-style: italic; margin-top: 10px; padding-left: 10px; border-left: 3px solid #d97706;">
        "{{ acknowledgment_text }}"
    </p>
</div>

<p><em>If you have not yet published results or if your research is still ongoing, you can disregard this message for now. We may follow up again in the future.</em></p>

<p>Thank you for using ReDIB COA resources and for helping us track the impact of our services!</p>

<p>Best regards,<br>
<strong>The ReDIB COA Team</strong></p>

<hr style="border: none; border-top: 1px solid #e2e8f0; margin: 30px 0;">

<p style="font-size: 12px; color: #718096;">This is an automated reminder from the ReDIB COA Management System.</p>

</body></html>''',
                'available_variables': '''Variables: applicant_name, application_code, project_name, handoff_date, acknowledgment_text, publication_url'''
            },
            {
                'template_type': 'call_published',
                'subject': 'ReDIB COA: New Call {{ call_code }} Now Open',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #2c3e50; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .button { display: inline-block; padding: 12px 24px; background-color: #3498db; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .info-box { background-color: #e8f4f8; border-left: 4px solid #3498db; padding: 15px; margin: 15px 0; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>New Call for Applications</p>
        </div>
        <div class="content">
            <p>Dear colleague,</p>
            <p>A new ReDIB Competitive Open Access call has been published and is now accepting applications.</p>
            <div class="info-box">
                <p><strong>Call Code:</strong> {{ call_code }}</p>
                <p><strong>Title:</strong> {{ call_title }}</p>
                <p><strong>Submission deadline:</strong> {{ submission_end }}</p>
            </div>
            <p style="text-align: center;">
                <a href="{{ call_url }}" class="button">View Call &amp; Apply</a>
            </p>
            <p>You are receiving this notification because your account is set to receive new-call announcements. You can update this preference in your profile.</p>
            <p>Best regards,<br>
            The ReDIB COA Team</p>
        </div>
        <div class="footer">
            <p>This is an automated message from the ReDIB COA Portal.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''Dear colleague,

A new ReDIB Competitive Open Access call has been published and is now accepting applications.

Call Details:
- Call Code: {{ call_code }}
- Title: {{ call_title }}
- Submission deadline: {{ submission_end }}

View Call & Apply:
{{ call_url }}

You are receiving this notification because your account is set to receive new-call announcements. You can update this preference in your profile.

Best regards,
The ReDIB COA Team

---
This is an automated message from the ReDIB COA Portal.
Please do not reply to this email.''',
                'available_variables': '''Variables: call_code, call_title, submission_end, call_url'''
            },
            {
                'template_type': 'feasibility_reminder',
                'subject': 'ReDIB COA: Feasibility review pending for {{ application_code }}',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #e67e22; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .info-box { background-color: #fef3e6; border-left: 4px solid #e67e22; padding: 15px; margin: 15px 0; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Feasibility Review Reminder</p>
        </div>
        <div class="content">
            <p>Dear {{ reviewer_name }},</p>
            <p>A feasibility review is still pending for an application at your node and has been waiting for {{ days_pending }} days. Please review it as soon as possible so the application can proceed.</p>
            <div class="info-box">
                <p><strong>Application Code:</strong> {{ application_code }}</p>
                <p><strong>Project Summary:</strong> {{ application_title }}</p>
                <p><strong>Your Node:</strong> {{ node_name }}</p>
                <p><strong>Call evaluation deadline:</strong> {{ deadline }}</p>
            </div>
            <p>Sign in to the portal to open the feasibility queue and complete your review.</p>
            <p>Best regards,<br>
            The ReDIB COA Team</p>
        </div>
        <div class="footer">
            <p>This is an automated reminder from the ReDIB COA Portal.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''Dear {{ reviewer_name }},

A feasibility review is still pending for an application at your node and has been waiting for {{ days_pending }} days. Please review it as soon as possible so the application can proceed.

Application Details:
- Application Code: {{ application_code }}
- Project Summary: {{ application_title }}
- Your Node: {{ node_name }}
- Call evaluation deadline: {{ deadline }}

Sign in to the portal to open the feasibility queue and complete your review.

Best regards,
The ReDIB COA Team

---
This is an automated reminder from the ReDIB COA Portal.
Please do not reply to this email.''',
                'available_variables': '''Variables: reviewer_name, application_code, application_title, node_name, days_pending, deadline'''
            },
            {
                'template_type': 'acceptance_reminder',
                'subject': 'ReDIB COA: {% if is_waitlist %}Reminder to respond to your waiting-list offer for {{ application_code }}{% else %}Reminder to accept access for {{ application_code }}{% endif %}',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #e67e22; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .button { display: inline-block; padding: 12px 24px; background-color: #27ae60; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .info-box { background-color: #fef3e6; border-left: 4px solid #e67e22; padding: 15px; margin: 15px 0; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Action Required: Accept or Decline Your Access Grant</p>
        </div>
        <div class="content">
            <p>Dear {{ applicant_name }},</p>
            {% if is_waitlist %}
            <p>This is a reminder that your application has been placed on the <strong>waiting list</strong> and awaits your formal response. You have <strong>{{ days_remaining }} days</strong> remaining to tell us whether you would like to stay on it.</p>
            {% else %}
            <p>This is a reminder that your application has been approved and awaits your formal acceptance. You have <strong>{{ days_remaining }} days</strong> remaining to respond.</p>
            {% endif %}
            <div class="info-box">
                <p><strong>Application Code:</strong> {{ application_code }}</p>
                <p><strong>Response deadline:</strong> {{ deadline }}</p>
            </div>
            <p style="text-align: center;">
                <a href="{{ acceptance_url }}" class="button">Accept or Decline</a>
            </p>
            {% if is_waitlist %}
            <p>Accepting keeps you on the waiting list; a node coordinator will contact you if a slot opens. If you do not respond by the deadline this link closes, and your node coordinator will be in touch to agree what happens next.</p>
            {% else %}
            <p>If you do not respond by the deadline this link closes, and your node coordinator will be in touch to agree what happens next.</p>
            {% endif %}
            <p>Best regards,<br>
            The ReDIB COA Team</p>
        </div>
        <div class="footer">
            <p>This is an automated reminder from the ReDIB COA Portal.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''Dear {{ applicant_name }},

{% if is_waitlist %}This is a reminder that your application has been placed on the waiting list and awaits your formal response. You have {{ days_remaining }} days remaining to tell us whether you would like to stay on it.{% else %}This is a reminder that your application has been approved and awaits your formal acceptance. You have {{ days_remaining }} days remaining to respond.{% endif %}

Application Details:
- Application Code: {{ application_code }}
- Response deadline: {{ deadline }}

Accept or Decline:
{{ acceptance_url }}

{% if is_waitlist %}Accepting keeps you on the waiting list; a node coordinator will contact you if a slot opens. If you do not respond by the deadline this link closes, and your node coordinator will be in touch to agree what happens next.{% else %}If you do not respond by the deadline this link closes, and your node coordinator will be in touch to agree what happens next.{% endif %}

Best regards,
The ReDIB COA Team

---
This is an automated reminder from the ReDIB COA Portal.
Please do not reply to this email.''',
                'available_variables': '''Variables: applicant_name, application_code, deadline, days_remaining, acceptance_url, is_waitlist (True for a waitlisted 'pending' application)'''
            },
            {
                'template_type': 'feasibility_consult_request',
                'subject': 'ReDIB COA: Pre-submission consult requested for {{ node_name }}',
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
        .info-box { background-color: #fff7e0; border-left: 4px solid #e6a23c; padding: 15px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Pre-submission consult requested</p>
        </div>

        <div class="content">
            <p>Dear {{ coordinator_name }},</p>

            <p>An applicant is preparing a COA proposal for call <strong>{{ call_code }}</strong> and has asked for a consult with your node before submitting. They have not yet confirmed technical feasibility and would like to discuss their request with you.</p>

            <div class="info-box">
                <p><strong>Applicant:</strong> {{ applicant_name }}</p>
                <p><strong>Contact:</strong> {{ applicant_email }}{% if applicant_phone %} &middot; {{ applicant_phone }}{% endif %}</p>
                <p><strong>Application (draft):</strong> {{ application_code }}</p>
                <p><strong>Your node:</strong> {{ node_name }}</p>
                <p><strong>Equipment requested at your node:</strong> {{ equipment_list }}</p>
                <p><strong>Call submission deadline:</strong> {{ submission_end }}</p>
            </div>

            <p>Please reach out to the applicant directly to discuss feasibility. You can review their draft application in the portal:</p>

            <p style="text-align: center;">
                <a href="{{ application_url }}" class="button">View draft application</a>
            </p>

            <p>The applicant has been told that you will contact them. This is a pre-submission consult only &mdash; no formal feasibility review has been triggered.</p>

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
Dear {{ coordinator_name }},

An applicant is preparing a COA proposal for call {{ call_code }} and has asked for a consult with your node before submitting. They have not yet confirmed technical feasibility and would like to discuss their request with you.

Applicant: {{ applicant_name }}
Contact: {{ applicant_email }}{% if applicant_phone %} - {{ applicant_phone }}{% endif %}
Application (draft): {{ application_code }}
Your node: {{ node_name }}
Equipment requested at your node: {{ equipment_list }}
Call submission deadline: {{ submission_end }}

Please reach out to the applicant directly to discuss feasibility. You can review their draft application in the portal:

{{ application_url }}

The applicant has been told that you will contact them. This is a pre-submission consult only - no formal feasibility review has been triggered.

Best regards,
The ReDIB COA Team

---
This is an automated message from the ReDIB COA Portal.
Please do not reply to this email.
                ''',
                'available_variables': '''
{
    "coordinator_name": "Full name of the node coordinator (recipient)",
    "applicant_name": "Full name of the applicant",
    "applicant_email": "Applicant contact email",
    "applicant_phone": "Applicant contact phone (may be blank)",
    "application_code": "Application code (draft)",
    "node_name": "Name of the node receiving this consult",
    "equipment_list": "Comma-separated list of equipment at this node requested by the applicant",
    "application_url": "Absolute URL to the application detail page",
    "call_code": "Code of the call (e.g., COA-2026-01)",
    "submission_end": "Formatted submission deadline of the call"
}
                '''
            },
            {
                'template_type': 'call_announced',
                'subject': 'ReDIB COA: Upcoming Call {{ call_code }} - opens {{ submission_start }}',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #2c3e50; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .button { display: inline-block; padding: 12px 24px; background-color: #3498db; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .info-box { background-color: #e8f4f8; border-left: 4px solid #3498db; padding: 15px; margin: 15px 0; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Upcoming Call for Applications</p>
        </div>
        <div class="content">
            <p>Dear colleague,</p>
            <p>A new ReDIB Competitive Open Access call has been announced. It is not open yet &mdash; we are letting you know in advance so you have time to prepare.</p>
            <div class="info-box">
                <p><strong>Call Code:</strong> {{ call_code }}</p>
                <p><strong>Title:</strong> {{ call_title }}</p>
                <p><strong>Opens:</strong> {{ submission_start }}</p>
                <p><strong>Submission deadline:</strong> {{ submission_end }}</p>
            </div>
            <p>You can already see the full list of available equipment on the call page. If you would like to discuss whether a particular instrument suits your study, you can request a consult with the node that operates it &mdash; no account and no application needed.</p>
            <p style="text-align: center;">
                <a href="{{ call_url }}" class="button">View Call Details</a>
            </p>
            <p>We will email you again on {{ submission_start }} when the call opens for submissions.</p>
            <p>You are receiving this notification because your account is set to receive new-call announcements. You can update this preference in your profile.</p>
            <p>Best regards,<br>
            The ReDIB COA Team</p>
        </div>
        <div class="footer">
            <p>This is an automated message from the ReDIB COA Portal.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''Dear colleague,

A new ReDIB Competitive Open Access call has been announced. It is not open yet - we are letting you know in advance so you have time to prepare.

Call Details:
- Call Code: {{ call_code }}
- Title: {{ call_title }}
- Opens: {{ submission_start }}
- Submission deadline: {{ submission_end }}

You can already see the full list of available equipment on the call page. If you would like to discuss whether a particular instrument suits your study, you can request a consult with the node that operates it - no account and no application needed.

View Call Details:
{{ call_url }}

We will email you again on {{ submission_start }} when the call opens for submissions.

You are receiving this notification because your account is set to receive new-call announcements. You can update this preference in your profile.

Best regards,
The ReDIB COA Team

---
This is an automated message from the ReDIB COA Portal.
Please do not reply to this email.''',
                'available_variables': '''Variables: call_code, call_title, submission_start, submission_end, call_url'''
            },
            {
                'template_type': 'equipment_consult_request',
                'subject': 'ReDIB COA: Equipment consult requested for {{ node_name }} ({{ call_code }})',
                'html_content': '''<!DOCTYPE html>
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
        .info-box { background-color: #fff7e0; border-left: 4px solid #e6a23c; padding: 15px; margin: 15px 0; }
        .message-box { background-color: #ffffff; border: 1px solid #ddd; padding: 15px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Equipment consult requested</p>
        </div>

        <div class="content">
            <p>Dear {{ coordinator_name }},</p>

            {% if no_node_coordinator %}
            <p>A visitor asked for a consult about equipment on call <strong>{{ call_code }}</strong>, but the node(s) below have no active coordinator on file. You are receiving this as the ReDIB coordinator so the request does not go unanswered.</p>
            {% else %}
            <p>Someone has asked for a consult about equipment at your node, from the public page of call <strong>{{ call_code }}</strong> ({{ call_status }}). They have not applied &mdash; this is an informal enquiry before the application stage.</p>
            {% endif %}

            <div class="info-box">
                <p><strong>Requester:</strong> {{ requester_name }}</p>
                <p><strong>Contact:</strong> {{ requester_email }}{% if requester_phone %} &middot; {{ requester_phone }}{% endif %}</p>
                {% if requester_organization %}<p><strong>Institution:</strong> {{ requester_organization }}</p>{% endif %}
                <p><strong>Node:</strong> {{ node_name }}</p>
                <p><strong>Equipment they asked about:</strong> {{ equipment_list }}</p>
                <p><strong>Call:</strong> {{ call_code }} &mdash; {{ call_title }}</p>
                <p><strong>Submission window:</strong> {{ submission_start }} to {{ submission_end }}</p>
            </div>

            {% if message %}
            <div class="message-box">
                <p><strong>Their message:</strong></p>
                <p>{{ message|linebreaksbr }}</p>
            </div>
            {% endif %}

            <p>Please reply to them directly at <a href="mailto:{{ requester_email }}">{{ requester_email }}</a>. They have been told that the node will get in touch.</p>

            <p style="text-align: center;">
                <a href="{{ call_url }}" class="button">View the call</a>
            </p>

            <p>All consult requests for this call are listed here: <a href="{{ consult_requests_url }}">{{ consult_requests_url }}</a></p>

            <p>No application, feasibility review, or other workflow step has been triggered by this request.</p>

            <p>Best regards,<br>
            The ReDIB COA Team</p>
        </div>

        <div class="footer">
            <p>This is an automated message from the ReDIB COA Portal.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''Dear {{ coordinator_name }},

{% if no_node_coordinator %}A visitor asked for a consult about equipment on call {{ call_code }}, but the node(s) below have no active coordinator on file. You are receiving this as the ReDIB coordinator so the request does not go unanswered.{% else %}Someone has asked for a consult about equipment at your node, from the public page of call {{ call_code }} ({{ call_status }}). They have not applied - this is an informal enquiry before the application stage.{% endif %}

Requester: {{ requester_name }}
Contact: {{ requester_email }}{% if requester_phone %} - {{ requester_phone }}{% endif %}
{% if requester_organization %}Institution: {{ requester_organization }}
{% endif %}Node: {{ node_name }}
Equipment they asked about: {{ equipment_list }}
Call: {{ call_code }} - {{ call_title }}
Submission window: {{ submission_start }} to {{ submission_end }}
{% if message %}
Their message:
{{ message }}
{% endif %}
Please reply to them directly at {{ requester_email }}. They have been told that the node will get in touch.

View the call:
{{ call_url }}

All consult requests for this call:
{{ consult_requests_url }}

No application, feasibility review, or other workflow step has been triggered by this request.

Best regards,
The ReDIB COA Team

---
This is an automated message from the ReDIB COA Portal.
Please do not reply to this email.''',
                'available_variables': '''
{
    "coordinator_name": "Full name of the recipient coordinator",
    "requester_name": "Name typed on the public consult form",
    "requester_email": "Contact email of the requester",
    "requester_phone": "Contact phone (may be blank)",
    "requester_organization": "Institution / company (may be blank)",
    "call_code": "Code of the call (e.g., COA-2026-01)",
    "call_title": "Title of the call",
    "call_status": "Human-readable call status (Announced / Open)",
    "node_name": "Name of the node this request concerns",
    "equipment_list": "Comma-separated equipment at this node the requester selected",
    "message": "Free-text message from the requester (may be blank)",
    "submission_start": "Call submission start date (e.g. October 01, 2026)",
    "submission_end": "Call submission deadline (e.g. October 31, 2026)",
    "call_url": "Absolute URL of the public call page",
    "consult_requests_url": "Absolute URL of the coordinator consult-request list",
    "no_node_coordinator": "True when sent to a ReDIB coordinator because the node has no active coordinator"
}
                '''
            },
            {
                'template_type': 'equipment_consult_confirmation',
                'subject': 'ReDIB COA: We received your consult request for {{ call_code }}',
                'html_content': '''<!DOCTYPE html>
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
            <p>Consult request received</p>
        </div>

        <div class="content">
            <p>Dear {{ requester_name }},</p>

            <p>Thank you for your interest in ReDIB. We have passed your enquiry to the coordinator(s) of <strong>{{ node_names }}</strong>, who will contact you directly.</p>

            <div class="info-box">
                <p><strong>Call:</strong> {{ call_code }} &mdash; {{ call_title }}</p>
                <p><strong>Equipment you asked about:</strong> {{ equipment_list }}</p>
                <p><strong>Submission window:</strong> {{ submission_start }} to {{ submission_end }}</p>
            </div>

            {% if message %}
            <p><strong>Your message:</strong></p>
            <p>{{ message|linebreaksbr }}</p>
            {% endif %}

            <p>This was an informal enquiry: no application has been started, and you are under no obligation to submit one. If you do decide to apply, you can do so from the call page while the call is open.</p>

            <p style="text-align: center;">
                <a href="{{ call_url }}" class="button">View the call</a>
            </p>

            <p>If you do not hear back within a few working days, or if you have any other question, write to us at <a href="mailto:{{ contact_email }}">{{ contact_email }}</a>.</p>

            <p>Best regards,<br>
            The ReDIB COA Team</p>
        </div>

        <div class="footer">
            <p>This is an automated message from the ReDIB COA Portal.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''Dear {{ requester_name }},

Thank you for your interest in ReDIB. We have passed your enquiry to the coordinator(s) of {{ node_names }}, who will contact you directly.

Call: {{ call_code }} - {{ call_title }}
Equipment you asked about: {{ equipment_list }}
Submission window: {{ submission_start }} to {{ submission_end }}
{% if message %}
Your message:
{{ message }}
{% endif %}
This was an informal enquiry: no application has been started, and you are under no obligation to submit one. If you do decide to apply, you can do so from the call page while the call is open.

View the call:
{{ call_url }}

If you do not hear back within a few working days, or if you have any other question, write to us at {{ contact_email }}.

Best regards,
The ReDIB COA Team

---
This is an automated message from the ReDIB COA Portal.
Please do not reply to this email.''',
                'available_variables': '''
{
    "requester_name": "Name typed on the public consult form",
    "call_code": "Code of the call (e.g., COA-2026-01)",
    "call_title": "Title of the call",
    "node_names": "Comma-separated names of the nodes that were notified",
    "equipment_list": "Equipment the requester selected, with node names",
    "message": "Free-text message from the requester (may be blank)",
    "submission_start": "Call submission start date (e.g. October 01, 2026)",
    "submission_end": "Call submission deadline (e.g. October 31, 2026)",
    "call_url": "Absolute URL of the public call page",
    "contact_email": "ReDIB contact address (settings.CONTACT_EMAIL)"
}
                '''
            },
            {
                'template_type': 'waitlist_digest',
                'subject': 'ReDIB COA: Waitlisted applications need a decision',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #e67e22; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .button { display: inline-block; padding: 12px 24px; background-color: #27ae60; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .info-box { background-color: #fef3e6; border-left: 4px solid #e67e22; padding: 15px; margin: 15px 0; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Waitlisted Applications Need a Decision</p>
        </div>
        <div class="content">
            <p>Dear {{ coordinator_name }},</p>
            <p>The following applicants have accepted a waitlist offer and are still waiting to hear whether a slot has opened. For each one: if a slot is now available, promote it to Accepted; if it will not open this call, close it out as "Not Reached This Call" so it does not dangle.</p>
            {% for node in node_summaries %}
            <div class="info-box">
                <p><strong>{{ node.node_name }}</strong></p>
                {% for app in node.applications %}
                <p>&bull; {{ app.application_code }} &mdash; {{ app.applicant_name }} (waiting {{ app.days_waiting }} days)</p>
                {% endfor %}
            </div>
            {% endfor %}
            <p style="text-align: center;">
                <a href="{{ access_tracking_url }}" class="button">Open Access Tracking</a>
            </p>
            <p>Best regards,<br>
            The ReDIB COA Team</p>
        </div>
        <div class="footer">
            <p>This is an automated reminder from the ReDIB COA Portal.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''Dear {{ coordinator_name }},

The following applicants have accepted a waitlist offer and are still waiting to hear whether a slot has opened. For each one: if a slot is now available, promote it to Accepted; if it will not open this call, close it out as "Not Reached This Call" so it does not dangle.
{% for node in node_summaries %}
{{ node.node_name }}:
{% for app in node.applications %}  - {{ app.application_code }} - {{ app.applicant_name }} (waiting {{ app.days_waiting }} days)
{% endfor %}{% endfor %}
Open Access Tracking:
{{ access_tracking_url }}

Best regards,
The ReDIB COA Team

---
This is an automated reminder from the ReDIB COA Portal.
Please do not reply to this email.''',
                'available_variables': '''Variables: coordinator_name, node_summaries (list of {node_name, applications: [{application_code, applicant_name, days_waiting}]}), access_tracking_url'''
            },
            {
                'template_type': 'waitlist_not_reached',
                'subject': 'ReDIB COA: Update on your waitlisted application {{ application_code }}',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #7f8c8d; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .info-box { background-color: #ecf0f1; border-left: 4px solid #7f8c8d; padding: 15px; margin: 15px 0; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Waitlist Update</p>
        </div>
        <div class="content">
            <p>Dear {{ applicant_name }},</p>
            <p>Thank you for your patience while you were on the waiting list for <strong>{{ call_code }}</strong>. Unfortunately no slot became available before the call closed, so we are not able to offer you access this round.</p>
            <div class="info-box">
                <p><strong>Application:</strong> {{ application_code }}</p>
                <p><strong>Note from the coordinator:</strong> {{ reason }}</p>
            </div>
            <p>This is not a reflection of your application's merit — it reached the waiting list on its own strength. We encourage you to apply again in a future call.</p>
            <p>Best regards,<br>
            The ReDIB COA Team</p>
        </div>
        <div class="footer">
            <p>This is an automated message from the ReDIB COA Portal.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''Dear {{ applicant_name }},

Thank you for your patience while you were on the waiting list for {{ call_code }}. Unfortunately no slot became available before the call closed, so we are not able to offer you access this round.

Application: {{ application_code }}
Note from the coordinator: {{ reason }}

This is not a reflection of your application's merit - it reached the waiting list on its own strength. We encourage you to apply again in a future call.

Best regards,
The ReDIB COA Team

---
This is an automated message from the ReDIB COA Portal.
Please do not reply to this email.''',
                'available_variables': '''Variables: applicant_name, application_code, call_code, reason'''
            },
            {
                'template_type': 'freed_capacity_notice',
                'subject': 'ReDIB COA: Capacity freed on {{ application_code }}',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #2c3e50; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .button { display: inline-block; padding: 12px 24px; background-color: #3498db; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .info-box { background-color: #e8f4f8; border-left: 4px solid #3498db; padding: 15px; margin: 15px 0; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Equipment Hours Freed</p>
        </div>
        <div class="content">
            <p>Dear {{ coordinator_name }},</p>
            <p>Application <strong>{{ application_code }}</strong> ({{ applicant_name }}) at <strong>{{ node_name }}</strong> {% if reason == 'expired' %}auto-expired without a response{% else %}was declined by the applicant{% endif %}, freeing the following approved hours:</p>
            <div class="info-box">
                {% for line in freed_lines %}
                <p>&bull; {{ line.equipment_name }}: {{ line.hours_freed }} hours</p>
                {% endfor %}
            </div>
            <p>If you have waitlisted applicants for this equipment, consider promoting one from Access Tracking.</p>
            <p style="text-align: center;">
                <a href="{{ access_tracking_url }}" class="button">Open Access Tracking</a>
            </p>
            <p>Best regards,<br>
            The ReDIB COA Team</p>
        </div>
        <div class="footer">
            <p>This is an automated notice from the ReDIB COA Portal.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''Dear {{ coordinator_name }},

Application {{ application_code }} ({{ applicant_name }}) at {{ node_name }} {% if reason == 'expired' %}auto-expired without a response{% else %}was declined by the applicant{% endif %}, freeing the following approved hours:
{% for line in freed_lines %}  - {{ line.equipment_name }}: {{ line.hours_freed }} hours
{% endfor %}
If you have waitlisted applicants for this equipment, consider promoting one from Access Tracking.

Open Access Tracking:
{{ access_tracking_url }}

Best regards,
The ReDIB COA Team

---
This is an automated notice from the ReDIB COA Portal.
Please do not reply to this email.''',
                'available_variables': '''Variables: coordinator_name, application_code, applicant_name, node_name, reason ('expired' or 'declined'), freed_lines (list of {equipment_name, hours_freed}), application_url, access_tracking_url'''
            },
            {
                'template_type': 'completion_reminder',
                'subject': 'ReDIB COA: Log your final hours for {{ application_code }}',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #e67e22; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .button { display: inline-block; padding: 12px 24px; background-color: #27ae60; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .info-box { background-color: #fef3e6; border-left: 4px solid #e67e22; padding: 15px; margin: 15px 0; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Reminder: Report Your Final Hours</p>
        </div>
        <div class="content">
            <p>Dear {{ applicant_name }},</p>
            <p>Your access under <strong>{{ call_code }}</strong> is still open. Once your work on each piece of equipment is finished, please mark it done and enter the actual hours used so the network can close out the project.</p>
            <div class="info-box">
                <p><strong>Application:</strong> {{ application_code }}</p>
            </div>
            <p style="text-align: center;">
                <a href="{{ application_url }}" class="button">Open Your Application</a>
            </p>
            <p>Best regards,<br>
            The ReDIB COA Team</p>
        </div>
        <div class="footer">
            <p>This is an automated reminder from the ReDIB COA Portal.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''Dear {{ applicant_name }},

Your access under {{ call_code }} is still open. Once your work on each piece of equipment is finished, please mark it done and enter the actual hours used so the network can close out the project.

Application: {{ application_code }}

Open your application:
{{ application_url }}

Best regards,
The ReDIB COA Team

---
This is an automated reminder from the ReDIB COA Portal.
Please do not reply to this email.''',
                'available_variables': '''Variables: applicant_name, application_code, call_code, application_url'''
            },
            {
                'template_type': 'completion_reminder_coordinator',
                'subject': 'ReDIB COA: Check completion status for {{ application_code }}',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #e67e22; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .button { display: inline-block; padding: 12px 24px; background-color: #27ae60; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .info-box { background-color: #fef3e6; border-left: 4px solid #e67e22; padding: 15px; margin: 15px 0; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Reminder: Confirm Completion Status</p>
        </div>
        <div class="content">
            <p>Dear {{ coordinator_name }},</p>
            <p>Application <strong>{{ application_code }}</strong> ({{ applicant_name }}, {{ call_code }}) at your node is still open. Once the applicant's work is finished, confirm the equipment lines as done and check the actual hours used are recorded.</p>
            <div class="info-box">
                <p><strong>Node(s):</strong> {{ node_name }}</p>
            </div>
            <p style="text-align: center;">
                <a href="{{ application_url }}" class="button">Open Application</a>
            </p>
            <p>Best regards,<br>
            The ReDIB COA Team</p>
        </div>
        <div class="footer">
            <p>This is an automated reminder from the ReDIB COA Portal.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''Dear {{ coordinator_name }},

Application {{ application_code }} ({{ applicant_name }}, {{ call_code }}) at your node is still open. Once the applicant's work is finished, confirm the equipment lines as done and check the actual hours used are recorded.

Node(s): {{ node_name }}

Open application:
{{ application_url }}

Best regards,
The ReDIB COA Team

---
This is an automated reminder from the ReDIB COA Portal.
Please do not reply to this email.''',
                'available_variables': '''Variables: coordinator_name, application_code, applicant_name, call_code, node_name (comma-separated if the coordinator manages more than one of this application's nodes), application_url'''
            },
            {
                'template_type': 'stalled_acceptance_reminder',
                'subject': 'ReDIB COA: Reminder #{{ reminder_number }} - {{ application_code }} needs your decision',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #d35400; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .info-box { background-color: #fdf2e9; border-left: 4px solid #d35400; padding: 15px; margin: 15px 0; }
        .option-box { background-color: #ffffff; border: 1px solid #ddd; padding: 15px; margin: 15px 0; }
        .button { display: inline-block; padding: 10px 20px; color: white; text-decoration: none; border-radius: 5px; margin: 5px 0; }
        .button-expire { background-color: #c0392b; }
        .button-accept { background-color: #7f8c8d; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Unanswered Application - Reminder #{{ reminder_number }}</p>
        </div>
        <div class="content">
            <p>Dear {{ coordinator_name }},</p>

            <p>This is reminder #{{ reminder_number }}.</p>

            <p>The applicant {{ applicant_name }} has not officially acknowledged their application's status of <strong>{{ status_label }}</strong>. The deadline for them to acknowledge and accept ({{ deadline }}) has passed. They were sent several reminders before it did.</p>

            <div class="info-box">
                <p><strong>Application:</strong> {{ application_code }} &ndash; {{ call_code }}</p>
                <p><strong>Applicant:</strong> {{ applicant_name }} ({{ applicant_email }})</p>
                <p><strong>Node(s):</strong> {{ node_name }}</p>
            </div>

            <p>Unless there are extenuating circumstances the application itself should be expired. <strong>The node coordinator must act</strong> &mdash; the ReDIB coordinator is copied on this message for visibility, not to resolve it.</p>

            <p><strong>Resolution options:</strong></p>

            <div class="option-box">
                <p><strong>(1) Expire the application.</strong>{% if not is_waitlist %} Once expired, you may promote a waitlisted application to fill the space.{% endif %}</p>
                <p><a href="{{ expire_url }}" class="button button-expire">Expire {{ application_code }}</a></p>
            </div>

            <div class="option-box">
                <p><strong>(2) Override and force the acceptance on the applicant's behalf.</strong> Not recommended. You must be sure the applicant is prepared to start work within the execution window{% if is_waitlist %}, and this moves them from the waiting list to accepted{% endif %}. A reason is required and the ReDIB coordinator is notified.</p>
                <p><a href="{{ force_accept_url }}" class="button button-accept">Accept on their behalf</a></p>
            </div>

            <p>Best regards,<br>
            The ReDIB COA Team</p>
        </div>
        <div class="footer">
            <p>This reminder repeats every 3 days until the application is resolved.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''Dear {{ coordinator_name }},

This is reminder #{{ reminder_number }}.

The applicant {{ applicant_name }} has not officially acknowledged their
application's status of {{ status_label }}. The deadline for them to
acknowledge and accept ({{ deadline }}) has passed. They were sent several
reminders before it did.

Application: {{ application_code }} - {{ call_code }}
Applicant:   {{ applicant_name }} ({{ applicant_email }})
Node(s):     {{ node_name }}

Unless there are extenuating circumstances the application itself should be
expired. THE NODE COORDINATOR MUST ACT - the ReDIB coordinator is copied
on this message for visibility, not to resolve it.

Resolution options:

(1) Expire the application:
    {{ expire_url }}
{% if not is_waitlist %}    Once expired, you may promote a waitlisted application to fill the space.
{% endif %}
(2) Override and force the acceptance on the applicant's behalf:
    {{ force_accept_url }}
    Not recommended. You must be sure the applicant is prepared to start work
    within the execution window{% if is_waitlist %}, and this moves them from the
    waiting list to accepted{% endif %}. A reason is required and the ReDIB
    coordinator is notified.

Best regards,
The ReDIB COA Team

---
This reminder repeats every 3 days until the application is resolved.
Please do not reply to this email.''',
                'available_variables': '''Variables: coordinator_name, reminder_number (counted from EmailLog by distinct send day), applicant_name, applicant_email, status_label, deadline, application_code, call_code, node_name, is_waitlist, expire_url, force_accept_url, application_url'''
            },
            {
                'template_type': 'stalled_acceptance_actioned',
                'subject': 'ReDIB COA: {{ application_code }} was {{ action }} by {{ actioned_by }}',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #2c3e50; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .info-box { background-color: #ecf0f1; border-left: 4px solid #2c3e50; padding: 15px; margin: 15px 0; }
        .reason-box { background-color: #ffffff; border: 1px solid #ddd; padding: 15px; margin: 15px 0; white-space: pre-wrap; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #777; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Coordinator Action Recorded</p>
        </div>
        <div class="content">
            <p>Dear {{ coordinator_name }},</p>

            <p>Application <strong>{{ application_code }}</strong> was <strong>{{ action }}</strong> by {{ actioned_by }} on {{ actioned_on }}.</p>

            <div class="info-box">
                <p><strong>Application:</strong> {{ application_code }} &ndash; {{ call_code }}</p>
                <p><strong>Applicant:</strong> {{ applicant_name }} ({{ applicant_email }})</p>
                <p><strong>Node(s):</strong> {{ node_name }}</p>
                <p><strong>Status now:</strong> {{ status_label }}</p>
            </div>

            <p>{{ change_line }}</p>

            <p><strong>Reason given:</strong></p>
            <div class="reason-box">{{ reason }}</div>

            <p><a href="{{ application_url }}">View the application</a></p>

            <p>Best regards,<br>
            The ReDIB COA Team</p>
        </div>
        <div class="footer">
            <p>You receive this because you hold the ReDIB coordinator role. It is a record of what happened, not a request to act.</p>
            <p>Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>''',
                'text_content': '''Dear {{ coordinator_name }},

Application {{ application_code }} was {{ action }} by {{ actioned_by }} on
{{ actioned_on }}.

Application: {{ application_code }} - {{ call_code }}
Applicant:   {{ applicant_name }} ({{ applicant_email }})
Node(s):     {{ node_name }}
Status now:  {{ status_label }}

{{ change_line }}

Reason given:
{{ reason }}

View the application:
{{ application_url }}

Best regards,
The ReDIB COA Team

---
You receive this because you hold the ReDIB coordinator role. It is a record
of what happened, not a request to act.
Please do not reply to this email.''',
                'available_variables': '''Variables: coordinator_name, action (expired / force-accepted / reinstated), actioned_by, actioned_on, reason, change_line, application_code, call_code, applicant_name, applicant_email, node_name, status_label, application_url'''
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
