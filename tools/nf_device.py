"""Explicit local claim/passage observations; never an NF or factual verdict."""
import hashlib
import json
from pathlib import Path
from protocol import corpus
from protocol.normalization import normalize_nfc, NORMALIZATION_ID

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'nf-selected-reference-device/1.0.0'
COMMON = ('tools/nf_device.py', 'protocol/corpus.py', 'protocol/normalization.py',
          'protocol/unicode15-data.json')
OPTIONAL = {'literal': (), 'cosine': ('protocol/corpus_support.py',)}
METHODS = {'literal': 'corpus-query-case-sensitive-nonoverlapping/v1',
           'cosine': 'corpus-support-ascii-cosine/1.0.0'}
MAX_RECORD_BYTES = 262144


def need(value):
    if not value:
        raise ValueError('Selected reference observation unavailable.')


def subject(text):
    need(type(text) is str and bool(text.strip()) and '\0' not in text and len(text) <= 2000)
    raw = text.encode('utf-8', 'strict')
    normalized = normalize_nfc(text)
    need(len(raw) <= 8000 and 0 < len(normalized) <= 2000)
    return normalized, {'raw_sha256': corpus.sha(raw), 'raw_bytes': len(raw),
        'raw_characters': len(text), 'normalized_sha256': corpus.sha(normalized.encode()),
        'normalized_characters': len(normalized)}


def inspect_nf_device(claim, passage, check):
    need(type(check) is str and check in METHODS)
    normalized_claim, claim_identity = subject(claim)
    normalized_passage, passage_identity = subject(passage)
    # Preserve original source bytes as the corpus document identity; canonical
    # methods use their frozen NFC projection, never overwrite the raw identity.
    content = {'format': corpus.VERSION, 'documents': [{'id': 'selected',
        'sha256': corpus.sha(passage.encode()), 'text': passage}]}
    record = dict(content, manifest_sha256=corpus.sha(corpus.encoded(content)))
    record = corpus.parse(corpus.encoded(record))
    if check == 'literal':
        original = corpus.query(record, claim)
    else:
        from protocol import corpus_support
        original = corpus_support.observe(record, claim, threshold=.75, maximum=10)
    value = {'format': PROFILE, 'check': check, 'method': METHODS[check],
        'claim': claim_identity, 'passage': passage_identity,
        'normalization_id': NORMALIZATION_ID, 'offset_unit': 'NFC_unicode_codepoint',
        'selection': 'complete_explicit_claim_and_passage',
        'corpus_manifest_sha256': record['manifest_sha256'], 'original': original,
        'source_sha256': {p: corpus.sha((ROOT/p).read_bytes()) for p in (*COMMON, *OPTIONAL[check])},
        'tags': [], 'tag_asserted': False, 'truth_established': False,
        'source_support_established': False, 'independent_accuracy_evidence': False,
        'reference_freshness': 'unestablished', 'network_used': False}
    raw = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False)
    need(len(raw.encode()) <= MAX_RECORD_BYTES)
    return raw
