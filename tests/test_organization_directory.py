"""Local gate boundaries; real provider/database acceptance is a separate lab."""
import copy,json,os,time,uuid,sqlite3
from pathlib import Path
from unittest.mock import patch
import pytest
from tools import organization_directory as d

@pytest.fixture
def selected(tmp_path):
    root=tmp_path.resolve();root.chmod(0o700);tenant=str(uuid.uuid4());sub=str(uuid.uuid4());other=str(uuid.uuid4())
    binding={'service':'reader','service_file':str(root/'database.conf'),'pass_file':None,'principal':'audit_reader'}
    cfg={'format':d.FORMAT,'tenant':tenant,'issuer':'https://identity.example.invalid/realms/test','realm':'test','client_id':'aitrust-broker','role_groups':{op:str(uuid.uuid4()) for op in d.OPS},'client_secret':'synthetic-not-a-live-credential','bindings':{sub:binding,other:dict(binding)},'state_file':str(root/'access.sqlite'),'event_days':7,'allow_loopback_http':False,'ca_file':None}
    path=root/'config.json';path.write_bytes(d.encoded(cfg));path.chmod(0o600)
    return cfg,path,sub,other,root

class Provider:
    def __init__(self,sub,roles):self.sub=sub;self.roles=set(roles);self.issued=int(time.time())-1;self.failed=False
    def current(self,token):
        if self.failed:raise d.Refused('provider_unavailable')
        return self.sub,self.issued,self.roles
    def revoke(self,session):
        if self.failed:raise d.Refused('provider_unavailable')

class Store:
    def __init__(self,tenant):self.tenant=tenant;self.opened=0;self.reviews=[]
    def factory(self,*a):self.opened+=1;return self
    def sql(self,s):assert s=='SELECT current_user;';return 'audit_reader'
    def call(self,op,*a):
        if op=='snapshot':return {'tenant':self.tenant}
        self.reviews.append(a);return {'recorded':True}
    def export(self):return {'header':{'tenant':self.tenant},'records':[],'events':[]}

def prepared(selected,roles):
    cfg,path,sub,other,root=selected;p=Provider(sub,roles);store=Store(cfg['tenant']);b=d.Broker(d.config(path),provider=p,store_factory=store.factory);b.journal.initialize();return b,p,store

def request(selected,op='view',args=None,token='invented-token'):
    return {'tenant':selected[0]['tenant'],'operation':op,'token':token,'arguments':{} if args is None else args}

def test_config_accepts_https_and_private_exact_schema(selected):assert d.config(selected[1])==selected[0]

@pytest.mark.parametrize('field,value',[('issuer','http://remote.example/realms/test'),('issuer','https://user:password@identity.example/realms/test'),('issuer','https://identity.example/realms/test?redirect=other'),('issuer','https://identity.example/realms/../test'),('issuer','https://identity.example/realms/%74est'),('event_days',0),('event_days',True),('allow_loopback_http',1),('realm','test/other'),('client_id','bad&client')])
def test_unsafe_provider_config_refused(selected,field,value):
    cfg,path,*_=selected;cfg[field]=value;path.write_bytes(d.encoded(cfg))
    with pytest.raises(Exception):d.config(path)

def test_loopback_lab_is_explicit(selected):
    cfg,path,*_=selected;cfg['issuer']='http://127.0.0.1:18080/realms/test';path.write_bytes(d.encoded(cfg))
    with pytest.raises(Exception):d.config(path)
    cfg['allow_loopback_http']=True;path.write_bytes(d.encoded(cfg));assert d.config(path)['allow_loopback_http'] is True

@pytest.mark.parametrize('kind',['public','symlink','hardlink','extra_field','duplicate_json'])
def test_private_configuration_boundaries(selected,kind):
    cfg,path,sub,other,root=selected
    if kind=='public':path.chmod(0o644)
    elif kind=='symlink':original=root/'original';path.rename(original);path.symlink_to(original)
    elif kind=='hardlink':os.link(path,root/'second')
    elif kind=='extra_field':cfg['token']='invented';path.write_bytes(d.encoded(cfg))
    else:path.write_bytes(b'{"format":"one","format":"two"}')
    with pytest.raises(Exception):d.config(path)

@pytest.mark.parametrize('op',['view','export','review','configure'])
def test_each_permission_has_a_working_job(selected,op):
    b,p,s=prepared(selected,[d.ROLES[op]])
    args={'id':'a'*64,'decision':'disagree','reason':'false_alarm'} if op=='review' else {'subject':selected[3],'action':'revoke'} if op=='configure' else {}
    r=b.dispatch(request(selected,op,args));assert r is not None
    assert s.opened==(0 if op=='configure' else 1)

@pytest.mark.parametrize('op',['view','export','review','configure'])
def test_missing_current_role_denies_before_database(selected,op):
    b,p,s=prepared(selected,[])
    with pytest.raises(Exception):b.dispatch(request(selected,op))
    assert s.opened==0

def test_directory_role_removal_is_applied_on_the_next_call(selected):
    b,p,s=prepared(selected,[d.ROLES['view']]);b.dispatch(request(selected));p.roles.clear()
    with pytest.raises(Exception):b.dispatch(request(selected))
    assert s.opened==1

def test_wrong_tenant_or_unknown_subject_never_opens_store(selected):
    b,p,s=prepared(selected,[d.ROLES['view']]);r=request(selected);r['tenant']=str(uuid.uuid4())
    with pytest.raises(Exception):b.dispatch(r)
    p.sub=str(uuid.uuid4())
    with pytest.raises(Exception):b.dispatch(request(selected))
    assert s.opened==0

def test_database_principal_or_tenant_mismatch_refused(selected):
    b,p,s=prepared(selected,[d.ROLES['view']]);s.tenant=str(uuid.uuid4())
    with pytest.raises(Exception):b.dispatch(request(selected))
    s.tenant=selected[0]['tenant'];s.sql=lambda _: 'privileged_user'
    with pytest.raises(Exception):b.dispatch(request(selected))

def test_extra_fields_arbitrary_operations_and_review_values_refused(selected):
    b,p,s=prepared(selected,list(d.ROLES.values()))
    for row in [{**request(selected),'raw_answer':'must-not-enter'},request(selected,'issue-IV'),request(selected,'review',{'id':'a'*64,'decision':'certified','reason':'other'})]:
        with pytest.raises(Exception):b.dispatch(row)
    assert not s.reviews

def test_provider_outage_fails_closed_without_store_or_personal_import(selected):
    b,p,s=prepared(selected,[d.ROLES['view']]);p.failed=True
    with pytest.raises(Exception):b.dispatch(request(selected))
    assert s.opened==0
    raw=Path('scripts/check-ps.py').read_text();assert 'organization_directory' not in raw and 'keycloak' not in raw.lower()

def test_local_logout_survives_provider_outage_and_process_restart(selected):
    b,p,s=prepared(selected,[d.ROLES['view']]);p.failed=True
    session={'format':'directory-session/v1','issuer':selected[0]['issuer'],'client_id':selected[0]['client_id'],'access_token':'invented-token','refresh_token':'invented-refresh'}
    r=b.logout(session);assert r=={'local_logout':True,'provider_revocation':'unavailable'}
    p.failed=False;b=d.Broker(d.config(selected[1]),provider=p,store_factory=s.factory)
    with pytest.raises(Exception):b.dispatch(request(selected))
    assert s.opened==0

def test_compromised_admin_recovery_fences_old_tokens_and_cannot_be_undone_by_configure(selected,monkeypatch):
    b,p,s=prepared(selected,[d.ROLES['configure']]);old=selected[2];p.sub=selected[3]
    b.journal.recover(old,'replacement-session',p)
    with pytest.raises(Exception):b.dispatch(request(selected,'configure',{'subject':old,'action':'restore'}))
    later=int(time.time())+d.CLOCK_SKEW_SECONDS+2;monkeypatch.setattr(d.time,'time',lambda:later);p.issued=later
    with pytest.raises(Exception):b.dispatch(request(selected,'configure',{'subject':old,'action':'restore'}))
    p.sub=old
    with pytest.raises(Exception):b.dispatch(request(selected,'configure',{'subject':selected[3],'action':'revoke'}))

def test_self_recovery_and_non_admin_replacement_refused(selected):
    b,p,s=prepared(selected,[d.ROLES['configure']])
    with pytest.raises(Exception):b.journal.recover(selected[2],'replacement',p)
    p.sub=selected[3];p.roles.clear()
    with pytest.raises(Exception):b.journal.recover(selected[2],'replacement',p)

def test_local_revoke_and_restore_are_separate_from_provider_roles(selected):
    b,p,s=prepared(selected,list(d.ROLES.values()));p.sub=selected[3]
    b.dispatch(request(selected,'configure',{'subject':selected[2],'action':'revoke'}));p.sub=selected[2]
    with pytest.raises(Exception):b.dispatch(request(selected))
    p.sub=selected[3];b.dispatch(request(selected,'configure',{'subject':selected[2],'action':'restore'}));p.sub=selected[2];b.dispatch(request(selected))
    assert s.opened==1

def test_journal_has_no_token_identity_or_answer_and_event_expiry_runs(selected):
    b,p,s=prepared(selected,[d.ROLES['view']]);b.dispatch(request(selected));path=Path(selected[0]['state_file'])
    raw=path.read_bytes();assert b'invented-token' not in raw and selected[2].encode() not in raw and selected[0]['client_secret'].encode() not in raw
    with b.journal.db() as db:
        db.execute('INSERT INTO events(at,actor,operation,outcome) VALUES(0,?,?,?)',('old','view','allowed'))
    b.dispatch(request(selected))
    with b.journal.db() as db:assert not db.execute('SELECT 1 FROM events WHERE at=0').fetchone()
    assert stat_mode(path)==0o600

def stat_mode(path):return path.stat().st_mode&0o777

def test_state_reinitialize_or_symlink_refused(selected):
    b,p,s=prepared(selected,[d.ROLES['view']])
    with pytest.raises(Exception):b.journal.initialize()
    path=Path(selected[0]['state_file']);original=path.with_name('original.sqlite');path.rename(original);path.symlink_to(original)
    with pytest.raises(Exception):b.dispatch(request(selected))

def test_cross_origin_discovery_endpoint_redirect_and_encoded_admin_path_refused(selected):
    p=d.Provider(d.config(selected[1]))
    for url in ['https://attacker.example/realms/test/token',selected[0]['issuer']+'/token?redirect=x',selected[0]['issuer']+'/%2e%2e/token']:
        with pytest.raises(Exception):p.url(url)
    with pytest.raises(Exception):d.NoRedirect().redirect_request(None,None,None,None,None,None)


def test_private_material_in_another_git_checkout_is_refused(selected):
    cfg,path,sub,other,root=selected
    other_checkout=root/'different-checkout';other_checkout.mkdir(mode=0o700);(other_checkout/'.git').write_text('gitdir: arbitrary')
    target=other_checkout/'config.json';target.write_bytes(d.encoded(cfg));target.chmod(0o600)
    with pytest.raises(Exception):d.config(target)
    cfg['state_file']=str(other_checkout/'state.sqlite');path.write_bytes(d.encoded(cfg))
    with pytest.raises(Exception):d.config(path)


def test_provider_arrays_use_the_network_contract_without_relaxing_audit_records():
    assert d.provider_json(b'[{"id":"group"}]')==[{'id':'group'}]
    with pytest.raises(Exception):d.parse(b'[{"id":"group"}]')

@pytest.mark.parametrize('raw',[b'null',b'123',b'{"active":true,"active":false}',b'{"score":NaN}',b'\xff',b'['+b' '*262144+b']'])
def test_provider_json_refuses_ambiguous_unbounded_or_nonfinite_input(raw):
    with pytest.raises(Exception):d.provider_json(raw)

def network_fixture(selected,**token_overrides):
    cfg,path,sub,other,root=selected
    provider=d.Provider(d.config(path));base=cfg['issuer']
    metadata={'issuer':base,'device_authorization_endpoint':base+'/device','token_endpoint':base+'/token','introspection_endpoint':base+'/introspect','revocation_endpoint':base+'/revoke'}
    token={'active':True,'iss':base,'client_id':cfg['client_id'],'aud':[cfg['client_id']],'exp':int(time.time())+300,'iat':int(time.time())-1,'sub':sub,**token_overrides}
    def read(url,fields=None,bearer=None,**kwargs):
        if url.endswith('openid-configuration'):return d.provider_json(d.encoded(metadata))
        if url.endswith('/introspect'):return d.provider_json(d.encoded(token))
        if url.endswith('/token'):return d.provider_json(b'{"access_token":"synthetic-service-token"}')
        if url.endswith('/groups'):return d.provider_json(d.encoded([{'id':cfg['role_groups']['view'],'name':'an-editable-name-is-not-a-key'}]))
        return d.provider_json(d.encoded({'id':sub,'enabled':True}))
    provider.request=read
    return provider

def test_complete_provider_contract_accepts_group_array_and_immutable_group_binding(selected):
    provider=network_fixture(selected);sub,issued,roles=provider.current('synthetic-user-token')
    assert sub==selected[2] and roles=={d.ROLES['view']}

@pytest.mark.parametrize('overrides',[{'active':False},{'iss':'https://another.example/realms/test'},{'client_id':'another-client'},{'aud':['another-client']},{'exp':0},{'iat':int(time.time())-1000},{'sub':str(uuid.uuid4())}])
def test_complete_provider_contract_rejects_bad_identity_or_timing(selected,overrides):
    provider=network_fixture(selected,**overrides)
    with pytest.raises(Exception):provider.current('synthetic-user-token')


@pytest.mark.parametrize('command',['begin','finish','call'])
def test_cli_refuses_other_checkout_output_before_provider_or_credentials(selected,command,monkeypatch,capsys):
    import runpy,sys
    root=selected[4];checkout=root/'other-checkout';checkout.mkdir(mode=0o700);(checkout/'.git').write_text('gitdir: other')
    script=Path(__file__).resolve().parents[1]/'scripts/organization-directory.py'
    cli=runpy.run_path(str(script));called=[]
    cli['main'].__globals__['config']=lambda path:called.append(path)
    args=[str(script),'--config',str(selected[1]),command,'--output',str(checkout/'private')]
    if command=='finish':args+=['--pending',str(root/'not-read.json')]
    monkeypatch.setattr(sys,'argv',args)
    assert cli['main']()==2 and called==[] and not (checkout/'private').exists()
    assert 'organization_directory_contract_refused' in capsys.readouterr().err


def test_busy_logout_journal_can_roll_over_and_recover(selected,monkeypatch):
    b,p,s=prepared(selected,[d.ROLES['configure']]);now=int(time.time())
    with b.journal.db() as db:
        db.executemany('INSERT INTO logged_out VALUES(?,?)',[(d.digest(('previously-logged-out-token' if i==0 else str(i)).encode()),now) for i in range(10000)])
        db.executemany('INSERT INTO events(at,actor,operation,outcome) VALUES(?,?,?,?)',[(now,'a'*64,'configure','allowed') for _ in range(10000)])
    assert Path(selected[0]['state_file']).stat().st_size>2_000_000
    assert b.journal.logout('additional-realistic-token')=={'local_logout':True}
    with b.journal.db() as db:
        with pytest.raises(d.Refused):b.journal.allowed(db,selected[2],'previously-logged-out-token',now+3)
    later=now+d.CLOCK_SKEW_SECONDS+2;monkeypatch.setattr(d.time,'time',lambda:later);p.issued=later
    result=b.journal.recover(selected[3],'fresh-replacement-token',p)
    assert result['recovered'] is True
    with b.journal.db() as db:
        assert db.execute('SELECT count(*) FROM logged_out').fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM events').fetchone()[0]<=10000


@pytest.mark.parametrize('skew',[1,5])
def test_recovery_fence_covers_the_provider_accepted_future_issue_interval(selected,monkeypatch,skew):
    now=int(time.time());monkeypatch.setattr(d.time,'time',lambda:now)
    # The same provider contract explicitly accepts this issue timestamp.
    _,issued,_=network_fixture(selected,iat=now+skew).current('synthetic-clock-token')
    assert issued==now+skew
    b,p,s=prepared(selected,[d.ROLES['configure'],d.ROLES['view']]);p.issued=issued
    b.journal.recover(selected[3],'pre-recovery-session',p)
    with pytest.raises(d.Refused):b.dispatch(request(selected,token='pre-recovery-session'))
    later=now+d.CLOCK_SKEW_SECONDS+2;monkeypatch.setattr(d.time,'time',lambda:later);p.issued=later
    assert b.dispatch(request(selected,token='fresh-after-fence'))['records']==[]


@pytest.mark.parametrize('issuer_offset',[-5,5])
def test_documented_login_wait_covers_either_clock_direction(selected,monkeypatch,issuer_offset):
    now=int(time.time());monkeypatch.setattr(d.time,'time',lambda:now)
    b,p,s=prepared(selected,[d.ROLES['configure'],d.ROLES['view']]);result=b.journal.recover(selected[3],'old-session',p)
    assert result['new_login_wait_seconds']==d.LOGIN_WAIT_SECONDS==12
    later=now+d.LOGIN_WAIT_SECONDS;monkeypatch.setattr(d.time,'time',lambda:later);p.issued=later+issuer_offset
    assert network_fixture(selected,iat=p.issued).current('fresh-provider-token')[1]==p.issued
    assert b.dispatch(request(selected,token='fresh-login'))['records']==[]
