#!/usr/bin/env python3
"""Restore a protected generation into a fresh socket-only synthetic drill.

Never reads or alters the primary cluster. Each drill gets a new directory.
"""
import argparse
import configparser
import json
import os
from pathlib import Path
import re
import subprocess
import time
import uuid


def run(args, check=True):
    return subprocess.run(args, capture_output=True, text=True, check=check, timeout=240)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True)
    parser.add_argument('--schema', required=True)
    parser.add_argument('--expected-rows', type=int, choices=[1,2], required=True)
    parser.add_argument('--generation', required=True)
    parser.add_argument('--backup-label', required=True)
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit('Run as root')
    if not re.fullmatch(r'aitrust_probe_[a-f0-9]{32}_(before|after)', args.target):
        raise SystemExit('Only a named synthetic recovery point is allowed')
    if not re.fullmatch(r'recovery_[a-f0-9]{32}', args.schema):
        raise SystemExit('Only the named synthetic recovery schema is allowed')
    if not re.fullmatch(r'\d{8}T\d{6}Z-[a-f0-9]{8}', args.generation):
        raise SystemExit('Only an explicitly named protected generation is allowed')
    if not re.fullmatch(r'\d{8}-\d{6}F(?:_\d{8}-\d{6}[DI])?', args.backup_label):
        raise SystemExit('Invalid explicit backup label')
    started = time.monotonic()
    os.umask(0o077)
    protected = Path('/var/lib/aitrust-id/protected')
    generation = (protected/args.generation).resolve(strict=True)
    if generation.parent != protected or generation.is_symlink():
        raise SystemExit('Invalid protected generation')
    parent = Path('/var/lib/aitrust-id/restore-drill')
    parent.mkdir(mode=0o750, exist_ok=True)
    parent.chmod(0o750)
    run(['chown','root:postgres',str(parent)])
    work = parent / uuid.uuid4().hex
    work.mkdir(mode=0o750)
    work.chmod(0o750)
    run(['chown','root:postgres',str(work)])
    data, repo = [work/name for name in ['data','repository']]
    # Runtime test identities need to reach a peer-authenticated socket, while
    # PGDATA and decrypted repository/configuration remain private to postgres.
    socket = Path('/run') / ('aitrust-restore-' + work.name)
    for path in [data,repo,socket]:
        path.mkdir(mode=0o700)
        run(['chown','postgres:postgres',str(path)])
    socket.chmod(0o755)
    # rsync creates independent files; protected generations never share writable
    # inodes with this disposable restore repository.
    run(['rsync','-rt','--no-links','--no-specials','--no-devices',str(generation)+'/',str(repo)+'/'])
    run(['chown','-R','postgres:postgres',str(repo)])
    config = configparser.ConfigParser(interpolation=None)
    config.read('/etc/pgbackrest/pgbackrest.conf')
    restore_config = work/'pgbackrest.conf'
    restore_config.write_text('[global]\nrepo1-path='+str(repo)+'\nrepo1-cipher-type=aes-256-cbc\nrepo1-cipher-pass='+config['global']['repo1-cipher-pass']+'\nlog-level-console=warn\nlog-level-file=off\nlock-path='+str(work/'locks')+'\n\n[aitrustid]\npg1-path='+str(data)+'\n')
    restore_config.chmod(0o640)
    run(['chown','root:postgres',str(restore_config)])
    run(['pgbackrest','--config='+str(restore_config),'--stanza=aitrustid','--set='+args.backup_label,'--type=name',
         '--target='+args.target,'--target-action=promote','--archive-mode=off','restore'])
    locks = work/'locks'
    locks.mkdir(mode=0o700, exist_ok=True)
    run(['chown','-R','postgres:postgres',str(locks)])
    hba = work/'pg_hba.conf'
    ident = work/'pg_ident.conf'
    hba.write_text('local all postgres peer\nlocal all aitrust_reader peer map=drill\nlocal all aitrust_intake peer map=drill\n')
    ident.write_text('drill ait-analysis aitrust_reader\ndrill ait-intake aitrust_intake\n')
    for account in ['ait-analysis','ait-intake']:
        if run(['id',account],check=False).returncode:
            run(['useradd','--system','--user-group','--no-create-home','--shell','/usr/sbin/nologin',account])
    pgconfig = work/'postgresql.conf'
    settings = json.loads(Path('/etc/pgbackrest/recovery-settings.json').read_text())
    required = {'max_connections','max_worker_processes','max_wal_senders','max_prepared_transactions','max_locks_per_transaction'}
    if set(settings) != required or any(type(value) is not int or value < 0 for value in settings.values()):
        raise SystemExit('Invalid source recovery settings')
    pgconfig.write_text("listen_addresses = ''\nport = 55432\nunix_socket_directories = '"+str(socket)+"'\nhba_file = '"+str(hba)+"'\nident_file = '"+str(ident)+"'\nshared_buffers = '128MB'\nfsync = on\nfull_page_writes = on\n" + ''.join(f'{name} = {value}\n' for name,value in settings.items()))
    for path in [hba,ident,pgconfig]:
        path.chmod(0o640)
        run(['chown','root:postgres',str(path)])
    # pg_ctl creates its log outside PGDATA; pre-create an owner-writable file.
    log = work/'postgres.log'
    log.touch(mode=0o600)
    run(['chown','postgres:postgres',str(log)])
    pgctl=['runuser','-u','postgres','--','/usr/lib/postgresql/18/bin/pg_ctl','-D',str(data)]
    checks={}

    def sql(query, account='postgres', role='postgres', check=True, readwrite=False):
        command=['runuser','-u',account,'--','psql','--no-psqlrc','-XAt','--set','ON_ERROR_STOP=1',
                 '-h',str(socket),'-p','55432','-U',role,'-d','aitrustid']
        if readwrite:
            command += ['-c','SET default_transaction_read_only=off']
        return run([*command,'-c',query], check=check)

    try:
        run([*pgctl,'-o','-c config_file='+str(pgconfig),'-l',str(log),'-w','start'])
        deadline = time.monotonic() + 30
        while sql('SELECT pg_is_in_recovery()').stdout.strip() != 'f':
            if time.monotonic() >= deadline:
                raise RuntimeError('Named recovery target did not complete and promote')
            time.sleep(0.1)
        checks['target_promoted']=True
        checks['network_namespace_isolated']=os.stat('/proc/self/ns/net').st_ino != os.stat('/proc/1/ns/net').st_ino
        checks['synthetic_rows']=int(sql('SELECT count(*) FROM '+args.schema+'.probe').stdout.strip())==args.expected_rows
        checks['checksums']=sql('SHOW data_checksums').stdout.strip()=='on'
        checks['socket_only']=sql('SHOW listen_addresses').stdout.strip()==''
        checks['runtime_roles_unprivileged']=sql("SELECT count(*) FROM pg_roles WHERE rolname IN ('aitrust_intake','aitrust_reader','aitrust_reviewer') AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)").stdout.strip()=='0'
        checks['reader_select']=int(sql('SELECT count(*) FROM '+args.schema+'.probe','ait-analysis','aitrust_reader').stdout.strip())==args.expected_rows
        denied=sql('INSERT INTO '+args.schema+'.probe VALUES (99)','ait-analysis','aitrust_reader',check=False,readwrite=True)
        checks['reader_write_denied']=denied.returncode!=0 and 'permission denied' in denied.stderr
        denied=sql('SELECT * FROM '+args.schema+'.probe','ait-intake','aitrust_intake',check=False)
        checks['intake_read_denied']=denied.returncode!=0 and 'permission denied' in denied.stderr
        checks['intake_insert']=sql('INSERT INTO '+args.schema+'.probe VALUES (98)','ait-intake','aitrust_intake',check=False).returncode==0
    finally:
        stopped=run([*pgctl,'-m','fast','-w','stop'],check=False)
        checks['restore_cluster_stopped']=stopped.returncode==0
        if stopped.returncode == 0:
            socket.rmdir()
    result={'scope':'isolated_protected_restore','target_kind':args.target.rsplit('_',1)[-1],
            'generation':generation.name,'backup_label':args.backup_label,'checks':checks,'passed':all(checks.values()),
            'elapsed_seconds':round(time.monotonic()-started,3),'production_ready':False}
    (work/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
