"""Small source-copy V5 boundary controls, never protected production evidence."""
import base64
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('copy_v5_test',ROOT/'tools/source_release_policy_v5.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

class SourceCopyV5(unittest.TestCase):
    def data(self):return v.policy((ROOT/v.POLICY).read_bytes())
    def fixture(self, extra=None):
        blobs={};q={}
        for name,body in {'LICENSE':b'Apache project license\n','tools/dependency_policy.py':b'# pinned code\n','owned.py':b'# SPDX-License-Identifier: Apache-2.0\nold=1\n'}.items():
            oid=hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest();q[name]=('100644',oid,len(body));blobs[oid]=body
        observed=dict(q)
        for name,body in (extra or {}).items():
            oid=hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest();observed[name]=('100644',oid,len(body));blobs[oid]=body
        d={'project_files':['owned.py','new.py'],'maintained_project_files':['owned.py'],'copied_files':[]};reads=[]
        def read(row):reads.append(row);return blobs[row[1]]
        return d,q,observed,read,reads
    def classify(self,*args):return v.classify(*args,v.Clock(),lambda n:None)
    def test_literal_current_policy_and_immutable_foundations(self):
        d=self.data();self.assertEqual(len(d['legacy_v4_names']),159);self.assertEqual(len(d['project_files'])+len(d['copied_files']),127)
        for name,row in v.FOUNDATION_PINS.items():
            raw=(ROOT/name).read_bytes();self.assertEqual(v.sha(raw),row['sha256']);self.assertEqual(len(raw),row['bytes'])
        self.assertEqual(len(d['copied_files'][0]['anchors']),95)
    def test_tiny_complete_source_positive_is_not_q_release(self):
        d,q,o,r,_=self.fixture({'new.py':b'# SPDX-License-Identifier: Apache-2.0\nx=1\n','owned.py':b'# SPDX-License-Identifier: Apache-2.0\nnew=2\n'})
        f=self.classify(d,q,o,r);self.assertEqual(f['introduced_named_project_text_files'],1);self.assertEqual(f['changed_named_project_text_files'],1);self.assertNotIn('release_authorized',f)
    def test_unknown_denominator_refuses_before_body(self):
        d,q,o,r,reads=self.fixture({'future.py':b'unknown'})
        with self.assertRaises(v.Refused)as e:self.classify(d,q,o,r)
        self.assertEqual(e.exception.code,'unknown_path');self.assertEqual(reads,[])
    def test_missing_base_member_refuses(self):
        d,q,o,r,_=self.fixture();o.pop('LICENSE')
        with self.assertRaises(v.Refused):self.classify(d,q,o,r)
    def test_changed_nonproject_and_dependency_code_refuse(self):
        for name in ['LICENSE','tools/dependency_policy.py']:
            d,q,o,r,_=self.fixture({name:b'changed'})
            with self.assertRaises(v.Refused):self.classify(d,q,o,r)
    def test_copyright_marker_change_refuses(self):
        d,q,o,r,_=self.fixture({'owned.py':b'# SPDX-License-Identifier: MIT\nx=2\n'})
        with self.assertRaises(v.Refused)as e:self.classify(d,q,o,r)
        self.assertEqual(e.exception.code,'license_declaration_changed')
    def test_new_foreign_grant_not_project_prose(self):
        d,q,o,r,_=self.fixture({'new.py':b'# Copyright Unrelated Author\nx=2\n'})
        with self.assertRaises(v.Refused):self.classify(d,q,o,r)
    def test_bool_numeric_git_rows_refuse(self):
        d,q,o,r,_=self.fixture();o['owned.py']=('100644','a'*40,True)
        with self.assertRaises(v.Refused):self.classify(d,q,o,r)
    def test_161_literal_capacity_refuses(self):
        d,q,o,r,_=self.fixture();d['project_files']=['x'+str(x)for x in range(161)]
        with self.assertRaises(v.Refused):self.classify(d,q,o,r)
    def test_one_body_and_decoded_budget_no_reset(self):
        c=v.Clock();b=v.Bodies(lambda a,n:b'x',c,reserved=v.MAX_INSPECTED-2);row=('100644',hashlib.sha1(b'blob 1\0x').hexdigest(),1)
        self.assertEqual(b.read(row),b'x');self.assertEqual(b.read(row),b'x')
        with self.assertRaises(v.Refused):b.charge(1)
    def test_sticky_backwards_and_nonfinite_clock(self):
        with mock.patch.object(v.time,'monotonic',side_effect=[100.,101.,99.,102.]):
            c=v.Clock();c.now()
            with self.assertRaises(v.Refused):c.now()
            with self.assertRaises(v.Refused):c.now()
        with mock.patch.object(v.time,'monotonic',return_value=float('nan')):
            with self.assertRaises(v.Refused):v.Clock()
    def test_original_timer_setup_and_teardown_restore(self):
        old=signal.getsignal(signal.SIGALRM)
        with mock.patch.object(v.signal,'setitimer',side_effect=[OSError('setup'),None]):
            with self.assertRaises(OSError):
                with v.original_clock(v.Clock()):pass
        self.assertEqual(signal.getsignal(signal.SIGALRM),old)
        actual=signal.setitimer
        def fail_cancel(which,seconds,*args):
            if seconds==0:raise OSError('cancel')
            return actual(which,seconds,*args)
        try:
            with mock.patch.object(v.signal,'setitimer',side_effect=fail_cancel):
                with self.assertRaises(OSError):
                    with v.original_clock(v.Clock()):pass
            self.assertEqual(signal.getsignal(signal.SIGALRM),old)
        finally:actual(signal.ITIMER_REAL,0)
    def test_regular_capture_and_fifo_preallocation_refusal(self):
        with tempfile.TemporaryDirectory()as t:
            p=Path(t).resolve()/'x';p.write_bytes(b'one');self.assertEqual(v.capture(p,3,v.Clock()),b'one')
            with self.assertRaises(v.Refused):v.capture(p,2,v.Clock())
            p.unlink();os.mkfifo(p)
            with self.assertRaises(v.Refused):v.capture(p,10,v.Clock())
    def test_baseline_normal_ack_and_no_ack_refusal(self):
        good="import sys,json;sys.stdin.buffer.read();print(json.dumps({'cleanup_complete':True,'cancelled':False,'result':{'scope':'inert fixture only'}}))"
        self.assertEqual(v._run_baseline(good,b'{}',v.Clock())['scope'],'inert fixture only')
        bad=good.replace("'cleanup_complete':True","'cleanup_complete':False")
        with self.assertRaises(v.Refused):v._run_baseline(bad,b'{}',v.Clock())
    def test_actual_git_fifo_term_unwinds_captured_worker(self):
        # Actual read-only Git blocks on a private fake loose-object FIFO. The
        # fixed worker bytes run unchanged; only Popen gets a child-PID observer.
        with tempfile.TemporaryDirectory()as t:
            root=Path(t);repo=root/'repo';subprocess.run(['/usr/bin/git','init','--bare','-q',str(repo)],check=True)
            oid='ab'+'1'*38;(repo/'objects'/'ab').mkdir();os.mkfifo(repo/'objects'/'ab'/('1'*38));pidfile=root/'pid'
            worker=(ROOT/'scripts/worker_process.py').read_text()
            program="""import sys,os,signal,json,subprocess,types
class Cancelled(BaseException):pass
def cancel(*args):raise Cancelled()
signal.signal(signal.SIGTERM,cancel)
sys.stdin.buffer.read()
ns={};exec(compile(WORKER,'<exact-captured-worker>','exec'),ns)
real=subprocess.Popen
def observe(*a,**kw):
 p=real(*a,**kw)
 with open(PIDFILE,'w')as f:f.write(str(p.pid))
 return p
proxy=types.SimpleNamespace(**{k:getattr(subprocess,k)for k in dir(subprocess)})
proxy.Popen=observe;ns['subprocess']=proxy
cancelled=False;clean=False
try:ns['run_worker'](ARGV,input=b'',timeout=20,output_limit=1024)
except Cancelled:cancelled=True
finally:
 try:os.waitpid(-1,os.WNOHANG)
 except ChildProcessError:clean=True
print(json.dumps({'cleanup_complete':clean,'cancelled':cancelled,'result':None}),flush=True)
""".replace('WORKER',repr(worker)).replace('PIDFILE',repr(str(pidfile))).replace('ARGV',repr(['/usr/bin/git','--git-dir',str(repo),'cat-file','-p',oid]))
            clock=v.Clock();clock.work=clock.start+.4;clock.end=clock.start+5.4
            with self.assertRaises(v.Refused)as e:
                with v.original_clock(clock):v._run_baseline(program,b'{}',clock)
            self.assertTrue(e.exception.cleanup_complete,'TERM/leader-exit alone cannot pass');self.assertTrue(pidfile.exists())
            with self.assertRaises(ProcessLookupError):os.kill(int(pidfile.read_text()),0)
            self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.,0.))
    def test_baseline_setup_failure_does_not_leak_fds(self):
        before=v.fd_room()
        with mock.patch.object(v.subprocess,'Popen',side_effect=OSError('spawn')):
            with self.assertRaises(OSError):v._run_baseline('',b'{}',v.Clock())
        self.assertEqual(v.fd_room(),before)
    def test_no_ack_on_early_exit_or_output_overflow(self):
        for body in ["import sys;sys.stdin.buffer.read()","import sys;sys.stdin.buffer.read();print('x'*4097)"]:
            with self.assertRaises((v.Refused,ValueError)):v._run_baseline(body,b'{}',v.Clock())
    def test_exact_tokenizer_record_and_all95_source_anchors(self):
        d=self.data();row=d['copied_files'][0]
        # Read only exact small retained source data, not a native/archive replay.
        raw=subprocess.check_output(['/usr/bin/git','show','976864835b8a57633a1bd1a7c74186ea022e10d5:'+row['path']])
        observed={n:(a['mode'],a['git_blob_oid'],a['bytes'])for n,a in row['anchors'].items()};bodies={r[1]:(ROOT/n).read_bytes()for n,r in observed.items()};charge=[]
        v.mixed_tokenizers(raw,row,observed,lambda r:bodies[r[1]],v.Clock(),charge.append)
        self.assertEqual(sum(charge),300341);self.assertEqual(len(charge),93)
    def test_mixed_terms_missing_anchor_or_coherent_body_edit_refuse(self):
        row=self.data()['copied_files'][0];raw=subprocess.check_output(['/usr/bin/git','show','976864835b8a57633a1bd1a7c74186ea022e10d5:'+row['path']]);o={n:(a['mode'],a['git_blob_oid'],a['bytes'])for n,a in row['anchors'].items()};o.pop(next(iter(o)))
        with self.assertRaises(v.Refused):v.mixed_tokenizers(raw,row,o,lambda r:b'',v.Clock(),lambda n:None)
        body=json.loads(raw);body['claims']['license_clearance']=True;bad=v.canonical(body);new=copy.deepcopy(row);new['sha256']=v.sha(bad);new['bytes']=len(bad)
        with self.assertRaises(v.Refused):v.mixed_tokenizers(bad,new,o,lambda r:b'',v.Clock(),lambda n:None)
    def test_policy_duplicate_and_numeric_claims_refuse(self):
        with self.assertRaises(v.Refused):v.parse(b'{"x":1,"x":2}')
        with self.assertRaises(v.Refused):v.parse(b'{"x":1.0}')
        d=self.data();d['claims']['accuracy']=0;raw=v.canonical(d)
        with mock.patch.object(v,'POLICY_SHA256',v.sha(raw)):
            with self.assertRaises(v.Refused):v.policy(raw)
    def test_archive_invalid_preflight_before_classifier(self):
        with mock.patch.object(v,'_verify',side_effect=AssertionError('must not classify')):
            self.assertFalse(v.verify_archive(b'',source_commit=v.Q)['pass'])
            self.assertFalse(v.verify_archive(b'x',source_commit='not-an-oid')['pass'])

    def test_actual_fd_exhaustion_refuses_before_spawn_all_owned_closed(self):
        before=v.fd_room();owned=[]
        try:
            for invalid in [True,-1,1.0]:
                with self.assertRaises(v.Refused):v.fd_room(invalid)
            while v.fd_room()<32:owned.append(os.open(os.devnull,os.O_RDONLY))
            self.assertEqual(v.spawn_room(),32)
            owned.append(os.open(os.devnull,os.O_RDONLY));self.assertEqual(v.fd_room(),33)
            with mock.patch.object(v.subprocess,'Popen',side_effect=AssertionError('must refuse before spawn')):
                with self.assertRaises(v.Refused)as e:v._run_baseline('',b'{}',v.Clock())
                self.assertEqual(e.exception.code,'resource_limit')
        finally:
            for fd in owned:os.close(fd)
        self.assertEqual(v.fd_room(),before)
    def test_actual_close_boundary_depleted_clock_never_returns_bytes(self):
        with tempfile.TemporaryDirectory()as t:
            p=Path(t).resolve()/'x';p.write_bytes(b'one');clock=v.Clock();real=os.close;closed=[]
            def close(fd):
                real(fd);closed.append(fd);clock.work=clock.start-1
            with mock.patch.object(v.os,'close',side_effect=close):
                with self.assertRaises(v.Refused)as e:v.capture(p,3,clock)
            self.assertEqual(e.exception.code,'deadline');self.assertEqual(len(closed),1)
            with self.assertRaises(OSError):os.fstat(closed[0])
    def test_public_clock_failure_and_bad_commit_are_typed_without_baseline(self):
        with mock.patch.object(v.time,'monotonic',return_value=float('nan')):
            self.assertFalse(v.verify()['pass']);self.assertFalse(v.verify_archive(b'x',source_commit=v.Q)['pass'])
        with mock.patch.object(v,'_run_baseline',side_effect=AssertionError('must refuse before baseline')):
            self.assertEqual(v.verify(source_commit='bad')['reason'],'unsupported_source_commit')

    def test_joined_binder_fd_admission_before_capture(self):
        before=v.fd_room();owned=[];source=(ROOT/'tools/source_snapshot_binding.py').read_bytes()
        try:
            while v.fd_room()<32:owned.append(os.open(os.devnull,os.O_RDONLY))
            with mock.patch.object(v,'original_clock',side_effect=AssertionError('admitted32')):
                with self.assertRaisesRegex(AssertionError,'admitted32'):v._binding_call(source,b'x',v.Q,v.Clock(95))
            owned.append(os.open(os.devnull,os.O_RDONLY));self.assertEqual(v.fd_room(),33)
            with mock.patch.object(v,'original_clock',side_effect=AssertionError('must refuse before binder setup')):
                with self.assertRaises(v.Refused)as e:v._binding_call(source,b'x',v.Q,v.Clock(95))
                self.assertEqual(e.exception.code,'resource_limit')
        finally:
            for fd in owned:os.close(fd)
        self.assertEqual(v.fd_room(),before)
    def test_binder_boundary_uses_original_clock_and_final_sample(self):
        # No real archive/Git binding. Fixed source is parsed; only its capture
        # callable is substituted by the test exec boundary to isolate timing.
        source=(ROOT/'tools/source_snapshot_binding.py').read_bytes();real_exec=__builtins__['exec'] if isinstance(__builtins__,dict)else __builtins__.exec
        clock=v.Clock(95);observed=[]
        def execute(code,namespace):
            real_exec(code,namespace)
            def capture(*args,**kwargs):
                observed.append((args[2],kwargs['new_session']));clock.work=clock.start-1;return b'{}'
            namespace['_capture']=capture
        with mock.patch('builtins.exec',side_effect=execute):
            with self.assertRaises(v.Refused):v._binding_call(source,b'x',v.Q,clock)
        self.assertEqual(len(observed),1);self.assertLessEqual(observed[0][0],clock.start+60.1);self.assertTrue(observed[0][1]);self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.,0.))

if __name__=='__main__':unittest.main()
