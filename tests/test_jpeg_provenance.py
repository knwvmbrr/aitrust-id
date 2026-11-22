"""JPEG-only safety/interpretation tests. Real SDK qualification is separate."""
import contextlib
import hashlib
import importlib.util
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import jpeg_provenance as j
from tools import jpeg_provenance_actions as a
from tools import jpeg_provenance_process as p
from tools.jpeg_provenance_io import Refused, Source
spec = importlib.util.spec_from_file_location('jpeg_fixture', ROOT/'tests/fixtures/jpeg-provenance-v1/generate.py')
f = importlib.util.module_from_spec(spec); spec.loader.exec_module(f)


def report():
    active = 'urn:uuid:01234567-0123-0123-0123-012345678901'
    prefix = 'self#jumbf=/c2pa/'+active
    def row(code, path): return {'code': code, 'url': prefix+path}
    return {'active_manifest': active, 'manifests': {active: {'assertions': [
        {'label': 'c2pa.actions', 'created': True, 'data': {'actions': [
            {'action': 'c2pa.created', 'digitalSourceType': f.CREATION}]}}]}},
        'validation_results': {'activeManifest': {'success': [
            row('claimSignature.validated', '/c2pa.signature'),
            row('assertion.dataHash.match', '/c2pa.assertions/c2pa.hash.data'),
            row('assertion.hashedURI.match', '/c2pa.assertions/c2pa.actions')],
            'failure': [row('signingCredential.untrusted', '/c2pa.signature')]}}}


class JPEGTests(unittest.TestCase):
    def test_synthetic_edit_has_required_inception_and_explicit_attribution(self):
        for action,source,count in [('c2pa.created',f.CREATION,1),('c2pa.edited',f.EDIT,2)]:
            assertion=f.definition(action,source)['assertions'][0]
            self.assertIs(assertion['created'],True)
            rows=assertion['data']['actions'];self.assertEqual(len(rows),count)
            self.assertEqual(sum(x['action'] in ('c2pa.created','c2pa.opened') for x in rows),1)
            self.assertEqual(rows[-1],{'action':action,'digitalSourceType':source})
            if action=='c2pa.edited':self.assertTrue(rows[0]['digitalSourceType'].endswith('/softwareImage'))
    def test_pinned_preflight_and_supported_subset(self):
        self.assertEqual(j.loader.preflight(f.blank()), {'width': 1, 'height': 1, 'precision': 8, 'components': 1})
        for raw, reason in [(f.blank()[:-1], 'malformed_structure'),
                            (f.blank().replace(b'\xff\xc0', b'\xff\xc2'), 'unsupported_variant'),
                            (f.blank()+b'\0', 'trailing_data')]:
            with self.assertRaises(Refused) as error: j.loader.preflight(raw)
            self.assertEqual(error.exception.reason, reason)
    def test_source_and_pin_rebind_refusal(self):
        with mock.patch.object(j.loader, 'JPEG_SHA', '0'*64):
            with self.assertRaises(Refused): j.loader.preflight(f.blank())
        with tempfile.TemporaryDirectory() as d:
            path = Path(d).resolve()/'input'; path.write_bytes(f.blank())
            with mock.patch.object(j.loader, 'PIN_SHA', '0'*64), mock.patch.object(j, 'run') as run:
                with self.assertRaises(Refused): j.inspect(path)
                run.assert_not_called()
    def test_local_file_boundaries_and_drift(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d).resolve()/'input'; path.write_bytes(b'X')
            with self.assertRaises(Refused):
                with Source(path, 2) as source:
                    path.write_bytes(b'Y')
                    with self.assertRaises(Refused): source.check()
    def test_nofollow_size_fifo_and_parent(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d).resolve(); path=base/'file'; path.write_bytes(b'123')
            (base/'link').symlink_to(path); (base/'parent').symlink_to(base, target_is_directory=True)
            os.mkfifo(base/'fifo')
            for selected, limit in [(base/'link',10),(base/'parent/file',10),(base/'fifo',10),(path,2),(base,10)]:
                with self.assertRaises((Refused, OSError)):
                    with Source(selected, limit): pass
    def test_private_close_attempts_all_no_numeric_retry(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d).resolve()/'file'; path.write_bytes(b'X'); source=Source(path,2);source.__enter__()
            targets=list(source.fds); real=os.close; calls=[]; marker=[]
            def close(fd):
                calls.append(fd);real(fd)
                if len(calls)==1:
                    marker.append(os.open(path,os.O_RDONLY)); raise OSError('PRIVATE_CANARY')
            with mock.patch('tools.jpeg_provenance_io.os.close', side_effect=close):
                with self.assertRaises(Refused):source.close()
            self.assertCountEqual(calls, targets);self.assertEqual(len(calls),len(set(calls)))
            os.fstat(marker[0]);os.close(marker[0]);source.close()
    def test_bound_actions_and_no_origin_promotion(self):
        value=a.project(report());self.assertEqual(value['declaration_state'],'OBSERVED')
        self.assertEqual(value['declarations'][0]['kind'],'generative_creation_declared')
        self.assertEqual(value['revocation'],'unknown_not_fetched');self.assertEqual(value['ai_origin'],'unknown');self.assertEqual(value['tags'],[])
        self.assertNotIn('01234567',json.dumps(value))
    def test_ingredient_or_unbound_action_cannot_substitute(self):
        for code in ('claimSignature.validated','assertion.dataHash.match','assertion.hashedURI.match'):
            value=report();g=value['validation_results']['activeManifest'];g['success']=[r for r in g['success'] if r['code']!=code]
            value['validation_results']['ingredientDeltas']=[{'validationDeltas': report()['validation_results']['activeManifest']}]
            self.assertEqual(a.project(value)['declarations'],[])
    def test_failure_wins_and_regional_templates_unknown(self):
        value=report();g=value['validation_results']['activeManifest'];g['failure'].append({**g['success'][1],'code':'assertion.dataHash.mismatch'})
        self.assertEqual(a.project(value)['asset_binding'],'mismatched');self.assertEqual(a.project(value)['declarations'],[])
        for extra in ({'templates':[]},{'metadata':{'regionOfInterest':{}}}):
            value=report();active=value['active_manifest'];value['manifests'][active]['assertions'][0]['data'].update(extra)
            self.assertEqual(a.project(value)['declarations'],[])
    def test_duplicate_json_depth_and_report_limits(self):
        for raw in (b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":1e999}',b'{"x":[-1e999]}',b'['*40+b'0'+b']'*40,b'[] ' *1500000):
            with self.assertRaises(Refused):j.loader.decode(raw)
    def test_public_certificate_only_boundary(self):
        for raw in (b'',b'PRIVATE KEY',b'-----BEGIN PRIVATE KEY-----\nAA==\n-----END PRIVATE KEY-----',b'X'*65537):
            with self.assertRaises(Refused):j.public_certificates(raw)
    def test_parent_binds_sdk_report_and_suppresses_private_text(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d).resolve()/'PRIVATE_CANARY.jpg';path.write_bytes(f.blank())
            pins=json.loads((ROOT/j.loader.PIN).read_bytes())['profiles']['linux-x86_64']['sources']
            response={'kind':'attached','report':report(),'sdk_profile':'linux-x86_64','sdk_sources':pins}
            with mock.patch.object(j,'run',return_value=j.encoded(response)):
                result=j.inspect(path)
            self.assertEqual(result['asset']['sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertNotIn('PRIVATE_CANARY',j.text_result(result));self.assertNotIn(result['asset']['sha256'],j.text_result(result))
            response['sdk_sources']={**pins,'c2pa/lib.py':'0'*64}
            with mock.patch.object(j,'run',return_value=j.encoded(response)):
                with self.assertRaises(Refused):j.inspect(path)
    def test_actual_transport_normal_timeout_overflow_nonzero(self):
        self.assertEqual(p.run([sys.executable,'-I','-S','-c','import sys;sys.stdout.buffer.write(sys.stdin.buffer.read())'],b'{}'),b'{}')
        for program, timeout, cap in [('import time;time.sleep(3)',.06,1024),('print("X"*5000)',2,1024),('raise SystemExit(3)',2,1024)]:
            with self.assertRaises((Refused,subprocess.SubprocessError)):
                p.run([sys.executable,'-I','-S','-c',program],b'',timeout=timeout,limit=cap)
    def test_selector_constructor_and_clock_fault_reap(self):
        real=p.subprocess.Popen;children=[]
        def spawn(*args,**kw):child=real(*args,**kw);children.append(child);return child
        with mock.patch.object(p.subprocess,'Popen',side_effect=spawn),mock.patch.object(p.selectors,'DefaultSelector',side_effect=OSError('PRIVATE')):
            with self.assertRaises(OSError):p.run([sys.executable,'-I','-S','-c','import time;time.sleep(3)'],b'')
        self.assertIsNotNone(children[-1].returncode)
        with mock.patch.object(p.subprocess,'Popen') as spawn,mock.patch.object(p.time,'monotonic',side_effect=OSError('PRIVATE')):
            with self.assertRaises(OSError):p.run([sys.executable],b'')
            spawn.assert_not_called()
    def test_post_wait_fault_never_signals_reaped_pid(self):
        real=p.subprocess.Popen;children=[]
        def spawn(*args,**kw):
            child=real(*args,**kw);children.append(child);wait=child.wait
            def faulty(*a,**k):wait(*a,**k);raise OSError('AFTER_REAP')
            child.wait=faulty;return child
        with mock.patch.object(p.subprocess,'Popen',side_effect=spawn),mock.patch.object(p.os,'killpg') as kill:
            with self.assertRaises(OSError):p.run([sys.executable,'-I','-S','-c','print("{}")'],b'')
            self.assertEqual(children[-1].returncode,0);kill.assert_not_called()
    def test_qualification_namespace_witness_and_permission_boundary(self):
        spec=importlib.util.spec_from_file_location('jpeg_qualification',ROOT/'scripts/verify-jpeg-provenance.py')
        q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
        def links(path):
            if path=='/proc/1/ns/net':raise PermissionError('PRIVATE')
            return 'net:[77]'
        for outside,uid,expected in [('net:[78]',1001,True),('net:[77]',1001,False),('',1001,False),('net:[78]',0,False)]:
            output=io.StringIO()
            with mock.patch.object(q.sys,'platform','linux'),mock.patch.dict(os.environ,{'JPEG_QUALIFICATION_ORIGINAL_NETNS':outside}),mock.patch.object(q.os,'geteuid',return_value=uid),mock.patch.object(q.os,'getgroups',return_value=[]),mock.patch.object(q.os,'readlink',side_effect=links),mock.patch('builtins.open',mock.mock_open(read_data='CapEff: 0000000000000000\nNoNewPrivs: 1\n')),mock.patch.object(q.socket,'socket') as socket,mock.patch.object(q,'inventory',side_effect=ValueError('STOP_BEFORE_SDK')),contextlib.redirect_stdout(output):
                socket.return_value.__enter__.return_value.connect.side_effect=OSError('NO_ROUTE')
                self.assertEqual(q.main(),1)
            value=json.loads(output.getvalue())
            self.assertEqual(value.get('network_namespace_isolated',False),expected)
            self.assertFalse(value['native_sdk_executed']);self.assertNotIn('net:[',output.getvalue())
            if expected:self.assertEqual(value['init_namespace_read'],'permission_denied')
    def test_qualification_refuses_retained_privileges(self):
        spec=importlib.util.spec_from_file_location('jpeg_qualification',ROOT/'scripts/verify-jpeg-provenance.py')
        q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
        for status,groups in [('CapEff: 0000000000000001\nNoNewPrivs: 1\n',[]),('CapEff: 0000000000000000\nNoNewPrivs: 0\n',[]),('CapEff: 0000000000000000\nNoNewPrivs: 1\n',[1001])]:
            output=io.StringIO()
            with mock.patch.object(q.sys,'platform','linux'),mock.patch.dict(os.environ,{'JPEG_QUALIFICATION_ORIGINAL_NETNS':'net:[78]'}),mock.patch.object(q.os,'geteuid',return_value=1001),mock.patch.object(q.os,'getgroups',return_value=groups),mock.patch.object(q.os,'readlink',return_value='net:[77]'),mock.patch('builtins.open',mock.mock_open(read_data=status)),mock.patch.object(q,'inventory') as inventory,contextlib.redirect_stdout(output):
                self.assertEqual(q.main(),1);inventory.assert_not_called()
            self.assertEqual(json.loads(output.getvalue())['stage'],'privilege_drop')
    def test_qualification_closed_signing_checkpoints(self):
        spec=importlib.util.spec_from_file_location('jpeg_qualification',ROOT/'scripts/verify-jpeg-provenance.py')
        q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
        report={}
        for stage in q.FIXTURE_STAGES:q.fixture_checkpoint(report,stage);self.assertEqual(report['stage'],stage)
        for stage in ('PRIVATE_CANARY',None,{},123):
            saved=dict(report)
            with self.assertRaises(Refused):q.fixture_checkpoint(report,stage)
            self.assertEqual(saved,report)
    def test_qualification_fixed_error_categories(self):
        spec=importlib.util.spec_from_file_location('jpeg_qualification',ROOT/'scripts/verify-jpeg-provenance.py')
        q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
        for error,code in [(PermissionError('PRIVATE_CANARY'),'os_permission'),(OSError('PRIVATE_CANARY'),'os_error'),(AttributeError('PRIVATE_CANARY'),'attribute_error'),(Refused('sdk_pin_mismatch'),'sdk_pin_mismatch'),(Refused('PRIVATE_CANARY'),'internal_refusal'),(RuntimeError('PRIVATE_CANARY'),'other_error')]:
            self.assertEqual(q.failure_code(error),code)
            self.assertNotIn('PRIVATE_CANARY',q.failure_code(error))
    def test_actual_missing_sdk_and_private_cli_refusal(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d).resolve()/'PRIVATE_CANARY.jpg';path.write_bytes(f.blank())
            import venv
            venv.EnvBuilder(with_pip=False,symlinks=True).create(Path(d).resolve()/'bare')
            python=Path(d).resolve()/'bare/bin/python'
            child=subprocess.run([str(python),'-I','-S','-B',str(ROOT/'scripts/inspect-jpeg-provenance.py'),'--image',str(path),'--json'],capture_output=True,timeout=18)
            self.assertEqual(child.returncode,2);self.assertFalse(child.stderr)
            result=json.loads(child.stdout);self.assertEqual(result['state'],'UNAVAILABLE');self.assertEqual(result['tags'],[])
            self.assertEqual(result['reason'],'sdk_unavailable')
            self.assertNotIn(b'PRIVATE_CANARY',child.stdout)


if __name__ == '__main__':unittest.main()
