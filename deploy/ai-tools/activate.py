#!/usr/bin/env python3
"""Explicit root-only activation/rollback of the NEW isolated API namespace.

Never loads the host firewall file or changes other services. Operator must
review the immutable release and this finite plan before --apply-reviewed.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time
import asyncio
import fcntl
import secrets
from contextlib import contextmanager
from functools import wraps
from time import monotonic as ready_now

APPROVED_COMMIT='a5215149af23be51cd29f9b37ce1d85bdeff0c49'
APPROVED_SOURCE={'LICENSE': 'cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30',
 'NOTICE': 'e185f305c76f821aa56011cd201ea03f49e97c57dfc786517f77bfc00c7fecd6',
 'integrations/mcp/requirements.in': 'e6c1d29fe87f6e388e1bc35a791364b788f5452ab0524f8b452084e2cf569400',
 'integrations/mcp/requirements.lock': '82375e677571a53a1d3c8b5f13312ae8f81da2a05e4bea0ab59417d4486d95ea',
 'protocol/normalization.py': 'd949dd32a43762b6d71c7c746430c3ee0fc0d4036885e3b1a2a94deb056f09d1',
 'protocol/unicode15-data.json': '76121e982f9338f18905eb69e9c9c4b5268247b91841eb20e999b39e11aa0458',
 'scripts/build-device-detector.py': '582e2b24f8895071216bbbde0891062feb093869283e776757ea5def40ea93a3',
 'scripts/check-ps.py': '0e4532e95a7f71cac8874f42e1c4ecbc363b159cbed43b7f48bd5146210ed240',
 'scripts/check-tags.py': 'c3cd8c05ad2969b023bb6f332331787b13b2ff6347913fc0f0c3144321279c96',
 'scripts/remote-tag-server.py': 'e759f37f66a119aab3ad1716bf35de547edfa07b926cb512e8059f9fd079a064',
 'scripts/worker_process.py': 'ee73563027d7481f8990cc37ba57732f6eaef5c56ed476831f04612c468a82dd',
 'services/evaluator/app.py': 'ee1cc1e11b68de9c6971714232b505b97e4a9f32e216d544217fbebf04779631',
 'tools/remote_tag_server.py': 'b656abfb64eb925f8e63789365590a35c652d35e16001da284fa8f827162a72d',
 'tools/tag_api.py': 'd12d162a549d0f8c430eee5be05a8db0f874bf2062acc04fd9d717b257b35b2e'}

def approved_projection(commit,manifest):
    return type(commit)is str and commit==APPROVED_COMMIT and type(manifest)is dict and manifest.get('commit')==APPROVED_COMMIT and manifest.get('source_sha256')==APPROVED_SOURCE

BASE=Path('/opt/aitrustid-ai-tools')
UNITS=('aitrustid-ai-tools.service','aitrustid-ai-tools-proxy.service')
TAG='aitrustid-ai-tools-https-v1'
RULE=f'insert rule inet aitrust_host input ct state new tcp dport 443 limit rate 40/second burst 80 packets accept comment "{TAG}"'
BLOCK=('# BEGIN '+TAG+'\n'+RULE+'\n# END '+TAG+'\n').encode()
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('render',HERE/'render.py');render=importlib.util.module_from_spec(s);s.loader.exec_module(render)

def digest(b):return hashlib.sha256(b).hexdigest()
def run(args,timeout=20):
    p=subprocess.run(args,capture_output=True,timeout=timeout)
    if p.returncode:raise ValueError('operation_unavailable')
    if len(p.stdout)+len(p.stderr)>256000:raise ValueError('operation_unavailable')
    return p.stdout

def read_regular(path,limit=131072):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode)or st.st_uid!=0 or st.st_mode&0o022 or st.st_size>limit:raise ValueError('operator_file_refused')
        b=os.read(fd,limit+1)
        if len(b)>limit or len(b)!=st.st_size:raise ValueError('operator_file_refused')
        return b
    finally:owned=fd;fd=None;os.close(owned)

def exclusive(path,data,mode=0o600):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    identity=os.fstat(fd)
    try:
        try:
            with os.fdopen(fd,'wb',closefd=False)as f:f.write(data);f.flush();os.fsync(f.fileno())
        finally:owned=fd;fd=None;os.close(owned)
    except BaseException:
        # Only the just-created inode is ours; never remove a replacement.
        try:
            current=os.lstat(path)
            if current.st_dev==identity.st_dev and current.st_ino==identity.st_ino:os.unlink(path)
        except FileNotFoundError:pass
        raise

def atomic_replace(path,before,after):
    if read_regular(path)!=before:raise ValueError('operator_file_changed')
    fd,name=tempfile.mkstemp(prefix='.aitrust-api-',dir=path.parent)
    try:
        try:
            with os.fdopen(fd,'wb',closefd=False)as f:f.write(after);f.flush();os.fsync(f.fileno());os.fchmod(fd,0o644)
        finally:owned=fd;fd=None;os.close(owned)
        if read_regular(path)!=before:raise ValueError('operator_file_changed')
        os.replace(name,path)
        d=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(d)
        finally:owned=d;d=None;os.close(owned)
    finally:
        try:os.unlink(name)
        except FileNotFoundError:pass

def input_rules():
    return [x['rule']for x in json.loads(run(['nft','-j','list','chain','inet','aitrust_host','input']))['nftables']if 'rule'in x]

def normalized(value):
    if isinstance(value,dict):return {k:normalized(v)for k,v in value.items()if k not in ('packets','bytes')}
    if isinstance(value,list):return [normalized(x)for x in value]
    return value

def owned_rule_definition(value):
    # Only nft's mutable counter values are ignored, never semantic fields.
    if isinstance(value,dict):
        return {key:({k:owned_rule_definition(v)for k,v in item.items()if k not in ('packets','bytes')}if key=='counter'and isinstance(item,dict)else owned_rule_definition(item))for key,item in value.items()}
    if isinstance(value,list):return [owned_rule_definition(item)for item in value]
    return value

def preserved(before,after):
    current={r['handle']:normalized(r)for r in after}
    return all(current.get(r['handle'])==normalized(r)for r in before)

def checked_release(commit):
    if type(commit)is not str or commit!=APPROVED_COMMIT:raise ValueError('release_refused')
    release=BASE/'releases'/commit
    if release.resolve(strict=True)!=release or release.stat().st_uid!=0 or release.stat().st_mode&0o022:raise ValueError('release_refused')
    m=json.loads(read_regular(release/'release.json'))
    if not approved_projection(commit,m) or m.get('schema')!='aitrust-ai-tools-prepared-release-1' or m.get('venv_provisioned')is not True:raise ValueError('release_refused')
    if m.get('caddy_package_sha256')!=render.CADDY_SHA256 or digest(read_regular(release/'caddy',64_000_000))!='6d1dc61710d336c37fb5aca50260bf017bf10e948a31e8b381a7d03ddede1543':raise ValueError('release_refused')
    allowed={'LICENSE','NOTICE','tools/tag_api.py','tools/remote_tag_server.py','scripts/remote-tag-server.py','scripts/check-tags.py','scripts/check-ps.py','scripts/worker_process.py','scripts/build-device-detector.py','services/evaluator/app.py','protocol/normalization.py','protocol/unicode15-data.json','integrations/mcp/requirements.lock','integrations/mcp/requirements.in'}
    if set(m.get('source_sha256',{}))!=allowed:raise ValueError('release_refused')
    for n,h in m['source_sha256'].items():
        if digest(read_regular(release/'source'/n,1000000))!=h:raise ValueError('release_refused')
    files={'Caddyfile':render.caddyfile(),**render.units(commit)}
    for n,t in files.items():
        if read_regular(release/n)!=t.encode():raise ValueError('configuration_refused')
    return release,m,files

async def health_attempt():
    # Existing hash-locked optional deployment environment, never global install.
    import httpx2
    try:
        async with httpx2.AsyncClient(trust_env=False,timeout=.3,follow_redirects=False)as client:
            async with client.stream('GET','http://127.0.0.1:8790/healthz',headers={'Host':render.HOST})as response:
                if response.status_code!=200:return False
                raw=bytearray()
                async for chunk in response.aiter_raw():
                    if len(raw)+len(chunk)>4096:return False
                    raw.extend(chunk)
                value=json.loads(raw)
                return type(value)is dict and value.get('ok')is True
    except (httpx2.HTTPError,OSError,ValueError):return False

async def private_health_ready(seconds):
    deadline=ready_now()+seconds;attempts=0
    try:
        # Covers connection, headers, bounded body, parsing, closing and retries.
        async with asyncio.timeout(seconds):
            while True:
                if ready_now()>=deadline:raise ValueError('private_health_unavailable')
                attempts+=1;positive=await health_attempt()
                if ready_now()>=deadline:raise ValueError('private_health_unavailable')
                if positive is True:return {'ready':True,'attempts':attempts}
                await asyncio.sleep(min(.025,max(0,deadline-ready_now())))
    except TimeoutError:raise ValueError('private_health_unavailable')from None

def wait_private_health(seconds=5):
    return asyncio.run(private_health_ready(seconds))

def isolation_proof(commit,public_ip):
    spec=importlib.util.spec_from_file_location('api_isolation',HERE/'verify-isolation.py');isolation=importlib.util.module_from_spec(spec);spec.loader.exec_module(isolation)
    return isolation.observe(commit,public_ip)

def sync_directory(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:owned=fd;fd=None;os.close(owned)

@contextmanager
def operation_lock():
    # Do not create BASE or remove a persistent lock inode during handoff.
    info=BASE.stat()
    if BASE.resolve(strict=True)!=BASE or not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o022:raise ValueError('ownership_namespace_refused')
    fd=os.open(BASE/'.activation-operation.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o600 or info.st_nlink!=1:raise ValueError('operation_lock_refused')
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield
    finally:owned=fd;fd=None;os.close(owned)

def serialized(function):
    @wraps(function)
    def guarded(*args,**kwargs):
        with operation_lock():return function(*args,**kwargs)
    return guarded

def owner_value(record,state):
    epoch=state.get('ownership_epoch')
    if type(epoch)is not str or re.fullmatch('[a-f0-9]{64}',epoch)is None or state.get('ownership_record')!=record.name:raise ValueError('record_ownership_refused')
    return {'schema':'aitrust-ai-tools-active-record-1','record_name':record.name,'epoch':epoch}

def require_active_record(record,state):
    expected=owner_value(record,state)
    if json.loads(read_regular(BASE/'active-record.json'))!=expected:raise ValueError('record_ownership_refused')
    return expected

def checked_unit(state,unit):
    path=Path('/etc/systemd/system')/unit;before=os.lstat(path)
    if [before.st_dev,before.st_ino]!=state['unit_identity'][unit]:raise ValueError('unit_ownership_changed')
    raw=read_regular(path);after=os.lstat(path)
    if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise ValueError('unit_changed')
    return raw

def save_state(record,state):
    path=record/'state.json';raw=(json.dumps(state,indent=2)+'\n').encode()
    if path.exists():atomic_replace(path,read_regular(path),raw)
    else:exclusive(path,raw)

def activate(commit,apply=False,public_ip=None):
    if not apply:return _activate(commit,False,public_ip)
    with operation_lock():return _activate(commit,True,public_ip)

def _activate(commit,apply=False,public_ip=None):
    release,m,files=checked_release(commit)
    owner=BASE/'active-record.json'
    if owner.exists()or owner.is_symlink():raise ValueError('active_record_collision')
    for unit in UNITS:
        p=Path('/etc/systemd/system')/unit
        if p.exists()or p.is_symlink()or run(['systemctl','show',unit,'-p','LoadState','--value']).strip()!=b'not-found':raise ValueError('unit_collision')
    if Path('/var/lib/aitrustid-ai-tools-proxy').exists():raise ValueError('state_collision')
    before=read_regular(Path('/etc/nftables.conf'));rules=input_rules()
    if TAG.encode()in before or any(r.get('comment')==TAG for r in rules):raise ValueError('rule_collision')
    run(['nft','-c',*__import__('shlex').split(RULE)])
    plan={'release_commit':commit,'release_source_sha256':m['source_sha256'],'caddyfile_sha256':digest(files['Caddyfile'].encode()),'unit_sha256':{n:digest(files[n].encode())for n in UNITS},'firewall_before_sha256':digest(before),'rule_tag':TAG,'public_port':443,'host':render.HOST,'apply':apply,'public_activation_requires_separate_command':True}
    if not apply:return plan
    records=BASE/'activation-records';records.mkdir(mode=0o700,exist_ok=True)
    epoch=secrets.token_hex(32)
    record=records/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+commit[:12]+'-'+epoch[:16]);record.mkdir(mode=0o700)
    exclusive(record/'firewall.before',before)
    exclusive(record/'input-rules.before.json',(json.dumps(rules,indent=2)+'\n').encode())
    exclusive(record/'plan.json',(json.dumps(plan,indent=2)+'\n').encode())
    state={'phase':'prepared','commit':commit,'unit_sha256':plan['unit_sha256'],'installed_units':[],'rule_handle':None,'rule_definition':None,'persistence':False,'failure':None,'ownership_record':record.name,'ownership_epoch':epoch,'unit_identity':{}}
    def save():save_state(record,state)
    save();sync_directory(record);sync_directory(records)
    exclusive(owner,(json.dumps(owner_value(record,state),indent=2)+'\n').encode());sync_directory(BASE)
    stage='unit_install'
    try:
        for unit in UNITS:
            exclusive(Path('/etc/systemd/system')/unit,files[unit].encode(),0o644);info=os.lstat(Path('/etc/systemd/system')/unit);state['unit_identity'][unit]=[info.st_dev,info.st_ino];state['installed_units'].append(unit);save()
        run(['systemd-analyze','verify',*[str(Path('/etc/systemd/system')/u)for u in UNITS]])
        run(['systemctl','daemon-reload']);stage='private_start';run(['systemctl','start',UNITS[0]],30);state['phase']='private_app_started';save()
        stage='private_health';readiness=wait_private_health();exclusive(record/'private-readiness.json',(json.dumps(readiness,indent=2)+'\n').encode())
        stage='private_isolation';proof=isolation_proof(commit,public_ip);exclusive(record/'effective-isolation.json',(json.dumps(proof,indent=2)+'\n').encode())
        state['phase']='private_isolation_ready';save()
        return {'pass':True,'record':str(record),'plan':plan,'phase':state['phase'],'public_activation_performed':False}
    except Exception:
        state['failure']='activation_unavailable';state['failure_stage']=stage;save()
        # Keep the exact ledger/snapshot; root operator can invoke bounded rollback.
        return {'pass':False,'record':str(record),'phase':state['phase'],'reason':'activation_unavailable','failure_stage':stage,'rollback_required':True}

def approved_record(state,plan):
    hashes={n:digest(t.encode())for n,t in render.units(APPROVED_COMMIT).items()}
    return type(state)is dict and type(plan)is dict and state.get('commit')==APPROVED_COMMIT and plan.get('release_commit')==APPROVED_COMMIT and state.get('unit_sha256')==hashes and plan.get('unit_sha256')==hashes and plan.get('release_source_sha256')==APPROVED_SOURCE and plan.get('caddyfile_sha256')==digest(render.caddyfile().encode()) and plan.get('rule_tag')==TAG and plan.get('public_port')==443 and plan.get('host')==render.HOST and type(state.get('installed_units'))is list and len(state['installed_units'])<=2 and len(set(state['installed_units']))==len(state['installed_units'])and all(x in UNITS for x in state['installed_units'])

def root_owned_record(path):
    info=path.stat()
    return stat.S_ISDIR(info.st_mode)and info.st_uid==0 and not info.st_mode&0o022

def checked_record(path):
    p=Path(path)
    if p.parent!=BASE/'activation-records'or p.resolve(strict=True)!=p or not root_owned_record(p):raise ValueError('record_refused')
    state=json.loads(read_regular(p/'state.json'));plan=json.loads(read_regular(p/'plan.json'))
    if not approved_record(state,plan) or state.get('phase') not in ('prepared','private_app_started','private_isolation_ready','firewall_inserted','running_pending_public_proof','enabled_after_operator_public_proof','rollback_in_progress'):raise ValueError('record_refused')
    if type(state.get('persistence'))is not bool or not(state.get('rule_handle')is None or type(state['rule_handle'])is int and state['rule_handle']>0):raise ValueError('record_refused')
    definition=state.get('rule_definition')
    if state['rule_handle']is None:
        if definition is not None:raise ValueError('record_refused')
    elif type(definition)is not dict or definition.get('handle')!=state['rule_handle']or definition.get('comment')!=TAG or owned_rule_definition(definition)!=definition:raise ValueError('record_refused')
    identities=state.get('unit_identity')
    if type(identities)is not dict or set(identities)!=set(state['installed_units'])or any(type(v)is not list or len(v)!=2 or any(type(n)is not int or n<0 for n in v)for v in identities.values()):raise ValueError('record_refused')
    require_active_record(p,state)
    return p,state,plan

@serialized
def publish(path,public_ip):
    record,state,plan=checked_record(path)
    if state['phase']!='private_isolation_ready':raise ValueError('private_acceptance_unavailable')
    release,manifest,canonical=checked_release(state['commit'])
    for unit in UNITS:
        if digest(checked_unit(state,unit))!=digest(render.units(APPROVED_COMMIT)[unit].encode()):raise ValueError('unit_changed')
    if run(['systemctl','show',UNITS[1],'-p','ActiveState','--value']).strip()!=b'inactive':raise ValueError('proxy_state_changed')
    before=read_regular(record/'firewall.before');current=read_regular(Path('/etc/nftables.conf'));rules=input_rules()
    if current!=before or any(r.get('comment')==TAG for r in rules):raise ValueError('firewall_changed')
    # Fresh actual isolation proof before the separately authorized public step.
    proof=isolation_proof(state['commit'],public_ip);exclusive(record/'effective-isolation-public.json',(json.dumps(proof,indent=2)+'\n').encode())
    def save():atomic_replace(record/'state.json',read_regular(record/'state.json'),(json.dumps(state,indent=2)+'\n').encode())
    stage='public_rule'
    try:
        run(['nft',*__import__('shlex').split(RULE)])
        after=input_rules();owned=[r for r in after if r.get('comment')==TAG]
        if len(owned)!=1 or not preserved(rules,after):raise ValueError('rule_verification_unavailable')
        state['rule_handle']=owned[0]['handle'];state['rule_definition']=owned_rule_definition(owned[0]);state['phase']='firewall_inserted';save()
        stage='public_persistence';atomic_replace(Path('/etc/nftables.conf'),before,before+b'\n'+BLOCK);state['persistence']=True;save()
        stage='public_proxy_start';run(['systemctl','start',UNITS[1]],30);state['phase']='running_pending_public_proof';save()
        return {'pass':True,'record':str(record),'phase':state['phase']}
    except Exception:
        state['failure']='publication_unavailable';state['failure_stage']=stage;save()
        return {'pass':False,'record':str(record),'phase':state['phase'],'failure_stage':stage,'rollback_required':True}

@serialized
def rollback(path):
    p,state,plan=checked_record(path)
    recovering=state['phase']=='rollback_in_progress';present=[]
    # Validate the entire recorded resource set BEFORE stopping/disabling units.
    for unit in UNITS:
        target=Path('/etc/systemd/system')/unit
        if unit not in state['installed_units']and(target.exists()or target.is_symlink()):raise ValueError('unit_unrecorded')
    for unit in state['installed_units']:
        try:raw=checked_unit(state,unit)
        except FileNotFoundError:
            if not recovering:raise ValueError('unit_changed')from None
            continue
        if digest(raw)!=state['unit_sha256'][unit]:raise ValueError('unit_changed')
        present.append(unit)
    rules=input_rules();owned=[r for r in rules if r.get('comment')==TAG]
    handle=state['rule_handle']
    if owned:
        if len(owned)!=1 or handle is None or owned[0]['handle']!=handle or owned_rule_definition(owned[0])!=state['rule_definition']:raise ValueError('rule_changed')
    elif handle is not None and not recovering:raise ValueError('rule_changed')
    before=read_regular(p/'firewall.before');current=read_regular(Path('/etc/nftables.conf'))
    if state['persistence']:
        if current!=before+b'\n'+BLOCK and not(recovering and current==before):raise ValueError('persistence_changed')
    elif current!=before:raise ValueError('persistence_changed')
    state['phase']='rollback_in_progress';save_state(p,state)
    for unit in reversed(present):run(['systemctl','stop',unit],30)
    for unit in present:run(['systemctl','disable',unit])
    if owned:run(['nft','delete','rule','inet','aitrust_host','input','handle',str(handle)])
    if current!=before:atomic_replace(Path('/etc/nftables.conf'),current,before)
    for unit in present:os.unlink(Path('/etc/systemd/system')/unit)
    run(['systemctl','daemon-reload'])
    # A failed terminal write retains the lease and blocks replacement apply.
    state['phase']='rolled_back';state['retired_at']=datetime.now(timezone.utc).isoformat();save_state(p,state)
    expected=require_active_record(p,state)
    if json.loads(read_regular(BASE/'active-record.json'))!=expected:raise ValueError('record_ownership_refused')
    os.unlink(BASE/'active-record.json');sync_directory(BASE)
    return {'pass':True,'phase':'rolled_back','record_retired':True,'release_retained_for_review':True,'other_services_modified':False}

@serialized
def finalize(path):
    p,state,plan=checked_record(path)
    if state['phase']!='running_pending_public_proof':raise ValueError('state_refused')
    for unit in UNITS:
        if digest(checked_unit(state,unit))!=digest(render.units(APPROVED_COMMIT)[unit].encode()):raise ValueError('unit_changed')
        if run(['systemctl','is-active',unit]).strip()!=b'active':raise ValueError('service_unavailable')
    run(['systemctl','enable',*UNITS]);state['phase']='enabled_after_operator_public_proof';atomic_replace(p/'state.json',read_regular(p/'state.json'),(json.dumps(state,indent=2)+'\n').encode())
    return {'pass':True,'phase':state['phase']}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--commit');p.add_argument('--own-public-ip');p.add_argument('--apply-reviewed',action='store_true');p.add_argument('--rollback',type=Path);p.add_argument('--publish-reviewed',type=Path);p.add_argument('--finalize-after-proof',type=Path);a=p.parse_args()
    if os.getuid()!=0:raise ValueError('root_operator_required')
    if sum([bool(a.commit),bool(a.rollback),bool(a.finalize_after_proof),bool(a.publish_reviewed)])!=1:raise ValueError('operation_refused')
    result=rollback(a.rollback)if a.rollback else publish(a.publish_reviewed,a.own_public_ip)if a.publish_reviewed else finalize(a.finalize_after_proof)if a.finalize_after_proof else activate(a.commit,a.apply_reviewed,a.own_public_ip)
    print(json.dumps(result));return 0 if result.get('pass',True)else 1
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:print('{"pass":false,"reason":"api_activation_refused_or_unavailable"}');raise SystemExit(1)
