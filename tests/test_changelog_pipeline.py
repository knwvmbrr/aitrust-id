"""Exercise actual Git histories and failure paths, not just entry formatting."""
import copy
import datetime as dt
import importlib.util
import json
import os
from unittest.mock import patch
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('changes',Path(__file__).resolve().parents[1]/'scripts/changelog_core.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ChangePipeline(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        for d in ['docs','runs/changes','scripts']: (self.root/d).mkdir(parents=True,exist_ok=True)
        (self.root/'docs/master-scope.json').write_text(json.dumps({'records':[{'id':'F-139'}]}))
        (self.root/'docs/scope-delivery.json').write_text(json.dumps({'packages':[{'id':'WP-RELEASE'}]}))
        (self.root/'CHANGELOG.md').write_text('# Changelog\n\n## Previous history\n\nOld work.\n')
        (self.root/'source.py').write_text('before\n')
        self.git('init','-q');self.git('config','user.email','test@example.invalid');self.git('config','user.name','Test')
        self.commit();self.base=self.git('rev-parse','HEAD').strip()
    def tearDown(self):self.temp.cleanup()
    def git(self,*a):return m.git(self.root,*a)
    def commit(self):self.git('add','.');self.git('commit','-qm','test')
    def record(self,**override):
        r={'schema_version':1,'id':'test-event-one','recorded_at':dt.datetime.now(dt.timezone.utc).isoformat(),'author':'Codex','kind':'change','claim_level':'engineering_only','independent_release_validated':False,'source_base':self.base,'changed':'Change the source.','proves':'Execute the syntax check.','limits':'Independent detector accuracy remains unverified.','scope_ids':['F-139'],'files':{'source.py':m.digest(self.root,'source.py')},'evidence':[],'checks':[{'argv':['python3','-m','py_compile','source.py'],'exit_status':0,'pass':True,'finished_at':dt.datetime.now(dt.timezone.utc).isoformat()}]}
        r.update(override);name='runs/changes/'+r['id']+'.json';(self.root/name).write_text(json.dumps(r,indent=2)+'\n')
        p=self.root/'CHANGELOG.md';p.write_text(p.read_text()+'\n'+m.entry(r,name))
        return r,name
    def test_actual_change_passes(self):
        (self.root/'source.py').write_text('after\n');self.record();self.assertTrue(m.verify(self.root)['pass'])
    def first_push_base(self, **overrides):
        values={'base':'0'*40,'head':'HEAD','default_ref':'refs/remotes/origin/main','event_ref':'refs/heads/feature'}
        values.update(overrides)
        return m.select_change_base(self.root, **values)
    def test_first_push_checks_full_documented_branch(self):
        self.git('update-ref','refs/remotes/origin/main',self.base)
        (self.root/'source.py').write_text('after\n');self.record();self.commit()
        base=self.first_push_base()
        self.assertEqual(base,self.base)
        self.assertTrue(m.verify(self.root,base)['pass'])
    def test_first_push_cannot_hide_earlier_undocumented_commit(self):
        self.git('update-ref','refs/remotes/origin/main',self.base)
        (self.root/'earlier.py').write_text('undocumented\n');self.commit()
        parent=self.git('rev-parse','HEAD').strip()
        (self.root/'source.py').write_text('after\n');self.record(source_base=parent);self.commit()
        self.assertTrue(m.verify(self.root,parent)['pass'])
        result=m.verify(self.root,self.first_push_base())
        self.assertFalse(result['pass'])
        self.assertIn('New change missing fresh matching event: earlier.py',result['errors'])
    def test_first_push_current_undocumented_commit_fails(self):
        self.git('update-ref','refs/remotes/origin/main',self.base)
        (self.root/'source.py').write_text('after\n');self.commit()
        self.assertFalse(m.verify(self.root,self.first_push_base())['pass'])
    def test_first_push_requires_metadata(self):
        for overrides in [{'default_ref':None},{'event_ref':None},{'default_ref':'main'},{'event_ref':'feature'},
                          {'default_ref':'refs/remotes/origin/bad ref'},{'event_ref':'refs/heads/../main'}]:
            with self.subTest(overrides=overrides),self.assertRaises(ValueError):self.first_push_base(**overrides)
    def test_first_push_missing_default_history_refuses(self):
        with self.assertRaises(ValueError):self.first_push_base()
    def test_first_push_unrelated_history_refuses(self):
        self.git('update-ref','refs/remotes/origin/main',self.base)
        self.git('checkout','--orphan','unrelated')
        (self.root/'source.py').write_text('unrelated\n');self.commit()
        with self.assertRaises(ValueError):self.first_push_base()
    def test_initial_default_branch_checks_entire_tree(self):
        base=self.first_push_base(event_ref='refs/heads/main')
        self.assertEqual(base,self.git('hash-object','-t','tree','/dev/null').strip())
        result=m.verify(self.root,base)
        self.assertFalse(result['pass'])
        self.assertIn('New change missing fresh matching event: source.py',result['errors'])
    def test_normal_push_and_pr_keep_supplied_base(self):
        for base in [None,self.base,self.git('hash-object','-t','tree','/dev/null').strip()]:
            self.assertEqual(m.select_change_base(self.root,base),base)
    def test_first_push_cli_uses_event_metadata_and_fails_closed(self):
        scripts=Path(__file__).resolve().parents[1]/'scripts'
        for f in ['verify-changelog.py','changelog_core.py']:shutil.copyfile(scripts/f,self.root/'scripts'/f)
        self.git('update-ref','refs/remotes/origin/main',self.base)
        (self.root/'source.py').write_text('after\n')
        self.record(files={f:m.digest(self.root,f) for f in ['source.py','scripts/verify-changelog.py','scripts/changelog_core.py']})
        self.commit()
        env=dict(os.environ,CI='true',AITRUST_CHANGELOG_BASE='0'*40,
                 AITRUST_CHANGELOG_DEFAULT_REF='refs/remotes/origin/main',GITHUB_REF='refs/heads/feature')
        command=['python3',str(self.root/'scripts/verify-changelog.py')]
        result=subprocess.run(command,cwd=self.root,env=env,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        env['AITRUST_CHANGELOG_DEFAULT_REF']='refs/remotes/origin/missing'
        result=subprocess.run(command,cwd=self.root,env=env,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('unavailable or unrelated',result.stderr)
    def test_staged_dependency_link_cannot_bypass_exclusions(self):
        self.record()
        (self.root/'node_modules').symlink_to(self.root/'scripts',target_is_directory=True)
        self.git('add','node_modules','CHANGELOG.md','runs/changes')
        result=m.verify_staged(self.root)
        self.assertFalse(result['pass'])
        self.assertTrue(any('dependency/build artifact' in e for e in result['errors']))
    def test_new_change_fails_without_event(self):
        self.record();self.commit();(self.root/'source.py').write_text('after\n');self.assertFalse(m.verify(self.root)['pass'])
    def test_edit_after_record_fails(self):
        self.record();(self.root/'source.py').write_text('after\n');self.assertFalse(m.verify(self.root)['pass'])
    def test_clean_ci_detects_undocumented_commit(self):
        self.record();self.commit();old=self.git('rev-parse','HEAD').strip();(self.root/'source.py').write_text('after\n');self.commit();self.assertFalse(m.verify(self.root,old)['pass'])
    def test_clean_ci_accepts_documented_commit(self):
        (self.root/'source.py').write_text('after\n');self.record();self.commit();self.assertTrue(m.verify(self.root,self.base)['pass'])
    def test_unknown_scope_rejected(self):
        r,n=self.record(scope_ids=['F-999']);self.assertTrue(m.validate_record(self.root,r,n))
    def test_explicit_owner_required(self):
        r,n=self.record(author='');self.assertTrue(m.validate_record(self.root,r,n))
    def test_utc_required(self):
        r,n=self.record(recorded_at='2026-10-09T09:00:00');self.assertTrue(m.validate_record(self.root,r,n))
    def test_missing_evidence_rejected(self):
        r,n=self.record(checks=[],evidence=[{'path':'runs/missing.json','sha256':'0'*64}]);self.assertTrue(m.validate_record(self.root,r,n,current=True))
    def test_changed_evidence_rejected(self):
        (self.root/'runs/proof.json').write_text('{}');r,n=self.record(evidence=[{'path':'runs/proof.json','sha256':m.digest(self.root,'runs/proof.json')}]);(self.root/'runs/proof.json').write_text('{"pass":true}');self.assertTrue(m.validate_record(self.root,r,n,current=True))
    def test_unrelated_pass_cannot_support_release_claim(self):
        r,n=self.record(changed='PS is independently validated.');self.assertTrue(m.validate_record(self.root,r,n))
    def test_failed_gate_rejected(self):
        r,n=self.record();r['checks'][0]['exit_status']=1;self.assertTrue(m.validate_record(self.root,r,n))
    def test_no_evidence_rejected(self):
        r,n=self.record(checks=[]);self.assertTrue(m.validate_record(self.root,r,n))
    def test_deleted_source_supported(self):
        (self.root/'source.py').unlink();self.record();self.assertTrue(m.verify(self.root)['pass'])
    def test_historical_event_cannot_be_edited(self):
        r,n=self.record();self.commit();(self.root/n).write_text(json.dumps(r));self.assertFalse(m.verify(self.root)['pass'])
    def test_human_entry_must_agree(self):
        self.record();(self.root/'CHANGELOG.md').write_text('# Changelog\n');self.assertFalse(m.verify(self.root)['pass'])
    def test_traversal_rejected(self):
        r,n=self.record(files={'../private.env':'0'*64});self.assertTrue(m.validate_record(self.root,r,n))
    def test_hook_relative_index_environment(self):
        (self.root/'source.py').write_text('after\n');r,n=self.record()
        self.git('add','source.py','CHANGELOG.md',n)
        with patch.dict(os.environ, {'GIT_INDEX_FILE':'.git/index'}):
            self.assertTrue(m.verify_staged(self.root)['pass'])
    def test_staged_ignores_unrelated_drafts(self):
        (self.root/'source.py').write_text('after\n');r,n=self.record()
        self.git('add','source.py','CHANGELOG.md',n)
        (self.root/'unrelated-draft.md').write_text('In progress')
        self.assertTrue(m.verify_staged(self.root)['pass'])
        self.assertFalse(m.verify(self.root)['pass'])
    def test_staged_rejects_record_only_in_working_tree(self):
        (self.root/'source.py').write_text('after\n');self.record();self.git('add','source.py')
        self.assertFalse(m.verify_staged(self.root)['pass'])
    def test_staged_rejects_hash_for_unstaged_source(self):
        (self.root/'source.py').write_text('staged\n');self.git('add','source.py')
        (self.root/'source.py').write_text('unstaged\n');r,n=self.record();self.git('add','CHANGELOG.md',n)
        self.assertFalse(m.verify_staged(self.root)['pass'])
    def test_writer_failure_writes_nothing(self):
        scripts=Path(__file__).resolve().parents[1]/'scripts'
        for f in ['changelog-add.py','changelog_core.py']:shutil.copyfile(scripts/f,self.root/'scripts'/f)
        before=(self.root/'CHANGELOG.md').read_text()
        proc=subprocess.run(['python3',str(self.root/'scripts/changelog-add.py'),'--author','Test','--slug','failed','--changed','Change.','--proves','Check.','--limits','No accuracy claim.','--records','F-139','--files','source.py','--gate','python3 -c "raise SystemExit(1)"'],capture_output=True)
        self.assertNotEqual(proc.returncode,0);self.assertEqual((self.root/'CHANGELOG.md').read_text(),before);self.assertEqual(list((self.root/'runs/changes').glob('*.json')),[])
    def test_writer_commits_both_and_never_overwrites(self):
        scripts=Path(__file__).resolve().parents[1]/'scripts'
        for f in ['changelog-add.py','changelog_core.py']:shutil.copyfile(scripts/f,self.root/'scripts'/f)
        command=['python3',str(self.root/'scripts/changelog-add.py'),'--author','Test','--slug','written','--changed','Change.','--proves','Check.','--limits','No accuracy claim.','--records','F-139','--files','source.py','--gate','python3 -c "pass"']
        for _ in range(2):self.assertEqual(subprocess.run(command,capture_output=True).returncode,0)
        events=list((self.root/'runs/changes').glob('*.json'));self.assertEqual(len(events),2)
        for f in events:self.assertIn(m.entry(json.loads(f.read_text()),f.relative_to(self.root).as_posix()),(self.root/'CHANGELOG.md').read_text())
    def test_concurrent_writer_lock_refuses_without_changes(self):
        scripts=Path(__file__).resolve().parents[1]/'scripts'
        for f in ['changelog-add.py','changelog_core.py']:shutil.copyfile(scripts/f,self.root/'scripts'/f)
        lock=self.root/'runs/changes/.writer.lock';lock.write_text('')
        proc=subprocess.run(['python3',str(self.root/'scripts/changelog-add.py'),'--author','Test','--slug','locked','--changed','Change.','--proves','Check.','--limits','No accuracy claim.','--records','F-139','--files','source.py','--gate','python3 -c "pass"'],capture_output=True)
        self.assertNotEqual(proc.returncode,0);self.assertEqual(list((self.root/'runs/changes').glob('*.json')),[]);self.assertTrue(lock.exists())

if __name__=='__main__':unittest.main()
