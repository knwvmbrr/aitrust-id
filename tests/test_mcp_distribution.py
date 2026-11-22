"""Inert format, platform, privacy and atomic-publication controls, no SDK needed."""
import base64
import hashlib
import gzip
import io
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import platform
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import mcp_distribution as m
from tools.artifact_evidence_io import Capture, OutputCommitUncertain


def synthetic_wheel(*, change=None):
    prefix = 'example-1.dist-info/'
    members = {'example.py': b'value = 1\n', prefix+'METADATA':
               b'Metadata-Version: 2.4\nName: example\nVersion: 1\nLicense-Expression: MIT\n\n',
               prefix+'WHEEL': b'Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n',
               prefix+'licenses/LICENSE': b'MIT License\nCopyright Example\n'}
    rows = []
    for name, raw in sorted(members.items()):
        h = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip('=')
        rows.append(f'{name},sha256={h},{len(raw)}\n')
    members[prefix+'RECORD'] = (''.join(rows)+prefix+'RECORD,,\n').encode()
    if change:
        change(members)
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name, raw in members.items():
            z.writestr(name, raw)
    raw = out.getvalue()
    return raw, {'name': 'example', 'version': '1', 'filename': 'example-1-py3-none-any.whl',
                 'sha256': m.sha(raw), 'bytes': len(raw)}


class WheelContract(unittest.TestCase):
    def test_real_record_members_and_license_are_bound(self):
        raw, expected = synthetic_wheel()
        record = m.wheel(raw, expected)
        self.assertEqual(record['notice_members'], ['example-1.dist-info/licenses/LICENSE'])
        self.assertEqual(len(record['members']), 5)
        self.assertFalse(record['native_members'])
        self.assertEqual(record['license_declared'], 'MIT')

    def test_hash_refusal_precedes_zip_allocation(self):
        raw, expected = synthetic_wheel()
        with patch.object(m.zipfile, 'ZipFile', side_effect=AssertionError('must not parse')):
            with self.assertRaises(m.DistributionError):
                m.wheel(raw+b'X', expected)

    def test_record_tamper_refuses_even_with_correct_outer_hash(self):
        raw, expected = synthetic_wheel(change=lambda rows: rows.update({'example.py': b'value = 2\n'}))
        with self.assertRaises(m.DistributionError):
            m.wheel(raw, expected)

    def test_omitted_extra_member_refuses(self):
        raw, expected = synthetic_wheel(change=lambda rows: rows.update({'hidden.py': b'not recorded'}))
        with self.assertRaises(m.DistributionError):
            m.wheel(raw, expected)

    def test_duplicate_record_refuses(self):
        def corrupt(rows):
            key = 'example-1.dist-info/RECORD'
            rows[key] += rows[key].splitlines(keepends=True)[0]
        raw, expected = synthetic_wheel(change=corrupt)
        with self.assertRaises(m.DistributionError):
            m.wheel(raw, expected)

    def test_preallocation_count_and_size_bounds(self):
        raw, expected = synthetic_wheel()
        for offset, value in ((8, 4097), (10, 4097)):
            changed = bytearray(raw)
            struct.pack_into('<H', changed, len(raw)-22+offset, value)
            with patch.object(m.zipfile, 'ZipFile', side_effect=AssertionError('late bound')):
                with self.assertRaises(m.DistributionError):
                    m.wheel(bytes(changed), {**expected, 'sha256': m.sha(changed)})

    def test_raw_nul_and_local_central_disagreement_refuse(self):
        raw, expected = synthetic_wheel()
        for changed in (raw.replace(b'example.py', b'exam\0le.py'),
                        raw.replace(b'example.py', b'changed.py', 1)):
            with self.assertRaises(m.DistributionError):
                m.wheel(changed, {**expected, 'sha256': m.sha(changed)})

    def test_link_and_traversal_refuse(self):
        raw, expected = synthetic_wheel()
        with zipfile.ZipFile(io.BytesIO(raw)) as original:
            for bad in ('../escape', 'link'):
                out = io.BytesIO()
                with zipfile.ZipFile(out, 'w') as z:
                    for info in original.infolist():
                        z.writestr(info, original.read(info))
                    info = zipfile.ZipInfo(bad)
                    info.create_system = 3
                    info.external_attr = (stat.S_IFLNK|0o777) << 16
                    z.writestr(info, b'example.py')
                changed = out.getvalue()
                with self.assertRaises(m.DistributionError):
                    m.wheel(changed, {**expected, 'bytes': len(changed), 'sha256': m.sha(changed)})


class PlatformContract(unittest.TestCase):
    def test_exact_four_targets(self):
        for v in (12, 13):
            common = {'implementation': 'CPython', 'version': [3, v], 'gil_disabled': False, 'pointer_bits': 64}
            for platform in ({'platform': 'darwin', 'machine': 'arm64', 'macos': '15.2', 'libc': ['', '']},
                             {'platform': 'linux', 'machine': 'x86_64', 'libc': ['glibc', '2.34'], 'macos': ''}):
                self.assertIn(m.target_for_runtime({**common, **platform}), m.TARGETS)

    def test_no_abi_arch_or_libc_guess(self):
        row = {'implementation': 'CPython', 'version': [3, 13], 'platform': 'linux',
               'machine': 'x86_64', 'libc': ['glibc', '2.34'], 'macos': '', 'gil_disabled': False, 'pointer_bits': 64}
        for change in ({'implementation': 'PyPy'}, {'version': [3, 14]}, {'version': [3, True]},
                       {'machine': 'aarch64'}, {'libc': ['musl', '2.34']}, {'libc': ['glibc', '2.33']},
                       {'libc': ['glibc', '2.34 extra']}, {'gil_disabled': True},
                       {'gil_disabled': 0}, {'pointer_bits': 32}, {'pointer_bits': True}):
            with self.assertRaises(m.DistributionError):
                m.target_for_runtime({**row, **change})


class DependencyContract(unittest.TestCase):
    def test_numeric_markers_and_no_evaluation(self):
        env = {'python_version': '3.13', 'sys_platform': 'linux', 'extra': ''}
        self.assertTrue(m.marker_matches("python_version > '3.9' and sys_platform != 'emscripten'", env))
        self.assertFalse(m.marker_matches("extra == 'ssh'", env))
        with self.assertRaises((m.DistributionError, SyntaxError)):
            m.marker_matches("__import__('os').system('PRIVATE')", env)
        with self.assertRaises(m.DistributionError):
            m.marker_matches("unknown_field == 'anything'", env)

    def test_active_crypto_extra_and_all_four_declared_graphs(self):
        value = json.loads((ROOT/m.PROFILE_FILE).read_bytes())
        for target, rows in value['targets'].items():
            graph = m.dependency_graph(target, rows, value['wheels'])
            self.assertIn(['pyjwt', 'cryptography'], graph['edges'])
            self.assertIn(['cryptography', 'cffi'], graph['edges'])
            self.assertIn(['rfc3339-validator', 'six'], graph['edges'])
            self.assertEqual(graph['selected_extras'], {'pyjwt': ['crypto']})
            self.assertFalse(any('pywin32' in edge for edge in graph['edges']))

    def test_missing_or_incompatible_runtime_package_refuses(self):
        value = json.loads((ROOT/m.PROFILE_FILE).read_bytes())
        target = sorted(value['targets'])[0]
        rows = json.loads(json.dumps(value['targets'][target]))
        next(x for x in rows if x['name'] == 'cryptography')['version'] = '0.1'
        with self.assertRaises(m.DistributionError):
            m.dependency_graph(target, rows, value['wheels'])
        with self.assertRaises(m.DistributionError):
            m.dependency_graph(target, rows[:-1], value['wheels'])

    def test_release_constraints_and_unknown_syntax_refusal(self):
        self.assertTrue(m.version_satisfies('2.16.2', [('>=', '2.10.0'), ('<', '3')]))
        self.assertFalse(m.version_satisfies('2.16.2', [('==', '1.*')]))
        self.assertEqual(m.requirement_parts('pyjwt[crypto]>=2.10.1')[0:2], ('pyjwt', ['crypto']))
        with self.assertRaises(m.DistributionError):
            m.requirement_parts('pkg @ https://unapproved.invalid/package.whl')


class ObligationEncoding(unittest.TestCase):
    def test_exact_expanded_graph_preserved(self):
        raw = (ROOT/'sbom/mcp-runtime/obligations.json.gz').read_bytes()
        value = m.decode_obligations(raw)
        self.assertEqual(len(value['source_packages']), 150)
        self.assertEqual(m.sha(gzip.decompress(raw)),
                         'c26b2f4503739275a5f6d8f7686de052a5de065d3016f51293185fcc25cb6675')
        self.assertFalse(value['claims']['distribution_approved'])

    def test_truncation_trailing_and_concatenated_members_refuse(self):
        raw = (ROOT/'sbom/mcp-runtime/obligations.json.gz').read_bytes()
        for changed in (raw[:-1], raw+b'extra', raw+raw):
            with self.assertRaises(m.DistributionError):
                m.decode_obligations(changed)

    def test_expansion_overflow_refuses_before_json_validation(self):
        packed = gzip.compress(b'x'*4_000_001, mtime=0)
        # CPython3.12 may use zlib's platform OS byte; the released format pins
        # 255, independently of the interpreter executing this inert control.
        packed = packed[:9]+b'\xff'+packed[10:]
        with patch.object(m, 'decode', side_effect=AssertionError('must not parse')), \
             self.assertRaises(m.DistributionError):
            m.decode_obligations(packed)

    def test_compressed_input_bound_precedes_inflate(self):
        oversized = bytes.fromhex('1f8b08000000000002ff')+b'x'*2_000_000
        with patch.object(m.zlib, 'decompressobj', side_effect=AssertionError('must not inflate')), \
             self.assertRaises(m.DistributionError):
            m.decode_obligations(oversized)


class Publication(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        # macOS's default /var temporary prefix is a system symlink. The tool
        # intentionally refuses supplied links; use the actual owned directory.
        self.parent = Path(self.temp.name).resolve()
        self.parent.chmod(0o700)
        self.output = self.parent/'artifact.zip'

    def test_nooverwrite_complete_private_file(self):
        with Capture() as c:
            m.publish_bytes(c, self.output, b'complete', lambda: None)
        self.assertEqual(self.output.read_bytes(), b'complete')
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o600)
        with self.assertRaises(m.DistributionError), Capture() as c:
            m.publish_bytes(c, self.output, b'replacement', lambda: None)
        self.assertEqual(self.output.read_bytes(), b'complete')

    def test_source_drift_before_link_leaves_no_final(self):
        with self.assertRaises(m.DistributionError), Capture() as c:
            m.publish_bytes(c, self.output, b'complete', lambda: m.need(False))
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.parent.glob('.mcp-bundle-*')))

    def test_temporary_cleanup_after_link_reports_uncertainty(self):
        original = os.unlink
        def fail(name, *args, **kwargs):
            if str(name).startswith('.mcp-bundle-'):
                raise OSError('PRIVATE CANARY must never escape')
            return original(name, *args, **kwargs)
        with self.assertRaises(OutputCommitUncertain), Capture() as c, patch.object(m.os, 'unlink', side_effect=fail):
            m.publish_bytes(c, self.output, b'complete', lambda: None)
        self.assertEqual(self.output.read_bytes(), b'complete')
        for p in self.parent.glob('.mcp-bundle-*'):
            p.unlink()

    def test_fdopen_failure_relinquishes_all_raw_descriptors(self):
        c = Capture()
        with self.assertRaises(OSError), patch.object(m.os, 'fdopen', side_effect=OSError('private')):
            with c:
                m.publish_bytes(c, self.output, b'complete', lambda: None)
        self.assertFalse(c.fds)
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.parent.glob('.mcp-bundle-*')))

    def test_all_closes_attempted_postcommit_failure_is_uncertain(self):
        c = Capture()
        m.publish_bytes(c, self.output, b'complete', lambda: None)
        owned = list(c.fds)
        closed = []
        original = os.close
        def close(fd):
            closed.append(fd)
            original(fd)
            if fd == owned[-1]:
                raise OSError('after release')
        with patch.object(m.os, 'close', side_effect=close), self.assertRaises(OutputCommitUncertain):
            c.close()
        self.assertEqual(set(closed), set(owned))
        self.assertEqual(len(closed), len(set(closed)))
        self.assertEqual(self.output.read_bytes(), b'complete')

    def test_parent_link_and_fifo_are_refused(self):
        link = self.parent/'symlink'
        link.symlink_to(self.parent, target_is_directory=True)
        with self.assertRaises(OSError), Capture() as c:
            m.publish_bytes(c, link/'bad.zip', b'bytes', lambda: None)
        fifo = self.parent/'fifo'
        os.mkfifo(fifo, 0o600)
        with self.assertRaises(ValueError), Capture() as c:
            c.read(fifo, 1000)

    def test_materialize_refuses_parent_link_without_touching_external(self):
        actual = self.parent/'actual'
        actual.mkdir(mode=0o700)
        outside = self.parent/'outside'
        outside.mkdir(mode=0o700)
        (outside/'canary').write_bytes(b'UNCHANGED')
        (actual/'link').symlink_to(outside, target_is_directory=True)
        fd = os.open(actual, os.O_RDONLY|os.O_DIRECTORY)
        try:
            with self.assertRaises(m.DistributionError):
                m.materialize(fd, {'link/canary': b'changed'})
        finally:
            os.close(fd)
        self.assertEqual((outside/'canary').read_bytes(), b'UNCHANGED')

    def test_materialize_detects_short_write_and_closes_raw_fd(self):
        actual = self.parent/'actual'
        actual.mkdir(mode=0o700)
        root = os.open(actual, os.O_RDONLY|os.O_DIRECTORY)
        seen = []
        def fail(fd, *args, **kwargs):
            seen.append(fd)
            self.assertIs(kwargs['closefd'], False)
            raise OSError('PRIVATE')
        try:
            with patch.object(m.os, 'fdopen', side_effect=fail), self.assertRaises(m.DistributionError):
                m.materialize(root, {'file': b'body'})
        finally:
            os.close(root)
        self.assertEqual(len(seen), 1)
        with self.assertRaises(OSError):
            os.fstat(seen[0])

    def test_home_is_preserved_and_no_service_credentials_passed(self):
        called = []
        def child(argv, **kwargs):
            called.append(argv)
            return subprocess.CompletedProcess(argv, 0, b'fixed', b'')
        with patch.object(m, 'run_worker', side_effect=child):
            self.assertEqual(m.command(['/fixed/python', '-I'], task_directory=self.parent), b'fixed')
        argv = called[0]
        self.assertEqual([x for x in argv if x.startswith('HOME=')],
                         ['HOME='+os.environ['HOME']] if 'HOME' in os.environ else [])
        self.assertIn('PIP_CONFIG_FILE=/dev/null', argv)
        self.assertFalse(any(x.startswith(('GITHUB_TOKEN=', 'AITRUST_TOKEN=', 'CODEX_HOME=')) for x in argv))

    def test_zero_length_payload_and_link_refusal(self):
        empty = self.parent/'empty'
        empty.write_bytes(b'')
        with Capture() as capture:
            self.assertEqual(m.read_payload(capture, empty, 0), b'')
            capture.check()
        link = self.parent/'link'
        link.symlink_to(empty)
        with Capture() as capture, self.assertRaises(OSError):
            m.read_payload(capture, link, 0)

    def test_capacity_refusal_precedes_workspace_and_child_creation(self):
        archive = self.parent/'input.zip'
        archive.write_bytes(b'fixed')
        result = {'target': 'cp313-macosx_11_0_arm64', 'sha256': m.sha(b'fixed')}
        usage = type('Usage', (), {'free': 1})()
        with patch.object(m, 'verify', return_value=(result, {})), \
             patch.object(m.shutil, 'disk_usage', return_value=usage), \
             patch.object(m.os, 'mkdir', side_effect=AssertionError('must not create')), \
             patch.object(m, 'command', side_effect=AssertionError('must not spawn')):
            with self.assertRaises(m.InstallCapacityUnavailable):
                m.install(archive, self.parent/'connection.json', python=sys.executable, pip_python=sys.executable)
        self.assertFalse((self.parent/'connection.json').exists())


class CliPrivacy(unittest.TestCase):
    def test_invalid_argument_and_missing_file_never_echo(self):
        for args in (['--PRIVATE-CANARY'], ['verify', '/PRIVATE-CANARY/missing.zip']):
            p = subprocess.run([sys.executable, '-I', '-S', '-B', str(ROOT/'scripts/mcp-distribution.py'), *args],
                               capture_output=True, timeout=5)
            self.assertEqual(p.returncode, 2)
            self.assertNotIn(b'PRIVATE-CANARY', p.stdout+p.stderr)
            self.assertNotIn(b'Traceback', p.stderr)


class InstalledPayloads(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.base.chmod(0o700)
        self.site = self.base/'venv/lib/python3.13/site-packages'
        self.site.mkdir(parents=True)
        raw, expected = synthetic_wheel()
        record = m.wheel(raw, expected)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            for name in z.namelist():
                path = self.site/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(z.read(name))
        self.target = 'cp313-linux_x86_64_glibc_2_34'
        self.profile = {'targets': {self.target: [expected]}, 'wheels': [record]}

    def test_version_label_cannot_hide_changed_code(self):
        self.assertEqual(m.verify_runtime_files(self.base, self.target, self.profile), 4)
        (self.site/'example.py').write_bytes(b'value = 2\n')
        with self.assertRaises(m.DistributionError):
            m.verify_runtime_files(self.base, self.target, self.profile)

    def test_unknown_code_or_pth_refuses_without_execution(self):
        for name in ('unknown.py', 'unknown.pth'):
            p = self.site/name
            p.write_bytes(b'raise RuntimeError("must not execute")\n')
            with self.assertRaises(m.DistributionError):
                m.verify_runtime_files(self.base, self.target, self.profile)
            p.unlink()

    def test_payload_symlink_refuses(self):
        p = self.site/'example.py'
        p.unlink()
        outside = self.base/'outside'
        outside.write_bytes(b'value = 1\n')
        p.symlink_to(outside)
        with self.assertRaises(m.DistributionError):
            m.verify_runtime_files(self.base, self.target, self.profile)

    def test_received_launch_command_is_not_authority(self):
        archive = self.base/'artifact.zip'
        archive.write_bytes(b'fixed')
        connection = self.base/'connection.json'
        workspace = self.base/'workspace'
        workspace.mkdir(mode=0o700)
        record = {'profile': m.PROFILE, 'target': self.target, 'artifact_sha256': m.sha(b'fixed'),
                  'runtime_distributions': [], 'workspace': str(workspace), 'runtime_payload_count': 4,
                  'mcpServers': {'aitrustid': {'command': '/unapproved/caller-command', 'args': []}},
                  'release_authorized': False, 'privacy_service_installed': False}
        connection.write_bytes(m.canonical(record))
        connection.chmod(0o600)
        result = {'target': self.target, 'sha256': m.sha(b'fixed')}
        with patch.object(m, 'verify', return_value=(result, {})), \
             patch.object(m, 'command', side_effect=AssertionError('must not execute')):
            with self.assertRaises(m.DistributionError):
                m.verify_install(archive, connection, execute_probe=True)

    def target_configuration(self, target):
        # Isolate the prerequisite-target boundary after trusted format/source
        # checks: no SDK is installed/imported; only fixed stdlib Python runs.
        archive = self.base/'artifact.zip'
        archive.write_bytes(b'fixed')
        connection = self.base/'connection.json'
        workspace = self.base/'workspace'
        workspace.mkdir(mode=0o700)
        (workspace/'tmp').mkdir(mode=0o700)
        (workspace/'venv/bin').mkdir(parents=True)
        (workspace/'venv/bin/python').symlink_to(sys.executable)
        (workspace/'venv/pyvenv.cfg').write_text('include-system-site-packages = false\n')
        record = {'profile': m.PROFILE, 'target': target, 'artifact_sha256': m.sha(b'fixed'),
                  'runtime_distributions': [['example', '1']], 'workspace': str(workspace), 'runtime_payload_count': 4,
                  'mcpServers': {'aitrustid': {'command': str(workspace/'venv/bin/python'),
                       'args': ['-I', '-B', str(workspace/'project/scripts/ai-tools-server.py')]}},
                  'release_authorized': False, 'privacy_service_installed': False}
        connection.write_bytes(m.canonical(record))
        connection.chmod(0o600)
        profile = {'targets': {target: [{'name': 'example', 'version': '1'}]}}
        return archive, connection, {'target': target, 'sha256': m.sha(b'fixed')}, \
            {'project/'+m.PROFILE_FILE: m.canonical(profile)}

    def host_target(self, minor):
        return f'cp3{minor}-'+('macosx_11_0_arm64' if sys.platform == 'darwin' else 'linux_x86_64_glibc_2_34')

    def test_changed_interpreter_target_refuses_before_sdk_probe(self):
        target = self.host_target(12 if sys.version_info.minor == 13 else 13)
        archive, connection, result, members = self.target_configuration(target)
        with patch.object(m, 'verify', return_value=(result, members)), \
             patch.object(m, 'verify_materialized'), patch.object(m, 'verify_runtime_files', return_value=4), \
             self.assertRaises(m.DistributionError):
            m.verify_install(archive, connection, python=sys.executable)

    def test_actual_matching_stdlib_target_rechecked_without_sdk(self):
        target = self.host_target(sys.version_info.minor)
        archive, connection, result, members = self.target_configuration(target)
        with patch.object(m, 'verify', return_value=(result, members)), \
             patch.object(m, 'verify_materialized'), patch.object(m, 'verify_runtime_files', return_value=4):
            value = m.verify_install(archive, connection, python=sys.executable)
        self.assertTrue(value['runtime_target_verified'])
        self.assertIsNone(value['runtime'])


if __name__ == '__main__':
    unittest.main()
