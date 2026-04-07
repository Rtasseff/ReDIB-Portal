"""
Management command to send all email templates to a single recipient for verification.

Creates minimal isolated test data, sends all 15 seeded templates, and optionally
cleans up afterward. Used to verify email rendering and link correctness.

Usage:
    python manage.py send_test_emails --to rtasseff@cicbiomagune.es
    python manage.py send_test_emails --cleanup
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import reverse
from django.utils import timezone

from applications.models import Application, FeasibilityReview
from calls.models import Call
from communications.tasks import send_email_from_template
from core.models import Node, User, UserRole
from evaluations.models import Evaluation


TEST_CALL_CODE = 'COA-EMAIL-TEST'


class Command(BaseCommand):
    help = 'Send all email templates to a single recipient for verification'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            default='rtasseff@cicbiomagune.es',
            help='Recipient email address (default: rtasseff@cicbiomagune.es)',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Delete all test objects created by a previous run, then exit',
        )

    def handle(self, *args, **options):
        recipient_email = options['to']

        if options['cleanup']:
            self._cleanup()
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\nSending all email templates to: {recipient_email}'
        ))

        # ── Setup ──────────────────────────────────────────────────
        user = User.objects.filter(email=recipient_email).first()
        if not user:
            self.stdout.write(self.style.ERROR(
                f'User with email {recipient_email} not found.'
            ))
            return

        user_name = user.get_full_name()
        node = Node.objects.filter(code='CICBIO').first()
        if not node:
            node = Node.objects.first()
        if not node:
            self.stdout.write(self.style.ERROR('No nodes exist in the database.'))
            return

        node_name = node.name

        # Create (or get) test call
        now = timezone.now()
        call, _ = Call.objects.get_or_create(
            code=TEST_CALL_CODE,
            defaults={
                'title': 'Email Template Test Call',
                'status': 'closed',
                'submission_start': now - timedelta(days=60),
                'submission_end': now - timedelta(days=30),
                'evaluation_deadline': now - timedelta(days=5),
                'execution_start': now + timedelta(days=30),
                'execution_end': now + timedelta(days=180),
                'description': 'Temporary call for email template testing.',
            },
        )

        # Create test application (bypass state-machine by setting code explicitly)
        app = Application.objects.filter(call=call).first()
        if not app:
            app = Application(
                call=call,
                applicant=user,
                code=f'{TEST_CALL_CODE}-001',
                status='accepted',
                brief_description='Test application for email verification',
                applicant_name=user_name,
                applicant_entity='CIC biomaGUNE',
                applicant_email=recipient_email,
                applicant_phone='+34 000 000 000',
                project_title='Email Link Verification Project',
                service_modality='full_assistance',
                final_score='9.50',
                resolution='accepted',
                resolution_date=now - timedelta(days=2),
                acceptance_deadline=now + timedelta(days=8),
                submitted_at=now - timedelta(days=45),
            )
            # Use super().save() to skip the code-generation / transition logic
            super(Application, app).save()

        # Create feasibility review
        review, _ = FeasibilityReview.objects.get_or_create(
            application=app,
            node=node,
            defaults={
                'reviewer': user,
                'is_feasible': None,
            },
        )

        # Ensure user has evaluator role (track if we created it)
        evaluator_role, eval_role_created = UserRole.objects.get_or_create(
            user=user,
            role='evaluator',
            node=None,
            defaults={'areas': 'preclinical'},
        )

        # Create evaluation
        evaluation, _ = Evaluation.objects.get_or_create(
            application=app,
            evaluator=user,
        )

        # ── Build URLs ─────────────────────────────────────────────
        base = settings.SITE_URL
        review_url = base + reverse('applications:feasibility_review', kwargs={'pk': review.pk})
        evaluation_url = base + reverse('evaluations:evaluation_detail', kwargs={'pk': evaluation.pk})
        application_url = base + reverse('applications:detail', kwargs={'pk': app.pk})
        accept_url = base + reverse('applications:application_acceptance', kwargs={'pk': app.pk})
        publication_url = base + reverse('access:publication_submit')

        deadline = call.evaluation_deadline

        # ── Template contexts ──────────────────────────────────────
        templates = [
            ('feasibility_request', {
                'reviewer_name': user_name,
                'application_code': app.code,
                'node_name': node_name,
                'review_url': review_url,
            }),
            ('application_received', {
                'applicant_name': user_name,
                'application_code': app.code,
                'call_code': call.code,
            }),
            ('feasibility_complete', {
                'applicant_name': user_name,
                'application_code': app.code,
                'status': 'approved and ready for evaluation',
            }),
            ('evaluation_assigned', {
                'evaluator_name': user_name,
                'application_code': app.code,
                'call_code': call.code,
                'deadline': deadline,
                'evaluation_url': evaluation_url,
            }),
            ('evaluation_reminder', {
                'evaluator_name': user_name,
                'application_code': app.code,
                'application_title': app.brief_description,
                'call_code': call.code,
                'days_remaining': 3,
                'deadline': deadline,
                'evaluation_url': evaluation_url,
            }),
            ('evaluation_overdue', {
                'evaluator_name': user_name,
                'application_code': app.code,
                'call_code': call.code,
                'deadline': deadline,
                'evaluation_url': evaluation_url,
            }),
            ('coordinator_overdue_evaluations', {
                'coordinator_name': user_name,
                'call_code': call.code,
                'call_title': call.title,
                'deadline': deadline,
                'pending_count': 2,
                'pending_evaluations': (
                    f'  - {app.code}: {user_name} ({recipient_email})\n'
                    f'  - {app.code}: Test Evaluator (evaluator@example.com)'
                ),
            }),
            ('coordinator_evaluations_locked', {
                'coordinator_name': user_name,
                'call_code': call.code,
                'call_title': call.title,
                'deadline': deadline,
                'days_overdue': 8,
                'pending_count': 1,
                'pending_evaluations': (
                    f'  - {app.code}: Test Evaluator (evaluator@example.com)'
                ),
            }),
            ('evaluations_complete', {
                'coordinator_name': user_name,
                'application_code': app.code,
                'applicant_name': user_name,
                'brief_description': app.brief_description,
                'call_code': call.code,
                'num_evaluations': 2,
                'average_score': '9.50',
                'application_url': application_url,
            }),
            ('resolution_accepted', {
                'applicant_name': user_name,
                'application_code': app.code,
                'call_code': call.code,
                'final_score': '9.50',
                'resolution': 'accepted',
                'hours_approved': 24,
                'resolution_comments': 'Excellent scientific proposal with strong methodology.',
                'resolution_date': app.resolution_date,
                'acceptance_deadline': app.acceptance_deadline,
                'days_to_respond': 8,
                'accept_url': accept_url,
            }),
            ('resolution_pending', {
                'applicant_name': user_name,
                'application_code': app.code,
                'call_code': call.code,
                'final_score': '6.00',
                'resolution': 'pending',
                'hours_granted': 0,
                'resolution_comments': 'Application placed on waiting list due to limited capacity.',
                'resolution_date': now,
            }),
            ('resolution_rejected', {
                'applicant_name': user_name,
                'application_code': app.code,
                'call_code': call.code,
                'final_score': '3.50',
                'resolution': 'rejected',
                'hours_granted': 0,
                'resolution_comments': 'Score below threshold for this call period.',
                'resolution_date': now,
            }),
            ('handoff_notification', {
                'applicant_name': user_name,
                'applicant_entity': 'CIC biomaGUNE',
                'applicant_email': recipient_email,
                'applicant_phone': '+34 000 000 000',
                'application_code': app.code,
                'project_title': app.project_title,
                'brief_description': app.brief_description,
                'service_modality': 'Full Assistance',
                'node_names': node_name,
                'requested_access': [
                    {
                        'node_name': node_name,
                        'equipment_name': 'PET-MRI 3T',
                        'hours_requested': 16,
                    },
                    {
                        'node_name': node_name,
                        'equipment_name': 'Cyclotron',
                        'hours_requested': 8,
                    },
                ],
            }),
            ('acceptance_expired', {
                'applicant_name': user_name,
                'application_code': app.code,
                'deadline': (now - timedelta(days=1)).strftime('%B %d, %Y'),
            }),
            ('publication_followup', {
                'applicant_name': user_name,
                'application_code': app.code,
                'project_title': app.project_title,
                'handoff_date': (now - timedelta(days=180)).strftime('%B %d, %Y'),
                'acknowledgment_text': (
                    'This work was supported by the ReDIB-ICTS infrastructure '
                    '(ICTS-2017-28-CICbiomaGUNE-4) funded by MCIN/AEI/10.13039/501100011033 '
                    'and by the European Union.'
                ),
                'publication_url': publication_url,
            }),
        ]

        # ── Send ───────────────────────────────────────────────────
        success = 0
        failed = 0
        for template_type, context in templates:
            ok = send_email_from_template(
                template_type=template_type,
                recipient_email=recipient_email,
                context_data=context,
                recipient_user_id=user.pk,
                related_call_id=call.pk,
                related_application_id=app.pk,
            )
            if ok:
                success += 1
                self.stdout.write(self.style.SUCCESS(f'  [OK]   {template_type}'))
            else:
                failed += 1
                self.stdout.write(self.style.ERROR(f'  [FAIL] {template_type}'))

        # ── Summary ────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'Done: {success} sent, {failed} failed (out of {len(templates)} templates)'
        ))
        if eval_role_created:
            self.stdout.write(self.style.WARNING(
                f'Note: evaluator role was added to {recipient_email} for testing.'
            ))
        self.stdout.write(self.style.WARNING(
            f'Run with --cleanup to remove test data (call {TEST_CALL_CODE} and related objects).'
        ))

    # ── Cleanup helper ─────────────────────────────────────────────
    def _cleanup(self):
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\nCleaning up test data for call {TEST_CALL_CODE}...'
        ))

        try:
            call = Call.objects.get(code=TEST_CALL_CODE)
        except Call.DoesNotExist:
            self.stdout.write(self.style.WARNING('No test call found. Nothing to clean up.'))
            return

        apps = Application.objects.filter(call=call)

        # Delete evaluations
        eval_count, _ = Evaluation.objects.filter(application__in=apps).delete()
        self.stdout.write(f'  Deleted {eval_count} evaluation object(s)')

        # Delete feasibility reviews
        review_count, _ = FeasibilityReview.objects.filter(application__in=apps).delete()
        self.stdout.write(f'  Deleted {review_count} feasibility review object(s)')

        # Delete applications (use raw delete to skip state-machine validation)
        app_count = apps.count()
        apps.delete()
        self.stdout.write(f'  Deleted {app_count} application(s)')

        # Delete the call
        call.delete()
        self.stdout.write(f'  Deleted call {TEST_CALL_CODE}')

        # Remove evaluator role if it was added for testing
        # (only remove if user has no other evaluations)
        # We don't track which user, so skip automatic role removal — it's harmless.

        self.stdout.write(self.style.SUCCESS('\nCleanup complete.'))
