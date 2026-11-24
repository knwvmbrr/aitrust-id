"""Finite Q-based source-copy extension; no archive authenticity or route approval.

SPDX-License-Identifier: Apache-2.0
"""
import argparse
import builtins
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import threading
import time
import types

ROOT=Path(__file__).resolve().parents[1]
PROFILE='source-copy-additions/v4'
POLICY='eval/dependencies/source-snapshot-additions-v4.json'
POLICY_SHA256='6b2ea3a3734f44a678753566a48470a4a2c7df7cc37ad5271be780ef9a2c00fd'
Q='9c98ac5000a2784df66d8e1f5bf17d34cb0f53b7'
Q_TREE='d5ad815a57ff55a49569c1dbce20c77f3420b3ed'
Q_FILES,Q_BYTES=13747,147265706
V3_METHOD='26a6bb8be66cab5a355bfbe6fcfbd16cefe994d1e7ade8b26b3cd227f0f82d41'
V3_POLICY='3bd727fef18736bcd259fa4f1e21fd25fa8629f361b25289dc0016f48394db3e'
MAX_FILES,MAX_TOTAL,MAX_ARCHIVE=16384,256_000_000,64_000_000
MAX_POLICY,MAX_PROJECT,MAX_COPIED=1_000_000,160,256
MAX_BODY,MAX_INSPECTED=2_000_000,64_000_000
OID=re.compile('[a-f0-9]{40}');SHA=re.compile('[a-f0-9]{64}')
FOUNDATION_PATHS=frozenset({'tools/source_release_policy.py','tools/source_release_policy_v2.py','tools/source_release_policy_v3.py','eval/dependencies/source-snapshot-release.json','eval/dependencies/source-snapshot-release-v2.json','eval/dependencies/source-snapshot-additions-v3.json','tools/source_snapshot_binding.py','scripts/worker_process.py'})
CODES=frozenset({'invalid_request','foundation_changed','policy_changed','invalid_profile','source_unavailable','source_changed','resource_limit','git_unavailable','unknown_path','missing_path','grant_changed','grant_unavailable','third_party_or_asset_changed','license_declaration_changed','unsupported_source_commit','unsupported_git_entry','unsupported_first_party_text','archive_refused','deadline','unavailable'})
FALSE_CLAIMS=('legal_clearance','compiled_runtime_permission','source_archive_admitted','release_authorized','accuracy','complete_F057_X02')


class Refused(ValueError):
    def __init__(self,code='unavailable'):
        self.code=code if code in CODES else 'unavailable';super().__init__('Source-copy V4 unavailable.')


def need(value,code='invalid_profile'):
    if not value:raise Refused(code)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False,separators=(',',':')).encode()


def captured_v3():
    # Do not import/reuse a cached repository module or change any legacy global.
    import os
    path=ROOT/'tools/source_release_policy_v3.py'
    need(not path.is_symlink()and not any(p.is_symlink()for p in path.parents),'source_unavailable')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd);need(stat.S_ISREG(before.st_mode)and before.st_nlink==1 and before.st_size==24924,'foundation_changed')
        raw=bytearray()
        while len(raw)<before.st_size:
            b=os.read(fd,min(65536,before.st_size-len(raw)));need(b,'source_changed');raw.extend(b)
        after=os.fstat(fd);named=path.lstat()
        key=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        need(key(before)==key(after)==key(named),'source_changed')
    finally:os.close(fd)
    raw=bytes(raw);need(sha(raw)==V3_METHOD,'foundation_changed')
    original=builtins.__import__
    def standard(name,globals=None,locals=None,fromlist=(),level=0):
        need(level==0 and name in {'argparse','builtins','hashlib','json','os','pathlib','re','stat','subprocess','sys','time','types'},'foundation_changed')
        return original(name,globals,locals,fromlist,level)
    ns={'__name__':'_captured_immutable_source_copy_v3','__file__':str(path),
        '__builtins__':{**vars(builtins),'__import__':standard}}
    exec(compile(raw,'<captured-source-copy-v3>','exec'),ns)
    return types.SimpleNamespace(**ns),raw


@contextmanager
def original_clock(deadline):
    need(threading.current_thread()is threading.main_thread()and threading.active_count()==1
      and hasattr(signal,'SIGALRM')and signal.getitimer(signal.ITIMER_REAL)==(0.0,0.0),'source_unavailable')
    old=signal.getsignal(signal.SIGALRM)
    def expired(*unused):raise Refused('deadline')
    try:
        signal.signal(signal.SIGALRM,expired)
        signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.monotonic()))
        yield
    finally:
        # Setup may fail after changing state; try both independent restorations.
        try:signal.setitimer(signal.ITIMER_REAL,0)
        finally:signal.signal(signal.SIGALRM,old)


def keys(value,names):need(type(value)is dict and set(value)==set(names))


def policy(raw,v3,v2,base,legacy_names,qrows,owned):
    need(sha(raw)==POLICY_SHA256,'policy_changed');d=v2.parse(raw)
    keys(d,('profile','protected_q','protected_q_tree','q_files','q_bytes','foundations','legacy_v3_names','source_observation','baseline_read_reservation','project_files','copied_files','origins','metadata_transitions','claims'))
    need(d['profile']==PROFILE and d['protected_q']==Q and d['protected_q_tree']==Q_TREE
      and type(d['q_files'])is int and d['q_files']==Q_FILES and type(d['q_bytes'])is int and d['q_bytes']==Q_BYTES)
    need(d['legacy_v3_names']==legacy_names and len(legacy_names)==155,'foundation_changed')
    keys(d['foundations'],FOUNDATION_PATHS)
    fixed={'tools/source_release_policy_v3.py':V3_METHOD,'eval/dependencies/source-snapshot-additions-v3.json':V3_POLICY,
      'tools/source_release_policy_v2.py':v3.V2_METHOD_SHA256,'eval/dependencies/source-snapshot-release-v2.json':v3.V2_POLICY_SHA256,
      'tools/source_release_policy.py':v2.LEGACY_HELPER_SHA256,'eval/dependencies/source-snapshot-release.json':v2.LEGACY_SHA256,
      'tools/source_snapshot_binding.py':v2.BINDING_SHA256,'scripts/worker_process.py':v2.WORKER_SHA256}
    need(all(d['foundations'][name].get('sha256')==value for name,value in fixed.items()),'foundation_changed')
    for value in d['foundations'].values():
        keys(value,('bytes','sha256'));need(type(value['bytes'])is int and 0<value['bytes']<=12_000_000 and type(value['sha256'])is str and SHA.fullmatch(value['sha256']))
    keys(d['baseline_read_reservation'],('unique_oids','bytes','readset_sha256'))
    need(type(d['baseline_read_reservation']['unique_oids'])is int and type(d['baseline_read_reservation']['bytes'])is int
      and type(d['baseline_read_reservation']['readset_sha256'])is str and SHA.fullmatch(d['baseline_read_reservation']['readset_sha256']))
    keys(d['claims'],FALSE_CLAIMS);need(all(d['claims'][k]is False for k in FALSE_CLAIMS))
    keys(d['source_observation'],('candidate_commit','candidate_is_protected','actual_candidate_verified'))
    need(type(d['source_observation']['candidate_commit'])is str and OID.fullmatch(d['source_observation']['candidate_commit'])
      and d['source_observation']['candidate_is_protected']is False and d['source_observation']['actual_candidate_verified']is False)
    need(type(d['project_files'])is list and len(d['project_files'])<=MAX_PROJECT
      and len(set(d['project_files']))==len(d['project_files']))
    project=set()
    for name in d['project_files']:
        v2.path_name(name);need(name not in qrows or name in owned,'third_party_or_asset_changed');project.add(name)
    need(type(d['copied_files'])is list and len(d['copied_files'])<=MAX_COPIED and type(d['origins'])is dict and len(d['origins'])<=256)
    copied={};capacity=len(project)
    for row in d['copied_files']:
        keys(row,('path','mode','git_blob_oid','bytes','sha256','grant_group','authored_capacity_charge','container'))
        name=v2.path_name(row['path']);need(name not in qrows and name not in project and name not in legacy_names and name not in copied)
        need(row['mode']in('100644','100755')and type(row['git_blob_oid'])is str and OID.fullmatch(row['git_blob_oid'])
          and type(row['bytes'])is int and 0<=row['bytes']<=MAX_BODY and type(row['sha256'])is str and SHA.fullmatch(row['sha256'])
          and type(row['authored_capacity_charge'])is bool and row['grant_group']in d['origins'])
        capacity+=int(row['authored_capacity_charge']);need(capacity<=MAX_PROJECT,'resource_limit')
        if row['container']is not None:
            keys(row['container'],('format','members'));need(row['container']['format']=='mt-mobile-source-bundle/v1'
              and type(row['container']['members'])is dict and len(row['container']['members'])==15)
            for member,item in row['container']['members'].items():
                v2.path_name(member);keys(item,('bytes','sha256'));need(type(item['bytes'])is int and 0<=item['bytes']<=MAX_BODY and type(item['sha256'])is str and SHA.fullmatch(item['sha256']))
        copied[name]=row
    allowed=qrows.keys()|project|copied.keys()|set(legacy_names)
    for origin in d['origins'].values():
        keys(origin,('scope','conditions','required_anchors','required_cohort','unresolved'))
        need(type(origin['scope'])is str and 0<len(origin['scope'])<=8000 and type(origin['conditions'])is list and len(origin['conditions'])<=32
          and all(type(x)is str and 0<len(x)<=8000 for x in origin['conditions'])
          and type(origin['unresolved'])is list and len(origin['unresolved'])<=32)
        need(type(origin['required_anchors'])is list and 0<len(origin['required_anchors'])<=128)
        seen=set()
        for anchor in origin['required_anchors']:
            keys(anchor,('path','bytes','sha256'));name=v2.path_name(anchor['path'])
            need(name in allowed and name not in seen and type(anchor['bytes'])is int and 0<=anchor['bytes']<=MAX_BODY
              and type(anchor['sha256'])is str and SHA.fullmatch(anchor['sha256']));seen.add(name)
        need(type(origin['required_cohort'])is list and len(origin['required_cohort'])<=128
          and len(set(origin['required_cohort']))==len(origin['required_cohort'])and all(n in copied for n in origin['required_cohort']))
    # No future metadata leaf/producer is silently adopted. Current Q→365 needs no transition.
    need(d['metadata_transitions']==[],'grant_changed')
    return d,project,copied


def baseline_reads(qrows,d2,legacy,base,additions,copied,project):
    reads={}
    def add(oid,size):
        need(oid not in reads or reads[oid]==size,'source_changed');reads[oid]=size
    expected=dict(base)
    for name,row in copied.items():
        if name not in qrows:continue
        add(row['git_blob_oid'],row['bytes'])
        for anchor in additions['origins'][row['origin']]['required_anchors']:
            r=qrows[anchor['path']];add(r[1],r[2])
        expected[name]=(row['mode'],row['git_blob_oid'],row['bytes'],'copy',None)
    transition=additions['metadata_transitions']
    for name in (transition['producer_path'],transition['evidence']['path']):r=qrows[name];add(r[1],r[2])
    for row in transition['rows']:
        for phase in ('old','new'):r=row[phase];add(r['git_blob_oid'],r['bytes'])
        n=row['path'];r=row['new'];expected[n]=(r['mode'],r['git_blob_oid'],r['bytes'],*base[n][3:])
    for name,row in qrows.items():
        if name in project or name not in expected or row!=expected[name][:3]:add(row[1],row[2])
    return reads


class Bodies:
    def __init__(self,git,tick,reserved):
        need(type(reserved)is int and 0<=reserved<=MAX_INSPECTED,'resource_limit')
        self.git=git;self.tick=tick;self.used=reserved;self.cache={}
    def read(self,oid,size):
        self.tick();need(type(size)is int and 0<=size<=MAX_BODY,'resource_limit')
        if oid in self.cache:need(len(self.cache[oid])==size,'source_changed');return self.cache[oid]
        self.used+=size+1;need(self.used<=MAX_INSPECTED,'resource_limit')
        raw=self.git(['cat-file','blob',oid],min(size+1,MAX_BODY));need(len(raw)==size
          and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+raw).hexdigest()==oid,'source_changed')
        self.cache[oid]=raw;return raw


def classify(d,project,copied,qrows,observed,legacy_names,owned,v2,read,tick):
    need(0<len(observed)<=MAX_FILES,'resource_limit');total=0
    for name,row in observed.items():
        v2.path_name(name);need(type(row)in(tuple,list)and len(row)==3 and row[0]in('100644','100755')
          and type(row[1])is str and OID.fullmatch(row[1])and type(row[2])is int and 0<=row[2]<=v2.MAX_FILE,'unsupported_git_entry')
        total+=row[2];need(total<=MAX_TOTAL,'resource_limit')
    # The full denominator is checked before filtering/decoding any path.
    need(observed.keys()<=qrows.keys()|project|copied.keys()|set(legacy_names),'unknown_path')
    need(qrows.keys()<=observed.keys(),'missing_path')
    # No transition facts are selected: old generated metadata requires the exact old producer.
    need(observed['tools/dependency_policy.py']==qrows['tools/dependency_policy.py'],'source_changed')
    allowed={'SPDX-License-Identifier: Apache-2.0','Licensed under the Apache License, Version 2.0.',
             'Copyright 2026 Michael Raashad McGuire and AITrust-ID contributors.'}
    changed=introduced=present=0
    for name,row in observed.items():
        tick()
        if name in qrows and row==qrows[name]:continue
        if name in copied:
            expected=copied[name];need(row==(expected['mode'],expected['git_blob_oid'],expected['bytes']),'third_party_or_asset_changed')
            origin=d['origins'][expected['grant_group']];need(not origin['unresolved'],'grant_unavailable')
            need(set(origin['required_cohort'])<=observed.keys(),'missing_path')
            for anchor in origin['required_anchors']:
                need(anchor['path']in observed,'missing_path');r=observed[anchor['path']]
                need(r[2]==anchor['bytes']and sha(read(r[1],r[2]))==anchor['sha256'],'grant_changed')
            raw=read(row[1],row[2]);need(sha(raw)==expected['sha256'],'source_changed')
            if expected['container']is not None:
                packet=v2.parse(raw);keys(packet,('format','files'));need(packet['format']==expected['container']['format']and type(packet['files'])is dict
                  and packet['files'].keys()==expected['container']['members'].keys(),'source_changed')
                for member,item in expected['container']['members'].items():
                    need(type(packet['files'][member])is str,'source_changed');value=packet['files'][member].encode()
                    need(len(value)==item['bytes']and sha(value)==item['sha256'],'source_changed')
            present+=1;continue
        need(name in project or(name not in qrows and name in legacy_names),'third_party_or_asset_changed')
        raw=read(row[1],row[2]);marker,lines=v2.markers(raw)
        if name in qrows:
            need(name in owned,'third_party_or_asset_changed');old=qrows[name]
            need(marker==v2.markers(read(old[1],old[2]))[0],'license_declaration_changed');changed+=1
        else:
            need(all(line.strip().lstrip('#/*; ').rstrip('*/ ').strip()in allowed for line in lines),'license_declaration_changed');introduced+=1
    return {'files':len(observed),'source_bytes':total,'present_optional_copied_files':present,
            'changed_named_project_text_files':changed,'introduced_named_project_text_files':introduced}


def verify(root=ROOT,source_commit=None):
    result={'profile':PROFILE,'pass':False,'status':'UNAVAILABLE','source_copy_profile_satisfied':False,**{k:False for k in FALSE_CLAIMS}}
    try:
        need(Path(root).resolve()==ROOT,'source_unavailable');deadline=time.monotonic()+30
        with original_clock(deadline):
            def tick():need(time.monotonic()<deadline,'deadline')
            v3,v3raw=captured_v3();v2,v2raw=v3.pinned_v2();method_raw=v3.capture(Path(__file__),100000)
            raw=v3.capture(ROOT/POLICY,MAX_POLICY);table=v3.capture(ROOT/v3.POLICY,v3.MAX_POLICY)
            need(sha(table)==V3_POLICY,'foundation_changed')
            old=v2.file_bytes(ROOT/v2.POLICY,v2.MAX_POLICY);legacy_raw=v2.file_bytes(ROOT/v2.LEGACY,v2.MAX_POLICY)
            d2,legacy,base=v2.policy(old,legacy_raw);additions,oldcopied,oldproject=v3.overlay(table,base,v2)
            worker=v2.worker()
            def git(args,limit=v2.MAX_LISTING):
                tick();remaining=min(20,deadline-time.monotonic());need(remaining>0,'deadline')
                outcome=worker([sys.executable,'-I','-S','-B','-c',v2.GIT_EXEC,'-C',str(ROOT),*args],input=b'',timeout=remaining,output_limit=limit)
                need(outcome.returncode==0,'git_unavailable');tick();return outcome.stdout
            head=git(['rev-parse','HEAD^{commit}'],100).decode().strip();commit=head if source_commit is None else source_commit
            need(type(commit)is str and OID.fullmatch(commit),'unsupported_source_commit')
            git(['merge-base','--is-ancestor',Q,commit],100)
            need(git(['rev-parse',Q+'^{tree}'],100).decode().strip()==Q_TREE,'source_changed')
            qrows,qtotal=v2.tree_rows(git(['ls-tree','-r','-l','-z','--full-tree',Q]))
            need(len(qrows)==Q_FILES and qtotal==Q_BYTES,'source_changed')
            owned={n for n,r in base.items()if r[3]=='project-text'}|oldproject|set(d2['named_first_party_extensions'])
            d,project,copied=policy(raw,v3,v2,base,additions['project_files'],qrows,owned)
            pinned={}
            for name,expected_pin in d['foundations'].items():
                value=v3.capture(ROOT/name,expected_pin['bytes']);need(len(value)==expected_pin['bytes']and sha(value)==expected_pin['sha256'],'foundation_changed');pinned[name]=value
            reads=baseline_reads(qrows,d2,legacy,base,additions,oldcopied,oldproject)
            expected={'unique_oids':len(reads),'bytes':sum(n+1 for n in reads.values()),'readset_sha256':sha(canonical(reads))}
            need(d['baseline_read_reservation']==expected,'foundation_changed')
            # Independent actual V3 verification is never replaced by a status/table or our own checker.
            baseline=v3.verify(source_commit=Q)
            need(baseline.get('pass')is True and baseline.get('source_copy_profile_satisfied')is True
              and baseline.get('source_commit')==Q and baseline.get('source_tree')==Q_TREE and type(baseline.get('files'))is int
              and baseline['files']==Q_FILES and type(baseline.get('source_bytes'))is int and baseline['source_bytes']==Q_BYTES
              and baseline.get('method_sha256')==V3_METHOD and baseline.get('policy_sha256')==V3_POLICY
              and all(baseline.get(k)is False for k in FALSE_CLAIMS),baseline.get('reason','foundation_changed'))
            tick();observed,total=v2.tree_rows(git(['ls-tree','-r','-l','-z','--full-tree',commit]))
            bodies=Bodies(git,tick,expected['bytes']);facts=classify(d,project,copied,qrows,observed,additions['project_files'],owned,v2,bodies.read,tick)
            tree=git(['rev-parse',commit+'^{tree}'],100).decode().strip();need(OID.fullmatch(tree),'git_unavailable')
            need(git(['rev-parse','HEAD^{commit}'],100).decode().strip()==head,'source_changed')
            need(v3.capture(ROOT/POLICY,MAX_POLICY)==raw and v3.capture(ROOT/'tools/source_release_policy_v3.py',100000)==v3raw
              and v3.capture(ROOT/'tools/source_release_policy_v2.py',100000)==v2raw and v3.capture(ROOT/v3.POLICY,12_000_000)==table
              and v2.file_bytes(ROOT/v2.POLICY,12_000_000)==old and v2.file_bytes(ROOT/v2.LEGACY,12_000_000)==legacy_raw,'source_changed')
            need(all(v3.capture(ROOT/n,len(value))==value for n,value in pinned.items())and v3.capture(Path(__file__),100000)==method_raw,'source_changed')
            method=sha(method_raw);tick()
            result.update({'pass':True,'status':'SOURCE_COPY_PROFILE_SATISFIED','source_copy_profile_satisfied':True,
              'source_commit':commit,'source_tree':tree,'checkout_commit':head,'policy_sha256':POLICY_SHA256,'method_sha256':method,
              'baseline_v3_verified':True,'baseline_v3_method_sha256':V3_METHOD,'baseline_v3_policy_sha256':V3_POLICY,
              'protected_baseline_commit':Q,'selected_profile_base_is_protected_release':True,
              'selected_source_protected_release_claimed':commit==Q,'inspected_body_charge':bodies.used,**facts})
    except Exception as error:result['reason']=getattr(error,'code','unavailable')if getattr(error,'code','unavailable')in CODES else 'unavailable'
    return result


def verify_archive(raw,*,source_commit):
    result={'profile':'source-copy-archive-obligations/v4','pass':False,'status':'UNAVAILABLE','source_copy_profile_satisfied':False,
            'trusted_git_bytes_matched':False,'signature_verified':False,**{k:False for k in FALSE_CLAIMS}}
    try:
        need(type(raw)is bytes and 0<len(raw)<=MAX_ARCHIVE and type(source_commit)is str and OID.fullmatch(source_commit),'invalid_request')
        deadline=time.monotonic()+95;rights=verify(source_commit=source_commit);need(rights.get('pass')is True,rights.get('reason','unavailable'))
        v3,v3raw=captured_v3();v2,v2raw=v3.pinned_v2()
        method_raw=v3.capture(Path(__file__),100000);need(sha(method_raw)==rights['method_sha256'],'source_changed')
        policy_raw=v3.capture(ROOT/POLICY,MAX_POLICY);need(sha(policy_raw)==POLICY_SHA256,'policy_changed')
        fixed=v2.parse(policy_raw)['foundations'];keys(fixed,FOUNDATION_PATHS);pinned={}
        for name,item in fixed.items():
            value=v3.capture(ROOT/name,item['bytes']);need(len(value)==item['bytes']and sha(value)==item['sha256'],'foundation_changed');pinned[name]=value
        source=pinned['tools/source_snapshot_binding.py'];need(sha(source)==v2.BINDING_SHA256,'foundation_changed')
        program='exec(compile('+repr(source)+", '<captured-source-binding>', 'exec'), "+repr({'__name__':'__main__','__file__':str(ROOT/'tools/source_snapshot_binding.py')})+')'
        remaining=min(60,deadline-time.monotonic());need(remaining>0,'deadline')
        summary=v2._binding_capture(source)([sys.executable,'-I','-S','-B','-c',program,'--binding-worker',str(ROOT),source_commit],raw,time.monotonic()+remaining,4096,new_session=True)
        value=v2.parse(summary);keys(value,('profile','pass','source_commit','source_tree','source_files','source_bytes','archive_sha256','trusted_git_bytes_matched','signature_verified','rights_approved','release_authorized'))
        need(value['profile']=='source-snapshot-trusted-git-binding/v1'and value['pass']is True and value['source_commit']==source_commit
          and value['source_tree']==rights['source_tree']and type(value['source_files'])is int and value['source_files']==rights['files']
          and type(value['source_bytes'])is int and value['source_bytes']==rights['source_bytes']and value['archive_sha256']==sha(raw)
          and value['trusted_git_bytes_matched']is True and all(value[k]is False for k in ('signature_verified','rights_approved','release_authorized')),'archive_refused')
        need(v3.capture(ROOT/'tools/source_release_policy_v3.py',100000)==v3raw and v3.capture(ROOT/'tools/source_release_policy_v2.py',100000)==v2raw
          and v3.capture(ROOT/POLICY,MAX_POLICY)==policy_raw and v3.capture(Path(__file__),100000)==method_raw
          and all(v3.capture(ROOT/name,len(value))==value for name,value in pinned.items()),'source_changed')
        need(time.monotonic()<deadline,'deadline');result.update({'pass':True,'status':'COPY_OBLIGATIONS_AND_GIT_BYTES_BOUND','source_copy_profile_satisfied':True,
          'trusted_git_bytes_matched':True,'source_commit':source_commit,'source_tree':value['source_tree'],'source_files':value['source_files'],
          'source_bytes':value['source_bytes'],'archive_sha256':value['archive_sha256'],'archive_bytes':len(raw),'method_sha256':rights['method_sha256'],
          'policy_sha256':POLICY_SHA256,'binding_method_sha256':v2.BINDING_SHA256})
    except Exception as error:result['reason']=getattr(error,'code','archive_refused')if getattr(error,'code','archive_refused')in CODES else 'archive_refused'
    return result


class Parser(argparse.ArgumentParser):
    def error(self,message):raise Refused('invalid_request')


def main(argv=None):
    try:
        parser=Parser(description=__doc__);parser.add_argument('--source-commit');parser.add_argument('--archive',type=Path);args=parser.parse_args(argv)
        if args.archive is None:result=verify(source_commit=args.source_commit)
        else:
            need(args.source_commit is not None,'invalid_request');v3,_=captured_v3();result=verify_archive(v3.capture(args.archive,MAX_ARCHIVE),source_commit=args.source_commit)
    except Exception as error:result={'profile':PROFILE,'pass':False,'status':'UNAVAILABLE','reason':getattr(error,'code','unavailable'),**{k:False for k in FALSE_CLAIMS}}
    print(json.dumps(result,sort_keys=True));return 0 if result['pass']else 2


if __name__=='__main__':raise SystemExit(main())
