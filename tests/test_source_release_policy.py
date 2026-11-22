"""Source-copy classification controls; no SDK, install or archive build.

SPDX-License-Identifier: Apache-2.0
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import source_release_policy as p
from scripts.worker_process import run_worker


def oid(raw):
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


class RightsControls(unittest.TestCase):
    def fixture(self):
        grant = b'Project grant\n'
        project = b'# SPDX-License-Identifier: Apache-2.0\nx=1\n'
        vendor = b'Original vendor source and retained notices\n'
        raws = {'LICENSE': grant, 'x.py': project, 'vendor.c': vendor}
        rows = {n: ('100644', oid(v), len(v)) for n, v in raws.items()}
        d = {'files': [[n, *rows[n], 'project-text' if n == 'x.py' else 'fixed',
                       p.markers(v) if n == 'x.py' else None] for n, v in raws.items()],
             'introduced_first_party': {'new.py': 'project-text'},
             'grant_anchors': {'LICENSE': oid(grant)},
             'categories': {'project-text': {'mutable_project_text': True},
                            'fixed': {'mutable_project_text': False}}}
        return d, rows, raws

    def check(self, d, rows, raws):
        seen = []
        def blob(name, selected, size):
            seen.append(name)
            return raws[name]
        return p.checked(d, rows, blob, lambda: None), seen

    def test_supported_exact_profile_and_maintained_known_project_source(self):
        d, rows, raw = self.fixture()
        result, seen = self.check(d, rows, raw)
        self.assertEqual(result['files'], 3)
        self.assertEqual(seen, [])
        raw['x.py'] = raw['x.py'].replace(b'x=1', b'x=200')
        rows['x.py'] = ('100644', oid(raw['x.py']), len(raw['x.py']))
        result, seen = self.check(d, rows, raw)
        self.assertEqual(result['changed_project_text_files'], 1)
        self.assertEqual(seen, ['x.py'])

    def test_unknown_new_path_missing_member_and_changed_vendor_refuse_before_read(self):
        d, rows, raw = self.fixture()
        cases = [dict(rows, unknown=('100644', '1'*40, 1)),
                 {k: v for k, v in rows.items() if k != 'vendor.c'},
                 dict(rows, **{'vendor.c': ('100644', '2'*40, 1)})]
        for current in cases:
            with self.subTest(current=len(current)):
                reader = mock.Mock(side_effect=AssertionError('NO_READ'))
                with self.assertRaises(p.Refused):
                    p.checked(d, current, reader, lambda: None)
                reader.assert_not_called()

    def test_grant_text_is_immutable_even_if_project_paths_may_change(self):
        d, rows, raw = self.fixture()
        rows['LICENSE'] = ('100644', '3'*40, 10)
        with self.assertRaisesRegex(p.Refused, 'Source-copy profile unavailable'):
            self.check(d, rows, raw)

    def test_new_license_declaration_and_non_text_project_change_refuse(self):
        d, rows, raw = self.fixture()
        for value in [b'# SPDX-License-Identifier: GPL-3.0-only\nx=1\n', b'\0BINARY', b'\xff']:
            raw['x.py'] = value
            rows['x.py'] = ('100644', oid(value), len(value))
            with self.assertRaises(p.Refused):
                self.check(d, rows, raw)

    def test_only_explicit_named_new_project_text_is_accepted(self):
        d, rows, raw = self.fixture()
        value = b'# SPDX-License-Identifier: Apache-2.0\nnew=1\n'
        raw['new.py'] = value
        rows['new.py'] = ('100644', oid(value), len(value))
        result, _ = self.check(d, rows, raw)
        self.assertEqual(result['introduced_named_project_text_files'], 1)
        for value in [b'# SPDX-License-Identifier: GPL-3.0-only AND Apache-2.0\n',
                      b'# spdx-license-identifier: GPL-3.0-only\n',
                      b'# Copyright 2026 OTHER ALL RIGHTS RESERVED\n']:
            raw['new.py'] = value
            rows['new.py'] = ('100644', oid(value), len(value))
            with self.assertRaises(p.Refused):
                self.check(d, rows, raw)

    def test_changed_blob_contents_must_match_selected_git_identity(self):
        d, rows, raw = self.fixture()
        rows['x.py'] = ('100644', '5'*40, len(raw['x.py']))
        with self.assertRaises(p.Refused) as e:
            self.check(d, rows, raw)
        self.assertEqual(e.exception.code, 'source_changed')

    def test_changed_text_and_whole_check_budgets_refuse(self):
        d, rows, raw = self.fixture()
        rows['x.py'] = ('100644', '6'*40, p.MAX_CHANGED_TEXT+1)
        reader = mock.Mock(side_effect=AssertionError('NO_READ'))
        with self.assertRaises(p.Refused):
            p.checked(d, rows, reader, lambda: None)
        reader.assert_not_called()
        _, rows, _ = self.fixture()
        with self.assertRaises(p.Refused):
            p.checked(d, rows, reader, lambda: p.need(False, 'deadline'))

    def test_git_listing_has_closed_types_names_modes_and_resource_caps(self):
        def row(name='x', mode='100644', size='1', kind='blob'):
            return f'{mode} {kind} {"1"*40} {size}\t{name}'.encode()+b'\0'
        self.assertEqual(p.tree_rows(row())[1], 1)
        for raw in [row('../x'), row('.git/x'), row(mode='120000'), row(kind='commit'),
                    row(size='True'), row(size='1.0'), row(size='-1'), row(size='01'),
                    row(size=str(p.MAX_FILE+1)), row()+row(), row()[:-1]]:
            with self.assertRaises((p.Refused, ValueError)):
                p.tree_rows(raw)
        raw = b''.join(row(str(i), size=str(p.MAX_FILE)) for i in range(9))
        with self.assertRaises(p.Refused):
            p.tree_rows(raw)
        raw = b''.join(row(str(i), size='0') for i in range(p.MAX_FILES+1))
        with self.assertRaises(p.Refused):
            p.tree_rows(raw)

    def test_policy_cannot_be_coherently_rebound_by_adjacent_data(self):
        original = p.file_bytes(ROOT/p.POLICY, p.MAX_POLICY)
        self.assertEqual(p.policy(original)['profile'], p.PROFILE)
        value = json.loads(original)
        vendor = next(row for row in value['files'] if row[4] == 'pyodide-js-source')
        vendor[4] = 'project-text'
        vendor[5] = p.sha(b'')
        encoded = json.dumps(value, sort_keys=True).encode()
        with self.assertRaises(p.Refused) as error:
            p.policy(encoded)
        self.assertEqual(error.exception.code, 'policy_changed')

    def test_policy_typed_claims_not_integer_aliases(self):
        original = p.file_bytes(ROOT/p.POLICY, p.MAX_POLICY)
        value = json.loads(original)
        value['claims']['legal_clearance'] = 0
        encoded = json.dumps(value).encode()
        with mock.patch.object(p, 'POLICY_SHA256', p.sha(encoded)):
            with self.assertRaises(p.Refused):
                p.policy(encoded)

    def test_actual_source_file_io_cap_symlink_fifo_and_close_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            source = base/'source'
            source.write_bytes(b'PUBLIC')
            self.assertEqual(p.file_bytes(source, 6), b'PUBLIC')
            with self.assertRaises(p.Refused):
                p.file_bytes(source, 5)
            link = base/'linked'
            link.symlink_to(source)
            with self.assertRaises(p.Refused):
                p.file_bytes(link, 6)
            fifo = base/'fifo'
            os.mkfifo(fifo)
            with self.assertRaises(p.Refused):
                p.file_bytes(fifo, 6)
            real = os.close
            seen = []
            reused = []
            def release_then_fail(fd):
                seen.append(fd)
                real(fd)
                reused.append(os.open(source, os.O_RDONLY))
                raise OSError('PRIVATE_CLOSE_CANARY')
            with mock.patch.object(p.os, 'close', side_effect=release_then_fail):
                with self.assertRaises(OSError):
                    p.file_bytes(source, 6)
            self.assertEqual(len(seen), 1)
            self.assertEqual(reused, seen)
            try:
                self.assertEqual(os.read(reused[0], 6), b'PUBLIC')
            finally:
                real(reused[0])

    def test_actual_sparse_checkout_profile_and_source_id_are_current(self):
        value = p.verify()
        self.assertTrue(value['pass'], value)
        self.assertFalse(value['release_authorized'])
        self.assertFalse(value['legal_clearance'])
        self.assertFalse(value['compiled_runtime_permission'])
        self.assertEqual(value['source_commit'], value['checkout_commit'])
        self.assertGreaterEqual(value['files'], 12925)
        with tempfile.TemporaryDirectory() as other:
            value = p.verify(root=Path(other))
            self.assertFalse(value['pass'])
            self.assertNotIn(other, json.dumps(value))

    def test_actual_cli_bootstrap_from_unrelated_cwd_and_fixed_private_refusal(self):
        script = str(ROOT/'tools/source_release_policy.py')
        with tempfile.TemporaryDirectory() as other:
            result = subprocess.run([sys.executable, '-I', '-S', '-B', script], cwd=other,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=40)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, b'')
            self.assertTrue(json.loads(result.stdout)['pass'])
            for args in [['--unknown=PRIVATE_ARGUMENT_CANARY'],
                         ['--source-commit', 'PRIVATE_ARGUMENT_CANARY']]:
                result = subprocess.run([sys.executable, '-I', '-S', '-B', script, *args], cwd=other,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
                self.assertEqual(result.returncode, 2)
                self.assertNotIn(b'PRIVATE_ARGUMENT_CANARY', result.stdout+result.stderr)
                self.assertNotIn(other.encode(), result.stdout+result.stderr)

    def test_tree_oid_is_not_a_source_commit(self):
        d = p.policy(p.file_bytes(ROOT/p.POLICY, p.MAX_POLICY))
        value = p.verify(source_commit=d['base_tree'])
        self.assertFalse(value['pass'])
        self.assertEqual(value['reason'], 'unsupported_source_commit')

    def test_actual_owned_git_summary_larger_than_pipe_cap_and_wrong_size_refusal(self):
        d = p.policy(p.file_bytes(ROOT/p.POLICY, p.MAX_POLICY))
        row = next(row for row in d['files'] if row[0].endswith('.json') and row[3] > 2_000_000)
        self.assertGreater(row[3], 2_000_000)
        value = p.blob_summary(run_worker, row[2], row[3], 10)
        self.assertEqual(value['markers'], p.sha(b''))
        self.assertEqual(value['bytes'], row[3])
        with self.assertRaises(p.Refused):
            p.blob_summary(run_worker, row[2], 1, 10)
        with self.assertRaises(p.Refused):
            p.blob_summary(run_worker, '0'*40, 0, 10)

    def test_summary_closed_fields_and_typed_counts(self):
        value = {'pass': True, 'oid': '1'*40, 'bytes': 1,
                 'markers': '2'*64, 'introduced_markers_allowed': True}
        for changed in [dict(value, bytes=True), dict(value, unknown='PRIVATE'),
                        dict(value, oid='3'*40), dict(value, pass_as_string='true')]:
            def runner(*args, **kwargs):
                self.assertEqual(kwargs['output_limit'], 1024)
                return subprocess.CompletedProcess(args[0], 0, json.dumps(changed).encode(), b'')
            with self.assertRaises(p.Refused):
                p.blob_summary(runner, '1'*40, 1, 10)

    def test_actual_summary_supervisor_deadline_is_a_refusal(self):
        d = p.policy(p.file_bytes(ROOT/p.POLICY, p.MAX_POLICY))
        row = next(row for row in d['files'] if row[0] == 'docs/scope-progress.json')
        with self.assertRaises(subprocess.TimeoutExpired):
            p.blob_summary(run_worker, row[2], row[3], 0.000001)

    def test_separate_spec_grant_follows_actual_copied_blob_and_license_copies_are_pinned(self):
        d = p.policy(p.file_bytes(ROOT/p.POLICY, p.MAX_POLICY))
        rows = {row[0]: row for row in d['files']}
        for copied, source in [('signal-registry.json', 'signal-registry.json'),
                               ('signals.md', 'signals.md'),
                               ('spec-license.txt', 'LICENSE'),
                               ('taxonomy.md', 'taxonomy.md')]:
            a, b = rows['site/public/reference/'+copied], rows['spec/'+source]
            self.assertEqual(a[2], b[2])
            self.assertEqual(a[4], 'spec')
            self.assertFalse(d['categories'][a[4]]['mutable_project_text'])
            self.assertEqual(d['categories'][a[4]]['license'], 'CC-BY-4.0')
        row = rows['site/public/reference/code-license.txt']
        self.assertEqual(row[4], 'project-grant')
        self.assertEqual(row[2], rows['LICENSE'][2])
        self.assertFalse(d['categories'][row[4]]['mutable_project_text'])


if __name__ == '__main__':
    unittest.main()
