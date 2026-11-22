"""Inert managed-consumer ordering/atomicity controls: no SDK or crypto proof."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import mcp_managed_release as m
from tools.artifact_evidence_io import Capture, OutputCommitUncertain


class ManagedConsumer(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name).resolve()
        self.directory.chmod(0o700)
        self.artifact = self.directory / 'source.zip'
        self.artifact.write_bytes(b'fixed inert archive')
        self.digest = hashlib.sha256(self.artifact.read_bytes()).hexdigest()
        self.record = {'artifact': {'sha256': self.digest, 'bytes': self.artifact.stat().st_size}}
        self.inputs = []
        for name, raw in [('packet', json.dumps(self.record).encode()),
                          ('spdx', b'{}'), ('bundle', b'{}'), ('roots', b'{}')]:
            path = self.directory / name
            path.write_bytes(raw)
            path.chmod(0o600)
            self.inputs.append(path)
        self.output = self.directory / 'connection.json'
        self.commit = '1' * 40
        self.events = []

    def authorize(self, record, archive, *args):
        self.events.append('authorize')
        self.assertEqual(archive.read_bytes(), self.artifact.read_bytes())
        return {'state': 'AUTHORIZED', 'release_authorized': True,
                'attestation_verified': True, 'policy_admitted': True,
                'artifact_sha256': self.digest, 'source_commit': self.commit}

    def install(self, archive, connection, **kwargs):
        self.events.append('install')
        self.assertFalse(self.output.exists())
        with Capture() as capture:
            capture.save(connection, {'release_authorized': False, 'mcpServers': {}}, 32_000)

    def verify(self, archive, connection, **kwargs):
        probe = kwargs['execute_probe']
        self.events.append('probe' if probe else 'recheck')
        self.assertFalse(self.output.exists())
        return {'sha256': self.digest, 'target': 'inert-target',
                'configuration_verified': True, 'runtime_target_verified': True,
                'release_authorized': False,
                'runtime': {'profile': 'mcp-installed-synthetic-runtime-proof/v1',
                    'pass': True, 'sdk_version': '2.3.0',
                    'cases': [{'id': x, 'status': 'PASS'} for x in m.PROBE_IDS]}}

    def run_install(self, *, authorize=None, installer=None, verifier=None, replay=None):
        with patch.object(m.shutil, 'disk_usage', return_value=type('Disk', (), {'free': 4*1024**3})()), \
             patch.object(m.artifacts, 'authorize_release', side_effect=authorize or self.authorize), \
             patch.object(m.runtime, 'install', side_effect=installer or self.install), \
             patch.object(m.runtime, 'verify_install', side_effect=verifier or self.verify), \
             patch.object(m.artifacts, 'verify_packet', side_effect=replay or (lambda *a: self.record)):
            return m.install_managed(self.artifact, *self.inputs, self.output,
                source_commit=self.commit, python=sys.executable, pip_python=sys.executable)

    def test_authorize_probe_recheck_then_private_publication(self):
        result = self.run_install()
        self.assertEqual(self.events, ['authorize', 'install', 'probe', 'recheck'])
        self.assertTrue(result['release_authorized'])
        self.assertNotIn(str(self.directory), json.dumps(result))
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)
        self.assertFalse(json.loads(self.output.read_bytes())['release_authorized'])

    def test_policy_refusal_precedes_signature_and_installer(self):
        # Exercise the real authorization gate with an injected denied policy
        # packet, isolating expensive packet construction only.
        with patch.object(m.artifacts, 'verify_packet', return_value={'policy': {'release_allowed': False}}), \
             patch.object(m.artifacts, 'verify_attestation') as signer, \
             patch.object(m.runtime, 'install') as installer, \
             patch.object(m.shutil, 'disk_usage', return_value=type('Disk', (), {'free': 4*1024**3})()):
            with self.assertRaises(m.ManagedReleaseUnavailable):
                m.install_managed(self.artifact, *self.inputs, self.output,
                    source_commit=self.commit, python=sys.executable, pip_python=sys.executable)
            signer.assert_not_called()
            installer.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_bad_signature_refuses_before_sdk(self):
        def refused(*args):
            self.events.append('bad-signature')
            raise ValueError('PRIVATE-CANARY')
        with self.assertRaises(m.ManagedReleaseUnavailable) as error:
            self.run_install(authorize=refused)
        self.assertEqual(self.events, ['bad-signature'])
        self.assertNotIn('PRIVATE-CANARY', str(error.exception))
        self.assertFalse(self.output.exists())
        self.assertTrue(list(self.directory.glob('.mcp-managed-*')))

    def test_original_input_drift_after_authorization_prevents_sdk(self):
        def changed(*args):
            result = self.authorize(*args)
            self.inputs[2].write_bytes(b'changed')
            return result
        with self.assertRaises(m.ManagedReleaseUnavailable):
            self.run_install(authorize=changed)
        self.assertEqual(self.events, ['authorize'])
        self.assertFalse(self.output.exists())

    def test_stage_drift_after_authorization_prevents_sdk(self):
        def changed(*args):
            result = self.authorize(*args)
            args[1].write_bytes(b'changed')
            return result
        with self.assertRaises(m.ManagedReleaseUnavailable):
            self.run_install(authorize=changed)
        self.assertEqual(self.events, ['authorize'])

    def test_duplicate_or_missing_probe_identity_refuses(self):
        for change in ('duplicate', 'missing', 'version', 'bool'):
            def bad(*args, **kwargs):
                value = self.verify(*args, **kwargs)
                if change == 'duplicate':
                    value['runtime']['cases'][1] = value['runtime']['cases'][0]
                elif change == 'missing':
                    value['runtime']['cases'].pop()
                elif change == 'version':
                    value['runtime']['sdk_version'] = 'unknown'
                else:
                    value['runtime']['pass'] = 1
                return value
            with self.subTest(change=change), self.assertRaises(m.ManagedReleaseUnavailable):
                self.run_install(verifier=bad)
            self.assertFalse(self.output.exists())

    def test_current_graph_drift_after_probe_prevents_publication(self):
        def drift(*args):
            raise ValueError('changed source')
        with self.assertRaises(m.ManagedReleaseUnavailable):
            self.run_install(replay=drift)
        self.assertEqual(self.events, ['authorize', 'install', 'probe'])
        self.assertFalse(self.output.exists())

    def test_existing_output_and_no_capacity_are_prework_refusals(self):
        self.output.write_bytes(b'owned existing')
        with self.assertRaises(m.ManagedReleaseUnavailable):
            self.run_install()
        self.assertEqual(self.output.read_bytes(), b'owned existing')
        self.assertFalse(self.events)
        self.output.unlink()
        with patch.object(m.shutil, 'disk_usage', return_value=type('Disk', (), {'free': 1})()):
            with self.assertRaises(m.ManagedReleaseUnavailable):
                m.install_managed(self.artifact, *self.inputs, self.output,
                    source_commit=self.commit, python=sys.executable, pip_python=sys.executable)
        self.assertFalse(list(self.directory.glob('.mcp-managed-*')))

    def test_internal_uncertainty_does_not_claim_final_output(self):
        def uncertain(*args, **kwargs):
            raise OutputCommitUncertain()
        with self.assertRaises(m.ManagedReleaseUnavailable) as error:
            self.run_install(installer=uncertain)
        self.assertIs(type(error.exception), m.ManagedReleaseUnavailable)
        self.assertFalse(error.exception.output_may_exist)
        self.assertFalse(self.output.exists())

    def test_post_final_link_cleanup_fault_is_explicit_uncertainty(self):
        real_unlink = os.unlink
        def fail_last(name, *args, **kwargs):
            if str(name).startswith('.artifact-evidence-') and self.output.exists():
                raise OSError('PRIVATE-CANARY')
            return real_unlink(name, *args, **kwargs)
        with patch.object(os, 'unlink', side_effect=fail_last):
            with self.assertRaises(m.ManagedReleaseUncertain) as error:
                self.run_install()
        self.assertTrue(error.exception.output_may_exist)
        self.assertTrue(self.output.exists())
        self.assertTrue(list(self.directory.glob('.mcp-managed-*')))

    def test_post_publication_close_fault_is_uncertain_without_fd_retry(self):
        real_close = os.close
        closed = []
        fault = []
        def fail_after_release(fd):
            self.assertNotIn(fd, closed)
            real_close(fd)
            if self.output.exists():
                closed.append(fd)
                if not fault:
                    fault.append(True)
                    raise OSError('PRIVATE-CANARY')
        with patch.object(os, 'close', side_effect=fail_after_release):
            with self.assertRaises(m.ManagedReleaseUncertain):
                self.run_install()
        self.assertTrue(fault)
        self.assertTrue(self.output.exists())

    def test_failed_stage_never_recursively_deletes_successor(self):
        marker = self.directory / 'unrelated-marker'
        marker.write_text('owned synthetic marker')
        def refused(*args):
            raise ValueError('signature refusal')
        with patch.object(m.shutil, 'rmtree', side_effect=AssertionError('no deletion')):
            with self.assertRaises(m.ManagedReleaseUnavailable):
                self.run_install(authorize=refused)
        self.assertEqual(marker.read_text(), 'owned synthetic marker')
        self.assertTrue(list(self.directory.glob('.mcp-managed-*')))

    def test_late_git_boundary_change_refuses_before_final_link(self):
        def marked(*args, **kwargs):
            result = self.verify(*args, **kwargs)
            if not kwargs['execute_probe']:
                (self.directory / '.git').write_text('owned synthetic marker')
            return result
        with self.assertRaises(m.ManagedReleaseUnavailable):
            self.run_install(verifier=marked)
        self.assertFalse(self.output.exists())

    def test_cli_isolated_help_and_malformed_args_are_private(self):
        script = ROOT / 'scripts/install-managed-mcp.py'
        for args, code in [(['--help'], 0), (['--unknown', 'PRIVATE-CANARY'], 2)]:
            result = subprocess.run([sys.executable, '-I', '-S', '-B', str(script), *args],
                                    cwd=self.directory, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, code)
            self.assertNotIn(b'PRIVATE-CANARY', result.stdout + result.stderr)

    def test_actual_cli_missing_input_is_fixed_and_no_publication(self):
        args = []
        for key, path in zip(('artifact', 'packet', 'spdx', 'bundle', 'trusted-root'),
                             (self.artifact, *self.inputs)):
            args.extend(['--' + key, str(path)])
        # A real CLI refusal, not a cryptographic/SDK success claim. Existing
        # capacity rules can refuse before these deliberately invalid inputs.
        result = subprocess.run([sys.executable, '-I', '-S', '-B',
            str(ROOT / 'scripts/install-managed-mcp.py'), *args,
            '--output', str(self.output), '--source-commit', self.commit,
            '--pip-python', sys.executable], cwd=self.directory, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b'')
        self.assertNotIn(str(self.directory).encode(), result.stderr)
        self.assertFalse(json.loads(result.stderr)['output_may_exist'])
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
