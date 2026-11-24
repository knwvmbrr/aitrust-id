"""Real private SQLite/KDF lifecycle. Entitlement stand-in is NOT a payment proof."""
from pathlib import Path
import sqlite3
import tempfile
import unittest
import uuid
from unittest import mock

from tools import account_core as c
from tools.account_store import AccountStore, initialize, SESSION_SECONDS
from test_account_core import NOW, record

PASSWORD = 'a public synthetic passphrase only'


class AccountStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve())
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'accounts'
        self.store = initialize(self.path)
        self.user, self.secret = self.signup('alice-test')
        self.owner = self.user['account']['id']

    def signup(self, name):
        _, bootstrap = self.store.session(None, NOW, 'fixture-peer')
        return self.store.signup(name, PASSWORD, bootstrap, NOW, 'fixture-peer')

    def active(self, owner, now):
        return {'format': 'account-history-entitlement/v1', 'account_id': owner, 'state': 'ACTIVE', 'valid_until': now + 3600, 'revision': 1}

    def append(self):
        self.store.history_change(self.secret, NOW, 'enable', self.active, acknowledge=True)
        return self.store.history_change(self.secret, NOW, 'append', self.active, record=record())

    def test_two_owners_durable_history_and_no_plaintext_credentials(self):
        saved = self.append()
        other, other_secret = self.signup('bob-test')
        self.assertNotEqual(self.owner, other['account']['id'])
        self.assertEqual(AccountStore(self.path).history_list(self.secret, NOW)['items'], [saved])
        self.assertEqual(self.store.history_list(other_secret, NOW)['items'], [])
        with self.assertRaises(c.AccountError) as failure:
            self.store.history_delete(other_secret, NOW, saved['event_id'])
        self.assertEqual(failure.exception.status, 404)
        raw = (self.path / 'accounts.sqlite').read_bytes()
        for secret in (PASSWORD.encode(), self.secret.encode(), c.csrf(self.secret).encode()):
            self.assertNotIn(secret, raw)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.path / 'accounts.sqlite').stat().st_mode & 0o777, 0o600)

    def test_opt_in_inactive_outage_and_export_delete_independence(self):
        with self.assertRaises(c.AccountError):
            self.store.history_change(self.secret, NOW, 'append', self.active, record=record())
        saved = self.append()
        def unavailable(*unused):
            raise RuntimeError('PRIVATE_ENTITLEMENT_CANARY')
        with self.assertRaises(c.AccountError) as error:
            self.store.history_change(self.secret, NOW, 'append', unavailable, record=record())
        self.assertEqual(error.exception.code, 'history_access_unavailable')
        with mock.patch.object(c, 'assessment', side_effect=AssertionError('must not assess')):
            self.assertEqual(self.store.history_list(self.secret, NOW, export=True)['items'], [saved])
            self.store.history_change(self.secret, NOW, 'disable', unavailable)
            self.store.history_delete(self.secret, NOW, saved['event_id'])
            self.assertEqual(self.store.history_list(self.secret, NOW)['items'], [])

    def test_duplicate_history_is_idempotent_but_conflict_refuses(self):
        saved = self.append()
        original = {key: saved[key] for key in ('event_id', 'displayed_at', 'adapter', 'tag', 'state', 'method')}
        self.assertEqual(self.store.history_change(self.secret, NOW + 1, 'append', self.active, record=original), saved)
        changed = {**original, 'state': 'NO_FINDING'}
        with self.assertRaises(c.AccountError) as error:
            self.store.history_change(self.secret, NOW + 1, 'append', self.active, record=changed)
        self.assertEqual(error.exception.code, 'history_conflict')
        self.assertEqual(self.store.history_list(self.secret, NOW + 1)['total_entries'], 1)

    def test_rotation_revocation_and_absent_user_real_dummy_kdf(self):
        self.store.logout(self.secret, NOW)
        with self.assertRaises(c.AccountError):
            self.store.authenticate(self.secret, NOW)
        _, bootstrap = self.store.session(None, NOW, 'fixture-peer')
        actual = c.derive
        with mock.patch.object(c, 'derive', wraps=actual) as checked:
            for name in ('alice-test', 'absent-test'):
                with self.assertRaises(c.AccountError) as error:
                    self.store.login(name, 'wrong synthetic passphrase', bootstrap, NOW, 'fixture-peer')
                self.assertEqual(error.exception.status, 401)
            self.assertEqual(checked.call_count, 2)
        public, new = self.store.login('alice-test', PASSWORD, bootstrap, NOW, 'fixture-peer')
        self.assertTrue(public['authenticated'])
        self.assertNotEqual(bootstrap, new)
        with self.assertRaises(c.AccountError):
            self.store.authenticate(bootstrap, NOW, False)

    def test_failed_login_rate_is_persisted_and_not_reset_by_refusal(self):
        _, bootstrap = self.store.session(None, NOW, 'rate-peer')
        for _ in range(10):
            with self.assertRaises(c.AccountError) as error:
                self.store.login('absent-rate-test', PASSWORD, bootstrap, NOW, 'rate-peer')
            self.assertEqual(error.exception.status, 401)
        with mock.patch.object(c, 'derive', side_effect=AssertionError('rate must precede KDF')):
            with self.assertRaises(c.AccountError) as error:
                self.store.login('absent-rate-test', PASSWORD, bootstrap, NOW, 'rate-peer')
        self.assertEqual(error.exception.status, 429)

    def test_session_expiry_history_retention_and_clock_rollback(self):
        self.append()
        other, other_secret = self.signup('cold-account')
        self.store.history_change(other_secret, NOW, 'enable', self.active, acknowledge=True)
        self.store.history_change(other_secret, NOW, 'append', self.active, record=record())
        with self.assertRaises(c.AccountError) as error:
            self.store.authenticate(self.secret, NOW - 1)
        self.assertEqual(error.exception.code, 'clock_unavailable')
        later = NOW + c.RETENTION + 1
        self.store.maintenance(later)
        with self.store._db(later) as (db, _):
            self.assertEqual(db.execute('SELECT count(*) FROM history').fetchone()[0], 0)
        _, bootstrap = self.store.session(None, later, 'fixture-peer')
        _, new = self.store.login('alice-test', PASSWORD, bootstrap, later, 'fixture-peer')
        self.assertEqual(self.store.history_list(new, later)['items'], [])
        with self.assertRaises(c.AccountError):
            self.store.authenticate(self.secret, later)

    def test_per_owner_full_quota_refuses_without_evicting_data(self):
        self.store.history_change(self.secret, NOW, 'enable', self.active, acknowledge=True)
        with self.store._db(NOW) as (db, _):
            for _ in range(1000):
                item = c.history_record(record(), NOW)
                db.execute('INSERT INTO history(account_id,event_id,created_at,payload) VALUES(?,?,?,?)',
                           (self.owner, item['event_id'], NOW, c.encode(item)))
        with self.assertRaises(c.AccountError) as error:
            self.store.history_change(self.secret, NOW, 'append', self.active, record=record())
        self.assertEqual(error.exception.code, 'history_full')
        self.assertEqual(self.store.history_list(self.secret, NOW, export=True)['total_entries'], 1000)
        other, secret = self.signup('quota-other')
        self.store.history_change(secret, NOW, 'enable', self.active, acknowledge=True)
        self.store.history_change(secret, NOW, 'append', self.active, record=record())
        self.assertEqual(self.store.history_list(secret, NOW)['total_entries'], 1)

    def test_account_delete_erases_own_data_and_retains_retryable_operator_cleanup(self):
        self.append()
        with self.store._db(NOW) as (db, _):
            attempts = db.execute('SELECT sum(count) FROM rates').fetchone()[0]
        with self.assertRaises(c.AccountError):
            self.store.delete_account(self.secret, 'incorrect synthetic passphrase', NOW)
        with self.store._db(NOW) as (db, _):
            self.assertEqual(db.execute('SELECT sum(count) FROM rates').fetchone()[0], attempts + 1)
        removed = self.store.delete_account(self.secret, PASSWORD, NOW)
        self.assertTrue(removed['deleted'])
        def failed(*unused):
            raise OSError('PRIVATE_OPERATOR_LEDGER')
        self.assertFalse(self.store.finish_cleanup(self.owner, failed, NOW))
        with self.assertRaises(c.AccountError):
            self.store.authenticate(self.secret, NOW)
        with self.store._db(NOW) as (db, _):
            self.assertEqual(db.execute('SELECT count(*) FROM accounts').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM history').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM sessions WHERE account_id IS NOT NULL').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM cleanup').fetchone()[0], 1)
        self.assertEqual(self.store.retry_cleanup(lambda *_: {'removed': True, 'payment_processed': False}, NOW)['completed'], 1)

    def test_private_links_unknown_schema_and_corrupt_payload_refuse(self):
        with self.assertRaises((c.AccountError, OSError, ValueError)):
            initialize(self.path)
        with sqlite3.connect(self.path / 'accounts.sqlite') as db:
            db.execute('PRAGMA user_version=1')
        with mock.patch.object(c, 'derive', side_effect=AssertionError('old schema must refuse before KDF')):
            with self.assertRaises(c.AccountError) as error:
                self.store.session(None, NOW, 'fixture-peer')
        self.assertEqual(error.exception.code, 'storage_unavailable')
        with sqlite3.connect(self.path / 'accounts.sqlite') as db:
            db.execute('PRAGMA user_version=2')
        saved = self.append()
        with sqlite3.connect(self.path / 'accounts.sqlite') as db:
            db.execute('UPDATE history SET payload=? WHERE event_id=?', (b'{"text":"PRIVATE_CORRUPTION"}', saved['event_id']))
        with self.assertRaises(c.AccountError) as error:
            self.store.history_list(self.secret, NOW)
        self.assertEqual(error.exception.code, 'storage_unavailable')
        self.assertNotIn('PRIVATE', str(error.exception))
        alias = self.path.parent / 'alias'
        alias.symlink_to(self.path, target_is_directory=True)
        with self.assertRaises(c.AccountError):
            AccountStore(alias).session(None, NOW, 'fixture-peer')

    def test_clock_is_selected_under_writer_lock_and_cleanup_uses_fresh_transactions(self):
        moment, calls = [NOW + 1], []
        def clock():
            # A second real SQLite writer cannot acquire the lock when sampled.
            with sqlite3.connect(self.path / 'accounts.sqlite', timeout=0) as other:
                with self.assertRaises(sqlite3.OperationalError):
                    other.execute('BEGIN IMMEDIATE')
            calls.append(moment[0])
            return moment[0]
        self.store.history_change(self.secret, clock, 'enable', self.active, acknowledge=True)
        self.assertEqual(calls, [NOW + 1])
        moment[0] += 1
        saved = self.store.history_change(self.secret, clock, 'append', self.active, record=record())
        self.assertEqual(saved['received_at'], moment[0])
        self.assertEqual(saved['expires_at'], moment[0] + c.RETENTION)
        with self.store._db(clock) as (db, selected):
            self.assertEqual(selected, moment[0])
            self.assertEqual(db.execute('SELECT max(at) FROM audit').fetchone()[0], selected)
        self.store.delete_account(self.secret, PASSWORD, clock)
        def forget(account_id, selected):
            self.assertEqual((account_id, selected), (self.owner, moment[0]))
            moment[0] += 1
            self.store.maintenance(clock)  # Another legitimate completed transaction.
            return {'removed': True, 'payment_processed': False}
        self.assertTrue(self.store.finish_cleanup(self.owner, forget, clock))
        with self.store._db(clock) as (db, selected):
            self.assertEqual(selected, moment[0])
            self.assertEqual(db.execute('SELECT count(*) FROM cleanup').fetchone()[0], 0)
        self.assertEqual(calls[-1], NOW + 3)


if __name__ == '__main__':
    unittest.main()
