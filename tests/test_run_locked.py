"""#37 — `run_locked` serialises the containers' startup commands.

The Postgres path cannot run here (dev and tests are SQLite), so it is
exercised with the module's `connection` replaced: the test pins the order
lock → command → unlock, that unlock still happens when the command raises,
and that a non-Postgres backend takes no lock at all.
"""
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase

from core.management.commands import run_locked as module


class RunLockedTests(SimpleTestCase):

    def _fake_postgres(self):
        conn = mock.MagicMock()
        conn.vendor = 'postgresql'
        cursor = conn.cursor.return_value.__enter__.return_value
        return conn, cursor

    def test_postgres_takes_lock_runs_command_then_unlocks(self):
        conn, cursor = self._fake_postgres()
        events = []
        cursor.execute.side_effect = lambda sql, params=None: events.append(('sql', sql, tuple(params or ())))
        with mock.patch.object(module, 'connection', conn), \
                mock.patch.object(module, 'call_command',
                                  side_effect=lambda *a: events.append(('cmd', a))):
            call_command('run_locked', 'migrate', '--noinput')
        self.assertEqual(events, [
            ('sql', 'SELECT pg_advisory_lock(%s)', (module.STARTUP_LOCK_KEY,)),
            ('cmd', ('migrate', '--noinput')),
            ('sql', 'SELECT pg_advisory_unlock(%s)', (module.STARTUP_LOCK_KEY,)),
        ])

    def test_unlock_still_runs_when_the_command_fails(self):
        conn, cursor = self._fake_postgres()
        with mock.patch.object(module, 'connection', conn), \
                mock.patch.object(module, 'call_command', side_effect=RuntimeError('boom')):
            with self.assertRaises(RuntimeError):
                call_command('run_locked', 'migrate', '--noinput')
        executed = [c.args[0] for c in cursor.execute.call_args_list]
        self.assertEqual(executed, ['SELECT pg_advisory_lock(%s)', 'SELECT pg_advisory_unlock(%s)'])

    def test_other_backends_run_the_command_without_a_lock(self):
        conn = mock.MagicMock()
        conn.vendor = 'sqlite'
        with mock.patch.object(module, 'connection', conn), \
                mock.patch.object(module, 'call_command') as cc:
            call_command('run_locked', 'seed_email_templates')
        cc.assert_called_once_with('seed_email_templates')
        conn.cursor.assert_not_called()

    def test_refuses_to_wrap_itself(self):
        with self.assertRaises(CommandError):
            call_command('run_locked', 'run_locked', 'migrate')
