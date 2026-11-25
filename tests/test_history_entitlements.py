"""Real private-ledger lifecycle and refusal controls; not payment processing."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
import uuid

from tools import history_entitlements as h

ROOT = Path(__file__).resolve().parents[1]


def key():
    return str(uuid.uuid4())


class HistoryEntitlementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='aitrust-history-access-')
        self.base = Path(self.temp.name).resolve(); self.base.chmod(0o700)
        self.path = self.base / 'access'; self.store = h.initialize(self.path)
        self.a, self.b, self.now = key(), key(), 1_800_000_000

    def tearDown(self):
        self.temp.cleanup()

    def test_grant_expiry_renewal_revoke_and_replay(self):
        self.assertEqual(self.store.assess(self.a, self.now)['state'], 'INACTIVE')
        event = key(); until = self.now + 100
        first = self.store.grant(self.a, event, until, self.now)
        self.assertEqual((first['state'], first['revision']), ('ACTIVE', 1))
        self.assertEqual(self.store.grant(self.a, event, until, self.now + 1), first)
        self.assertEqual(self.store.assess(self.a, until)['state'], 'INACTIVE')
        self.store.grant(self.a, key(), until + 200, until)
        revoked = self.store.revoke(self.a, key(), until + 1)
        self.assertEqual((revoked['state'], revoked['revision']), ('INACTIVE', 3))
        self.assertEqual(self.store.grant(self.a, event, until, until + 2)['revision'], 3)
        self.assertEqual(self.store.assess(self.b, until + 2)['state'], 'INACTIVE')

    def test_event_collision_and_invalid_lease_never_grant_other_account(self):
        event = key(); self.store.grant(self.a, event, self.now + 100, self.now)
        with self.assertRaises(h.EntitlementError):
            self.store.grant(self.b, event, self.now + 100, self.now)
        for until in (self.now, self.now + h.MAX_LEASE + 1, True, None):
            with self.subTest(until=until), self.assertRaises(h.EntitlementError):
                self.store.grant(self.b, key(), until, self.now)
        self.assertEqual(self.store.assess(self.b, self.now)['state'], 'INACTIVE')

    def test_clock_rollback_refuses_after_reopen_and_cannot_reactivate_expiry(self):
        self.store.grant(self.a, key(), self.now + 5, self.now)
        self.assertEqual(self.store.assess(self.a, self.now + 6)['state'], 'INACTIVE')
        reopened = h.HistoryEntitlements(self.path)
        self.assertEqual(reopened.assess(self.a, self.now + 1)['state'], 'UNAVAILABLE')
        with self.assertRaises(h.EntitlementError):
            reopened.grant(self.a, key(), self.now + 100, self.now + 1)

    def test_trusted_service_clock_is_selected_under_lock_without_clamping(self):
        self.store.grant(self.a, key(), self.now + 5, self.now)
        self.store.grant(self.b, key(), self.now + 100, self.now + 1)
        clock = mock.Mock(return_value=self.now + 2)
        service = h.HistoryEntitlements(self.path, clock=clock)
        self.assertEqual(service.assess(self.a, self.now)['state'], 'ACTIVE')
        self.assertEqual(clock.call_count, 1)
        clock.return_value = self.now + 5
        self.assertEqual(service.assess(self.a, self.now)['state'], 'INACTIVE')
        clock.return_value = self.now + 3
        self.assertEqual(service.assess(self.a, self.now)['state'], 'UNAVAILABLE')
        clock.side_effect = RuntimeError('private clock marker')
        self.assertEqual(service.assess(self.a, self.now)['state'], 'UNAVAILABLE')

    def test_corruption_duplicate_keys_and_coherent_boolean_revision_refuse(self):
        original = (self.path / 'grants.json').read_bytes()
        self.store.grant(self.a, key(), self.now + 5, self.now)
        active = json.loads((self.path / 'grants.json').read_bytes())
        active['accounts'][self.a]['revision'] = True
        for raw in (b'{bad', b'{"version":1,"version":1}', json.dumps(active).encode()):
            (self.path / 'grants.json').write_bytes(raw)
            self.assertEqual(self.store.assess(self.a, self.now)['state'], 'UNAVAILABLE')
        (self.path / 'grants.json').write_bytes(original)
        self.assertEqual(self.store.assess(self.a, self.now)['state'], 'INACTIVE')

    def test_missing_store_private_permissions_links_and_lock_fail_closed(self):
        self.assertEqual(h.HistoryEntitlements(self.base / 'missing').assess(self.a, self.now)['state'], 'UNAVAILABLE')
        file = self.path / 'grants.json'; file.chmod(0o644)
        self.assertEqual(self.store.assess(self.a, self.now)['state'], 'UNAVAILABLE'); file.chmod(0o600)
        link = self.base / 'link'; link.symlink_to(self.path, target_is_directory=True)
        self.assertEqual(h.HistoryEntitlements(link).assess(self.a, self.now)['state'], 'UNAVAILABLE')
        alias = self.base / 'hardlink'; os.link(file, alias)
        self.assertEqual(self.store.assess(self.a, self.now)['state'], 'UNAVAILABLE'); alias.unlink()
        with (self.path / 'access.lock').open('r+b') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(self.store.assess(self.a, self.now)['state'], 'UNAVAILABLE')

    def test_reserved_capacity_allows_every_current_grant_to_be_revoked(self):
        # Small real fixture exercises the production reservation invariant.
        with mock.patch.object(h, 'MAX_EVENTS', 6), mock.patch.object(h, 'MAX_ACCOUNTS', 3):
            ids = [self.a, self.b, key()]
            for account in ids:
                self.store.grant(account, key(), self.now + 100, self.now)
            with self.assertRaises(h.EntitlementError):
                self.store.grant(self.a, key(), self.now + 200, self.now)
            for account in ids:
                self.assertEqual(self.store.revoke(account, key(), self.now)['state'], 'INACTIVE')
            self.assertEqual(len(json.loads((self.path / 'grants.json').read_text())['events']), 6)

    def test_forget_erases_only_selected_account_and_events(self):
        for account in (self.a, self.b):
            self.store.grant(account, key(), self.now + 100, self.now)
        self.assertTrue(self.store.forget(self.a, self.now)['removed'])
        state = (self.path / 'grants.json').read_text()
        self.assertNotIn(self.a, state); self.assertIn(self.b, state)
        self.assertEqual(self.store.assess(self.b, self.now)['state'], 'ACTIVE')
        self.assertFalse(self.store.forget(self.a, self.now)['removed'])

    def test_prepublication_fault_leaves_original_and_removes_owned_temp(self):
        before = (self.path / 'grants.json').read_bytes()
        with mock.patch.object(h.os, 'replace', side_effect=OSError('private marker')):
            with self.assertRaises(h.EntitlementUncertain):
                self.store.grant(self.a, key(), self.now + 100, self.now)
        self.assertEqual((self.path / 'grants.json').read_bytes(), before)
        self.assertEqual(set(os.listdir(self.path)), {'access.lock', 'grants.json'})

    def test_postreplacement_fault_is_explicit_uncertainty(self):
        original = h.os.fsync
        def fsync(fd):
            if os.path.isdir('/dev/fd/' + str(fd)):
                raise OSError('private marker')
            return original(fd)
        with mock.patch.object(h.os, 'fsync', side_effect=fsync):
            with self.assertRaises(h.EntitlementUncertain):
                self.store.grant(self.a, key(), self.now + 100, self.now)
        self.assertEqual(self.store.assess(self.a, self.now)['state'], 'ACTIVE')

    def test_read_write_cancellation_propagates(self):
        with mock.patch.object(h.os, 'replace', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.store.assess(self.a, self.now)

    def test_real_replace_then_fault_or_cancel_is_uncertain_not_rolled_back(self):
        original = h.os.replace
        for error in (OSError('private marker'), KeyboardInterrupt(), SystemExit(7)):
            path = self.base / key(); store = h.initialize(path)
            def replace(*args, **kwargs):
                original(*args, **kwargs)
                raise error
            expected = h.EntitlementUncertain if isinstance(error, OSError) else h.EntitlementInterrupted if isinstance(error, KeyboardInterrupt) else h.EntitlementExit
            with mock.patch.object(h.os, 'replace', side_effect=replace):
                with self.assertRaises(expected) as caught:
                    store.grant(self.a, key(), self.now + 100, self.now)
            if isinstance(error, SystemExit): self.assertEqual(caught.exception.code, 7)
            self.assertEqual(store.assess(self.a, self.now)['state'], 'ACTIVE')
            self.assertEqual(set(os.listdir(path)), {'access.lock', 'grants.json'})

    def test_late_directory_privacy_drift_refuses_before_and_after_commit(self):
        original = h.os.fsync
        for after_commit in (False, True):
            path = self.base / key(); store = h.initialize(path)
            def fsync(fd):
                original(fd)
                is_directory = os.path.isdir('/dev/fd/' + str(fd))
                if is_directory == after_commit:
                    path.chmod(0o755)
            with mock.patch.object(h.os, 'fsync', side_effect=fsync):
                with self.assertRaises(h.EntitlementUncertain if after_commit else h.EntitlementError):
                    store.grant(self.a, key(), self.now + 100, self.now)
            self.assertEqual(store.assess(self.a, self.now)['state'], 'UNAVAILABLE')
            path.chmod(0o700)
            self.assertEqual(store.assess(self.a, self.now)['state'], 'ACTIVE' if after_commit else 'INACTIVE')

    def test_real_operator_cli_init_grant_status_revoke_never_claims_payment(self):
        path = self.base / 'cli'; until = int(time.time()) + 600
        def cli(operation, *args):
            child = subprocess.run([sys.executable, str(ROOT / 'scripts/history-entitlements.py'), operation,
                                    '--directory', str(path), *args], capture_output=True, text=True, timeout=5)
            self.assertEqual(child.returncode, 0, child.stdout)
            value = json.loads(child.stdout); self.assertFalse(value['payment_processed']); self.assertEqual(child.stderr, '')
            return value['result']
        cli('init')
        self.assertEqual(cli('grant', '--account', self.a, '--event', key(), '--until', str(until))['state'], 'ACTIVE')
        self.assertEqual(cli('status', '--account', self.a)['state'], 'ACTIVE')
        self.assertEqual(cli('revoke', '--account', self.a, '--event', key())['state'], 'INACTIVE')
        self.assertTrue(cli('forget', '--account', self.a, '--confirm-delete')['removed'])


if __name__ == '__main__':
    unittest.main()
