"""Owner-controlled local tenant policy governance; no hosted service or public tag."""
from contextlib import closing,contextmanager
import fcntl
from functools import wraps
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat
import sys
import time
import uuid

from protocol.normalization import normalize_nfc,NORMALIZATION_ID
from scripts.worker_process import run_worker
from tools import private_policy
from tools.organization_policy_io import Capture,PrivateInputError,OutputCommitUncertain,encoded,sha,need

ROOT=Path(__file__).resolve().parents[1]
CONTRACT='local-owner-organization-namespace/v1'
AUTHORITY='local-organization-authority/v1'
CREDENTIAL='local-organization-capability/v1'
SELECTION='local-organization-policy-selection/v1'
RESULT='local-organization-policy-result/v1'
ROLES=frozenset({'view','check','export','configure'})
MAX_TENANTS=8
MAX_JOBS=8
MAX_REVISIONS=8
MAX_GRANTS=16
MAX_EVENTS=256
MAX_DATABASE=8*1024**2
SOURCES=('tools/organization_policy_registry.py','tools/organization_policy_worker.py',
    'tools/organization_policy_io.py','tools/private_policy.py','protocol/normalization.py',
    'protocol/unicode15-data.json','protocol/evidence.py','spec/vocabulary.json','scripts/worker_process.py')


def boundary(function):
    @wraps(function)
    def call(*args,**kwargs):
        try:return function(*args,**kwargs)
        except OutputCommitUncertain:raise
        except Exception:raise PrivateInputError('Organization policy unavailable.') from None
    return call


def parse(raw,limit=65536):
    need(type(raw) is bytes and 0<len(raw)<=limit)
    def unique(pairs):
        value={}
        for k,v in pairs:
            need(k not in value);value[k]=v
        return value
    def reject(_):raise PrivateInputError('Organization policy unavailable.')
    value=json.loads(raw.decode('utf-8','strict'),object_pairs_hook=unique,parse_constant=reject)
    return value


def identifier(value):
    need(type(value) is str and str(uuid.UUID(value))==value)
    return value


def namespace(value):
    need(type(value) is str and re.fullmatch(r'[a-z][a-z0-9-]{2,47}',value) is not None)
    need(value not in {'aitrust','aitrust-id','public','standard','system','personal'})
    return value


def source_bindings(capture):
    return {n:sha(capture.read(ROOT/n,4_000_000,private=False)) for n in SOURCES}


def private_parent(capture,path):
    return capture.parent(Path(path).absolute())


def regular(capture,path,limit=MAX_DATABASE):
    parent,name=capture.parent(path)
    fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent);capture.fds.append(fd)
    info=os.fstat(fd)
    need(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_uid==os.getuid()
         and stat.S_IMODE(info.st_mode)==0o600 and 0<info.st_size<=limit)
    return fd,info


def preflight_output(capture,path):
    parent,name=capture.parent(path)
    try:
        os.stat(name,dir_fd=parent,follow_symlinks=False)
    except FileNotFoundError:
        return
    raise PrivateInputError('Organization policy unavailable.')


def authority(raw):
    value=parse(raw,4096)
    need(type(value) is dict and set(value)=={'format','authority_id','secret'} and value['format']==AUTHORITY)
    identifier(value['authority_id'])
    need(type(value['secret']) is str and re.fullmatch('[0-9a-f]{64}',value['secret']) is not None)
    return value


@boundary
def keygen(output):
    with Capture() as c:
        value={'format':AUTHORITY,'authority_id':str(uuid.uuid4()),'secret':secrets.token_hex(32)}
        c.save(output,value,4096)
    return {'state':'COMPLETE','authority_saved':True,'public_tag_asserted':False}


@boundary
def initialize(root,authority_file,accepted=False):
    need(accepted is True)
    root=Path(root).absolute()
    with Capture() as c:
        raw=c.read(authority_file,4096);a=authority(raw);parent,name=private_parent(c,root)
        os.mkdir(name,0o700,dir_fd=parent)
        # An interrupted initialization may leave a private incomplete directory.
        # Contract publication is last; it is never considered an enrolled registry
        # until every required internal directory exists and that file is complete.
        c.output_may_exist=True
        os.mkdir(root/'tenants',0o700)
        lock=os.open(root/'enrollment.lock',os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600);os.close(lock)
        value={'format':CONTRACT,'registry_id':str(uuid.uuid4()),'owner_uid':os.getuid(),
            'authority_id':a['authority_id'],'authority_sha256':sha(raw),'maximum_tenants':MAX_TENANTS,
            'namespace_claim':'local_filesystem_owner_control_not_real_organization_identity',
            'personal_enrollment_required':False,'commercial_terms_accepted':False}
        c.save(root/'registry.json',value,4096)
    return {'state':'COMPLETE','registry_initialized':True,'service_running':False,'public_tag_asserted':False}


class Registry:
    def __init__(self,root,capture):
        self.root=Path(root).absolute();self.c=capture
        self.fd=capture.directory(self.root)
        self.contract=parse(capture.read(self.root/'registry.json',4096),4096)
        d=self.contract
        need(type(d) is dict and set(d)=={'format','registry_id','owner_uid','authority_id','authority_sha256','maximum_tenants','namespace_claim','personal_enrollment_required','commercial_terms_accepted'})
        need(d['format']==CONTRACT and type(d['owner_uid']) is int and d['owner_uid']==os.getuid()
            and type(d['maximum_tenants']) is int and d['maximum_tenants']==MAX_TENANTS
            and d['namespace_claim']=='local_filesystem_owner_control_not_real_organization_identity'
            and d['personal_enrollment_required'] is False and d['commercial_terms_accepted'] is False)
        identifier(d['registry_id']);identifier(d['authority_id'])
        need(type(d['authority_sha256']) is str and re.fullmatch('[0-9a-f]{64}',d['authority_sha256']) is not None)
        self.tenants_fd=capture.directory(self.root/'tenants')

    def admin(self,path):
        raw=self.c.read(path,4096);a=authority(raw)
        need(a['authority_id']==self.contract['authority_id'] and hmac.compare_digest(sha(raw),self.contract['authority_sha256']))

    def tenant_names(self):
        names=[]
        with os.scandir(self.tenants_fd) as rows:
            for row in rows:
                need(len(names)<MAX_TENANTS);namespace(row.name)
                need(row.is_dir(follow_symlinks=False));names.append(row.name)
        return sorted(names)

    def enroll(self,name,offering,admin_file):
        self.admin(admin_file);namespace(name);need(offering in ('team','enterprise','proprietary'))
        lock,_=self.empty_lock(self.root/'enrollment.lock')
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        need(len(self.tenant_names())<MAX_TENANTS)
        os.mkdir(name,0o700,dir_fd=self.tenants_fd);self.c.output_may_exist=True
        folder=self.root/'tenants'/name
        lock=os.open(folder/'access.lock',os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600);os.close(lock)
        dbfd=os.open(folder/'state.sqlite',os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600);os.close(dbfd)
        tenant_id=str(uuid.uuid4())
        with closing(sqlite3.connect(folder/'state.sqlite',timeout=.5)) as db:
            db.execute('PRAGMA page_size=4096');db.execute('PRAGMA max_page_count=2048')
            db.executescript('CREATE TABLE control(singleton INTEGER PRIMARY KEY CHECK(singleton=1),epoch INTEGER NOT NULL,enabled INTEGER NOT NULL);'
                'CREATE TABLE jobs(job TEXT PRIMARY KEY,revision INTEGER NOT NULL,enabled INTEGER NOT NULL);'
                'CREATE TABLE policies(job TEXT NOT NULL,revision INTEGER NOT NULL,raw BLOB NOT NULL,hash TEXT NOT NULL,sources TEXT NOT NULL,PRIMARY KEY(job,revision));'
                'CREATE TABLE grants(capability TEXT PRIMARY KEY,hash TEXT NOT NULL,roles TEXT NOT NULL,expires INTEGER NOT NULL,revoked INTEGER NOT NULL);'
                'CREATE TABLE events(sequence INTEGER PRIMARY KEY,previous TEXT NOT NULL,payload TEXT NOT NULL,hash TEXT NOT NULL);'
                'INSERT INTO control VALUES(1,1,1);')
        meta={'format':'local-organization-tenant/v1','registry_id':self.contract['registry_id'],
            'tenant_id':tenant_id,'namespace':name,'offering':offering,'owner_uid':os.getuid()}
        self.c.save(folder/'tenant.json',meta,4096)
        return {'state':'COMPLETE','tenant_registered':True,'organization_identity_verified':False,'public_tag_asserted':False}

    @contextmanager
    def tenant(self,name,write=False):
        namespace(name);folder=self.root/'tenants'/name
        self.c.directory(folder)
        meta=parse(self.c.read(folder/'tenant.json',4096),4096)
        need(type(meta) is dict and set(meta)=={'format','registry_id','tenant_id','namespace','offering','owner_uid'}
            and meta['format']=='local-organization-tenant/v1' and meta['registry_id']==self.contract['registry_id']
            and meta['namespace']==name and meta['offering'] in ('team','enterprise','proprietary')
            and type(meta['owner_uid']) is int and meta['owner_uid']==os.getuid())
        identifier(meta['tenant_id'])
        lock,_=self.empty_lock(folder/'access.lock')
        fcntl.flock(lock,(fcntl.LOCK_EX if write else fcntl.LOCK_SH)|fcntl.LOCK_NB)
        fd,info=regular(self.c,folder/'state.sqlite')
        db=sqlite3.connect(folder/'state.sqlite',timeout=.5,isolation_level=None)
        try:
            need((os.stat(folder/'state.sqlite',follow_symlinks=False).st_dev,os.stat(folder/'state.sqlite',follow_symlinks=False).st_ino)==(info.st_dev,info.st_ino))
            db.execute('PRAGMA trusted_schema=OFF');db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA busy_timeout=500')
            need(db.execute('PRAGMA page_size').fetchone()==(4096,));db.execute('PRAGMA max_page_count=2048')
            need(db.execute('PRAGMA quick_check(1)').fetchone()==('ok',))
            need(db.execute('SELECT count(*) FROM control').fetchone()==(1,))
            need(db.execute('SELECT count(*) FROM events').fetchone()[0]<=MAX_EVENTS)
            yield Tenant(self,meta,db)
            need(os.fstat(fd).st_size<=MAX_DATABASE)
            self.c.check()
        finally:db.close()

    def empty_lock(self,path):
        parent,name=self.c.parent(path)
        fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent);self.c.fds.append(fd)
        info=os.fstat(fd)
        need(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_uid==os.getuid()
            and stat.S_IMODE(info.st_mode)==0o600 and info.st_size==0)
        return fd,info


class Tenant:
    def __init__(self,registry,meta,db):
        self.registry=registry;self.meta=meta;self.db=db;self.c=registry.c
        rows=db.execute('SELECT sequence,previous,payload,hash FROM events ORDER BY sequence LIMIT 257').fetchall()
        need(len(rows)<=MAX_EVENTS)
        prior='0'*64
        for sequence,row in enumerate(rows,1):
            need(row[0]==sequence and row[1]==prior and type(row[2]) is str and len(row[2])<=4096)
            payload=parse(row[2].encode(),4096)
            need(type(payload) is dict and set(payload)=={'operation','fields','epoch'} and payload['epoch']==sequence+1)
            need(row[3]==sha(encoded({'sequence':sequence,'previous':prior,'payload':row[2]})))
            prior=row[3]
        need(self.state()[0]==len(rows)+1)

    def state(self):
        row=self.db.execute('SELECT epoch,enabled FROM control WHERE singleton=1').fetchone()
        need(row is not None and type(row[0]) is int and 1<=row[0]<=MAX_EVENTS+1 and row[1] in (0,1))
        return row

    def authorize(self,path,roles):
        raw=self.c.read(path,4096);v=parse(raw,4096)
        need(type(v) is dict and set(v)=={'format','registry_id','tenant_id','capability_id','secret'}
            and v['format']==CREDENTIAL and v['registry_id']==self.meta['registry_id'] and v['tenant_id']==self.meta['tenant_id'])
        identifier(v['capability_id']);need(type(v['secret']) is str and re.fullmatch('[0-9a-f]{64}',v['secret']) is not None)
        row=self.db.execute('SELECT hash,roles,expires,revoked FROM grants WHERE capability=?',(v['capability_id'],)).fetchone()
        need(row is not None and hmac.compare_digest(sha(raw),row[0]) and row[3]==0
            and type(row[2]) is int and row[2]>int(time.time()) and self.state()[1]==1)
        granted=parse(row[1].encode(),4096)
        need(type(granted) is list and len(granted)==len(set(granted)) and set(granted)<=ROLES and set(roles)<=set(granted))
        return v['capability_id']

    @contextmanager
    def mutation(self,operation,fields):
        need(type(operation) is str and operation in ('grant','revoke','policy','job_enabled','tenant_enabled'))
        self.db.execute('BEGIN IMMEDIATE')
        committed=False
        try:
            need(self.db.execute('SELECT count(*) FROM events').fetchone()[0]<MAX_EVENTS)
            yield
            epoch,_=self.state();self.db.execute('UPDATE control SET epoch=? WHERE singleton=1',(epoch+1,))
            previous=self.db.execute('SELECT sequence,hash FROM events ORDER BY sequence DESC LIMIT 1').fetchone()
            sequence=1 if previous is None else previous[0]+1;prior='0'*64 if previous is None else previous[1]
            payload=encoded({'operation':operation,'fields':fields,'epoch':epoch+1}).decode('ascii')
            digest=sha(encoded({'sequence':sequence,'previous':prior,'payload':payload}))
            self.db.execute('INSERT INTO events VALUES(?,?,?,?)',(sequence,prior,payload,digest))
            self.c.check();self.c.output_may_exist=True
            self.db.commit();committed=True
        finally:
            if not committed:self.db.rollback()

    def grant(self,admin_file,roles,seconds,output):
        self.registry.admin(admin_file)
        need(type(roles) in (list,tuple) and roles and len(roles)==len(set(roles)) and set(roles)<=ROLES)
        need(type(seconds) is int and 1<=seconds<=86400 and self.state()[1]==1)
        need(self.db.execute('SELECT count(*) FROM grants').fetchone()[0]<MAX_GRANTS)
        preflight_output(self.c,output)
        value={'format':CREDENTIAL,'registry_id':self.meta['registry_id'],'tenant_id':self.meta['tenant_id'],
            'capability_id':str(uuid.uuid4()),'secret':secrets.token_hex(32)}
        raw=encoded(value)+b'\n';expiry=int(time.time())+seconds
        with self.mutation('grant',{'capability':value['capability_id'],'roles':sorted(roles),'expires':expiry}):
            self.db.execute('INSERT INTO grants VALUES(?,?,?,?,0)',(value['capability_id'],sha(raw),encoded(sorted(roles)).decode(),expiry))
        self.c.save(output,value,4096)
        return {'state':'COMPLETE','credential_saved':True,'public_tag_asserted':False}

    def revoke(self,admin_file,credential_file):
        self.registry.admin(admin_file);v=parse(self.c.read(credential_file,4096),4096)
        need(type(v) is dict and v.get('tenant_id')==self.meta['tenant_id'] and v.get('registry_id')==self.meta['registry_id'])
        key=identifier(v.get('capability_id'))
        need(self.db.execute('SELECT count(*) FROM grants WHERE capability=?',(key,)).fetchone()==(1,))
        with self.mutation('revoke',{'capability':key}):self.db.execute('UPDATE grants SET revoked=1 WHERE capability=?',(key,))
        return {'state':'COMPLETE','credential_revoked':True,'public_tag_asserted':False}

    def add_policy(self,credential_file,policy_file):
        self.authorize(credential_file,{'configure'})
        raw=self.c.read(policy_file,65536);policy=private_policy.policy(raw)
        need(policy.namespace==self.meta['namespace'])
        previous=self.db.execute('SELECT revision FROM jobs WHERE job=?',(policy.policy_id,)).fetchone()
        count=self.db.execute('SELECT count(*) FROM policies WHERE job=?',(policy.policy_id,)).fetchone()[0]
        need(count<MAX_REVISIONS and (previous is not None or self.db.execute('SELECT count(*) FROM jobs').fetchone()[0]<MAX_JOBS))
        need(policy.revision==(1 if previous is None else previous[0]+1))
        sources=source_bindings(self.c)
        with self.mutation('policy',{'job':policy.policy_id,'revision':policy.revision,'sha256':sha(raw)}):
            self.db.execute('INSERT INTO policies VALUES(?,?,?,?,?)',(policy.policy_id,policy.revision,raw,sha(raw),encoded(sources).decode()))
            self.db.execute('INSERT INTO jobs VALUES(?,?,1) ON CONFLICT(job) DO UPDATE SET revision=excluded.revision,enabled=1',(policy.policy_id,policy.revision))
            self.authorize(credential_file,{'configure'})
        return {'state':'COMPLETE','policy_registered':True,'public_tag_asserted':False}

    def enable_job(self,credential_file,job,enabled):
        self.authorize(credential_file,{'configure'});need(type(enabled) is bool)
        need(self.db.execute('SELECT count(*) FROM jobs WHERE job=?',(job,)).fetchone()==(1,))
        with self.mutation('job_enabled',{'job':job,'enabled':enabled}):
            self.db.execute('UPDATE jobs SET enabled=? WHERE job=?',(int(enabled),job))
            self.authorize(credential_file,{'configure'})
        return {'state':'COMPLETE','job_enabled':enabled,'public_tag_asserted':False}

    def enable_tenant(self,admin_file,enabled):
        self.registry.admin(admin_file);need(type(enabled) is bool)
        with self.mutation('tenant_enabled',{'enabled':enabled}):self.db.execute('UPDATE control SET enabled=? WHERE singleton=1',(int(enabled),))
        return {'state':'COMPLETE','tenant_enabled':enabled,'public_tag_asserted':False}

    def policy(self,job,revision):
        need(type(job) is str and re.fullmatch('[a-z][a-z0-9-]{0,47}',job) is not None and type(revision) is int)
        current=self.db.execute('SELECT revision,enabled FROM jobs WHERE job=?',(job,)).fetchone()
        need(current==(revision,1))
        row=self.db.execute('SELECT raw,hash,sources FROM policies WHERE job=? AND revision=?',(job,revision)).fetchone()
        need(row is not None and type(row[0]) is bytes and len(row[0])<=65536 and sha(row[0])==row[1])
        policy=private_policy.policy(row[0]);need(policy.namespace==self.meta['namespace'] and policy.policy_id==job and policy.revision==revision)
        sources=source_bindings(self.c);need(parse(row[2].encode(),16384)==sources)
        return row[0],policy,sources


@contextmanager
def registry(root):
    try:
        with Capture() as c:yield Registry(root,c)
    except OutputCommitUncertain:raise
    except Exception:raise PrivateInputError('Organization policy unavailable.') from None


def subject(c,path):
    raw=c.read(path,80000);text=raw.decode('utf-8','strict');need(0<len(text)<=private_policy.MAX_TEXT)
    need('\0' not in text)
    frozen=normalize_nfc(text);need(frozen.strip() and len(frozen)<=private_policy.MAX_TEXT)
    return text,sha(raw),sha(frozen.encode('utf-8'))


@boundary
def prepare(root,name,credential_file,job,revision,subject_file,output):
    with registry(root) as r:
        with r.tenant(name) as t:
            actor=t.authorize(credential_file,{'check'});raw,policy,sources=t.policy(job,revision)
            text,raw_hash,nfc_hash=subject(r.c,subject_file)
            value={'format':SELECTION,'registry_id':r.contract['registry_id'],'tenant_id':t.meta['tenant_id'],
                'namespace':name,'offering':t.meta['offering'],'capability_id':actor,'epoch':t.state()[0],
                'job':job,'revision':revision,'policy_sha256':sha(raw),'subject_raw_sha256':raw_hash,
                'subject_nfc_sha256':nfc_hash,'normalization_id':NORMALIZATION_ID,'sources':sources}
            t.authorize(credential_file,{'check'})
            r.c.save(output,value,16384)
    return {'state':'COMPLETE','selection_saved':True,'public_tag_asserted':False}


@boundary
def check(root,name,credential_file,selection_file,subject_file,reviewed=False,output=None):
    need(reviewed is True)
    with registry(root) as r:
        with r.tenant(name) as t:
            actor=t.authorize(credential_file,{'check','export'} if output is not None else {'check'})
            selected=parse(r.c.read(selection_file,16384),16384)
            need(type(selected) is dict and set(selected)=={'format','registry_id','tenant_id','namespace','offering','capability_id','epoch','job','revision','policy_sha256','subject_raw_sha256','subject_nfc_sha256','normalization_id','sources'})
            need(selected['format']==SELECTION and selected['registry_id']==r.contract['registry_id'] and selected['tenant_id']==t.meta['tenant_id']
                and selected['namespace']==name and selected['offering']==t.meta['offering'] and selected['capability_id']==actor
                and type(selected['epoch']) is int and selected['epoch']==t.state()[0] and selected['normalization_id']==NORMALIZATION_ID)
            raw,policy,sources=t.policy(selected['job'],selected['revision']);text,raw_hash,nfc_hash=subject(r.c,subject_file)
            need(selected['policy_sha256']==sha(raw) and selected['sources']==sources and selected['subject_raw_sha256']==raw_hash and selected['subject_nfc_sha256']==nfc_hash)
            context={'format':private_policy.CONTEXT,'namespace':name,'policy_sha256':sha(raw),'subject_sha256':nfc_hash}
            request={'format':'local-organization-policy-job/v1','subject':text,'policy':raw.decode('utf-8'),'context':context}
            start=time.monotonic()
            result=run_worker([sys.executable,'-I','-S','-B',str(ROOT/'tools/organization_policy_worker.py')],input=encoded(request),timeout=3,output_limit=262144)
            need(result.returncode==0)
            observed=parse(result.stdout,262144)
            # Exact bounded replay binds values/counts/completeness, not merely
            # plausible spans or a claimed worker/method hash.
            expected=private_policy.observe(text,raw,context,reviewed=True)
            need(encoded(observed)==encoded(expected) and time.monotonic()-start<=4)
            t.authorize(credential_file,{'check','export'} if output is not None else {'check'})
            r.c.check()
            record={'format':RESULT,'state':'COMPLETE','registry_id':r.contract['registry_id'],'tenant_id':t.meta['tenant_id'],
                'local_qualified_namespace':'local:'+r.contract['registry_id']+':'+t.meta['tenant_id']+':'+name,
                'ownership_contract':CONTRACT,'ownership_claim':'selected_local_owner_control_only',
                'organization_identity_verified':False,'employee_consent_proved':False,'commercial_terms_accepted':False,
                'selection_sha256':sha(encoded(selected)),'subject_raw_sha256':raw_hash,'subject_nfc_sha256':nfc_hash,
                'job':selected['job'],'revision':selected['revision'],'epoch':selected['epoch'],'sources':sources,
                'observation':observed,'public_tag_asserted':False,'compliance_established':False}
            if output is not None:r.c.save(output,record,262144)
            return {'state':'COMPLETE','literal_occurrences':observed['total_observations'],
                'details_saved':output is not None,'public_tag_asserted':False,'compliance_established':False}


@boundary
def enroll(root,name,offering,admin_file):
    with registry(root) as r:return r.enroll(name,offering,admin_file)


@boundary
def grant(root,name,admin_file,roles,seconds,output):
    with registry(root) as r:
        with r.tenant(name,write=True) as t:return t.grant(admin_file,roles,seconds,output)


@boundary
def revoke(root,name,admin_file,credential_file):
    with registry(root) as r:
        with r.tenant(name,write=True) as t:return t.revoke(admin_file,credential_file)


@boundary
def add_policy(root,name,credential_file,policy_file):
    with registry(root) as r:
        with r.tenant(name,write=True) as t:return t.add_policy(credential_file,policy_file)


@boundary
def enable_job(root,name,credential_file,job,enabled):
    with registry(root) as r:
        with r.tenant(name,write=True) as t:return t.enable_job(credential_file,job,enabled)


@boundary
def enable_tenant(root,name,admin_file,enabled):
    with registry(root) as r:
        with r.tenant(name,write=True) as t:return t.enable_tenant(admin_file,enabled)


@boundary
def inspect_tenant(root,name,credential_file,output=None):
    with registry(root) as r:
        with r.tenant(name) as t:
            t.authorize(credential_file,{'view','export'} if output is not None else {'view'})
            jobs=t.db.execute('SELECT job,revision,enabled FROM jobs ORDER BY job LIMIT 9').fetchall()
            need(len(jobs)<=MAX_JOBS)
            if output is not None:
                details={'format':'local-organization-policy-inventory/v1','tenant':t.meta,
                    'epoch':t.state()[0],'jobs':[{'job':row[0],'revision':row[1],'enabled':bool(row[2])} for row in jobs],
                    'events':[{'sequence':row[0],'hash':row[1]} for row in t.db.execute('SELECT sequence,hash FROM events ORDER BY sequence')],
                    'organization_identity_verified':False,'employee_consent_proved':False,'commercial_terms_accepted':False}
                t.authorize(credential_file,{'view','export'})
                r.c.save(output,details,65536)
            return {'state':'COMPLETE','jobs':len(jobs),'details_saved':output is not None,'public_tag_asserted':False}


@boundary
def remove_tenant(root,name,admin_file):
    with registry(root) as r:
        r.admin(admin_file);namespace(name);folder=r.root/'tenants'/name
        fd=r.c.directory(folder);lock,_=r.empty_lock(folder/'access.lock')
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        names=[]
        with os.scandir(fd) as entries:
            for entry in entries:
                need(len(names)<3 and entry.name in ('access.lock','state.sqlite','tenant.json'))
                info=entry.stat(follow_symlinks=False)
                need(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==0o600)
                names.append(entry.name)
        need(set(names)=={'access.lock','state.sqlite','tenant.json'})
        r.c.check();r.c.output_may_exist=True
        for name in ('state.sqlite','tenant.json','access.lock'):os.unlink(name,dir_fd=fd)
        os.rmdir(folder.name,dir_fd=r.tenants_fd);os.fsync(r.tenants_fd)
    return {'state':'COMPLETE','tenant_removed':True,'other_tenants_removed':False,'public_tag_asserted':False}


@boundary
def remove_registry(root,admin_file):
    with registry(root) as r:
        r.admin(admin_file)
        lock,_=r.empty_lock(r.root/'enrollment.lock');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        need(not r.tenant_names())
        names=[]
        with os.scandir(r.fd) as rows:
            for row in rows:
                need(len(names)<3);names.append(row.name)
        need(set(names)=={'registry.json','tenants','enrollment.lock'})
        parent,name=r.c.parent(r.root);r.c.check();r.c.output_may_exist=True
        os.unlink('registry.json',dir_fd=r.fd);os.unlink('enrollment.lock',dir_fd=r.fd);os.rmdir('tenants',dir_fd=r.fd)
        os.rmdir(name,dir_fd=parent);os.fsync(parent)
    return {'state':'COMPLETE','registry_removed':True,'external_credentials_or_exports_removed':False,'public_tag_asserted':False}
