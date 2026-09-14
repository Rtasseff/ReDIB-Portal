"""Run one management command under a Postgres advisory lock (#37).

All three app containers (web, celery, celery-beat) share docker/entrypoint.sh
and are released by the same `db` health gate at the same moment, so they
used to race `migrate`: with real DDL one container won and the others died
with DuplicateColumn until `restart: unless-stopped` brought them back; with
no-op migrations all three "applied" it and django_migrations got three rows.

    python manage.py run_locked migrate --noinput
    python manage.py run_locked seed_email_templates

A session-level advisory lock serialises the containers: the first one in
runs the command, the others block on pg_advisory_lock() and then run it too,
finding nothing left to do. The lock lives on the connection, so it is
released by the finally: below or, if the process dies, by Postgres when the
session ends. On any other backend (SQLite in dev and tests) there is no lock
and the command simply runs.
"""
import argparse

from django.core.management import BaseCommand, CommandError, call_command
from django.db import connection

# Any constant bigint; only has to be the same in every container.
STARTUP_LOCK_KEY = 20260914


class Command(BaseCommand):
    help = "Run a management command under a Postgres advisory lock (#37)."

    def add_arguments(self, parser):
        parser.add_argument('command', help='the management command to run')
        # REMAINDER so options such as --noinput reach the wrapped command
        # instead of being rejected here.
        parser.add_argument('args', nargs=argparse.REMAINDER, help='its arguments, passed through')

    def handle(self, *args, **options):
        name = options['command']
        if name == 'run_locked':
            raise CommandError('run_locked cannot wrap itself')

        if connection.vendor != 'postgresql':
            call_command(name, *args)
            return

        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_lock(%s)', [STARTUP_LOCK_KEY])
            try:
                call_command(name, *args)
            finally:
                cursor.execute('SELECT pg_advisory_unlock(%s)', [STARTUP_LOCK_KEY])
