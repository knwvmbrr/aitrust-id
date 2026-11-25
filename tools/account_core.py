"""Account/history validation and bounded password work; no network or tag execution."""
import hashlib
import hmac
import json
import re
import secrets
import threading
import uuid

HISTORY_COUNT = 1000
HISTORY_BYTES = 5_000_000
RETENTION = 30 * 86400
RECORD_BYTES = 4096
KDF_ID = 'scrypt-n32768-r8-p3-dk32/v1'
TAGS = frozenset({'NF', 'FI', 'HP', 'MT', 'PS', 'IV', 'FA', 'PA', 'UNK', 'PII_REDACTED'})
ADAPTERS = {'web-check': 'Web check', 'extension-check': 'Extension check', 'native-share': 'Native Share', 'summary-import': 'Imported summary'}
EXPLANATIONS = {
    'FINDING': 'A supported signal was displayed; review its method and limits.',
    'NO_FINDING': 'No supported signal was displayed; this is not a safety clearance.',
    'UNAVAILABLE': 'No valid check completed.',
    'UNSUPPORTED': 'This check did not support the selected subject.',
}
_KDF_SLOTS = threading.BoundedSemaphore(2)


class AccountError(ValueError):
    """Only fixed codes cross the HTTP/log boundary."""
    def __init__(self, code='unavailable', status=503):
        super().__init__('Account service unavailable or refused.')
        self.code = code
        self.status = status


def need(condition, code='invalid_request', status=400):
    if not condition:
        raise AccountError(code, status)


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def parse(raw):
    need(type(raw) is bytes and 0 < len(raw) <= 16_384)
    depth, nodes, quoted, escaped = 0, 0, False, False
    for char in raw:
        if quoted:
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                quoted = False
        elif char == 34:
            quoted = True
        elif char in (91, 123):
            depth += 1
            nodes += 1
            need(depth <= 32 and nodes <= 4096)
        elif char in (93, 125):
            depth -= 1
            need(depth >= 0)
    need(depth == 0 and not quoted)
    def unique(items):
        result = {}
        for key, value in items:
            need(key not in result)
            result[key] = value
        return result
    try:
        value = json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=unique,
                           parse_constant=lambda _: need(False))
        need(type(value) is dict)
        return value
    except (UnicodeError, ValueError, RecursionError):
        raise AccountError('invalid_request', 400) from None


def timestamp(value):
    need(type(value) is int and 0 < value <= 2**53 - 1)
    return value


def identity(value):
    need(type(value) is str)
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        raise AccountError('invalid_request', 400) from None
    need(parsed.version == 4 and parsed.variant == uuid.RFC_4122 and str(parsed) == value)
    return value


def username(value):
    need(type(value) is str and re.fullmatch(r'[a-z][a-z0-9_-]{2,31}', value) is not None)
    return value


def password_bytes(value):
    need(type(value) is str and 15 <= len(value) <= 128)
    try:
        raw = value.encode('utf-8', 'strict')
    except UnicodeError:
        raise AccountError('invalid_request', 400) from None
    need(len(raw) <= 512 and '\0' not in value)
    return raw


def derive(password, salt):
    raw = password_bytes(password)
    need(type(salt) is bytes and len(salt) == 16, 'storage_unavailable', 503)
    need(_KDF_SLOTS.acquire(blocking=False), 'busy', 503)
    try:
        return hashlib.scrypt(raw, salt=salt, n=32768, r=8, p=3, dklen=32, maxmem=64_000_000)
    finally:
        _KDF_SLOTS.release()


def token():
    return secrets.token_urlsafe(32)


def token_hash(value):
    need(type(value) is str and re.fullmatch(r'[A-Za-z0-9_-]{43}', value) is not None, 'authentication_required', 401)
    return hashlib.sha256(b'aitrust-account-session/v1\0' + value.encode('ascii')).digest()


def csrf(value):
    token_hash(value)
    return hmac.new(value.encode('ascii'), b'aitrust-account-csrf/v1', hashlib.sha256).hexdigest()


def history_record(value, now):
    timestamp(now)
    need(type(value) is dict and set(value) == {'event_id', 'displayed_at', 'adapter', 'tag', 'state', 'method'})
    identity(value['event_id'])
    shown = timestamp(value['displayed_at'])
    need(now - RETENTION <= shown <= now + 300)
    adapter, tag, state = value['adapter'], value['tag'], value['state']
    need(type(adapter) is str and adapter in ADAPTERS and type(tag) is str and tag in TAGS
         and type(state) is str and state in EXPLANATIONS)
    method = value['method']
    if state in ('FINDING', 'NO_FINDING'):
        need(type(method) is dict and set(method) == {'name', 'revision', 'sha256'})
        for key, maximum in [('name', 80), ('revision', 80)]:
            need(type(method[key]) is str and 0 < len(method[key]) <= maximum
                 and re.fullmatch(r'[A-Za-z0-9_.:/+ -]+', method[key]) is not None)
        need(type(method['sha256']) is str and re.fullmatch('[a-f0-9]{64}', method['sha256']) is not None)
    else:
        need(method is None)
    result = {'format': 'personal-tag-history-record/v1', **value,
              'source_label': ADAPTERS[adapter], 'explanation': EXPLANATIONS[state],
              'display_time_authority': 'client_import_time_untrusted' if adapter == 'summary-import' else 'client_local_untrusted',
              'display_binding': 'client_summary_import' if adapter == 'summary-import' else 'client_declared',
              'received_at': now, 'expires_at': now + RETENTION,
              'input_included': False, 'research_consent': False, 'verified_assertion': False}
    need(len(encode(result)) <= RECORD_BYTES)
    return result


def assessment(callback, account_id, now):
    """Only the trusted server factory supplies this callback; no client grants."""
    unavailable = {'format': 'account-history-entitlement/v1', 'account_id': account_id,
                   'state': 'UNAVAILABLE', 'valid_until': None, 'revision': 0}
    try:
        value = callback(account_id, now)
        need(type(value) is dict and set(value) == set(unavailable)
             and value['format'] == unavailable['format'] and value['account_id'] == account_id
             and value['state'] in ('ACTIVE', 'INACTIVE', 'UNAVAILABLE')
             and type(value['revision']) is int and value['revision'] >= 0)
        end = value['valid_until']
        need(end is None or type(end) is int and 0 < end <= 2**53 - 1)
        if value['state'] == 'ACTIVE':
            need(end is not None and end > now)
        return {key: value[key] for key in unavailable}
    except Exception:
        return unavailable
