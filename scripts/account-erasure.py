#!/usr/bin/env python3
"""Closed synthetic erasure operator; never main PostgreSQL or public serving."""
import argparse
import grp
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import re
import signal
import stat
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('/var/lib/aitrust-id/account-review')
BIN = Path('/usr/lib/postgresql/18/bin')
SOURCE_DB, RESTORE_DB = 'ait_erasure_review', 'ait_erasure_restore'
sys.path.insert(0, str(ROOT))
from tools import account_erasure as e
from tools import account_postgres as p

HBA = ('local all debian peer\nlocal ait_account_review,ait_account_restore ait_account_runtime peer map=account_review\n'
       'local all all reject\nhost all all 0.0.0.0/0 reject\nhost all all ::0/0 reject\n')


def need(value):
    e.need(value)


def run(argv, timeout=8, good=True, data=None):
    """A new owned process group; cancellation cannot abandon a dump child."""
    child, failure, result = None, None, None
    cleanup_errors = []
    try:
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGALRM})
        try:
            child = subprocess.Popen(list(map(str, argv)), stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     start_new_session=True)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)
        stdout, stderr = child.communicate(input=data, timeout=timeout)
        result = subprocess.CompletedProcess(argv, child.returncode, stdout, stderr)
        if good: need(result.returncode == 0)
    except BaseException as error:
        failure = error
    finally:
        if child is not None:
            try:
                if child.poll() is None:
                    try: os.killpg(child.pid, signal.SIGTERM)
                    except ProcessLookupError: pass
                    try: child.communicate(timeout=2)
                    except BaseException as error:
                        cleanup_errors.append(error)
                        try: os.killpg(child.pid, signal.SIGKILL)
                        except ProcessLookupError: pass
                        child.communicate(timeout=2)
            except BaseException as error:
                cleanup_errors.append(error)
            finally:
                for stream in (child.stdin, child.stdout, child.stderr):
                    if stream is not None:
                        try: stream.close()
                        except BaseException as error: cleanup_errors.append(error)
    if failure is not None: raise failure
    if cleanup_errors: raise cleanup_errors[0]
    return result


def old_tool(work):
    path = work / 'source/scripts/account-postgres-review.py'
    need(hashlib.sha256(path.read_bytes()).hexdigest() == 'e302513ff2eb5871bbce90b9c49429c9f06153b71669cd5fdd3942d2b16eb356')
    spec = importlib.util.spec_from_file_location('prior_account_review', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def owned(work, root=True):
    need(sys.platform == 'linux' and work.parent == BASE and re.fullmatch('[0-9a-f]{32}', work.name)
         and ROOT == work / 'erasure-source')
    for part in (work, *work.parents): need(not part.is_symlink())
    info = work.stat()
    need(info.st_uid == pwd.getpwnam('debian').pw_uid and stat.S_IMODE(info.st_mode) == 0o750)
    if root:
        need(os.geteuid() == 0)
        approval = work / 'erasure-approval.json'
        metadata = approval.stat(follow_symlinks=False)
        need(stat.S_ISREG(metadata.st_mode) and metadata.st_uid == 0
             and metadata.st_nlink == 1 and stat.S_IMODE(metadata.st_mode) == 0o600 and metadata.st_size <= 16384)
        value = json.loads(approval.read_text())
        need(value['workspace'] == {'dev': info.st_dev, 'ino': info.st_ino, 'uid': info.st_uid, 'mode': 0o750}
             and value['source_base'] == '5f250b473cba913647ea5599cbcb701594e01497'
             and value['synthetic_only'] is True and value['remote_authorized'] is True)
        for name, expected in value['source'].items():
            need(type(name) is str and not Path(name).is_absolute() and '..' not in Path(name).parts
                 and hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected)
        need(value['source'].get('scripts/account-erasure.py') == hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    else:
        need(os.geteuid() == pwd.getpwnam('debian').pw_uid)


def sql(work, query, database=SOURCE_DB, good=True):
    need(database in (SOURCE_DB, RESTORE_DB, 'postgres', 'ait_account_review'))
    old = old_tool(work)
    # Root invokes a fixed client as the real Unix peer operator; no password.
    argv = ['/usr/bin/env', '-i', 'PATH=/usr/bin:/bin',
                        'PGOPTIONS=-c statement_timeout=3000 -c lock_timeout=1000',
                        BIN / 'psql', '-XqAtw', '-v', 'ON_ERROR_STOP=1', '-h', work / 'socket',
                        '-p', '55449', '-U', 'debian', '-d', conninfo(work, database), '-c', query]
    return run(old.user(argv) if os.geteuid() == 0 else argv, good=good)


def conninfo(work, database):
    need(work.parent == BASE and re.fullmatch('[0-9a-f]{32}', work.name)
         and database in (SOURCE_DB, RESTORE_DB, 'postgres', 'ait_account_review'))
    # One argv value, never shell text; all values have a closed character set.
    return ('host=' + str(work / 'socket') + ' port=55449 dbname=' + database
            + " user=debian requirepeer=debian password='' passfile=/run/aitrust-account-peer-no-password"
            + ' sslmode=disable gssencmode=disable connect_timeout=3')


def private_file(path, value, user):
    need(not path.exists())
    raw = p.c.encode(value) + b'\n'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(fd, 0o600)
        os.fchown(fd, pwd.getpwnam(user).pw_uid, grp.getgrnam('ait-intake').gr_gid)
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    finally:
        os.close(fd)


def operator_record(path, user='debian'):
    """Root copies only fixed operator outputs with verified foreign ownership."""
    from tools.artifact_evidence_io import Capture
    with Capture() as held:
        parent, _ = held.parent(path, private=False)
        info = os.fstat(parent)
        need(user in ('debian', 'ait-intake') and info.st_uid == pwd.getpwnam(user).pw_uid and stat.S_IMODE(info.st_mode) == 0o700)
        raw = held.read(path, 16384, private=False)
        info = os.fstat(held.fds[-1])
        need(info.st_uid == pwd.getpwnam(user).pw_uid and stat.S_IMODE(info.st_mode) == 0o600)
        value = p.c.parse(raw); held.check()
    return value


def profile(work, generation, restored=False):
    database = RESTORE_DB if restored else SOURCE_DB
    identity = sql(work, 'SELECT system_identifier::text FROM pg_catalog.pg_control_system();', database).stdout.strip()
    need(re.fullmatch(rb'[0-9]{1,20}', identity) is not None and int(identity) > 0)
    return {'format': e.PROFILE, 'socket': str(work / 'socket'), 'port': 55449,
            'database': database, 'role': 'ait_account_runtime',
            'server_os_user': 'debian', 'cluster': 'aitrust-account-review', 'schema_sha256': p.SCHEMA_SHA,
            'erasure_sha256': e.MIGRATION_SHA, 'generation': generation,
            'system_identity_sha256': e.digest(identity),
            'purpose': 'restored' if restored else 'source',
            'restore_receipt': str(work / 'erasure/runtime/serving-receipt.json') if restored else None}


def bootstrap(work):
    old = old_tool(work); old.owned(work); old.guard_cluster(work)
    available = next(int(line.split()[1]) * 1024 for line in Path('/proc/meminfo').read_text().splitlines()
                     if line.startswith('MemAvailable:'))
    disk = os.statvfs(work)
    need(available >= 2 * 1024**3 and disk.f_bavail * disk.f_frsize >= 128 * 1024**2)
    need(sql(work, "SELECT count(*) FROM pg_database WHERE datname IN ('ait_erasure_review','ait_erasure_restore');", 'postgres').stdout.strip() == b'0')
    need(sql(work, "SELECT count(*) FROM pg_stat_activity WHERE datname='ait_account_review';", 'postgres').stdout.strip() == b'0')
    need(sql(work, 'SELECT schema_sha FROM accounts.meta WHERE singleton=1;', 'ait_account_review').stdout.strip().decode() == p.SCHEMA_SHA)
    table_names = sql(work, "SELECT tablename FROM pg_tables WHERE schemaname='accounts' ORDER BY tablename;", 'ait_account_review').stdout.decode().splitlines()
    need(tuple(table_names) == p.TABLES)
    count = int(sql(work, 'SELECT count(*) FROM accounts.accounts;', 'ait_account_review').stdout)
    need(count <= 10 and int(sql(work, 'SELECT count(*) FROM accounts.history;', 'ait_account_review').stdout) <= 200)
    folder = work / 'erasure'; need(not folder.exists()); folder.mkdir(mode=0o750)
    os.chown(folder, pwd.getpwnam('debian').pw_uid, grp.getgrnam('ait-intake').gr_gid)
    for name, user in (('operator', 'debian'), ('runtime', 'ait-intake')):
        path = folder / name; path.mkdir(mode=0o700)
        os.chown(path, pwd.getpwnam(user).pw_uid, grp.getgrnam('ait-intake').gr_gid)
    # Clone the exact qualified001 state. Do not edit001, clear data/rates or copy DDL by hand.
    sql(work, 'CREATE DATABASE ait_erasure_review WITH TEMPLATE ait_account_review OWNER ait_account_owner ALLOW_CONNECTIONS false;', 'postgres')
    sql(work, 'REVOKE ALL ON DATABASE ait_erasure_review FROM PUBLIC,ait_account_runtime;', 'postgres')
    sql(work, 'ALTER DATABASE ait_erasure_review ALLOW_CONNECTIONS true;', 'postgres')
    migration = (ROOT / e.MIGRATION_FILE).read_bytes(); need(e.digest(migration) == e.MIGRATION_SHA)
    generation = str(uuid.uuid4())
    body = migration.decode().replace('DATABASE_GENERATION', generation).replace('ERASURE_SOURCE_DIGEST', e.MIGRATION_SHA)
    missing = sql(work, 'BEGIN; DELETE FROM accounts.meta;\n' + body.replace('BEGIN;', '', 1), good=False)
    need(missing.returncode != 0 and sql(work, 'SELECT count(*) FROM accounts.meta WHERE singleton=1;').stdout.strip() == b'1'
         and sql(work, "SELECT count(*) FROM pg_tables WHERE schemaname='accounts' AND tablename LIKE 'erasure_%';").stdout.strip() == b'0')
    failure = sql(work, body.replace('COMMIT;', 'SELECT 1/0;\nCOMMIT;'), good=False)
    need(failure.returncode != 0 and sql(work, "SELECT count(*) FROM pg_tables WHERE schemaname='accounts' AND tablename LIKE 'erasure_%';").stdout.strip() == b'0'
         and int(sql(work, 'SELECT count(*) FROM accounts.accounts;').stdout) == count)
    sql(work, body)
    need(sql(work, body, good=False).returncode != 0)
    hba = work / 'pgdata/pg_hba.conf'; need(hba.read_text() == HBA)
    original = folder / 'operator/original-review-hba.txt'
    original.write_text(HBA); original.chmod(0o600); os.chown(original, pwd.getpwnam('debian').pw_uid, grp.getgrnam('ait-intake').gr_gid)
    updated = HBA.replace('local all all reject', 'local ait_erasure_review,ait_erasure_restore ait_account_runtime peer map=account_review\nlocal all all reject')
    hba.write_text(updated); hba.chmod(0o600); os.chown(hba, pwd.getpwnam('debian').pw_uid, grp.getgrnam('ait-intake').gr_gid)
    run(old.user([BIN / 'pg_ctl', '-D', work / 'pgdata', 'reload']))
    selected = profile(work, generation)
    private_file(folder / 'operator/source-profile.json', selected, 'debian')
    private_file(folder / 'runtime/source-profile.json', selected, 'ait-intake')
    return {'pass': True, 'migration_rollback': True, 'missing_meta_refused_and_rolled_back': True, 'duplicate_migration_refused': True,
            'inherited_accounts_preserved': count, 'prior_databases_unchanged': True}


def worker(work, operation):
    if operation == 'restore': return restore(work)
    path = work / 'erasure/operator'; selected = p.load_profile(path / ('restore-profile.json' if operation in ('reconcile', 'validate-ready') else 'source-profile.json'))
    now = lambda: int(time.time())
    if operation == 'validate-ready':
        receipt, _ = e.read_record(path / 'serving-receipt.json')
        with e.operator(selected) as transaction:
            e.require_quiescent(transaction)
            e.verify_receipt(transaction, selected, receipt)
        return {'pass': True, 'authoritative_operator_receipt_and_actual_database_ready': True}
    if operation == 'backup':
        def dump(snapshot):
            target = path / 'synthetic.pgdump'; need(not os.path.lexists(target))
            run([BIN / 'pg_dump', '-w', '-d', conninfo(work, SOURCE_DB),
                 '--format=custom', '--no-owner', '--snapshot=' + snapshot, '--file', target], timeout=5)
            target.chmod(0o600); need(0 < target.stat().st_size <= 5 * 1024 * 1024)
            return {'bytes': target.stat().st_size, 'sha256': e.digest(target.read_bytes())}
        value = e.snapshot_backup(selected, dump, now)
        return {'pass': True, 'backup_manifest_sha256': e.write_record(path / 'backup.json', value)}
    if operation == 'export':
        value = e.export_journal(selected, now)
        sha = e.write_record(path / 'journal.json', value)
        checkpoint = {'format': 'account-erasure-checkpoint/v1', 'generation': value['generation'],
                      'journal_sha256': sha, 'head': value['head'], 'captured_at': value['captured_at']}
        e.write_record(path / 'selected-checkpoint.json', checkpoint)
        return {'pass': True, 'journal_sha256': sha, 'rows': len(value['rows']),
                'checkpoint_source': 'operator-selected actual quiesced synthetic source; not independent latest-copy proof'}
    if operation == 'prune': return {'pass': True, **e.prune(selected, now)}
    manifest, _ = e.read_record(path / 'backup.json'); received, raw = e.read_record(path / 'journal.json')
    expected, _ = e.read_record(path / 'selected-checkpoint.json')
    dump = path / 'synthetic.pgdump'
    need(dump.stat().st_size == manifest['dump_bytes'] and e.digest(dump.read_bytes()) == manifest['dump_sha256'])
    receipt = e.reconcile(selected, manifest, received, expected, raw, now)
    return {'pass': True, 'receipt_sha256': e.write_record(path / 'serving-receipt.json', receipt),
            'public_service_enabled': False}


def restore(work):
    from tools.artifact_evidence_io import Capture
    path = work / 'erasure/operator'; manifest, _ = e.read_record(path / 'backup.json')
    e.backup(manifest)
    dump = path / 'synthetic.pgdump'
    with Capture() as held:
        raw = held.read(dump, 5 * 1024 * 1024)
        need(len(raw) == manifest['dump_bytes'] and e.digest(raw) == manifest['dump_sha256'])
        held.check()
    need(sql(work, "SELECT count(*) FROM pg_database WHERE datname='ait_erasure_restore';", 'postgres').stdout.strip() == b'0')
    sql(work, 'CREATE DATABASE ait_erasure_restore OWNER ait_account_owner TEMPLATE template0 ALLOW_CONNECTIONS false;', 'postgres')
    sql(work, 'REVOKE ALL ON DATABASE ait_erasure_restore FROM PUBLIC,ait_account_runtime;', 'postgres')
    sql(work, 'ALTER DATABASE ait_erasure_restore ALLOW_CONNECTIONS true;', 'postgres')
    run([BIN / 'pg_restore', '-w', '-d', conninfo(work, RESTORE_DB),
         '--exit-on-error', '--single-transaction', '--no-owner', '--role=ait_account_owner'], data=raw)
    # Built-in catalog function ACLs are not assumed to travel in a user dump.
    sql(work, 'REVOKE EXECUTE ON FUNCTION pg_catalog.pg_control_system() FROM PUBLIC; GRANT EXECUTE ON FUNCTION pg_catalog.pg_control_system() TO ait_account_runtime;', RESTORE_DB)
    selected = profile(work, manifest['generation'], True)
    with e.operator(selected, write=True) as transaction:
        state = e.state(transaction, True)
        need(state['restored_from_sha'] is None and state['reconciled_sha'] is None
             and state['generation'] == manifest['generation'])
        transaction.raw('UPDATE accounts.erasure_state SET restored_from_sha=%s WHERE singleton=1', (manifest['dump_sha256'],)).close()
    e.write_record(path / 'restore-profile.json', selected)
    return {'pass': True, 'restored_old_backup': True, 'runtime_connect_revoked': True}


def root_operation(work, operation):
    if operation == 'bootstrap': return bootstrap(work)
    if operation == 'capture-fixture':
        value = operator_record(work / 'erasure/runtime/fixture.json', 'ait-intake')
        need(value.get('format') == 'synthetic-account-erasure-fixture/v1' and len(value.get('accounts', [])) == 2)
        private_file(work / 'erasure/operator/fixture.json', value, 'debian')
        return {'pass': True, 'synthetic_two_account_fixture_copied_to_review_operator': True}
    if operation == 'probe-unreconciled':
        need(sql(work, 'SELECT reconciled_sha IS NULL AND reconciled_at IS NULL FROM accounts.erasure_state WHERE singleton=1;', RESTORE_DB).stdout.strip() == b't')
        need(sql(work, "SELECT has_database_privilege('ait_account_runtime','ait_erasure_restore','CONNECT');", 'postgres').stdout.strip() == b'f')
        failure, value = None, None
        try:
            sql(work, 'GRANT CONNECT ON DATABASE ait_erasure_restore TO ait_account_runtime;', 'postgres')
            result = run(old_tool(work).user([work / 'venv/bin/python', ROOT / 'scripts/verify-account-erasure.py',
                                             '--phase', 'unready', '--workspace', work], account='ait-intake'))
            value = json.loads(result.stdout); need(value.get('pass') is True)
        except BaseException as error:
            failure = error
        finally:
            try: sql(work, 'REVOKE CONNECT ON DATABASE ait_erasure_restore FROM ait_account_runtime;', 'postgres')
            except BaseException as error:
                if failure is None: failure = error
        if failure is not None: raise failure
        return value
    if operation in ('backup', 'export', 'restore', 'reconcile', 'prune', 'validate-ready'):
        result = run(old_tool(work).user([work / 'venv/bin/python', ROOT / 'scripts/account-erasure.py', operation,
                                         '--workspace', work, '--worker']))
        value = json.loads(result.stdout); need(value.get('pass') is True)
        if operation == 'reconcile':
            receipt = operator_record(work / 'erasure/operator/serving-receipt.json')
            private_file(work / 'erasure/runtime/serving-receipt.json', receipt, 'ait-intake')
        if operation == 'restore':
            selected = operator_record(work / 'erasure/operator/restore-profile.json')
            private_file(work / 'erasure/runtime/restore-profile.json', selected, 'ait-intake')
        return value
    if operation == 'finish':
        errors = []
        try:
            for name in (SOURCE_DB, RESTORE_DB):
                exists = sql(work, "SELECT count(*) FROM pg_database WHERE datname='" + name + "';", 'postgres').stdout.strip() == b'1'
                if exists: sql(work, 'REVOKE CONNECT ON DATABASE ' + name + ' FROM ait_account_runtime;', 'postgres')
        except BaseException as error: errors.append(type(error).__name__)
        finally:
            result = old_tool(work).finish(work)
        result['erasure_quiescence_failure_types'] = errors
        result['erasure_workspace_within_256_mib'] = (type(result.get('workspace_allocated_bytes')) is int
                                                      and result['workspace_allocated_bytes'] <= 256 * 1024**2)
        result['pass'] = result['pass'] and not errors and result['erasure_workspace_within_256_mib']
        return result
    database = RESTORE_DB if operation.endswith('restored') else SOURCE_DB
    if operation.startswith('quiesce'):
        sql(work, 'REVOKE CONNECT ON DATABASE ' + database + ' FROM ait_account_runtime;', 'postgres')
        need(sql(work, "SELECT count(*) FROM pg_stat_activity WHERE datname='" + database + "';", 'postgres').stdout.strip() == b'0')
        return {'pass': True, 'runtime_connect_revoked': True}
    if database == RESTORE_DB:
        # Runtime-owned bytes never authorize CONNECT. A real operator peer
        # validates its own private receipt against authoritative current DB state.
        result = run(old_tool(work).user([work / 'venv/bin/python', ROOT / 'scripts/account-erasure.py', 'validate-ready',
                                         '--workspace', work, '--worker']))
        need(json.loads(result.stdout).get('authoritative_operator_receipt_and_actual_database_ready') is True)
    sql(work, 'GRANT CONNECT ON DATABASE ' + database + ' TO ait_account_runtime;', 'postgres')
    return {'pass': True, 'synthetic_runtime_peer_enabled': True, 'public_service_enabled': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('bootstrap', 'capture-fixture', 'backup', 'export', 'restore', 'probe-unreconciled', 'reconcile', 'prune', 'validate-ready',
                        'quiesce-source', 'quiesce-restored', 'grant-source', 'grant-restored', 'finish'))
    parser.add_argument('--workspace', required=True, type=Path); parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        owned(args.workspace, not args.worker)
        if args.worker:
            need(args.operation in ('backup', 'export', 'restore', 'reconcile', 'prune', 'validate-ready'))
            value = worker(args.workspace, args.operation)
        else: value = root_operation(args.workspace, args.operation)
        print(json.dumps(value, sort_keys=True)); return 0 if value.get('pass') is True else 2
    except Exception as error:
        print(json.dumps({'pass': False, 'state': 'UNAVAILABLE', 'failure_type': type(error).__name__,
                          'owned_private_artifacts_retained': True, 'public_service_enabled': False})); return 2


if __name__ == '__main__': raise SystemExit(main())
