"""Fixed qualification-only monotonic window and owned phase-process boundary."""
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import tempfile
import time

SECOND=1_000_000_000
TOTAL=1740
WORK=1560
DRAIN=10
CAPS={'source':120,'acquire':1000,'install':480,'fixtures':120,'seal':60,'forward':1500,'cleanup':180}
MAX_STDOUT=65536
REASONS={'budget_invalid','budget_expired','phase_refused','phase_deadline','phase_cancelled','phase_failed','output_limit','cleanup_uncertain'}
class BudgetRefused(Exception):
 def __init__(self,reason='phase_refused'):
  self.reason=reason if reason in REASONS else 'phase_refused';super().__init__(self.reason)
class PublicationUncertain(BudgetRefused):
 def __init__(self):super().__init__('cleanup_uncertain')
class BudgetUncertain(BudgetRefused):
 def __init__(self):super().__init__('cleanup_uncertain')
def need(ok,reason='budget_invalid'):
 if not ok:raise BudgetRefused(reason)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def clock():return time.monotonic_ns()
def boot():
 value=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
 need(re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',value) is not None)
 return value
def identity(s):return s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_size,s.st_mtime_ns,s.st_ctime_ns
def private_read(path,cap):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
 try:
  s=os.fstat(fd);need(stat.S_ISREG(s.st_mode) and s.st_uid==os.geteuid() and stat.S_IMODE(s.st_mode)==0o600 and 0<s.st_size<=cap)
  raw=os.read(fd,cap+1);need(len(raw)==s.st_size and identity(os.fstat(fd))==identity(s));return raw
 finally:os.close(fd)
def write_private(path,raw):
 need(type(raw)is bytes and len(raw)<=2*1024**2)
 parent=Path(path).parent;fd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
 try:
  s=os.fstat(fd);need(s.st_uid==os.geteuid() and stat.S_IMODE(s.st_mode)==0o700)
  leaf=Path(path).name;need(leaf not in ('','.','..') and '/' not in leaf and '\\' not in leaf)
  out=os.open(leaf,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=fd)
  try:
   view=memoryview(raw)
   while view:view=view[os.write(out,view):]
   os.fsync(out)
  finally:os.close(out)
  need(identity(os.fstat(fd))[:4]==identity(s)[:4] and (parent.lstat().st_dev,parent.lstat().st_ino)==(s.st_dev,s.st_ino))
 finally:os.close(fd)
def encode(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def new_record(commit):
 need(type(commit)is str and re.fullmatch('[0-9a-f]{40}',commit) is not None)
 now=clock();need(type(now)is int and now>0)
 return {'profile':'visual-score-shared-budget/v1','source_commit':commit,'boot_id':boot(),'started_monotonic_ns':now,'work_deadline_ns':now+WORK*SECOND,'cleanup_deadline_ns':now+TOTAL*SECOND}
def validate(value):
 need(type(value)is dict and set(value)=={'profile','source_commit','boot_id','started_monotonic_ns','work_deadline_ns','cleanup_deadline_ns'})
 need(value['profile']=='visual-score-shared-budget/v1' and type(value['source_commit'])is str and re.fullmatch('[0-9a-f]{40}',value['source_commit']) is not None and value['boot_id']==boot())
 s=value['started_monotonic_ns'];need(all(type(value[k])is int for k in ('started_monotonic_ns','work_deadline_ns','cleanup_deadline_ns')) and s>0)
 need(value['work_deadline_ns']==s+WORK*SECOND and value['cleanup_deadline_ns']==s+TOTAL*SECOND)
 now=clock();need(type(now)is int and now>=s)
 return value
def load(path,expected_sha):
 need(type(expected_sha)is str and re.fullmatch('[0-9a-f]{64}',expected_sha) is not None)
 raw=private_read(path,2048);need(digest(raw)==expected_sha)
 def unique(pairs):
  d={}
  for k,v in pairs:need(k not in d);d[k]=v
  return d
 try:value=json.loads(raw,object_pairs_hook=unique)
 except (ValueError,UnicodeError,RecursionError):raise BudgetRefused('budget_invalid') from None
 return validate(value)
def phase_end(record,phase):
 validate(record);need(phase in CAPS)
 now=clock();end=min(record['cleanup_deadline_ns' if phase=='cleanup' else 'work_deadline_ns'],now+CAPS[phase]*SECOND)
 need(end-now>DRAIN*SECOND,'budget_expired')
 return end

def _signalable(child):
 """Our actual Popen child, same UID and group; not a sudo monitor or selected PID."""
 if child.poll() is not None:return False
 need(os.getpgid(child.pid)==child.pid,'cleanup_uncertain')
 with open('/proc/'+str(child.pid)+'/status') as stream:status=stream.read(16385)
 need(len(status)<=16384,'cleanup_uncertain')
 uid=next(line.split()[1:] for line in status.splitlines() if line.startswith('Uid:'))
 need(len(uid)==4 and all(int(x)==os.geteuid() for x in uid),'cleanup_uncertain')
 return True

def run_owned(argv,env,end_ns,input=None,accepted_codes=(0,),output_limit=MAX_STDOUT):
 """Internal fixed-phase caller only; no argv/duration input in the operator CLI."""
 need(input is None or type(input)is bytes and len(input)<=512)
 need(type(accepted_codes)is tuple and accepted_codes and all(type(c)is int and c in (0,2) for c in accepted_codes))
 need(type(output_limit)is int and 0<output_limit<=MAX_STDOUT)
 need(type(end_ns)is int and end_ns-clock()>DRAIN*SECOND,'budget_expired')
 # All fallible construction/clock work precedes spawn; ownership try is immediate.
 output=tempfile.TemporaryFile();child=None;complete=False;uncertain=False
 try:
  stop_at=end_ns-DRAIN*SECOND
  child=subprocess.Popen(argv,stdin=subprocess.PIPE if input is not None else subprocess.DEVNULL,stdout=output,stderr=subprocess.DEVNULL,start_new_session=True,close_fds=True,env=env)
  try:
   if input is not None:child.stdin.write(input);child.stdin.close()
   while True:
    code=child.poll()
    if code is not None:complete=True;break
    need(clock()<stop_at,'phase_deadline');need(os.fstat(output.fileno()).st_size<=output_limit,'output_limit')
    time.sleep(.02)
   need(clock()<=stop_at,'phase_deadline');need(child.returncode in accepted_codes,'phase_failed')
   need(os.fstat(output.fileno()).st_size<=output_limit,'output_limit');output.seek(0);raw=output.read(output_limit+1);need(len(raw)<=output_limit,'output_limit');return raw
  finally:
   if not complete and child.returncode is None:
    try:
     try:
      if _signalable(child):os.killpg(child.pid,signal.SIGTERM)
     except (OSError,ValueError,StopIteration,BudgetRefused):uncertain=True
     left=max(0,(end_ns-time.monotonic_ns())/SECOND)
     try:child.wait(timeout=min(5,left))
     except subprocess.TimeoutExpired:
      try:
       if _signalable(child):os.killpg(child.pid,signal.SIGKILL)
      except (OSError,ValueError,StopIteration,BudgetRefused):uncertain=True
      child.wait(timeout=max(0,min(5,(end_ns-time.monotonic_ns())/SECOND)))
    except (OSError,ValueError,StopIteration,subprocess.SubprocessError,BudgetRefused):uncertain=True

 finally:
  try:
   if child is not None and child.stdin is not None:
    try:child.stdin.close()
    except OSError:uncertain=True
  finally:
   try:
    try:output.close()
    except OSError:uncertain=True
   finally:
    if uncertain:raise BudgetUncertain() from None
