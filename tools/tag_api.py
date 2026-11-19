"""Free local tag API. Submitted text is data, never a program or an upload."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import importlib.util
import threading

ROOT = Path(__file__).resolve().parents[1]
MAX_CHARS = 20_000
MAX_BYTES = 80_000
CODES = ('PS', 'PII_REDACTED')
_slots = threading.BoundedSemaphore(2)
_spec = importlib.util.spec_from_file_location('ai_trust_independent_batch', ROOT / 'scripts/check-tags.py')
_batch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_batch)
PRIVACY_ENV_FILE = _batch.DEFAULT_ENV

MESSAGES = {
    ('PS', 'FINDING'): 'Supported command-risk pattern found. Review the command before using it.',
    ('PS', 'NO_FINDING'): 'No supported command pattern found. This is not a safety clearance.',
    ('PII_REDACTED', 'FINDING'): 'Possible personal details were masked during the check. Your original text is unchanged.',
    ('PII_REDACTED', 'NO_FINDING'): 'No supported personal details were masked. Private details may still be present.',
}


def list_tags():
    """Discover implemented checks without probing a service or reading user text."""
    return {'format': 'ai-trust-id-tool-catalog/v1', 'tags': [
        {'code': 'PS', 'job': 'Find supported download-and-run or encoded-code execution patterns in selected text.',
         'setup': 'local_python', 'status': 'development', 'independently_validated': False},
        {'code': 'PII_REDACTED', 'job': 'Report whether the configured local privacy service masked supported personal details.',
         'setup': 'authenticated_loopback_service', 'status': 'development', 'independently_validated': False},
    ], 'checking_requires_account': False, 'automated_research_submission': False}


def validate_request(arguments):
    if type(arguments) is not dict or not {'text'} <= arguments.keys() <= {'text', 'tags'}:
        raise ValueError('Unsupported tag-check request.')
    text = arguments['text']
    tags = arguments.get('tags', ['PS'])
    if (type(text) is not str or not text.strip() or len(text) > MAX_CHARS
            or type(tags) is not list or not 1 <= len(tags) <= len(CODES)
            or any(type(code) is not str or code not in CODES for code in tags)
            or len(set(tags)) != len(tags)):
        raise ValueError('Unsupported tag-check request.')
    try:
        if len(text.encode('utf-8', 'strict')) > MAX_BYTES:
            raise ValueError('Unsupported tag-check request.')
    except UnicodeError:
        raise ValueError('Unsupported tag-check request.') from None
    return text, tags


def unavailable(code):
    return {'code': code, 'state': 'UNAVAILABLE', 'message': 'No valid check completed. Other tag checks remain separate.',
            'method': [], 'evidence': []}


def summarize(code, row, text):
    """Project validated records onto a fixed non-content result contract."""
    if type(row) is not dict or row.get('code') != code or row.get('state') not in ('FINDING', 'NO_FINDING', 'UNAVAILABLE'):
        raise ValueError('Unsupported checker result.')
    if row['state'] == 'UNAVAILABLE':
        return unavailable(code)
    record = row['record']
    if code == 'PS':
        record = _batch.load_checker('check-ps.py').validate(record, text)
        signals = [signal for candidate in record['candidates'] for signal in candidate['signals']]
        evidence = [{'signal_id': signal['id'], 'count': len(signal['spans'])} for signal in signals]
        method = record['models']
    else:
        record = _batch.load_checker('aitrust.py').validate_result(record, privacy=True)
        signals = [signal for tag in record['tags'] for signal in tag['signals']]
        evidence = [{'signal_id': 'presidio.entity.v1', 'count': signal['detail']['count']} for signal in signals]
        method = record['evaluator']['models']
    # Multiple occurrences are separate source signals, but the brief API
    # contract has one row per supported signal ID. Preserve every count.
    totals = {}
    for item in evidence:
        totals[item['signal_id']] = totals.get(item['signal_id'], 0) + item['count']
    evidence = [{'signal_id': key, 'count': value} for key, value in sorted(totals.items())]
    expected = 'FINDING' if evidence else 'NO_FINDING'
    if row['state'] != expected:
        raise ValueError('Checker state contradicts evidence.')
    return {'code': code, 'state': expected, 'message': MESSAGES[(code, expected)],
            'method': method, 'evidence': evidence}


def one_check(code, text):
    try:
        return summarize(code, _batch.run_tag(code, text, PRIVACY_ENV_FILE), text)
    except Exception:
        return unavailable(code)


def result(checks, reason=None):
    unavailable_count = sum(row['state'] == 'UNAVAILABLE' for row in checks)
    return {'format': 'ai-trust-id-tool-result/v1',
            'state': 'UNAVAILABLE' if unavailable_count == len(checks) else 'PARTIAL' if unavailable_count else 'COMPLETE',
            'checks': checks, 'reason': reason, 'independently_validated': False,
            'safety_clearance': False, 'text_included': False, 'subject_identity_included': False,
            'research_submitted': False}


def check_text(text, tags=None):
    """Check selected text with separate tag workers; never execute its contents."""
    text, tags = validate_request({'text': text, 'tags': ['PS'] if tags is None else tags})
    if not _slots.acquire(blocking=False):
        return result([unavailable(code) for code in tags], 'busy')
    try:
        with ThreadPoolExecutor(max_workers=len(tags)) as pool:
            futures = [pool.submit(one_check, code, text) for code in tags]
            return result([future.result() for future in futures])
    finally:
        _slots.release()
