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

            <h3>Next Step: Accept or Decline Access</h3>
            <p>You have until <strong>{{ acceptance_deadline|date:"F d, Y" }}</strong> to respond.</p>

            <p style="text-align: center;">
                <a href="{{ accept_url }}" style="display:inline-block;padding:12px 24px;background-color:#198754;color:#ffffff;text-decoration:none;border-radius:6px;font-weight:bold;">Accept or Decline Access</a>
            </p>

            <p><small>Or copy this link into your browser: {{ accept_url }}</small></p>

            <p><em>If you do not respond by the deadline, your access will expire automatically.</em></p>

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

Next Step: Accept or Decline Access
You have until {{ acceptance_deadline|date:"F d, Y" }} to respond.

Please visit the following link to accept or decline:
{{ accept_url }}

If you do not respond by the deadline, your access will expire automatically.

Best regards,
ReDIB COA Team''',
                'available_variables': '''Variables: applicant_name, application_code, call_code, final_score, resolution, hours_approved, resolution_comments, resolution_date, acceptance_deadline, days_to_respond, accept_url'''
            },
            {
                'template_type': 'resolution_pending',
                'subject': 'ReDIB COA: Application {{ application_code }} Pending',
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
        .info-box { background-color: #fef5e7; border-left: 4px solid #f39c12; padding: 15px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ReDIB COA Portal</h1>
            <p>Application Pending (Waiting List)</p>
        </div>

        <div class="content">
            <p>Dear {{ applicant_name }},</p>

            <p>Your application <strong>{{ application_code }}</strong> for call {{ call_code }} has been marked as <strong>PENDING</strong> (waiting list).</p>

            <div class="info-box">
                <p><strong>Final Score:</strong> {{ final_score }}/12.00</p>
            </div>

            {% if resolution_comments %}<p>{{ resolution_comments }}</p>{% endif %}

            <p>You will be notified if hours become available.</p>

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
                'text_content': '''Application Pending (Waiting List)

Dear {{ applicant_name }},

Your application {{ application_code }} for call {{ call_code }} has been marked as PENDING (waiting list).

Final Score: {{ final_score }}/12.00

{% if resolution_comments %}{{ resolution_comments }}{% endif %}

You will be notified if hours become available.

Best regards,
ReDIB COA Team

---
This is an automated message from the ReDIB COA Portal.
Please do not reply to this email.''',
                'available_variables': '''Variables: applicant_name, application_code, call_code, final_score, resolution, hours_granted, resolution_comments, resolution_date'''
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
                'subject': 'ReDIB COA: Acceptance Deadline Expired for Application {{ application_code }}',
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
            <p>Acceptance Deadline Expired</p>
        </div>

        <div class="content">
            <p>Dear {{ applicant_name }},</p>

            <p>This is to inform you that the acceptance deadline for your approved COA application <strong>{{ application_code }}</strong> has expired.</p>

            <div class="warning-box">
                <p><strong>Deadline was:</strong> {{ deadline }}</p>
            </div>

            <p>Since we did not receive your acceptance or decline response within the required 10-day period, this application has been automatically marked as expired and the access grant is no longer available.</p>

            <p>If you would like to request access in the future, please apply during the next open call period.</p>

            <p>If you believe this is an error, please contact us at {{ contact_email }}.</p>

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
                'text_content': '''Acceptance Deadline Expired

Dear {{ applicant_name }},

This is to inform you that the acceptance deadline for your approved COA application {{ application_code }} has expired.

Deadline was: {{ deadline }}

Since we did not receive your acceptance or decline response within the required 10-day period, this application has been automatically marked as expired and the access grant is no longer available.

If you would like to request access in the future, please apply during the next open call period.

If you believe this is an error, please contact us at {{ contact_email }}.

Best regards,
ReDIB COA Team

---
This is an automated message from the ReDIB COA Portal.
Please do not reply to this email.''',
                'available_variables': '''Variables: applicant_name, application_code, deadline'''
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
                'subject': 'ReDIB COA: Reminder to accept access for {{ application_code }}',
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
            <p>This is a reminder that your application has been approved and awaits your formal acceptance. You have <strong>{{ days_remaining }} days</strong> remaining to respond before the grant expires.</p>
            <div class="info-box">
                <p><strong>Application Code:</strong> {{ application_code }}</p>
                <p><strong>Response deadline:</strong> {{ deadline }}</p>
            </div>
            <p style="text-align: center;">
                <a href="{{ acceptance_url }}" class="button">Accept or Decline</a>
            </p>
            <p>If you do not respond by the deadline the access grant will be automatically expired and offered to the next applicant on the waiting list.</p>
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

This is a reminder that your application has been approved and awaits your formal acceptance. You have {{ days_remaining }} days remaining to respond before the grant expires.

Application Details:
- Application Code: {{ application_code }}
- Response deadline: {{ deadline }}

Accept or Decline:
{{ acceptance_url }}

If you do not respond by the deadline the access grant will be automatically expired and offered to the next applicant on the waiting list.

Best regards,
The ReDIB COA Team

---
This is an automated reminder from the ReDIB COA Portal.
Please do not reply to this email.''',
                'available_variables': '''Variables: applicant_name, application_code, deadline, days_remaining, acceptance_url'''
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
