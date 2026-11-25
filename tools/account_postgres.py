"""Psycopg account transactions reusing the reviewed account domain, never payments."""
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import re
import stat
import time

from tools import account_core as c
from tools.account_store import AccountStore, IDLE_SECONDS
from tools.artifact_evidence_io import Capture

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FILE = 'deploy/accounts/001-account-schema.sql'
SCHEMA_SHA = '8bf9fe5a84f6cf13d5118a8fe8e18a27edeae3d2f980ceec0e34ca0500c5e159'
PROFILE = 'account-postgres-runtime/v1'
MAX_TRANSACTION = 8
MAX_RESULT_BYTES = 8_000_000
TABLES = ('accounts', 'audit', 'cleanup', 'history', 'meta', 'rates', 'sessions')
INDEXES = ('history_expiry', 'history_owner_sequence', 'rates_expiry', 'sessions_expiry', 'sessions_idle', 'sessions_owner')

# Every statement originates in the existing domain. Values always go separately
# to psycopg; no HTTP input is a SQL string or identifier. Both exact historical
# and payload-inclusive owner-history projections are supported during handoff.
QUERIES = frozenset('''DELETE FROM accounts WHERE account_id=?
DELETE FROM audit WHERE sequence IN(SELECT sequence FROM audit ORDER BY sequence LIMIT 32)
DELETE FROM cleanup WHERE account_id=?
DELETE FROM history WHERE account_id=?
DELETE FROM history WHERE account_id=? AND created_at<=?
DELETE FROM history WHERE account_id=? AND event_id=?
DELETE FROM sessions WHERE token_hash=?
INSERT INTO accounts VALUES(?,?,?,?,?,0)
INSERT INTO audit(account_id,operation,at) VALUES(?,?,?)
INSERT INTO cleanup VALUES(?,?)
INSERT INTO history(account_id,event_id,created_at,payload) VALUES(?,?,?,?)
INSERT INTO rates VALUES(?,?,1)
INSERT INTO sessions VALUES(?,?,?,?,?)
SELECT 1 FROM accounts WHERE username=?
SELECT 1 FROM cleanup WHERE account_id=?
SELECT account_id FROM cleanup ORDER BY at,account_id LIMIT 20
SELECT account_id,created_at,seen_at,expires_at FROM sessions WHERE token_hash=?
SELECT account_id,salt,password_hash FROM accounts WHERE username=?
SELECT count(*) FROM accounts
SELECT count(*) FROM audit
SELECT count(*) FROM cleanup
SELECT count(*) FROM rates
SELECT count(*) FROM sessions
SELECT count(*) FROM sessions WHERE account_id IS NULL
SELECT count(*) FROM sessions WHERE account_id=?
SELECT history_enabled FROM accounts WHERE account_id=?
SELECT payload FROM history WHERE account_id=? AND event_id=?
SELECT payload,created_at FROM history WHERE account_id=? AND event_id=?
SELECT salt,password_hash FROM accounts WHERE account_id=?
SELECT sequence,event_id,created_at,length(payload) AS bytes FROM history WHERE account_id=? ORDER BY sequence
SELECT sequence,event_id,created_at,length(payload) AS bytes,payload FROM history WHERE account_id=? ORDER BY sequence
SELECT until_at,count FROM rates WHERE rate_key=?
SELECT username,history_enabled FROM accounts WHERE account_id=?
UPDATE accounts SET history_enabled=0 WHERE account_id=?
UPDATE accounts SET history_enabled=1 WHERE account_id=?
UPDATE audit SET account_id=NULL WHERE account_id=?
UPDATE rates SET count=count+1 WHERE rate_key=?
UPDATE sessions SET seen_at=? WHERE token_hash=?'''.splitlines())


class CommitUncertain(c.AccountError):
    update_may_have_committed = True

    def __init__(self):
        super().__init__('commit_uncertain', 503)


class CommitInterrupted(KeyboardInterrupt):
    update_may_have_committed = True


class CommitExit(SystemExit):
    update_may_have_committed = True


def unavailable(value):
    c.need(value, 'storage_unavailable', 503)


def dialect(query, values):
    unavailable(type(query) is str and query in QUERIES and type(values) is tuple
                and len(values) <= 16 and query.count('?') == len(values)
                and all(v is None or type(v) in (str, int, bytes) for v in values))
    result = query.replace('?', '%s')
    if query.startswith('SELECT ') and ' LIMIT ' not in query:
        result += ' LIMIT 1001'
    return result


class Row:
    def __init__(self, names, values):
        self.names, self.values = names, values

    def __getitem__(self, key):
        return self.values[key if type(key) is int else self.names.index(key)]


class Cursor:
    def __init__(self, cursor, budget):
        self.cursor, self.budget = cursor, budget
        self.rowcount = cursor.rowcount
        self.names = tuple(x.name for x in cursor.description) if cursor.description else ()
        unavailable(len(self.names) <= 16 and len(set(self.names)) == len(self.names))

    def row(self, values):
        if values is None:
            return None
        unavailable(len(values) == len(self.names))
        values = tuple(v.tobytes() if isinstance(v, memoryview) else v for v in values)
        for value in values:
            unavailable(value is None or type(value) in (str, int, bytes))
            size = len(value.encode()) if type(value) is str else len(value) if type(value) is bytes else 8
            self.budget.result_bytes += size
            unavailable(self.budget.result_bytes <= MAX_RESULT_BYTES)
        return Row(self.names, values)

    def fetchone(self):
        try:
            return self.row(self.cursor.fetchone())
        finally:
            self.cursor.close()

    def fetchall(self):
        try:
            rows = self.cursor.fetchmany(1002)
            unavailable(len(rows) <= 1001)
            return [self.row(row) for row in rows]
        finally:
            self.cursor.close()


class Transaction:
    def __init__(self, connection, start=None):
        self.connection = connection
        self.start = self.last = time.monotonic() if start is None else start
        self.result_bytes = 0

    def tick(self):
        now = time.monotonic()
        unavailable(type(now) in (int, float) and type(self.start) in (int, float)
                    and math.isfinite(now) and math.isfinite(self.start)
                    and self.last <= now < self.start + MAX_TRANSACTION)
        self.last = now

    def raw(self, query, values=()):
        self.tick()
        remaining_ms = max(1, min(3000, int((self.start + MAX_TRANSACTION - self.last) * 1000)))
        self.connection.execute("SELECT set_config('statement_timeout',%s,false)", (str(remaining_ms),)).close()
        self.tick()
        cursor = self.connection.execute(query, values, prepare=False)
        try:
            self.tick()
        except BaseException:
            cursor.close()
            raise
        return cursor

    def one(self, query, values=()):
        cursor = self.raw(query, values)
        try:
            return cursor.fetchone()
        finally:
            cursor.close()

    def all(self, query):
        cursor = self.raw(query)
        try:
            rows = cursor.fetchmany(1002)
            unavailable(len(rows) <= 1001)
            return rows
        finally:
            cursor.close()

    def execute(self, query, values=()):
        translated = dialect(query, values)
        cursor = self.raw(translated, values)
        if cursor.description is None:
            count = cursor.rowcount
            cursor.close()
            class Count:
                rowcount = count
            return Count()
        return Cursor(cursor, self)


def load_profile(path):
    with Capture() as held:
        raw = held.read(path, 4096)
        value = c.parse(raw)
        keys = {'format', 'socket', 'port', 'database', 'role', 'server_os_user', 'cluster', 'schema_sha256'}
        if value.get('format') == PROFILE:
            unavailable(set(value) == keys)
            databases = ('ait_account_review', 'ait_account_restore')
        else:
            from tools import account_erasure as erasure
            unavailable(value.get('format') == erasure.PROFILE
                        and set(value) == keys | {'erasure_sha256', 'generation', 'purpose', 'restore_receipt', 'system_identity_sha256'}
                        and value['erasure_sha256'] == erasure.MIGRATION_SHA
                        and value['purpose'] in ('source', 'restored'))
            c.identity(value['generation'])
            erasure.sha(value['system_identity_sha256'])
            if value['purpose'] == 'source':
                unavailable(value['database'] == 'ait_erasure_review' and value['restore_receipt'] is None)
            else:
                unavailable(value['database'] == 'ait_erasure_restore'
                            and type(value['restore_receipt']) is str
                            and Path(value['restore_receipt']).is_absolute()
                            and '..' not in Path(value['restore_receipt']).parts)
            databases = erasure.DATABASES
        unavailable(value['schema_sha256'] == SCHEMA_SHA
                    and value['role'] == 'ait_account_runtime' and value['cluster'] == 'aitrust-account-review'
                    and value['database'] in databases
                    and value['server_os_user'] == 'debian' and value['port'] == 55449)
        socket = Path(value['socket'])
        unavailable(type(value['socket']) is str and socket.is_absolute() and '..' not in socket.parts)
        for part in (socket, *socket.parents):
            unavailable(not part.is_symlink())
        held.check()
    return value


def connect(profile):
    # Refuse environment overrides BEFORE any connection/address/service lookup.
    unavailable(not any(name.startswith('PG') for name in os.environ))
    # No import/install side effects on systems without the approved dependency.
    import psycopg
    info = os.stat('/run', follow_symlinks=False)
    unavailable(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022)
    passfile = '/run/aitrust-account-peer-no-password'
    try:
        os.stat(passfile, follow_symlinks=False)
    except FileNotFoundError:
        pass
    else:
        raise c.AccountError('storage_unavailable', 503)
    return psycopg.connect(host=profile['socket'], port=profile['port'], dbname=profile['database'],
                           user=profile['role'], requirepeer=profile['server_os_user'],
                           password='', passfile=passfile, sslmode='disable', gssencmode='disable',
                           connect_timeout=3, client_encoding='UTF8', application_name='aitrust-account-review',
                           options='-c search_path=pg_catalog,accounts -c statement_timeout=3000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=5000 -c client_min_messages=error -c standard_conforming_strings=on',
                           autocommit=True, prepare_threshold=None)


def verify_runtime(transaction, profile):
    connection = transaction
    row = connection.one("SELECT current_database(),current_user,session_user,current_setting('cluster_name'),current_setting('listen_addresses'),inet_server_addr(),current_setting('server_version_num')::integer,current_setting('fsync'),current_setting('synchronous_commit')")
    unavailable(row[:6] == (profile['database'], profile['role'], profile['role'], profile['cluster'], '', None)
                and 180000 <= row[6] < 190000 and row[7:] == ('on', 'on'))
    role = connection.one("SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls,rolinherit,(SELECT count(*) FROM pg_auth_members WHERE member=pg_roles.oid) FROM pg_roles WHERE rolname=current_user")
    unavailable(role == (False, False, False, False, False, False, 0))
    tables = connection.all("SELECT tablename FROM pg_tables WHERE schemaname='accounts' ORDER BY tablename")
    expected = TABLES
    if profile['format'] != PROFILE:
        expected = tuple(sorted((*TABLES, 'erasure_journal', 'erasure_state')))
    unavailable(tuple(x[0] for x in tables) == expected)
    indexes = connection.all("SELECT indexname FROM pg_indexes WHERE schemaname='accounts'")
    unavailable(set(INDEXES).issubset(x[0] for x in indexes))
    privilege = connection.one("SELECT has_schema_privilege(current_user,'accounts','CREATE'),has_database_privilege(current_user,current_database(),'CREATE'),has_database_privilege(current_user,current_database(),'TEMP'),has_table_privilege(current_user,'accounts.meta','INSERT'),has_table_privilege(current_user,'accounts.meta','DELETE'),has_column_privilege(current_user,'accounts.meta','schema_sha','UPDATE')")
    unavailable(privilege == (False,) * 6)
    if profile['format'] != PROFILE:
        from tools import account_erasure as erasure
        erasure.verify_runtime(transaction, profile)


class PostgresAccountStore(AccountStore):
    def __init__(self, profile):
        self.profile_path = Path(profile).absolute()
        self.profile = load_profile(self.profile_path)

    @contextmanager
    def _db(self, now):
        unavailable(callable(now) or type(now) is int)
        connection = None
        attempted = False
        entry = time.monotonic()
        try:
            unavailable(load_profile(self.profile_path) == self.profile)
            connection = connect(self.profile)
            transaction = Transaction(connection, entry)
            transaction.tick()
            verify_runtime(transaction, self.profile)
            transaction.raw('BEGIN').close()
            clock = transaction.one('SELECT clock,kdf,schema_sha FROM accounts.meta WHERE singleton=1 FOR UPDATE')
            try:
                chosen = c.timestamp(now() if callable(now) else now)
            except Exception:
                raise c.AccountError('clock_unavailable', 503) from None
            unavailable(clock is not None and type(clock[0]) is int and 0 <= clock[0] <= chosen
                        and clock[1:] == (c.KDF_ID, SCHEMA_SHA))
            transaction.raw('UPDATE accounts.meta SET clock=%s WHERE singleton=1', (chosen,)).close()
            transaction.raw('DELETE FROM accounts.sessions WHERE expires_at<=%s OR seen_at<=%s', (chosen, chosen - IDLE_SECONDS)).close()
            transaction.raw('DELETE FROM accounts.rates WHERE until_at<=%s', (chosen,)).close()
            transaction.raw('DELETE FROM accounts.history WHERE created_at<=%s', (chosen - c.RETENTION,)).close()
            yield transaction, chosen
            transaction.tick()
            unavailable(load_profile(self.profile_path) == self.profile)
            attempted = True
            transaction.raw('COMMIT').close()
            transaction.tick()
            # A close failure after COMMIT is explicitly not reported as rollback.
            connection.close(); connection = None
        except BaseException as error:
            if connection is not None:
                if not attempted:
                    try:
                        connection.execute('ROLLBACK')
                    except BaseException:
                        pass
                try:
                    connection.close()
                except BaseException:
                    pass
            if attempted:
                if isinstance(error, KeyboardInterrupt):
                    raise CommitInterrupted('Account update may have committed.') from None
                if isinstance(error, SystemExit):
                    raise CommitExit(error.code) from None
                raise CommitUncertain() from None
            if isinstance(error, (KeyboardInterrupt, SystemExit, c.AccountError)):
                raise
            raise c.AccountError('storage_unavailable', 503) from None
