"""Offline dependency checks; declared review windows are neither freshness nor truth."""
from datetime import datetime, timezone
import json
import math
import re
from protocol import corpus, corpus_support
from protocol.normalization import normalize_nfc

PROFILE = 'reference-revision-review/1.0.0'
POLICY = 'declared-reference-review-windows/1.0.0'
MAX_POLICY_BYTES = 20_000
MAX_OBSERVATION_BYTES = 30_000
UTC = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z')
HASH = re.compile(r'[0-9a-f]{64}')


class RevisionError(ValueError):
    """Diagnostics must contain no caller content or private paths."""


def require(condition):
    if not condition:
        raise RevisionError('Private reference input or evidence contract refused.')


def timestamp(value):
    require(type(value) is str and UTC.fullmatch(value) is not None)
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    except ValueError:
        raise RevisionError('Private reference input or evidence contract refused.') from None


def finite_float(value):
    parsed = float(value)
    require(math.isfinite(parsed))
    return parsed


def decode(raw, limit):
    require(type(raw) is bytes and 0 < len(raw) <= limit)
    try:
        return json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=corpus.unique_pairs,
            parse_float=finite_float, parse_constant=lambda _: require(False))
    except (ValueError, UnicodeError, RecursionError):
        raise RevisionError('Private reference input or evidence contract refused.') from None


def windows(policy, current, at):
    """Only the declared window is measured; its authority is not authenticated."""
    if policy is None:
        return {}
    require(type(policy) is dict and set(policy) == {'profile', 'manifest_sha256', 'documents'})
    require(policy['profile'] == POLICY and policy['manifest_sha256'] == current['manifest_sha256'])
    require(type(policy['documents']) is list and len(policy['documents']) <= corpus.MAX_DOCUMENTS)
    documents = {d['id']: d for d in current['documents']}
    result = {}
    for row in policy['documents']:
        require(type(row) is dict and set(row) == {'document_id', 'document_sha256', 'opens_at', 'expires_at'})
        identity = row['document_id']
        require(corpus.valid_id(identity) and identity in documents and identity not in result)
        require(type(row['document_sha256']) is str and HASH.fullmatch(row['document_sha256']) is not None
                and row['document_sha256'] == documents[identity]['sha256'])
        start, end = timestamp(row['opens_at']), timestamp(row['expires_at'])
        require(start < end)
        result[identity] = 'not_yet_open' if at < start else 'elapsed' if at >= end else 'within_declared_window'
    return result


def review(previous, current, subject, observation, policy, evaluated_at):
    """Validate captured evidence before describing exact dependency changes."""
    at = timestamp(evaluated_at)
    try:
        previous = corpus.parse(corpus.encoded(previous))
        current = corpus.parse(corpus.encoded(current))
        require(type(observation) is dict)
        require(type(observation.get('threshold')) in (float, int)
                and type(observation.get('maximum_findings')) is int)
        expected = corpus_support.observe(previous, subject, observation['threshold'], observation['maximum_findings'])
        # Canonical bytes distinguish bool/int, type substitutions and unknown fields.
        require(corpus.encoded(observation) == corpus.encoded(expected))
        declared = windows(policy, current, at)
        present = {d['id']: d for d in current['documents']}
        rows = []
        for index, finding in enumerate(expected['findings']):
            reference = finding['reference']
            document = present.get(reference['document_id'])
            if document is None:
                state = 'document_removed'
            elif document['sha256'] != reference['document_sha256']:
                state = 'document_changed'
            else:
                normalized = normalize_nfc(document['text'])
                left, right = reference['source_span']
                require(corpus.sha(normalized.encode()) == reference['normalized_source_sha256']
                        and 0 <= left < right <= len(normalized))
                state = 'pair_context_current'
            rows.append({'finding_index': index, 'claim_span': list(finding['spans'][0]),
                'reference': dict(reference), 'dependency_state': state,
                'declared_review_window': declared.get(reference['document_id'], 'unknown'),
                'pair_context_current': state == 'pair_context_current'})
        retrieval_current = previous['manifest_sha256'] == current['manifest_sha256']
        return {'profile': PROFILE, 'evaluated_at': evaluated_at,
            'previous_manifest_sha256': previous['manifest_sha256'], 'current_manifest_sha256': current['manifest_sha256'],
            'subject_sha256': expected['subject_sha256'], 'method': expected['method'], 'method_sha256': expected['method_sha256'],
            'span_units': 'NFC_unicode_codepoints', 'findings': rows,
            'global_retrieval_current': retrieval_current, 'global_retrieval_must_rerun': not retrieval_current,
            'source_freshness_authenticated': False, 'window_authority': 'caller_declared_not_authenticated',
            'truth_established': False, 'tag_asserted': False, 'release_approved': False,
            'independent_accuracy_evidence': False, 'network_used': False,
            'meaning': 'Unchanged pair context does not establish current ranking, source freshness, truth or an NF/FI tag.'}
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError, OverflowError):
        raise RevisionError('Private reference input or evidence contract refused.') from None


def summary(result, saved=False):
    rows = result['findings']
    return {'profile': PROFILE, 'state': 'dependencies_reviewed', 'findings_reviewed': len(rows),
        'unchanged_pair_contexts': sum(r['pair_context_current'] for r in rows),
        'changed_or_removed_pair_contexts': sum(not r['pair_context_current'] for r in rows),
        'declared_review_windows': {state: sum(r['declared_review_window'] == state for r in rows)
            for state in ('unknown', 'not_yet_open', 'within_declared_window', 'elapsed')},
        'global_retrieval_must_rerun': result['global_retrieval_must_rerun'],
        'next_step': ('Rerun passage selection against the changed corpus before using its ranking.'
            if result['global_retrieval_must_rerun'] else 'Review unknown or elapsed source windows; pair identity alone does not establish truth.'),
        'details_saved': saved, 'source_freshness_authenticated': False, 'tag_asserted': False,
        'independent_accuracy_evidence': False, 'network_used': False}
