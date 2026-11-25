"""Transactional SQLite development/review accounts. Operational PostgreSQL is separate."""
from contextlib import contextmanager
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import sqlite3
import stat
import uuid
from urllib.parse import quote

from tools.artifact_evidence_io import Capture, snapshot
from tools import account_core as c

MAX_DB = 512_000_000
MAX_ACCOUNTS, MAX_SESSIONS, MAX_BOOTSTRAP, MAX_RATES = 4096, 8192, 1024, 4096
SESSION_SECONDS, IDLE_SECONDS, BOOTSTRAP_SECONDS = 86400, 3600, 600
SCHEMA = {
    'meta': "CREATE TABLE meta(singleton INTEGER PRIMARY KEY CHECK(singleton=1),clock INTEGER NOT NULL,kdf TEXT NOT NULL CHECK(kdf='scrypt-n32768-r8-p3-dk32/v1')) STRICT",
    'accounts': 'CREATE TABLE accounts(account_id TEXT PRIMARY KEY,username TEXT UNIQUE NOT NULL,salt BLOB NOT NULL,password_hash BLOB NOT NULL,created_at INTEGER NOT NULL,history_enabled INTEGER NOT NULL CHECK(history_enabled IN(0,1))) STRICT',
    'sessions': 'CREATE TABLE sessions(token_hash BLOB PRIMARY KEY,account_id TEXT REFERENCES accounts(account_id) ON DELETE CASCADE,created_at INTEGER NOT NULL,seen_at INTEGER NOT NULL,expires_at INTEGER NOT NULL) STRICT',
    'history': 'CREATE TABLE history(sequence INTEGER PRIMARY KEY,account_id TEXT NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,event_id TEXT NOT NULL,created_at INTEGER NOT NULL,payload BLOB NOT NULL,UNIQUE(account_id,event_id)) STRICT',
    'rates': 'CREATE TABLE rates(rate_key TEXT PRIMARY KEY,until_at INTEGER NOT NULL,count INTEGER NOT NULL) STRICT',
    'audit': 'CREATE TABLE audit(sequence INTEGER PRIMARY KEY,account_id TEXT,operation TEXT NOT NULL,at INTEGER NOT NULL) STRICT',
    'cleanup': 'CREATE TABLE cleanup(account_id TEXT PRIMARY KEY,at INTEGER NOT NULL) STRICT',
}


def _location(directory):
    path = Path(directory).expanduser().absolute()
    forbidden = {'.git', '.ssh', '.gnupg', '.aws', '.config', '.password-store', 'library'}
    c.need(not any(part.lower() in forbidden or part == '..' for part in path.parts), 'storage_unavailable', 503)
    return path


def initialize(directory):
    """Exclusive explicit creation. A failed private initialization is retained, never overwritten."""
    path = _location(directory)
    with Capture() as held:
        parent, name = held.parent(path)
        os.mkdir(name, 0o700, dir_fd=parent)
        fd = held.directory(path)
        leaf = os.open('accounts.sqlite', os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        held.fds.append(leaf)
        db = sqlite3.connect(path / 'accounts.sqlite')
        try:
            db.execute('PRAGMA journal_mode=DELETE')
            db.execute('PRAGMA application_id=1095324737')
            db.execute('PRAGMA user_version=2')
            for sql in SCHEMA.values():
                db.execute(sql)
            db.execute('INSERT INTO meta VALUES(1,0,?)', (c.KDF_ID,))
            db.commit()
        finally:
            db.close()
        os.fsync(leaf)
        held.files.append((fd, 'accounts.sqlite', leaf, snapshot(os.fstat(leaf))))
        held.check()
    return AccountStore(path)


class AccountStore:
    def __init__(self, directory):
        self.directory = _location(directory)

    @contextmanager
    def _db(self, now):
        c.need(callable(now) or type(now) is int, 'clock_unavailable', 503)
        try:
            with Capture() as held:
                parent = held.directory(self.directory)
                with os.scandir(parent) as entries:
                    for index, item in enumerate(entries):
                        c.need(index < 2 and item.name in ('accounts.sqlite', 'accounts.sqlite-journal'), 'storage_unavailable', 503)
                        info = item.stat(follow_symlinks=False)
                        c.need(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                               and stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1
                               and info.st_size <= MAX_DB, 'storage_unavailable', 503)
                leaf = os.open('accounts.sqlite', os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
                held.fds.append(leaf)
                original = os.fstat(leaf)
                def stable():
                    info = os.stat('accounts.sqlite', dir_fd=parent, follow_symlinks=False)
                    c.need((info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_nlink)
                           == (original.st_dev, original.st_ino, original.st_mode, original.st_uid, 1)
                           and 0 < info.st_size <= MAX_DB, 'storage_unavailable', 503)
                    held.check()
                db = sqlite3.connect('file:' + quote(str(self.directory / 'accounts.sqlite'), safe='/') + '?mode=rw', uri=True, timeout=.2)
                try:
                    db.row_factory = sqlite3.Row
                    db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 16_384)
                    db.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 16_384)
                    db.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
                    db.execute('PRAGMA trusted_schema=OFF')
                    db.execute('PRAGMA foreign_keys=ON')
                    db.execute('PRAGMA temp_store=MEMORY')
                    db.execute('PRAGMA secure_delete=ON')
                    c.need(db.execute('PRAGMA journal_mode').fetchone()[0] == 'delete', 'storage_unavailable', 503)
                    pagesize = db.execute('PRAGMA page_size').fetchone()[0]
                    c.need(512 <= pagesize <= 65536 and pagesize & (pagesize - 1) == 0, 'storage_unavailable', 503)
                    c.need(db.execute('PRAGMA max_page_count=' + str(MAX_DB // pagesize)).fetchone()[0] == MAX_DB // pagesize, 'storage_unavailable', 503)
                    c.need(db.execute('PRAGMA application_id').fetchone()[0] == 1095324737
                           and db.execute('PRAGMA user_version').fetchone()[0] == 2, 'storage_unavailable', 503)
                    rows = db.execute("SELECT name,sql FROM sqlite_schema WHERE name NOT GLOB 'sqlite_*' ORDER BY name").fetchall()
                    c.need([(r[0], r[1]) for r in rows] == sorted(SCHEMA.items()), 'storage_unavailable', 503)
                    stable()
                    db.execute('BEGIN IMMEDIATE')
                    try:
                        now = c.timestamp(now() if callable(now) else now)
                    except Exception:
                        raise c.AccountError('clock_unavailable', 503) from None
                    clock = db.execute('SELECT clock,kdf FROM meta WHERE singleton=1').fetchone()
                    c.need(clock is not None and type(clock[0]) is int and 0 <= clock[0] <= now, 'clock_unavailable', 503)
                    c.need(clock[1] == c.KDF_ID, 'storage_unavailable', 503)
                    db.execute('UPDATE meta SET clock=? WHERE singleton=1', (now,))
                    db.execute('DELETE FROM sessions WHERE expires_at<=? OR seen_at<=?', (now, now - IDLE_SECONDS))
                    db.execute('DELETE FROM rates WHERE until_at<=?', (now,))
                    db.execute('DELETE FROM history WHERE created_at<=?', (now - c.RETENTION,))
                    yield db, now
                    stable()
                    db.commit()
                    stable()
                except BaseException:
                    db.rollback()
                    raise
                finally:
                    db.close()
        except c.AccountError:
            raise
        except (OSError, ValueError, sqlite3.Error):
            raise c.AccountError('storage_unavailable', 503) from None

    def _rate(self, db, label, value, now, maximum, seconds):
        c.need(type(value) is str and 0 < len(value) <= 128)
        key = hashlib.sha256((label + '\0' + value).encode()).hexdigest()
        row = db.execute('SELECT until_at,count FROM rates WHERE rate_key=?', (key,)).fetchone()
        if row is None:
            c.need(db.execute('SELECT count(*) FROM rates').fetchone()[0] < MAX_RATES, 'busy', 503)
            db.execute('INSERT INTO rates VALUES(?,?,1)', (key, now + seconds))
        else:
            c.need(type(row[0]) is int and now < row[0] <= now + seconds and type(row[1]) is int and 0 < row[1] <= maximum, 'storage_unavailable', 503)
            c.need(row[1] < maximum, 'rate_limited', 429)
            db.execute('UPDATE rates SET count=count+1 WHERE rate_key=?', (key,))

    def _audit(self, db, account_id, operation, now):
        if db.execute('SELECT count(*) FROM audit').fetchone()[0] >= 8192:
            db.execute('DELETE FROM audit WHERE sequence IN(SELECT sequence FROM audit ORDER BY sequence LIMIT 32)')
        db.execute('INSERT INTO audit(account_id,operation,at) VALUES(?,?,?)', (account_id, operation, now))

    def _session(self, db, value, now, authenticated=True):
        digest = c.token_hash(value)
        row = db.execute('SELECT account_id,created_at,seen_at,expires_at FROM sessions WHERE token_hash=?', (digest,)).fetchone()
        c.need(row is not None, 'authentication_required', 401)
        c.need(all(type(row[k]) is int for k in ('created_at', 'seen_at', 'expires_at'))
               and 0 < row['created_at'] <= row['seen_at'] <= now < row['expires_at']
               and now - row['seen_at'] < IDLE_SECONDS
               and row['expires_at'] == row['created_at'] + (BOOTSTRAP_SECONDS if row['account_id'] is None else SESSION_SECONDS), 'authentication_required', 401)
        if authenticated:
            c.need(row['account_id'] is not None, 'authentication_required', 401)
        if row['account_id'] is not None:
            c.identity(row['account_id'])
        db.execute('UPDATE sessions SET seen_at=? WHERE token_hash=?', (now, digest))
        return row['account_id']

    def _new_session(self, db, account_id, now, previous=None):
        if previous is not None:
            db.execute('DELETE FROM sessions WHERE token_hash=?', (c.token_hash(previous),))
        c.need(db.execute('SELECT count(*) FROM sessions').fetchone()[0] < MAX_SESSIONS, 'busy', 503)
        if account_id is None:
            c.need(db.execute('SELECT count(*) FROM sessions WHERE account_id IS NULL').fetchone()[0] < MAX_BOOTSTRAP, 'busy', 503)
        else:
            c.need(db.execute('SELECT count(*) FROM sessions WHERE account_id=?', (account_id,)).fetchone()[0] < 8, 'session_limit', 429)
        value = c.token()
        db.execute('INSERT INTO sessions VALUES(?,?,?,?,?)', (c.token_hash(value), account_id, now, now,
                   now + (BOOTSTRAP_SECONDS if account_id is None else SESSION_SECONDS)))
        return value

    def _public(self, db, account_id, value):
        account, enabled = None, False
        if account_id is not None:
            row = db.execute('SELECT username,history_enabled FROM accounts WHERE account_id=?', (account_id,)).fetchone()
            c.need(row is not None and row['history_enabled'] in (0, 1), 'storage_unavailable', 503)
            account = {'id': c.identity(account_id), 'username': c.username(row['username'])}
            enabled = bool(row['history_enabled'])
        return {'format': 'account-session/v1', 'authenticated': account is not None, 'account': account,
                'csrf_token': c.csrf(value), 'history_enabled': enabled, 'recovery_available': False}

    def session(self, value, now, peer):
        with self._db(now) as (db, now):
            account_id = None
            if value is not None:
                try:
                    account_id = self._session(db, value, now, False)
                except c.AccountError as error:
                    if error.status != 401:
                        raise
                    value = None
            if value is None:
                self._rate(db, 'bootstrap', peer, now, 60, 600)
                value = self._new_session(db, None, now)
            public = self._public(db, account_id, value)
        return public, value

    def authenticate(self, value, now, authenticated=True):
        with self._db(now) as (db, now):
            return self._session(db, value, now, authenticated)

    def signup(self, username, password, previous, now, peer):
        name = c.username(username)
        c.password_bytes(password)
        refused = False
        with self._db(now) as (db, now):
            c.need(self._session(db, previous, now, False) is None, 'already_authenticated', 409)
            self._rate(db, 'signup', peer, now, 5, 3600)
            c.need(db.execute('SELECT count(*) FROM accounts').fetchone()[0]
                   + db.execute('SELECT count(*) FROM cleanup').fetchone()[0] < MAX_ACCOUNTS, 'busy', 503)
            salt = secrets.token_bytes(16)
            derived = c.derive(password, salt)
            if db.execute('SELECT 1 FROM accounts WHERE username=?', (name,)).fetchone():
                refused = True
                self._audit(db, None, 'signup_refused', now)
            else:
                account_id = str(uuid.uuid4())
                db.execute('INSERT INTO accounts VALUES(?,?,?,?,?,0)', (account_id, name, salt, derived, now))
                value = self._new_session(db, account_id, now, previous)
                public = self._public(db, account_id, value)
                self._audit(db, account_id, 'signup', now)
        c.need(not refused, 'account_unavailable', 409)
        return public, value

    def login(self, username, password, previous, now, peer):
        name = c.username(username)
        c.password_bytes(password)
        refused = False
        with self._db(now) as (db, now):
            self._session(db, previous, now, False)
            self._rate(db, 'login_peer', peer, now, 10, 600)
            self._rate(db, 'login_username', name, now, 10, 600)
            row = db.execute('SELECT account_id,salt,password_hash FROM accounts WHERE username=?', (name,)).fetchone()
            salt, expected = (bytes(range(16)), bytes(32)) if row is None else (row['salt'], row['password_hash'])
            c.need(type(salt) is bytes and len(salt) == 16 and type(expected) is bytes and len(expected) == 32, 'storage_unavailable', 503)
            valid = hmac.compare_digest(c.derive(password, salt), expected)
            if row is None or not valid:
                refused = True
                self._audit(db, None, 'login_refused', now)
            else:
                account_id = c.identity(row['account_id'])
                value = self._new_session(db, account_id, now, previous)
                public = self._public(db, account_id, value)
                self._audit(db, account_id, 'login', now)
        c.need(not refused, 'authentication_required', 401)
        return public, value

    def logout(self, value, now):
        with self._db(now) as (db, now):
            account_id = self._session(db, value, now, False)
            db.execute('DELETE FROM sessions WHERE token_hash=?', (c.token_hash(value),))
            self._audit(db, account_id, 'logout', now)
        return {'format': 'account-session/v1', 'authenticated': False, 'account': None,
                'csrf_token': None, 'history_enabled': False, 'recovery_available': False}

    def entitlements(self, value, now, callback):
        with self._db(now) as (db, now):
            account_id = self._session(db, value, now)
            result = c.assessment(callback, account_id, now)
        return result

    def _history(self, db, account_id, now):
        db.execute('DELETE FROM history WHERE account_id=? AND created_at<=?', (account_id, now - c.RETENTION))
        rows = db.execute('SELECT sequence,event_id,created_at,length(payload) AS bytes,payload FROM history WHERE account_id=? ORDER BY sequence', (account_id,)).fetchall()
        c.need(len(rows) <= c.HISTORY_COUNT and all(type(r['bytes']) is int and 0 < r['bytes'] <= c.RECORD_BYTES for r in rows)
               and all(type(r['created_at']) is int and now - c.RETENTION < r['created_at'] <= now for r in rows)
               and sum(r['bytes'] for r in rows) <= c.HISTORY_BYTES, 'storage_unavailable', 503)
        return rows

    def _record(self, raw, created):
        c.need(type(raw) is bytes and 0 < len(raw) <= c.RECORD_BYTES, 'storage_unavailable', 503)
        stored = c.parse(raw)
        try:
            original = {k: stored[k] for k in ('event_id', 'displayed_at', 'adapter', 'tag', 'state', 'method')}
            expected = c.history_record(original, created)
            c.need(c.encode(expected) == raw, 'storage_unavailable', 503)
            return expected
        except (KeyError, ValueError, TypeError):
            raise c.AccountError('storage_unavailable', 503) from None

    def history_list(self, value, now, *, after=None, limit=50, export=False, state=None):
        c.need(type(limit) is int and 1 <= limit <= 50)
        c.need(state is None or type(state) is str and state in c.EXPLANATIONS)
        c.need(not export or state is None and after is None)
        if after is not None:
            c.identity(after)
        with self._db(now) as (db, now):
            account_id = self._session(db, value, now)
            rows = self._history(db, account_id, now)
            parsed = {}
            for row in rows:
                item = self._record(row['payload'], row['created_at'])
                c.need(item['event_id'] == row['event_id'], 'storage_unavailable', 503)
                parsed[row['event_id']] = item
            matching = rows if state is None else [r for r in rows if parsed[r['event_id']]['state'] == state]
            cursor = 0
            if after is not None:
                selected = [r for r in matching if r['event_id'] == after]
                c.need(len(selected) == 1, 'not_found', 404)
                cursor = selected[0]['sequence']
            remaining = [r for r in matching if r['sequence'] > cursor]
            chosen = matching if export else remaining[:limit]
            items = [parsed[r['event_id']] for r in chosen]
            enabled = db.execute('SELECT history_enabled FROM accounts WHERE account_id=?', (account_id,)).fetchone()[0]
            result = {'format': 'personal-tag-history-export/v1' if export else 'personal-tag-history-page/v1',
                      'items': items, 'history_enabled': bool(enabled), 'retention_days': 30,
                      'total_entries': len(rows), 'matching_entries': len(matching),
                      'next': chosen[-1]['event_id'] if not export and len(remaining) > len(chosen) else None,
                      'research_consent': False, 'verified_assertions': False}
        return result

    def history_change(self, value, now, operation, callback, *, record=None, acknowledge=False):
        c.need(operation in ('enable', 'disable', 'append'))
        with self._db(now) as (db, now):
            account_id = self._session(db, value, now)
            rows = self._history(db, account_id, now)
            if operation != 'disable':
                entitlement = c.assessment(callback, account_id, now)
                c.need(entitlement['state'] == 'ACTIVE', 'history_access_inactive' if entitlement['state'] == 'INACTIVE' else 'history_access_unavailable', 403 if entitlement['state'] == 'INACTIVE' else 503)
            if operation == 'enable':
                c.need(acknowledge is True)
                db.execute('UPDATE accounts SET history_enabled=1 WHERE account_id=?', (account_id,))
                result = {'format': 'personal-tag-history-status/v1', 'history_enabled': True}
            elif operation == 'disable':
                db.execute('UPDATE accounts SET history_enabled=0 WHERE account_id=?', (account_id,))
                result = {'format': 'personal-tag-history-status/v1', 'history_enabled': False}
            else:
                c.need(db.execute('SELECT history_enabled FROM accounts WHERE account_id=?', (account_id,)).fetchone()[0] == 1, 'history_disabled', 403)
                proposed = c.history_record(record, now)
                previous = db.execute('SELECT payload,created_at FROM history WHERE account_id=? AND event_id=?', (account_id, proposed['event_id'])).fetchone()
                if previous is not None:
                    stored = self._record(previous['payload'], previous['created_at'])
                    c.need(all(stored[k] == record[k] for k in record), 'history_conflict', 409)
                    result = stored
                else:
                    raw = c.encode(proposed)
                    c.need(len(rows) < c.HISTORY_COUNT and sum(r['bytes'] for r in rows) + len(raw) <= c.HISTORY_BYTES, 'history_full', 409)
                    db.execute('INSERT INTO history(account_id,event_id,created_at,payload) VALUES(?,?,?,?)', (account_id, proposed['event_id'], now, raw))
                    result = proposed
            self._audit(db, account_id, 'history_' + operation, now)
        return result

    def history_delete(self, value, now, event_id=None):
        if event_id is not None:
            c.identity(event_id)
        with self._db(now) as (db, now):
            account_id = self._session(db, value, now)
            if event_id is None:
                db.execute('DELETE FROM history WHERE account_id=?', (account_id,))
                db.execute('UPDATE accounts SET history_enabled=0 WHERE account_id=?', (account_id,))
            else:
                changed = db.execute('DELETE FROM history WHERE account_id=? AND event_id=?', (account_id, event_id)).rowcount
                c.need(changed == 1, 'not_found', 404)
            self._audit(db, account_id, 'history_delete', now)
        return {'format': 'personal-tag-history-deletion/v1', 'deleted': True, 'physical_erasure_claimed': False}

    def delete_account(self, value, password, now):
        c.password_bytes(password)
        refused = False
        with self._db(now) as (db, now):
            account_id = self._session(db, value, now)
            self._rate(db, 'account_reauthentication', account_id, now, 10, 600)
            row = db.execute('SELECT salt,password_hash FROM accounts WHERE account_id=?', (account_id,)).fetchone()
            c.need(row is not None and type(row['password_hash']) is bytes and len(row['password_hash']) == 32, 'storage_unavailable', 503)
            if not hmac.compare_digest(c.derive(password, row['salt']), row['password_hash']):
                refused = True
                self._audit(db, account_id, 'account_reauthentication_refused', now)
            else:
                db.execute('DELETE FROM accounts WHERE account_id=?', (account_id,))
                db.execute('UPDATE audit SET account_id=NULL WHERE account_id=?', (account_id,))
                db.execute('INSERT INTO cleanup VALUES(?,?)', (account_id, now))
                self._audit(db, None, 'account_deleted', now)
        c.need(not refused, 'authentication_required', 401)
        return {'format': 'account-deletion/v1', 'deleted': True, 'physical_erasure_claimed': False,
                'entitlement_cleanup': 'PENDING', '_cleanup_account_id': account_id}

    def finish_cleanup(self, account_id, callback, now):
        c.identity(account_id)
        clock = now
        with self._db(clock) as (db, now):
            row = db.execute('SELECT 1 FROM cleanup WHERE account_id=?', (account_id,)).fetchone()
            if row is None:
                return True
        if callback is None:
            return False
        try:
            result = callback(account_id, now)
            c.need(type(result) is dict and set(result) == {'removed', 'payment_processed'}
                   and type(result['removed']) is bool and result['payment_processed'] is False)
        except Exception:
            return False
        with self._db(clock) as (db, now):
            db.execute('DELETE FROM cleanup WHERE account_id=?', (account_id,))
        return True

    def retry_cleanup(self, callback, now):
        clock = now
        with self._db(clock) as (db, now):
            rows = db.execute('SELECT account_id FROM cleanup ORDER BY at,account_id LIMIT 20').fetchall()
        completed = sum(self.finish_cleanup(row['account_id'], callback, clock) for row in rows)
        return {'examined': len(rows), 'completed': completed, 'all_pending_examined': False}

    def maintenance(self, now):
        with self._db(now):
            pass  # The same transaction performs global logical expiry, not an owner-only filter.
        return {'format': 'account-maintenance/v1', 'logical_expiry_checked': True}
