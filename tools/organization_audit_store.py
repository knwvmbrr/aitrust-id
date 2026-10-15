"""Fixed PostgreSQL audit operations. No listener, credentials in argv, or automatic intake."""
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import uuid
from datetime import datetime, timezone
from tools.organization_audit import ROOT, SCHEMA, parse, require, encoded, digest, hash_value, validate_metadata, fixed


def literal(value):
    require(type(value) is str and '\x00' not in value)
    return "'"+value.replace("'","''")+"'"


def private_file(path):
    from tools.blind_review_io import directory
    path=Path(path).absolute()
    with directory(path.parent,ROOT) as parent:
        fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
        try:
            info=os.fstat(fd)
            require(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid() and info.st_nlink==1 and not info.st_mode&0o077 and info.st_size<=2_000_000)
            raw=os.read(fd,2_000_001);require(len(raw)==info.st_size)
            after=os.fstat(fd);require((info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns))
            return raw
        finally:os.close(fd)


def bounded_command(argv,env,*,input=None,timeout=25,diagnostics=None):
    import tempfile,signal
    require(input is None or type(input) is bytes and len(input)<=3_000_000)
    with tempfile.TemporaryFile() as out:
        def limits():
            import resource
            resource.setrlimit(resource.RLIMIT_FSIZE,(2_000_000,2_000_000))
        process=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=out,
          stderr=diagnostics if diagnostics is not None else subprocess.DEVNULL,
          env=env,start_new_session=True,preexec_fn=limits)
        try:process.communicate(input,timeout=timeout)
        except BaseException:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            process.wait();raise
        require(process.returncode==0)
        out.seek(0);raw=out.read(2_000_001);require(len(raw)<=2_000_000)
        return raw


class Store:
    def __init__(self, service, service_file, pass_file=None, *, diagnostics=None):
        require(type(service) is str and re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',service))
        self.diagnostics=diagnostics
        self.service_raw=private_file(service_file)
        self.pass_raw=private_file(pass_file) if pass_file else b''
        self.env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','TZ':'UTC',
                  'PGSERVICEFILE':str(Path(service_file).absolute()),'PGPASSFILE':str(Path(pass_file).absolute()) if pass_file else '/dev/null',
                  'PGOPTIONS':'-c statement_timeout=10000 -c lock_timeout=5000 -c standard_conforming_strings=on -c timezone=UTC'}
        psql=shutil.which('psql');require(psql is not None)
        self.argv=[psql,'-XqAt','-v','ON_ERROR_STOP=1','-v','VERBOSITY=terse',
                   '--dbname','service='+service+' sslmode=verify-full connect_timeout=5']

    def sql(self, sql):
        require(type(sql) is str and len(sql.encode())<=3_000_000)
        # Private temporary output bounds disk growth and keeps diagnostics out of public logs.
        import tempfile
        with tempfile.TemporaryDirectory(prefix='aitrust-audit-credentials-') as secret_dir:
            secret_dir=Path(secret_dir);secret_dir.chmod(0o700)
            child_env=dict(self.env)
            for key,contents in [('PGSERVICEFILE',self.service_raw),('PGPASSFILE',self.pass_raw)]:
                target=secret_dir/key;fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                with os.fdopen(fd,'wb') as stream:stream.write(contents)
                child_env[key]=str(target)
            return bounded_command(self.argv,child_env,input=sql.encode(),diagnostics=self.diagnostics).decode('utf-8','strict').strip()

    def call(self, name, *args):
        require(name in {'policy','append','review','remove_record','expire','snapshot'})
        values=[('NULL' if v is None else literal(v)) for v in args]
        raw=self.sql('SELECT aitrust_audit.'+name+'('+','.join(values)+');')
        return parse(raw.encode(),2_000_000) if raw.startswith('{') else json.loads(raw)

    def export(self):
        header=self.call('snapshot','header','',None);head=hash_value(header['head'])
        pages={}
        for section,cursor in [('records',''),('events','0')]:
            rows=[]
            while True:
                page=self.call('snapshot',section,cursor,head)
                require(type(page) is list)
                if not page:break
                rows+=page;require(len(rows)<=10000)
                cursor=str(page[-1]['id' if section=='records' else 'seq'])
                require(len(encoded({'header':header,**pages,section:rows}))<=20_000_000)
            pages[section]=rows
        end=self.call('snapshot','header','',head)
        require(all(end[k]==header[k] for k in ('head','base_seq','base_hash','active_count','event_count','policy_sha256')))
        require(all(datetime.fromisoformat(r['expires_at'])>datetime.fromisoformat(end['captured_at']) for r in pages['records']))
        require(len(pages['records'])==header['active_count'] and len(pages['events'])==header['event_count'])
        packet={'header':header,**pages}
        verify_export(packet)
        return packet


def verify_export(packet, checkpoint=None):
    require(type(packet) is dict and set(packet)=={'header','records','events'})
    require(len(encoded(packet))<=20_000_000)
    h=packet['header'];require(h['format']=='organization-audit-export/v1' and h['metadata_only'] is True and h['independent_witness'] is False)
    require(digest(encoded(h['policy']))==h['policy_sha256'])
    seq=h['base_seq'];previous=hash_value(h['base_hash'])
    require(type(seq) is int and seq>=0 and len(packet['events'])==h['event_count'] and len(packet['records'])==h['active_count'])
    for event in packet['events']:
        fixed(event,{'seq','material','previous','hash','created_at'})
        require(type(event['seq']) is int)
        seq+=1;require(event['seq']==seq and event['previous']==previous)
        material=event['material'];require(type(material) is str)
        require(event['hash']==digest(bytes.fromhex(previous)+material.encode()))
        row=parse(material.encode());fixed(row,{'sequence','action','record','detail','principal','at'})
        require(type(row['sequence']) is int and row['sequence']==seq)
        require(type(event['created_at']) is str and type(row['at']) is str)
        visible=datetime.fromisoformat(event['created_at']);protected=datetime.fromisoformat(row['at'])
        require(visible.tzinfo is not None and protected.tzinfo is not None and visible==protected)
        require(row['action'] in {'append','review','remove','expire'})
        previous=event['hash']
    require(previous==h['head'] and seq+1==h['next_seq'])
    seen=set();appends={}
    for event in packet['events']:
        row=parse(event['material'].encode())
        if row['action']=='append':
            require(row['record'] not in appends);appends[row['record']]=row
    for record in packet['records']:
        validate_metadata(record['metadata']);identity=hash_value(record['id'])
        require(identity not in seen and identity==record['metadata']['source_record_sha256']);seen.add(identity)
        # PostgreSQL's exact representation is preserved for byte-level metadata hashes.
        material=record.get('metadata_material');require(type(material) is str and parse(material.encode())==record['metadata'])
        require(digest(material.encode())==record['metadata_hash'])
        require(identity in appends)
        detail=appends[identity]['detail']
        require(detail['metadata_sha256']==record['metadata_hash'] and detail['predecessor']==record['predecessor'])
        require(all(datetime.fromisoformat(detail[k])==datetime.fromisoformat(record[k]) for k in ('received_at','expires_at')))
        require(datetime.fromisoformat(record['expires_at'])>datetime.fromisoformat(h['captured_at']))
    if checkpoint is not None:
        require(set(checkpoint)=={'installation','tenant','head','next_seq','base_seq','base_hash','snapshot_sha256'})
        require(checkpoint['snapshot_sha256']==digest(encoded(packet)))
        require(all(checkpoint[k]==h[k] for k in checkpoint if k!='snapshot_sha256'))
    return {'valid':True,'records':len(seen),'events':len(packet['events']),
            'externally_pinned_checkpoint_matched':checkpoint is not None,'source_authenticity_verified':False}


def checkpoint(packet):
    verify_export(packet)
    return {**{k:packet['header'][k] for k in ('installation','tenant','head','next_seq','base_seq','base_hash')},'snapshot_sha256':digest(encoded(packet))}


def checked_schema():
    schema=json.loads(SCHEMA.read_text())
    supported={'$schema','type','required','additionalProperties','properties','const','enum','pattern',
               'minLength','maxLength','minimum','maximum','format','items','minItems','maxItems','uniqueItems'}
    def visit(s):
        require(type(s) is dict and set(s)<=supported)
        if s.get('type')=='object':
            require(s.get('additionalProperties') is False and set(s['required'])==set(s['properties']))
        for v in s.get('properties',{}).values():visit(v)
        if 'items' in s:visit(s['items'])
        if 'format' in s:require(s['format'] in {'uuid','date-time'})
    visit(schema)
    return schema


def install(store):
    # Refuse existing/shared/system databases. Never migrate or overwrite implicitly.
    guard="""DO $$ BEGIN
    IF current_setting('server_version_num')::integer NOT BETWEEN 180000 AND 189999 OR current_database() IN ('postgres','template0','template1') OR
    EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%')
    THEN RAISE EXCEPTION 'Dedicated empty database required'; END IF; END $$;"""
    sql=(ROOT/'deploy/audit/store.sql').read_text()
    require(sql.startswith('-- Dedicated') and sql.rstrip().endswith('-- Installer inserts the reviewed schema and installation identity before committing.'))
    return store.sql(guard+'\n'+sql+'\nINSERT INTO aitrust_audit.control VALUES(true,'+literal(str(uuid.uuid4()))+",false,NULL,"+literal(encoded(checked_schema()).decode())+"::jsonb);\nREVOKE CREATE ON SCHEMA public FROM PUBLIC;\nCOMMIT;")


def policy(record_days,audit_days,backup_hours):
    require(all(type(v) is int for v in (record_days,audit_days,backup_hours)))
    require(1<=record_days<=3650 and record_days+1<=audit_days<=4000 and 1<=backup_hours<=168 and audit_days*24>=record_days*24+backup_hours)
    return {'format':'organization-audit-policy/v1','metadata_profile':'organization-audit-metadata/v1',
            'record_days':record_days,'audit_days':audit_days,'maximum_backup_age_hours':backup_hours,
            'hashes_are_linkable':True,'automatic_collection':False,'raw_text_allowed':False,
            'source_authentication':False,'independent_validation':False}


def tenant_create(store,tenant,selected):
    require(str(uuid.UUID(tenant))==tenant)
    require(selected==policy(selected['record_days'],selected['audit_days'],selected['maximum_backup_age_hours']))
    sha=digest(encoded(selected))
    store.sql('INSERT INTO aitrust_audit.tenants(tenant,policy,policy_hash) VALUES('+literal(tenant)+','+literal(encoded(selected).decode())+'::jsonb,'+literal(sha)+');')
    return {'tenant':tenant,'policy_sha256':sha,'policy':selected}


def enroll(store,tenant,principal,capabilities):
    require(str(uuid.UUID(tenant))==tenant and re.fullmatch(r'[a-z_][a-z0-9_]{0,62}',principal))
    require(type(capabilities) is list and capabilities and len(set(capabilities))==len(capabilities)
            and set(capabilities)<={'write','read','review','delete'})
    # An enrolled identity may never SET ROLE to a privileged or shared identity.
    sql="""BEGIN; DO $$ BEGIN IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=PRINCIPAL AND rolcanlogin AND NOT (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls))
    OR EXISTS(SELECT 1 FROM pg_database WHERE datname=current_database() AND datdba=(SELECT oid FROM pg_roles WHERE rolname=PRINCIPAL))
    OR EXISTS(SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=PRINCIPAL) AND admin_option)
    OR EXISTS(WITH RECURSIVE memberships(id) AS (SELECT roleid FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=PRINCIPAL) UNION SELECT m.roleid FROM pg_auth_members m JOIN memberships p ON p.id=m.member)
    SELECT 1 FROM memberships JOIN pg_roles r ON r.oid=id WHERE r.rolname<>'aitrust_audit_client') THEN RAISE EXCEPTION 'Audit principal refused'; END IF; END $$;
    INSERT INTO aitrust_audit.principals VALUES(PRINCIPAL,TENANT,CAPABILITIES);
    GRANT aitrust_audit_client TO IDENTIFIER; COMMIT;"""
    sql=sql.replace('PRINCIPAL',literal(principal)).replace('TENANT',literal(tenant)).replace('CAPABILITIES','ARRAY['+','.join(literal(c) for c in capabilities)+']::text[]').replace('IDENTIFIER','"'+principal+'"')
    store.sql(sql)
    return {'enrolled':True,'tenant':tenant,'capabilities':capabilities,'verified_human_identity':False}


def recovery_controls(store):
    # Administrative export only, deliberately unavailable through the tenant API.
    raw=store.sql("SELECT jsonb_build_object('format','organization-audit-recovery/v1','installation',installation,'issued_at',clock_timestamp(),'tenants',(SELECT coalesce(jsonb_agg(jsonb_build_object('tenant',t.tenant,'head',t.head,'next_seq',t.next_seq,'policy_sha256',t.policy_hash,'keep',(SELECT coalesce(jsonb_object_agg(id,metadata_hash),'{}') FROM aitrust_audit.records r WHERE r.tenant=t.tenant AND expires_at>clock_timestamp()))),'[]') FROM aitrust_audit.tenants t)) FROM aitrust_audit.control WHERE singleton;")
    return parse(raw.encode())


def reconcile(store,controls,expected_sha256,maximum_age_minutes):
    require(digest(encoded(controls))==hash_value(expected_sha256))
    require(type(maximum_age_minutes) is int and 1<=maximum_age_minutes<=60)
    require(set(controls)=={'format','installation','issued_at','tenants'} and controls['format']=='organization-audit-recovery/v1')
    stamp=datetime.fromisoformat(controls['issued_at']);require(stamp.tzinfo is not None)
    age=(datetime.now(timezone.utc)-stamp).total_seconds();require(0<=age<=maximum_age_minutes*60)
    require(str(uuid.UUID(controls['installation']))==controls['installation'])
    require(type(controls['tenants']) is list and len(controls['tenants'])<=1000)
    seen=set()
    for t in controls['tenants']:
        require(set(t)=={'tenant','head','next_seq','policy_sha256','keep'} and t['tenant'] not in seen)
        require(str(uuid.UUID(t['tenant']))==t['tenant']);seen.add(t['tenant'])
        hash_value(t['head']);hash_value(t['policy_sha256']);require(type(t['next_seq']) is int and t['next_seq']>=1)
        require(type(t['keep']) is dict and len(t['keep'])<=10000)
        for k,v in t['keep'].items():hash_value(k);hash_value(v)
    blob=literal(encoded(controls).decode())+'::jsonb'
    # Recovery is only to a still-quarantined backup. No general unlock command exists.
    sql="""BEGIN; LOCK TABLE aitrust_audit.control IN EXCLUSIVE MODE;
    DO $$ DECLARE c jsonb=CONTROLS; t jsonb; expected integer; BEGIN
    IF NOT EXISTS(SELECT 1 FROM aitrust_audit.control WHERE singleton AND locked AND installation=(c->>'installation')::uuid)
    OR (SELECT count(*) FROM aitrust_audit.tenants)<>jsonb_array_length(c->'tenants') THEN RAISE EXCEPTION 'Audit recovery refused'; END IF;
    FOR t IN SELECT value FROM jsonb_array_elements(c->'tenants') LOOP
     IF NOT EXISTS(SELECT 1 FROM aitrust_audit.tenants WHERE tenant=(t->>'tenant')::uuid AND policy_hash=t->>'policy_sha256' AND next_seq<=(t->>'next_seq')::bigint)
     THEN RAISE EXCEPTION 'Audit recovery refused'; END IF;
     -- Missing current rows are explicitly reported as unavailable; never invented from controls.
     DELETE FROM aitrust_audit.records WHERE tenant=(t->>'tenant')::uuid AND
     (expires_at<=clock_timestamp() OR NOT (t->'keep' ? id) OR t->'keep'->>id<>metadata_hash);
    UPDATE aitrust_audit.tenants SET recovery=jsonb_build_object('authority_head',t->>'head','authority_next_seq',t->'next_seq','authority_sha256',PIN,'applied_at',clock_timestamp(),'newer_history_unavailable',true) WHERE tenant=(t->>'tenant')::uuid;
    END LOOP;
    -- Restored audit events are historical, not a false continuation of the newer authority head.
    UPDATE aitrust_audit.control SET locked=false WHERE singleton;
    END $$;
    SELECT jsonb_build_object('recovered',true,'missing_newer_records_not_reconstructed',true,'independent_witness',false);
    COMMIT;""".replace('CONTROLS',blob).replace('PIN',literal(expected_sha256))
    return parse(store.sql(sql).encode())


def backup(store,config,include_directory,stanza):
    import configparser
    raw=private_file(config).decode('utf-8')
    cfg=configparser.ConfigParser(interpolation=None,strict=True);cfg.read_string(raw)
    require(set(cfg.sections())=={'global',stanza} and not cfg.defaults())
    require(set(cfg['global'])<={'repo1-path','repo1-cipher-type','repo1-cipher-pass','repo1-retention-full','expire-auto','log-level-console','log-level-file','lock-path','spool-path','start-fast','archive-timeout','neutral-umask'})
    require(set(cfg[stanza])=={'pg1-path','pg1-socket-path','pg1-port'})
    require(cfg['global'].get('log-level-file')=='off' and cfg['global'].get('log-level-console') in {'warn','error','off'})
    require(cfg['global'].get('repo1-cipher-type')=='aes-256-cbc' and len(cfg['global'].get('repo1-cipher-pass',''))>=32)
    include=Path(include_directory).absolute()
    require(include.is_dir() and not include.is_symlink() and not any(include.iterdir()) and not include.stat().st_mode&0o077)
    require(re.fullmatch(r'[a-z][a-z0-9_-]{0,31}',stanza))
    tool=shutil.which('pgbackrest');require(tool is not None)
    identity=parse(store.sql("SELECT jsonb_build_object('path',current_setting('data_directory'),'port',current_setting('port'),'socket',current_setting('unix_socket_directories'),'local',inet_server_addr() IS NULL,'databases',(SELECT count(*) FROM pg_database WHERE NOT datistemplate AND datname<>'postgres'),'hours',(SELECT min((policy->>'maximum_backup_age_hours')::integer) FROM aitrust_audit.tenants));").encode())
    require(identity['local'] is True and identity['databases']==1 and type(identity['hours']) is int)
    require(Path(cfg[stanza]['pg1-path']).resolve()==Path(identity['path']).resolve() and cfg[stanza]['pg1-port']==identity['port'] and cfg[stanza]['pg1-socket-path'] in identity['socket'].split(','))
    repository=Path(cfg['global']['repo1-path'])
    require(repository.is_absolute() and repository.is_dir() and not repository.is_symlink() and repository.stat().st_uid==os.getuid() and not repository.stat().st_mode&0o077)
    require(set(p.name for p in repository.iterdir())<={'archive','backup'})
    for name in ('archive','backup'):
        folder=repository/name
        if folder.exists():require(not folder.is_symlink() and folder.is_dir() and set(p.name for p in folder.iterdir())<={stanza})
    # Cipher/config secrets never enter argv, stdout, or exception diagnostics.
    command=[tool,'--config='+str(Path(config).absolute()),'--config-include-path='+str(include),'--stanza='+stanza]
    def b(*args):
        require(private_file(config).decode('utf-8')==raw)
        return bounded_command(command+list(args),{'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','TZ':'UTC'},timeout=120,diagnostics=store.diagnostics)
    token=str(uuid.uuid4())
    locked=store.sql("UPDATE aitrust_audit.control SET locked=true,backup_token="+literal(token)+" WHERE singleton AND NOT locked RETURNING 1;")
    require(locked=='1')
    try:
        b('--expire-auto=n','--type=full','backup')
        listing=json.loads(b('--output=json','info'));require(len(listing)==1 and listing[0]['name']==stanza)
        backups=listing[0]['backup'];require(listing[0]['cipher']=='aes-256-cbc' and listing[0]['status']['code']==0 and backups and all(v['type']=='full' and v['error'] is False for v in backups))
        now=datetime.now(timezone.utc).timestamp();expired=[]
        for item in backups:
            if now-item['timestamp']['start']>identity['hours']*3600:
                label=item['label'];require(re.fullmatch(r'[0-9]{8}-[0-9]{6}F',label))
                b('--repo1-retention-full=9999999','--set='+label,'expire');expired.append(label)
        after=json.loads(b('--output=json','info'))[0]['backup']
        require(after and all(now-item['timestamp']['start']<=identity['hours']*3600 for item in after))
        return {'backed_up':True,'encrypted':True,'restores_quarantined':True,'expired_sets':len(expired),'physical_erasure_verified':False}
    finally:
        # Token comparison prevents another operation from unlocking this backup's marker.
        require(store.sql("UPDATE aitrust_audit.control SET locked=false,backup_token=NULL WHERE singleton AND locked AND backup_token="+literal(token)+" RETURNING 1;")=='1')
