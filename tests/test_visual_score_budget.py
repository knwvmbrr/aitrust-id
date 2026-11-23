"""Bounded operator controls: no SDK, model, acquisition or native inference."""
import contextlib,hashlib,io,importlib.util,json,os,signal,stat,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import visual_score_budget as b
from tools import visual_score_qualification as q
spec=importlib.util.spec_from_file_location('_fixed_phase_operator',ROOT/'scripts/run-visual-score-phase.py');operator=importlib.util.module_from_spec(spec);spec.loader.exec_module(operator)
BOOT='12345678-1234-1234-1234-123456789abc'
class BudgetTests(unittest.TestCase):
 def record(self):
  with mock.patch.object(b,'boot',return_value=BOOT):return b.new_record('a'*40)
 @contextlib.contextmanager
 def private(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);os.chmod(root,0o700);yield root
 def write(self,p,value):
  raw=b.encode(value);b.write_private(p,raw);return b.digest(raw)
 def test_full_relations_and_nonextending_phase_caps(self):
  r=self.record();now=r['started_monotonic_ns']
  with mock.patch.object(b,'boot',return_value=BOOT),mock.patch.object(b,'clock',return_value=now):
   self.assertEqual(b.phase_end(r,'forward'),now+1500*b.SECOND)
  with mock.patch.object(b,'boot',return_value=BOOT),mock.patch.object(b,'clock',return_value=now+1000*b.SECOND):
   self.assertEqual(b.phase_end(r,'forward'),r['work_deadline_ns'])
  self.assertEqual(r['cleanup_deadline_ns']-r['work_deadline_ns'],180*b.SECOND)
 def test_cleanup_after_work_expiry_cannot_reset_window(self):
  r=self.record();now=r['work_deadline_ns']+b.SECOND
  with mock.patch.object(b,'boot',return_value=BOOT),mock.patch.object(b,'clock',return_value=now):
   with self.assertRaises(b.BudgetRefused):b.phase_end(r,'acquire')
   self.assertEqual(b.phase_end(r,'cleanup'),r['cleanup_deadline_ns'])
 def test_coherent_extended_record_and_boot_changes_refuse(self):
  with self.private() as d:
   r=self.record()
   for changed in [r|{'cleanup_deadline_ns':r['cleanup_deadline_ns']+b.SECOND},r|{'work_deadline_ns':r['work_deadline_ns']+1},r|{'boot_id':'0'*36},r|{'extra':True}]:
    p=d/str(len(list(d.iterdir())));h=self.write(p,changed)
    with mock.patch.object(b,'boot',return_value=BOOT),self.assertRaises(b.BudgetRefused):b.load(p,h)
 def test_hash_permissions_and_no_follow(self):
  with self.private() as d:
   p=d/'budget';r=self.record();h=self.write(p,r)
   with mock.patch.object(b,'boot',return_value=BOOT):self.assertEqual(b.load(p,h),r)
   with self.assertRaises(b.BudgetRefused):b.load(p,'b'*64)
   os.chmod(p,0o644)
   with self.assertRaises(b.BudgetRefused):b.load(p,h)
   (d/'link').symlink_to(p)
   with self.assertRaises(OSError):b.load(d/'link',h)
 def test_backwards_clock_and_exhausted_no_spawn(self):
  r=self.record()
  with mock.patch.object(b,'boot',return_value=BOOT),mock.patch.object(b,'clock',return_value=r['started_monotonic_ns']-1),self.assertRaises(b.BudgetRefused):b.validate(r)
  with mock.patch.object(b.subprocess,'Popen') as spawn,self.assertRaises(b.BudgetRefused):b.run_owned([sys.executable],{},b.clock())
  spawn.assert_not_called()
 def signalable(self,child):
  # Actual owned PGID; Linux UID witness inert on this Mac-only author control.
  return child.poll() is None and os.getpgid(child.pid)==child.pid
 def test_actual_owned_completion(self):
  raw=b.run_owned([sys.executable,'-I','-S','-B','-c','print("fixed")'],q.credential_free(),b.clock()+11*b.SECOND)
  self.assertEqual(raw,b'fixed\n')
 def test_actual_owned_deadline_and_reap(self):
  original=subprocess.Popen;children=[]
  def spawn(*a,**k):p=original(*a,**k);children.append(p);return p
  with mock.patch.object(b,'DRAIN',.15),mock.patch.object(b,'_signalable',side_effect=self.signalable),mock.patch.object(b.subprocess,'Popen',side_effect=spawn),self.assertRaises(b.BudgetRefused) as e:
   b.run_owned([sys.executable,'-I','-S','-B','-c','import time;time.sleep(5)'],q.credential_free(),b.clock()+int(.3*b.SECOND))
  self.assertEqual(e.exception.reason,'phase_deadline');self.assertEqual(len(children),1);self.assertIsNotNone(children[0].returncode)
 def test_postspawn_clock_fault_still_reaps(self):
  original=subprocess.Popen;children=[];now=b.clock()
  def spawn(*a,**k):p=original(*a,**k);children.append(p);return p
  with mock.patch.object(b,'clock',side_effect=[now,OSError('PRIVATE_CANARY')]),mock.patch.object(b,'_signalable',side_effect=self.signalable),mock.patch.object(b.subprocess,'Popen',side_effect=spawn),self.assertRaises(OSError):
   b.run_owned([sys.executable,'-I','-S','-B','-c','import time;time.sleep(5)'],q.credential_free(),now+11*b.SECOND)
  self.assertIsNotNone(children[0].returncode)
 def test_postreap_fault_never_signals_numeric_group(self):
  original=subprocess.Popen;children=[]
  class ClosedClock:
   def __call__(self):
    if children and children[0].returncode is not None:raise OSError('post_reap')
    return time.monotonic_ns()
  def spawn(*a,**k):p=original(*a,**k);children.append(p);return p
  with mock.patch.object(b,'clock',side_effect=ClosedClock()),mock.patch.object(b.subprocess,'Popen',side_effect=spawn),mock.patch.object(b.os,'killpg') as kill,self.assertRaises(OSError):
   b.run_owned([sys.executable,'-I','-S','-B','-c','pass'],q.credential_free(),time.monotonic_ns()+11*b.SECOND)
  kill.assert_not_called();self.assertEqual(children[0].returncode,0)
 def test_constructor_failure_closes_output(self):
  original=tempfile.TemporaryFile;files=[]
  def opened():f=original();files.append(f);return f
  with mock.patch.object(b.tempfile,'TemporaryFile',side_effect=opened),mock.patch.object(b.subprocess,'Popen',side_effect=OSError('spawn')),self.assertRaises(OSError):b.run_owned([sys.executable],{},b.clock()+11*b.SECOND)
  self.assertTrue(files[0].closed)
 def test_missing_seal_retains_actual_private_stage(self):
  with self.private() as d:
   reports=d/'reports';reports.mkdir(mode=0o700);stage=d/'visual-score-partial';stage.mkdir(mode=0o700);sentinel=stage/'keep';sentinel.write_bytes(b'private')
   with self.assertRaises(b.BudgetRefused):operator.worker('cleanup',stage,reports,sys.executable,self.record())
   self.assertEqual(sentinel.read_bytes(),b'private');self.assertEqual(json.loads((reports/'cleanup-private.json').read_text()),{'pass':False,'state':'retained_unsealed','private_bytes_may_remain':True})
 def test_failure_records_noecho_nooverwrite_and_no_success_promotion(self):
  with self.private() as d:
   operator.failure(d,'acquire','PRIVATE_CANARY');raw=(d/'qualification.json').read_bytes();self.assertNotIn(b'PRIVATE_CANARY',raw);self.assertFalse(json.loads(raw)['pass'])
   operator.failure(d,'forward','phase_failed');self.assertEqual((d/'qualification.json').read_bytes(),raw)
 def test_capacity_threshold_and_exact_facts(self):
  def disk(free):return mock.Mock(free=free)
  mem='MemAvailable: '+str(8*1024**3//1024)+' kB\n'
  with mock.patch.object(q.sys,'platform','linux'),mock.patch.object(q.sys,'version_info',(3,13,18)),mock.patch.object(q.platform,'machine',return_value='x86_64'),mock.patch.object(q.Path,'read_text',return_value=mem),mock.patch.object(q.shutil,'disk_usage',return_value=disk(14*1024**3-1)),self.assertRaises(q.QualificationRefused):q.capacity_facts(Path('.'))
  with mock.patch.object(q.sys,'platform','linux'),mock.patch.object(q.sys,'version_info',(3,13,18)),mock.patch.object(q.platform,'machine',return_value='x86_64'),mock.patch.object(q.Path,'read_text',return_value=mem),mock.patch.object(q.shutil,'disk_usage',return_value=disk(14*1024**3)),mock.patch.object(q.os,'cpu_count',return_value=4):
   facts=q.capacity_facts(Path('.'));self.assertEqual(facts['free_disk_bytes'],14*1024**3);self.assertEqual(facts['available_memory_bytes'],8*1024**3);self.assertEqual(facts['python_version'],[3,13,18]);self.assertEqual(facts['cpu_count'],4)
 def test_capacity_refusal_precedes_acquire_and_stage(self):
  with self.private() as d:
   reports=d/'reports';reports.mkdir(mode=0o700);stage=d/'visual-score-not-created'
   with mock.patch.object(q,'capacity_facts',side_effect=q.QualificationRefused),mock.patch.object(q,'main') as acquire,self.assertRaises(q.QualificationRefused):operator.worker('acquire',stage,reports,sys.executable,self.record())
   acquire.assert_not_called();self.assertFalse(stage.exists());self.assertEqual(list(reports.iterdir()),[])
 def test_actual_cancel_unwinds_and_reaps(self):
  original=subprocess.Popen;children=[];now=b.clock()
  def spawn(*a,**k):p=original(*a,**k);children.append(p);return p
  with mock.patch.object(b,'clock',side_effect=[now,KeyboardInterrupt()]),mock.patch.object(b,'_signalable',side_effect=self.signalable),mock.patch.object(b.subprocess,'Popen',side_effect=spawn),self.assertRaises(KeyboardInterrupt):
   b.run_owned([sys.executable,'-I','-S','-B','-c','import time;time.sleep(5)'],q.credential_free(),now+11*b.SECOND)
  self.assertIsNotNone(children[0].returncode)
 def test_released_output_close_error_is_typed_without_signal(self):
  original=tempfile.TemporaryFile;attempts=[]
  class File:
   def __init__(self):self.inner=original()
   def __getattr__(self,k):return getattr(self.inner,k)
   def close(self):self.inner.close();attempts.append(True);raise OSError('released')
  with mock.patch.object(b.tempfile,'TemporaryFile',side_effect=File),mock.patch.object(b.os,'killpg') as kill,self.assertRaises(b.BudgetUncertain):
   b.run_owned([sys.executable,'-I','-S','-B','-c','pass'],q.credential_free(),b.clock()+11*b.SECOND)
  self.assertEqual(len(attempts),1);kill.assert_not_called()
 def test_unknown_signalability_refuses_but_reaps_short_child(self):
  original=subprocess.Popen;children=[];now=b.clock()
  def spawn(*a,**k):p=original(*a,**k);children.append(p);return p
  with mock.patch.object(b,'clock',side_effect=[now,OSError('clock')]),mock.patch.object(b,'_signalable',side_effect=b.BudgetUncertain),mock.patch.object(b.subprocess,'Popen',side_effect=spawn),mock.patch.object(b.os,'killpg') as kill,self.assertRaises(b.BudgetUncertain):
   b.run_owned([sys.executable,'-I','-S','-B','-c','import time;time.sleep(.05)'],q.credential_free(),now+11*b.SECOND)
  kill.assert_not_called();self.assertIsNotNone(children[0].returncode)
 def test_forward_execs_fixed_verifier_no_kill_wrapper(self):
  with self.private() as d:
   record=self.record()
   with mock.patch.object(b,'boot',return_value=BOOT),mock.patch.object(operator.os,'execve',side_effect=OSError('exec unavailable')) as execute,mock.patch.object(q,'call') as wrapped,self.assertRaises(OSError):
    operator.worker('forward',d/'visual-score-owned',d,sys.executable,record)
   wrapped.assert_not_called();args=execute.call_args.args
   self.assertEqual(args[0],sys.executable);self.assertEqual(args[1][:4],[sys.executable,'-I','-B',str(ROOT/'scripts/verify-visual-score-qualification.py')]);self.assertNotIn('HF_TOKEN',args[2]);self.assertNotIn('GITHUB_TOKEN',args[2])
 def test_late_positive_private_candidate_never_published(self):
  with self.private() as d:
   stage=d/'visual-score-owned';r=self.record();current=[r['work_deadline_ns']+1];h=self.write(d/'budget.json',r)
   def late(*a):
    operator.emit(d/'qualification-candidate-private.json',{'pass':True});current[0]=r['cleanup_deadline_ns']+1;return b''
   argv=['operator','run','--phase','cleanup','--reports',str(d),'--workspace',str(stage),'--python',sys.executable,'--base-python',sys.executable,'--budget-sha',h]
   with mock.patch.object(sys,'argv',argv),mock.patch.object(b,'boot',return_value=BOOT),mock.patch.object(b,'clock',side_effect=lambda:current[0]),mock.patch.object(b,'run_owned',side_effect=late):self.assertEqual(operator.main(),2)
   self.assertFalse(json.loads((d/'qualification.json').read_text())['pass']);self.assertTrue(json.loads((d/'qualification-candidate-private.json').read_text())['pass'])
 def test_expired_cleanup_admission_no_child_or_deletion(self):
  with self.private() as d:
   stage=d/'visual-score-retained';stage.mkdir(mode=0o700);(stage/'keep').write_bytes(b'owned');r=self.record();h=self.write(d/'budget.json',r)
   argv=['operator','run','--phase','cleanup','--reports',str(d),'--workspace',str(stage),'--python',sys.executable,'--base-python',sys.executable,'--budget-sha',h]
   with mock.patch.object(sys,'argv',argv),mock.patch.object(b,'boot',return_value=BOOT),mock.patch.object(b,'clock',return_value=r['cleanup_deadline_ns']+1),mock.patch.object(b,'run_owned') as run:self.assertEqual(operator.main(),2)
   run.assert_not_called();self.assertEqual((stage/'keep').read_bytes(),b'owned');self.assertFalse(json.loads((d/'cleanup.json').read_text())['pass'])
 def test_actual_invalid_cli_noecho(self):
  p=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/run-visual-score-phase.py'),'PRIVATE_CANARY','--reports','PRIVATE_PATH'],capture_output=True,timeout=5)
  self.assertEqual(p.returncode,2);self.assertNotIn(b'PRIVATE',p.stdout+p.stderr);self.assertEqual(json.loads(p.stdout),{'pass':False,'reason':'phase_refused'})
 def test_actual_fixed_stdin_and_refusal_exit(self):
  raw=b.run_owned([sys.executable,'-I','-S','-B','-c','import sys;print(len(sys.stdin.buffer.read()));raise SystemExit(2)'],q.credential_free(),b.clock()+11*b.SECOND,input=b'fixed',accepted_codes=(2,),output_limit=16384)
  self.assertEqual(raw,b'5\n')
 def test_actual_output_limit_before_read(self):
  with self.assertRaises(b.BudgetRefused) as e:
   b.run_owned([sys.executable,'-I','-S','-B','-c','print("x"*20000)'],q.credential_free(),b.clock()+11*b.SECOND,output_limit=16384)
  self.assertEqual(e.exception.reason,'output_limit')
 def prepared_case(self,d):
  r=self.record();h=self.write(d/'budget.json',r);clean={'pass':True,'workspace_removed':True,'recursive_deletion_used':False}
  operator.emit(d/'cleanup-private.json',clean)
  operator.emit(d/'qualification-candidate-private.json',{'format':'offline-image-score-native-qualification/v1','pass':True,'state':'ENGINEERING_REFERENCE_QUALIFIED','cleanup':clean})
  return r,h,clean
 def test_original_postwrite_error_now_conditional_and_typed(self):
  with self.private() as d:
   r,h,clean=self.prepared_case(d);real=b.write_private
   def release_then_error(path,raw):
    real(path,raw)
    if Path(path).name=='qualification.json':raise OSError('after_actual_publication')
   with mock.patch.object(b,'boot',return_value=BOOT),mock.patch.object(b,'write_private',side_effect=release_then_error),self.assertRaises(b.PublicationUncertain):operator.publish_prepared(d,r,h,b.clock()+180*b.SECOND)
   result=json.loads((d/'qualification.json').read_text());self.assertFalse(result['pass']);self.assertTrue(result['requires_successful_exact_source_job']);self.assertFalse(result['publication_completion_attested']);self.assertEqual(result['candidate']['cleanup'],clean)
   self.assertFalse((d/'cleanup.json').exists())
  # Replay the original controller path too: actual write then fault, no child.
  with self.private() as d:
   r,h,clean=self.prepared_case(d);real=b.write_private;captured=io.StringIO()
   def broken(path,raw):
    real(path,raw)
    if Path(path).name=='qualification.json':raise OSError('after_complete_write')
   argv=['operator','run','--phase','cleanup','--reports',str(d),'--workspace',str(d/'visual-score-owned'),'--python',sys.executable,'--base-python',sys.executable,'--budget-sha',h]
   with mock.patch.object(sys,'argv',argv),mock.patch.object(b,'boot',return_value=BOOT),mock.patch.object(b,'run_owned',return_value=b''),mock.patch.object(b,'write_private',side_effect=broken),contextlib.redirect_stdout(captured):self.assertEqual(operator.main(),2)
   self.assertFalse(json.loads((d/'qualification.json').read_text())['pass']);last=json.loads((d/'cleanup.json').read_text());self.assertFalse(last['pass']);self.assertEqual(last['observed_cleanup'],clean);self.assertIn('Prepared output may remain',captured.getvalue())
 def test_postwrite_expiry_refuses_terminal_and_keeps_candidate_conditional(self):
  with self.private() as d:
   r,h,_=self.prepared_case(d);now=[b.clock()];end=now[0]+180*b.SECOND;real=b.write_private
   def slow(path,raw):real(path,raw);now[0]=end+1
   with mock.patch.object(b,'boot',return_value=BOOT),mock.patch.object(b,'clock',side_effect=lambda:now[0]),mock.patch.object(b,'write_private',side_effect=slow),self.assertRaises(b.PublicationUncertain):operator.publish_prepared(d,r,h,end)
   self.assertFalse(json.loads((d/'qualification.json').read_text())['pass']);self.assertFalse((d/'cleanup.json').exists())
 def test_normal_prepared_pair_binds_source_and_never_self_accepts(self):
  with self.private() as d:
   r,h,clean=self.prepared_case(d)
   with mock.patch.object(b,'boot',return_value=BOOT):self.assertTrue(operator.publish_prepared(d,r,h,b.clock()+180*b.SECOND))
   raw=(d/'qualification.json').read_bytes();first=json.loads(raw);last=json.loads((d/'cleanup.json').read_text())
   self.assertFalse(first['pass']);self.assertFalse(last['pass']);self.assertFalse(last['publication_completion_attested']);self.assertEqual(last['qualification_sha256'],b.digest(raw));self.assertEqual(last['source_commit'],'a'*40);self.assertEqual(last['observed_cleanup'],clean)
   self.assertTrue(last['candidate_pass']);self.assertTrue(first['candidate']['pass']);self.assertTrue(last['requires_successful_exact_source_job'])
 def test_exact_source_suite_admission_before_execution_and_actual_count(self):
  from types import SimpleNamespace
  expected={'test_visual_score.py':33,'test_visual_score_qualification.py':33,'test_visual_score_workflow.py':5,'test_visual_score_budget.py':27}
  self.assertEqual(operator.SOURCE_SUITE_COUNTS,expected)
  def suites(counts):return {name:unittest.TestSuite(unittest.FunctionTestCase(lambda:None) for _ in range(n)) for name,n in counts.items()}
  with self.private() as d:
   stage=d/'visual-score-not-created';record=self.record()
   for name,n in expected.items():
    for partial in (0,n-1):
     with self.subTest(discovery=name,count=partial):
      selected=suites(expected|{name:partial});loader=mock.Mock();loader.discover.side_effect=lambda *a,**k:selected[k['pattern']]
      with mock.patch.object(b,'boot',return_value=BOOT),mock.patch.object(unittest,'defaultTestLoader',loader),mock.patch.object(unittest,'TextTestRunner') as runner,mock.patch.object(q,'main') as check,self.assertRaises(b.BudgetRefused):operator.worker('source',stage,d,sys.executable,record)
      self.assertEqual(loader.discover.call_count,4);runner.assert_not_called();check.assert_not_called();self.assertFalse(stage.exists());self.assertFalse((d/'source-controls-private.json').exists())
   for bad in expected:
    with self.subTest(executed_count_mismatch=bad):
     selected=suites(expected);loader=mock.Mock();loader.discover.side_effect=lambda *a,**k:selected[k['pattern']]
     def result(suite):
      name=next(k for k,v in selected.items() if v is suite)
      return SimpleNamespace(testsRun=expected[name]-(1 if name==bad else 0),skipped=[],wasSuccessful=lambda:True)
     with mock.patch.object(b,'boot',return_value=BOOT),mock.patch.object(unittest,'defaultTestLoader',loader),mock.patch.object(unittest,'TextTestRunner') as runner,mock.patch.object(q,'main') as check,self.assertRaises(b.BudgetRefused):
      runner.return_value.run.side_effect=result;operator.worker('source',stage,d,sys.executable,record)
     check.assert_not_called();self.assertFalse(stage.exists());self.assertFalse((d/'source-controls-private.json').exists())
   selected=suites(expected);loader=mock.Mock();loader.discover.side_effect=lambda *a,**k:selected[k['pattern']]
   with mock.patch.object(b,'boot',return_value=BOOT),mock.patch.object(unittest,'defaultTestLoader',loader),mock.patch.object(unittest,'TextTestRunner') as runner,mock.patch.object(q,'main') as check:
    runner.return_value.run.side_effect=lambda suite:SimpleNamespace(testsRun=suite.countTestCases(),skipped=[],wasSuccessful=lambda:True)
    operator.worker('source',stage,d,sys.executable,record)
   self.assertEqual(runner.return_value.run.call_count,4);check.assert_called_once_with(['check-lock']);self.assertEqual(json.loads((d/'source-controls-private.json').read_text()),{'pass':True,'counts':expected,'skips':0});self.assertFalse(stage.exists())
if __name__=='__main__':unittest.main()
