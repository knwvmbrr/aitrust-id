"""Finite protected-Q source-copy extension. No runtime, signature or release approval.

SPDX-License-Identifier: Apache-2.0
"""
import argparse
import base64
import builtins
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import sys
import threading
import time
import types

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'source-copy-additions/v5'
POLICY = 'eval/dependencies/source-snapshot-additions-v5.json'
POLICY_SHA256 = 'bed27448c456186eded268ef30c9b4cef6205d554f901586720bb107122fd134'
Q = '898dc254ff8d4c924d699afe732d3c1bbfe1bb01'
Q_TREE = '87b84b9a0f16987cdc3d696c52cf33e049088465'
Q_FILES, Q_BYTES = 13888, 151697171
V4_SHA = '0e70d9f360533dbd13f67192b967e8831787fce381c220bc013fc8a7eaa0989e'
FOUNDATION_PINS = {'tools/source_release_policy.py': {'mode': '100644', 'git_blob_oid': 'b97601876dd182d298944d11816cdb07c296f1fe', 'bytes': 17412, 'sha256': '897d287a1dc91c441db54237b0b80dfe634521ecc6b644944d04a63623b591b6'}, 'tools/source_release_policy_v2.py': {'mode': '100644', 'git_blob_oid': '0353dfd270ff31353455c2b154b909b4a5bad2e6', 'bytes': 22383, 'sha256': '6642ab4ec688754ed5234027bdf029fd2a100b77d262fc98b958e1aed7c7126c'}, 'tools/source_release_policy_v3.py': {'mode': '100644', 'git_blob_oid': 'cd3183ed19f8ecd7f11808380c06265eb2c94f80', 'bytes': 24924, 'sha256': '26a6bb8be66cab5a355bfbe6fcfbd16cefe994d1e7ade8b26b3cd227f0f82d41'}, 'tools/source_release_policy_v4.py': {'mode': '100644', 'git_blob_oid': 'b609d81bd2ca00ef925fc0d6ced4e66a3c6289ef', 'bytes': 24893, 'sha256': '0e70d9f360533dbd13f67192b967e8831787fce381c220bc013fc8a7eaa0989e'}, 'eval/dependencies/source-snapshot-release.json': {'mode': '100644', 'git_blob_oid': '76153604af07df009b857ada090c3449d390a488', 'bytes': 3049927, 'sha256': '2e555a5dc31a9d92b0982a9dba1fefea9376a45bb0d4c99625332b59965c6645'}, 'eval/dependencies/source-snapshot-release-v2.json': {'mode': '100644', 'git_blob_oid': 'ea2c7c5dce0510b4248cfe81b6ac93150d6b5204', 'bytes': 410005, 'sha256': '2c6bc3c14c8825f8fdd583e42adb1df39e7983ee6f2bac96004231a3dbd6543d'}, 'eval/dependencies/source-snapshot-additions-v3.json': {'mode': '100644', 'git_blob_oid': 'e5ba152d50922057f255b22a96a83062f661d655', 'bytes': 142724, 'sha256': '3bd727fef18736bcd259fa4f1e21fd25fa8629f361b25289dc0016f48394db3e'}, 'eval/dependencies/source-snapshot-additions-v4.json': {'mode': '100644', 'git_blob_oid': 'c21ffaaf9f11666c9db504665f4ab4eb6b1c32fa', 'bytes': 49133, 'sha256': 'da42db15f4fdb9b17784344fb5c7381bbd7e2d257b7a01f4b18fc88678c9db8c'}, 'tools/source_snapshot_binding.py': {'mode': '100644', 'git_blob_oid': 'fe41b0cb7247c97e3723af126c72e2fe0a6a77c3', 'bytes': 14697, 'sha256': 'c219f326861c2634e930d7c0b74c0abad9859b3abe746a77464ece5ba8fceffb'}, 'scripts/worker_process.py': {'mode': '100644', 'git_blob_oid': '2f3164958b6a04768a57c3f5367c6b4b1b5da18f', 'bytes': 3483, 'sha256': '9411406936c9757a67306211a695cbe54c0e318ca1d7e6c9229d24103baeb7a3'}, 'tools/dependency_policy.py': {'mode': '100644', 'git_blob_oid': 'd202aa40abee220e608f98eba903d4bf004419ea', 'bytes': 15682, 'sha256': 'e72e478a7508e6c3e6e000803ee4d583900f626cc219870fd1ad140131608408'}}
V4_POLICY_SHA = 'da42db15f4fdb9b17784344fb5c7381bbd7e2d257b7a01f4b18fc88678c9db8c'
MAX_FILES, MAX_TOTAL, MAX_ARCHIVE = 16384, 256_000_000, 64_000_000
MAX_PROJECT, MAX_COPIED, MAX_POLICY = 160, 256, 1_000_000
MAX_BODY, MAX_INSPECTED, MAX_FDS = 2_000_000, 64_000_000, 80
BASELINE_RESERVATION = 26_353_551
OID = re.compile('[a-f0-9]{40}')
SHA = re.compile('[a-f0-9]{64}')
FALSE_CLAIMS = ('legal_clearance', 'compiled_runtime_permission', 'source_archive_admitted',
                'release_authorized', 'accuracy', 'complete_F057_X02')
CODES = frozenset({'invalid_request','foundation_changed','policy_changed','invalid_profile',
 'source_unavailable','source_changed','resource_limit','git_unavailable','unknown_path',
 'missing_path','grant_changed','grant_unavailable','third_party_or_asset_changed',
 'license_declaration_changed','unsupported_source_commit','unsupported_git_entry',
 'unsupported_first_party_text','archive_refused','deadline','cleanup_unconfirmed','unavailable'})
ENV = {'PATH':'/usr/bin:/bin','LC_ALL':'C','GIT_CONFIG_NOSYSTEM':'1',
 'GIT_CONFIG_SYSTEM':'/dev/null','GIT_CONFIG_GLOBAL':'/dev/null','GIT_NO_LAZY_FETCH':'1',
 'GIT_TERMINAL_PROMPT':'0','GIT_OPTIONAL_LOCKS':'0'}
MARKERS = re.compile(r'^\s*(?:[#/*;]+\s*)?(?:SPDX-License-Identifier:.*|Copyright\b.*|Licensed under\b.*)$', re.I|re.M)

class Refused(ValueError):
    def __init__(self, code='unavailable', *, cleanup_complete=False):
        self.code = code if code in CODES else 'unavailable'
        self.cleanup_complete = cleanup_complete
        super().__init__('Source-copy V5 unavailable.')

def need(value, code='invalid_profile'):
    if not value: raise Refused(code)

def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(value): return json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False,separators=(',',':')).encode()
def keys(value, names): need(type(value) is dict and value.keys()==set(names))
def parse(raw):
    def pairs(items):
        result={}
        for k,v in items: need(k not in result); result[k]=v
        return result
    def bad(value): raise Refused('invalid_profile')
    return json.loads(raw.decode('utf8','strict'),object_pairs_hook=pairs,parse_float=bad,parse_constant=bad)

def path_name(name):
    need(type(name)is str and 0<len(name.encode())<=1000 and not name.startswith('/')
      and '\\' not in name and all(x not in ('','.','..','.git') for x in name.split('/'))
      and not any(ord(x)<32 for x in name)); return name

def fd_room(reserve=1):
    # Bound enumeration too; caller cannot provide a numeric override through verify/CLI.
    need(type(reserve)is int and 0<=reserve<=MAX_FDS,'resource_limit')
    count=0
    with os.scandir('/dev/fd' if sys.platform=='darwin' else '/proc/self/fd') as scan:
        for unused in scan:
            count+=1; need(count+reserve<=MAX_FDS,'resource_limit')
    return count

def spawn_room():
    # N includes the bounded /dev/fd or /proc/self/fd enumeration transient.
    # Outer Popen fork transient <=2N+16; post-exec fixed nested worker <=N+32.
    # This deliberately refuses high-FD callers; there is no numeric allow flag.
    n=fd_room(0);need(max(2*n+16,n+32)<=MAX_FDS,'resource_limit');return n

class Clock:
    def __init__(self, seconds=30):
        self.cleanup_complete=False;self.failed=False;self.start=self.last=self.sample(); self.work=self.start+seconds-5; self.end=self.start+seconds
    @staticmethod
    def sample():
        value=time.monotonic();need(type(value)in(int,float)and math.isfinite(value),'deadline');return value
    def now(self, cleanup=False):
        try:
            value=self.sample();need(value>=self.last and (cleanup or not self.failed),'deadline');self.last=value
            need(value<(self.end if cleanup else self.work),'deadline');return value
        except BaseException:
            self.failed=True;raise
    def remaining(self, cleanup=False): return (self.end if cleanup else self.work)-self.now(cleanup)

@contextmanager
def original_clock(clock):
    need(threading.current_thread()is threading.main_thread() and threading.active_count()==1
      and signal.getitimer(signal.ITIMER_REAL)==(0.,0.),'source_unavailable')
    old=signal.getsignal(signal.SIGALRM)
    def expired(*unused): raise Refused('deadline',cleanup_complete=clock.cleanup_complete)
    try:
        signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,clock.remaining());yield
    finally:
        try: signal.setitimer(signal.ITIMER_REAL,0)
        finally: signal.signal(signal.SIGALRM,old)

@contextmanager
def masked_alarm():
    old=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGALRM})
    try: yield
    finally: signal.pthread_sigmask(signal.SIG_SETMASK,old)

def capture(path, limit, clock):
    clock.now();path=Path(path);need(not path.is_symlink()and not any(p.is_symlink()for p in path.parents),'source_unavailable')
    fd_room();fd=None
    try:
        with masked_alarm(): fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        before=os.fstat(fd);need(stat.S_ISREG(before.st_mode)and before.st_nlink==1 and 0<=before.st_size<=limit,'resource_limit')
        out=bytearray()
        while len(out)<before.st_size:
            clock.now();b=os.read(fd,min(65536,before.st_size-len(out)));need(b,'source_changed');out.extend(b)
        after=os.fstat(fd);named=path.lstat();identity=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        need(identity(before)==identity(after)==identity(named),'source_changed');return bytes(out)
    finally:
        if fd is not None:
            with masked_alarm(): owned,fd=fd,None;os.close(owned)
        clock.now()

# The child executes only the exact fixed V4 bytes. Its SIGTERM interrupts immutable
# worker finally paths; an acknowledgement is written ONLY after no child remains.
BASELINE_PROGRAM = r'''
import base64,builtins,hashlib,json,os,signal,sys,types
class Cancelled(BaseException):pass
def cancel(*args):raise Cancelled()
old=signal.signal(signal.SIGTERM,cancel)
result=None;cancelled=False;clean=False
try:
 raw=sys.stdin.buffer.read(100001)
 if len(raw)>100000:raise ValueError()
 d=json.loads(raw);source=base64.b64decode(d['source'],validate=True)
 if hashlib.sha256(source).hexdigest()!='0e70d9f360533dbd13f67192b967e8831787fce381c220bc013fc8a7eaa0989e':raise ValueError()
 ns={'__name__':'_captured_source_copy_v4','__file__':d['root']+'/tools/source_release_policy_v4.py'}
 exec(compile(source,'<captured-source-copy-v4>','exec'),ns)
 result=ns['verify'](source_commit='898dc254ff8d4c924d699afe732d3c1bbfe1bb01')
except Cancelled:cancelled=True
except BaseException:result=None
finally:
 try:
  # Fresh process owns every child; V4 read-only Git calls are direct children.
  # A live child (0,0) or unreaped unexpected child is NOT a clean acknowledgement.
  try:os.waitpid(-1,os.WNOHANG)
  except ChildProcessError:clean=True
 finally:signal.signal(signal.SIGTERM,old)
print(json.dumps({'cleanup_complete':clean,'cancelled':cancelled,'result':result},sort_keys=True),flush=True)
'''

def _run_baseline(program, payload, clock):
    clock.now();spawn_room();need(type(payload)is bytes and len(payload)<=100000,'resource_limit')
    env=dict(ENV)
    if 'HOME'in os.environ:env['HOME']=os.environ['HOME']
    child=None;selector=None;complete=False;output=bytearray();offset=0;cleanup=False;failure=None
    try:
        with masked_alarm():
            child=subprocess.Popen([sys.executable,'-I','-S','-B','-c',program],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
              stderr=subprocess.DEVNULL,bufsize=0,start_new_session=True,close_fds=True,env=env)
        selector=selectors.DefaultSelector();os.set_blocking(child.stdin.fileno(),False);os.set_blocking(child.stdout.fileno(),False)
        selector.register(child.stdout,selectors.EVENT_READ,'out');selector.register(child.stdin,selectors.EVENT_WRITE,'in')
        eof=False
        while not eof:
            for key,unused in selector.select(min(.05,clock.remaining())):
                if key.data=='in':
                    try:offset+=os.write(child.stdin.fileno(),memoryview(payload)[offset:offset+65536])
                    except BlockingIOError:continue
                    if offset==len(payload):selector.unregister(child.stdin);child.stdin.close()
                else:
                    try:b=os.read(child.stdout.fileno(),4097-len(output))
                    except BlockingIOError:continue
                    if not b:selector.unregister(child.stdout);eof=True;break
                    output.extend(b);need(len(output)<=4096,'resource_limit')
        need(child.wait(timeout=clock.remaining())==0,'unavailable')
        value=parse(bytes(output));keys(value,('cleanup_complete','cancelled','result'))
        need(value['cleanup_complete']is True and value['cancelled']is False,'cleanup_unconfirmed')
        cleanup=True;complete=True;clock.now();return value['result']
    except BaseException as error:
        failure=error;raise
    finally:
        # One original cleanup deadline, not a fresh five seconds. TERM permits
        # the immutable worker's own group kill+wait finally to run first.
        with masked_alarm():
            try:
                if child is not None and not complete and child.returncode is None:
                    try:os.killpg(child.pid,signal.SIGTERM)
                    except ProcessLookupError:pass
                    try:
                        child.wait(timeout=clock.remaining(True))
                        if child.stdout and not child.stdout.closed:
                            os.set_blocking(child.stdout.fileno(),False)
                            while len(output)<=4096:
                                try:b=os.read(child.stdout.fileno(),4097-len(output))
                                except BlockingIOError:break
                                if not b:break
                                output.extend(b)
                        try:cleanup=parse(bytes(output)).get('cleanup_complete')is True
                        except Exception:cleanup=False
                    except BaseException:
                        cleanup=False
                        if child.returncode is None:
                            try:os.killpg(child.pid,signal.SIGKILL)
                            except ProcessLookupError:pass
                            try:child.wait(timeout=clock.remaining(True))
                            except BaseException:pass
            finally:
                errors=[]
                for owned in (selector,child.stdin if child else None,child.stdout if child else None):
                    if owned is not None:
                        try:owned.close()
                        except BaseException as error:errors.append(error)
                if errors:raise Refused('cleanup_unconfirmed')
                clock.cleanup_complete=cleanup
                if failure is not None and isinstance(failure,Refused):failure.cleanup_complete=cleanup
        if complete:clock.now()


def foundations(data,clock):
    captured={}
    need(data['foundations']==FOUNDATION_PINS,'foundation_changed')
    for name,row in data['foundations'].items():
        path_name(name);keys(row,('mode','git_blob_oid','bytes','sha256'))
        raw=capture(ROOT/name,row['bytes'],clock);need(len(raw)==row['bytes']and sha(raw)==row['sha256'],'foundation_changed');captured[name]=raw
    need(sha(captured['tools/source_release_policy_v4.py'])==V4_SHA
      and sha(captured['eval/dependencies/source-snapshot-additions-v4.json'])==V4_POLICY_SHA,'foundation_changed')
    return captured

def worker(raw):
    ns={'__name__':'_captured_source_worker'};exec(compile(raw,'<captured-source-worker>','exec'),ns);return ns['run_worker']

def git_reader(run,clock):
    def git(args,limit=2_000_000):
        clock.now();spawn_room()
        # The literal interpreter shim clears inherited Git/config/transport state.
        shim="import os,sys\ne="+repr(ENV)+"\nif 'HOME' in os.environ:e['HOME']=os.environ['HOME']\nos.execve('/usr/bin/git',['git','--no-replace-objects','-c','protocol.allow=never','-c','core.useReplaceRefs=false',*sys.argv[1:]],e)"
        out=run([sys.executable,'-I','-S','-B','-c',shim,'-C',str(ROOT),*args],input=b'',timeout=min(20,clock.remaining()),output_limit=limit)
        need(out.returncode==0,'git_unavailable');clock.now();return out.stdout
    return git

def tree_rows(raw):
    need(type(raw)is bytes and 0<len(raw)<=2_000_000,'resource_limit');parts=raw.split(b'\0');need(parts[-1:]==[b''],'unsupported_git_entry')
    rows={};total=0
    for item in parts[:-1]:
        fields,name=item.split(b'\t',1);mode,kind,oid,size=fields.decode('ascii').split();name=path_name(name.decode('utf8','strict'))
        need(mode in('100644','100755')and kind=='blob'and OID.fullmatch(oid)and re.fullmatch('0|[1-9][0-9]*',size),'unsupported_git_entry')
        size=int(size);total+=size;need(name not in rows and size<=32_000_000 and total<=MAX_TOTAL and len(rows)<MAX_FILES,'resource_limit');rows[name]=(mode,oid,size)
    need(rows,'missing_path');return rows,total

class Bodies:
    def __init__(self,git,clock,reserved=BASELINE_RESERVATION):
        need(type(reserved)is int and 0<=reserved<=MAX_INSPECTED,'resource_limit');self.git=git;self.clock=clock;self.used=reserved;self.cache={}
    def charge(self,size):
        need(type(size)is int and 0<=size<=MAX_BODY,'resource_limit');self.used+=size;need(self.used<=MAX_INSPECTED,'resource_limit')
    def read(self,row):
        self.clock.now();mode,oid,size=row;need(type(size)is int and 0<=size<=MAX_BODY,'resource_limit')
        if oid in self.cache:need(len(self.cache[oid])==size,'source_changed');return self.cache[oid]
        self.used+=size+1;need(self.used<=MAX_INSPECTED,'resource_limit');raw=self.git(['cat-file','blob',oid],min(size+1,MAX_BODY))
        need(len(raw)==size and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+raw).hexdigest()==oid,'source_changed');self.cache[oid]=raw;return raw

def markers(raw):
    need(type(raw)is bytes and b'\0'not in raw,'unsupported_first_party_text');text=raw.decode('utf8','strict');lines=MARKERS.findall(text)
    return sha('\n'.join(x.strip()for x in lines).encode()),lines

def mixed_tokenizers(raw,row,observed,read,clock,charge):
    need(sha(raw)==row['sha256']and len(raw)==row['bytes'],'source_changed');d=parse(raw)
    keys(d,('associations','carried_notices','claims','counts','format','limits','packages','policy','purpose','source','target','texts'))
    need(d['format']=='visual-score-exact-wheel-source-preservation/v1'and d['policy']=='private-reference-source-notice-preservation/v1'
      and d['purpose']=='PRIVATE_REFERENCE_QUALIFICATION_ONLY'and d['carried_notices']==[],'grant_changed')
    need(d['counts']==row['counts']and all(type(x)is int for x in d['counts'].values())
      and d['claims']==row['claims']and all(x is False for x in d['claims'].values()),'grant_changed')
    need(sha(canonical(d['source']))==row['source_sha256']and sha(canonical(d['target']))==row['target_sha256']
      and sha(canonical(d['packages']))==row['packages_sha256']and sha(canonical(d['associations']))==row['associations_sha256'],'grant_changed')
    need(type(d['texts'])is list and len(d['texts'])==93 and type(d['associations'])is list and len(d['associations'])==309,'grant_changed')
    terms={}
    for item in d['texts']:
        clock.now();keys(item,('base64','bytes','sha256'));need(type(item['bytes'])is int and 0<=item['bytes']<=MAX_BODY and type(item['base64'])is str,'grant_changed')
        charge(item['bytes']);value=base64.b64decode(item['base64'],validate=True);need(len(value)==item['bytes']and sha(value)==item['sha256']and item['sha256']not in terms,'grant_changed');terms[item['sha256']]=value
    need(sorted((k,len(v))for k,v in terms.items())==[tuple(x)for x in row['terms']],'grant_changed')
    anchors=row['anchors'];need(len(anchors)==95,'grant_changed')
    for name,anchor in anchors.items():
        clock.now();need(name in observed and observed[name]==(anchor['mode'],anchor['git_blob_oid'],anchor['bytes']),'grant_changed')
        need(sha(read(observed[name]))==anchor['sha256'],'grant_changed')
    need({x['term_sha256']for x in d['associations']}==terms.keys()and {x['retained_source_path']for x in d['associations']}==anchors.keys(),'grant_changed')
    for item in d['associations']:
        clock.now();need(item['retained_source_path']in anchors and item['term_sha256']in terms and item['role']in('source-carried','project-source-carried','upstream-source-supplement'),'grant_changed')
        need(sha(read(observed[item['retained_source_path']]))==item['term_sha256'],'grant_changed')

def classify(data,qrows,observed,read,clock,charge):
    total=0
    need(0<len(observed)<=MAX_FILES,'resource_limit')
    for r in observed.values():
        need(type(r)in(tuple,list)and len(r)==3 and r[0]in('100644','100755')and type(r[1])is str and OID.fullmatch(r[1])and type(r[2])is int and 0<=r[2]<=32_000_000,'unsupported_git_entry');total+=r[2];need(total<=MAX_TOTAL,'resource_limit')
    project=set(data['project_files']);copied={x['path']:x for x in data['copied_files']}
    need(len(project)==len(data['project_files'])and len(project)+sum(x['authored_capacity_charge']for x in copied.values())<=MAX_PROJECT,'resource_limit')
    need(len(copied)==len(data['copied_files'])and len(copied)<=MAX_COPIED,'resource_limit')
    for name in project|copied.keys():path_name(name)
    # Full denominator FIRST. No filtering can hide a copied or unknown member.
    need(observed.keys()<=qrows.keys()|project|copied.keys(),'unknown_path');need(qrows.keys()<=observed.keys(),'missing_path')
    need(observed['tools/dependency_policy.py']==qrows['tools/dependency_policy.py'],'source_changed')
    allowed={'SPDX-License-Identifier: Apache-2.0','Licensed under the Apache License, Version 2.0.','Copyright 2026 Michael Raashad McGuire and AITrust-ID contributors.'}
    changed=introduced=present=0
    for name,row in observed.items():
        clock.now()
        if name in qrows and row==qrows[name]:continue
        if name in copied:
            item=copied[name];need(name not in qrows and row==(item['mode'],item['git_blob_oid'],item['bytes']),'third_party_or_asset_changed')
            need(item['kind']=='tokenizers-source-preservation/v1'and item['unresolved']==[],'grant_unavailable');mixed_tokenizers(read(row),item,observed,read,clock,charge);present+=1;continue
        need(name in project,'third_party_or_asset_changed');raw=read(row);marker,lines=markers(raw)
        if name in qrows:
            need(name in data['maintained_project_files'],'third_party_or_asset_changed');need(marker==markers(read(qrows[name]))[0],'license_declaration_changed');changed+=1
        else:
            need(all(x.strip().lstrip('#/*; ').rstrip('*/ ').strip()in allowed for x in lines),'license_declaration_changed');introduced+=1
    return {'files':len(observed),'source_bytes':sum(x[2]for x in observed.values()),'changed_named_project_text_files':changed,'introduced_named_project_text_files':introduced,'present_optional_copied_files':present}

def policy(raw):
    need(sha(raw)==POLICY_SHA256,'policy_changed');d=parse(raw)
    keys(d,('profile','protected_q','protected_q_tree','q_files','q_bytes','foundations','legacy_v4_names','baseline_read_reservation','project_files','maintained_project_files','copied_files','claims','source_observation'))
    need(d['profile']==PROFILE and d['protected_q']==Q and d['protected_q_tree']==Q_TREE and type(d['q_files'])is int and d['q_files']==Q_FILES
      and type(d['q_bytes'])is int and d['q_bytes']==Q_BYTES,'foundation_changed')
    need(d['baseline_read_reservation']['bytes']==BASELINE_RESERVATION and type(d['baseline_read_reservation']['bytes'])is int,'foundation_changed')
    need(len(d['legacy_v4_names'])==159 and len(set(d['legacy_v4_names']))==159,'foundation_changed')
    need(type(d['project_files'])is list and len(d['project_files'])<=MAX_PROJECT and type(d['maintained_project_files'])is list
      and set(d['maintained_project_files'])<=set(d['project_files'])and len(set(d['maintained_project_files']))==len(d['maintained_project_files']),'invalid_profile')
    need(type(d['copied_files'])is list and len(d['copied_files'])<=MAX_COPIED,'invalid_profile')
    keys(d['claims'],FALSE_CLAIMS);need(all(x is False for x in d['claims'].values()),'invalid_profile')
    keys(d['source_observation'],('selected_source_is_protected','actual_candidate_verified'));need(all(x is False for x in d['source_observation'].values()),'invalid_profile')
    need(all(type(x.get('authored_capacity_charge'))is bool for x in d['copied_files']),'invalid_profile');return d

def _verify(root,source_commit,clock):
    result={'profile':PROFILE,'pass':False,'status':'UNAVAILABLE','source_copy_profile_satisfied':False,**{k:False for k in FALSE_CLAIMS}}
    try:
        clock.now();need(Path(root).resolve()==ROOT,'source_unavailable')
        need(source_commit is None or(type(source_commit)is str and OID.fullmatch(source_commit)),'unsupported_source_commit')
        with original_clock(clock):
            own=capture(Path(__file__),100000,clock);raw=capture(ROOT/POLICY,MAX_POLICY,clock);d=policy(raw);fixed=foundations(d,clock)
            # Baseline copied names/grants are inherited exactly, never recycled.
            v4=parse(fixed['eval/dependencies/source-snapshot-additions-v4.json']);need(v4['project_files']==d['legacy_v4_names'],'foundation_changed')
            payload=canonical({'root':str(ROOT),'source':base64.b64encode(fixed['tools/source_release_policy_v4.py']).decode()})
            baseline=_run_baseline(BASELINE_PROGRAM,payload,clock)
            need(type(baseline)is dict and baseline.get('profile')=='source-copy-additions/v4'and baseline.get('status')=='SOURCE_COPY_PROFILE_SATISFIED'and baseline.get('pass')is True and baseline.get('source_copy_profile_satisfied')is True
              and baseline.get('source_commit')==Q and baseline.get('source_tree')==Q_TREE and type(baseline.get('files'))is int and baseline['files']==Q_FILES
              and type(baseline.get('source_bytes'))is int and baseline['source_bytes']==Q_BYTES and baseline.get('method_sha256')==V4_SHA
              and baseline.get('policy_sha256')==V4_POLICY_SHA and baseline.get('inspected_body_charge')==BASELINE_RESERVATION
              and all(baseline.get(k)is False for k in FALSE_CLAIMS),'foundation_changed')
            run=worker(fixed['scripts/worker_process.py']);git=git_reader(run,clock);head=git(['rev-parse','HEAD^{commit}'],100).decode().strip();commit=head if source_commit is None else source_commit
            need(type(commit)is str and OID.fullmatch(commit),'unsupported_source_commit');git(['merge-base','--is-ancestor',Q,commit],100)
            need(git(['rev-parse',Q+'^{tree}'],100).decode().strip()==Q_TREE,'source_changed')
            qrows,total=tree_rows(git(['ls-tree','-r','-l','-z','--full-tree',Q]));need(len(qrows)==Q_FILES and total==Q_BYTES,'source_changed')
            observed,total=tree_rows(git(['ls-tree','-r','-l','-z','--full-tree',commit]));bodies=Bodies(git,clock);facts=classify(d,qrows,observed,bodies.read,clock,bodies.charge)
            tree=git(['rev-parse',commit+'^{tree}'],100).decode().strip();need(OID.fullmatch(tree),'source_changed');need(git(['rev-parse','HEAD^{commit}'],100).decode().strip()==head,'source_changed')
            need(capture(Path(__file__),100000,clock)==own and capture(ROOT/POLICY,MAX_POLICY,clock)==raw,'source_changed')
            for name,value in fixed.items():need(capture(ROOT/name,len(value),clock)==value,'source_changed')
            clock.now();result.update({'pass':True,'status':'SOURCE_COPY_PROFILE_SATISFIED','source_copy_profile_satisfied':True,'source_commit':commit,'source_tree':tree,'checkout_commit':head,
              'method_sha256':sha(own),'policy_sha256':POLICY_SHA256,'protected_baseline_commit':Q,'baseline_v4_verified':True,'baseline_cleanup_acknowledged':True,
              'selected_profile_base_is_protected_release':True,'selected_source_protected_release_claimed':commit==Q,'inspected_body_charge':bodies.used,**facts})
    except (Exception,KeyboardInterrupt)as error:result['reason']=getattr(error,'code','unavailable')if getattr(error,'code','unavailable')in CODES else 'unavailable'
    return result


def verify(root=ROOT,source_commit=None):
    try:return _verify(root,source_commit,Clock())
    except(Exception,KeyboardInterrupt)as error:return {'profile':PROFILE,'pass':False,'status':'UNAVAILABLE','reason':getattr(error,'code','unavailable'),'source_copy_profile_satisfied':False,**{k:False for k in FALSE_CLAIMS}}


def _verify_archive(raw,source_commit,clock):
    result={'profile':'source-copy-archive-obligations/v5','pass':False,'status':'UNAVAILABLE','source_copy_profile_satisfied':False,'trusted_git_bytes_matched':False,'signature_verified':False,**{k:False for k in FALSE_CLAIMS}}
    try:
        need(type(raw)is bytes and 0<len(raw)<=MAX_ARCHIVE and type(source_commit)is str and OID.fullmatch(source_commit),'invalid_request')
        start=clock.start;limits=(clock.work,clock.end)
        try:
            clock.work=start+25;clock.end=start+30;rights=_verify(ROOT,source_commit,clock)
        finally:clock.work,clock.end=limits
        need(rights['pass'],rights.get('reason','unavailable'));clock.now()
        method=capture(Path(__file__),100000,clock);need(sha(method)==rights['method_sha256'],'source_changed');table=capture(ROOT/POLICY,MAX_POLICY,clock);d=policy(table);fixed=foundations(d,clock)
        summary=_binding_call(fixed['tools/source_snapshot_binding.py'],raw,source_commit,clock);value=parse(summary)
        keys(value,('profile','pass','source_commit','source_tree','source_files','source_bytes','archive_sha256','trusted_git_bytes_matched','signature_verified','rights_approved','release_authorized'))
        need(value.get('profile')=='source-snapshot-trusted-git-binding/v1'and value.get('pass')is True and value.get('source_commit')==source_commit and value.get('source_tree')==rights['source_tree']
          and type(value.get('source_files'))is int and value['source_files']==rights['files'] and type(value.get('source_bytes'))is int and value['source_bytes']==rights['source_bytes']
          and value.get('archive_sha256')==sha(raw)and value.get('trusted_git_bytes_matched')is True and all(value.get(k)is False for k in('signature_verified','rights_approved','release_authorized')),'archive_refused')
        need(capture(Path(__file__),100000,clock)==method and capture(ROOT/POLICY,MAX_POLICY,clock)==table,'source_changed')
        for name,b in fixed.items():need(capture(ROOT/name,len(b),clock)==b,'source_changed')
        clock.now();result.update({'pass':True,'status':'COPY_OBLIGATIONS_AND_GIT_BYTES_BOUND','source_copy_profile_satisfied':True,'trusted_git_bytes_matched':True,
          'source_commit':source_commit,'source_tree':rights['source_tree'],'source_files':rights['files'],'source_bytes':rights['source_bytes'],
          'archive_sha256':sha(raw),'archive_bytes':len(raw),'method_sha256':rights['method_sha256'],'policy_sha256':POLICY_SHA256,'binding_method_sha256':sha(fixed['tools/source_snapshot_binding.py'])})
    except (Exception,KeyboardInterrupt)as error:result['reason']=getattr(error,'code','archive_refused')if getattr(error,'code','archive_refused')in CODES else 'archive_refused'
    return result

def _binding_call(source,raw,source_commit,clock):
    clock.now();need(sha(source)==FOUNDATION_PINS['tools/source_snapshot_binding.py']['sha256'],'foundation_changed')
    env={'__name__':'_captured_source_binding','__file__':str(ROOT/'tools/source_snapshot_binding.py')}
    exec(compile(source,'<captured-source-binding>','exec'),env)
    program='exec(compile('+repr(source)+", '<captured-source-binding>', 'exec'), "+repr({'__name__':'__main__','__file__':str(ROOT/'tools/source_snapshot_binding.py')})+')'
    # Bound the joined parent + binder child + its fixed read-only Git worker,
    # including both pipe/selector sets; never rely on the last leaf capture.
    clock.now();spawn_room()
    with original_clock(clock):
        summary=env['_capture']([sys.executable,'-I','-S','-B','-c',program,'--binding-worker',str(ROOT),source_commit],raw,min(clock.work,clock.now()+60),4096,new_session=True)
        clock.now()
    clock.now();return summary

def verify_archive(raw,*,source_commit):
    try:return _verify_archive(raw,source_commit,Clock(95))
    except(Exception,KeyboardInterrupt)as error:return {'profile':'source-copy-archive-obligations/v5','pass':False,'status':'UNAVAILABLE','reason':getattr(error,'code','unavailable'),'source_copy_profile_satisfied':False,'trusted_git_bytes_matched':False,'signature_verified':False,**{k:False for k in FALSE_CLAIMS}}

class Parser(argparse.ArgumentParser):
    def error(self,message):raise Refused('invalid_request')

def main(argv=None):
    try:
        p=Parser(description=__doc__);p.add_argument('--source-commit');p.add_argument('--archive',type=Path);a=p.parse_args(argv)
        if a.archive is None:r=verify(source_commit=a.source_commit)
        else:
            need(a.source_commit is not None,'invalid_request');clock=Clock(95);raw=capture(a.archive,MAX_ARCHIVE,clock);r=_verify_archive(raw,a.source_commit,clock)
    except(Exception,KeyboardInterrupt)as e:r={'profile':PROFILE,'pass':False,'status':'UNAVAILABLE','reason':getattr(e,'code','unavailable'),**{k:False for k in FALSE_CLAIMS}}
    print(json.dumps(r,sort_keys=True));return 0 if r['pass']else 2
if __name__=='__main__':raise SystemExit(main())
