"""Private operator recovery barrier; no tag, HTTP, payment or training dependency."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re

from tools import account_core as c
from tools.account_store import MAX_ACCOUNTS
from tools.artifact_evidence_io import Capture

MIGRATION_FILE = 'deploy/accounts/002-erasure-schema.sql'
MIGRATION_SHA = '9220cca1e4e6663eeab57be6dbccda245253f95a576ddfc28174551c8e58e757'
FUNCTION_SHA = {'reserve_erasure_slot': '0c37600c9e7ef0ed8d26e5e7c34cc028c25248d490afb2fe00ee5b8bb12ef5dd', 'record_account_erasure': '9520735b204869a88541a6a4ea09eeab840ece1502a07c4bf82a383f1d126134'}
PROFILE = 'account-postgres-runtime/v2'
DATABASES = ('ait_erasure_review', 'ait_erasure_restore')
WINDOW = 7 * 86400
MAX_ROWS, MAX_BYTES = 4096, 1024 * 1024
STATE_FIELDS = ('generation', 'migration_sha', 'clock', 'head', 'floor', 'floor_time',
                'reserved_live', 'retained_rows', 'restored_from_sha', 'reconciled_sha', 'reconciled_at')
HEX = re.compile('[0-9a-f]{64}')


def need(value):
    c.need(value, 'recovery_unavailable', 503)


def digest(raw):
    need(type(raw) is bytes)
    return hashlib.sha256(raw).hexdigest()


def integer(value, minimum=0):
    need(type(value) is int and minimum <= value < 2**63)
    return value


def sha(value):
    need(type(value) is str and HEX.fullmatch(value) is not None)
    return value


def _migration_one():
    from tools.account_postgres import SCHEMA_SHA
    return SCHEMA_SHA


def _clock(now):
    return integer(now() if callable(now) else now, 1)


def parse_record(raw):
    need(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES)
    def unique(pairs):
        value = {}
        for key, item in pairs:
            need(key not in value)
            value[key] = item
        return value
    try:
        value = json.loads(raw, object_pairs_hook=unique,
                           parse_constant=lambda _: need(False))
    except (ValueError, UnicodeError, RecursionError):
        raise c.AccountError('recovery_unavailable', 503) from None
    need(type(value) is dict)
    return value


def read_record(path):
    """Bounded duplicate-refusing file input, never a URL or HTTP request."""
    with Capture() as held:
        raw = held.read(Path(path), MAX_BYTES)
        value = parse_record(raw)
        held.check()
    return value, raw


def write_record(path, value):
    """Exclusive private output; never overwrite a receipt after uncertain commit."""
    raw = c.encode(value) + b'\n'
    with Capture() as held:
        held.save(path, value, MAX_BYTES)
    return digest(raw)


def _rows(transaction, query, values=()):
    """The operator's journal limit exceeds the unchanged domain's1001 rows."""
    cursor = transaction.raw(query, values)
    try:
        rows = cursor.fetchmany(MAX_ROWS + 1)
        need(len(rows) <= MAX_ROWS)
        transaction.tick()
        return rows
    finally:
        cursor.close()


def journal(value):
    need(type(value) is dict and set(value) == {'format', 'generation', 'migration_one', 'migration_two',
         'captured_at', 'clock', 'head', 'floor', 'floor_time', 'rows'})
    need(value['format'] == 'account-erasure-journal/v1'
         and value['migration_one'] == _migration_one() and value['migration_two'] == MIGRATION_SHA)
    c.identity(value['generation'])
    captured = integer(value['captured_at'], 1)
    clock = integer(value['clock'])
    head, floor = integer(value['head']), integer(value['floor'])
    floor_time = integer(value['floor_time'])
    need(floor <= head and 0 <= floor_time <= clock <= captured
         and type(value['rows']) is list and len(value['rows']) == head - floor <= MAX_ROWS)
    seen, previous = set(), floor_time
    for sequence, row in enumerate(value['rows'], floor + 1):
        need(type(row) is dict and set(row) == {'sequence', 'account_id', 'erased_at'})
        need(integer(row['sequence'], 1) == sequence)
        identity = c.identity(row['account_id'])
        at = integer(row['erased_at'], 1)
        need(identity not in seen and previous <= at <= clock and at >= captured - WINDOW)
        seen.add(identity); previous = at
    need(len(c.encode(value)) <= MAX_BYTES)
    return value


def backup(value):
    need(type(value) is dict and set(value) == {'format', 'generation', 'migration_one', 'migration_two',
         'captured_at', 'clock', 'head', 'dump_sha256', 'dump_bytes'})
    need(value['format'] == 'account-erasure-backup/v1'
         and value['migration_one'] == _migration_one() and value['migration_two'] == MIGRATION_SHA)
    c.identity(value['generation']); sha(value['dump_sha256'])
    need(0 < integer(value['dump_bytes']) <= 5 * 1024 * 1024)
    need(integer(value['clock']) <= integer(value['captured_at'], 1))
    integer(value['head'])
    return value


def checkpoint(value):
    need(type(value) is dict and set(value) == {'format', 'generation', 'journal_sha256', 'head', 'captured_at'})
    need(value['format'] == 'account-erasure-checkpoint/v1')
    c.identity(value['generation']); sha(value['journal_sha256'])
    integer(value['head']); integer(value['captured_at'], 1)
    return value


def compatible(manifest, received, expected, raw, now):
    """A trusted operator selects expected; a hash does not prove it is latest."""
    backup(manifest); journal(received); checkpoint(expected)
    need(journal(parse_record(raw)) == received)
    now = _clock(now)
    need(manifest['generation'] == received['generation'] == expected['generation']
         and expected['journal_sha256'] == digest(raw)
         and expected['head'] == received['head']
         and expected['captured_at'] == received['captured_at']
         and now - WINDOW <= manifest['captured_at'] <= received['captured_at'] <= now
         and manifest['clock'] <= received['clock'] <= now
         and received['floor'] <= manifest['head'] <= received['head'])
    return now


def state(transaction, locked=False):
    row = transaction.one('SELECT ' + ','.join(STATE_FIELDS)
                          + ',(SELECT count(*) FROM accounts.accounts) FROM accounts.erasure_state WHERE singleton=1'
                          + (' FOR UPDATE' if locked else ''))
    need(row is not None and len(row) == len(STATE_FIELDS) + 1)
    value = dict(zip(STATE_FIELDS, row[:-1]))
    c.identity(value['generation']); need(value['migration_sha'] == MIGRATION_SHA)
    for key in ('clock', 'head', 'floor', 'floor_time', 'reserved_live', 'retained_rows'):
        integer(value[key])
    need(value['floor'] <= value['head'] and value['retained_rows'] == value['head'] - value['floor']
         and value['reserved_live'] + value['retained_rows'] <= MAX_ROWS
         and value['floor_time'] <= value['clock'] and row[-1] == value['reserved_live'])
    need((value['reconciled_sha'] is None) == (value['reconciled_at'] is None))
    if value['restored_from_sha'] is not None: sha(value['restored_from_sha'])
    if value['reconciled_sha'] is not None:
        sha(value['reconciled_sha']); integer(value['reconciled_at'], 1); sha(value['restored_from_sha'])
    return value


def system_identity(transaction):
    row = transaction.one('SELECT system_identifier::text FROM pg_catalog.pg_control_system()')
    need(row is not None and len(row) == 1 and type(row[0]) is str
         and re.fullmatch('[0-9]{1,20}', row[0]) is not None and int(row[0]) > 0)
    return digest(row[0].encode('ascii'))


def verify_receipt(transaction, profile, receipt=None):
    """Readiness is authoritative DB state, never a runtime-owned file alone."""
    need(profile['purpose'] == 'restored' and profile['database'] == 'ait_erasure_restore')
    value = state(transaction)
    sha(value['reconciled_sha']); integer(value['reconciled_at'], 1); sha(value['restored_from_sha'])
    if receipt is None: receipt, _ = read_record(profile['restore_receipt'])
    need(type(receipt) is dict and set(receipt) == {'format', 'database', 'database_oid', 'generation', 'migration_one', 'migration_two',
         'system_identity_sha256', 'journal_sha256', 'backup_sha256', 'head', 'reconciled_at'})
    sha(receipt['journal_sha256']); sha(receipt['backup_sha256']); sha(receipt['system_identity_sha256'])
    integer(receipt['reconciled_at'], 1); integer(receipt['head']); integer(receipt['database_oid'], 1)
    need(receipt['format'] == 'account-erasure-serving-receipt/v1'
         and receipt['database'] == profile['database'] and receipt['generation'] == value['generation']
         and receipt['migration_one'] == _migration_one() and receipt['migration_two'] == MIGRATION_SHA
         and receipt['journal_sha256'] == value['reconciled_sha']
         and receipt['backup_sha256'] == value['restored_from_sha']
         and receipt['reconciled_at'] == value['reconciled_at']
         and receipt['head'] <= value['head']
         and receipt['system_identity_sha256'] == profile['system_identity_sha256'] == system_identity(transaction))
    oid = transaction.one('SELECT oid::bigint FROM pg_database WHERE datname=current_database()')
    need(oid == (receipt['database_oid'],))
    return True


def verify_runtime(transaction, profile):
    """Actual migration/function/ACL identity; runtime never changes the journal."""
    value = state(transaction)
    need(value['generation'] == profile['generation'] and profile['erasure_sha256'] == MIGRATION_SHA
         and system_identity(transaction) == profile['system_identity_sha256'])
    functions = transaction.all("SELECT p.proname,p.prosecdef,p.proconfig,pg_get_userbyid(p.proowner),has_function_privilege(current_user,p.oid,'EXECUTE'),p.prosrc,l.lanname,p.pronargs FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.oid=p.prolang WHERE n.nspname='accounts' ORDER BY p.proname")
    need(len(functions) == 2)
    for row, name in zip(functions, ('record_account_erasure', 'reserve_erasure_slot')):
        need(row[:5] == (name, True, ['search_path=pg_catalog'], 'ait_account_owner', False)
             and row[6:] == ('plpgsql', 0) and type(row[5]) is str
             and digest(row[5].encode()) == FUNCTION_SHA[name])
    owners = transaction.all("SELECT relname,pg_get_userbyid(relowner) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='accounts' AND relname IN ('erasure_state','erasure_journal') ORDER BY relname")
    need(owners == [('erasure_journal', 'ait_account_owner'), ('erasure_state', 'ait_account_owner')])
    triggers = transaction.all("SELECT t.tgname,t.tgtype,t.tgenabled,p.proname FROM pg_trigger t JOIN pg_class r ON r.oid=t.tgrelid JOIN pg_namespace n ON n.oid=r.relnamespace JOIN pg_proc p ON p.oid=t.tgfoid WHERE n.nspname='accounts' AND r.relname='accounts' AND NOT t.tgisinternal ORDER BY t.tgname")
    need(triggers == [('account_erasure_record', 9, 'O', 'record_account_erasure'),
                      ('account_erasure_reservation', 5, 'O', 'reserve_erasure_slot')])
    permissions = transaction.one("SELECT has_table_privilege(current_user,'accounts.erasure_journal','SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'),has_table_privilege(current_user,'accounts.erasure_state','INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')")
    need(permissions == (False, False))
    if profile['purpose'] == 'restored':
        verify_receipt(transaction, profile)


@contextmanager
def operator(profile, write=False):
    """Fixed peer operator only; same maintained driver and connection defenses."""
    from tools import account_postgres as p
    need(profile['format'] == PROFILE and profile['database'] in DATABASES)
    connection, attempted = None, False
    try:
        selected = dict(profile, role='debian')
        connection = p.connect(selected)
        transaction = p.Transaction(connection)
        identity = transaction.one("SELECT current_database(),current_user,session_user,current_setting('cluster_name'),current_setting('listen_addresses'),inet_server_addr()")
        need(identity == (profile['database'], 'debian', 'debian', 'aitrust-account-review', '', None)
             and system_identity(transaction) == profile['system_identity_sha256'])
        transaction.raw('BEGIN' if write else 'BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY').close()
        yield transaction
        transaction.tick(); attempted = True
        transaction.raw('COMMIT').close()
        connection.close(); connection = None
    except BaseException as error:
        if connection is not None:
            if not attempted:
                try: connection.execute('ROLLBACK').close()
                except BaseException: pass
            try: connection.close()
            except BaseException: pass
        if attempted:
            if isinstance(error, KeyboardInterrupt): raise p.CommitInterrupted('Recovery may have committed.') from None
            if isinstance(error, SystemExit): raise p.CommitExit(error.code) from None
            raise p.CommitUncertain() from None
        if isinstance(error, (KeyboardInterrupt, SystemExit, c.AccountError)): raise
        raise c.AccountError('recovery_unavailable', 503) from None


def require_quiescent(transaction):
    row = transaction.one("SELECT has_database_privilege('ait_account_runtime',current_database(),'CONNECT'),(SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid())")
    need(row == (False, 0))


def export_journal(profile, now):
    need(profile['purpose'] == 'source' and profile['database'] == 'ait_erasure_review')
    with operator(profile) as transaction:
        require_quiescent(transaction)
        value = state(transaction)
        captured = _clock(now)
        need(value['clock'] <= captured)
        rows = _rows(transaction, 'SELECT sequence,account_id,erased_at FROM accounts.erasure_journal ORDER BY sequence LIMIT 4097')
        result = {'format': 'account-erasure-journal/v1', 'generation': value['generation'],
                  'migration_one': _migration_one(), 'migration_two': MIGRATION_SHA, 'captured_at': captured,
                  'clock': value['clock'], 'head': value['head'], 'floor': value['floor'], 'floor_time': value['floor_time'],
                  'rows': [dict(zip(('sequence', 'account_id', 'erased_at'), row)) for row in rows]}
        return journal(result)


def snapshot_backup(profile, dump, now):
    """dump receives the held exported snapshot and must return exact bytes/hash."""
    need(profile['purpose'] == 'source' and profile['database'] == 'ait_erasure_review')
    with operator(profile) as transaction:
        require_quiescent(transaction)
        value = state(transaction)
        need(value['restored_from_sha'] is None and value['reconciled_sha'] is None)
        captured = _clock(now); need(value['clock'] <= captured)
        snapshot = transaction.one('SELECT pg_export_snapshot()')[0]
        need(type(snapshot) is str and re.fullmatch('[0-9A-Fa-f]{8}-[0-9A-Fa-f]{8}-[0-9]+', snapshot) is not None)
        received = dump(snapshot)
        need(type(received) is dict and set(received) == {'sha256', 'bytes'})
        transaction.tick()
        return backup({'format': 'account-erasure-backup/v1', 'generation': value['generation'],
                       'migration_one': _migration_one(), 'migration_two': MIGRATION_SHA,
                       'captured_at': captured, 'clock': value['clock'], 'head': value['head'],
                       'dump_sha256': received['sha256'], 'dump_bytes': received['bytes']})


def _prune(transaction, chosen):
    """Owner-only transaction body, also exercised by a rolled-back real drill."""
    chosen = _clock(chosen)
    require_quiescent(transaction)
    meta = transaction.one('SELECT clock FROM accounts.meta WHERE singleton=1 FOR UPDATE')
    value = state(transaction, True)
    need(meta is not None and max(meta[0], value['clock']) <= chosen)
    # Equality is retained: an exact seven-day boundary remains recoverable.
    rows = _rows(transaction, 'SELECT sequence,erased_at FROM accounts.erasure_journal WHERE erased_at<%s ORDER BY sequence LIMIT 4097', (chosen - WINDOW,))
    if rows:
        need(rows[0][0] == value['floor'] + 1 and len(rows) <= value['retained_rows'])
        floor, floor_time = rows[-1]
        need(floor == value['floor'] + len(rows))
        transaction.raw('DELETE FROM accounts.erasure_journal WHERE sequence<=%s', (floor,)).close()
        transaction.raw('UPDATE accounts.erasure_state SET floor=%s,floor_time=%s,retained_rows=retained_rows-%s,clock=%s WHERE singleton=1', (floor, floor_time, len(rows), chosen)).close()
    else:
        transaction.raw('UPDATE accounts.erasure_state SET clock=%s WHERE singleton=1', (chosen,)).close()
    transaction.raw('UPDATE accounts.meta SET clock=%s WHERE singleton=1', (chosen,)).close()
    return {'pruned': len(rows), 'seven_day_window_seconds': WINDOW}


def prune(profile, now):
    with operator(profile, write=True) as transaction:
        return _prune(transaction, _clock(now))


def reconcile(profile, manifest, received, expected, raw, now, before_commit=None, _before_apply=None):
    chosen = compatible(manifest, received, expected, raw, now)
    need(profile['database'] == 'ait_erasure_restore' and profile['purpose'] == 'restored'
         and profile['generation'] == received['generation'])
    journal_sha = digest(raw)
    with operator(profile, write=True) as transaction:
        require_quiescent(transaction)
        transaction.raw('SELECT singleton FROM accounts.meta WHERE singleton=1 FOR UPDATE').close()
        transaction.raw('LOCK TABLE accounts.accounts IN ACCESS EXCLUSIVE MODE').close()
        value = state(transaction, True)
        need(value['generation'] == received['generation'] and value['clock'] <= chosen
             and value['restored_from_sha'] == manifest['dump_sha256'])
        if _before_apply is not None: _before_apply(transaction)
        oid = transaction.one('SELECT oid::bigint FROM pg_database WHERE datname=current_database()')[0]
        if value['reconciled_sha'] is not None:
            need(value['reconciled_sha'] == journal_sha)
            at = value['reconciled_at']
        else:
            # Owner-only DDL in this transaction; runtime cannot set a bypass flag.
            transaction.raw('SET LOCAL ROLE ait_account_owner').close()
            transaction.raw('ALTER TABLE accounts.accounts DISABLE TRIGGER account_erasure_record').close()
            data = c.encode(received['rows']).decode('ascii')
            identities = "SELECT account_id FROM jsonb_to_recordset(%s::jsonb) AS j(sequence bigint,account_id text,erased_at bigint) WHERE sequence>%s"
            transaction.raw('DELETE FROM accounts.accounts WHERE account_id IN (' + identities + ')', (data, manifest['head'])).close()
            transaction.raw('UPDATE accounts.audit SET account_id=NULL WHERE account_id IN (' + identities + ')', (data, manifest['head'])).close()
            transaction.raw('INSERT INTO accounts.cleanup(account_id,at) SELECT account_id,%s FROM (' + identities + ') AS erased ON CONFLICT(account_id) DO NOTHING', (chosen, data, manifest['head'])).close()
            transaction.raw('ALTER TABLE accounts.accounts ENABLE TRIGGER account_erasure_record').close()
            transaction.raw('DELETE FROM accounts.erasure_journal').close()
            transaction.raw('INSERT INTO accounts.erasure_journal SELECT sequence,account_id,erased_at FROM jsonb_to_recordset(%s::jsonb) AS j(sequence bigint,account_id text,erased_at bigint)', (data,)).close()
            live = transaction.one('SELECT count(*) FROM accounts.accounts')[0]
            need(live + len(received['rows']) <= MAX_ROWS)
            transaction.raw('UPDATE accounts.erasure_state SET clock=%s,head=%s,floor=%s,floor_time=%s,reserved_live=%s,retained_rows=%s,reconciled_sha=%s,reconciled_at=%s WHERE singleton=1',
                            (chosen, received['head'], received['floor'], received['floor_time'], live, len(received['rows']), journal_sha, chosen)).close()
            transaction.raw('UPDATE accounts.meta SET clock=%s WHERE singleton=1', (chosen,)).close()
            transaction.raw('DELETE FROM accounts.history WHERE created_at<=%s', (chosen - c.RETENTION,)).close()
            transaction.raw('DELETE FROM accounts.sessions WHERE expires_at<=%s OR seen_at<=%s', (chosen, chosen - 3600)).close()
            at = chosen
        # The unchanged domain reserves capacity for BOTH live accounts and
        # pending entitlement removals. Keep every pending action on refusal.
        counts = transaction.one('SELECT (SELECT count(*) FROM accounts.accounts),(SELECT count(*) FROM accounts.cleanup)')
        need(counts is not None and len(counts) == 2 and all(type(x) is int and x >= 0 for x in counts))
        c.need(sum(counts) <= MAX_ACCOUNTS, 'recovery_capacity_unavailable', 503)
        if before_commit is not None: before_commit()
        # Only the real operator/runtime have the narrow control-file grant;
        # do not expand the NOLOGIN schemaowner's permissions to mint receipts.
        transaction.raw('RESET ROLE').close()
        receipt = {'format': 'account-erasure-serving-receipt/v1', 'database': profile['database'],
                   'database_oid': oid, 'generation': value['generation'], 'migration_one': _migration_one(),
                   'migration_two': MIGRATION_SHA, 'system_identity_sha256': system_identity(transaction), 'journal_sha256': journal_sha,
                   'backup_sha256': manifest['dump_sha256'], 'head': received['head'], 'reconciled_at': at}
    # Only return after acknowledged COMMIT/close. Caller writes private receipt.
    return receipt
