"""Bounded independent framing evidence. No MT assertion or collection."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys
import time

from protocol.normalization import normalize_nfc, NORMALIZATION_ID

ROOT = Path(__file__).resolve().parents[1]
QUOTATION = 'authority-quotation'
COMPONENTS = ('urgency', 'authority', 'choice', QUOTATION)
CONTEXT_PROFILE = 'independent-framing-context-evidence/v1'
PROFILE = 'independent-framing-evidence/v1'
MAX_BYTES = 32000
MAX_CHARACTERS = 8000
OUTPUT_LIMIT = 1_000_000
DEADLINE = 6
SUPERVISE = runpy.run_path(str(ROOT / 'scripts/worker_process.py'))['run_worker']
LIMITS = {'tag_asserted': False, 'intent_established': False,
          'independent_accuracy_evidence': False, 'independent_corroboration': False,
          'combined_confidence': None}
MESSAGES = {
    'urgency': ('A supported instruction and time phrase appear together. Urgency can be legitimate.',
                'No supported urgency pattern found. Other pressure may still be present.'),
    'authority': ('An authority phrase has no source marker in its sentence. A source may appear elsewhere.',
                  'No supported unsourced authority pattern found. Sources have not been verified.'),
    'choice': ('Your selected wording mentions two choices. Your extra passage is unverified context.',
               'No supported two-choice pattern matched your selections. Other framing may still be present.')}


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate field')
        result[key] = value
    return result


def parse(raw):
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Invalid number')))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def subject(text, language):
    if (language != 'en' or not isinstance(text, str) or not text.strip()
            or len(text) > MAX_CHARACTERS or '\0' in text):
        raise ValueError('Unsupported subject')
    raw = text.encode('utf-8', 'strict')
    normalized = normalize_nfc(text)
    if len(raw) > MAX_BYTES or len(normalized) > MAX_CHARACTERS:
        raise ValueError('Oversized subject')
    return normalized


def identity(kind):
    files = ['tools/mt_workflow.py', 'scripts/mt-evidence-worker.py', 'scripts/worker_process.py',
             'protocol/normalization.py', 'protocol/unicode15-data.json',
             'tools/language_observations.py', 'protocol/corpus.py']
    if kind == 'choice':
        files.extend(['tools/choice_framing.py', 'tools/blind_review_io.py'])
    if kind == QUOTATION:
        files.extend(['tools/mt_quotation_component.py', 'tools/authority_quotation.py',
                      'scripts/authority-quotation.py', 'tools/blind_review_io.py',
                      'scripts/check-mt-evidence.py'])
    return {name: sha((ROOT / name).read_bytes()) for name in files}


def unavailable(kind):
    return {'component': kind, 'state': 'UNAVAILABLE',
            'reason': 'No valid observation completed; the other selected checks are separate.'}


def valid_span(value, size):
    return (isinstance(value, list) and len(value) == 2
            and all(type(v) is int for v in value) and 0 <= value[0] < value[1] <= size)


def valid_hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def validate(row, kind, text, sources, *, replay_timeout=DEADLINE):
    if kind == QUOTATION:
        from tools.mt_quotation_component import validate_shape, expected_replay, canonical_json
        validate_shape(row, text, sources, LIMITS)
        request = json.dumps({'component': kind, 'subject': text,
                              'packet': {'replay_record': row}}, allow_nan=False, separators=(',', ':')).encode()
        if len(request) > 200000:
            raise ValueError('Quotation replay request exceeds its budget')
        child = SUPERVISE([sys.executable, '-I', '-S', '-B', str(ROOT / 'scripts/mt-evidence-worker.py')],
                          input=request, timeout=replay_timeout, output_limit=OUTPUT_LIMIT)
        if (child.returncode != 0 or identity(kind) != sources
                or canonical_json(parse(child.stdout)) != canonical_json(expected_replay(text, sources))):
            raise ValueError('Canonical quotation replay unavailable')
        return row

    keys = {'component', 'state', 'method', 'subject_sha256', 'normalization_id',
            'observations', 'sources', 'context_selection_performed', 'limitations'}
    if (not isinstance(row, dict) or set(row) != keys or row['component'] != kind
            or row['state'] not in ('OBSERVATIONS', 'NO_SUPPORTED_PATTERN')
            or row['subject_sha256'] != sha(text.encode()) or row['sources'] != sources
            or row['normalization_id'] != NORMALIZATION_ID
            or row['context_selection_performed'] is not (kind == 'choice')
            or json.dumps(row['limitations'], sort_keys=True) != json.dumps(LIMITS, sort_keys=True)):
        raise ValueError('Invalid worker contract')
    methods = {'urgency': 'english-context-observations/1.1.0',
               'authority': 'english-context-observations/1.0.0',
               'choice': 'caller-bound-choice-framing-observation/1.3.0'}
    if row['method'] != methods[kind]:
        raise ValueError('Unexpected method')
    rows = row['observations']
    if (not isinstance(rows, list) or len(rows) > 1024
            or (row['state'] == 'OBSERVATIONS') is not bool(rows)):
        raise ValueError('Invalid observation state')
    for item in rows:
        if (not isinstance(item, dict) or set(item) != {'subject_spans', 'context_span', 'reference', 'construction'}
                or not isinstance(item['subject_spans'], list) or not 1 <= len(item['subject_spans']) <= 4096
                or not all(valid_span(s, len(text)) for s in item['subject_spans'])
                or (item['context_span'] is not None and not valid_span(item['context_span'], len(text)))):
            raise ValueError('Invalid evidence locations')
        context = item['context_span']
        if context is None or any(not context[0] <= start < end <= context[1] for start, end in item['subject_spans']):
            raise ValueError('Evidence outside its context')
        if (kind == 'choice' and len(item['subject_spans']) != 4) or (kind == 'authority' and len(item['subject_spans']) != 1) or (kind == 'urgency' and len(item['subject_spans']) < 2):
            raise ValueError('Invalid observation structure')
        if kind == 'choice':
            ref = item['reference']
            if (item['construction'] not in ('either_or', 'only_or', 'neither_nor', 'between_and', 'not_only_but_also')
                    or not isinstance(ref, dict) or set(ref) != {'sha256', 'normalized_sha256', 'span'}
                    or not valid_hash(ref['sha256']) or not valid_hash(ref['normalized_sha256'])
                    or not valid_span(ref['span'], 200000) or ref['span'][1] - ref['span'][0] > 2000):
                raise ValueError('Invalid nominated reference')
        elif item['reference'] is not None or item['construction'] is not None:
            raise ValueError('Unrequested reference')
    return row


def run_component(kind, text, packet=None, *, deadline=DEADLINE):
    try:
        # A broken optional choice module is loaded only in its child. Its failure
        # cannot invalidate the urgency/authority result or invoke another tag.
        if kind == QUOTATION and (type(deadline) not in (int, float) or not 0 < deadline <= 60):
            raise ValueError('Invalid quotation deadline')
        started = time.monotonic()
        before = identity(kind)
        request = json.dumps({'component': kind, 'subject': text,
                              'packet': str(packet) if packet is not None else None}, allow_nan=False).encode()
        first_budget = deadline - (time.monotonic() - started) if kind == QUOTATION else deadline
        if first_budget <= 0:
            raise ValueError('Component deadline exhausted')
        child = SUPERVISE([sys.executable, '-I', '-S', '-B', str(ROOT / 'scripts/mt-evidence-worker.py')],
                          input=request, timeout=first_budget, output_limit=OUTPUT_LIMIT)
        if child.returncode != 0 or identity(kind) != before:
            raise ValueError('Changed or failed worker')
        remaining = deadline - (time.monotonic() - started) if kind == QUOTATION else deadline
        if remaining <= 0:
            raise ValueError('Component deadline exhausted')
        result = validate(parse(child.stdout), kind, text, before, replay_timeout=remaining)
        if kind == QUOTATION and identity(kind) != before:
            raise ValueError('Method changed during validation')
        return result
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, ImportError,
            UnicodeError, RecursionError, subprocess.SubprocessError):
        return unavailable(kind)


def check(text, components, language, packet=None):
    original = text
    text = subject(text, language)
    if (not isinstance(components, (list, tuple)) or not components
            or len(components) > len(COMPONENTS) or any(v not in COMPONENTS for v in components)
            or len(set(components)) != len(components) or (packet is not None and 'choice' not in components)):
        raise ValueError('Explicit supported component selection required')
    rows = {}
    with ThreadPoolExecutor(max_workers=len(components)) as pool:
        pending = {pool.submit(run_component, kind, original if kind == QUOTATION else text, packet if kind == 'choice' else None): kind
                   for kind in components}
        for future in as_completed(pending):
            kind = pending[future]
            try:
                rows[kind] = future.result()
            except Exception:
                rows[kind] = unavailable(kind)
    checks = [rows[kind] for kind in components]
    failed = sum(r['state'] == 'UNAVAILABLE' for r in checks)
    result = {'format': CONTEXT_PROFILE if QUOTATION in components else PROFILE, 'state': 'UNAVAILABLE' if failed == len(checks) else 'PARTIAL' if failed else 'COMPLETE',
            'language': language, 'subject_sha256': sha(text.encode()), 'subject_characters': len(text),
            'normalization_id': NORMALIZATION_ID, 'span_units': 'NFC_unicode_codepoints',
            'checks': checks, 'text_included': False, **LIMITS}
    if QUOTATION in components:
        result.update(raw_subject_sha256=sha(original.encode('utf-8')),
                      raw_subject_characters=len(original), raw_subject_bytes=len(original.encode('utf-8')))
    return result


def brief(row):
    if row['state'] == 'UNAVAILABLE':
        label = 'Authority quotation' if row['component'] == QUOTATION else row['component'].capitalize()
        return label + ': unavailable. Other selected checks are separate.'
    if row['component'] == QUOTATION:
        counts = row['counts']
        return ('Authority quotation: ' + str(counts['quoted_phrase_count']) + ' quoted phrase(s); '
                + str(counts['outside_supported_quotes_without_marker']) + ' outside phrase(s) without a local marker; '
                + str(counts['outside_supported_quotes_with_marker']) + ' outside phrase(s) with a marker. '
                'Placement does not establish endorsement; sources are not verified.')
    if row['component'] == 'choice' and row['state'] == 'OBSERVATIONS':
        additive=sum(item['construction']=='not_only_but_also' for item in row['observations'])
        if additive==len(row['observations']):
            return ('Choice: your selection additively mentions two items, not exclusive alternatives. '
                    'Your extra passage is unverified context.')
        if additive:
            return ('Choice: your selections include additive mentions and two-choice markers. '
                    'These do not establish exclusive alternatives or manipulation; your extra passage is unverified context.')
    return row['component'].capitalize() + ': ' + MESSAGES[row['component']][row['state'] != 'OBSERVATIONS']
