"""Affected finite runtime boundaries; no SDK, native code or network execution."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import web_runtime_obligations as w


class RuntimeObligations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        b = w.Budget(ROOT)
        try:
            cls.manifest = b.initialize()
            cls.outputs = w.expected(b, cls.manifest)
        finally: b.close()

    def test_retained_exact_facts_and_no_global_clearance(self):
        result = w.verify()
        self.assertTrue(result['retained_facts_verified'])
        self.assertEqual(result['received_files_verified'], 0)
        self.assertEqual((result['runtime_files'], result['required_companions'], result['source_offers']), (5, 14, 3))
        self.assertTrue(all(type(v) is bool and v is False for v in result['claims'].values()))
        self.assertLess(result['resources']['held_fds'], 128)

    def test_complete_hiwire_preferred_source_and_mpl(self):
        raw = self.outputs['runtime-obligations/HIWIRE-SOURCES.zip']
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names = set(z.namelist())
            self.assertIn('hiwire/src/hiwire.c', names)
            self.assertIn('hiwire/src/wasm_table.c', names)
            self.assertIn('hiwire/Makefile', names)
            self.assertIn('hiwire/patches/emcc-emjs-dylink-externref.patch', names)
            self.assertIn('publisher/cpython-Makefile', names)
            self.assertIn(b'Mozilla Public License Version 2.0', z.read('hiwire/LICENSE'))
            index = json.loads(z.read('index.json'))
            self.assertEqual(names, set(index['members']) | {'index.json'})
            for name, row in index['members'].items():
                body = z.read(name)
                self.assertEqual(row, {'bytes': len(body), 'sha256': w.sha(body)})
        self.assertEqual(raw, self.outputs['runtime-obligations/HIWIRE-SOURCES.zip'])

    def test_all_legacy_output_bytes_unchanged(self):
        for name, row in self.manifest['legacy_outputs'].items():
            raw = self.outputs[name]
            self.assertEqual(row, {'bytes': len(raw), 'sha256': w.sha(raw)})

    def test_notice_terms_are_distinct_and_full(self):
        text = self.outputs['runtime-obligations/NOTICES.txt']
        for term in [b'HACL', b'Apache License', b'Oracle', b'INRIA', b'Pierre Curto',
                     b'Copyright', b'REDISTRIBUTION', b'Public License']:
            # Some notices use ordinary capitalization; the exact source bytes remain unchanged.
            self.assertIn(term.lower(), text.lower())
        index = json.loads(self.outputs['runtime-obligations/obligations.json'])
        self.assertEqual(index['claims'], w.CLAIMS)
        self.assertEqual(len(index['companion_files']), 13)

    def test_changed_manifest_refuses_before_any_producer(self):
        with patch.object(w, 'MANIFEST_SHA256', '0'*64), patch.object(w, 'private_producers') as produce:
            with self.assertRaises(w.Unavailable): w.verify()
            produce.assert_not_called()

    def test_unknown_source_path_refuses_before_read(self):
        b = w.Budget(ROOT)
        try:
            b.initialize()
            with patch.object(b.capture, 'read') as read:
                with self.assertRaises(w.Unavailable): b.read(ROOT, 'future/unknown.txt')
                read.assert_not_called()
        finally: b.close()

    def test_shared_read_and_cache_caps_before_read(self):
        for attribute, value in [('reads', w.MAX_READS), ('read_bytes', w.MAX_READ_BYTES), ('cache_bytes', w.MAX_CACHE)]:
            b = w.Budget(ROOT)
            try:
                b.initialize(); b.cache.pop('tools/artifact_evidence_io.py', None)
                setattr(b, attribute, value)
                with patch.object(b.capture, 'read') as read:
                    with self.assertRaises(w.Unavailable): b.read(ROOT, 'tools/artifact_evidence_io.py')
                    read.assert_not_called()
            finally: b.close()

    def test_descriptor_capacity_before_open(self):
        b = w.Budget(ROOT)
        try:
            b.capture.fds = [None]*128
            with self.assertRaises(w.Unavailable): b.capacity(ROOT/'future/file')
        finally: b.capture.fds = []; b.close()

    def test_one_deadline_covers_all_phases(self):
        b = w.Budget(ROOT)
        try:
            b.started -= 61
            with patch.object(b.capture, 'read') as read:
                with self.assertRaises(w.Unavailable): b.initialize()
                read.assert_not_called()
        finally: b.close()

    def test_json_duplicates_nodes_and_types_refuse(self):
        b = w.Budget(ROOT)
        try:
            with self.assertRaises(w.Unavailable): b.parse(b'{"a":1,"a":2}')
            b.nodes = 100_000
            with self.assertRaises(w.Unavailable): b.parse(b'{}')
        finally: b.close()
        self.assertNotEqual(type(True), type(1))

    def test_private_prepare_no_overwrite_and_partial_uncertainty(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp).resolve(); parent.chmod(0o700)
            target = parent/'companions'
            result = w.prepare(target)
            self.assertEqual(result['received_files_verified'], 0)
            for name, raw in self.outputs.items():
                self.assertEqual((target/name).read_bytes(), raw)
                self.assertEqual((target/name).stat().st_mode & 0o777, 0o600)
            with self.assertRaises(w.Unavailable): w.prepare(target)
            failed = parent/'partial'
            with patch.object(w.os, 'write', side_effect=OSError('private canary')):
                with self.assertRaises(w.OutputUncertain): w.prepare(failed)
            self.assertTrue(failed.is_dir())

    def test_received_unknown_and_incomplete_members_refuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp).resolve();p.chmod(0o700)
            (p/'unexpected').write_text('private-canary')
            with self.assertRaises(w.Unavailable): w.check_built(p)

    def test_received_notice_cannot_approve_its_own_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp).resolve();p.chmod(0o700)
            target = p/'artifact'; w.prepare(target)
            (target/'runtime').mkdir(mode=0o700)
            # Five fixed names are present; changed runtime refuses before any claimed support.
            for name in w.RUNTIME: (target/'runtime'/name).write_bytes(b'not-the-pinned-runtime')
            index = target/'runtime-obligations/obligations.json'
            obj = json.loads(index.read_bytes());obj['claims']['distribution_route_admitted'] = True
            index.write_text(json.dumps(obj))
            with self.assertRaises(w.Unavailable): w.check_built(target)

    def test_producer_namespaces_do_not_mutate_real_modules(self):
        from tools import pyodide_js_sources as js
        original = js.read
        b = w.Budget(ROOT)
        try:
            b.initialize(); captured, z = w.private_producers(b)
            self.assertIsNot(captured.read, original)
            self.assertIs(js.read, original)
        finally: b.close()

    def test_received_membership_stops_before_unbounded_listing(self):
        class Entries:
            def __init__(self): self.advanced = 0; self.closed = 0
            def __enter__(self): return self
            def __exit__(self, *args): self.closed += 1
            def __iter__(self): return self
            def __next__(self):
                self.advanced += 1
                if self.advanced > 2: raise AssertionError('unbounded entry collection')
                return type('Entry', (), {'name': 'known' if self.advanced == 1 else 'unknown'})()
        with tempfile.TemporaryDirectory() as tmp:
            b = w.Budget(ROOT); entries = Entries()
            try:
                with patch.object(w.os, 'scandir', return_value=entries), patch.object(w.os, 'listdir', side_effect=AssertionError('wide list')):
                    with self.assertRaises(w.Unavailable): w.membership(b, Path(tmp).resolve(), {'known'})
                self.assertEqual((entries.advanced, entries.closed), (2, 1))
            finally: b.close()

    def test_received_membership_normal_and_iterator_fd_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = w.Budget(ROOT)
            try:
                p = Path(tmp).resolve(); (p/'known').write_text('fixed')
                w.membership(b, p, {'known'})
                with patch.object(w, 'MAX_FDS', len(b.capture.fds)), patch.object(w.os, 'scandir') as scan:
                    with self.assertRaises(w.Unavailable): w.membership(b, p, {'known'})
                    scan.assert_not_called()
            finally: b.close()

    def test_prepare_post_real_mkdir_fault_is_uncertain_and_retained(self):
        original = w.os.mkdir
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp).resolve(); p.chmod(0o700); target = p/'new'
            def created_then_failed(name, *args, **kwargs):
                original(name, *args, **kwargs)
                if name == 'new': raise OSError('private canary')
            with patch.object(w.os, 'mkdir', side_effect=created_then_failed):
                with self.assertRaises(w.OutputUncertain): w.prepare(target)
            self.assertTrue(target.is_dir())
            self.assertEqual(target.stat().st_mode & 0o777, 0o700)

    def test_prepare_post_creation_cancel_and_close_fault_are_uncertain(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp).resolve(); p.chmod(0o700)
            target = p/'cancelled'
            with patch.object(w.os, 'write', side_effect=KeyboardInterrupt()):
                with self.assertRaises(w.OutputUncertain): w.prepare(target)
            self.assertTrue(target.is_dir())
            close = w.Budget.close; calls = []
            def closed_then_failed(budget):
                if budget.closed: return
                close(budget); calls.append(True); raise OSError('postclose')
            with patch.object(w.Budget, 'close', closed_then_failed):
                with self.assertRaises(w.OutputUncertain): w.prepare(p/'closed')
            self.assertEqual(len(calls), 1)
            self.assertTrue((p/'closed/runtime-obligations/HIWIRE-SOURCES.zip').is_file())

    def test_larger_changed_source_refuses_before_unbudgeted_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp).resolve(); (p/'source.txt').write_bytes(b'x'*100)
            b = w.Budget(p)
            b.allowed = {'source.txt': {'bytes': 1, 'sha256': w.sha(b'x')}}
            try:
                with patch.object(w.os, 'read', side_effect=AssertionError('read exceeds charged bytes')) as read:
                    with self.assertRaises(ValueError): b.read(p, 'source.txt', 200_000)
                    read.assert_not_called()
                self.assertEqual(b.read_bytes, 1)
                self.assertNotIn('source.txt', b.cache)
            finally: b.close()

    def test_cli_receipt_refusal_warns_after_successful_preparation(self):
        source = ROOT/'scripts/verify-web-runtime-obligations.py'
        namespace = {'__name__': '_trusted_cli_test', '__file__': str(source)}
        exec(compile(source.read_bytes(), '<trusted-cli-test>', 'exec'), namespace)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp).resolve(); p.chmod(0o700); stage = p/'stage'
            refused = ROOT/'output/verification/private-receipt-must-not-be-created.json'
            self.assertFalse(refused.exists())
            def prepare(destination):
                Path(destination).mkdir(mode=0o700)
                (Path(destination)/'marker').write_text('owned synthetic output')
                return {'pass': True}
            output = io.StringIO()
            with patch.object(namespace['runtime'], 'prepare', side_effect=prepare), patch.object(sys, 'argv', [str(source), '--prepare', str(stage), '--output', str(refused)]), contextlib.redirect_stdout(output):
                status = namespace['main']()
            self.assertEqual(status, 2)
            self.assertTrue(json.loads(output.getvalue())['output_may_exist'])
            self.assertTrue(stage.is_dir())
            self.assertFalse(refused.exists())
            self.assertNotIn(str(p), output.getvalue())
            output = io.StringIO(); cancelled = p/'cancelled'
            with patch.object(namespace['runtime'], 'prepare', side_effect=prepare), patch.object(namespace['evidence'].Capture, 'save', side_effect=KeyboardInterrupt()), patch.object(sys, 'argv', [str(source), '--prepare', str(cancelled), '--output', str(p/'receipt.json')]), contextlib.redirect_stdout(output):
                status = namespace['main']()
            self.assertEqual(status, 2)
            self.assertTrue(json.loads(output.getvalue())['output_may_exist'])
            self.assertTrue(cancelled.is_dir())

    def test_cli_isolated_help_and_fixed_private_failure(self):
        command = [sys.executable, '-I', '-S', '-B', str(ROOT/'scripts/verify-web-runtime-obligations.py')]
        help_run = subprocess.run(command+['--help'], cwd='/', capture_output=True, text=True, timeout=10)
        self.assertEqual(help_run.returncode, 0)
        with tempfile.TemporaryDirectory(prefix='private-canary-') as tmp:
            run = subprocess.run(command+['--artifact-dir', tmp], cwd='/', capture_output=True, text=True, timeout=20)
            self.assertEqual(run.returncode, 2)
            self.assertNotIn(tmp, run.stdout+run.stderr)
            self.assertEqual(json.loads(run.stdout)['status'], 'Unavailable')


if __name__ == '__main__': unittest.main()
