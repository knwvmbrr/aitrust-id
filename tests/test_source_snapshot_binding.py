"""Tiny actual Git/archive controls; no full repository archive or SDK."""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from unittest.mock import patch
from tools import source_snapshot_binding as binding
from scripts import source_snapshot_v3 as snapshot


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='source-binding-')
        self.root = Path(self.temp.name).resolve()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Synthetic Engineering')
        self.git('config', 'user.email', 'fixture@example.invalid')
        for name, raw in [('a.txt', b'actual-source\n'), ('binary.dat', b'\0\xff\x80test'), ('empty', b''), ('run.sh', b'echo synthetic\n')]:
            (self.root / name).write_bytes(raw)
        (self.root / 'run.sh').chmod(0o755)
        self.git('add', '.')
        self.git('commit', '-qm', 'Synthetic source fixture')
        self.commit = self.git('rev-parse', 'HEAD').decode().strip()
        self.raw = snapshot.build(self.root, self.commit)

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.check_output(['/usr/bin/git', '-C', str(self.root), *args], stderr=subprocess.DEVNULL)

    def forged(self, change, commit=None):
        with tarfile.open(fileobj=io.BytesIO(self.raw), mode='r:gz') as archive:
            rows = [(m.name[len(snapshot.PREFIX):], m.mode, archive.extractfile(m).read()) for m in archive.getmembers()][1:]
        rows = sorted(change(rows))
        metadata = {'profile': snapshot.PROFILE, 'source_commit': commit or self.commit,
                    'kind': 'development_source_snapshot', 'tag_release_validated': False,
                    'installed_dependencies_included': False,
                    'files': [{'path': n, 'mode': m, 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()} for n, m, b in rows]}
        manifest = json.dumps(metadata, sort_keys=True, separators=(',', ':')).encode()
        out = io.BytesIO()
        with gzip.GzipFile(fileobj=out, mode='wb', filename='', mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode='w', format=tarfile.USTAR_FORMAT) as archive:
                for n, m, b in [(snapshot.META, 0o644, manifest), *rows]:
                    info = tarfile.TarInfo(snapshot.PREFIX + n)
                    info.mode, info.size = m, len(b)
                    archive.addfile(info, io.BytesIO(b))
        return out.getvalue()

    def rejected(self, raw, code=None, commit=None):
        with self.assertRaises(binding.Refused) as error:
            binding.verify(raw, root=self.root, commit=self.commit if commit is None else commit)
        self.assertIn(error.exception.code, binding.CODES)
        self.assertEqual(str(error.exception), 'Source archive binding unavailable.')
        if code:
            self.assertEqual(error.exception.code, code)

    def test_actual_canonical_git_binary_empty_and_executable(self):
        result = binding.verify(self.raw, root=self.root, commit=self.commit)
        self.assertEqual(result['source_files'], 4)
        self.assertEqual(result['source_tree'], self.git('rev-parse', 'HEAD^{tree}').decode().strip())
        self.assertTrue(result['trusted_git_bytes_matched'])
        for k in ('signature_verified', 'rights_approved', 'release_authorized'):
            self.assertIs(result[k], False)

    def test_coherent_equal_length_forgery_passes_serializer_but_refuses_git(self):
        raw = self.forged(lambda rows: [(n, m, b'FORGED-source\n' if n == 'a.txt' else b) for n, m, b in rows])
        self.assertEqual(snapshot.inspect(raw, self.commit)['source_files'], 4)
        self.rejected(raw, 'blob_mismatch')

    def test_coherent_missing_extra_mode_and_size_refuse(self):
        cases = [lambda rows: rows[1:], lambda rows: rows + [('extra', 0o644, b'x')],
                 lambda rows: [(n, 0o755 if n == 'a.txt' else m, b) for n, m, b in rows],
                 lambda rows: [(n, m, b + b'x' if n == 'a.txt' else b) for n, m, b in rows]]
        for index, change in enumerate(cases):
            with self.subTest(case=index):
                raw = self.forged(change)
                snapshot.inspect(raw, self.commit)
                self.rejected(raw, 'inventory_mismatch')

    def test_explicit_identity_and_noncommit_refuse(self):
        for commit in ('HEAD', '../private-token', True, '0' * 40):
            self.rejected(self.raw, commit=commit)
        tree = self.git('rev-parse', 'HEAD^{tree}').decode().strip()
        raw = self.forged(lambda rows: rows, commit=tree)
        snapshot.inspect(raw, tree)
        self.rejected(raw, commit=tree)

    def test_truncation_and_trailing_gzip_refuse(self):
        for raw in (self.raw[:-1], self.raw + b'x', self.raw + self.raw):
            self.rejected(raw, 'archive_refused')

    def test_replacement_and_inherited_git_environment_cannot_choose_objects(self):
        oid = self.git('rev-parse', self.commit + ':a.txt').decode().strip()
        wrong = subprocess.check_output(['/usr/bin/git', '-C', str(self.root), 'hash-object', '-w', '--stdin'], input=b'WRONG-source\n').decode().strip()
        self.git('replace', oid, wrong)
        with patch.dict(os.environ, {'GIT_DIR': '/nonexistent/private-git', 'GIT_REPLACE_REF_BASE': 'refs/replace/', 'GIT_CONFIG_COUNT': '1', 'GIT_CONFIG_KEY_0': 'core.pager', 'GIT_CONFIG_VALUE_0': '/private/never-execute'}):
            result = binding.verify(self.raw, root=self.root, commit=self.commit)
        self.assertTrue(result['pass'])

    def test_git_symlink_refuses_regular_archive_record(self):
        os.symlink('a.txt', self.root / 'linked')
        self.git('add', 'linked')
        self.git('commit', '-qm', 'Synthetic symlink')
        commit = self.git('rev-parse', 'HEAD').decode().strip()
        raw = self.forged(lambda rows: rows + [('linked', 0o644, b'a.txt')], commit=commit)
        snapshot.inspect(raw, commit)
        self.rejected(raw, 'tree_refused', commit=commit)

    def test_stream_parser_one_byte_chunks_and_wrong_digest(self):
        raw = b'\0\xff\x80x'
        oid = binding._object_hash('blob', raw)
        row = {'oid': oid, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        parser = binding._Blobs([row], time.monotonic() + 2)
        stream = (oid + ' blob 4\n').encode() + raw + b'\n'
        for n in stream:
            parser.consume(bytes([n]))
        parser.finish()
        parser = binding._Blobs([dict(row, sha256='0' * 64)], time.monotonic() + 2)
        with self.assertRaises(binding.Refused):
            parser.consume(stream)

    def test_capture_timeout_overflow_and_constructor_ownership(self):
        owned, real = [], subprocess.Popen
        def spawn(*args, **kwargs):
            child = real(*args, **kwargs)
            owned.append(child)
            return child
        for argv, limit, delay in [([sys.executable, '-I', '-S', '-c', 'import time;time.sleep(5)'], 32, .05),
                                   ([sys.executable, '-I', '-S', '-c', 'import os;os.write(1,b"x"*100000)'], 16, 2)]:
            with patch.object(binding.subprocess, 'Popen', side_effect=spawn):
                with self.assertRaises(binding.Refused):
                    binding._capture(argv, b'', time.monotonic() + delay, limit, new_session=True)
            self.assertIsNotNone(owned[-1].returncode)
        with patch.object(binding.subprocess, 'Popen', side_effect=spawn), patch.object(binding.selectors, 'DefaultSelector', side_effect=OSError('PRIVATE_CONSTRUCTOR')):
            with self.assertRaises(OSError):
                binding._capture([sys.executable, '-I', '-S', '-c', 'import time;time.sleep(5)'], b'', time.monotonic() + 2, 32, new_session=True)
        self.assertIsNotNone(owned[-1].returncode)

    def test_reaped_leader_never_signaled_after_wait_fault(self):
        owned, real = [], subprocess.Popen
        def spawn(*args, **kwargs):
            child = real(*args, **kwargs)
            wait = child.wait
            def faulty_wait(*a, **kw):
                wait(*a, **kw)
                raise OSError('PRIVATE_POSTWAIT')
            child.wait = faulty_wait
            owned.append(child)
            return child
        with patch.object(binding.subprocess, 'Popen', side_effect=spawn), patch.object(binding.os, 'killpg') as kill:
            with self.assertRaises(OSError):
                binding._capture([sys.executable, '-I', '-S', '-c', 'pass'], b'', time.monotonic() + 2, 32, new_session=True)
            self.assertEqual(owned[0].returncode, 0)
            kill.assert_not_called()

    def test_foundation_change_and_cli_no_echo(self):
        with patch.dict(binding.FOUNDATION, {'scripts/source_snapshot_v3.py': '0' * 64}):
            with self.assertRaises(binding.Refused) as error:
                binding._foundation()
            self.assertEqual(error.exception.code, 'foundation_changed')
        secret = 'PRIVATE_ARGUMENT_DO_NOT_PRINT'
        result = subprocess.run([sys.executable, '-I', '-S', '-B', str(Path(binding.__file__)), secret], capture_output=True, timeout=5)
        self.assertNotIn(secret.encode(), result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout), {'pass': False, 'code': 'invalid_request'})
        self.assertEqual(result.stderr, b'')

    def test_captured_foundation_never_imports_repository_package(self):
        before = snapshot.MAX_TOTAL
        real_import = __import__
        def guard(name, *args, **kwargs):
            if name == 'scripts' or name.startswith('scripts.') or name == 'source_snapshot':
                raise AssertionError('Repository source reopened through import')
            return real_import(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=guard):
            pinned = binding._foundation()
            result = pinned.inspect(self.raw, self.commit)
        self.assertEqual(result['source_files'], 4)
        self.assertEqual(snapshot.MAX_TOTAL, before)
        self.assertIsNot(pinned, snapshot)

    def test_closed_summary_nonobject_refuses(self):
        with patch.object(binding, '_capture', return_value=b'[]'):
            self.rejected(self.raw, 'unavailable')

    def test_budget_preflight_and_truncated_batch_refuse(self):
        with patch.object(binding, 'MAX_TOTAL', 1):
            with self.assertRaises(binding.Refused) as error:
                binding._verify_inner(self.raw, self.root, self.commit)
            self.assertEqual(error.exception.code, 'resource_limit')
        parser = binding._Blobs([{'oid': '0' * 40, 'bytes': 4, 'sha256': '0' * 64}], time.monotonic() + 2)
        parser.consume(('0' * 40 + ' blob 4\nx').encode())
        with self.assertRaises(binding.Refused):
            parser.finish()


if __name__ == '__main__':
    unittest.main()
