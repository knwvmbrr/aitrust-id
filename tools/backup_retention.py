"""Actual encrypted synthetic retention controls; never production or physical erasure."""
from pathlib import Path
import os,sys,subprocess,tempfile,json,shutil,socket,time,secrets,re,hashlib,ctypes,pwd,importlib.util
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
SOURCES=('tools/backup_retention.py','scripts/verify-backup-retention.py','deploy/backup/restore.py','protocol/reports.py','tools/blind_review_io.py')

def require(ok):
    if not ok:raise ValueError('Synthetic backup boundary refused')

def hashes():return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES}

def prepare_account(name):
    require(sys.platform=='linux' and os.geteuid()==0 and sys.flags.optimize==0)
    require(type(name) is str and re.fullmatch(r'[a-z_][a-z0-9_-]{0,31}',name) is not None)
    spec=importlib.util.spec_from_file_location('existing_restore_guard',ROOT/'deploy/backup/restore.py')
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
    namespace=guard.require_isolated_network()
    account=pwd.getpwnam(name);require(account.pw_uid>=1000 and account.pw_gid>0)
    libc=ctypes.CDLL(None,use_errno=True)
    require(libc.prctl(38,1,0,0,0)==0)
    os.setgroups([]);os.setgid(account.pw_gid);os.setuid(account.pw_uid)
    status={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in Path('/proc/self/status').read_text().splitlines() if ':' in line}
    require(os.geteuid()==account.pw_uid and os.getegid()==account.pw_gid and os.getgroups()==[])
    require(status['NoNewPrivs']=='1' and int(status['CapEff'],16)==int(status['CapPrm'],16)==0)
    require_namespace(namespace);return namespace

def require_namespace(expected):
    require(sys.platform=='linux' and os.geteuid()!=0 and sys.flags.optimize==0)
    current=os.stat('/proc/self/ns/net')
    require((current.st_dev,current.st_ino)==expected and [name for _,name in socket.if_nameindex()]==['lo'])

def verify(namespace):
    before=hashes()
    work=None;active=[]
    try:
        require_namespace(namespace)
        os.umask(0o077)
        blocked=[]
        for family,address in [(socket.AF_INET,('1.1.1.1',443)),(socket.AF_INET6,('2606:4700:4700::1111',443,0,0))]:
         with socket.socket(family,socket.SOCK_STREAM) as connection:
          connection.settimeout(2)
          try:connection.connect(address);raise AssertionError('Unexpected network connection')
          except OSError as error:
           require(error.errno in (99,101,113));blocked.append(family)
        pg=Path('/usr/lib/postgresql/18/bin');backrest=Path('/usr/bin/pgbackrest')
        assert pg.is_dir() and backrest.is_file()
        require(shutil.disk_usage('/tmp').free >= 2_000_000_000)
        work=Path(tempfile.mkdtemp(prefix='aitrust-expiry-',dir='/tmp')).resolve();assert re.fullmatch(r'/tmp/aitrust-expiry-[a-z0-9_]+',str(work));work.chmod(0o700)
        log=(work/'execution.log').open('wb');controls=[];active=[];success=False
        cleanenv={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','TZ':'UTC','PGPASSFILE':'/dev/null'}
        def run(args,timeout=90,expected=0):
         require_namespace(namespace)
         r=subprocess.run([str(a) for a in args],capture_output=True,timeout=timeout,env=cleanenv)
         log.write(r.stdout+r.stderr);log.flush()
         if expected==0 and r.returncode!=0:raise RuntimeError('Private command failed with '+str(r.returncode))
         if expected=='refuse' and r.returncode==0:raise RuntimeError('Unexpected successful refusal control')
         return r
        source=work/'source';repo=work/'repository';sock=work/'socket';locks=work/'locks';spool=work/'spool';empty_config=work/'empty-config'
        for path in [repo,sock,locks,spool,empty_config]:path.mkdir(mode=0o700)
        config=work/'pgbackrest.conf';key=secrets.token_hex(32)
        config.write_text('[global]\nrepo1-path='+str(repo)+'\nrepo1-cipher-type=aes-256-cbc\nrepo1-cipher-pass='+key+'\nrepo1-retention-full=2\nexpire-auto=n\nlog-level-console=warn\nlog-level-file=off\nlock-path='+str(locks)+'\nspool-path='+str(spool)+'\nstart-fast=y\narchive-timeout=30\nneutral-umask=n\n\n[practice]\npg1-path='+str(source)+'\npg1-socket-path='+str(sock)+'\npg1-port=6540\n')
        config.chmod(0o600)
        def b(*args,configfile=config):return run([backrest,'--config='+str(configfile),'--config-include-path='+str(empty_config),'--stanza=practice',*args])
        def start(path,port):
         options="-c listen_addresses='' -c unix_socket_directories="+str(sock)+' -p '+str(port)
         if path!=source:options+=' -c archive_mode=off'
         active.append(path)
         run([pg/'pg_ctl','-D',path,'-l',work/(path.name+'.log'),'-o',options,'-w','start'])
        def stop(path):
         status=subprocess.run([str(pg/'pg_ctl'),'-D',str(path),'status'],capture_output=True,timeout=15,env=cleanenv)
         require(status.returncode in (0,3))
         if status.returncode==0:run([pg/'pg_ctl','-D',path,'-m','fast','-w','stop'],timeout=30)
         active.remove(path)
        def sql(text,port=6540):return run([pg/'psql','-h',sock,'-p',str(port),'-d','postgres','-X','-qAt','-v','ON_ERROR_STOP=1','-c',text]).stdout.decode().strip()
        def info():return json.loads(b('--output=json','info').stdout)[0]['backup']
        def restore(label,name,expected_rows,configfile=config):
         target=work/name;assert not target.exists()
         run([backrest,'--config='+str(configfile),'--config-include-path='+str(empty_config),'--stanza=practice','--pg1-path='+str(target),'--set='+label,'--type=immediate','--target-action=promote','restore'])
         start(target,6541)
         try:
          assert sql('SELECT count(*) FROM invented_feedback;',6541)==str(expected_rows)
          if expected_rows:assert sql('SELECT value FROM invented_feedback;',6541)=='synthetic-choice'
         finally:stop(target)
         controls.append({'case':name,'pass':True,'rows':expected_rows})
        try:
         version=run([backrest,'version']).stdout.decode().strip();pgversion=run([pg/'postgres','--version']).stdout.decode().strip()
         parsed=re.fullmatch(r'pgBackRest ([0-9]+)\.([0-9]+)\.([0-9]+)',version)
         require(parsed is not None and tuple(map(int,parsed.groups())) >= (2,59,3))
         require(re.fullmatch(r'postgres \(PostgreSQL\) 18\.[0-9]+(?: .*)?',pgversion) is not None)
         run([pg/'initdb','-D',source,'--auth-local=trust','--auth-host=reject','--no-locale','--encoding=UTF8'])
         with (source/'postgresql.conf').open('a') as f:
          f.write("\nlisten_addresses=''\nshared_buffers='16MB'\narchive_mode=on\narchive_command='"+str(backrest)+' --config='+str(config)+' --config-include-path='+str(empty_config)+' --stanza=practice archive-push %p'+"'\n")
         start(source,6540);b('stanza-create');b('check')
         assert sql("CREATE TABLE invented_feedback(value text); INSERT INTO invented_feedback VALUES ('synthetic-choice'); SELECT count(*) FROM invented_feedback;")=='1'
         b('--type=full','backup');labels=info();assert len(labels)==1;old=labels[0]['label'];restore(old,'before-withdrawal',1)
         assert sql('DELETE FROM invented_feedback; SELECT count(*) FROM invented_feedback;')=='0'
         b('--type=full','backup');labels=info();assert len(labels)==2;new=next(r['label'] for r in labels if r['label']!=old)
         restore(new,'after-withdrawal',0);restore(old,'retained-old-before-expiry',1)
         wrong=work/'wrong-key.conf';wrong.write_text(config.read_text().replace('repo1-cipher-pass='+key,'repo1-cipher-pass='+secrets.token_hex(32)));wrong.chmod(0o600)
         run([backrest,'--config='+str(wrong),'--config-include-path='+str(empty_config),'--stanza=practice','--pg1-path='+str(work/'wrong-key-restore'),'--set='+new,'restore'],expected='refuse');controls.append({'case':'wrong_cipher_key_refused','pass':True})
         corrupt=work/'corrupt-repository';shutil.copytree(repo,corrupt);
         for name in ['backup.info','backup.info.copy']:
          target=corrupt/'backup/practice'/name;raw=target.read_bytes();assert len(raw)>64;target.write_bytes(raw[:32]+bytes(v^255 for v in raw[32:48])+raw[48:])
         corruptcfg=work/'corrupt.conf';corruptcfg.write_text(config.read_text().replace('repo1-path='+str(repo),'repo1-path='+str(corrupt)));corruptcfg.chmod(0o600)
         run([backrest,'--config='+str(corruptcfg),'--config-include-path='+str(empty_config),'--stanza=practice','--pg1-path='+str(work/'corrupt-restore'),'--set='+new,'restore'],expected='refuse');controls.append({'case':'corrupt_repository_refused','pass':True})
         b('--repo1-retention-full=1','expire');labels=info();assert len(labels)==1 and labels[0]['label']==new
         run([backrest,'--config='+str(config),'--config-include-path='+str(empty_config),'--stanza=practice','--pg1-path='+str(work/'expired-restore'),'--set='+old,'restore'],expected='refuse');controls.append({'case':'expired_exact_label_refused','pass':True})
         restore(new,'retained-after-expiry',0);success=True
        except Exception as error:
         failure={'type':type(error).__name__,'reason':'synthetic_backup_control_refused'}
        finally:
         cleanup=True
         for path in list(active):
          try:stop(path)
          except Exception:cleanup=False
         log.close();raw=(work/'execution.log').read_bytes()
         proof={'captured_at':datetime.now(timezone.utc).isoformat(),'pass':success and cleanup,'controls':controls,'external_connections_refused':len(blocked),'non_root':True,'socket_only_clusters':True,'isolated_network_namespace':True,'pgbackrest_version':locals().get('version'),'postgresql_version':locals().get('pgversion'),'logical_sql_deletion_only':True,'physical_erasure_verified':False,'provider_copies_deleted':False,'production_changes':False,'actual_participant_data':False,'requirements_closed':0,'stdout_sha256':hashlib.sha256(raw).hexdigest(),'clusters_stopped':cleanup}
         if not success:proof['private_failure']=failure
         if cleanup:shutil.rmtree(work)
         proof['owned_database_directory_removed']=not work.exists()
         proof['sources']=before
         proof['source_unchanged_during_execution']=before==hashes()
         proof['pass']=proof['pass'] and proof['source_unchanged_during_execution'] and proof['owned_database_directory_removed']
         return proof,raw
    finally:
        if 'log' in locals() and not log.closed:log.close()
        if work is not None and work.exists() and not active:
            require(not work.is_symlink() and work.stat().st_uid==os.geteuid())
            require(re.fullmatch(r'/tmp/aitrust-expiry-[a-z0-9_]+',str(work)) is not None)
            shutil.rmtree(work)
