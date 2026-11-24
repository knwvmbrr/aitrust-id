"""V4 finite-source controls; only the named actual source test executes full Q."""
import copy
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import types
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import source_release_policy_v4 as p


def oid(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
def row(raw):return ('100644',oid(raw),len(raw))


class V4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v3,_=p.captured_v3();cls.v2,_=cls.v3.pinned_v2()
        cls.old=cls.v2.file_bytes(ROOT/cls.v2.POLICY,12_000_000);cls.legacy=cls.v2.file_bytes(ROOT/cls.v2.LEGACY,12_000_000)
        cls.d2,cls.l,cls.base=cls.v2.policy(cls.old,cls.legacy)
        cls.add,cls.oldcopies,cls.oldproject=cls.v3.overlay((ROOT/cls.v3.POLICY).read_bytes(),cls.base,cls.v2)
        raw=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'ls-tree','-rlz','--full-tree',p.Q]);cls.qrows,_=cls.v2.tree_rows(raw)
        cls.owned={n for n,r in cls.base.items()if r[3]=='project-text'}|cls.oldproject|set(cls.d2['named_first_party_extensions'])
        cls.raw=(ROOT/p.POLICY).read_bytes();cls.d,cls.project,cls.copied=p.policy(cls.raw,cls.v3,cls.v2,cls.base,cls.add['project_files'],cls.qrows,cls.owned)

    def fixture(self):
        license=(ROOT/'LICENSE').read_bytes();old=b'# SPDX-License-Identifier: Apache-2.0\nvalue=1\n';producer=b'old producer\n';vendor=b'authored synthetic fixture bytes\n'
        bodies={oid(x):x for x in(license,old,producer,vendor)}
        q={'LICENSE':row(license),'maintained.py':row(old),'tools/dependency_policy.py':row(producer),'fixed.bin':row(b'unchanged')}
        c={'new/vendor.c':{'path':'new/vendor.c','mode':'100644','git_blob_oid':oid(vendor),'bytes':len(vendor),'sha256':p.sha(vendor),'grant_group':'fixture','container':None}}
        d={'origins':{'fixture':{'unresolved':[],'required_cohort':['new/vendor.c'],'required_anchors':[{'path':'LICENSE','bytes':len(license),'sha256':p.sha(license)}]}}}
        def read(o,size):self.assertEqual(len(bodies[o]),size);return bodies[o]
        return d,{'new/owned.py','maintained.py','tools/dependency_policy.py'},c,q,bodies,read

    def check(self,f,observed,read=None):
        d,project,copied,q,bodies,reader=f
        return p.classify(d,project,copied,q,observed,[],{'maintained.py','tools/dependency_policy.py'},self.v2,read or reader,lambda:None)

    def test_actual_365_source_with_independent_Q_and_false_claims(self):
        result=p.verify(source_commit='365b5f2ac71158c39f1070533d1400f37a8b6efd')
        self.assertTrue(result['pass'],result);self.assertTrue(result['baseline_v3_verified'])
        self.assertEqual((result['files'],result['source_bytes']),(13829,149315264))
        self.assertEqual(result['present_optional_copied_files'],25);self.assertFalse(result['selected_source_protected_release_claimed'])
        for name in p.FALSE_CLAIMS:self.assertIs(result[name],False)

    def test_155_baseline_names_and_closed_source_read_reservation(self):
        self.assertEqual(self.d['legacy_v3_names'],self.add['project_files']);self.assertEqual(len(self.d['legacy_v3_names']),155)
        reads=p.baseline_reads(self.qrows,self.d2,self.l,self.base,self.add,self.oldcopies,self.oldproject)
        self.assertEqual((len(reads),sum(n+1 for n in reads.values())),(273,8774869))
        self.assertEqual(p.sha(p.canonical(reads)),self.d['baseline_read_reservation']['readset_sha256'])
        self.assertLessEqual(len(self.project)+sum(x['authored_capacity_charge']for x in self.copied.values()),160)

    def test_unknown_before_filter_or_body(self):
        f=self.fixture();observed={**f[3],'unknown/file':row(b'x')}
        with self.assertRaises(p.Refused)as error:self.check(f,observed,lambda *a:self.fail('unknown decoded'))
        self.assertEqual(error.exception.code,'unknown_path')

    def test_missing_Q_and_changed_nonproject_refuse(self):
        f=self.fixture();observed=dict(f[3]);del observed['fixed.bin']
        with self.assertRaises(p.Refused)as error:self.check(f,observed)
        self.assertEqual(error.exception.code,'missing_path')
        observed={**f[3],'fixed.bin':row(b'changed')}
        with self.assertRaises(p.Refused):self.check(f,observed)

    def test_named_maintenance_preserves_real_markers(self):
        f=self.fixture();raw=b'# SPDX-License-Identifier: Apache-2.0\nvalue=2\n';f[4][oid(raw)]=raw
        result=self.check(f,{**f[3],'maintained.py':row(raw)});self.assertEqual(result['changed_named_project_text_files'],1)
        raw=b'# Copyright unreviewed third party\n';f[4][oid(raw)]=raw
        with self.assertRaises(p.Refused)as error:self.check(f,{**f[3],'maintained.py':row(raw)})
        self.assertEqual(error.exception.code,'license_declaration_changed')

    def test_new_project_foreign_or_binary_refuses(self):
        for raw in (b'# Copyright unreviewed publisher\n',b'a\0b',b'\xff'):
            f=self.fixture();f[4][oid(raw)]=raw
            with self.assertRaises((p.Refused,ValueError)):self.check(f,{**f[3],'new/owned.py':row(raw)})
        f=self.fixture();raw=b'# SPDX-License-Identifier: Apache-2.0\n';f[4][oid(raw)]=raw
        self.assertEqual(self.check(f,{**f[3],'new/owned.py':row(raw)})['introduced_named_project_text_files'],1)

    def test_source_copy_present_requires_exact_actual_grant(self):
        f=self.fixture();r=f[2]['new/vendor.c'];observed={**f[3],'new/vendor.c':(r['mode'],r['git_blob_oid'],r['bytes'])}
        self.assertEqual(self.check(f,observed)['present_optional_copied_files'],1)
        f[0]['origins']['fixture']['required_anchors'][0]['sha256']='0'*64
        with self.assertRaises(p.Refused)as error:self.check(f,observed)
        self.assertEqual(error.exception.code,'grant_changed')

    def test_changed_copy_missing_cohort_and_unresolved_refuse(self):
        for kind in ('changed','cohort','unresolved'):
            f=self.fixture();r=f[2]['new/vendor.c'];observed={**f[3],'new/vendor.c':(r['mode'],r['git_blob_oid'],r['bytes'])}
            if kind=='changed':observed['new/vendor.c']=('100644','0'*40,r['bytes'])
            elif kind=='cohort':f[0]['origins']['fixture']['required_cohort'].append('missing/source.h')
            else:f[0]['origins']['fixture']['unresolved']=['Missing real source grant']
            with self.subTest(kind=kind),self.assertRaises(p.Refused):self.check(f,observed)

    def test_stale_metadata_requires_exact_old_producer(self):
        f=self.fixture();observed={**f[3],'tools/dependency_policy.py':row(b'changed producer')}
        with self.assertRaises(p.Refused)as error:self.check(f,observed,lambda *a:self.fail('stale producer decoded'))
        self.assertEqual(error.exception.code,'source_changed')

    def test_typed_counts_modes_and_aggregate_limits(self):
        for bad in [('100644','0'*40,True),('120000','0'*40,0),('100644','0'*40,32_000_001)]:
            f=self.fixture()
            with self.assertRaises(p.Refused):self.check(f,{**f[3],'new/owned.py':bad})
        f=self.fixture()
        with patch.object(p,'MAX_TOTAL',1),self.assertRaises(p.Refused):self.check(f,f[3])
        with patch.object(p,'MAX_FILES',1),self.assertRaises(p.Refused):self.check(f,f[3])

    def test_table_digest_coherent_foundation_change_and_161_refuse(self):
        bad=copy.deepcopy(self.d);bad['origins'][next(iter(bad['origins']))]['scope']='invented'
        with self.assertRaises(p.Refused):p.policy(json.dumps(bad).encode(),self.v3,self.v2,self.base,self.add['project_files'],self.qrows,self.owned)
        for mutate in (lambda d:d['project_files'].extend('future/'+str(n)+'.py'for n in range(161)),
                       lambda d:d['foundations']['tools/source_snapshot_binding.py'].update(sha256='0'*64),
                       lambda d:d['claims'].update(legal_clearance=0),
                       lambda d:d['baseline_read_reservation'].update(bytes=True),
                       lambda d:d['source_observation'].update(candidate_is_protected=0)):
            bad=copy.deepcopy(self.d);mutate(bad);raw=json.dumps(bad).encode()
            with patch.object(p,'POLICY_SHA256',p.sha(raw)),self.assertRaises((p.Refused,ValueError,TypeError)):
                p.policy(raw,self.v3,self.v2,self.base,self.add['project_files'],self.qrows,self.owned)

    def test_one_body_budget_and_same_verified_oid_cache(self):
        raw=b'body';calls=[]
        def git(args,limit):calls.append(args);return raw
        budget=p.Bodies(git,lambda:None,p.MAX_INSPECTED-5)
        self.assertEqual(budget.read(oid(raw),4),raw);self.assertEqual(budget.read(oid(raw),4),raw);self.assertEqual(len(calls),1)
        with self.assertRaises(p.Refused):budget.read('1'*40,1)
        with self.assertRaises(p.Refused):budget.read('1'*40,p.MAX_BODY+1)
        self.assertEqual(len(calls),1)

    def test_cached_poisoned_v3_never_used_or_mutated(self):
        fake=types.ModuleType('tools.source_release_policy_v3');fake.verify=lambda **k:self.fail('poison imported')
        with patch.dict(sys.modules,{'tools.source_release_policy_v3':fake}):
            a,raw=p.captured_v3();b,_=p.captured_v3();self.assertIsNot(a.verify.__globals__,b.verify.__globals__)
            self.assertEqual(p.sha(raw),p.V3_METHOD);self.assertEqual(a.POLICY_SHA256,p.V3_POLICY)

    def test_original_alarm_reaps_real_owned_child_and_restores(self):
        children=[];original=subprocess.Popen
        def popen(*a,**k):child=original(*a,**k);children.append(child);return child
        old=signal.getsignal(signal.SIGALRM)
        with patch.object(subprocess,'Popen',side_effect=popen),self.assertRaises(p.Refused):
            with p.original_clock(time.monotonic()+.05):self.v2.worker()([sys.executable,'-I','-S','-B','-c','import time;time.sleep(5)'],input=b'',timeout=5,output_limit=100)
        self.assertEqual(len(children),1);self.assertIsNotNone(children[0].returncode)
        self.assertTrue(children[0].stdin.closed and children[0].stdout.closed)
        with self.assertRaises(ChildProcessError):os.waitpid(children[0].pid,os.WNOHANG)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.,0.));self.assertIs(signal.getsignal(signal.SIGALRM),old)

    def test_clock_setup_and_teardown_faults_restore_handler(self):
        original=signal.setitimer;old=signal.getsignal(signal.SIGALRM)
        for phase in ('setup-before','setup-after','teardown-after'):
            calls=[]
            def timer(which,value):
                calls.append(value)
                if phase=='setup-before'and len(calls)==1:raise OSError('fixed setup refusal')
                result=original(which,value)
                if phase=='setup-after'and len(calls)==1:raise OSError('fixed post-setup refusal')
                if phase=='teardown-after'and value==0:raise OSError('fixed post-cancel refusal')
                return result
            try:
                with self.subTest(phase=phase),patch.object(signal,'setitimer',side_effect=timer),self.assertRaises(OSError):
                    with p.original_clock(time.monotonic()+1):pass
                self.assertIs(signal.getsignal(signal.SIGALRM),old);self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.,0.))
                self.assertIn(0,calls)
            finally:original(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)

    def test_fixed_foundation_fifo_refuses_without_blocking(self):
        with tempfile.TemporaryDirectory()as d:
            root=Path(d).resolve();(root/'tools').mkdir();os.mkfifo(root/'tools/source_release_policy_v3.py')
            started=time.monotonic()
            with patch.object(p,'ROOT',root),self.assertRaises(p.Refused):p.captured_v3()
            self.assertLess(time.monotonic()-started,1)

    def archive_fixture(self):
        from scripts import source_snapshot_v3 as snapshot
        temp=tempfile.TemporaryDirectory(prefix='v4-source-binding-');self.addCleanup(temp.cleanup);root=Path(temp.name).resolve()
        def git(*a):return subprocess.check_output(['/usr/bin/git','-C',str(root),*a],stderr=subprocess.DEVNULL)
        git('init','-q');git('config','user.name','Private synthetic fixture');git('config','user.email','fixture@invalid')
        (root/'a.txt').write_bytes(b'actual-source\n');git('add','a.txt');git('commit','-qm','Bounded source fixture')
        commit=git('rev-parse','HEAD').decode().strip();tree=git('rev-parse','HEAD^{tree}').decode().strip();raw=snapshot.build(root,commit)
        for name in (*p.FOUNDATION_PATHS,p.POLICY,'scripts/source_snapshot.py','scripts/source_snapshot_v2.py','scripts/source_snapshot_v3.py'):
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
        return root,commit,tree,raw,snapshot

    def test_rights_refuse_before_archive_interpretation(self):
        with patch.object(p,'verify',return_value={'pass':False,'reason':'unknown_path'}),patch.object(p,'captured_v3',side_effect=AssertionError('binder entered')):
            r=p.verify_archive(b'not a gzip',source_commit=p.Q)
        self.assertFalse(r['pass']);self.assertEqual(r['reason'],'unknown_path')

    def test_real_tiny_archive_canonical_positive_and_self_consistent_forgery(self):
        root,commit,tree,raw,snapshot=self.archive_fixture()
        def invoke(data):
            with patch.object(p,'ROOT',root),patch.object(p,'verify',return_value={'pass':True,'source_tree':tree,'files':1,'source_bytes':14,'method_sha256':p.sha(Path(p.__file__).read_bytes())}):return p.verify_archive(data,source_commit=commit)
        result=invoke(raw);self.assertTrue(result['pass'],result);self.assertTrue(result['trusted_git_bytes_matched'])
        forged=b'forged-source\n';meta={'profile':snapshot.PROFILE,'source_commit':commit,'kind':'development_source_snapshot','tag_release_validated':False,'installed_dependencies_included':False,'files':[{'path':'a.txt','mode':420,'bytes':len(forged),'sha256':p.sha(forged)}]}
        output=io.BytesIO()
        with gzip.GzipFile(fileobj=output,mode='wb',filename='',mtime=0)as gz:
            with tarfile.open(fileobj=gz,mode='w',format=tarfile.USTAR_FORMAT)as tar:
                for name,body in [(snapshot.META,p.canonical(meta)),('a.txt',forged)]:
                    info=tarfile.TarInfo(snapshot.PREFIX+name);info.mode=420;info.size=len(body);tar.addfile(info,io.BytesIO(body))
        data=output.getvalue();snapshot.inspect(data,commit);self.assertFalse(invoke(data)['pass'])

    def test_late_private_foundation_or_own_method_change_refuses(self):
        for victim in ('scripts/worker_process.py','tools/source_release_policy_v4.py'):
            root,commit,tree,raw,_=self.archive_fixture();method=root/'tools/source_release_policy_v4.py';method.write_bytes(Path(p.__file__).read_bytes())
            method_sha=p.sha(method.read_bytes())
            with patch.object(p,'ROOT',root):v3,v3raw=p.captured_v3();v2,v2raw=v3.pinned_v2()
            actual=v2._binding_capture
            def factory(source):
                call=actual(source)
                def run(*a,**k):
                    value=call(*a,**k);path=root/victim;path.write_bytes(path.read_bytes()+b'\n');return value
                return run
            v2._binding_capture=factory;v3.pinned_v2=lambda:(v2,v2raw)
            with self.subTest(victim=victim),patch.object(p,'ROOT',root),patch.object(p,'__file__',str(method)),patch.object(p,'captured_v3',return_value=(v3,v3raw)),patch.object(p,'verify',return_value={'pass':True,'source_tree':tree,'files':1,'source_bytes':14,'method_sha256':method_sha}):
                result=p.verify_archive(raw,source_commit=commit)
            self.assertFalse(result['pass'],result);self.assertFalse(result['trusted_git_bytes_matched'])

    def test_invalid_isolated_cli_fixed_noecho(self):
        result=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'tools/source_release_policy_v4.py'),'--private-canary'],cwd='/',capture_output=True,timeout=5)
        self.assertEqual(result.returncode,2);self.assertEqual(result.stderr,b'');self.assertNotIn(b'private-canary',result.stdout)


if __name__=='__main__':unittest.main()
