"""Small parameter/row/transaction fault controls; no fake PostgreSQL-positive claim."""
from contextlib import contextmanager
import hashlib
import importlib.util
import os
import tempfile
import pathlib
import stat
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

from tools import account_postgres as p
from tools import account_core as c


class AdapterBoundaries(unittest.TestCase):
    def test_closed_dialect_preserves_separate_values_and_refuses_unknown_sql(self):
        value = "name'; DROP SCHEMA accounts CASCADE; --"
        query = p.dialect('SELECT 1 FROM accounts WHERE username=?', (value,))
        self.assertEqual(query, 'SELECT 1 FROM accounts WHERE username=%s LIMIT 1001')
        self.assertNotIn(value, query)
        for query, values in [('SELECT 1; DROP TABLE accounts', ()), ('SELECT 1 FROM accounts WHERE username=?', ()), ('SELECT count(*) FROM accounts', (True,))]:
            with self.assertRaises(c.AccountError): p.dialect(query, values)

    def test_real_row_projection_supports_index_and_name_without_fabrication(self):
        row = p.Row(('payload', 'created_at'), (b'actual', 123))
        self.assertEqual(row[0], row['payload'])
        self.assertEqual(row[1], 123)
        with self.assertRaises(ValueError): _ = row['unlisted']

    def test_no_passfile_parent_or_existing_leaf_refuses_before_driver_connect(self):
        driver = SimpleNamespace(connect=mock.Mock())
        with mock.patch.dict(sys.modules, {'psycopg': driver}):
            with mock.patch.object(p.os, 'stat', return_value=SimpleNamespace(st_mode=stat.S_IFDIR | 0o777, st_uid=0)):
                with self.assertRaises(c.AccountError): p.connect({})
            def exists(path, **kwargs):
                return SimpleNamespace(st_mode=stat.S_IFDIR | 0o755, st_uid=0)
            with mock.patch.object(p.os, 'stat', side_effect=exists):
                with self.assertRaises(c.AccountError): p.connect({})
        driver.connect.assert_not_called()

    def test_inherited_pg_overrides_refuse_before_driver_or_address_lookup(self):
        driver = SimpleNamespace(connect=mock.Mock())
        for name in ('PGHOSTADDR', 'PGSERVICE', 'PGPASSWORD'):
            with mock.patch.dict(sys.modules, {'psycopg': driver}), mock.patch.dict(p.os.environ, {name: 'private-environment-canary'}):
                with self.assertRaises(c.AccountError) as seen: p.connect({})
                self.assertEqual(seen.exception.code, 'storage_unavailable')
                self.assertNotIn('canary', str(seen.exception))
        driver.connect.assert_not_called()

    def test_schema_source_digest_and_required_expiry_indexes_are_exact(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        raw = (root / p.SCHEMA_FILE).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), p.SCHEMA_SHA)
        for name in p.INDEXES:
            self.assertIn(('CREATE INDEX ' + name + ' ON accounts.').encode(), raw)
        self.assertNotIn(b'DROP ', raw)
        self.assertIn(b'SET LOCAL ROLE ait_account_owner', raw)

    def test_original_transaction_clock_refuses_deadline_backwards_boolean(self):
        transaction = p.Transaction(None)
        for now in (transaction.start - 1, transaction.start + p.MAX_TRANSACTION, True, float('nan')):
            with mock.patch.object(p.time, 'monotonic', return_value=now):
                with self.assertRaises(c.AccountError): transaction.tick()

    def test_cursor_uses_driver_values_closes_and_bounds_returned_rows(self):
        cursor = mock.Mock()
        cursor.rowcount = 1
        cursor.description = [mock.Mock(name='column')]
        cursor.description[0].name = 'payload'
        cursor.fetchone.return_value = (memoryview(b'actual'),)
        budget = mock.Mock(result_bytes=0)
        row = p.Cursor(cursor, budget).fetchone()
        self.assertEqual(row['payload'], b'actual')
        cursor.close.assert_called_once()
        cursor.reset_mock(); cursor.fetchmany.return_value = [(b'x',)] * 1002
        with self.assertRaises(c.AccountError): p.Cursor(cursor, budget).fetchall()
        cursor.close.assert_called_once()

    def test_commit_attempt_fault_is_uncertainty_and_never_claims_rollback(self):
        connection = mock.Mock()
        connection.execute.return_value.fetchone.return_value = (0, c.KDF_ID, p.SCHEMA_SHA)
        def execute(query, *args, **kwargs):
            if query == 'COMMIT': raise OSError('lost acknowledgement')
            return mock.Mock(fetchone=lambda: (0, c.KDF_ID, p.SCHEMA_SHA))
        connection.execute.side_effect = execute
        store = p.PostgresAccountStore.__new__(p.PostgresAccountStore)
        store.profile_path = pathlib.Path('/not-read')
        store.profile = {'synthetic': True}
        with mock.patch.object(p, 'load_profile', return_value=store.profile), mock.patch.object(p, 'connect', return_value=connection), mock.patch.object(p, 'verify_runtime'):
            with self.assertRaises(p.CommitUncertain) as seen:
                with store._db(123): pass
        self.assertTrue(seen.exception.update_may_have_committed)
        self.assertNotIn(mock.call('ROLLBACK'), connection.execute.call_args_list)
        connection.close.assert_called_once()

    def test_precommit_fault_rolls_back_and_close_is_attempted(self):
        connection = mock.Mock()
        connection.execute.return_value.fetchone.return_value = (0, c.KDF_ID, p.SCHEMA_SHA)
        store = p.PostgresAccountStore.__new__(p.PostgresAccountStore)
        store.profile_path = pathlib.Path('/not-read'); store.profile = {'synthetic': True}
        with mock.patch.object(p, 'load_profile', return_value=store.profile), mock.patch.object(p, 'connect', return_value=connection), mock.patch.object(p, 'verify_runtime'):
            with self.assertRaises(c.AccountError):
                with store._db(123): raise OSError('precommit refusal')
        self.assertIn(mock.call('ROLLBACK'), connection.execute.call_args_list)
        self.assertNotIn(mock.call('COMMIT'), connection.execute.call_args_list)
        connection.close.assert_called_once()


class ReviewCleanupBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = pathlib.Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location('account_pg_review_controls', root / 'scripts/account-postgres-review.py')
        cls.review = importlib.util.module_from_spec(spec); spec.loader.exec_module(cls.review)

    def test_observer_error_cannot_skip_owned_stop_or_mask_original(self):
        tool = self.review
        with (mock.patch.object(tool, 'observe_review', side_effect=RuntimeError('observer')),
             mock.patch.object(tool, 'stop', return_value={'owned_cluster_stopped': True}) as stop,
             mock.patch.object(tool, 'main_snapshot', side_effect=ValueError('later')),
             mock.patch.object(tool, 'run', return_value=SimpleNamespace(stdout=b''))):
            result = tool.finish(pathlib.Path('/not-operated'))
        stop.assert_called_once()
        self.assertEqual(result['original_observer_failure_type'], 'RuntimeError')
        self.assertEqual(result['main_snapshot_failure_type'], 'ValueError')
        self.assertTrue(result['owned_stop_attempted'])
        self.assertTrue(result['owned_cluster_stopped'])
        self.assertFalse(result['pass'])

    def test_observer_cancellation_still_attempts_verified_stop(self):
        tool = self.review
        with (mock.patch.object(tool, 'observe_review', side_effect=KeyboardInterrupt()),
             mock.patch.object(tool, 'stop', side_effect=OSError('stop uncertain')) as stop,
             mock.patch.object(tool, 'main_snapshot', return_value={'main_critical_snapshot_unchanged': True}),
             mock.patch.object(tool, 'run', return_value=SimpleNamespace(stdout=b''))):
            result = tool.finish(pathlib.Path('/not-operated'))
        stop.assert_called_once()
        self.assertEqual(result['original_observer_failure_type'], 'KeyboardInterrupt')
        self.assertEqual(result['owned_stop_failure_type'], 'OSError')
        self.assertFalse(result['pass'])

    def test_owned_pid_read_failure_closes_real_descriptor(self):
        tool = self.review
        with tempfile.TemporaryDirectory() as directory:
            work = pathlib.Path(directory); (work / 'pgdata').mkdir(mode=0o700)
            (work / 'pgdata/postmaster.pid').write_text('123\n' + str(work / 'pgdata') + '\n')
            real_open = os.open; seen = []
            def opened(*args, **kwargs):
                fd = real_open(*args, **kwargs); seen.append(fd); return fd
            with (mock.patch.object(tool.pwd, 'getpwnam', return_value=SimpleNamespace(pw_uid=os.getuid())),
                 mock.patch.object(tool.os, 'open', side_effect=opened),
                 mock.patch.object(tool.os, 'fstat', side_effect=OSError('identity unavailable'))):
                with self.assertRaises(OSError): tool.owned_postmaster(work)
            self.assertEqual(len(seen), 1)
            with self.assertRaises(OSError): os.fstat(seen[0])


if __name__ == '__main__': unittest.main()
