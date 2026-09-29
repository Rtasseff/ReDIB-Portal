"""
Tests for backlog #92: bots registering fake accounts through the public
signup form, each one emailing a verification link to a stranger.

- the signup form's browser check (core.forms.SignupForm) and allauth's
  honeypot and rate limit, as configured in settings;
- the applicant role, granted on email confirmation instead of at signup;
- purge_unverified_signups, which deletes the accounts the bots left behind.
"""
import re
import time
from datetime import timedelta
from io import StringIO
from unittest import mock

from allauth.account.models import EmailAddress
from allauth.account.signals import email_confirmed
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail, signing
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from applications.models import Application
from calls.models import Call
from core.forms import SignupForm
from core.management.commands.purge_unverified_signups import CHANGE_REASON
from core.models import UserRole

User = get_user_model()

PASSWORD = 'Imaging-Portal-2026'
REFUSED = 'We could not complete your registration'


def browser_check_token(age_seconds):
    """The token the signup page would carry, as if rendered age_seconds ago."""
    issued = time.time() - age_seconds
    with mock.patch('time.time', return_value=issued):
        return signing.dumps(issued, salt=SignupForm.BROWSER_CHECK_SALT)


class SignupMixin:
    def setUp(self):
        super().setUp()
        cache.clear()  # allauth's signup rate limit counts in the cache

    def signup(self, email='researcher@example.org', **overrides):
        data = {
            'email': email,
            'email2': email,
            'password1': PASSWORD,
            'password2': PASSWORD,
            'browser_check': browser_check_token(age_seconds=30),
        }
        data.update(overrides)
        return self.client.post(reverse('account_signup'), data)


class SignupBotProtectionTest(SignupMixin, TestCase):

    def assertRefused(self, browser_check, reason):
        with self.assertLogs('core.forms', 'WARNING') as logs:
            response = self.signup(browser_check=browser_check)
        self.assertIn(reason, logs.output[0])
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, REFUSED)
        self.assertFalse(User.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_page_carries_the_honeypot_and_a_valid_token(self):
        content = self.client.get(reverse('account_signup')).content.decode()
        self.assertIn(f'name="{settings.ACCOUNT_SIGNUP_FORM_HONEYPOT_FIELD}"', content)
        self.assertIn('name="browser_check"', content)
        token = re.search(r'data-token="([^"]+)"', content).group(1)
        issued = signing.loads(token, salt=SignupForm.BROWSER_CHECK_SALT)
        self.assertAlmostEqual(issued, time.time(), delta=60)

    def test_browser_signup_creates_an_unconfirmed_account_without_a_role(self):
        response = self.signup()
        self.assertRedirects(
            response, reverse('account_email_verification_sent'),
            fetch_redirect_response=False,
        )
        user = User.objects.get(email='researcher@example.org')
        self.assertFalse(EmailAddress.objects.get(user=user).verified)
        self.assertEqual([m.to for m in mail.outbox], [['researcher@example.org']])
        self.assertFalse(user.roles.exists())

    def test_post_without_the_token_is_refused(self):
        self.assertRefused('', 'no token')

    def test_token_signed_with_another_salt_is_refused(self):
        forged = signing.dumps(time.time() - 30, salt='something-else')
        self.assertRefused(forged, 'no token')

    def test_submitting_straight_after_the_page_rendered_is_refused(self):
        self.assertRefused(browser_check_token(age_seconds=0), 'too fast')

    def test_page_left_open_for_two_days_is_refused(self):
        self.assertRefused(browser_check_token(age_seconds=2 * 24 * 3600), 'over a day')

    def test_honeypot_fakes_success_without_an_account_or_an_email(self):
        response = self.signup(**{settings.ACCOUNT_SIGNUP_FORM_HONEYPOT_FIELD: 'http://spam.example'})
        self.assertRedirects(
            response, reverse('account_email_verification_sent'),
            fetch_redirect_response=False,
        )
        self.assertFalse(User.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_eleventh_signup_post_in_an_hour_from_one_ip_is_rate_limited(self):
        for i in range(10):
            self.assertEqual(self.signup(email=f'person{i}@example.org').status_code, 302)
        self.assertEqual(self.signup(email='person10@example.org').status_code, 429)
        self.assertEqual(User.objects.count(), 10)

    def test_rate_limit_counts_the_client_ip_that_caddy_forwards(self):
        # Behind Caddy every request comes from the same REMOTE_ADDR. Without
        # ALLAUTH_TRUSTED_PROXY_COUNT all visitors shared one limit.
        for i in range(11):
            response = self.client.post(reverse('account_signup'), {
                'email': f'person{i}@example.org', 'email2': f'person{i}@example.org',
                'password1': PASSWORD, 'password2': PASSWORD,
                'browser_check': browser_check_token(age_seconds=30),
            }, HTTP_X_FORWARDED_FOR=f'203.0.113.{i}')
            self.assertEqual(response.status_code, 302)


class ApplicantRoleOnConfirmationTest(SignupMixin, TestCase):

    def test_confirming_the_email_grants_the_applicant_role(self):
        self.signup()
        user = User.objects.get(email='researcher@example.org')
        self.assertFalse(user.roles.exists())

        confirm_path = re.search(r'/accounts/confirm-email/[^/\s]+/', mail.outbox[0].body).group(0)
        self.client.post(confirm_path)

        self.assertTrue(EmailAddress.objects.get(user=user).verified)
        self.assertTrue(
            UserRole.objects.filter(user=user, role='applicant', is_active=True).exists()
        )

    def test_a_deactivated_applicant_role_is_not_reactivated(self):
        self.signup()
        user = User.objects.get(email='researcher@example.org')
        UserRole.objects.create(user=user, role='applicant', is_active=False)

        confirm_path = re.search(r'/accounts/confirm-email/[^/\s]+/', mail.outbox[0].body).group(0)
        self.client.post(confirm_path)

        self.assertEqual(
            list(user.roles.values_list('role', 'is_active')), [('applicant', False)]
        )

    def test_provisioned_evaluator_confirming_a_new_address_gets_no_applicant_role(self):
        evaluator = User.objects.create_user(
            username='evaluator', email='evaluator@example.org', password=PASSWORD
        )
        EmailAddress.objects.create(
            user=evaluator, email='evaluator@example.org', verified=True, primary=True
        )
        UserRole.objects.create(user=evaluator, role='evaluator', is_active=True)
        added = EmailAddress.objects.create(
            user=evaluator, email='evaluator@new.example.org', verified=False
        )

        email_confirmed.send(sender=EmailAddress, request=None, email_address=added)

        self.assertEqual(list(evaluator.roles.values_list('role', flat=True)), ['evaluator'])


class PurgeUnverifiedSignupsTest(TestCase):

    def make_user(self, name, *, verified=False, joined_days_ago=30, roles=('applicant',),
                  **fields):
        email = f'{name}@example.org'
        user = User.objects.create_user(username=name, email=email, password=PASSWORD, **fields)
        if verified is not None:
            EmailAddress.objects.create(user=user, email=email, verified=verified, primary=True)
        for role in roles:
            UserRole.objects.create(user=user, role=role, is_active=True)
        User.objects.filter(pk=user.pk).update(
            date_joined=timezone.now() - timedelta(days=joined_days_ago)
        )
        return user

    def setUp(self):
        self.bot = self.make_user('bot')
        self.bot_without_role = self.make_user('bot2', roles=())
        self.kept = [
            self.make_user('recent', joined_days_ago=2),
            self.make_user('confirmed', verified=True),
            self.make_user('logged_in', last_login=timezone.now()),
            self.make_user('evaluator', roles=('applicant', 'evaluator')),
            self.make_user('admin_made', verified=None),
            self.make_user('staff', is_staff=True),
            self.make_user('has_draft'),
        ]
        now = timezone.now()
        call = Call.objects.create(
            code='CALL-1', title='Call',
            submission_start=now, submission_end=now + timedelta(days=30),
            evaluation_deadline=now + timedelta(days=60),
            execution_start=now + timedelta(days=70), execution_end=now + timedelta(days=100),
        )
        Application.objects.create(
            applicant=self.kept[-1], call=call, code='CALL-1-APP-001', status='draft'
        )

    def purge(self, *args):
        out = StringIO()
        call_command('purge_unverified_signups', *args, stdout=out)
        return out.getvalue()

    def test_dry_run_reports_and_deletes_nothing(self):
        output = self.purge('--dry-run')
        self.assertIn('2 account(s)', output)
        self.assertIn('1 hold the applicant role', output)
        self.assertIn('example.org 2', output)
        self.assertIn('Dry run', output)
        self.assertEqual(User.objects.count(), 9)

    def test_deletes_only_unconfirmed_never_used_signups(self):
        output = self.purge()
        self.assertIn('Deleted 2 account(s)', output)
        self.assertFalse(User.objects.filter(pk__in=[self.bot.pk, self.bot_without_role.pk]).exists())
        self.assertEqual(
            set(User.objects.values_list('pk', flat=True)), {u.pk for u in self.kept}
        )
        self.assertFalse(UserRole.objects.filter(user_id=self.bot.pk).exists())
        self.assertTrue(
            User.history.filter(
                id=self.bot.pk, history_type='-', history_change_reason=CHANGE_REASON
            ).exists()
        )

    def test_days_option_widens_the_window(self):
        self.purge('--days', '1')
        self.assertFalse(User.objects.filter(username='recent').exists())

    def test_nothing_to_delete(self):
        self.purge()
        self.assertIn('No unconfirmed sign-ups to delete.', self.purge())
