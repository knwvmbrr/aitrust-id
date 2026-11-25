"""Finite protected7ab source-copy successor; no runtime, accuracy or legal approval.

SPDX-License-Identifier: Apache-2.0
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import sys
import threading
import time
import types

ROOT=Path(__file__).resolve().parents[1]
PROFILE='source-copy-additions/v6'
POLICY='eval/dependencies/source-snapshot-additions-v6.json'
POLICY_SHA256='0df291bd1011b9866983c51f7cd5f310e13d1a3fb82e0df7f8217cc5bd1bb430'
BASELINE='7ab4d3036f6409ec72d6a23972a563fd81e0f416'
BASELINE_TREE='7f112209124a1608a287895280fe2e0195d2f515'
BASELINE_FILES,BASELINE_BYTES=13946,153744932
BASELINE_RESERVATION=40_242_180
V5_METHOD_SHA='737b1eb4c92ced709695aed80c13b7790b7e2e51183bd21416707b37a08a56bc'
V5_POLICY_SHA='bed27448c456186eded268ef30c9b4cef6205d554f901586720bb107122fd134'
MAX_FILES,MAX_TOTAL,MAX_ARCHIVE=16384,256_000_000,64_000_000
MAX_PROJECT,MAX_POLICY,MAX_BODY,MAX_INSPECTED,MAX_FDS=160,1_000_000,2_000_000,64_000_000,80
MAX_METHOD=65_536
OID=re.compile('[a-f0-9]{40}')
SHA=re.compile('[a-f0-9]{64}')
MARKERS=re.compile(r'^\s*(?:[#/*;]+\s*)?(?:SPDX-License-Identifier:.*|Copyright\b.*|Licensed under\b.*)$',re.I|re.M)
FALSE_CLAIMS=('legal_clearance','compiled_runtime_permission','source_archive_admitted','release_authorized','accuracy','complete_F057_X02')
CODES=frozenset({'invalid_request','foundation_changed','policy_changed','invalid_profile','source_unavailable','source_changed','resource_limit','git_unavailable','unknown_path','missing_path','grant_changed','grant_unavailable','third_party_or_asset_changed','license_declaration_changed','unsupported_source_commit','unsupported_git_entry','unsupported_first_party_text','archive_refused','deadline','cleanup_unconfirmed','unavailable'})
FOUNDATION_PINS={'tools/source_release_policy.py': {'mode': '100644', 'git_blob_oid': 'b97601876dd182d298944d11816cdb07c296f1fe', 'bytes': 17412, 'sha256': '897d287a1dc91c441db54237b0b80dfe634521ecc6b644944d04a63623b591b6'}, 'tools/source_release_policy_v2.py': {'mode': '100644', 'git_blob_oid': '0353dfd270ff31353455c2b154b909b4a5bad2e6', 'bytes': 22383, 'sha256': '6642ab4ec688754ed5234027bdf029fd2a100b77d262fc98b958e1aed7c7126c'}, 'tools/source_release_policy_v3.py': {'mode': '100644', 'git_blob_oid': 'cd3183ed19f8ecd7f11808380c06265eb2c94f80', 'bytes': 24924, 'sha256': '26a6bb8be66cab5a355bfbe6fcfbd16cefe994d1e7ade8b26b3cd227f0f82d41'}, 'tools/source_release_policy_v4.py': {'mode': '100644', 'git_blob_oid': 'b609d81bd2ca00ef925fc0d6ced4e66a3c6289ef', 'bytes': 24893, 'sha256': '0e70d9f360533dbd13f67192b967e8831787fce381c220bc013fc8a7eaa0989e'}, 'eval/dependencies/source-snapshot-release.json': {'mode': '100644', 'git_blob_oid': '76153604af07df009b857ada090c3449d390a488', 'bytes': 3049927, 'sha256': '2e555a5dc31a9d92b0982a9dba1fefea9376a45bb0d4c99625332b59965c6645'}, 'eval/dependencies/source-snapshot-release-v2.json': {'mode': '100644', 'git_blob_oid': 'ea2c7c5dce0510b4248cfe81b6ac93150d6b5204', 'bytes': 410005, 'sha256': '2c6bc3c14c8825f8fdd583e42adb1df39e7983ee6f2bac96004231a3dbd6543d'}, 'eval/dependencies/source-snapshot-additions-v3.json': {'mode': '100644', 'git_blob_oid': 'e5ba152d50922057f255b22a96a83062f661d655', 'bytes': 142724, 'sha256': '3bd727fef18736bcd259fa4f1e21fd25fa8629f361b25289dc0016f48394db3e'}, 'eval/dependencies/source-snapshot-additions-v4.json': {'mode': '100644', 'git_blob_oid': 'c21ffaaf9f11666c9db504665f4ab4eb6b1c32fa', 'bytes': 49133, 'sha256': 'da42db15f4fdb9b17784344fb5c7381bbd7e2d257b7a01f4b18fc88678c9db8c'}, 'tools/source_snapshot_binding.py': {'mode': '100644', 'git_blob_oid': 'fe41b0cb7247c97e3723af126c72e2fe0a6a77c3', 'bytes': 14697, 'sha256': 'c219f326861c2634e930d7c0b74c0abad9859b3abe746a77464ece5ba8fceffb'}, 'scripts/worker_process.py': {'mode': '100644', 'git_blob_oid': '2f3164958b6a04768a57c3f5367c6b4b1b5da18f', 'bytes': 3483, 'sha256': '9411406936c9757a67306211a695cbe54c0e318ca1d7e6c9229d24103baeb7a3'}, 'tools/dependency_policy.py': {'mode': '100644', 'git_blob_oid': 'd202aa40abee220e608f98eba903d4bf004419ea', 'bytes': 15682, 'sha256': 'e72e478a7508e6c3e6e000803ee4d583900f626cc219870fd1ad140131608408'}, 'tools/source_release_policy_v5.py': {'mode': '100644', 'git_blob_oid': '08eaf0fcce36e472f88fa962a68f16222871edf2', 'bytes': 32927, 'sha256': '737b1eb4c92ced709695aed80c13b7790b7e2e51183bd21416707b37a08a56bc'}, 'eval/dependencies/source-snapshot-additions-v5.json': {'mode': '100644', 'git_blob_oid': '340a8d610c1bc2c4067d1ce3846ffdade81c0cc0', 'bytes': 63488, 'sha256': 'bed27448c456186eded268ef30c9b4cef6205d554f901586720bb107122fd134'}}

class Refused(ValueError):
    def __init__(self, code='unavailable', *, cleanup_complete=False):
        self.code = code if code in CODES else 'unavailable'
        self.cleanup_complete = cleanup_complete
        super().__init__('Source-copy V6 unavailable.')

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

def markers(raw):
    need(type(raw)is bytes and b'\0'not in raw,'unsupported_first_party_text');text=raw.decode('utf8','strict');lines=MARKERS.findall(text)
    return sha('\n'.join(x.strip()for x in lines).encode()),lines

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


def policy(raw):
    need(sha(raw)==POLICY_SHA256,'policy_changed');d=parse(raw)
    keys(d,('profile','protected_baseline','protected_baseline_tree','baseline_files','baseline_bytes',
        'foundations','legacy_v4_names','legacy_v5_project_names','legacy_v5_copied_files',
        'baseline_read_reservation','project_files','maintained_project_files','project_limits','claims','source_observation'))
    need(d['profile']==PROFILE and d['protected_baseline']==BASELINE and d['protected_baseline_tree']==BASELINE_TREE,'foundation_changed')
    need(type(d['baseline_files'])is int and d['baseline_files']==BASELINE_FILES
      and type(d['baseline_bytes'])is int and d['baseline_bytes']==BASELINE_BYTES,'foundation_changed')
    need(d['foundations']==FOUNDATION_PINS and d['baseline_read_reservation']=={'inspected_body_charge':BASELINE_RESERVATION},'foundation_changed')
    project=d['project_files'];owned=d['maintained_project_files'];limits=d['project_limits']
    need(type(project)is list and project==sorted(set(project)) and 0<len(project)<=MAX_PROJECT,'resource_limit')
    need(type(owned)is list and owned==sorted(set(owned)) and set(owned)<=set(project),'invalid_profile')
    need(type(limits)is dict and set(limits)==set(project),'invalid_profile')
    for name in project:
        path_name(name);need(type(limits[name])is int and 0<limits[name]<=MAX_BODY,'resource_limit')
    need(not set(project)&set(FOUNDATION_PINS),'foundation_changed')
    keys(d['claims'],FALSE_CLAIMS);need(all(x is False for x in d['claims'].values()),'invalid_profile')
    keys(d['source_observation'],('selected_source_is_protected','actual_candidate_verified'))
    need(all(x is False for x in d['source_observation'].values()),'invalid_profile')
    return d


def metadata_maintenance_eligibility(fixed):
    # A single existing project role, not general V1 maintenance authority.
    expected=['services/anonymizer/replay_metadata.py','100644',
      '8a0fe8cad90eee3fd4cc73ba090fc5d7fe9ac6a1',1786,'project-text',
      'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855']
    legacy=parse(fixed['eval/dependencies/source-snapshot-release.json'])
    need(type(legacy)is dict and type(legacy.get('files'))is list,'grant_unavailable')
    matches=[row for row in legacy['files'] if type(row)is list and row and row[0]==expected[0]]
    need(matches==[expected],'grant_unavailable')
    return {expected[0]}


def captured_v5(data,clock):
    fixed={}
    for name,row in FOUNDATION_PINS.items():
        clock.now();raw=capture(ROOT/name,row['bytes'],clock)
        need(len(raw)==row['bytes']and sha(raw)==row['sha256'],'foundation_changed');fixed[name]=raw
    ns=types.ModuleType('_captured_protected7ab_source_copy_v5');ns.__file__=str(ROOT/'tools/source_release_policy_v5.py')
    exec(compile(fixed['tools/source_release_policy_v5.py'],'<captured-protected7ab-source-copy-v5>','exec'),ns.__dict__)
    need(ns.ROOT==ROOT and ns.POLICY_SHA256==V5_POLICY_SHA and ns.MAX_INSPECTED==MAX_INSPECTED
      and ns.MAX_FDS==MAX_FDS and ns.MAX_FILES==MAX_FILES and ns.MAX_TOTAL==MAX_TOTAL,'foundation_changed')
    prior=parse(fixed['eval/dependencies/source-snapshot-additions-v5.json'])
    need(data['legacy_v4_names']==prior['legacy_v4_names']and len(data['legacy_v4_names'])==159,'foundation_changed')
    need(data['legacy_v5_project_names']==prior['project_files']and len(prior['project_files'])==139,'foundation_changed')
    need(data['legacy_v5_copied_files']==prior['copied_files']and len(prior['copied_files'])==1
      and sum(x['authored_capacity_charge']for x in prior['copied_files'])==1
      and len(prior['copied_files'][0]['anchors'])==95,'foundation_changed')
    eligible=set(prior['project_files'])|set(prior['legacy_v4_names'])|metadata_maintenance_eligibility(fixed)
    need(set(data['maintained_project_files'])<=eligible,'grant_unavailable')
    copied={x['path']for x in prior['copied_files']}|set(prior['copied_files'][0]['anchors'])
    need(not set(data['project_files'])&copied,'third_party_or_asset_changed')
    return ns,fixed


def baseline(v5,clock):
    # Existing private V5 API already accepts its archive's cumulative Clock.
    # The same internal object crosses this boundary; no new timer allowance.
    original=(clock.start,clock.work,clock.end);clock.now()
    value=v5._verify(ROOT,BASELINE,clock)
    need((clock.start,clock.work,clock.end)==original,'deadline');clock.now()
    need(type(value)is dict and value.get('profile')=='source-copy-additions/v5'
      and value.get('pass')is True and value.get('status')=='SOURCE_COPY_PROFILE_SATISFIED'
      and value.get('source_copy_profile_satisfied')is True,'foundation_changed')
    need(value.get('source_commit')==BASELINE and value.get('source_tree')==BASELINE_TREE
      and type(value.get('files'))is int and value['files']==BASELINE_FILES
      and type(value.get('source_bytes'))is int and value['source_bytes']==BASELINE_BYTES,'foundation_changed')
    need(value.get('method_sha256')==V5_METHOD_SHA and value.get('policy_sha256')==V5_POLICY_SHA
      and value.get('baseline_v4_verified')is True and value.get('baseline_cleanup_acknowledged')is True
      and type(value.get('inspected_body_charge'))is int and value['inspected_body_charge']==BASELINE_RESERVATION
      and all(value.get(k)is False for k in FALSE_CLAIMS),'foundation_changed')
    return value


def classify(data,base,observed,read,clock):
    project=set(data['project_files']);maintained=set(data['maintained_project_files'])
    need(len(project)==len(data['project_files'])and 0<len(project)<=MAX_PROJECT,'resource_limit')
    need(0<len(observed)<=MAX_FILES,'resource_limit');total=0
    for row in observed.values():
        need(type(row)in(tuple,list)and len(row)==3 and row[0]in('100644','100755')
          and type(row[1])is str and OID.fullmatch(row[1])and type(row[2])is int
          and 0<=row[2]<=32_000_000,'unsupported_git_entry')
        total+=row[2];need(total<=MAX_TOTAL,'resource_limit')
    # Complete denominator before any body read: nothing is hidden by a filter.
    need(observed.keys()<=base.keys()|project,'unknown_path');need(base.keys()<=observed.keys(),'missing_path')
    for name in data['foundations']:
        need(name in base and observed.get(name)==base[name],'foundation_changed')
    for copied in data['legacy_v5_copied_files']:
        for name in {copied['path'],*copied['anchors']}:
            need(name in base and observed.get(name)==base[name],'grant_changed')
    allowed={'SPDX-License-Identifier: Apache-2.0','Licensed under the Apache License, Version 2.0.',
        'Copyright 2026 Michael Raashad McGuire and AITrust-ID contributors.'}
    changed=introduced=0
    for name,row in observed.items():
        clock.now()
        if name in base and row==base[name]:continue
        need(name in project,'third_party_or_asset_changed')
        need(row[2]<=data['project_limits'][name],'resource_limit')
        raw=read(row);marker,lines=markers(raw)
        if name in base:
            need(name in maintained,'third_party_or_asset_changed')
            need(marker==markers(read(base[name]))[0],'license_declaration_changed');changed+=1
        else:
            need(all(x.strip().lstrip('#/*; ').rstrip('*/ ').strip()in allowed for x in lines),'license_declaration_changed');introduced+=1
    return {'files':len(observed),'source_bytes':total,'changed_named_project_text_files':changed,
      'introduced_named_project_text_files':introduced,'selected_delta_capacity':len(project),
      'inherited_v5_authored_charge':140,'inherited_v4_names':159,'inherited_copied_anchors':95}


def _verify(root,source_commit,clock):
    result={'profile':PROFILE,'pass':False,'status':'UNAVAILABLE','source_copy_profile_satisfied':False,**{k:False for k in FALSE_CLAIMS}}
    try:
        need(Path(root).resolve()==ROOT,'source_unavailable')
        need(source_commit is None or(type(source_commit)is str and OID.fullmatch(source_commit)),'unsupported_source_commit')
        with original_clock(clock):
            own=capture(Path(__file__),MAX_METHOD,clock);raw=capture(ROOT/POLICY,MAX_POLICY,clock);d=policy(raw);v5,fixed=captured_v5(d,clock)
        # No parent alarm is stacked over V5's existing alarm; elapsed time and
        # the absolute work/end deadlines remain in this ONE original object.
        baseline(v5,clock)
        with original_clock(clock):
            run=v5.worker(fixed['scripts/worker_process.py']);git=v5.git_reader(run,clock)
            head=git(['rev-parse','HEAD^{commit}'],100).decode().strip();commit=head if source_commit is None else source_commit
            need(type(commit)is str and OID.fullmatch(commit),'unsupported_source_commit')
            git(['merge-base','--is-ancestor',BASELINE,commit],100)
            need(git(['rev-parse',BASELINE+'^{tree}'],100).decode().strip()==BASELINE_TREE,'source_changed')
            before,total=v5.tree_rows(git(['ls-tree','-r','-l','-z','--full-tree',BASELINE]))
            need(len(before)==BASELINE_FILES and total==BASELINE_BYTES,'source_changed')
            observed,total=v5.tree_rows(git(['ls-tree','-r','-l','-z','--full-tree',commit]));bodies=Bodies(git,clock,reserved=BASELINE_RESERVATION)
            facts=classify(d,before,observed,bodies.read,clock)
            tree=git(['rev-parse',commit+'^{tree}'],100).decode().strip();need(OID.fullmatch(tree),'source_changed')
            need(git(['rev-parse','HEAD^{commit}'],100).decode().strip()==head,'source_changed')
            need(capture(Path(__file__),MAX_METHOD,clock)==own and capture(ROOT/POLICY,MAX_POLICY,clock)==raw,'source_changed')
            for name,value in fixed.items():need(capture(ROOT/name,len(value),clock)==value,'source_changed')
            clock.now();result.update({'pass':True,'status':'SOURCE_COPY_PROFILE_SATISFIED','source_copy_profile_satisfied':True,
                'source_commit':commit,'source_tree':tree,'checkout_commit':head,'method_sha256':sha(own),'policy_sha256':POLICY_SHA256,
                'protected_baseline_commit':BASELINE,'baseline_v5_verified':True,'baseline_cleanup_acknowledged':True,
                'selected_profile_base_is_protected_release':True,'selected_source_protected_release_claimed':commit==BASELINE,
                'inspected_body_charge':bodies.used,**facts})
    except (Exception,KeyboardInterrupt)as error:
        code=getattr(error,'code','unavailable');result['reason']=code if code in CODES else'unavailable'
    return result


def verify(root=ROOT,source_commit=None):
    try:return _verify(root,source_commit,Clock())
    except(Exception,KeyboardInterrupt)as error:
        return {'profile':PROFILE,'pass':False,'status':'UNAVAILABLE','source_copy_profile_satisfied':False,
            'reason':getattr(error,'code','unavailable')if getattr(error,'code','unavailable')in CODES else'unavailable',**{k:False for k in FALSE_CLAIMS}}


def _verify_archive(raw,source_commit,clock):
    result={'profile':'source-copy-archive-obligations/v6','pass':False,'status':'UNAVAILABLE',
        'source_copy_profile_satisfied':False,'trusted_git_bytes_matched':False,'signature_verified':False,**{k:False for k in FALSE_CLAIMS}}
    try:
        need(type(raw)is bytes and 0<len(raw)<=MAX_ARCHIVE and type(source_commit)is str and OID.fullmatch(source_commit),'invalid_request')
        limits=clock.work,clock.end
        try:
            clock.work=clock.start+25;clock.end=clock.start+30;rights=_verify(ROOT,source_commit,clock)
        finally:clock.work,clock.end=limits
        need(rights['pass'],rights.get('reason','unavailable'));clock.now()
        with original_clock(clock):
            method=capture(Path(__file__),MAX_METHOD,clock);table=capture(ROOT/POLICY,MAX_POLICY,clock);d=policy(table);v5,fixed=captured_v5(d,clock)
            need(sha(method)==rights['method_sha256'] and sha(table)==rights['policy_sha256'],'source_changed')
        summary=v5._binding_call(fixed['tools/source_snapshot_binding.py'],raw,source_commit,clock);value=parse(summary)
        keys(value,('profile','pass','source_commit','source_tree','source_files','source_bytes','archive_sha256',
            'trusted_git_bytes_matched','signature_verified','rights_approved','release_authorized'))
        need(value.get('profile')=='source-snapshot-trusted-git-binding/v1'and value.get('pass')is True
          and value.get('source_commit')==source_commit and value.get('source_tree')==rights['source_tree']
          and type(value.get('source_files'))is int and value['source_files']==rights['files']
          and type(value.get('source_bytes'))is int and value['source_bytes']==rights['source_bytes']
          and value.get('archive_sha256')==sha(raw)and value.get('trusted_git_bytes_matched')is True
          and all(value.get(k)is False for k in('signature_verified','rights_approved','release_authorized')),'archive_refused')
        with original_clock(clock):
            need(capture(Path(__file__),MAX_METHOD,clock)==method and capture(ROOT/POLICY,MAX_POLICY,clock)==table,'source_changed')
            for name,body in fixed.items():need(capture(ROOT/name,len(body),clock)==body,'source_changed')
        result.update({'pass':True,'status':'COPY_OBLIGATIONS_AND_GIT_BYTES_BOUND','source_copy_profile_satisfied':True,
            'trusted_git_bytes_matched':True,'source_commit':source_commit,'source_tree':rights['source_tree'],
            'source_files':rights['files'],'source_bytes':rights['source_bytes'],'archive_sha256':sha(raw),
            'archive_bytes':len(raw),'method_sha256':rights['method_sha256'],'policy_sha256':POLICY_SHA256,
            'binding_method_sha256':sha(fixed['tools/source_snapshot_binding.py'])})
    except(Exception,KeyboardInterrupt)as error:
        code=getattr(error,'code','archive_refused');result['reason']=code if code in CODES else'archive_refused'
    return result


def verify_archive(raw,*,source_commit):
    try:return _verify_archive(raw,source_commit,Clock(95))
    except(Exception,KeyboardInterrupt)as error:
        return {'profile':'source-copy-archive-obligations/v6','pass':False,'status':'UNAVAILABLE',
            'reason':getattr(error,'code','unavailable')if getattr(error,'code','unavailable')in CODES else'unavailable',
            'source_copy_profile_satisfied':False,'trusted_git_bytes_matched':False,'signature_verified':False,**{k:False for k in FALSE_CLAIMS}}


class Parser(argparse.ArgumentParser):
    def error(self,message):raise Refused('invalid_request')


def main(argv=None):
    try:
        parser=Parser(description=__doc__);parser.add_argument('--source-commit');parser.add_argument('--archive')
        a=parser.parse_args(argv)
        if a.archive:
            need(a.source_commit is not None);clock=Clock(95);raw=capture(Path(a.archive),MAX_ARCHIVE,clock)
            result=_verify_archive(raw,a.source_commit,clock)
        else:result=verify(source_commit=a.source_commit)
    except(Exception,KeyboardInterrupt)as error:
        code=getattr(error,'code','unavailable');result={'profile':PROFILE,'pass':False,'status':'UNAVAILABLE',
            'reason':code if code in CODES else'unavailable','source_copy_profile_satisfied':False,**{k:False for k in FALSE_CLAIMS}}
    print(json.dumps(result,sort_keys=True));return 0 if result['pass']else 2


if __name__=='__main__':raise SystemExit(main())
