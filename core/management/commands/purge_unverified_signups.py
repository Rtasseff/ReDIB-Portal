"""
Delete accounts that signed up through the public form but never confirmed
their email and never logged in (backlog #92).

In 2026 a botnet registered ~1,400 of these with strangers' addresses. The
same rule also catches a real person who gave up before clicking the link;
they can simply register again.

Usage:
    python manage.py purge_unverified_signups --dry-run
    python manage.py purge_unverified_signups [--days 7]

An account is deleted only if every one of these holds:
- it has an allauth EmailAddress and none of its addresses is verified. The
  loaders and the manual recipe in data/README.md create a verified one, and
  an account made in the admin has none, so neither is touched;
- it has never logged in;
- it is not staff or a superuser;
- it holds no role other than applicant;
- it has no applications;
- it joined more than --days days ago (default 7, past the 3-day life of a
  confirmation link).
"""
from collections import Counter
from datetime import timedelta

from allauth.account.models import EmailAddress
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import User, UserRole

CHANGE_REASON = 'purge_unverified_signups: never confirmed their email (backlog #92)'


class Command(BaseCommand):
    help = 'Delete self-registered accounts that never confirmed their email or logged in.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Only accounts that joined more than this many days ago (default 7).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report what would be deleted without deleting anything.',
        )

    def handle(self, *args, days, dry_run, **options):
        candidates = (
            User.objects.filter(
                date_joined__lt=timezone.now() - timedelta(days=days),
                last_login__isnull=True,
                is_staff=False,
                is_superuser=False,
                pk__in=EmailAddress.objects.values('user'),
                applications__isnull=True,
            )
            .exclude(pk__in=EmailAddress.objects.filter(verified=True).values('user'))
            .exclude(pk__in=UserRole.objects.exclude(role='applicant').values('user'))
            .order_by('date_joined')
        )
        users = list(candidates)
        if not users:
            self.stdout.write('No unconfirmed sign-ups to delete.')
            return

        with_role = UserRole.objects.filter(user__in=candidates, role='applicant').count()
        domains = Counter(u.email.rsplit('@', 1)[-1].lower() for u in users)
        self.stdout.write(
            f'{len(users)} account(s) never confirmed their email and never logged in '
            f'(joined {users[0].date_joined:%Y-%m-%d} to {users[-1].date_joined:%Y-%m-%d}); '
            f'{with_role} hold the applicant role.'
        )
        self.stdout.write(
            'Most common email domains: '
            + ', '.join(f'{domain} {count}' for domain, count in domains.most_common(10))
        )
        if dry_run:
            self.stdout.write('Dry run: nothing deleted.')
            return

        with transaction.atomic():
            for user in users:
                user._change_reason = CHANGE_REASON  # recorded on the history row
                user.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {len(users)} account(s).'))
