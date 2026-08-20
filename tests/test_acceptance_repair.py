"""
Tests for #53 — acceptance-repair: no transition without a human.

The bucket's principle: *a beat task may compute and notify; only a human
writes a transition.* One test class per step of the brief.

1. the dead `access/tasks.py process_acceptance_deadlines` is gone
2. #52 — the two acceptance templates read correctly for a waitlisted
   applicant and no longer promise anything automatic
3. the pre-deadline reminder ladder fires at 7 / 3 / 1 days out
4. the expire and force-accept coordinator actions
5. no beat task writes an Application.status
6. the repeating stalled-acceptance nag, with its cc and its counter
7. #18 — reinstate an expired application
"""
import io
from datetime import timedelta
from decimal import Decimal

from django.core import mail
from django.core.management import call_command
from django.template import Context, Template
from django.test import Client, TestCase
from django.utils import timezone

from applications.models import Application, RequestedAccess
from applications.tasks import (
    process_acceptance_deadlines,
    send_stalled_acceptance_reminders,
)
from calls.models import Call
from communications.models import EmailLog, EmailTemplate
from core.models import Equipment, Node, Organization, UserRole
from core.test_utils import create_complete_user


class AcceptanceRepairTestCase(TestCase):
    """Shared fixture: one node with a coordinator, one ReDIB coordinator,
    one applicant, one call."""

    def setUp(self):
        call_command('seed_email_templates', stdout=io.StringIO())
        self.org = Organization.objects.create(
            name='Repair Org', iso2='ES', country='Spain', organization_type='other'
        )
        self.node = Node.objects.create(
            code='REPAIR-NODE', organization=self.org, location='Test City'
        )
        self.equipment = Equipment.objects.create(
            node=self.node, name='Repair Scanner', category='mri'
        )

        self.node_coordinator = create_complete_user(
            email='nodecoord@repair.test', organization=self.org)
        UserRole.objects.create(
            user=self.node_coordinator, role='node_coordinator',
            node=self.node, is_active=True)

        self.redib_coordinator = create_complete_user(
            email='redibcoord@repair.test', organization=self.org)
        UserRole.objects.create(
            user=self.redib_coordinator, role='coordinator', is_active=True)

        self.applicant = create_complete_user(
            email='applicant@repair.test', organization=self.org)

        self.call = Call.objects.create(
            code='REPAIR-2026',
            title='Repair Call',
            submission_start=timezone.now() - timedelta(days=60),
            submission_end=timezone.now() - timedelta(days=30),
            evaluation_deadline=timezone.now() - timedelta(days=10),
            execution_start=timezone.now() + timedelta(days=5),
            execution_end=timezone.now() + timedelta(days=100),
        )
        self._code_seq = 0

    def make_application(self, status='accepted', resolution=None, deadline_days=-1,
                         accepted_by_applicant=None, hours_approved=Decimal('8.0')):
        """An application whose acceptance deadline is `deadline_days` from
        now (negative = already passed)."""
        self._code_seq += 1
        application = Application.objects.create(
            applicant=self.applicant,
            call=self.call,
            code=f'REPAIR-APP-{self._code_seq:03d}',
            brief_description='Repair test application',
            applicant_name='Dr. Repair Applicant',
            applicant_email='applicant@repair.test',
            status=status,
            resolution=resolution if resolution is not None else status,
            resolution_date=timezone.now() - timedelta(days=10 + max(0, -deadline_days)),
            acceptance_deadline=timezone.now() + timedelta(days=deadline_days),
            accepted_by_applicant=accepted_by_applicant,
        )
        RequestedAccess.objects.create(
            application=application,
            equipment=self.equipment,
            hours_requested=Decimal('10.0'),
            hours_approved=hours_approved,
        )
        return application

    def node_client(self):
        client = Client()
        client.force_login(self.node_coordinator)
        return client

    def logs(self, template_type, application=None):
        qs = EmailLog.objects.filter(template__template_type=template_type)
        if application is not None:
            qs = qs.filter(related_application_id=application.id)
        return qs


class Step1DeadTaskDeletedTest(TestCase):
    """Step 1: the unscheduled duplicate in `access/tasks.py` is gone."""

    def test_access_tasks_no_longer_defines_process_acceptance_deadlines(self):
        import access.tasks as access_tasks

        self.assertFalse(
            hasattr(access_tasks, 'process_acceptance_deadlines'),
            "The dead access/tasks.py copy is back — it sets accepted -> rejected, "
            "not expired, and collides in name with the live task."
        )

    def test_publication_followups_survives(self):
        import access.tasks as access_tasks

        self.assertTrue(hasattr(access_tasks, 'send_publication_followups'))

    def test_beat_schedule_does_not_reference_the_dead_task(self):
        from redib.celery import app as celery_app

        tasks = {entry['task'] for entry in celery_app.conf.beat_schedule.values()}
        self.assertNotIn('access.tasks.process_acceptance_deadlines', tasks)


class Step2AcceptanceTemplateWordingTest(AcceptanceRepairTestCase):
    """Step 2 (#52): both acceptance templates now branch on is_waitlist,
    and neither promises anything automatic."""

    def render(self, template_type, **context):
        template = EmailTemplate.objects.get(template_type=template_type)
        context.setdefault('contact_email', 'coa@redib.net')
        ctx = Context(context)
        return (
            Template(template.subject).render(ctx)
            + '\n' + Template(template.text_content).render(ctx)
            + '\n' + Template(template.html_content).render(ctx)
        )

    def test_reminder_to_waitlisted_applicant_does_not_claim_approval(self):
        body = self.render(
            'acceptance_reminder', applicant_name='X', application_code='A-1',
            deadline='September 10, 2026', days_remaining=3,
            acceptance_url='http://x/accept/', is_waitlist=True)

        self.assertIn('waiting list', body)
        self.assertNotIn('has been approved', body)
        self.assertNotIn('access grant', body)

    def test_reminder_never_promises_the_slot_to_the_next_applicant(self):
        """Nonsense to someone who *is* the waiting list — and an expiring
        'pending' application frees no allocation at all."""
        for is_waitlist in (True, False):
            body = self.render(
                'acceptance_reminder', applicant_name='X', application_code='A-1',
                deadline='September 10, 2026', days_remaining=3,
                acceptance_url='http://x/accept/', is_waitlist=is_waitlist)

            self.assertNotIn('next applicant on the waiting list', body)
            self.assertNotIn('automatically expired', body)

    def test_reminder_to_accepted_applicant_still_reads_as_a_grant(self):
        body = self.render(
            'acceptance_reminder', applicant_name='X', application_code='A-1',
            deadline='September 10, 2026', days_remaining=7,
            acceptance_url='http://x/accept/', is_waitlist=False)

        self.assertIn('has been approved', body)

    def test_expired_template_is_not_written_as_an_automatic_act(self):
        for is_waitlist in (True, False):
            body = self.render(
                'acceptance_expired', applicant_name='X', application_code='A-1',
                deadline='September 10, 2026', is_waitlist=is_waitlist)

            self.assertNotIn('automatically marked as expired', body)
            self.assertIn('node coordinator', body)

    def test_expired_template_to_waitlisted_applicant_claims_no_grant(self):
        body = self.render(
            'acceptance_expired', applicant_name='X', application_code='A-1',
            deadline='September 10, 2026', is_waitlist=True)

        self.assertIn('waiting list', body)
        self.assertNotIn('approved COA application', body)
        self.assertNotIn('access grant', body)


class Step3ReminderLadderTest(AcceptanceRepairTestCase):
    """Step 3: reminders at 7, 3 and 1 days before the deadline."""

    def walk_to(self, app, deadline_days):
        """Advance the application to `deadline_days` before its deadline and
        run the beat once, as the daily task would."""
        app.acceptance_deadline = timezone.now() + timedelta(days=deadline_days)
        app.save(update_fields=['acceptance_deadline'])
        # Age any prior sends past the 24-hour same-day guard, the way the
        # days between checkpoints would.
        EmailLog.objects.filter(related_application_id=app.id).update(
            sent_at=timezone.now() - timedelta(days=2))
        process_acceptance_deadlines()

    def assert_sends(self, app, expected, note):
        self.assertEqual(
            self.logs('acceptance_reminder', app).count(), expected, note)

    def start_ladder(self):
        """An application that has just had its day-7 rung."""
        app = self.make_application(status='accepted', deadline_days=7)
        process_acceptance_deadlines()
        self.assert_sends(app, 1, "day-7 rung should send")
        return app

    def test_fires_seven_days_out(self):
        self.start_ladder()

    def test_fires_three_days_out(self):
        app = self.start_ladder()
        self.walk_to(app, 3)
        self.assert_sends(app, 2, "day-3 rung should send")

    def test_fires_one_day_out(self):
        app = self.start_ladder()
        self.walk_to(app, 3)
        self.walk_to(app, 1)
        self.assert_sends(app, 3, "day-1 rung should send")

    def test_silent_between_rungs(self):
        """Having sent the day-7 rung, days 6 and 5 owe nothing."""
        app = self.start_ladder()
        self.walk_to(app, 6)
        self.walk_to(app, 5)
        self.assert_sends(app, 1, "no rung is owed between 7 and 3")

    def test_silent_after_the_last_rung(self):
        """All three rungs spent — further runs inside the window add nothing."""
        app = self.start_ladder()
        self.walk_to(app, 3)
        self.walk_to(app, 1)
        self.walk_to(app, 1)
        self.assert_sends(app, 3, "the ladder has exactly three rungs")

    def test_silent_before_the_first_rung(self):
        app = self.make_application(status='accepted', deadline_days=9)
        process_acceptance_deadlines()
        self.assert_sends(app, 0, "nothing is owed 9 days out")

    def test_silent_after_the_deadline(self):
        """Past the deadline the applicant hears nothing further from the
        system; the node coordinator is nagged instead."""
        app = self.make_application(status='accepted', deadline_days=-1)
        process_acceptance_deadlines()
        self.assert_sends(app, 0, "the deadline has passed")

    def test_a_missed_rung_is_caught_up_not_lost(self):
        """If the beat is down on the day-7 rung, day 5 still owes it. The
        nag asserts the applicant was chased repeatedly, so a silently
        skipped rung would make that claim false."""
        app = self.make_application(status='accepted', deadline_days=5)

        process_acceptance_deadlines()

        self.assert_sends(app, 1, "the missed day-7 rung should be caught up")

    def test_catch_up_never_overshoots_the_ladder(self):
        """An application first seen with one day left owes three rungs but
        must not fire three emails at once."""
        app = self.make_application(status='accepted', deadline_days=1)

        process_acceptance_deadlines()
        process_acceptance_deadlines()

        self.assert_sends(app, 1, "at most one reminder per beat run")

    def test_ladder_gives_three_reminders_across_the_window(self):
        """The nag asserts the applicant 'was sent several reminders'."""
        app = self.make_application(status='accepted', deadline_days=7)

        for days_out in (7, 3, 1):
            app.acceptance_deadline = timezone.now() + timedelta(days=days_out)
            app.save(update_fields=['acceptance_deadline'])
            process_acceptance_deadlines()
            # Age the log the way the days between checkpoints would, so the
            # 24-hour same-day dedupe does not swallow the next rung.
            EmailLog.objects.filter(related_application_id=app.id).update(
                sent_at=timezone.now() - timedelta(days=4))

        self.assertEqual(self.logs('acceptance_reminder', app).count(), 3)

    def test_waitlisted_reminder_is_flagged_as_waitlist(self):
        app = self.make_application(status='pending', deadline_days=3)
        process_acceptance_deadlines()

        log = self.logs('acceptance_reminder', app).first()
        self.assertIsNotNone(log)
        self.assertIn('waiting list', log.text_content)


class Step4CoordinatorActionsTest(AcceptanceRepairTestCase):
    """Step 4: expire and force-accept, each with a required reason and a
    notice to the ReDIB coordinator."""

    # ---- shared guards ------------------------------------------------

    def test_expire_refused_before_the_deadline(self):
        """Before the deadline this is the applicant's decision."""
        app = self.make_application(deadline_days=3)

        self.node_client().post(f'/applications/{app.pk}/expire/', {'reason': 'nope'})
        app.refresh_from_db()

        self.assertEqual(app.status, 'accepted')

    def test_expire_refused_once_the_applicant_has_answered(self):
        app = self.make_application(deadline_days=-1, accepted_by_applicant=True)

        self.node_client().post(f'/applications/{app.pk}/expire/', {'reason': 'nope'})
        app.refresh_from_db()

        self.assertEqual(app.status, 'accepted')

    def test_expire_refused_in_a_non_acceptance_status(self):
        app = self.make_application(status='evaluated', resolution='', deadline_days=-1)

        self.node_client().post(f'/applications/{app.pk}/expire/', {'reason': 'nope'})
        app.refresh_from_db()

        self.assertEqual(app.status, 'evaluated')

    def test_expire_refused_without_a_reason(self):
        app = self.make_application(deadline_days=-1)

        self.node_client().post(f'/applications/{app.pk}/expire/', {'reason': '   '})
        app.refresh_from_db()

        self.assertEqual(app.status, 'accepted')

    def test_expire_refused_for_an_unrelated_node_coordinator(self):
        other_node = Node.objects.create(
            code='OTHER-NODE', organization=self.org, location='Elsewhere')
        outsider = create_complete_user(email='outsider@repair.test', organization=self.org)
        UserRole.objects.create(
            user=outsider, role='node_coordinator', node=other_node, is_active=True)
        app = self.make_application(deadline_days=-1)

        client = Client()
        client.force_login(outsider)
        client.post(f'/applications/{app.pk}/expire/', {'reason': 'not mine'})
        app.refresh_from_db()

        self.assertEqual(app.status, 'accepted')

    def test_get_renders_a_confirmation_screen(self):
        app = self.make_application(deadline_days=-1)

        response = self.node_client().get(f'/applications/{app.pk}/expire/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'applications/expire_stalled_confirm.html')
        app.refresh_from_db()
        self.assertEqual(app.status, 'accepted')

    def test_force_accept_get_renders_a_confirmation_screen(self):
        app = self.make_application(deadline_days=-1)

        response = self.node_client().get(f'/applications/{app.pk}/force-accept/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'applications/force_accept_confirm.html')
        app.refresh_from_db()
        self.assertIsNone(app.accepted_by_applicant)

    def test_access_tracking_offers_both_actions_on_a_stalled_application(self):
        app = self.make_application(deadline_days=-1)

        response = self.node_client().get('/access/tracking/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'/applications/{app.id}/expire/')
        self.assertContains(response, f'/applications/{app.id}/force-accept/')

    def test_access_tracking_hides_both_actions_before_the_deadline(self):
        app = self.make_application(deadline_days=3)

        response = self.node_client().get('/access/tracking/')

        self.assertNotContains(response, f'/applications/{app.id}/expire/')
        self.assertNotContains(response, f'/applications/{app.id}/force-accept/')

    # ---- expire -------------------------------------------------------

    def test_expire_writes_the_transition_and_the_reason(self):
        app = self.make_application(deadline_days=-1)

        self.node_client().post(
            f'/applications/{app.pk}/expire/',
            {'reason': 'Chased three times, no answer.'})
        app.refresh_from_db()

        self.assertEqual(app.status, 'expired')
        self.assertFalse(app.accepted_by_applicant)
        self.assertIsNotNone(app.accepted_at)
        self.assertIn('[EXPIRED BY COORDINATOR]', app.resolution_comments)
        self.assertIn('Chased three times', app.resolution_comments)

    def test_expire_is_silent_to_the_applicant_by_default(self):
        app = self.make_application(deadline_days=-1)

        self.node_client().post(f'/applications/{app.pk}/expire/', {'reason': 'Already phoned them.'})

        self.assertFalse(self.logs('acceptance_expired', app).exists())

    def test_expire_emails_the_applicant_when_the_box_is_ticked(self):
        app = self.make_application(deadline_days=-1)

        self.node_client().post(
            f'/applications/{app.pk}/expire/',
            {'reason': 'No contact at all.', 'notify_applicant': '1'})

        self.assertTrue(self.logs('acceptance_expired', app).exists())

    def test_expire_notifies_the_redib_coordinator(self):
        app = self.make_application(deadline_days=-1)

        self.node_client().post(f'/applications/{app.pk}/expire/', {'reason': 'No answer.'})

        log = self.logs('stalled_acceptance_actioned', app).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.recipient_email, self.redib_coordinator.email)
        self.assertIn('No answer.', log.text_content)
        self.assertIn('expired', log.text_content)

    def test_expiring_a_waitlisted_application_frees_nothing(self):
        app = self.make_application(status='pending', deadline_days=-1, hours_approved=None)

        self.node_client().post(f'/applications/{app.pk}/expire/', {'reason': 'No answer.'})
        app.refresh_from_db()

        self.assertEqual(app.status, 'expired')
        self.assertFalse(self.logs('freed_capacity_notice', app).exists())

    def test_expiring_an_accepted_application_frees_capacity(self):
        app = self.make_application(status='accepted', deadline_days=-1)

        self.node_client().post(f'/applications/{app.pk}/expire/', {'reason': 'No answer.'})

        self.assertTrue(self.logs('freed_capacity_notice', app).exists())

    # ---- force-accept -------------------------------------------------

    def test_force_accept_refused_without_a_reason(self):
        app = self.make_application(deadline_days=-1)

        self.node_client().post(f'/applications/{app.pk}/force-accept/', {'reason': ''})
        app.refresh_from_db()

        self.assertIsNone(app.accepted_by_applicant)

    def test_force_accept_refused_before_the_deadline(self):
        app = self.make_application(deadline_days=2)

        self.node_client().post(
            f'/applications/{app.pk}/force-accept/', {'reason': 'They said yes by phone.'})
        app.refresh_from_db()

        self.assertIsNone(app.accepted_by_applicant)

    def test_force_accept_on_an_accepted_application_fires_the_handoff(self):
        app = self.make_application(status='accepted', deadline_days=-1)

        self.node_client().post(
            f'/applications/{app.pk}/force-accept/', {'reason': 'PI confirmed by phone.'})
        app.refresh_from_db()

        self.assertEqual(app.status, 'accepted')
        self.assertTrue(app.accepted_by_applicant)
        self.assertIsNotNone(app.accepted_at)
        self.assertIsNotNone(app.handoff_email_sent_at)
        self.assertTrue(self.logs('handoff_notification', app).exists())
        self.assertIn('[FORCE-ACCEPTED BY COORDINATOR]', app.resolution_comments)
        self.assertIn('PI confirmed by phone.', app.resolution_comments)

    def test_force_accept_on_a_waitlisted_application_defers_the_handoff(self):
        app = self.make_application(status='pending', deadline_days=-1, hours_approved=None)

        self.node_client().post(
            f'/applications/{app.pk}/force-accept/', {'reason': 'PI confirmed by phone.'})
        app.refresh_from_db()

        self.assertEqual(app.status, 'pending')
        self.assertTrue(app.accepted_by_applicant)
        self.assertIsNone(app.handoff_email_sent_at)
        self.assertFalse(self.logs('handoff_notification', app).exists())

    def test_force_accept_notifies_the_redib_coordinator_every_time(self):
        app = self.make_application(deadline_days=-1)

        self.node_client().post(
            f'/applications/{app.pk}/force-accept/', {'reason': 'PI confirmed by phone.'})

        log = self.logs('stalled_acceptance_actioned', app).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.recipient_email, self.redib_coordinator.email)
        self.assertIn('force-accepted', log.text_content)
        self.assertIn('PI confirmed by phone.', log.text_content)
        self.assertIn(self.node_coordinator.get_full_name(), log.text_content)

    def test_a_force_accepted_waitlist_application_can_still_be_promoted(self):
        """The waitlist path defers the handoff until promotion — check the
        promotion still works from the force-accepted state."""
        app = self.make_application(status='pending', deadline_days=-1, hours_approved=None)
        self.node_client().post(
            f'/applications/{app.pk}/force-accept/', {'reason': 'PI confirmed by phone.'})

        self.node_client().post(f'/applications/{app.pk}/promote-waitlist/', {})
        app.refresh_from_db()

        self.assertEqual(app.status, 'accepted')
        self.assertIsNotNone(app.handoff_email_sent_at)


class Step5NoBeatTaskWritesStatusTest(AcceptanceRepairTestCase):
    """Step 5 / the acceptance criterion: no scheduled task writes an
    Application.status."""

    def test_every_scheduled_application_task_leaves_statuses_alone(self):
        from redib.celery import app as celery_app

        apps = [
            self.make_application(status='accepted', deadline_days=-1),
            self.make_application(status='pending', deadline_days=-1, hours_approved=None),
            self.make_application(status='accepted', deadline_days=3),
        ]
        before = {a.pk: a.status for a in apps}

        import importlib
        for entry in celery_app.conf.beat_schedule.values():
            module_path, _, func_name = entry['task'].rpartition('.')
            if not module_path.startswith(('applications.', 'access.')):
                continue
            module = importlib.import_module(module_path)
            getattr(module, func_name)()

        for app in apps:
            app.refresh_from_db()
            self.assertEqual(
                app.status, before[app.pk],
                f"A beat task moved {app.code} from {before[app.pk]} to {app.status}."
            )

    def test_auto_expire_branch_is_gone_from_the_source(self):
        import inspect
        from applications import tasks

        source = inspect.getsource(tasks.process_acceptance_deadlines)
        self.assertNotIn('AUTO-EXPIRED', source)
        self.assertNotIn("status = 'expired'", source)


class Step6StalledNagTest(AcceptanceRepairTestCase):
    """Step 6: the repeating nag to the node coordinator, ReDIB coordinator
    cc'd, with a reminder counter."""

    def test_no_nag_before_the_deadline(self):
        app = self.make_application(deadline_days=3)
        send_stalled_acceptance_reminders()
        self.assertFalse(self.logs('stalled_acceptance_reminder', app).exists())

    def test_no_nag_on_the_deadline_day_itself(self):
        """First send is 1 day after the deadline."""
        app = self.make_application(deadline_days=0)
        app.acceptance_deadline = timezone.now() - timedelta(hours=2)
        app.save(update_fields=['acceptance_deadline'])

        send_stalled_acceptance_reminders()

        self.assertFalse(self.logs('stalled_acceptance_reminder', app).exists())

    def test_nag_fires_on_the_cadence_days(self):
        """Day 1, then every 3 days: 1, 4, 7 fire; 2, 3, 5, 6 do not."""
        app = self.make_application(deadline_days=-1)

        for elapsed, expected in ((1, True), (2, False), (3, False),
                                  (4, True), (5, False), (7, True)):
            EmailLog.objects.filter(related_application_id=app.id).delete()
            app.acceptance_deadline = timezone.now() - timedelta(days=elapsed)
            app.save(update_fields=['acceptance_deadline'])

            send_stalled_acceptance_reminders()

            self.assertEqual(
                self.logs('stalled_acceptance_reminder', app).exists(), expected,
                f"{elapsed} days past the deadline: expected nag={expected}"
            )

    def test_nag_goes_to_the_node_coordinator_with_the_redib_coordinator_cc(self):
        app = self.make_application(deadline_days=-1)
        mail.outbox.clear()

        send_stalled_acceptance_reminders()

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, [self.node_coordinator.email])
        self.assertEqual(message.cc, [self.redib_coordinator.email])
        self.assertIn('node coordinator must act', message.body.lower())
        self.assertIn(str(app.code), message.body)

    def test_nag_carries_the_action_links(self):
        app = self.make_application(deadline_days=-1)

        send_stalled_acceptance_reminders()

        body = self.logs('stalled_acceptance_reminder', app).first().text_content
        self.assertIn(f'/applications/{app.id}/expire/', body)
        self.assertIn(f'/applications/{app.id}/force-accept/', body)

    def test_nag_never_implies_the_applicant_can_still_act(self):
        """Two resolution options, not three — the applicant's link is
        closed and no copy may suggest otherwise."""
        app = self.make_application(deadline_days=-1)

        send_stalled_acceptance_reminders()

        body = self.logs('stalled_acceptance_reminder', app).first().text_content
        self.assertNotIn(f'/applications/{app.id}/accept/', body)

    def test_reminder_number_counts_distinct_send_days(self):
        """A node with two active coordinators produces two rows per send;
        both people must still see the same number."""
        second = create_complete_user(email='nodecoord2@repair.test', organization=self.org)
        UserRole.objects.create(
            user=second, role='node_coordinator', node=self.node, is_active=True)
        app = self.make_application(deadline_days=-1)

        # Send 1 (day 1 after the deadline)
        send_stalled_acceptance_reminders()
        first_round = list(self.logs('stalled_acceptance_reminder', app))
        self.assertEqual(len(first_round), 2)
        for log in first_round:
            self.assertIn('reminder #1', log.text_content.lower())

        # Backdate both rows a day and move the deadline to the next
        # cadence day, so send 2 sees one distinct prior day, not two rows.
        EmailLog.objects.filter(related_application_id=app.id).update(
            sent_at=timezone.now() - timedelta(days=3))
        app.acceptance_deadline = timezone.now() - timedelta(days=4)
        app.save(update_fields=['acceptance_deadline'])

        send_stalled_acceptance_reminders()

        second_round = self.logs('stalled_acceptance_reminder', app).order_by('-id')[:2]
        for log in second_round:
            self.assertIn('reminder #2', log.text_content.lower())

    def test_nag_does_not_double_send_on_a_same_day_rerun(self):
        app = self.make_application(deadline_days=-1)

        send_stalled_acceptance_reminders()
        send_stalled_acceptance_reminders()

        self.assertEqual(self.logs('stalled_acceptance_reminder', app).count(), 1)

    def test_nag_stops_once_the_application_leaves_the_stalled_state(self):
        app = self.make_application(deadline_days=-1)
        self.node_client().post(f'/applications/{app.pk}/expire/', {'reason': 'No answer.'})
        EmailLog.objects.filter(related_application_id=app.id).delete()

        send_stalled_acceptance_reminders()

        self.assertFalse(self.logs('stalled_acceptance_reminder', app).exists())

    def test_nag_writes_no_status(self):
        app = self.make_application(status='pending', deadline_days=-4, hours_approved=None)

        send_stalled_acceptance_reminders()
        app.refresh_from_db()

        self.assertEqual(app.status, 'pending')
        self.assertIsNone(app.accepted_by_applicant)


class ReviewFindingsTest(AcceptanceRepairTestCase):
    """Regressions for the /code-review medium findings fixed on this branch."""

    def render(self, template_type, **context):
        template = EmailTemplate.objects.get(template_type=template_type)
        context.setdefault('contact_email', 'coa@redib.net')
        ctx = Context(context)
        return (Template(template.text_content).render(ctx)
                + '\n' + Template(template.html_content).render(ctx))

    def test_no_seeded_template_still_promises_automatic_expiry(self):
        """#53 removed auto-expire; resolution_accepted, resolution_pending
        and freed_capacity_notice all carried the old promise."""
        stale = ('expire automatically', 'auto-expire', 'automatically expired',
                 'automatically marked as expired')
        for template in EmailTemplate.objects.all():
            haystack = (template.subject + template.text_content
                        + template.html_content).lower()
            for phrase in stale:
                self.assertNotIn(
                    phrase, haystack,
                    f"{template.template_type} still says '{phrase}'"
                )

    def test_freed_capacity_notice_credits_the_coordinator_not_the_system(self):
        body = self.render(
            'freed_capacity_notice', coordinator_name='Ana', application_code='A-1',
            applicant_name='X', node_name='N', reason='expired', freed_lines=[],
            application_url='http://x/', access_tracking_url='http://x/t/')

        self.assertIn('expired by a coordinator', body)

    def test_nag_does_not_claim_force_accept_promotes_a_waitlist_application(self):
        """force_accept_stalled_application deliberately leaves it 'pending'."""
        app = self.make_application(status='pending', deadline_days=-1, hours_approved=None)

        send_stalled_acceptance_reminders()

        # Normalise the hard wrapping of the plain-text body before matching.
        body = ' '.join(
            self.logs('stalled_acceptance_reminder', app).first().text_content.split())
        self.assertNotIn('moves them from the waiting list to accepted', body)
        self.assertIn('stays on the waiting list until you promote it', body)

    def test_nag_falls_back_to_the_redib_coordinator_when_the_node_has_none(self):
        """The ReDIB coordinator normally rides in CC, which needs a To. With
        no reachable node coordinator the nag would otherwise send nothing
        and the application would stall unnoticed — the exact failure #53
        exists to prevent."""
        UserRole.objects.filter(user=self.node_coordinator).update(is_active=False)
        app = self.make_application(deadline_days=-1)
        mail.outbox.clear()

        send_stalled_acceptance_reminders()

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, [self.redib_coordinator.email])
        self.assertEqual(message.cc, [])
        self.assertIn('no active coordinator', message.body.lower())

    def test_nag_skips_a_node_coordinator_with_no_email(self):
        blank = create_complete_user(email='blank@repair.test', organization=self.org)
        UserRole.objects.create(
            user=blank, role='node_coordinator', node=self.node, is_active=True)
        blank.email = ''
        blank.save(update_fields=['email'])
        app = self.make_application(deadline_days=-1)

        send_stalled_acceptance_reminders()

        recipients = set(
            self.logs('stalled_acceptance_reminder', app).values_list(
                'recipient_email', flat=True))
        self.assertEqual(recipients, {self.node_coordinator.email})

    def test_force_accept_audit_does_not_claim_a_handoff_that_failed(self):
        """send_email_from_template returns False instead of raising, so a
        try/except alone would report success for a missing template."""
        EmailTemplate.objects.filter(template_type='handoff_notification').delete()
        app = self.make_application(status='accepted', deadline_days=-1)

        self.node_client().post(
            f'/applications/{app.pk}/force-accept/', {'reason': 'PI confirmed.'})
        app.refresh_from_db()

        # The acceptance still stands; only the handoff claim changes.
        self.assertTrue(app.accepted_by_applicant)
        self.assertIsNone(
            app.handoff_email_sent_at,
            "handoff_email_sent_at must stay unset so a coordinator can retry")
        audit = self.logs('stalled_acceptance_actioned', app).first()
        self.assertIsNotNone(audit)
        self.assertIn('could not be sent', audit.text_content)

    def test_action_refused_clearly_when_there_is_no_deadline_at_all(self):
        """Pre-existing hole (the deleted auto-expire skipped these too):
        say so instead of claiming the deadline has not passed."""
        app = self.make_application(deadline_days=-1)
        Application.objects.filter(pk=app.pk).update(acceptance_deadline=None)

        response = self.node_client().post(
            f'/applications/{app.pk}/expire/', {'reason': 'try it'}, follow=True)
        app.refresh_from_db()

        self.assertEqual(app.status, 'accepted')
        self.assertContains(response, 'no acceptance deadline recorded')


class Step7ReinstateTest(AcceptanceRepairTestCase):
    """Step 7 (#18): the repair path for a mis-clicked expire."""

    def expired(self, resolution='accepted'):
        status = 'accepted' if resolution == 'accepted' else 'pending'
        app = self.make_application(
            status=status, resolution=resolution, deadline_days=-1,
            hours_approved=Decimal('8.0') if resolution == 'accepted' else None)
        self.node_client().post(f'/applications/{app.pk}/expire/', {'reason': 'Mis-click.'})
        app.refresh_from_db()
        self.assertEqual(app.status, 'expired')
        EmailLog.objects.filter(related_application_id=app.id).delete()
        return app

    def test_reinstate_get_renders_a_confirmation_screen(self):
        app = self.expired('accepted')

        response = self.node_client().get(f'/applications/{app.pk}/reinstate/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'applications/reinstate_confirm.html')
        app.refresh_from_db()
        self.assertEqual(app.status, 'expired')

    def test_detail_page_offers_reinstate_to_a_coordinator(self):
        app = self.expired('accepted')

        response = self.node_client().get(f'/applications/{app.pk}/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'/applications/{app.id}/reinstate/')

    def test_detail_page_does_not_offer_reinstate_to_the_applicant(self):
        app = self.expired('accepted')

        client = Client()
        client.force_login(self.applicant)
        response = client.get(f'/applications/{app.pk}/')

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, f'/applications/{app.id}/reinstate/')

    def test_expired_is_no_longer_a_terminal_state(self):
        self.assertEqual(
            Application.VALID_TRANSITIONS['expired'], ['accepted', 'pending'])

    def test_reinstate_restores_the_status_the_resolution_names(self):
        app = self.expired('accepted')

        self.node_client().post(
            f'/applications/{app.pk}/reinstate/', {'reason': 'Expired by mistake.'})
        app.refresh_from_db()

        self.assertEqual(app.status, 'accepted')
        self.assertIsNone(app.accepted_by_applicant)
        self.assertIsNone(app.accepted_at)
        self.assertIn('[REINSTATED BY COORDINATOR]', app.resolution_comments)
        self.assertIn('Expired by mistake.', app.resolution_comments)

    def test_reinstate_restores_a_waitlisted_application_to_pending(self):
        app = self.expired('pending')

        self.node_client().post(
            f'/applications/{app.pk}/reinstate/', {'reason': 'Expired by mistake.'})
        app.refresh_from_db()

        self.assertEqual(app.status, 'pending')

    def test_reinstate_sets_a_fresh_ten_day_deadline(self):
        app = self.expired('accepted')

        self.node_client().post(
            f'/applications/{app.pk}/reinstate/', {'reason': 'Expired by mistake.'})
        app.refresh_from_db()

        remaining = app.acceptance_deadline - timezone.now()
        self.assertGreater(remaining, timedelta(days=9, hours=23))
        self.assertLessEqual(remaining, timedelta(days=10))
        self.assertFalse(app.acceptance_deadline_passed)

    def test_reinstate_tells_the_applicant_their_link_works_again(self):
        app = self.expired('accepted')

        self.node_client().post(
            f'/applications/{app.pk}/reinstate/', {'reason': 'Expired by mistake.'})

        log = self.logs('acceptance_reminder', app).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.recipient_email, app.applicant_email)
        self.assertIn(f'/applications/{app.id}/accept/', log.text_content)

    def test_reinstate_notifies_the_redib_coordinator(self):
        app = self.expired('accepted')

        self.node_client().post(
            f'/applications/{app.pk}/reinstate/', {'reason': 'Expired by mistake.'})

        log = self.logs('stalled_acceptance_actioned', app).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.recipient_email, self.redib_coordinator.email)
        self.assertIn('reinstated', log.text_content)

    def test_reinstated_application_can_be_accepted_by_the_applicant(self):
        """The whole point: the applicant's link works again."""
        app = self.expired('accepted')
        self.node_client().post(
            f'/applications/{app.pk}/reinstate/', {'reason': 'Expired by mistake.'})

        client = Client()
        client.force_login(self.applicant)
        client.post(f'/applications/{app.pk}/accept/', {'action': 'accept'})
        app.refresh_from_db()

        self.assertTrue(app.accepted_by_applicant)
        self.assertIsNotNone(app.handoff_email_sent_at)

    def test_reinstate_refused_without_a_reason(self):
        app = self.expired('accepted')

        self.node_client().post(f'/applications/{app.pk}/reinstate/', {'reason': ''})
        app.refresh_from_db()

        self.assertEqual(app.status, 'expired')

    def test_reinstate_refused_on_a_non_expired_application(self):
        app = self.make_application(status='accepted', deadline_days=-1)

        self.node_client().post(f'/applications/{app.pk}/reinstate/', {'reason': 'Why not.'})
        app.refresh_from_db()

        self.assertEqual(app.status, 'accepted')

    def test_reinstate_refused_when_the_resolution_names_no_window(self):
        """An application expired out of some other resolution has nothing
        to restore."""
        app = self.expired('accepted')
        Application.objects.filter(pk=app.pk).update(resolution='rejected')

        self.node_client().post(f'/applications/{app.pk}/reinstate/', {'reason': 'Try it.'})
        app.refresh_from_db()

        self.assertEqual(app.status, 'expired')

    def test_reinstate_refused_for_an_unrelated_node_coordinator(self):
        other_node = Node.objects.create(
            code='OTHER-NODE-2', organization=self.org, location='Elsewhere')
        outsider = create_complete_user(email='outsider2@repair.test', organization=self.org)
        UserRole.objects.create(
            user=outsider, role='node_coordinator', node=other_node, is_active=True)
        app = self.expired('accepted')

        client = Client()
        client.force_login(outsider)
        client.post(f'/applications/{app.pk}/reinstate/', {'reason': 'not mine'})
        app.refresh_from_db()

        self.assertEqual(app.status, 'expired')

    def test_reinstated_application_runs_the_reminder_ladder_again(self):
        """The ladder is anchored on acceptance_deadline, not
        resolution_date, precisely so a fresh window is chased."""
        app = self.expired('accepted')
        self.node_client().post(
            f'/applications/{app.pk}/reinstate/', {'reason': 'Expired by mistake.'})
        app.refresh_from_db()
        EmailLog.objects.filter(related_application_id=app.id).delete()

        app.acceptance_deadline = timezone.now() + timedelta(days=3)
        app.save(update_fields=['acceptance_deadline'])
        process_acceptance_deadlines()

        self.assertTrue(self.logs('acceptance_reminder', app).exists())
