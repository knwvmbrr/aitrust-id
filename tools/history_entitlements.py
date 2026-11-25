"""Bounded operator grants for history; no payment, account or detector authority."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import secrets
import stat
import uuid

from tools.blind_review_io import PacketError, create, directory, member

ROOT = Path(__file__).resolve().parents[1]
FORMAT = 'account-history-entitlement/v1'
MAX_ACCOUNTS = 1024
MAX_EVENTS = 8192
MAX_BYTES = 2_000_000
MAX_LEASE = 31 * 86400
MAX_TIME = 253402300799


class EntitlementError(ValueError):
    """Fixed private-store diagnostics, without account or filesystem values."""


class EntitlementUncertain(EntitlementError):
    """Replacement occurred but its durable completion could not be established."""


class EntitlementInterrupted(KeyboardInterrupt):
    """Cancellation propagates; the attempted update may have committed."""
    update_may_have_committed = True


class EntitlementExit(SystemExit):
    """Preserve requested process exit and disclose possible update completion."""
    update_may_have_committed = True


def need(value):
    if not value:
        raise EntitlementError('History access operation unavailable.')


def identifier(value):
    need(type(value) is str)
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        raise EntitlementError('History access operation unavailable.') from None
    need(parsed.version == 4 and str(parsed) == value)
    return value


def moment(value):
    need(type(value) is int and 0 < value <= MAX_TIME)
    return value


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def pairs(values):
    result = {}
    for key, value in values:
        need(key not in result)
        result[key] = value
    return result


def validate(state):
    need(type(state) is dict and set(state) == {'version', 'last_now', 'deletions', 'accounts', 'events'})
    need(type(state['version']) is int and state['version'] == 1)
    need(type(state['last_now']) is int and 0 <= state['last_now'] <= MAX_TIME)
    need(type(state['deletions']) is int and 0 <= state['deletions'] <= MAX_TIME)
    need(type(state['accounts']) is dict and len(state['accounts']) <= MAX_ACCOUNTS)
    need(type(state['events']) is list and len(state['events']) <= MAX_EVENTS)
    for account, row in state['accounts'].items():
        identifier(account)
        need(type(row) is dict and set(row) == {'revision', 'valid_until'})
        need(type(row['revision']) is int and 0 < row['revision'] <= MAX_EVENTS)
        if row['valid_until'] is not None:
            moment(row['valid_until'])
    expected, seen, previous_time = {}, set(), 0
    for event in state['events']:
        need(type(event) is dict and set(event) == {'id', 'account_id', 'action', 'until', 'at'})
        key, account = identifier(event['id']), identifier(event['account_id'])
        need(key not in seen); seen.add(key)
        at = moment(event['at']); need(previous_time <= at <= state['last_now']); previous_time = at
        need(event['action'] in ('grant', 'revoke'))
        if event['action'] == 'grant':
            until = moment(event['until']); need(at < until <= min(MAX_TIME, at + MAX_LEASE))
        else:
            need(event['until'] is None and account in expected)
        revision = expected.get(account, {}).get('revision', 0) + 1
        expected[account] = {'revision': revision, 'valid_until': event['until']}
    need(expected == state['accounts'])
    # Every outstanding grant keeps one emergency revocation event in reserve.
    need(len(state['events']) + sum(row['valid_until'] is not None for row in expected.values()) <= MAX_EVENTS)
    need(len(encoded(state)) <= MAX_BYTES)
    return state


def result(state, account_id, now):
    row = state['accounts'].get(account_id)
    until = row['valid_until'] if row else None
    return {'format': FORMAT, 'account_id': account_id,
            'state': 'ACTIVE' if until is not None and now < until else 'INACTIVE',
            'valid_until': until, 'revision': row['revision'] if row else 0}


def initialize(path):
    state = {'version': 1, 'last_now': 0, 'deletions': 0, 'accounts': {}, 'events': []}
    try:
        create(path, ROOT, {'access.lock': b'', 'grants.json': encoded(state)})
    except (OSError, PacketError):
        raise EntitlementError('History access initialization unavailable.') from None
    return HistoryEntitlements(path)


class HistoryEntitlements:
    def __init__(self, path, *, clock=None):
        need(clock is None or callable(clock))
        self.path = Path(path).expanduser().absolute()
        self.clock = clock

    def _private(self, fd):
        held, named = os.fstat(fd), self.path.stat(follow_symlinks=False)
        for info in (held, named):
            need(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077)
        need((held.st_dev, held.st_ino) == (named.st_dev, named.st_ino))

    def _current(self, fd, original):
        self._private(fd)
        info = os.stat('grants.json', dir_fd=fd, follow_symlinks=False)
        need((info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns) == original)

    def _replace(self, fd, raw, original):
        name = '.grant-' + secrets.token_hex(16)
        output, identity, attempted = None, None, False
        try:
            output = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
            info = os.fstat(output); identity = (info.st_dev, info.st_ino)
            with os.fdopen(output, 'wb') as stream:
                output = None
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            self._current(fd, original)
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            need((info.st_dev, info.st_ino) == identity)
            # An interrupted system call may have replaced the file even if it
            # never returned to Python. Mark possible completion before calling.
            attempted = True
            os.replace(name, 'grants.json', src_dir_fd=fd, dst_dir_fd=fd)
            os.fsync(fd)
            self._private(fd)
            need(member(fd, 'grants.json', MAX_BYTES) == raw)
            self._private(fd)
        except BaseException as error:
            if attempted:
                if isinstance(error, KeyboardInterrupt):
                    raise EntitlementInterrupted('History access update may have committed.') from None
                if isinstance(error, SystemExit):
                    raise EntitlementExit(error.code) from None
                raise EntitlementUncertain('History access update durability is uncertain.') from None
            raise
        finally:
            if output is not None:
                os.close(output)
            if identity is not None:
                try:
                    info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                    if (info.st_dev, info.st_ino) == identity:
                        os.unlink(name, dir_fd=fd)
                except FileNotFoundError:
                    pass

    @contextmanager
    def _transaction(self, now):
        moment(now)
        try:
            with directory(self.path, ROOT) as fd:
                seen = set()
                with os.scandir(fd) as entries:
                    for entry in entries:
                        need(entry.name in {'access.lock', 'grants.json'} and len(seen) < 2)
                        seen.add(entry.name)
                need(seen == {'access.lock', 'grants.json'})
                lock = os.open('access.lock', os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                try:
                    info = os.fstat(lock)
                    need(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                         and not info.st_mode & 0o077 and info.st_nlink == 1 and info.st_size == 0)
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    raw = member(fd, 'grants.json', MAX_BYTES)
                    info = os.stat('grants.json', dir_fd=fd, follow_symlinks=False)
                    original = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
                    need(member(fd, 'grants.json', MAX_BYTES) == raw)
                    state = validate(json.loads(raw, object_pairs_hook=pairs))
                    try:
                        selected = moment(self.clock()) if self.clock is not None else now
                    except Exception:
                        raise EntitlementError('History access clock unavailable.') from None
                    need(selected >= state['last_now']); state['last_now'] = selected
                    yield state
                    updated = encoded(validate(state)); self._current(fd, original)
                    if updated != raw:
                        self._replace(fd, updated, original)
                finally:
                    os.close(lock)
        except EntitlementError:
            raise
        except (OSError, PacketError, ValueError, TypeError, KeyError, RecursionError, OverflowError):
            raise EntitlementError('History access operation unavailable.') from None

    def assess(self, account_id, now):
        identifier(account_id); moment(now)
        try:
            with self._transaction(now) as state:
                value = result(state, account_id, state['last_now'])
            return value
        except EntitlementError:
            return {'format': FORMAT, 'account_id': account_id, 'state': 'UNAVAILABLE',
                    'valid_until': None, 'revision': 0}

    def _apply(self, account_id, event_id, action, until, now):
        identifier(account_id); identifier(event_id); moment(now)
        if until is not None:
            moment(until)
        with self._transaction(now) as state:
            now = state['last_now']
            previous = next((e for e in state['events'] if e['id'] == event_id), None)
            if previous is not None:
                need((previous['account_id'], previous['action'], previous['until']) == (account_id, action, until))
            else:
                if action == 'grant':
                    need(now < until <= min(MAX_TIME, now + MAX_LEASE))
                    need(account_id in state['accounts'] or len(state['accounts']) < MAX_ACCOUNTS)
                else:
                    need(account_id in state['accounts'])
                revision = state['accounts'].get(account_id, {}).get('revision', 0) + 1
                state['events'].append({'id': event_id, 'account_id': account_id, 'action': action, 'until': until, 'at': now})
                state['accounts'][account_id] = {'revision': revision, 'valid_until': until}
                validate(state)
            value = result(state, account_id, now)
        return value

    def grant(self, account_id, event_id, valid_until, now):
        """Trusted local operator action, never proof that payment occurred."""
        return self._apply(account_id, event_id, 'grant', valid_until, now)

    def revoke(self, account_id, event_id, now):
        return self._apply(account_id, event_id, 'revoke', None, now)

    def forget(self, account_id, now):
        identifier(account_id)
        with self._transaction(now) as state:
            existed = account_id in state['accounts']
            state['accounts'].pop(account_id, None)
            state['events'] = [e for e in state['events'] if e['account_id'] != account_id]
            state['deletions'] += int(existed)
        return {'removed': existed, 'payment_processed': False}
