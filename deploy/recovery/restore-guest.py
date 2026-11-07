#!/usr/bin/env python3
"""Restore the actual selected backup only inside the nonce-bound recovery VM."""
import argparse,hashlib,json,os,re,secrets,shutil,socket,stat,subprocess,time
from pathlib import Path
BASE=Path('/var/lib/aitrust-recovery')
def require(ok):
    if not ok:raise ValueError('Recovery guest restore refused')
def run(args,*,raw=None,timeout=120,check=True):return subprocess.run(list(map(str,args)),input=raw,stdin=subprocess.DEVNULL if raw is None else None,capture_output=True,timeout=timeout,check=check)
def sql(query):return run(['runuser','-u','postgres','--','psql','-XAt','-v','ON_ERROR_STOP=1','-d','aitrustid'],raw=query.encode(),timeout=45).stdout.decode().strip()
def inventory():
    q=r"""SELECT format('SELECT json_build_object(''schema'',%L,''table'',%L,''rows'',count(*)) FROM %I.%I;',n.nspname,c.relname,n.nspname,c.relname) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind='r' AND n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%' ORDER BY n.nspname,c.relname
\gexec
"""
    return [json.loads(line) for line in sql(q).splitlines() if line.strip()]
def configuration(repo,cipher,target):return '[global]\nrepo1-type=posix\nrepo1-path='+str(repo)+'\nrepo1-cipher-type=aes-256-cbc\nrepo1-cipher-pass='+cipher+'\nlog-level-console=off\nlog-level-file=off\nlock-path=/var/lib/aitrust-recovery/locks\n\n[aitrustid]\npg1-path='+str(target)+'\n'
def private(path,contents):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as out:out.write(contents)
    shutil.chown(path,user='postgres',group='postgres')
def info(cfg):
    p=run(['runuser','-u','postgres','--','pgbackrest','--config='+str(cfg),'--stanza=aitrustid','info','--output=json'],check=False)
    try:d=json.loads(p.stdout);return p.returncode==0 and d[0]['status']['code']==0,d
    except Exception:return False,None

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--nonce',required=True);p.add_argument('--data-directory',type=Path,default=Path('/var/lib/postgresql/18/main'));p.add_argument('--verify-only',action='store_true');a=p.parse_args()
    require(os.geteuid()==0 and re.fullmatch('[a-f0-9]{32}',a.nonce) and socket.gethostname()=='aitrust-recovery-'+a.nonce[:8])
    require(Path('/var/lib/aitrust-recovery-prepared').is_file() and a.data_directory==Path('/var/lib/postgresql/18/main'))
    require(not a.data_directory.is_symlink() and a.data_directory.resolve()==a.data_directory)
    material=Path('/etc/aitrust-recovery/material.json');s=material.lstat();require(s.st_uid==0 and stat.S_ISREG(s.st_mode) and not s.st_mode&0o077)
    d=json.loads(material.read_bytes());require(d['nonce']==a.nonce and re.fullmatch('[a-f0-9]{64}',d['source_system_sha256']) and len(d['cipher'])>=48 and not any(c.isspace() for c in d['cipher']))
    require(run(['systemd-detect-virt','--vm']).stdout.strip()==b'kvm')
    base=BASE;repo=base/'repository';base.mkdir(mode=0o750,exist_ok=True);shutil.chown(base,user='root',group='postgres')
    controls=[]
    def case(name):controls.append({'case':name,'pass':True})
    if not a.verify_only:
        require(not (base/'restored.json').exists())
        fresh=sql('SELECT system_identifier FROM pg_control_system();');require(hashlib.sha256(fresh.encode()).hexdigest()!=d['source_system_sha256']);require(inventory()==[])
        case('fresh_replacement_os_and_empty_distinct_cluster')
        for path in [repo,*repo.rglob('*')]:
            require(not path.is_symlink());shutil.chown(path,user='postgres',group='postgres');path.chmod(0o700 if path.is_dir() else 0o600)
        for name in ['locks','wrong-key-target']:
            (base/name).mkdir(mode=0o700);shutil.chown(base/name,user='postgres',group='postgres')
        cfg=base/'restore.conf';private(cfg,configuration(repo,d['cipher'],a.data_directory));valid,data=info(cfg);require(valid)
        available=data[0]['backup'];require(available);chosen=max(available,key=lambda r:r['timestamp']['stop']);label=chosen['label'];require(re.fullmatch(r'\d{8}-\d{6}F(?:_\d{8}-\d{6}[DI])?',label));case('selected_encrypted_repository_and_backup_metadata_valid')
        bad=base/'wrong-cipher.conf';private(bad,configuration(repo,secrets.token_urlsafe(48),base/'wrong-key-target'));require(info(bad)[0] is False);case('wrong_recovery_key_refused')
        corrupt=base/'corrupt-repository';shutil.copytree(repo,corrupt)
        for path in [corrupt,*corrupt.rglob('*')]:shutil.chown(path,user='postgres',group='postgres')
        badcopy=base/'corrupt.conf';private(badcopy,configuration(corrupt,d['cipher'],base/'wrong-key-target'));require(info(badcopy)[0] is True)
        for name in ['backup.info','backup.info.copy']:
            path=corrupt/'backup/aitrustid'/name;require(path.is_file());raw=bytearray(path.read_bytes());require(len(raw)>32);raw[16]^=0x40;path.write_bytes(raw)
        require(info(badcopy)[0] is False);case('corrupted_repository_metadata_refused');shutil.rmtree(corrupt)
        run(['systemctl','stop','postgresql@18-main']);require(run(['pg_ctlcluster','18','main','status'],check=False).returncode!=0)
        a.data_directory.rename(base/'empty-preparation-cluster')
        # Match recovery-sensitive source parameters and prohibit any outbound WAL push.
        settings=d['source_settings'];allowed={'max_connections','max_worker_processes','max_wal_senders','max_prepared_transactions','max_locks_per_transaction'};require(set(settings)==allowed and all(type(v) is int and 0<=v<=10000 for v in settings.values()))
        control='\n'.join(k+' = '+str(v) for k,v in settings.items())+"\nlisten_addresses = ''\narchive_mode = off\n"
        target=Path('/etc/postgresql/18/main/conf.d/99-aitrust-recovery.conf');target.write_text(control);target.chmod(0o640);shutil.chown(target,user='postgres',group='postgres')
        started=time.monotonic();run(['runuser','-u','postgres','--','pgbackrest','--config='+str(cfg),'--stanza=aitrustid','--set='+label,'--type=immediate','--target-action=promote','--archive-mode=off','restore'],timeout=240)
        auto=a.data_directory/'postgresql.auto.conf'
        with auto.open('a') as out:out.write("\n# Offline replacement drill: never publish WAL or open database TCP.\narchive_mode = 'off'\narchive_command = ''\nlisten_addresses = ''\n")
        os.chown(auto,__import__('pwd').getpwnam('postgres').pw_uid,__import__('grp').getgrnam('postgres').gr_gid);auto.chmod(0o600)
        run(['systemctl','start','postgresql@18-main'],timeout=150)
        checkpoint={'backup_label':label,'restore_seconds':time.monotonic()-started,'pre_restore_controls':controls,'source_system_sha256':d['source_system_sha256']}
        (base/'restored.json').write_text(json.dumps(checkpoint,indent=2)+'\n');(base/'restored.json').chmod(0o600)
    checkpoint=json.loads((base/'restored.json').read_text());controls=checkpoint['pre_restore_controls']
    restored=sql('SELECT system_identifier FROM pg_control_system();');require(hashlib.sha256(restored.encode()).hexdigest()==d['source_system_sha256']);case('actual_source_cluster_identity_restored')
    rows=inventory();require(rows==d['source_inventory']);case('actual_application_and_synthetic_table_counts_match')
    require(sql('SHOW listen_addresses;')=='');require(sql('SHOW archive_mode;')=='off');case('restored_database_is_socket_only_and_outbound_archiving_disabled')
    require(sql('SHOW data_checksums;')=='on');require(sql('SELECT pg_is_in_recovery();')=='f');case('checksummed_restored_database_promoted')
    require(sql("SELECT count(*) FROM pg_roles WHERE rolname IN ('aitrust_intake','aitrust_reviewer','aitrust_reader') AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls);")=='0');case('restored_runtime_roles_remain_unprivileged')
    for account,role in [('debian','aitrust_reader'),('ait-analysis','aitrust_reader'),('ait-intake','aitrust_intake'),('ait-review','aitrust_reviewer')]:
        args=['runuser','-u',account,'--','psql','-XAt','-v','ON_ERROR_STOP=1','-U',role,'-d','aitrustid','-c']
        require(run([*args,'SELECT current_user;']).stdout.decode().strip()==role)
        require(run([*args,'SET ROLE aitrust_owner;'],check=False).returncode!=0)
    case('reconstructed_os_peer_identity_and_admin_denial')
    require(run(['sshd','-T']).stdout.decode().find('passwordauthentication no')>=0);require(run(['nft','list','table','inet','aitrust_host']).returncode==0);case('reconstructed_ssh_and_dual_stack_firewall_active')
    require(run(['systemctl','is-active','ssh']).stdout.strip()==b'active');case('replacement_administration_works')
    public=d['owner_admin_public_key'];require(public.startswith('ssh-ed25519 ') and '\n' not in public)
    authorized=Path('/home/debian/.ssh/authorized_keys')
    if public not in authorized.read_text().splitlines():
        with authorized.open('a') as out:out.write(public+'\n')
    authorized.chmod(0o600);case('owner_public_administration_key_reconstructed')
    proof={'pass':True,'captured_at':time.time(),'nonce':a.nonce,'backup_label':checkpoint['backup_label'],'restore_seconds':checkpoint['restore_seconds'],'table_count':len(rows),'controls':controls,'boot_id_sha256':hashlib.sha256(Path('/proc/sys/kernel/random/boot_id').read_bytes()).hexdigest(),'source_system_identity_matched':True,'actual_guest_kernel':os.uname().release,'production_collection_enabled':False,'public_network_access':False,'physical_or_human_acceptance':False}
    out=base/'verified.json';out.write_text(json.dumps(proof,indent=2)+'\n');out.chmod(0o600);print(json.dumps(proof))
if __name__=='__main__':main()
