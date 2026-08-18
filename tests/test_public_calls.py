"""
Tests for announced ("upcoming") calls and the public equipment consult form.

Two features, one branch (see docs/handoffs/public-calls.md):

A. A coordinator can *announce* a call: it becomes publicly visible under
   "Upcoming Calls" with its own detail page, takes no applications, and
   auto-promotes to `open` on `submission_start` (Celery Beat daily, with a
   view-level fallback in between).
B. Anyone — logged in or not — can request a consult about specific equipment
   listed on an announced or open call. The request is persisted and emailed
   to *every* active node coordinator of each node involved.
"""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from calls.models import Call, CallEquipmentAllocation, ConsultRequest
from calls.tasks import check_call_deadlines
from core.models import Organization, Node, Equipment, UserRole

User = get_user_model()


def _make_call(status='draft', starts_in_days=10, code='COA-TEST-1', num_nodes=1,
               coordinators_per_node=1):
    """Call + org + N nodes + one instrument per node, with NCs attached."""
    org = Organization.objects.create(
        name=f'Test Org {code}', short_name=f'TO-{code}', country='ES',
        organization_type='university',
    )
    now = timezone.now()
    call = Call.objects.create(
        code=code,
        title='Test Call',
        status=status,
        description='A call for testing.',
        submission_start=now + timedelta(days=starts_in_days),
        submission_end=now + timedelta(days=starts_in_days + 30),
        evaluation_deadline=now + timedelta(days=starts_in_days + 60),
        execution_start=now + timedelta(days=starts_in_days + 70),
        execution_end=now + timedelta(days=starts_in_days + 100),
    )
    equipment_list = []
    coordinators = []
    for node_index in range(num_nodes):
        node = Node.objects.create(
            code=f'{code}-N{node_index}', organization=org, location='Madrid',
        )
        equipment = Equipment.objects.create(
            node=node, name=f'MRI {node_index}', category='mri',
            area='preclinical', description='A scanner.',
        )
        CallEquipmentAllocation.objects.create(call=call, equipment=equipment)
        equipment_list.append(equipment)
        for coord_index in range(coordinators_per_node):
            coordinator = User.objects.create_user(
                username=f'nc-{code}-{node_index}{coord_index}',
                email=f'nc-{code}-{node_index}{coord_index}@test.com',
                password='x', first_name='Node', last_name='Coord',
                phone='+34 900 000 001', organization=org, position='NC',
            )
            UserRole.objects.create(
                user=coordinator, role='node_coordinator', node=node, is_active=True
            )
            coordinators.append(coordinator)
    return call, equipment_list, coordinators


def _seed_email_templates():
    """Email templates live in the DB; seed the real ones so tests exercise
    the same rendering path (and template syntax) as production."""
    call_command('seed_email_templates', verbosity=0)


def _make_coordinator(email='coord@test.com'):
    org = Organization.objects.create(
        name='ReDIB', country='ES', organization_type='research_center'
    )
    user = User.objects.create_user(
        username='coord', email=email, password='x',
        first_name='Coco', last_name='Ordinator',
        phone='+34 900 000 002', organization=org, position='Coordinator',
    )
    UserRole.objects.create(user=user, role='coordinator', is_active=True)
    return user


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage'
)
class AnnounceCallTests(TestCase):
    """A. Announce is a distinct action from Publish."""

    @classmethod
    def setUpTestData(cls):
        _seed_email_templates()

    def setUp(self):
        self.client = Client()
        self.coordinator = _make_coordinator()

    def test_announce_requires_coordinator_role(self):
        call, _, _ = _make_call()
        applicant = User.objects.create_user(
            username='app', email='app@test.com', password='x',
            first_name='A', last_name='B', phone='+34 900 000 003',
            organization=call.equipment_allocations.first().equipment.node.organization,
            position='Researcher',
        )
        UserRole.objects.create(user=applicant, role='applicant', is_active=True)
        self.client.force_login(applicant)

        response = self.client.get(reverse('calls:announce', kwargs={'pk': call.pk}))

        call.refresh_from_db()
        self.assertEqual(call.status, 'draft')
        self.assertRedirects(response, reverse('core:dashboard'),
                             fetch_redirect_response=False)

    def test_announce_sets_status_and_published_at(self):
        call, _, _ = _make_call()
        self.client.force_login(self.coordinator)

        self.client.get(reverse('calls:announce', kwargs={'pk': call.pk}))

        call.refresh_from_db()
        self.assertEqual(call.status, 'announced')
        self.assertIsNotNone(call.published_at)
        self.assertTrue(call.is_announced)
        self.assertTrue(call.is_publicly_visible)
        self.assertFalse(call.is_open)

    def test_announce_emails_opted_in_users_only(self):
        call, _, _ = _make_call()
        User.objects.create_user(
            username='sub', email='sub@test.com', password='x',
            receive_call_notifications=True,
        )
        User.objects.create_user(
            username='nosub', email='nosub@test.com', password='x',
            receive_call_notifications=False,
        )
        self.client.force_login(self.coordinator)
        mail.outbox = []

        self.client.get(reverse('calls:announce', kwargs={'pk': call.pk}))

        recipients = [address for message in mail.outbox for address in message.to]
        self.assertIn('sub@test.com', recipients)
        self.assertNotIn('nosub@test.com', recipients)
        self.assertTrue(
            any('Upcoming Call' in message.subject for message in mail.outbox),
            f"expected the announcement subject, got {[m.subject for m in mail.outbox]}"
        )

    def test_announce_refused_without_equipment(self):
        call, _, _ = _make_call()
        call.equipment_allocations.all().delete()
        self.client.force_login(self.coordinator)

        self.client.get(reverse('calls:announce', kwargs={'pk': call.pk}))

        call.refresh_from_db()
        self.assertEqual(call.status, 'draft')

    def test_announce_refused_when_already_started(self):
        call, _, _ = _make_call(starts_in_days=-1)
        self.client.force_login(self.coordinator)

        self.client.get(reverse('calls:announce', kwargs={'pk': call.pk}))

        call.refresh_from_db()
        self.assertEqual(call.status, 'draft')

    def test_publish_refused_when_start_is_in_the_future(self):
        call, _, _ = _make_call(starts_in_days=10)
        self.client.force_login(self.coordinator)
        mail.outbox = []

        response = self.client.get(
            reverse('calls:publish', kwargs={'pk': call.pk}), follow=True
        )

        call.refresh_from_db()
        self.assertEqual(call.status, 'draft')
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(response, 'Use Announce')

    def test_publish_opens_an_announced_call_whose_window_has_started(self):
        call, _, _ = _make_call(status='announced', starts_in_days=-1)
        self.client.force_login(self.coordinator)

        self.client.get(reverse('calls:publish', kwargs={'pk': call.pk}))

        call.refresh_from_db()
        self.assertEqual(call.status, 'open')

    def test_publish_refused_for_closed_call(self):
        call, _, _ = _make_call(status='closed', starts_in_days=-40)
        self.client.force_login(self.coordinator)

        self.client.get(reverse('calls:publish', kwargs={'pk': call.pk}))

        call.refresh_from_db()
        self.assertEqual(call.status, 'closed')


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage'
)
class AnnouncedCallVisibilityTests(TestCase):
    """A. Where announced calls do and do not show up."""

    def setUp(self):
        self.client = Client()

    def test_announced_call_listed_as_upcoming_with_link(self):
        call, _, _ = _make_call(status='announced')

        response = self.client.get(reverse('calls:public_list'))

        self.assertEqual(list(response.context['upcoming_calls']), [call])
        self.assertEqual(list(response.context['open_calls']), [])
        self.assertContains(
            response, reverse('calls:public_detail', kwargs={'pk': call.pk})
        )

    def test_draft_call_not_listed(self):
        _make_call(status='draft')

        response = self.client.get(reverse('calls:public_list'))

        self.assertEqual(list(response.context['upcoming_calls']), [])

    def test_announced_detail_shows_opens_on_and_no_apply(self):
        call, _, _ = _make_call(status='announced')

        response = self.client.get(
            reverse('calls:public_detail', kwargs={'pk': call.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['can_apply'])
        self.assertTrue(response.context['can_request_consult'])
        self.assertContains(response, 'Opens on')
        self.assertNotContains(response, 'Apply for Access')

    def test_draft_detail_is_404(self):
        call, _, _ = _make_call(status='draft')

        response = self.client.get(
            reverse('calls:public_detail', kwargs={'pk': call.pk})
        )

        self.assertEqual(response.status_code, 404)

    def test_announced_call_absent_from_evaluation_and_report_surfaces(self):
        _make_call(status='announced')

        self.assertFalse(
            Call.objects.filter(status__in=['open', 'closed']).exists(),
            "announced calls must not leak into open/closed-only querysets"
        )


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage'
)
class AutoOpenTests(TestCase):
    """A. Announced calls open by themselves on their start date."""

    @classmethod
    def setUpTestData(cls):
        _seed_email_templates()

    def test_beat_task_promotes_and_emails_once(self):
        call, _, _ = _make_call(status='announced', starts_in_days=-1)
        User.objects.create_user(
            username='sub', email='sub@test.com', password='x',
            receive_call_notifications=True,
        )
        mail.outbox = []

        check_call_deadlines()

        call.refresh_from_db()
        self.assertEqual(call.status, 'open')
        now_open = [
            m for m in mail.outbox
            if 'Now Open' in m.subject and 'sub@test.com' in m.to
        ]
        self.assertEqual(len(now_open), 1)

        # A second run must not re-send: the call is no longer announced.
        mail.outbox = []
        check_call_deadlines()
        self.assertEqual(len(mail.outbox), 0)

    def test_beat_task_leaves_future_calls_announced(self):
        call, _, _ = _make_call(status='announced', starts_in_days=5)

        check_call_deadlines()

        call.refresh_from_db()
        self.assertEqual(call.status, 'announced')

    def test_view_fallback_promotes_on_public_list(self):
        call, _, _ = _make_call(status='announced', starts_in_days=-1)

        response = self.client.get(reverse('calls:public_list'))

        call.refresh_from_db()
        self.assertEqual(call.status, 'open')
        self.assertEqual(list(response.context['open_calls']), [call])

    def test_view_fallback_promotes_even_when_celery_is_down(self):
        """The status change is the point; a dead broker only costs the email."""
        call, _, _ = _make_call(status='announced', starts_in_days=-1)
        User.objects.create_user(
            username='sub', email='sub@test.com', password='x',
            receive_call_notifications=True,
        )
        mail.outbox = []

        with patch(
            'communications.tasks.send_email_from_template.delay',
            side_effect=OSError('broker down'),
        ):
            self.client.get(reverse('calls:public_list'))

        call.refresh_from_db()
        self.assertEqual(call.status, 'open')
        self.assertEqual(len(mail.outbox), 0)


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage'
)
class ConsultRequestFormTests(TestCase):
    """B. Form contract."""

    def setUp(self):
        cache.clear()
        self.client = Client()

    def _post(self, call, **overrides):
        data = {
            'name': 'Rita Requester',
            'email': 'rita@example.org',
            'phone': '+34 900 111 222',
            'organization': 'Example University',
            'message': 'Is this scanner suitable for mouse brain imaging?',
            'website': '',
        }
        data.update(overrides)
        return self.client.post(
            reverse('calls:public_consult', kwargs={'pk': call.pk}), data
        )

    def test_equipment_is_required(self):
        call, _, _ = _make_call(status='announced')

        response = self._post(call)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ConsultRequest.objects.count(), 0)
        self.assertContains(response, 'Select at least one instrument')

    def test_equipment_must_belong_to_this_call(self):
        call, _, _ = _make_call(status='announced')
        other_call, other_equipment, _ = _make_call(
            status='announced', code='COA-TEST-2'
        )

        response = self._post(call, equipment=[other_equipment[0].pk])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ConsultRequest.objects.count(), 0)

    def test_honeypot_blocks_submission(self):
        call, equipment, _ = _make_call(status='announced')

        response = self._post(call, equipment=[equipment[0].pk], website='http://spam')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ConsultRequest.objects.count(), 0)

    def test_logged_in_user_gets_prefilled_editable_fields(self):
        call, _, _ = _make_call(status='announced')
        org = Organization.objects.create(
            name='Applicant Org', country='ES', organization_type='university'
        )
        applicant = User.objects.create_user(
            username='app', email='app@test.com', password='x',
            first_name='Aida', last_name='Applicant',
            phone='+34 900 000 000', organization=org, position='Researcher',
        )
        self.client.force_login(applicant)

        response = self.client.get(
            reverse('calls:public_consult', kwargs={'pk': call.pk})
        )

        initial = response.context['form'].initial
        self.assertEqual(initial['name'], 'Aida Applicant')
        self.assertEqual(initial['email'], 'app@test.com')
        self.assertEqual(initial['phone'], '+34 900 000 000')
        self.assertEqual(initial['organization'], 'Applicant Org')

    def test_equipment_query_param_preselects(self):
        call, equipment, _ = _make_call(status='announced')
        url = reverse('calls:public_consult', kwargs={'pk': call.pk})

        response = self.client.get(f'{url}?equipment={equipment[0].pk}')

        groups = response.context['form'].grouped_equipment()
        checked = [
            item['equipment'].pk
            for group in groups for item in group['items'] if item['checked']
        ]
        self.assertEqual(checked, [equipment[0].pk])

    def test_form_only_offers_equipment_on_this_call(self):
        call, equipment, _ = _make_call(status='announced')
        _make_call(status='announced', code='COA-TEST-2')

        response = self.client.get(
            reverse('calls:public_consult', kwargs={'pk': call.pk})
        )

        offered = list(response.context['form'].fields['equipment'].queryset)
        self.assertEqual(offered, equipment)


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage'
)
class ConsultRequestSubmissionTests(TestCase):
    """B. Persistence, routing and email fan-out."""

    @classmethod
    def setUpTestData(cls):
        _seed_email_templates()

    def setUp(self):
        cache.clear()
        self.client = Client()

    def _submit(self, call, equipment_ids, **overrides):
        data = {
            'equipment': equipment_ids,
            'name': 'Rita Requester',
            'email': 'rita@example.org',
            'phone': '+34 900 111 222',
            'organization': 'Example University',
            'message': 'Is this scanner suitable for mouse brain imaging?',
            'website': '',
        }
        data.update(overrides)
        return self.client.post(
            reverse('calls:public_consult', kwargs={'pk': call.pk}), data
        )

    def test_anonymous_submission_creates_row_and_emails_everyone(self):
        call, equipment, coordinators = _make_call(
            status='announced', num_nodes=2, coordinators_per_node=2
        )
        mail.outbox = []

        response = self._submit(call, [equipment[0].pk, equipment[1].pk])

        self.assertRedirects(
            response,
            reverse('calls:public_consult_thanks', kwargs={'pk': call.pk}),
            fetch_redirect_response=False,
        )

        consult = ConsultRequest.objects.get()
        self.assertEqual(consult.call, call)
        self.assertIsNone(consult.user)
        self.assertEqual(consult.name, 'Rita Requester')
        self.assertEqual(consult.equipment.count(), 2)
        self.assertIsNotNone(consult.emails_sent_at)
        self.assertTrue(consult.ip_hash)

        recipients = [address for message in mail.outbox for address in message.to]
        # All four node coordinators (2 nodes x 2 NCs), not just the first.
        for coordinator in coordinators:
            self.assertIn(coordinator.email, recipients)
        # Plus the confirmation to the requester.
        self.assertIn('rita@example.org', recipients)
        self.assertEqual(len(mail.outbox), len(coordinators) + 1)

    def test_only_the_selected_nodes_are_notified(self):
        call, equipment, coordinators = _make_call(status='announced', num_nodes=2)
        mail.outbox = []

        self._submit(call, [equipment[0].pk])

        recipients = [address for message in mail.outbox for address in message.to]
        self.assertIn(coordinators[0].email, recipients)
        self.assertNotIn(coordinators[1].email, recipients)

    def test_logged_in_submission_records_the_user(self):
        call, equipment, _ = _make_call(status='announced')
        org = Organization.objects.create(
            name='Applicant Org', country='ES', organization_type='university'
        )
        applicant = User.objects.create_user(
            username='app', email='app@test.com', password='x',
            first_name='Aida', last_name='Applicant',
            phone='+34 900 000 000', organization=org, position='Researcher',
        )
        self.client.force_login(applicant)

        self._submit(call, [equipment[0].pk])

        consult = ConsultRequest.objects.get()
        self.assertEqual(consult.user, applicant)

    def test_node_without_coordinator_falls_back_to_redib_coordinator(self):
        call, equipment, _ = _make_call(status='announced', coordinators_per_node=0)
        redib_coordinator = _make_coordinator(email='redib@test.com')
        mail.outbox = []

        response = self._submit(call, [equipment[0].pk])

        self.assertEqual(ConsultRequest.objects.count(), 1)
        recipients = [address for message in mail.outbox for address in message.to]
        self.assertIn(redib_coordinator.email, recipients)
        self.assertIn('rita@example.org', recipients)
        self.assertEqual(response.status_code, 302)

    def test_open_call_accepts_consult_requests(self):
        call, equipment, _ = _make_call(status='open', starts_in_days=-1)

        self._submit(call, [equipment[0].pk])

        self.assertEqual(ConsultRequest.objects.count(), 1)

    def test_closed_call_refuses_consult_requests(self):
        call, equipment, _ = _make_call(status='closed', starts_in_days=-40)

        response = self.client.get(
            reverse('calls:public_consult', kwargs={'pk': call.pk})
        )

        self.assertRedirects(
            response,
            reverse('calls:public_detail', kwargs={'pk': call.pk}),
            fetch_redirect_response=False,
        )
        self.assertEqual(ConsultRequest.objects.count(), 0)

    def test_draft_call_consult_is_404(self):
        call, _, _ = _make_call(status='draft')

        response = self.client.get(
            reverse('calls:public_consult', kwargs={'pk': call.pk})
        )

        self.assertEqual(response.status_code, 404)

    def test_thanks_page_names_the_nodes_and_contact_address(self):
        call, equipment, _ = _make_call(status='announced')

        self._submit(call, [equipment[0].pk])
        response = self.client.get(
            reverse('calls:public_consult_thanks', kwargs={'pk': call.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'rita@example.org')
        self.assertContains(response, 'TO-COA-TEST-1')

    def test_row_survives_email_dispatch_failure(self):
        call, equipment, _ = _make_call(status='announced')

        with patch(
            'communications.tasks.send_email_from_template.delay',
            side_effect=OSError('broker down'),
        ):
            self._submit(call, [equipment[0].pk])

        consult = ConsultRequest.objects.get()
        self.assertIsNone(consult.emails_sent_at)


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage'
)
class ConsultRateLimitTests(TestCase):
    """B. Cache-backed abuse protection (no captcha)."""

    def setUp(self):
        cache.clear()
        self.client = Client()

    def tearDown(self):
        cache.clear()

    def _submit(self, call, equipment_ids, message='Question', **extra):
        data = {
            'equipment': equipment_ids,
            'name': 'Rita Requester',
            'email': 'rita@example.org',
            'phone': '',
            'organization': '',
            'message': message,
            'website': '',
        }
        return self.client.post(
            reverse('calls:public_consult', kwargs={'pk': call.pk}), data, **extra
        )

    def test_identical_request_within_ten_minutes_is_not_duplicated(self):
        call, equipment, _ = _make_call(status='announced')

        self._submit(call, [equipment[0].pk])
        self._submit(call, [equipment[0].pk])

        self.assertEqual(ConsultRequest.objects.count(), 1)

    def test_sixth_submission_from_one_ip_is_refused(self):
        call, equipment, _ = _make_call(
            status='announced', num_nodes=5, coordinators_per_node=1
        )

        # Five distinct equipment sets get through; the sixth is throttled.
        for index in range(5):
            self._submit(call, [equipment[index].pk], message=f'Question {index}')
        self.assertEqual(ConsultRequest.objects.count(), 5)

        response = self._submit(
            call, [equipment[0].pk, equipment[1].pk], message='One more'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ConsultRequest.objects.count(), 5)
        self.assertContains(response, 'several consult requests recently')


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage'
)
class ConsultVisibilityTests(TestCase):
    """B. Who can see the requests afterwards."""

    def setUp(self):
        cache.clear()
        self.client = Client()

    def _make_consult(self, call, equipment, name='Rita Requester'):
        consult = ConsultRequest.objects.create(
            call=call, name=name, email='rita@example.org',
            organization='Example University', message='A question.',
        )
        consult.equipment.set(equipment)
        return consult

    def test_coordinator_call_detail_lists_requests(self):
        call, equipment, _ = _make_call(status='announced')
        self._make_consult(call, [equipment[0]])
        self.client.force_login(_make_coordinator())

        response = self.client.get(reverse('calls:detail', kwargs={'pk': call.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Consult Requests')
        self.assertContains(response, 'rita@example.org')

    def test_consult_requests_page_shows_all_to_redib_coordinator(self):
        call, equipment, _ = _make_call(status='announced', num_nodes=2)
        self._make_consult(call, [equipment[0]], name='First Requester')
        self._make_consult(call, [equipment[1]], name='Second Requester')
        self.client.force_login(_make_coordinator())

        response = self.client.get(
            reverse('calls:consult_requests', kwargs={'pk': call.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'First Requester')
        self.assertContains(response, 'Second Requester')

    def test_node_coordinator_sees_only_their_own_nodes_requests(self):
        call, equipment, coordinators = _make_call(status='announced', num_nodes=2)
        self._make_consult(call, [equipment[0]], name='First Requester')
        self._make_consult(call, [equipment[1]], name='Second Requester')
        self.client.force_login(coordinators[0])

        response = self.client.get(
            reverse('calls:consult_requests', kwargs={'pk': call.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'First Requester')
        self.assertNotContains(response, 'Second Requester')

    def test_applicant_cannot_see_consult_requests(self):
        call, equipment, _ = _make_call(status='announced')
        self._make_consult(call, [equipment[0]])
        org = Organization.objects.create(
            name='Applicant Org', country='ES', organization_type='university'
        )
        applicant = User.objects.create_user(
            username='app', email='app@test.com', password='x',
            first_name='Aida', last_name='Applicant',
            phone='+34 900 000 000', organization=org, position='Researcher',
        )
        UserRole.objects.create(user=applicant, role='applicant', is_active=True)
        self.client.force_login(applicant)

        response = self.client.get(
            reverse('calls:consult_requests', kwargs={'pk': call.pk})
        )

        self.assertRedirects(response, reverse('core:dashboard'),
                             fetch_redirect_response=False)


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage'
)
class ConsultMiddlewareExemptionTests(TestCase):
    """B. An incomplete profile must not block an informal enquiry."""

    def setUp(self):
        cache.clear()
        self.client = Client()

    def test_incomplete_profile_can_reach_the_consult_form(self):
        call, _, _ = _make_call(status='announced')
        user = User.objects.create_user(
            username='incomplete', email='incomplete@test.com', password='x',
        )
        self.assertFalse(user.is_profile_complete)
        self.client.force_login(user)

        response = self.client.get(
            reverse('calls:public_consult', kwargs={'pk': call.pk})
        )

        self.assertEqual(response.status_code, 200)

    def test_incomplete_profile_is_still_redirected_elsewhere(self):
        user = User.objects.create_user(
            username='incomplete', email='incomplete@test.com', password='x',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('core:dashboard'))

        self.assertRedirects(response, reverse('core:profile'),
                             fetch_redirect_response=False)


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage'
)
class CallStatusNotEditableTests(TestCase):
    """#27 — `status` must not be settable through `CallForm`.

    The 2026-08-18 production walkthrough found that hand-setting it created
    states no guard catches: `announced` that can never send its announcement
    (the Announce action requires `draft`), and `open` with a future
    `submission_start`, which falls out of both public querysets while staying
    live at its direct URL. Transitions belong to the guarded action views.
    """

    def _form_data(self, call, **overrides):
        data = {
            'code': call.code,
            'title': call.title,
            'description': call.description,
            'guidelines': call.guidelines,
            'submission_start': call.submission_start.strftime('%Y-%m-%dT%H:%M'),
            'submission_end': call.submission_end.strftime('%Y-%m-%dT%H:%M'),
            'evaluation_deadline': call.evaluation_deadline.strftime('%Y-%m-%dT%H:%M'),
            'execution_start': call.execution_start.strftime('%Y-%m-%dT%H:%M'),
            'execution_end': call.execution_end.strftime('%Y-%m-%dT%H:%M'),
        }
        data.update(overrides)
        return data

    def test_status_is_not_a_form_field(self):
        from calls.forms import CallForm
        self.assertNotIn('status', CallForm().fields)

    def test_smuggled_status_is_ignored_on_edit(self):
        from calls.forms import CallForm
        call, _, _ = _make_call(status='announced', code='COA-STATUS-1')
        form = CallForm(data=self._form_data(call, status='open'), instance=call)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        call.refresh_from_db()
        self.assertEqual(call.status, 'announced')

    def test_smuggled_status_is_ignored_on_create(self):
        from calls.forms import CallForm
        template, _, _ = _make_call(status='draft', code='COA-STATUS-2')
        data = self._form_data(template, code='COA-STATUS-3', status='open')
        form = CallForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        created = form.save()
        self.assertEqual(created.status, 'draft')


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage'
)
class TotalApprovedHoursTests(TestCase):
    """#33 — the "Total Approved Hours" figure summed `hours_requested`.

    On REDIB-2601 that reported 2,176 h against a true 1,991 h. Approved
    hours are the truth; requested is only a fallback for a line the node has
    not resolved yet.
    """

    def setUp(self):
        from decimal import Decimal
        from applications.models import Application, RequestedAccess

        self.call, equipment, coordinators = _make_call(
            status='closed', code='COA-HOURS-1', num_nodes=2,
        )
        self.equipment = equipment
        application = Application.objects.create(
            applicant=coordinators[0], call=self.call, code='COA-HOURS-1-001',
            brief_description='hours test', status='accepted',
            resolution='accepted', applicant_email='a@test.com',
        )
        # Resolved line: 40 h asked, 25 h granted.
        RequestedAccess.objects.create(
            application=application, equipment=equipment[0],
            hours_requested=Decimal('40'), hours_approved=Decimal('25'),
        )
        # Unresolved line: nothing granted yet, so requested stands in.
        RequestedAccess.objects.create(
            application=application, equipment=equipment[1],
            hours_requested=Decimal('10'),
        )

    def test_call_total_uses_approved_hours(self):
        from decimal import Decimal
        self.assertEqual(self.call.total_approved_hours, Decimal('35'))

    def test_allocation_total_uses_approved_hours(self):
        from decimal import Decimal
        allocation = self.call.equipment_allocations.get(equipment=self.equipment[0])
        self.assertEqual(allocation.total_approved_hours, Decimal('25'))
