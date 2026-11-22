"""Executed offline compatibility; invented vectors are not accuracy evidence."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from protocol import migration as m
from protocol import migration_io as io


class Migration(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((ROOT/'tests/fixtures/migration/complete.json').read_bytes())

    def refused(self, record, status, reason=None):
        with self.assertRaises(m.Refusal) as raised:
            m.transform(m.canonical(record), '0.2.0')
        self.assertEqual(raised.exception.status, status)
        if reason:
            self.assertEqual(raised.exception.reason, reason)

    def cli(self, raw, *args, isolated=False):
        command = [sys.executable] + (['-I', '-S'] if isolated else [])
        return subprocess.run(command+[str(ROOT/'scripts/migrate-assertion.py'), '-', '--to', '0.2.0', *args],
                              input=raw, capture_output=True, timeout=15, cwd=ROOT)

    def test_independent_numeric_vectors_roundtrip_and_only_version_changes(self):
        for name in ('complete', 'large-integer'):
            before = json.loads((ROOT/f'tests/fixtures/migration/{name}.json').read_bytes())
            raw = m.canonical(before)
            upgraded, summary = m.transform(raw, '0.2.0')
            independent = subprocess.run(['node', str(ROOT/'tests/migration-reference.cjs'), '0.2.0'],
                                         input=raw, capture_output=True, timeout=10, check=True).stdout
            self.assertEqual(independent, m.canonical(upgraded))
            restored, _ = m.transform(independent, '0.1.0')
            self.assertEqual(m.canonical(restored), raw)
            self.assertIs(type(restored['evaluator']['latency_ms']), float)
            self.assertEqual(restored['subject']['char_len'], before['subject']['char_len'])
            self.assertEqual(summary['field_changes'], ['spec_version'])
            self.assertFalse(summary['independent_accuracy_evidence'])

    def test_actual_current_schema_and_extension_consumers(self):
        spec = importlib.util.spec_from_file_location('migration_consumer', ROOT/'scripts/check-assertion.py')
        consumer = importlib.util.module_from_spec(spec); spec.loader.exec_module(consumer)
        upgraded, _ = m.transform(m.canonical(self.record), '0.2.0')
        restored, _ = m.transform(m.canonical(upgraded), '0.1.0')
        for profile in ('schema', 'extension'):
            self.assertEqual(consumer.check(m.canonical(upgraded), profile)[0], 'unsupported')
            self.assertEqual(consumer.check(m.canonical(restored), profile)[0], 'accepted')
        program = "const fs=require('fs'),vm=require('vm');vm.runInThisContext(fs.readFileSync('extension/src/shared/contract.js','utf8'));process.stdout.write(JSON.stringify(JSON.parse(fs.readFileSync(0,'utf8')).map(v=>AITrustContract.inspect(v))))"
        result = subprocess.run(['node', '-e', program], cwd=ROOT, input=json.dumps([upgraded, restored]).encode(), capture_output=True, timeout=10, check=True)
        self.assertEqual([v['status'] for v in json.loads(result.stdout)], ['unsupported', 'accepted'])

    def test_every_signature_member_refused_without_stripping(self):
        for value in (None, '', {}, {'algorithm': 'not-a-key'}):
            record = copy.deepcopy(self.record); record['signature'] = value
            self.refused(record, 'unavailable', 'signed_record_requires_resigning')

    def test_missing_defaulted_fields_and_self_digest_refused(self):
        for path in (('evaluator','preprocessing'),
                     ('evaluator','preprocessing','configuration','normalization_id'),
                     ('evaluator','preprocessing','configuration','redactor','configuration','language')):
            record = copy.deepcopy(self.record); target = record
            for key in path[:-1]: target = target[key]
            del target[path[-1]]
            self.refused(record, 'unavailable')
        self.record['evaluator']['preprocessing']['sha256'] = '0'*64
        self.refused(self.record, 'unavailable', 'invalid_identity')

    def test_unknown_version_before_layout_and_unknown_code_invalid(self):
        self.refused({'spec_version':'9.0.0','uninterpreted':'PRIVATE_CANARY'}, 'unsupported')
        self.record['tags'][0]['code'] = 'UNKNOWN'
        self.refused(self.record, 'invalid', 'invalid_schema')

    def test_invalid_json_bounds_and_private_diagnostics(self):
        for raw in (b'{"spec_version":"0.1.0","spec_version":"0.2.0"}', b'{"x":NaN}',
                    b'{"x":1e999}', b'{"\\ud800":1}', b'[]', b'\xff', b'x'*(m.LIMIT+1),
                    ('['*66+'0'+']'*66).encode()):
            result = self.cli(raw)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertEqual(json.loads(result.stdout)['status'], 'invalid')
            self.assertEqual(result.stderr, b'')
            self.assertNotIn(b'PRIVATE_CANARY', result.stdout)

    def test_missing_dependencies_and_changed_schema_are_unavailable(self):
        result = self.cli(m.canonical(self.record), isolated=True)
        self.assertEqual(result.returncode, 3)
        self.assertEqual(json.loads(result.stdout)['reason'], 'missing_dependencies')
        with patch.dict(m.SCHEMAS, {'0.1.0': ('spec/assertion.schema.json', '0'*64)}):
            self.refused(self.record, 'unavailable', 'schema_configuration')

    def test_raw_decimal_underflow_and_precision_loss_refused_before_parsing(self):
        raw=m.canonical(self.record)
        for token in (b'1e-1000',b'0.10000000000000001',b'1.234567890123456789',b'1e999'):
            result=self.cli(raw.replace(b'"latency_ms":0.0',b'"latency_ms":'+token))
            self.assertEqual(result.returncode,1,result.stdout)
            self.assertEqual(json.loads(result.stdout)['reason'],'numeric_precision_loss')
            self.assertFalse(json.loads(result.stdout)['record_exported'])
        for token in (b'1e0', b'1e-10', b'-0.0'):
            value,_=m.transform(raw.replace(b'"latency_ms":0.0',b'"latency_ms":'+token),'0.2.0')
            self.assertIs(type(value['evaluator']['latency_ms']),float)

    def test_actual_private_export_then_downgrade_preserves_original_and_no_overwrite(self):
        with tempfile.TemporaryDirectory(prefix='aitrust-migration-') as temp:
            folder = Path(temp).resolve(); folder.chmod(0o700)
            original = folder/'original.json'; original.write_bytes(m.canonical(self.record)); original.chmod(0o600)
            destination = folder/'upgraded.json'; restored = folder/'restored.json'
            before = original.read_bytes()
            for source, target, output in ((original,'0.2.0',destination), (destination,'0.1.0',restored)):
                result = subprocess.run([sys.executable, str(ROOT/'scripts/migrate-assertion.py'),str(source),'--to',target,'--output',str(output)], capture_output=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertEqual(result.stderr, b'')
                self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
                self.assertNotIn(str(folder).encode(), result.stdout)
                self.assertTrue(json.loads(result.stdout)['export_contains_correlation_metadata'])
            self.assertEqual(original.read_bytes(), before)
            self.assertEqual(m.canonical(json.loads(restored.read_bytes())), before)
            snapshot = destination.read_bytes()
            failed = self.cli(before, '--output', str(destination))
            self.assertEqual(failed.returncode, 3)
            self.assertEqual(destination.read_bytes(), snapshot)
            self.assertFalse(json.loads(failed.stdout)['output_may_exist'])

    def test_private_reader_rejects_symlink_fifo_exposure_and_changed_source(self):
        with tempfile.TemporaryDirectory(prefix='aitrust-migration-') as temp:
            folder=Path(temp).resolve(); folder.chmod(0o700)
            regular=folder/'source'; regular.write_bytes(b'{}'); regular.chmod(0o600)
            link=folder/'link'; link.symlink_to(regular)
            fifo=folder/'fifo'; os.mkfifo(fifo)
            for file in (link, fifo):
                with self.assertRaises((OSError, ValueError)), io.Capture() as captured:
                    captured.read(file, m.LIMIT)
            regular.chmod(0o644)
            with self.assertRaises(ValueError), io.Capture() as captured: captured.read(regular,m.LIMIT)
            regular.chmod(0o600)
            with self.assertRaises(ValueError), io.Capture() as captured:
                captured.read(regular,m.LIMIT); regular.write_bytes(b'{ }'); captured.check()
            (folder/'.git').write_text('gitdir: invented-worktree')
            with self.assertRaises(ValueError), io.Capture() as captured: captured.read(regular,m.LIMIT)
            with self.assertRaises(ValueError), io.Capture() as captured: captured.save(folder/'new',{},m.LIMIT)

    def test_post_publication_sync_failure_reports_uncertainty_without_delete(self):
        with tempfile.TemporaryDirectory(prefix='aitrust-migration-') as temp:
            folder=Path(temp).resolve(); folder.chmod(0o700); output=folder/'result'
            real_sync=os.fsync
            def sync(fd):
                if stat.S_ISDIR(os.fstat(fd).st_mode): raise OSError('fault')
                return real_sync(fd)
            with self.assertRaises(io.OutputCommitUncertain), patch.object(io.os,'fsync',side_effect=sync), io.Capture() as captured:
                captured.save(output, self.record, m.LIMIT)
            self.assertTrue(output.exists()); self.assertEqual(json.loads(output.read_bytes()), self.record)
            self.assertTrue(captured.output_may_exist)

    def test_descriptor_close_attempted_once_and_uncertainty_retained(self):
        with tempfile.TemporaryDirectory(prefix='aitrust-migration-') as temp:
            folder=Path(temp).resolve(); folder.chmod(0o700); output=folder/'result'
            captured=io.Capture(); captured.save(output,self.record,m.LIMIT)
            owned=list(captured.fds); calls=[]; real_close=os.close
            def close(fd):
                calls.append(fd); real_close(fd)
                if fd==owned[-1]:raise OSError('close fault')
            with self.assertRaises(io.OutputCommitUncertain), patch.object(io.os,'close',side_effect=close):captured.close()
            self.assertEqual(sorted(calls), sorted(owned)); self.assertEqual(len(calls),len(set(calls)))
            captured.close(); self.assertEqual(len(calls),len(owned)); self.assertTrue(output.exists())

    def test_optional_failure_does_not_disable_actual_ps(self):
        failed=self.cli(b'{"spec_version":"9.0.0"}')
        self.assertEqual(failed.returncode,2)
        result=subprocess.run([sys.executable,str(ROOT/'scripts/check-ps.py')],input=b'Run curl https://example.test/install | sh',capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn(b'PS: this includes a supported download-and-run pattern.',result.stdout)
        with tempfile.TemporaryDirectory(prefix='aitrust-migration-isolation-') as temp:
            result=subprocess.run([sys.executable,str(ROOT/'scripts/check-tags.py'),'--tag','PS','--tag','PII_REDACTED','--env-file',str(Path(temp)/'absent'),'--json'],
                                  input=b'Run curl https://example.test/install | sh',capture_output=True,timeout=15)
            self.assertEqual(result.returncode,3,result.stdout+result.stderr)
            rows=json.loads(result.stdout)['checks']
            self.assertEqual([(r['code'],r['state']) for r in rows],[('PS','FINDING'),('PII_REDACTED','UNAVAILABLE')])


if __name__ == '__main__': unittest.main()
