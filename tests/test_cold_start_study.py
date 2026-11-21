"""Source/workflow and synthetic strict-aggregation controls; never emulator evidence."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import yaml
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('cold_study',ROOT/'scripts/cold-start-study.py')
study=importlib.util.module_from_spec(spec);spec.loader.exec_module(study)

class Workflow(unittest.TestCase):
    def setUp(self):
        self.workflow=yaml.safe_load((ROOT/'.github/workflows/android-cold-start-study.yml').read_text())
        self.original=yaml.safe_load(subprocess.check_output(['git','show',study.FROZEN_COMMIT+':.github/workflows/android-share.yml'],cwd=ROOT))
    def test_only_opened_path_can_launch_one_owned_three_job_wave(self):
        w=self.workflow;self.assertEqual(w['on'],{'pull_request':{'types':['opened'],'paths':['.github/workflows/android-cold-start-study.yml']}})
        self.assertEqual(w['permissions'],{'contents':'read'});self.assertEqual(set(w['jobs']),{'cold-start','aggregate'})
        job=w['jobs']['cold-start'];self.assertEqual(job['runs-on'],'ubuntu-24.04');self.assertEqual(job['timeout-minutes'],15)
        self.assertEqual(job['strategy'],{'fail-fast':False,'max-parallel':3,'matrix':{'sample':[1,2,3]}})
        self.assertEqual(job['if'],"github.event.action == 'opened' && github.run_attempt == 1 && github.head_ref == 'codex/android-cold-start-study' && github.base_ref == 'codex/android-hosted-followup' && github.event.pull_request.head.repo.full_name == github.repository")
        self.assertNotIn('secrets.',json.dumps(w));self.assertNotIn('continue-on-error',json.dumps(w))
    def test_original_runtime_steps_commands_env_and_bounds_are_identical(self):
        steps=self.workflow['jobs']['cold-start']['steps'];original=self.original['jobs']['offline-share']['steps']
        self.assertEqual(steps[3:-2],original[1:-1])
        checkout=copy.deepcopy(original[0]);checkout['with'].update(ref=study.FROZEN_COMMIT,path='frozen-runtime')
        self.assertEqual(steps[0],checkout)
        self.assertEqual(steps[1]['with'],{'persist-credentials':False,'ref':'${{ github.sha }}','path':'study-control'})
        self.assertEqual(self.workflow['jobs']['cold-start']['defaults'],{'run':{'working-directory':'frozen-runtime'}})
        self.assertIn('source-start',steps[2]['run']);self.assertIn('source-end',steps[-2]['run']);self.assertEqual(steps[-2]['if'],'always()')
    def test_unique_full_artifacts_and_all_outcomes_aggregate_are_pinned(self):
        w=self.workflow;j=w['jobs']['cold-start'];upload=j['steps'][-1]
        self.assertEqual(upload['uses'],'actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02')
        self.assertEqual(upload['if'],'always()');self.assertEqual(upload['with']['name'],'android-cold-start-${{ github.run_id }}-sample-${{ matrix.sample }}')
        paths=upload['with']['path'].splitlines()
        for path in self.original['jobs']['offline-share']['steps'][-1]['with']['path'].splitlines():self.assertIn('frozen-runtime/'+path,paths)
        self.assertIn('frozen-runtime/output/android-share/study-source-start.json',paths);self.assertIn('frozen-runtime/output/android-share/study-source-end.json',paths)
        aggregate=w['jobs']['aggregate'];self.assertEqual(aggregate['needs'],['cold-start']);self.assertEqual(aggregate['if'],'always()')
        self.assertEqual(aggregate['steps'][0],j['steps'][1]);self.assertEqual(aggregate['steps'][1]['uses'],'actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093')
        self.assertEqual(aggregate['steps'][1]['with']['merge-multiple'],False);self.assertIn('needs.cold-start.result',aggregate['steps'][2]['run'])
        self.assertEqual(aggregate['steps'][-1]['if'],'always()')
        for job in w['jobs'].values():
            for step in job['steps']:
                if 'uses' in step:self.assertRegex(step['uses'],r'^[a-z-]+/[a-z-]+@[0-9a-f]{40}$')
    def test_study_paths_do_not_trigger_existing_android_workflow(self):
        import fnmatch
        patterns=self.original[True]['pull_request']['paths'] if True in self.original else self.original['on']['pull_request']['paths']
        for name in ['.github/workflows/android-cold-start-study.yml','scripts/cold-start-study.py','tests/test_cold_start_study.py','docs/android-cold-start-study-plan.md']:
            self.assertFalse(any(fnmatch.fnmatch(name,p) for p in patterns),name)

class Aggregate(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve();self.run_id='123456'
        self.source={'format':'android-cold-start-source/v1','pass':True,'source_commit':study.FROZEN_COMMIT,'sources_sha256':study.EXPECTED_SOURCES,'tracked_source_clean':True,'control_script_sha256':study.sha((ROOT/'scripts/cold-start-study.py').read_bytes())}
        self.emulator={'format':'ai-trust-id-android-emulator/v1','status':'EXECUTED','pass':True,'phase':'complete','case_count':7,'api_level':'36','internet_permission':False,'license_record_unchanged':True,'sdk_license_acceptance_inferred_from_metadata_hash':False,'physical_device_evidence':False,'independent_accuracy_evidence':False,'cases':[{'case':name,'pass':True} for name in study.CASES]}
        for sample in study.SAMPLES:
            p=self.folder(sample);p.mkdir()
            for phase in ['start','end']:self.put(sample,'study-source-'+phase+'.json',{**self.source,'phase':phase})
            self.put(sample,'emulator.json',self.emulator)
            self.put(sample,'build.json',{'pass':True,'sources':study.NATIVE_SOURCES,'permission_count':0,'method_sha256':'a'*64})
            self.put(sample,'engine-parity.json',{'pass':True,'method_sha256':'a'*64})
            self.put(sample,'preparation.json',{'pass':True,'method_sha256':'a'*64,'runtime':'314.0.7'})
    def folder(self,sample):return self.root/f'android-cold-start-{self.run_id}-sample-{sample}'
    def put(self,sample,name,value):(self.folder(sample)/name).write_text(json.dumps(value))
    def aggregate(self,**kwargs):return study.aggregate(self.root,self.run_id,kwargs.get('attempt','1'),kwargs.get('matrix','success'))
    def test_all_three_exact_successes_required_without_reliability_claim(self):
        result=self.aggregate();self.assertTrue(result['pass']);self.assertEqual(result['samples_executed_seven'],3)
        self.assertFalse(result['historical_cause_known'] or result['startup_reliability_established'] or result['original_requirement_closed'])
    def test_any_failed_unavailable_or_partial_sample_fails_without_average(self):
        for status in ['FAILED','UNAVAILABLE']:
            value=copy.deepcopy(self.emulator);value.update(status=status,**{'pass':False},cases=[]);self.put(2,'emulator.json',value)
            result=self.aggregate();self.assertFalse(result['pass']);self.assertEqual(result['samples_executed_seven'],2);self.assertEqual(result['samples'][1]['reported_status'],status)
        value=copy.deepcopy(self.emulator);value['cases'].pop();self.put(2,'emulator.json',value);self.assertFalse(self.aggregate()['pass'])
    def test_missing_extra_and_wrong_order_cases_refuse(self):
        for cases in [self.emulator['cases'][:6],self.emulator['cases']+[{'case':'PRIVATE_UNKNOWN_CASE','pass':True}],list(reversed(self.emulator['cases']))]:
            value=copy.deepcopy(self.emulator);value['cases']=cases;self.put(1,'emulator.json',value);result=self.aggregate();self.assertFalse(result['pass']);self.assertNotIn('PRIVATE_',json.dumps(result))
    def test_bool_and_string_success_impostors_and_claim_promotions_refuse(self):
        for key,value in [('pass',1),('pass','true'),('internet_permission',True),('license_record_unchanged',False),('sdk_license_acceptance_inferred_from_metadata_hash',True),('physical_device_evidence',True),('independent_accuracy_evidence',True)]:
            report=copy.deepcopy(self.emulator);report[key]=value;self.put(3,'emulator.json',report);self.assertFalse(self.aggregate()['pass'])
        report=copy.deepcopy(self.emulator);report['cases'][0]['pass']=1;self.put(3,'emulator.json',report);self.assertFalse(self.aggregate()['pass'])
    def test_build_native_identity_permissions_and_method_are_required(self):
        valid={'pass':True,'sources':study.NATIVE_SOURCES,'permission_count':0,'method_sha256':'a'*64}
        for key,value in [('pass',False),('sources',{}),('permission_count',False),('method_sha256',None),('method_sha256','PRIVATE_METHOD_CANARY')]:
            record={**valid,key:value};self.put(1,'build.json',record);result=self.aggregate();self.assertFalse(result['pass']);self.assertNotIn('PRIVATE_',json.dumps(result))
    def test_source_commit_hash_drift_and_missing_final_snapshot_refuse(self):
        value={**self.source,'phase':'end','source_commit':'b'*40};self.put(1,'study-source-end.json',value);self.assertFalse(self.aggregate()['pass'])
        self.put(1,'study-source-end.json',{**self.source,'phase':'end','sources_sha256':{}});self.assertFalse(self.aggregate()['pass'])
        (self.folder(1)/'study-source-end.json').unlink();self.assertFalse(self.aggregate()['pass'])
    def test_emulator_digest_is_bound_to_the_single_inspected_read(self):
        original=study.read_regular;reads=[]
        def read(path,*args,**kwargs):
            if Path(path)==self.folder(1)/'emulator.json':reads.append(path)
            return original(path,*args,**kwargs)
        with mock.patch.object(study,'read_regular',side_effect=read):self.assertTrue(study.sample_result(self.folder(1))['pass'])
        self.assertEqual(len(reads),1)
    def test_missing_artifact_extra_sample_upstream_failure_and_attempt_two_fail(self):
        self.assertFalse(self.aggregate(matrix='failure')['pass']);self.assertFalse(self.aggregate(attempt='2')['pass'])
        (self.root/'android-cold-start-123456-sample-4').mkdir();self.assertFalse(self.aggregate()['pass'])
        (self.root/'android-cold-start-123456-sample-4').rmdir();(self.folder(2)/'emulator.json').unlink()
        result=self.aggregate();self.assertFalse(result['pass']);self.assertIsNone(result['samples'][1]['reported_case_count'])
    def test_duplicate_json_nonfinite_links_fifo_and_oversize_refuse(self):
        target=self.folder(1)/'emulator.json'
        for raw in [b'{"pass":true,"pass":true}',b'{"pass":NaN}',b'x'*(study.MAX_JSON+1)]:
            target.write_bytes(raw);self.assertFalse(self.aggregate()['pass'])
        target.unlink();other=self.root/'private';other.write_text('PRIVATE_CANARY');target.symlink_to(other);self.assertFalse(self.aggregate()['pass'])
        target.unlink();os.mkfifo(target);self.assertFalse(self.aggregate()['pass']);self.assertEqual(other.read_text(),'PRIVATE_CANARY')
    def test_private_unknown_fields_and_diagnostics_never_echo(self):
        value=copy.deepcopy(self.emulator);value.update(status='FAILED',**{'pass':False},cases=[],raw_input='PRIVATE_SUBJECT_CANARY',diagnostic_code='PRIVATE_CODE')
        value['last_ui_observation']={'owned_ui_present':True,'raw':'PRIVATE_UI'};value['first_failure_lifecycle']={'state':'PRIVATE_STATE','raw':'PRIVATE_EVENTS','observed_sequence':['PRIVATE_TOKEN']}
        self.put(1,'emulator.json',value);result=self.aggregate();self.assertFalse(result['pass']);self.assertNotIn('PRIVATE_',json.dumps(result))
        self.assertEqual(result['samples'][0]['last_ui_booleans'],{'owned_ui_present':True})
    def test_atomic_output_no_overwrite_and_symlink_parent_refusal(self):
        output=self.root/'reports/study.json';study.save(output,{'pass':False});before=output.read_bytes();self.assertEqual(output.stat().st_mode&0o777,0o600)
        with self.assertRaises(study.StudyError):study.save(output,{'pass':True})
        self.assertEqual(output.read_bytes(),before)
        owner=self.root/'owner';owner.mkdir();link=self.root/'link';link.symlink_to(owner,target_is_directory=True)
        with self.assertRaises(OSError):study.save(link/'new/report.json',{'pass':True})
        self.assertEqual(list(owner.iterdir()),[])
    def test_postlink_cleanup_failure_is_explicit_publication_uncertainty(self):
        output=self.root/'uncertain/report.json';original=study.os.unlink
        def unlink(name,*args,**kwargs):
            if str(name).startswith('.study-'):raise OSError('PRIVATE_CLEANUP_CANARY')
            return original(name,*args,**kwargs)
        with mock.patch.object(study.os,'unlink',side_effect=unlink):
            with self.assertRaisesRegex(study.OutputCommitUncertain,'^output_commit_uncertain$'):study.save(output,{'pass':False})
        self.assertEqual(json.loads(output.read_bytes()),{'pass':False})
    def test_real_cli_success_and_failed_sample_exit_status(self):
        script=ROOT/'scripts/cold-start-study.py'
        for outcome in ['success','failure']:
            if outcome=='failure':(self.folder(2)/'emulator.json').unlink()
            output=self.root/(outcome+'.json')
            result=subprocess.run([sys.executable,'-I','-S','-B',str(script),'aggregate','--inputs',str(self.root),'--run-id',self.run_id,'--attempt','1','--matrix-result','success','--output',str(output)],capture_output=True,timeout=10)
            # Output must be outside the expected artifact inventory.
            if outcome=='success':self.assertEqual(result.returncode,0)
            else:self.assertEqual(result.returncode,1)
            self.assertEqual(json.loads(output.read_bytes())['pass'],outcome=='success');self.assertFalse(result.stderr)
            output.unlink()
    def test_cli_unknown_argument_has_fixed_diagnostic(self):
        result=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/cold-start-study.py'),'--PRIVATE_PATH_CANARY'],capture_output=True,timeout=5)
        self.assertEqual(result.returncode,2);self.assertNotIn(b'PRIVATE_',result.stdout+result.stderr);self.assertFalse(result.stderr)

class FrozenSource(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
        import shutil
        for name in study.EXPECTED_SOURCES:
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,path)
    def git(self,commit=study.FROZEN_COMMIT,dirty=False):
        def run(argv,**kwargs):return subprocess.CompletedProcess(argv,0,(commit+'\n').encode() if argv[3:]==['rev-parse','HEAD'] else (b'M PRIVATE_PATH_CANARY\n' if dirty else b''),b'')
        return mock.patch.object(study.subprocess,'run',side_effect=run)
    def test_frozen_identity_and_clean_snapshot_have_exact_selected_inventory(self):
        with self.git():record=study.source_record(self.root,'start')
        self.assertTrue(record['pass']);self.assertEqual(record['sources_sha256'],study.EXPECTED_SOURCES)
    def test_wrong_commit_dirty_source_or_changed_selected_bytes_refuse(self):
        for patch in [self.git(commit='b'*40),self.git(dirty=True)]:
            with patch:
                with self.assertRaises(study.StudyError):study.source_record(self.root,'end')
        (self.root/'scripts/verify-android-emulator.py').write_text('PRIVATE_SOURCE_CANARY')
        with self.git():
            with self.assertRaises(study.StudyError):study.source_record(self.root,'start')
    def test_source_link_and_fifo_refuse_without_reading_private_target(self):
        path=self.root/'scripts/verify-android-emulator.py';private=self.root/'private';private.write_text('PRIVATE_OWNER_CANARY')
        path.unlink();path.symlink_to(private)
        with self.git():
            with self.assertRaises(OSError):study.source_record(self.root,'end')
        path.unlink();os.mkfifo(path)
        with self.git():
            with self.assertRaises(study.StudyError):study.source_record(self.root,'end')
        self.assertEqual(private.read_text(),'PRIVATE_OWNER_CANARY')

if __name__=='__main__':unittest.main()
