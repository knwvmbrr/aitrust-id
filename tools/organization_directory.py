"""Operator-owned OIDC directory gate for private audit records; no web listener."""
from contextlib import contextmanager
import hashlib,hmac,json,os,re,secrets,sqlite3,ssl,stat,time,uuid
from pathlib import Path
from urllib.parse import urlsplit,urlencode,quote
from urllib.request import Request,build_opener,ProxyHandler,HTTPRedirectHandler,HTTPSHandler
from tools.organization_audit import ROOT,parse,encoded,require,digest
from tools.organization_audit_store import private_file as audit_private_file,Store
from tools.blind_review_io import directory,create

def outside_git(path):
    path=Path(path).absolute()
    check(not path.is_symlink())
    resolved=path.resolve()
    check(not any((parent/'.git').exists() for parent in [resolved.parent,*resolved.parents]))
    return resolved

def private_file(path):
    outside_git(path)
    return audit_private_file(path)

FORMAT='organization-directory/v1'
ROLES={'view':'aitrust-view','export':'aitrust-export','review':'aitrust-review','configure':'aitrust-configure'}
OPS=set(ROLES)
class Refused(ValueError):pass

def check(ok):
    if not ok:raise Refused('Organization access unavailable')

def identifier(value):
    check(type(value) is str and str(uuid.UUID(value))==value);return value

def secret(value):
    check(type(value) is str and 1<=len(value)<=16384 and all(33<=ord(c)<=126 for c in value));return value

def config(path):
    d=parse(private_file(path));check(type(d) is dict and set(d)=={'format','tenant','issuer','realm','client_id','directory_client_uuid','client_secret','bindings','state_file','event_days','allow_loopback_http','ca_file'})
    check(d['format']==FORMAT);identifier(d['tenant']);identifier(d['directory_client_uuid'])
    check(type(d['event_days']) is int and 1<=d['event_days']<=30 and type(d['allow_loopback_http']) is bool)
    check(type(d['realm']) is str and re.fullmatch('[a-zA-Z0-9_-]{1,64}',d['realm']))
    check(type(d['client_id']) is str and re.fullmatch('[a-zA-Z0-9_-]{1,64}',d['client_id']));secret(d['client_secret'])
    u=urlsplit(d['issuer']);check(u.hostname and not u.username and not u.password and not u.query and not u.fragment)
    check(u.path.endswith('/realms/'+d['realm']) and re.fullmatch(r'/[a-zA-Z0-9_/-]+',u.path) and '..' not in u.path)
    check(u.scheme=='https' or d['allow_loopback_http'] is True and u.scheme=='http' and u.hostname=='127.0.0.1')
    check(d['issuer']==u.geturl().rstrip('/'))
    check(type(d['bindings']) is dict and 1<=len(d['bindings'])<=1000)
    for sub,b in d['bindings'].items():
        identifier(sub);check(type(b) is dict and set(b)=={'service','service_file','pass_file','principal'})
        check(re.fullmatch('[a-zA-Z0-9_-]{1,64}',b['service']) and re.fullmatch('[a-z_][a-z0-9_]{0,62}',b['principal']))
        check(type(b['service_file']) is str and Path(b['service_file']).is_absolute())
        check(b['pass_file'] is None or type(b['pass_file']) is str and Path(b['pass_file']).is_absolute())
        outside_git(b['service_file'])
        if b['pass_file'] is not None:outside_git(b['pass_file'])
    check(d['ca_file'] is None or type(d['ca_file']) is str and Path(d['ca_file']).is_absolute())
    if d['ca_file'] is not None:private_file(d['ca_file'])
    p=Path(d['state_file']);check(p.is_absolute());p=outside_git(p);d['state_file']=str(p)
    with directory(p.parent,ROOT):pass
    return d

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise Refused('Organization access unavailable')

class Provider:
    def __init__(self,c):
        self.c=c;self.last_status=None;context=ssl.create_default_context()
        if c['ca_file'] is not None:context.load_verify_locations(cadata=private_file(c['ca_file']).decode('ascii'))
        self.opener=build_opener(ProxyHandler({}),NoRedirect(),HTTPSHandler(context=context))
        self.origin=urlsplit(c['issuer']);self.base=c['issuer'].rsplit('/realms/',1)[0]
    def url(self,url,*,admin=False):
        check(type(url) is str and len(url)<=2048)
        u=urlsplit(url);check(u.scheme==self.origin.scheme and u.netloc==self.origin.netloc and not u.query and not u.fragment and not u.username and not u.password)
        prefix=self.base+'/admin/realms/'+self.c['realm']+'/' if admin else self.c['issuer']+'/'
        check(url.startswith(prefix) and '%' not in u.path and '..' not in u.path);return url
    def request(self,url,fields=None,bearer=None,*,admin=False,allow_empty=False):
        self.url(url,admin=admin);headers={'Accept':'application/json'}
        if bearer:headers['Authorization']='Bearer '+secret(bearer)
        body=None if fields is None else urlencode(fields).encode()
        if body is not None:headers['Content-Type']='application/x-www-form-urlencoded'
        try:
            with self.opener.open(Request(url,data=body,headers=headers),timeout=5) as response:
                self.last_status=response.status
                check(response.status==200 and response.geturl()==url)
                raw=response.read(262145)
                return {} if allow_empty and raw==b'' else parse(raw,262144)
        except Exception as error:
            self.last_status=getattr(error,'code',self.last_status)
            raise Refused('Organization access unavailable') from None
    def discovery(self):
        d=self.request(self.c['issuer']+'/.well-known/openid-configuration');check(type(d) is dict and d.get('issuer')==self.c['issuer'])
        for k in ('device_authorization_endpoint','token_endpoint','introspection_endpoint','revocation_endpoint'):self.url(d.get(k))
        return d
    def post(self,discovery,key,fields):
        return self.request(discovery[key],{'client_id':self.c['client_id'],'client_secret':self.c['client_secret'],**fields},allow_empty=key=='revocation_endpoint')
    def current(self,token):
        d=self.discovery();r=self.post(d,'introspection_endpoint',{'token':secret(token)})
        check(type(r) is dict and r.get('active') is True and r.get('iss')==self.c['issuer'] and r.get('client_id')==self.c['client_id'])
        aud=r.get('aud');check(aud==self.c['client_id'] or type(aud) is list and self.c['client_id'] in aud)
        check(type(r.get('exp')) is int and type(r.get('iat')) is int and r['iat']<=time.time()+5 and r['exp']>time.time() and time.time()-r['iat']<=900)
        sub=identifier(r.get('sub'));check(sub in self.c['bindings'])
        service=self.post(d,'token_endpoint',{'grant_type':'client_credentials'});service_token=secret(service['access_token'])
        base=self.base+'/admin/realms/'+self.c['realm']+'/users/'+sub
        user=self.request(base,bearer=service_token,admin=True);check(user.get('id')==sub and user.get('enabled') is True)
        roles=self.request(base+'/role-mappings/clients/'+self.c['directory_client_uuid']+'/composite',bearer=service_token,admin=True)
        check(type(roles) is list and len(roles)<=256 and all(type(x) is dict and type(x.get('name')) is str for x in roles))
        return sub,r['iat'],{x['name'] for x in roles}
    def begin(self):
        d=self.discovery();r=self.post(d,'device_authorization_endpoint',{'scope':'openid'})
        for k in ('device_code','user_code'):secret(r.get(k))
        uri=r.get('verification_uri');self.url(uri)
        check(type(r.get('expires_in')) is int and 1<=r['expires_in']<=1800)
        interval=r.get('interval',5);check(type(interval) is int and 1<=interval<=30)
        return {'format':'directory-device-pending/v1','issuer':self.c['issuer'],'client_id':self.c['client_id'],'device_code':r['device_code'],'user_code':r['user_code'],'verification_uri':uri,'expires_at':int(time.time())+min(r['expires_in'],600),'interval':max(5,interval)}
    def finish_once(self,pending):
        check(set(pending)=={'format','issuer','client_id','device_code','user_code','verification_uri','expires_at','interval'})
        check(pending['format']=='directory-device-pending/v1' and pending['issuer']==self.c['issuer'] and pending['client_id']==self.c['client_id'] and type(pending['expires_at']) is int and pending['expires_at']>time.time())
        # The interactive CLI polls only after the user completes provider approval.
        r=self.post(self.discovery(),'token_endpoint',{'grant_type':'urn:ietf:params:oauth:grant-type:device_code','device_code':secret(pending['device_code'])})
        access=secret(r['access_token']);refresh=secret(r['refresh_token']);self.current(access)
        return {'format':'directory-session/v1','issuer':self.c['issuer'],'client_id':self.c['client_id'],'access_token':access,'refresh_token':refresh}
    def revoke(self,session):
        check(type(session) is dict and set(session)=={'format','issuer','client_id','access_token','refresh_token'})
        check(session['format']=='directory-session/v1' and session['issuer']==self.c['issuer'] and session['client_id']==self.c['client_id'])
        d=self.discovery()
        for key in ('refresh_token','access_token'):
            self.post(d,'revocation_endpoint',{'token':secret(session[key]),'token_type_hint':key})

class Journal:
    def __init__(self,c):self.c=c;self.path=Path(c['state_file'])
    def initialize(self):
        with directory(self.path.parent,ROOT) as parent:
            fd=os.open(self.path.name,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600,dir_fd=parent);os.close(fd)
        with self.db() as db:
            db.execute('PRAGMA auto_vacuum=FULL')
            db.executescript('CREATE TABLE control(singleton INTEGER PRIMARY KEY CHECK(singleton=1),tenant TEXT NOT NULL,salt TEXT NOT NULL,fence INTEGER NOT NULL); CREATE TABLE blocked(subject TEXT PRIMARY KEY,compromised INTEGER NOT NULL); CREATE TABLE logged_out(token TEXT PRIMARY KEY,at INTEGER NOT NULL); CREATE TABLE events(id INTEGER PRIMARY KEY,at INTEGER NOT NULL,actor TEXT NOT NULL,operation TEXT NOT NULL,outcome TEXT NOT NULL);')
            db.execute('INSERT INTO control VALUES(1,?,?,0)',(self.c['tenant'],secrets.token_hex(32)))
        return {'initialized':True,'collection_enabled':False}
    @contextmanager
    def db(self):
        # Owner-private parent and no-follow regular-file read are required before SQLite.
        private_file(self.path)
        db=sqlite3.connect('file:'+quote(str(self.path),safe='/')+'?mode=rw',uri=True,timeout=5)
        try:
            db.execute('PRAGMA trusted_schema=OFF');db.execute('BEGIN IMMEDIATE')
            yield db;db.commit()
        except BaseException:db.rollback();raise
        finally:db.close()
    def control(self,db):
        row=db.execute('SELECT tenant,salt,fence FROM control WHERE singleton=1').fetchone();check(row is not None and row[0]==self.c['tenant']);return row
    def pseudonym(self,db,value):return hmac.new(bytes.fromhex(self.control(db)[1]),value.encode(),'sha256').hexdigest()
    def event(self,db,actor,op,outcome):
        now=int(time.time());db.execute('DELETE FROM events WHERE at<?',(now-self.c['event_days']*86400,))
        db.execute('DELETE FROM logged_out WHERE at<?',(now-1800,))
        db.execute('INSERT INTO events(at,actor,operation,outcome) VALUES(?,?,?,?)',(now,self.pseudonym(db,actor),op,outcome))
        db.execute('DELETE FROM events WHERE id NOT IN (SELECT id FROM events ORDER BY id DESC LIMIT 10000)')
    def allowed(self,db,sub,token,issued):
        check(not db.execute('SELECT 1 FROM blocked WHERE subject=?',(self.pseudonym(db,sub),)).fetchone())
        check(not db.execute('SELECT 1 FROM logged_out WHERE token=?',(digest(token.encode()),)).fetchone())
        check(issued>self.control(db)[2])
    def logout(self,token):
        secret(token)
        with self.db() as db:
            self.control(db)
            if db.execute('SELECT count(*) FROM logged_out').fetchone()[0]>=10000:
                db.execute('UPDATE control SET fence=max(fence,?) WHERE singleton=1',(int(time.time()),))
                db.execute('DELETE FROM logged_out')
            db.execute('INSERT OR IGNORE INTO logged_out VALUES(?,?)',(digest(token.encode()),int(time.time())));self.event(db,'local-session','logout','blocked')
        return {'local_logout':True}
    def recover(self,compromised,replacement,provider):
        identifier(compromised);check(compromised in self.c['bindings'])
        sub,issued,roles=provider.current(secret(replacement));check(sub!=compromised and ROLES['configure'] in roles)
        with self.db() as db:
            self.allowed(db,sub,replacement,issued)
            db.execute('INSERT INTO blocked VALUES(?,1) ON CONFLICT(subject) DO UPDATE SET compromised=1',(self.pseudonym(db,compromised),))
            db.execute('UPDATE control SET fence=? WHERE singleton=1',(int(time.time()),));self.event(db,sub,'owner-recovery','fenced')
        return {'recovered':True,'pre_recovery_tokens_blocked':True,'new_login_required':True}

class Broker:
    def __init__(self,c,*,provider=None,store_factory=Store):
        self.c=c;self.provider=provider if provider is not None else Provider(c);self.journal=Journal(c);self.store_factory=store_factory
    def dispatch(self,request):
        check(type(request) is dict and set(request)=={'tenant','operation','token','arguments'})
        check(request['tenant']==self.c['tenant'] and request['operation'] in OPS and type(request['arguments']) is dict)
        op=request['operation'];token=secret(request['token']);sub,issued,roles=self.provider.current(token)
        check(ROLES[op] in roles and sub in self.c['bindings'])
        # Keep the security-state transaction through database access so local
        # logout/recovery cannot pass between this authorization and its effect.
        with self.journal.db() as local:
            self.journal.allowed(local,sub,token,issued);args=request['arguments']
            if op=='configure':
                check(set(args)=={'subject','action'} and args['action'] in ('revoke','restore'))
                target=identifier(args['subject']);check(target in self.c['bindings']);key=self.journal.pseudonym(local,target)
                if args['action']=='revoke':local.execute('INSERT OR IGNORE INTO blocked VALUES(?,0)',(key,))
                else:
                    check(not local.execute('SELECT 1 FROM blocked WHERE subject=? AND compromised=1',(key,)).fetchone())
                    local.execute('DELETE FROM blocked WHERE subject=?',(key,))
                result={'updated':True,'action':args['action'],'independent_review_status_granted':False}
            else:
                binding=self.c['bindings'][sub]
                store=self.store_factory(binding['service'],binding['service_file'],binding['pass_file'])
                check(store.sql('SELECT current_user;')==binding['principal'])
                header=store.call('snapshot','header','',None);check(header['tenant']==self.c['tenant'])
                if op in ('view','export'):
                    check(args=={});packet=store.export();check(packet['header']['tenant']==self.c['tenant'])
                    result=packet if op=='export' else {'records':packet['records'],'organization_feedback_only':True}
                else:
                    check(set(args)=={'id','decision','reason'} and re.fullmatch('[a-f0-9]{64}',args['id']) and args['decision'] in ('agree','disagree','uncertain') and args['reason'] in ('supported','missed_pattern','false_alarm','insufficient_context','other'))
                    result=store.call('review',args['id'],args['decision'],args['reason'])
            self.journal.event(local,sub,op,'allowed')
            return result
    def logout(self,session):
        check(type(session) is dict and set(session)=={'format','issuer','client_id','access_token','refresh_token'} and session.get('format')=='directory-session/v1' and session.get('issuer')==self.c['issuer'] and session.get('client_id')==self.c['client_id'])
        secret(session['refresh_token'])
        result=self.journal.logout(secret(session['access_token']))
        try:self.provider.revoke(session);result['provider_revocation']='completed'
        except Exception:result['provider_revocation']='unavailable'
        return result
