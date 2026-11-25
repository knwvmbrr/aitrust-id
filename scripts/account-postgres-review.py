#!/usr/bin/env python3
"""Provision/stop only a fresh owned PostgreSQL synthetic review workspace."""
import argparse
import grp
import hashlib
import io
import json
import os
from pathlib import Path
import pwd
import re
import signal
import stat
import subprocess
import sys
import urllib.request
import zipfile

BASE = Path('/var/lib/aitrust-id/account-review')
BIN = Path('/usr/lib/postgresql/18/bin')
SOURCE = Path(__file__).resolve().parents[1]


class Refused(ValueError): pass


def need(value):
    if not value: raise Refused('Account PostgreSQL review unavailable.')


def run(argv, data=None, good=True):
    p = subprocess.run(list(map(str, argv)), input=data, capture_output=True, timeout=120)
    if good: need(p.returncode == 0)
    return p


def owned(work):
    need(sys.platform == 'linux' and os.geteuid() == 0 and work.parent == BASE and re.fullmatch('[0-9a-f]{32}', work.name))
    for part in [work, *work.parents]: need(not part.is_symlink())
    info = work.stat()
    need(info.st_uid == pwd.getpwnam('debian').pw_uid and stat.S_IMODE(info.st_mode) == 0o750)
    need(SOURCE == work / 'source')


CLEAN_EXEC = "import os,sys; e={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1','PSYCOPG_IMPL':'python'}; e.update({'HOME':os.environ['HOME']} if 'HOME' in os.environ else {}); os.execve(sys.argv[1],sys.argv[1:],e)"


def user(argv, account='debian'):
    need(account in ('debian', 'ait-intake') and str(argv[0]).startswith('/'))
    return ['runuser', '-u', account, '-g', 'ait-intake', '--', '/usr/bin/python3',
            '-I', '-B', '-c', CLEAN_EXEC, *map(str, argv)]


def sql(work, query, database='postgres', runtime=False, good=True):
    need(database in ('postgres', 'ait_account_review', 'ait_account_restore'))
    role = 'ait_account_runtime' if runtime else 'debian'
    return run(user(['/usr/bin/env', '-i', 'PATH=/usr/bin:/bin', 'PGOPTIONS=-c statement_timeout=5000 -c lock_timeout=1000',
                     BIN / 'psql', '-XqAtw', '-v', 'ON_ERROR_STOP=1', '-h', work / 'socket', '-p', '55449',
                     '-U', role, '-d', database], 'ait-intake' if runtime else 'debian'), query.encode(), good)


def guard_cluster(work):
    raw = sql(work, "SELECT json_build_object('data',current_setting('data_directory'),'cluster',current_setting('cluster_name'),'listen',current_setting('listen_addresses'),'port',current_setting('port'),'version',current_setting('server_version_num'),'tcp',inet_server_addr());").stdout
    value = json.loads(raw)
    need(value == {'data': str(work / 'pgdata'), 'cluster': 'aitrust-account-review', 'listen': '',
                   'port': '55449', 'version': value['version'], 'tcp': None} and 180000 <= int(value['version']) < 190000)


def provision(work):
    need(not (work / 'pgdata').exists() and not (work / 'venv').exists())
    uid, gid = pwd.getpwnam('debian').pw_uid, grp.getgrnam('ait-intake').gr_gid
    packages = json.loads((SOURCE / 'deploy/accounts/runtime-sources.json').read_text())
    need(packages['exact_package_count'] == 15 and packages['total_wheel_bytes'] == 3437525)
    wheels = work / 'wheels'; wheels.mkdir(mode=0o750); os.chown(wheels, uid, gid)
    notices = work / 'dependency-notices'; notices.mkdir(mode=0o750); os.chown(notices, uid, gid)
    received = []; total = expanded = 0
    for row in packages['packages']:
        wheel = row['wheel']; need(re.fullmatch('[A-Za-z0-9_.+-]+[.]whl', wheel['filename']))
        need(wheel['url'].startswith('https://files.pythonhosted.org/packages/') and wheel['bytes'] <= 4_000_000)
        with urllib.request.urlopen(wheel['url'], timeout=15) as response:
            need(response.geturl() == wheel['url']); raw = response.read(wheel['bytes'] + 1)
        total += len(raw); need(total <= 5_000_000 and len(raw) == wheel['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'])
        path = wheels / wheel['filename']
        with path.open('xb') as stream: stream.write(raw)
        path.chmod(0o600); os.chown(path, uid, gid)
        text_rows = []
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist(); need(0 < len(members) <= 2000)
            for item in members:
                name = item.filename
                need(not name.startswith('/') and '\\' not in name and all(p not in ('', '.', '..') for p in name.rstrip('/').split('/')))
                mode = item.external_attr >> 16
                need(not stat.S_ISLNK(mode) and item.file_size <= 20_000_000)
                expanded += item.file_size; need(expanded <= 60_000_000)
                if not item.is_dir() and any(re.search(r'license|licence|copying|copyright|notice|authors', p, re.I) for p in name.split('/')):
                    need(item.file_size <= 1_000_000)
                    text = archive.read(item); text.decode('utf8')
                    digest = hashlib.sha256(text).hexdigest(); target = notices / (digest + '.txt')
                    if not target.exists(): target.write_bytes(text); target.chmod(0o640); os.chown(target, uid, gid)
                    text_rows.append({'member': name, 'bytes': len(text), 'sha256': digest})
        need(text_rows)
        received.append({'name': row['name'], 'version': row['version'], 'wheel_sha256': row['sha256'], 'license_texts': text_rows, 'source': row['source']})
    (work / 'dependency-license-review.json').write_text(json.dumps(received, indent=2) + '\n')
    run(user(['/usr/bin/python3', '-m', 'venv', work / 'venv']))
    result = run(user([work / 'venv/bin/python', '-m', 'pip', '--isolated', 'install', '--disable-pip-version-check', '--no-cache-dir',
                      '--no-index', '--no-deps', '--only-binary=:all:', '--require-hashes', '--find-links', wheels,
                      '-r', SOURCE / 'deploy/accounts/requirements.lock']))
    (work / 'install-stdout.log').write_bytes(result.stdout); (work / 'install-stderr.log').write_bytes(result.stderr)
    for label in ('socket', 'pgdata'):
        path = work / label; path.mkdir(mode=0o770 if label == 'socket' else 0o700); os.chown(path, uid, gid)
    run(user([BIN / 'initdb', '-D', work / 'pgdata', '--username=debian', '--auth-local=peer', '--auth-host=reject', '--no-locale', '--encoding=UTF8', '--data-checksums']))
    settings = "\nlisten_addresses=''\nport=55449\ncluster_name='aitrust-account-review'\nunix_socket_directories='" + str(work / 'socket') + "'\nunix_socket_group='ait-intake'\nunix_socket_permissions=0770\nmax_connections=8\nshared_buffers='32MB'\nwork_mem='1MB'\nmaintenance_work_mem='16MB'\nmin_wal_size='32MB'\nmax_wal_size='64MB'\nfsync=on\nfull_page_writes=on\nsynchronous_commit=on\nlog_statement='none'\nlog_min_error_statement='panic'\nlog_parameter_max_length=0\nlog_parameter_max_length_on_error=0\n"
    with (work / 'pgdata/postgresql.conf').open('a') as stream: stream.write(settings)
    (work / 'pgdata/pg_hba.conf').write_text('local all debian peer\nlocal ait_account_review,ait_account_restore ait_account_runtime peer map=account_review\nlocal all all reject\nhost all all 0.0.0.0/0 reject\nhost all all ::0/0 reject\n')
    (work / 'pgdata/pg_ident.conf').write_text('account_review ait-intake ait_account_runtime\n')
    for path in (work / 'pgdata').glob('*.conf'): os.chown(path, uid, gid); path.chmod(0o600)
    log = work / 'postgres.log'; log.touch(mode=0o600); os.chown(log, uid, gid)
    run(user([BIN / 'pg_ctl', '-D', work / 'pgdata', '-l', log, '-w', 'start']))
    guard_cluster(work)
    sql(work, 'CREATE ROLE ait_account_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS; CREATE ROLE ait_account_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 2;')
    sql(work, 'CREATE DATABASE ait_account_review OWNER ait_account_owner TEMPLATE template0;')
    sql(work, 'REVOKE ALL ON DATABASE ait_account_review FROM PUBLIC; GRANT CONNECT ON DATABASE ait_account_review TO ait_account_runtime;')
    sql(work, 'REVOKE ALL ON SCHEMA public FROM PUBLIC;', 'ait_account_review')
    source = (SOURCE / 'deploy/accounts/001-account-schema.sql').read_bytes(); digest = hashlib.sha256(source).hexdigest()
    schema = source.decode().replace('SOURCE_DIGEST', digest)
    failure = sql(work, schema.replace('COMMIT;', 'SELECT 1/0;\nCOMMIT;'), 'ait_account_review', good=False)
    need(failure.returncode != 0 and sql(work, "SELECT count(*) FROM pg_namespace WHERE nspname='accounts';", 'ait_account_review').stdout.strip() == b'0')
    sql(work, schema, 'ait_account_review')
    repeated = sql(work, schema, 'ait_account_review', good=False); need(repeated.returncode != 0)
    runtime_dir = work / 'runtime'; runtime_dir.mkdir(mode=0o700); os.chown(runtime_dir, pwd.getpwnam('ait-intake').pw_uid, gid)
    profile = {'format': 'account-postgres-runtime/v1', 'socket': str(work / 'socket'), 'port': 55449, 'database': 'ait_account_review',
               'role': 'ait_account_runtime', 'server_os_user': 'debian', 'cluster': 'aitrust-account-review', 'schema_sha256': digest}
    profile_path = runtime_dir / 'profile.json'; profile_path.write_text(json.dumps(profile)); profile_path.chmod(0o600); os.chown(profile_path, pwd.getpwnam('ait-intake').pw_uid, gid)
    actual = sql(work, 'SELECT current_user,session_user;', 'ait_account_review', runtime=True).stdout.strip()
    need(actual == b'ait_account_runtime|ait_account_runtime')
    checks = {}
    for label, query in [('no_schema_create', 'CREATE TABLE accounts.not_allowed(x integer);'), ('no_owner_role', 'SET ROLE ait_account_owner;'), ('no_temp', 'CREATE TEMP TABLE not_allowed(x integer);')]:
        checks[label] = sql(work, query, 'ait_account_review', runtime=True, good=False).returncode != 0
    need(all(checks.values()))
    return {'pass': True, 'installed_packages': 15, 'wheel_bytes': total, 'expanded_wheel_bytes': expanded,
            'actual_role': 'ait_account_runtime', 'migration_rollback': True, 'existing_schema_refused': True,
            'privilege_refusals': checks, 'public_service_enabled': False, 'payments_processed': False}


def restore(work):
    guard_cluster(work)
    backup = work / 'synthetic-review.pgdump'
    need(not backup.exists() and sql(work, "SELECT count(*) FROM pg_database WHERE datname='ait_account_restore';").stdout.strip() == b'0')
    run(user([BIN / 'pg_dump', '-w', '-h', work / 'socket', '-p', '55449', '-U', 'debian', '-d',
              'ait_account_review', '--format=custom', '--no-owner', '--file', backup]))
    backup.chmod(0o600); need(0 < backup.stat().st_size <= 5_000_000)
    digest = hashlib.sha256(backup.read_bytes()).hexdigest()
    sql(work, 'CREATE DATABASE ait_account_restore OWNER ait_account_owner TEMPLATE template0;')
    sql(work, 'REVOKE ALL ON DATABASE ait_account_restore FROM PUBLIC; GRANT CONNECT ON DATABASE ait_account_restore TO ait_account_runtime;')
    run(user([BIN / 'pg_restore', '-w', '-h', work / 'socket', '-p', '55449', '-U', 'debian', '-d',
              'ait_account_restore', '--exit-on-error', '--single-transaction', '--no-owner',
              '--role=ait_account_owner', backup]))
    runtime = work / 'runtime'; profile = json.loads((runtime / 'profile.json').read_text())
    profile['database'] = 'ait_account_restore'
    path = runtime / 'restore-profile.json'; need(not path.exists())
    path.write_text(json.dumps(profile)); path.chmod(0o600)
    os.chown(path, pwd.getpwnam('ait-intake').pw_uid, grp.getgrnam('ait-intake').gr_gid)
    need(sql(work, 'SELECT current_user,session_user;', 'ait_account_restore', runtime=True).stdout.strip()
         == b'ait_account_runtime|ait_account_runtime')
    return {'pass': True, 'backup_bytes': backup.stat().st_size, 'backup_sha256': digest,
            'actual_restore': True, 'actual_runtime_role': 'ait_account_runtime',
            'synthetic_only': True, 'production_database_modified': False}


def owned_postmaster(work):
    # Ownership check is filesystem/process based, not a diagnostic SQL query.
    # The PG data directory belongs to this previously approved nonce only.
    data = work / 'pgdata'; info = data.stat(follow_symlinks=False)
    need(stat.S_ISDIR(info.st_mode) and info.st_uid == pwd.getpwnam('debian').pw_uid
         and stat.S_IMODE(info.st_mode) == 0o700)
    fd = None
    try:
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM, signal.SIGINT})
        try:
            fd = os.open(data / 'postmaster.pid', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)
        row = os.fstat(fd); need(stat.S_ISREG(row.st_mode) and row.st_uid == info.st_uid and row.st_size <= 4096)
        raw = os.read(fd, 4097); need(len(raw) <= 4096)
    finally:
        if fd is not None:
            os.close(fd)
    lines = raw.decode('ascii').splitlines()
    need(len(lines) >= 2 and lines[0].isdigit() and lines[1] == str(data))
    pid = int(lines[0]); need(pid > 1)
    process = Path('/proc') / str(pid)
    identity = (process / 'stat').read_text().rsplit(')', 1)[1].split()[19]
    command = (process / 'cmdline').read_bytes().split(b'\0')
    need(command[:3] == [str(BIN / 'postgres').encode(), b'-D', str(data).encode()])
    uid = next(line for line in (process / 'status').read_text().splitlines() if line.startswith('Uid:')).split()[1]
    need(int(uid) == info.st_uid)
    return pid, identity


def start(work):
    need(not (work / 'pgdata/postmaster.pid').exists())
    info = (work / 'pgdata').stat(follow_symlinks=False)
    need(stat.S_ISDIR(info.st_mode) and info.st_uid == pwd.getpwnam('debian').pw_uid
         and stat.S_IMODE(info.st_mode) == 0o700 and (work / 'pgdata/PG_VERSION').read_text().strip() == '18')
    run(user([BIN / 'pg_ctl', '-D', work / 'pgdata', '-l', work / 'postgres.log', '-t', '10', '-w', 'start']))
    try:
        guard_cluster(work)
    except BaseException:
        try: stop(work)
        except BaseException: pass
        raise
    return {'pass': True, 'owned_existing_cluster_started': True, 'public_service_enabled': False}


def stop(work):
    pid, identity = owned_postmaster(work)
    run(user([BIN / 'pg_ctl', '-D', work / 'pgdata', '-m', 'fast', '-t', '10', '-w', 'stop']))
    need(not (work / 'pgdata/postmaster.pid').exists() and not (work / 'socket/.s.PGSQL.55449').exists())
    try:
        now = Path('/proc') / str(pid) / 'stat'
        fields = now.read_text().rsplit(')', 1)[1].split()
        need(fields[19] != identity or fields[0] == 'Z')
    except FileNotFoundError:
        pass
    return {'pass': True, 'owned_cluster_stopped': True, 'owned_pg_socket_absent': True,
            'pg_ctl_wait_completed': True, 'owned_workspace_retained': True}


def observe_review(work):
    pid, _ = owned_postmaster(work); pids = [pid]; identities = {}; pss = 0
    for parent in pids:
        try:
            pids.extend(int(v) for v in Path(f'/proc/{parent}/task/{parent}/children').read_text().split() if int(v) not in pids)
        except FileNotFoundError:
            pass
    for pid in pids:
        try:
            identities[pid] = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]
            lines = Path(f'/proc/{pid}/smaps_rollup').read_text().splitlines()
            pss += int(next(line for line in lines if line.startswith('Pss:')).split()[1])
        except (FileNotFoundError, ProcessLookupError, StopIteration):
            pass
    allocated = int(run(['du', '-s', '-B1', work]).stdout.split()[0])
    return {'workspace_allocated_bytes': allocated, 'review_pg_idle_pss_kib': pss,
            'pss_is_not_peak_or_whole_runtime_enforcement': True, 'captured_identities': identities}


def main_snapshot(work):
    before = json.loads((work / 'main-before.json').read_text())
    files = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in before['files']}
    query = "SELECT json_build_object('identity',(SELECT system_identifier::text FROM pg_control_system()),'started',pg_postmaster_start_time(),'tables',(SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind='r' AND n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%'));"
    args = ['runuser', '-u', 'postgres', '--', '/usr/bin/env', '-i', 'PATH=/usr/bin:/bin',
            BIN / 'psql', '-XqAtw', '-h', '/var/run/postgresql', '-d', 'aitrustid', '-c',
            'BEGIN READ ONLY; ' + query + ' COMMIT;']
    main = json.loads(run(args).stdout)
    main['identity_sha256'] = hashlib.sha256(main.pop('identity').encode()).hexdigest()
    after = {'files': files, 'main': main}
    return {'main_critical_snapshot_unchanged': before == after, 'main_application_tables': main['tables']}


def finish(work):
    result = {'public_service_enabled': False, 'production_or_payment_active': False}
    original = None
    try:
        result.update(observe_review(work))
    except BaseException as error:
        original = error
        result['original_observer_failure_type'] = type(error).__name__
    finally:
        # No metadata/snapshot diagnostic can bypass verified owned cleanup.
        result['owned_stop_attempted'] = True
        try:
            result.update(stop(work))
        except BaseException as error:
            result['owned_stop_failure_type'] = type(error).__name__
    try:
        result.update(main_snapshot(work))
    except BaseException as error:
        result['main_snapshot_failure_type'] = type(error).__name__
        if original is None: original = error
    try:
        result['owned_http_listener_absent'] = not bool(run(['ss', '-H', '-lnt', 'sport = :18791']).stdout.strip())
    except BaseException as error:
        result['listener_observer_failure_type'] = type(error).__name__
        if original is None: original = error
    result.pop('captured_identities', None)
    result['pass'] = (original is None and result.get('owned_cluster_stopped') is True
                      and result.get('main_critical_snapshot_unchanged') is True
                      and result.get('owned_http_listener_absent') is True
                      and result.get('workspace_allocated_bytes', 512 * 1024**2) < 512 * 1024**2)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('operation', choices=('provision', 'stop', 'guard', 'restore', 'start', 'finish')); p.add_argument('--workspace', required=True, type=Path)
    args = p.parse_args(); owned(args.workspace)
    try:
        if args.operation == 'provision': result = provision(args.workspace)
        elif args.operation == 'stop': result = stop(args.workspace)
        elif args.operation == 'restore': result = restore(args.workspace)
        elif args.operation == 'start': result = start(args.workspace)
        elif args.operation == 'finish': result = finish(args.workspace)
        else: guard_cluster(args.workspace); result = {'pass': True}
        print(json.dumps(result, sort_keys=True)); return 0 if result.get('pass') is True else 2
    except Exception as error:
        print(json.dumps({'pass': False, 'failure_type': type(error).__name__, 'owned_private_workspace_may_remain': True, 'public_service_enabled': False})); return 2


if __name__ == '__main__': raise SystemExit(main())
