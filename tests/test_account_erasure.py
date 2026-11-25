"""Focused inert/file/child failure controls; real PG claims require the drill."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest import mock

from tools import account_core as c
from tools import account_erasure as e
from tools import account_postgres as p

NOW = 2_000_000_000


def records():
    generation, identity = str(uuid.uuid4()), str(uuid.uuid4())
    value = {'format': 'account-erasure-journal/v1', 'generation': generation,
             'migration_one': p.SCHEMA_SHA, 'migration_two': e.MIGRATION_SHA,
             'captured_at': NOW, 'clock': NOW, 'head': 1, 'floor': 0, 'floor_time': 0,
             'rows': [{'sequence': 1, 'account_id': identity, 'erased_at': NOW}]}
    raw = c.encode(value) + b'\n'
    selected = {'format': 'account-erasure-checkpoint/v1', 'generation': generation,
                'journal_sha256': e.digest(raw), 'head': 1, 'captured_at': NOW}
    backup = {'format': 'account-erasure-backup/v1', 'generation': generation,
              'migration_one': p.SCHEMA_SHA, 'migration_two': e.MIGRATION_SHA,
              'captured_at': NOW - 1, 'clock': NOW - 1, 'head': 0,
              'dump_sha256': 'a' * 64, 'dump_bytes': 100}
    return backup, value, selected, raw


def profile(generation=None, restored=False):
    value = {'format': e.PROFILE, 'socket': '/run/aitrust-synthetic-review', 'port': 55449,
             'database': 'ait_erasure_restore' if restored else 'ait_erasure_review',
             'role': 'ait_account_runtime', 'server_os_user': 'debian', 'cluster': 'aitrust-account-review',
             'schema_sha256': p.SCHEMA_SHA, 'erasure_sha256': e.MIGRATION_SHA,
             'system_identity_sha256': e.digest(b'123'),
             'generation': generation or str(uuid.uuid4()), 'purpose': 'restored' if restored else 'source',
             'restore_receipt': '/run/aitrust-synthetic-receipt.json' if restored else None}
    return value


class RecoveryBoundaries(unittest.TestCase):
    def test_null_reconciliation_marker_cannot_become_ready_by_null_equality(self):
        selected = profile(restored=True)
        with (mock.patch.object(e, 'state', return_value={'reconciled_sha': None, 'reconciled_at': None,
                                                        'restored_from_sha': 'a' * 64}),
              mock.patch.object(e, 'read_record') as reader):
            with self.assertRaises(c.AccountError): e.verify_receipt(mock.Mock(), selected)
        reader.assert_not_called()

    def test_receipt_cannot_substitute_live_system_or_received_backup_identity(self):
        selected = profile(restored=True)
        value = {'generation': selected['generation'], 'reconciled_sha': 'b' * 64,
                 'reconciled_at': NOW, 'head': 1, 'restored_from_sha': 'a' * 64}
        receipt = {'format': 'account-erasure-serving-receipt/v1', 'database': selected['database'],
                   'database_oid': 1, 'generation': value['generation'], 'migration_one': p.SCHEMA_SHA,
                   'migration_two': e.MIGRATION_SHA, 'system_identity_sha256': selected['system_identity_sha256'],
                   'journal_sha256': value['reconciled_sha'], 'backup_sha256': 'a' * 64,
                   'head': 1, 'reconciled_at': NOW}
        with (mock.patch.object(e, 'state', return_value=value),
              mock.patch.object(e, 'system_identity', return_value='c' * 64)):
            with self.assertRaises(c.AccountError): e.verify_receipt(mock.Mock(), selected, receipt)
        receipt['backup_sha256'] = 'd' * 64
        with (mock.patch.object(e, 'state', return_value=value),
              mock.patch.object(e, 'system_identity', return_value=selected['system_identity_sha256'])):
            with self.assertRaises(c.AccountError): e.verify_receipt(mock.Mock(), selected, receipt)

    def test_checkpoint_bytes_cannot_authorize_different_uuid_dictionary(self):
        manifest, value, selected, raw = records()
        different = copy.deepcopy(value)
        different['rows'][0]['account_id'] = str(uuid.uuid4())
        with self.assertRaises(c.AccountError):
            e.compatible(manifest, different, selected, raw, NOW)
        duplicate = raw.rstrip().replace(b'"head":1', b'"head":1,"head":1')
        selected['journal_sha256'] = e.digest(duplicate)
        with self.assertRaises(c.AccountError):
            e.compatible(manifest, value, selected, duplicate, NOW)

    def test_exact_checkpoint_window_generation_and_sequence_refusals(self):
        manifest, value, selected, raw = records()
        self.assertEqual(e.compatible(manifest, value, selected, raw, NOW), NOW)
        cases = []
        old = copy.deepcopy(manifest); old['captured_at'] = old['clock'] = NOW - e.WINDOW - 1
        cases.append((old, value, selected, raw, NOW))
        wrong = copy.deepcopy(selected); wrong['journal_sha256'] = 'b' * 64
        cases.append((manifest, value, wrong, raw, NOW))
        wrong = copy.deepcopy(selected); wrong['generation'] = str(uuid.uuid4())
        cases.append((manifest, value, wrong, raw, NOW))
        wrong = copy.deepcopy(value); wrong['rows'][0]['sequence'] = 2
        cases.append((manifest, wrong, selected, c.encode(wrong), NOW))
        cases.append((manifest, value, selected, raw, NOW - 1))
        for args in cases:
            with self.assertRaises(c.AccountError): e.compatible(*args)

    def test_exact_seven_day_boundary_and_retained_pruning_floor(self):
        manifest, value, selected, raw = records()
        manifest['captured_at'] = manifest['clock'] = NOW - e.WINDOW
        self.assertEqual(e.compatible(manifest, value, selected, raw, NOW), NOW)
        value['floor'] = value['head']; value['floor_time'] = NOW
        value['rows'] = []
        raw = c.encode(value); selected['journal_sha256'] = e.digest(raw)
        with self.assertRaises(c.AccountError): e.compatible(manifest, value, selected, raw, NOW)

    def test_boolean_duplicate_uuid_unsorted_time_and_oversize_refuse(self):
        _, value, _, _ = records()
        for field in ('head', 'floor', 'captured_at', 'clock'):
            wrong = copy.deepcopy(value); wrong[field] = True
            with self.assertRaises(c.AccountError): e.journal(wrong)
        wrong = copy.deepcopy(value); wrong['head'] = 2
        wrong['rows'].append(dict(wrong['rows'][0], sequence=2))
        with self.assertRaises(c.AccountError): e.journal(wrong)
        wrong['rows'][1]['account_id'] = str(uuid.uuid4())
        wrong['rows'][1]['erased_at'] = NOW - 1
        with self.assertRaises(c.AccountError): e.journal(wrong)
        wrong = copy.deepcopy(value); wrong['head'] = e.MAX_ROWS + 1
        with self.assertRaises(c.AccountError): e.journal(wrong)

    def test_private_file_roundtrip_duplicate_and_no_replace(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve(); target = root / 'journal.json'
            _, value, _, _ = records()
            actual = e.write_record(target, value)
            received, raw = e.read_record(target)
            self.assertEqual(received, value); self.assertEqual(actual, hashlib.sha256(raw).hexdigest())
            with self.assertRaises(Exception): e.write_record(target, value)
            bad = root / 'duplicate.json'; bad.write_bytes(b'{"head":1,"head":2}'); bad.chmod(0o600)
            with self.assertRaises(c.AccountError): e.read_record(bad)
            linked = root / 'link.json'; linked.symlink_to(target)
            with self.assertRaises(Exception): e.read_record(linked)

    def test_v1_identity_stays_separate_from_explicit_v2(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder).resolve() / 'profile.json'
            def put(value): file.write_bytes(c.encode(value)); file.chmod(0o600)
            current = profile(); put(current)
            self.assertEqual(p.load_profile(file), current)
            legacy = {k: v for k, v in current.items() if k not in ('erasure_sha256', 'generation', 'purpose', 'restore_receipt', 'system_identity_sha256')}
            legacy.update(format=p.PROFILE, database='ait_account_review'); put(legacy)
            self.assertEqual(p.load_profile(file), legacy)
            legacy['database'] = 'ait_erasure_review'; put(legacy)
            with self.assertRaises(c.AccountError): p.load_profile(file)
            current['erasure_sha256'] = 'c' * 64; put(current)
            with self.assertRaises(c.AccountError): p.load_profile(file)
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(hashlib.sha256((root / p.SCHEMA_FILE).read_bytes()).hexdigest(), p.SCHEMA_SHA)
        self.assertEqual(hashlib.sha256((root / e.MIGRATION_FILE).read_bytes()).hexdigest(), e.MIGRATION_SHA)

    def test_attempted_operator_commit_is_typed_uncertainty_and_closes(self):
        connection = mock.Mock()
        identity = ('ait_erasure_review', 'debian', 'debian', 'aitrust-account-review', '', None)
        def execute(query, *args, **kwargs):
            if query == 'COMMIT': raise OSError('acknowledgement lost')
            cursor = mock.Mock(); cursor.fetchone.return_value = ('123',) if 'pg_control_system' in query else identity
            return cursor
        connection.execute.side_effect = execute
        with mock.patch.object(p, 'connect', return_value=connection):
            with self.assertRaises(p.CommitUncertain):
                with e.operator(profile(), write=True): pass
        connection.close.assert_called_once()
        self.assertFalse(any(call.args[0] == 'ROLLBACK' for call in connection.execute.call_args_list))


class OwnedChildCleanup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location('erasure_cli_controls', root / 'scripts/account-erasure.py')
        cls.tool = importlib.util.module_from_spec(spec); spec.loader.exec_module(cls.tool)

    def test_dump_timeout_reaps_owned_process_without_leaving_it_running(self):
        tool = self.tool
        real_popen = subprocess.Popen; seen = []
        def opened(*args, **kwargs):
            process = real_popen(*args, **kwargs); seen.append(process); return process
        with mock.patch.object(tool.subprocess, 'Popen', side_effect=opened):
            with self.assertRaises(subprocess.TimeoutExpired):
                tool.run([sys.executable, '-I', '-c', 'import time; time.sleep(30)'], timeout=.05)
        self.assertEqual(len(seen), 1); self.assertIsNotNone(seen[0].poll())

    def test_mask_restore_fault_still_reaps_child_and_preserves_original(self):
        tool = self.tool
        real_popen, real_mask = subprocess.Popen, tool.signal.pthread_sigmask
        seen = []; original = OSError('injected mask restoration diagnostic')
        def opened(*args, **kwargs):
            process = real_popen(*args, **kwargs); seen.append(process); return process
        def masked(how, values):
            result = real_mask(how, values)
            if how == tool.signal.SIG_SETMASK: raise original
            return result
        with (mock.patch.object(tool.subprocess, 'Popen', side_effect=opened),
              mock.patch.object(tool.signal, 'pthread_sigmask', side_effect=masked)):
            with self.assertRaises(OSError) as caught:
                tool.run([sys.executable, '-I', '-c', 'import time; time.sleep(30)'])
        self.assertIs(caught.exception, original)
        self.assertEqual(len(seen), 1); self.assertIsNotNone(seen[0].poll())
        self.assertTrue(seen[0].stdout.closed and seen[0].stderr.closed)


if __name__ == '__main__': unittest.main()
