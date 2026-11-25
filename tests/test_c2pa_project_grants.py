"""Actual retained-source notice delivery, never SDK/route permission."""
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

from tools import c2pa_project_grants as g
from tools.artifact_evidence_io import Capture

ROOT = Path(__file__).resolve().parents[1]


class ProjectGrantDelivery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = g.expected()
        cls.raw = g._archive(cls.files)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve())
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.base.chmod(0o700)
        self.path = self.base / 'grants.zip'

    def write(self, raw):
        self.path.write_bytes(raw)
        self.path.chmod(0o600)

    def test_actual_prepare_and_received_four_members_full_notices(self):
        result = g.prepare(self.path)
        self.assertEqual(result, g.inspect(self.path))
        self.assertEqual(result['packages'], 3)
        self.assertEqual(result['members'], 4)
        self.assertTrue(all(v is False for v in result['claims'].values()))
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.path.read_bytes(), self.raw)
        with zipfile.ZipFile(self.path) as archive:
            self.assertEqual(archive.namelist(), sorted(self.files))
            for name, raw in self.files.items():
                self.assertEqual(archive.read(name), raw)
                if name.endswith('.txt'):
                    self.assertIn(b'Licensed under either of', raw)
                    self.assertIn(b'END OF TERMS AND CONDITIONS', raw)
                    self.assertIn(b'APPENDIX', raw)
                    self.assertIn(b'Not an upstream LICENSE or NOTICE filename.', raw)

    def test_omitted_modified_grant_license_and_coherent_index_refuse(self):
        first = next(n for n in self.files if n.endswith('.txt'))
        variants = []
        missing = dict(self.files); missing.pop(first); variants.append(missing)
        for old, new in ((b'Licensed under either of', b'NOT LICENSED under this'),
                         (b'Grant of Copyright License', b'NO COPYRIGHT GRANT GIVEN!!')):
            changed = dict(self.files); changed[first] = changed[first].replace(old, new, 1); variants.append(changed)
        coherent = dict(self.files); coherent[first] += b'\nchanged\n'
        index = json.loads(coherent['C2PA-PROJECT-GRANTS.json'])
        row = next(r for r in index['packages'] if r['path'] == first)
        row['bytes'] = len(coherent[first]); row['sha256'] = hashlib.sha256(coherent[first]).hexdigest()
        coherent['C2PA-PROJECT-GRANTS.json'] = g.encoded(index); variants.append(coherent)
        for files in variants:
            with self.subTest(paths=sorted(files)):
                self.write(g._archive(files))
                with self.assertRaises(g.Unavailable):g.inspect(self.path)

    def test_extra_trailing_truncated_or_alternate_encoding_refuse(self):
        extra = dict(self.files); extra['unknown.txt'] = b'not reviewed'
        alternate = io.BytesIO()
        with zipfile.ZipFile(alternate, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, raw in self.files.items():archive.writestr(name, raw)
        for raw in (g._archive(extra), self.raw + b'X', self.raw[:-1], alternate.getvalue()):
            self.write(raw)
            with self.assertRaises(g.Unavailable):g.inspect(self.path)

    def test_changed_primary_source_and_coherently_rebound_index_refuse(self):
        shadow = self.base / 'trusted-fixture'; shadow.mkdir()
        data = json.loads((ROOT / g.DATA).read_bytes())
        names = {g.DATA, data['source_manifest']['path'], data['apache_fulltext']['path']}
        names.update(row[key]['path'] for row in data['packages'] for key in ('readme', 'cargo_orig'))
        for name in names:
            target = shadow / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes((ROOT / name).read_bytes())
        row = data['packages'][0]['readme']; (shadow / row['path']).write_bytes(b'changed grant')
        with mock.patch.object(g, 'ROOT', shadow):
            with self.assertRaises(g.Unavailable):g.expected()
        row['bytes'] = len(b'changed grant'); row['sha256'] = hashlib.sha256(b'changed grant').hexdigest()
        (shadow / g.DATA).write_text(json.dumps(data, indent=2) + '\n')
        with mock.patch.object(g, 'ROOT', shadow):
            with self.assertRaises(g.Unavailable):g.expected()

    def test_existing_dangling_and_nonprivate_destination_refuse_unchanged(self):
        self.write(b'KEEP')
        with self.assertRaises(g.Unavailable) as caught:g.prepare(self.path)
        self.assertNotIsInstance(caught.exception, g.OutputUncertain)
        self.assertEqual(self.path.read_bytes(), b'KEEP'); self.path.unlink()
        self.path.symlink_to(self.base / 'absent')
        with self.assertRaises(g.Unavailable):g.prepare(self.path)
        self.assertTrue(self.path.is_symlink()); self.path.unlink()
        self.base.chmod(0o755)
        try:
            with self.assertRaises(g.Unavailable):g.prepare(self.path)
            self.assertFalse(self.path.exists())
        finally:self.base.chmod(0o700)

    def test_partial_actual_write_fault_retains_uncertain_bytes(self):
        real = os.write
        def write(fd, raw):
            real(fd, raw[:5]); raise OSError('OWNED_WRITE_FAULT')
        with mock.patch.object(g.os, 'write', side_effect=write):
            with self.assertRaises(g.OutputUncertain) as caught:g.prepare(self.path)
        self.assertTrue(caught.exception.output_may_exist)
        self.assertEqual(self.path.stat().st_size, 5)
        with self.assertRaises(g.Unavailable):g.inspect(self.path)

    def test_cancel_after_output_creation_is_typed_and_all_owned_close(self):
        held = []; real_open = os.open
        def open_file(*args, **kwargs):
            fd = real_open(*args, **kwargs)
            if args[1] & os.O_CREAT:held.append(fd)
            return fd
        with mock.patch.object(g.os, 'open', side_effect=open_file), mock.patch.object(g.os, 'fsync', side_effect=KeyboardInterrupt):
            with self.assertRaises(g.OutputUncertain):g.prepare(self.path)
        self.assertTrue(self.path.exists()); self.assertEqual(len(held), 1)
        with self.assertRaises(OSError):os.fstat(held[0])

    def test_actual_pending_alarm_after_create_adoption_closes_fd(self):
        real = os.open; held = []; old = signal.getsignal(signal.SIGALRM)
        class Cancelled(BaseException):pass
        def stop(*unused):raise Cancelled()
        def open_file(*args, **kwargs):
            fd = real(*args, **kwargs)
            if args[1] & os.O_CREAT:
                held.append(fd); signal.raise_signal(signal.SIGALRM)
            return fd
        try:
            signal.signal(signal.SIGALRM, stop)
            with mock.patch.object(g.os, 'open', side_effect=open_file):
                with self.assertRaises(g.OutputUncertain):g.prepare(self.path)
        finally:signal.signal(signal.SIGALRM, old)
        self.assertEqual(len(held), 1)
        with self.assertRaises(OSError):os.fstat(held[0])

    def test_close_fault_after_complete_output_is_uncertain(self):
        real = Capture.close
        def close(capture):
            real(capture); raise OSError('OWNED_CLOSE_FAULT')
        with mock.patch.object(Capture, 'close', side_effect=close, autospec=True):
            with self.assertRaises(g.OutputUncertain):g.prepare(self.path)
        self.assertEqual(self.path.read_bytes(), self.raw)

    def test_cleanup_mask_setup_and_restore_fault_always_close_owned_capture(self):
        real_expected = g._expected; real_mask = signal.pthread_sigmask; base = Capture
        for phase in ('setup', 'restore'):
            captures = []; ready = []; calls = []
            class Held(base):
                def __init__(self):super().__init__(); captures.append(self)
            def body(budget):
                files = real_expected(budget); ready.append(True); return files
            def mask(how, values):
                if ready:
                    calls.append(how)
                    if phase == 'setup' and how == signal.SIG_BLOCK:raise OSError('OWNED_MASK_SETUP')
                    if phase == 'restore' and how == signal.SIG_SETMASK:
                        real_mask(how, values); raise OSError('OWNED_MASK_RESTORE')
                return real_mask(how, values)
            original = real_mask(signal.SIG_BLOCK, set())
            try:
                with mock.patch.object(g, 'Capture', Held), mock.patch.object(g, '_expected', side_effect=body), mock.patch.object(g.signal, 'pthread_sigmask', side_effect=mask):
                    with self.assertRaises(g.Unavailable):g.expected()
                self.assertTrue(captures[0].closed); self.assertEqual(captures[0].fds, [])
                self.assertEqual(calls, [signal.SIG_BLOCK, signal.SIG_SETMASK])
                self.assertEqual(real_mask(signal.SIG_BLOCK, set()), original)
            finally:
                real_mask(signal.SIG_SETMASK, original)
                for capture in captures:capture.close()

    def test_one_clock_backwards_nonfinite_and_expired_refuse(self):
        for values in ([100., 101., 99.], [float('nan'), 101.], [100., 111.], [False, .5]):
            with mock.patch.object(g.time, 'monotonic', side_effect=values):
                with self.assertRaises(g.Unavailable):
                    budget = g.Budget(Capture()); budget.tick()

    def test_deep_ancestry_refuses_before_any_body_open(self):
        capture = Capture(); self.addCleanup(capture.close); budget = g.Budget(capture)
        with mock.patch.object(capture, 'read', side_effect=AssertionError('must refuse before open')):
            with self.assertRaises(g.Unavailable):budget.read('/' + 'nested/' * 90 + 'file', 1)

    def test_actual_isolated_CLI_prepare_inspect_and_fixed_refusal(self):
        script = ROOT / 'scripts/c2pa-project-grants.py'
        for args in (['--prepare', str(self.path)], ['--inspect', str(self.path)]):
            result = subprocess.run([sys.executable, '-I', '-S', '-B', str(script), *args], capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr); self.assertTrue(json.loads(result.stdout)['pass'])
        result = subprocess.run([sys.executable, '-I', '-S', '-B', str(script), '--PRIVATE_UNKNOWN_ARGUMENT'], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 2); self.assertNotIn(b'PRIVATE_UNKNOWN', result.stdout + result.stderr)


if __name__ == '__main__':unittest.main()
