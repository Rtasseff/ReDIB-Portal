#!/usr/bin/env python
"""Dress-rehearsal harness for a COA call, on the local dev sandbox only.

Lets a human walk the real October sequence — announce, open, submit, nudge,
close — in an afternoon instead of ten weeks, and see exactly which emails the
system would send at each step *before* any of it happens for real.

    python scripts/rehearsal.py seed          # sandbox + one draft call
    python scripts/rehearsal.py status        # where is everything right now
    python scripts/rehearsal.py advance 30    # simulate 30 days passing
    python scripts/rehearsal.py beat          # run all 10 beat tasks, report
    python scripts/rehearsal.py inbox         # every email the sandbox "sent"
    python scripts/rehearsal.py inbox --full  # ...with bodies

This is test scaffolding. It is never imported by the app, never run by the
deploy, and it **refuses to run unless DEBUG is on and the database is
SQLite** — the two conditions that together mean "this is a dev checkout".
See docs/developer/dress-rehearsal.md for the click-through script it goes with.

Why simulating time works here: nothing in this system stores "now". Call
transitions compare `submission_start`/`submission_end` against the clock, and
the reminder ladders measure elapsed days from an anchor. So moving a call's
dates backwards by N days is indistinguishable, to every code path, from N days
having passed — with the one exception noted under `advance` below.
"""
import argparse
import os
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redib.settings')

import django  # noqa: E402
django.setup()

from django.conf import settings  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.utils import timezone  # noqa: E402


REHEARSAL_CODE = 'REHEARSAL-2701'

# Every scheduled task, in beat-schedule order. Kept as (label, dotted path) so
# a task that disappears is reported as missing rather than silently skipped —
# this list is also a check that redib/celery.py still says what we think.
BEAT_TASKS = [
    ('08:00  waitlist digest',        'applications.tasks.send_waitlist_digest'),
    ('08:15  completion reminders',   'applications.tasks.send_completion_reminders'),
    ('08:30  draft nudges',           'calls.tasks.send_draft_nudges'),
    ('09:00  feasibility reminders',  'applications.tasks.send_feasibility_reminders'),
    ('09:00  evaluation reminders',   'evaluations.tasks.send_evaluation_reminders'),
    ('09:45  coordinator overdue',    'evaluations.tasks.notify_coordinator_overdue_evaluations'),
    ('10:00  acceptance deadlines',   'applications.tasks.process_acceptance_deadlines'),
    ('10:00  publication followups',  'access.tasks.send_publication_followups'),
    ('10:15  stalled acceptance',     'applications.tasks.send_stalled_acceptance_reminders'),
    ('00:15  call deadlines',         'calls.tasks.check_call_deadlines'),
]

DATE_FIELDS = [
    'submission_start', 'submission_end', 'evaluation_deadline',
    'execution_start', 'execution_end',
]


def guard():
    """Refuse to touch anything that isn't an obvious dev sandbox."""
    engine = settings.DATABASES['default']['ENGINE']
    name = str(settings.DATABASES['default']['NAME'])
    problems = []
    if not settings.DEBUG:
        problems.append('DEBUG is False — this looks like a real deployment')
    if 'sqlite' not in engine:
        problems.append(f'database engine is {engine}, not SQLite')
    if problems:
        print('REFUSING TO RUN. This script is for the local dev sandbox only.')
        for p in problems:
            print(f'  - {p}')
        sys.exit(1)
    return name


def get_call():
    from calls.models import Call
    try:
        return Call.objects.get(code=REHEARSAL_CODE)
    except Call.DoesNotExist:
        print(f'No {REHEARSAL_CODE} found. Run:  python scripts/rehearsal.py seed')
        sys.exit(1)


# --------------------------------------------------------------------------- seed
def cmd_seed(args):
    from calls.models import Call, CallEquipmentAllocation
    from applications.models import Application
    from communications.models import EmailLog
    from core.models import Equipment

    print('Seeding the base sandbox (users, nodes, equipment, organizations)...')
    call_command('setup_localtest3_database', reset=True, yes=True, verbosity=0)

    # localtest3 ships two calls and 16 applications so every screen has
    # something on it. A rehearsal has to start from nothing, or we are
    # testing the seed data instead of the workflow.
    Application.objects.all().delete()
    Call.objects.all().delete()
    EmailLog.objects.all().delete()

    now = timezone.now()

    def at(days, hour=23, minute=59):
        d = (now + timedelta(days=days)).astimezone(timezone.get_current_timezone())
        return d.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # Shaped like the real October call, measured from today so the rehearsal
    # starts where the real one does: announced two weeks out, opening a month
    # after that.
    call = Call.objects.create(
        code=REHEARSAL_CODE,
        title='Dress rehearsal — 2027 Competitive Open Access',
        status='draft',
        submission_start=at(14, hour=9, minute=0),
        submission_end=at(60),
        evaluation_deadline=at(100),
        execution_start=at(140, hour=9, minute=0),
        execution_end=at(320),
        description='<p>Rehearsal call. Not real. Safe to break.</p>',
        guidelines='<p>Rehearsal guidelines.</p>',
    )

    equipment = list(Equipment.objects.all())
    for eq in equipment:
        CallEquipmentAllocation.objects.get_or_create(call=call, equipment=eq)

    print(f'\n  {REHEARSAL_CODE} created as DRAFT with {len(equipment)} instruments.')
    print(f'  Opens in 14 days, closes in 60. No applications yet — that is the point.')
    print('\nNext:  python manage.py runserver')
    print('       then follow docs/developer/dress-rehearsal.md from Stage 1.')
    cmd_status(args)


# ------------------------------------------------------------------------- status
def cmd_status(args):
    from applications.models import Application
    from communications.models import EmailLog

    call = get_call()
    now = timezone.now()

    print('\n' + '=' * 70)
    print(f'{call.code}   status={call.status.upper()}   '
          f'{"released" if call.resolutions_released else "resolutions GATED"}')
    print('=' * 70)
    for f in DATE_FIELDS:
        when = getattr(call, f)
        days = (when - now).days
        when_str = timezone.localtime(when).strftime('%Y-%m-%d %H:%M')
        if days < 0:
            rel = f'{-days} days ago'
        elif days == 0:
            rel = 'today'
        else:
            rel = f'in {days} days'
        print(f'  {f:<22} {when_str}   ({rel})')

    apps = Application.objects.filter(call=call)
    print(f'\n  applications: {apps.count()}')
    for row in apps.values('status').annotate(
            n=__import__('django.db.models', fromlist=['Count']).Count('id')).order_by('-n'):
        print(f'      {row["status"]:<28} {row["n"]}')

    sent = EmailLog.objects.filter(sent_at__isnull=False).count()
    print(f'\n  emails logged as sent: {sent}   '
          f'(python scripts/rehearsal.py inbox)')
    print()


# ------------------------------------------------------------------------ advance
def cmd_advance(args):
    """Move the call's dates back by N days == let N days pass.

    Caveat worth knowing before you trust a result: this moves the CALL, not
    the applications. Anything anchored to an application's own timestamps —
    the acceptance ladder off `acceptance_deadline`, the stalled-acceptance
    nag, the 6-month publication follow-up — measures from rows this does not
    touch, so it will not come due just because the call moved. Those are
    exercised in Stage 6+ of the click-through, by setting the application
    dates directly.
    """
    days = args.days
    call = get_call()
    for f in DATE_FIELDS:
        setattr(call, f, getattr(call, f) - timedelta(days=days))
    call.save()
    print(f'Simulated {days} day(s) passing for {call.code}.')
    print('(Call dates only — application-anchored reminders are unaffected; '
          'see the docstring.)')
    cmd_status(args)


# --------------------------------------------------------------------------- beat
def cmd_beat(args):
    """Run every scheduled task once, in schedule order, and report.

    This is the question "what would the portal email today?" answered without
    waiting for tomorrow. In dev, CELERY_TASK_ALWAYS_EAGER is on and the email
    backend is the console, so nothing leaves the machine.
    """
    from communications.models import EmailLog
    import importlib

    before = EmailLog.objects.count()
    print('\nRunning all beat tasks. Nothing can leave this machine: '
          'EMAIL_BACKEND is the console.\n')

    for label, dotted in BEAT_TASKS:
        module_path, _, func_name = dotted.rpartition('.')
        try:
            module = importlib.import_module(module_path)
            task = getattr(module, func_name)
        except (ImportError, AttributeError) as exc:
            print(f'  {label:<32} MISSING — {exc}')
            continue

        n_before = EmailLog.objects.count()
        try:
            result = task()
        except Exception as exc:                       # noqa: BLE001
            print(f'  {label:<32} RAISED  {type(exc).__name__}: {exc}')
            continue
        sent = EmailLog.objects.count() - n_before
        flag = f'{sent} email(s)' if sent else '—'
        print(f'  {label:<32} {flag:<14} {result if result is not None else ""}')

    total = EmailLog.objects.count() - before
    print(f'\n  {total} new email log row(s) this run.')
    if total:
        print('  Read them:  python scripts/rehearsal.py inbox')
    print()


# -------------------------------------------------------------------------- inbox
def cmd_inbox(args):
    from communications.models import EmailLog

    logs = EmailLog.objects.select_related('template').order_by('created_at')
    if not logs:
        print('\nNo emails logged. Nothing has been sent in this sandbox.\n')
        return

    print(f'\n{logs.count()} email(s) logged in this sandbox:\n')
    for log in logs:
        when = timezone.localtime(log.created_at).strftime('%Y-%m-%d %H:%M')
        ttype = log.template.template_type if log.template else '(no template)'
        print(f'  [{log.status:<8}] {when}  ->  {log.recipient_email}')
        print(f'             {ttype}: {log.subject}')
        if args.full:
            body = (log.text_content or log.html_content or '').strip()
            for line in body.splitlines():
                print(f'             | {line}')
            print()
    print()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)

    sub.add_parser('seed', help='reset the sandbox and create one draft call')
    sub.add_parser('status', help='show where the rehearsal call is')
    p_adv = sub.add_parser('advance', help='simulate N days passing')
    p_adv.add_argument('days', type=int)
    sub.add_parser('beat', help='run all scheduled tasks once and report')
    p_in = sub.add_parser('inbox', help='list every email this sandbox logged')
    p_in.add_argument('--full', action='store_true', help='include bodies')

    args = parser.parse_args()
    db = guard()
    print(f'(sandbox: {db})')

    {
        'seed': cmd_seed,
        'status': cmd_status,
        'advance': cmd_advance,
        'beat': cmd_beat,
        'inbox': cmd_inbox,
    }[args.command](args)


if __name__ == '__main__':
    main()
