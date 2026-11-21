"""Local authority, independent tenant jobs and private output boundaries."""
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import organization_policy_registry as m
from tools import organization_policy_io as io


class RegistryFixture(unittest.TestCase):
    def setUp(self):
        self.base=Path(tempfile.mkdtemp(prefix='aitrust-policy-controls-')).resolve();self.base.chmod(0o700)
        self.root=self.base/'registry';self.admin=self.base/'authority.json'
        m.keygen(self.admin);m.initialize(self.root,self.admin,True)

    def tearDown(self):shutil.rmtree(self.base)

    def private(self,name,value):
        p=self.base/name;p.write_bytes(value if isinstance(value,bytes) else json.dumps(value).encode());p.chmod(0o600);return p

    def policy(self,name,job='review',revision=1,code='REVIEW',term='confidential draft'):
        return self.private(name+'-'+job+'-'+str(revision)+'.json',{'format':m.private_policy.POLICY,'namespace':name,'policy_id':job,'revision':revision,
            'claim':'literal_term_occurrence_only','limits_visible':True,'receipts_optional':True,'personal_checks_separate':True,
            'rules':[{'code':code,'terms':[term]}]})

    def tenant(self,name='example-team',roles=None):
        m.enroll(self.root,name,'team',self.admin);cap=self.base/(name+'.cap')
        m.grant(self.root,name,self.admin,roles or sorted(m.ROLES),3600,cap)
        m.add_policy(self.root,name,cap,self.policy(name))
        text=self.private(name+'.txt',b'PRIVATE_SUBJECT_CANARY Cafe\xcc\x81: confidential draft.')
        selection=self.base/(name+'.selection');m.prepare(self.root,name,cap,'review',1,text,selection)
        return cap,text,selection

    def assert_refused(self,call):
        with self.assertRaises(io.PrivateInputError) as caught:call()
        self.assertNotIn('PRIVATE_',str(caught.exception));self.assertNotIn(str(self.base),str(caught.exception))


class GovernedJobs(RegistryFixture):
    def test_two_independent_tenants_and_exact_canonical_private_export(self):
        a,text,selection=self.tenant();b,other,second=self.tenant('another-team')
        output=self.base/'details.json';result=m.check(self.root,'example-team',a,selection,text,True,output)
        self.assertEqual(result['literal_occurrences'],1);self.assertFalse(result['public_tag_asserted'])
        record=json.loads(output.read_text());self.assertEqual(record['subject_raw_sha256'],hashlib.sha256(text.read_bytes()).hexdigest())
        self.assertNotEqual(record['subject_raw_sha256'],record['subject_nfc_sha256'])
        self.assertNotIn('PRIVATE_SUBJECT_CANARY',output.read_text());self.assertEqual(output.stat().st_mode&0o777,0o600)
        self.assertNotIn(b'PRIVATE_SUBJECT_CANARY',(self.root/'tenants/example-team/state.sqlite').read_bytes())
        self.assertTrue(record['local_qualified_namespace'].endswith(':example-team'))
        self.assertFalse(record['organization_identity_verified']);self.assertFalse(record['employee_consent_proved'])
        self.assertEqual(m.check(self.root,'another-team',b,second,other,True)['literal_occurrences'],1)
        clean=self.private('no-match.txt',b'Nothing selected here.');s=self.base/'clean.selection'
        m.prepare(self.root,'another-team',b,'review',1,clean,s)
        self.assertEqual(m.check(self.root,'another-team',b,s,clean,True)['literal_occurrences'],0)

    def test_each_job_has_its_own_revision_source_and_failure_boundary(self):
        cap,text,unused=self.tenant()
        m.add_policy(self.root,'example-team',cap,self.policy('example-team',job='release',code='RELEASE',term='release candidate'))
        a=self.base/'job-a.selection';b=self.base/'job-b.selection'
        m.prepare(self.root,'example-team',cap,'review',1,text,a)
        m.prepare(self.root,'example-team',cap,'release',1,text,b)
        self.assertEqual(m.check(self.root,'example-team',cap,a,text,True)['literal_occurrences'],1)
        self.assertEqual(m.check(self.root,'example-team',cap,b,text,True)['literal_occurrences'],0)
        with sqlite3.connect(self.root/'tenants/example-team/state.sqlite') as db:
            db.execute('UPDATE policies SET raw=? WHERE job=?',(b'PRIVATE_MALFORMED_POLICY','review'))
        self.assert_refused(lambda:m.check(self.root,'example-team',cap,a,text,True))
        self.assertEqual(m.check(self.root,'example-team',cap,b,text,True)['literal_occurrences'],0)

    def test_cross_tenant_forgery_roles_and_separate_export_permission(self):
        a,text,selection=self.tenant();b,other,second=self.tenant('another-team')
        self.assert_refused(lambda:m.check(self.root,'another-team',a,second,other,True))
        forged=json.loads(a.read_text());forged['tenant_id']=json.loads(b.read_text())['tenant_id']
        forged=self.private('forged.cap',forged)
        self.assert_refused(lambda:m.check(self.root,'another-team',forged,second,other,True))
        viewer=self.base/'view.cap';m.grant(self.root,'example-team',self.admin,['view'],3600,viewer)
        self.assert_refused(lambda:m.prepare(self.root,'example-team',viewer,'review',1,text,self.base/'denied.selection'))
        self.assertEqual(m.inspect_tenant(self.root,'example-team',viewer)['jobs'],1)
        checker=self.base/'check.cap';m.grant(self.root,'example-team',self.admin,['check'],3600,checker)
        s=self.base/'checker.selection';m.prepare(self.root,'example-team',checker,'review',1,text,s)
        self.assertEqual(m.check(self.root,'example-team',checker,s,text,True)['literal_occurrences'],1)
        self.assert_refused(lambda:m.check(self.root,'example-team',checker,s,text,True,self.base/'denied.json'))
        self.assertFalse((self.base/'denied.json').exists())
        self.assert_refused(lambda:m.add_policy(self.root,'example-team',checker,self.policy('example-team',revision=2)))

    def test_revoke_recover_and_expiry_are_current_without_reviving_old_selection(self):
        cap,text,selection=self.tenant();m.revoke(self.root,'example-team',self.admin,cap)
        self.assert_refused(lambda:m.check(self.root,'example-team',cap,selection,text,True))
        fresh=self.base/'replacement.cap';m.grant(self.root,'example-team',self.admin,['check','export'],3600,fresh)
        self.assert_refused(lambda:m.check(self.root,'example-team',fresh,selection,text,True))
        s=self.base/'replacement.selection';m.prepare(self.root,'example-team',fresh,'review',1,text,s)
        self.assertEqual(m.check(self.root,'example-team',fresh,s,text,True)['literal_occurrences'],1)
        with mock.patch.object(m.time,'time',return_value=time.time()+7200):
            self.assert_refused(lambda:m.check(self.root,'example-team',fresh,s,text,True))

    def test_raw_equivalent_edit_policy_revision_and_job_pause_invalidate_exact_selection(self):
        cap,text,selection=self.tenant();text.write_text('PRIVATE_SUBJECT_CANARY Café: confidential draft.')
        self.assert_refused(lambda:m.check(self.root,'example-team',cap,selection,text,True))
        second=self.policy('example-team',revision=2);m.add_policy(self.root,'example-team',cap,second)
        self.assert_refused(lambda:m.prepare(self.root,'example-team',cap,'review',1,text,self.base/'old.selection'))
        s=self.base/'v2.selection';m.prepare(self.root,'example-team',cap,'review',2,text,s)
        m.enable_job(self.root,'example-team',cap,'review',False)
        self.assert_refused(lambda:m.check(self.root,'example-team',cap,s,text,True))
        m.enable_job(self.root,'example-team',cap,'review',True)
        self.assert_refused(lambda:m.check(self.root,'example-team',cap,s,text,True))
        fresh=self.base/'resumed.selection';m.prepare(self.root,'example-team',cap,'review',2,text,fresh)
        self.assertEqual(m.check(self.root,'example-team',cap,fresh,text,True)['literal_occurrences'],1)

    def test_public_codes_namespace_and_authority_cannot_be_adopted_by_caller_fields(self):
        for name in ['public','personal','aitrust-id','../escape']:
            self.assert_refused(lambda:m.enroll(self.root,name,'team',self.admin))
        cap,text,selection=self.tenant()
        self.assert_refused(lambda:m.add_policy(self.root,'example-team',cap,self.policy('example-team',revision=2,code='PS')))
        other=self.base/'other-authority';m.keygen(other)
        self.assert_refused(lambda:m.enroll(self.root,'new-team','enterprise',other))
        self.assert_refused(lambda:m.check(self.root,'example-team',cap,selection,text,False))

    def test_malformed_tenant_database_and_worker_failure_leave_other_tenant_available(self):
        cap,text,selection=self.tenant();other,subject,s=self.tenant('another-team')
        with sqlite3.connect(self.root/'tenants/example-team/state.sqlite') as db:db.execute('UPDATE control SET epoch=0')
        self.assert_refused(lambda:m.check(self.root,'example-team',cap,selection,text,True))
        with mock.patch.object(m,'run_worker',return_value=subprocess.CompletedProcess([],2,b'PRIVATE_CHILD_CANARY')):
            self.assert_refused(lambda:m.check(self.root,'another-team',other,s,subject,True))
        self.assertEqual(m.check(self.root,'another-team',other,s,subject,True)['literal_occurrences'],1)

    def test_worker_typed_forgery_and_incomplete_canonical_record_refuse(self):
        cap,text,selection=self.tenant();selected=json.loads(selection.read_text());raw=self.policy('example-team').read_bytes()
        context={'format':m.private_policy.CONTEXT,'namespace':'example-team','policy_sha256':m.sha(raw),'subject_sha256':selected['subject_nfc_sha256']}
        canonical=m.private_policy.observe(text.read_text(),raw,context,reviewed=True)
        for kind in ['bool_count','omitted','extra','span']:
            value=json.loads(json.dumps(canonical))
            if kind=='bool_count':value['total_observations']=True
            if kind=='omitted':value['observations']=[];value['total_observations']=0
            if kind=='extra':value['PRIVATE_EXTRA']='PRIVATE_SECRET'
            if kind=='span':value['observations'][0]['span']=[0,1]
            with mock.patch.object(m,'run_worker',return_value=subprocess.CompletedProcess([],0,json.dumps(value).encode())):
                self.assert_refused(lambda:m.check(self.root,'example-team',cap,selection,text,True,self.base/'forged.json'))
            self.assertFalse((self.base/'forged.json').exists())

    def test_per_tenant_lock_blocks_affected_mutation_but_not_other_tenant(self):
        cap,text,selection=self.tenant();other,subject,s=self.tenant('another-team')
        with m.registry(self.root) as r:
            with r.tenant('example-team'):
                self.assert_refused(lambda:m.enable_job(self.root,'example-team',cap,'review',False))
                self.assertEqual(m.check(self.root,'another-team',other,s,subject,True)['literal_occurrences'],1)

    def test_tenant_retire_restore_and_explicit_removal_preserve_unrelated_tenant(self):
        cap,text,selection=self.tenant();other,subject,s=self.tenant('another-team')
        m.enable_tenant(self.root,'example-team',self.admin,False)
        self.assert_refused(lambda:m.check(self.root,'example-team',cap,selection,text,True))
        m.enable_tenant(self.root,'example-team',self.admin,True)
        self.assert_refused(lambda:m.check(self.root,'example-team',cap,selection,text,True))
        m.remove_tenant(self.root,'example-team',self.admin)
        self.assertEqual(m.check(self.root,'another-team',other,s,subject,True)['literal_occurrences'],1)
        self.assert_refused(lambda:m.remove_registry(self.root,self.admin))
        m.remove_tenant(self.root,'another-team',self.admin);m.remove_registry(self.root,self.admin)
        self.assertFalse(self.root.exists());self.assertTrue(self.admin.exists())

    def test_expiry_during_worker_withholds_result_and_export(self):
        cap,text,selection=self.tenant();real=m.run_worker;clock=time.time()
        with mock.patch.object(m.time,'time',return_value=clock) as current:
            def expires(*args,**kwargs):
                result=real(*args,**kwargs);current.return_value=clock+7200;return result
            with mock.patch.object(m,'run_worker',side_effect=expires):
                self.assert_refused(lambda:m.check(self.root,'example-team',cap,selection,text,True,self.base/'expired.json'))
        self.assertFalse((self.base/'expired.json').exists())

    def test_per_tenant_capacity_is_explicit_and_another_tenant_can_enroll(self):
        cap,text,selection=self.tenant()
        with mock.patch.object(m,'MAX_GRANTS',1):
            self.assert_refused(lambda:m.grant(self.root,'example-team',self.admin,['check'],30,self.base/'over.cap'))
            self.assertFalse((self.base/'over.cap').exists())
            other,subject,s=self.tenant('another-team')
            self.assertEqual(m.check(self.root,'another-team',other,s,subject,True)['literal_occurrences'],1)


class PrivateBoundaries(RegistryFixture):
    def test_regular_private_single_link_and_no_overwrite_boundaries(self):
        cap,text,selection=self.tenant();link=self.base/'linked.txt';link.symlink_to(text)
        self.assert_refused(lambda:m.check(self.root,'example-team',cap,selection,link,True))
        os.link(text,self.base/'hardlink.txt');self.assert_refused(lambda:m.check(self.root,'example-team',cap,selection,text,True));(self.base/'hardlink.txt').unlink()
        fifo=self.base/'fifo';os.mkfifo(fifo,0o600);self.assert_refused(lambda:m.prepare(self.root,'example-team',cap,'review',1,fifo,self.base/'no.selection'))
        output=self.private('exists.json',b'KEEP');self.assert_refused(lambda:m.check(self.root,'example-team',cap,selection,text,True,output));self.assertEqual(output.read_bytes(),b'KEEP')
        text.chmod(0o644);self.assert_refused(lambda:m.check(self.root,'example-team',cap,selection,text,True))
        text.chmod(0o600)
        for invalid in (b'x'*20001,b'zero\0byte'):
            text.write_bytes(invalid)
            self.assert_refused(lambda:m.prepare(self.root,'example-team',cap,'review',1,text,self.base/'oversize.selection'))
            self.assertFalse((self.base/'oversize.selection').exists())

    def test_cached_directory_handle_never_accepts_replaced_parent(self):
        folder=self.base/'nested';folder.mkdir(mode=0o700)
        source=folder/'selected';source.write_bytes(b'owned');source.chmod(0o600)
        with io.Capture() as c:
            self.assertEqual(c.read(source,100),b'owned')
            folder.rename(self.base/'old-nested');folder.mkdir(mode=0o700)
            source.write_bytes(b'PRIVATE_REPLACEMENT_CANARY');source.chmod(0o600)
            with self.assertRaises(io.PrivateInputError):c.read(source,100)

    def test_input_drift_after_worker_is_refused_before_final_output(self):
        cap,text,selection=self.tenant();real=m.run_worker
        def drift(*args,**kwargs):
            value=real(*args,**kwargs);text.write_bytes(text.read_bytes());return value
        with mock.patch.object(m,'run_worker',side_effect=drift):
            self.assert_refused(lambda:m.check(self.root,'example-team',cap,selection,text,True,self.base/'drift.json'))
        self.assertFalse((self.base/'drift.json').exists())

    def test_fdopen_failure_closes_owned_raw_handle_and_publishes_no_final(self):
        handles=[];real_open=os.open
        def opened(path,*args,**kwargs):
            fd=real_open(path,*args,**kwargs)
            if str(path).startswith('.org-policy-'):handles.append(fd)
            return fd
        output=self.base/'failed-authority'
        with mock.patch.object(io.os,'open',side_effect=opened),mock.patch.object(io.os,'fdopen',side_effect=OSError('PRIVATE_FD_CANARY')):
            self.assert_refused(lambda:m.keygen(output))
        self.assertFalse(output.exists());self.assertEqual(len(handles),1)
        with self.assertRaises(OSError) as caught:os.fstat(handles[0])
        self.assertEqual(caught.exception.errno,errno.EBADF)

    def test_post_link_temporary_cleanup_failure_reports_explicit_uncertainty(self):
        real=os.unlink;output=self.base/'uncertain-authority'
        def unlink(path,*args,**kwargs):
            if str(path).startswith('.org-policy-'):raise OSError('PRIVATE_UNLINK_CANARY')
            return real(path,*args,**kwargs)
        with mock.patch.object(io.os,'unlink',side_effect=unlink):
            with self.assertRaises(io.OutputCommitUncertain):m.keygen(output)
        self.assertTrue(output.is_file());self.assertEqual(output.stat().st_mode&0o777,0o600)
        self.assertEqual(json.loads(output.read_text())['format'],m.AUTHORITY)

    def test_grant_output_exists_refuses_before_access_state_changes(self):
        cap,text,selection=self.tenant();out=self.private('existing.cap',b'KEEP')
        self.assert_refused(lambda:m.grant(self.root,'example-team',self.admin,['check'],100,out))
        self.assertEqual(m.check(self.root,'example-team',cap,selection,text,True)['literal_occurrences'],1)

    def test_close_failure_after_publication_attempts_all_handles_and_is_uncertain(self):
        real=os.close;handles=[]
        def close(fd):
            handles.append(fd);real(fd)
            if len(handles)==1:raise OSError('PRIVATE_CLOSE_CANARY')
        output=self.base/'close-uncertain'
        with mock.patch.object(io.os,'close',side_effect=close):
            with self.assertRaises(io.OutputCommitUncertain):m.keygen(output)
        self.assertGreater(len(handles),1);self.assertTrue(output.exists())
        for fd in handles:
            with self.assertRaises(OSError):os.fstat(fd)


if __name__=='__main__':unittest.main()
