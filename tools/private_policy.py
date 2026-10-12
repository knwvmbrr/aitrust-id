"""Optional caller-bound organization literal observations; no public assertion rewriting."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from protocol.evidence import unique, finite
from protocol.normalization import normalize_nfc, NORMALIZATION_ID

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'organization-literal-observation/1.0.0'
POLICY = 'organization-literal-policy/v1'
CONTEXT = 'organization-literal-selection/v1'
MAX_TEXT = 20_000
MAX_RESULTS = 64


class PolicyError(ValueError):
    pass


def require(value):
    if not value:
        raise PolicyError('Private policy or selection refused')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def parse(raw):
    require(isinstance(raw, bytes) and 0 < len(raw) <= 65_536)
    value = json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(PolicyError('Invalid number')))
    finite(value)
    return value


def vocabulary():
    raw = (ROOT / 'spec/vocabulary.json').read_bytes()
    value = parse(raw)
    return set(value['codes'] + value['proposed_codes'] + ['PII_OUTBOUND', 'VALID', 'VALIDATED',
                'CERTIFIED', 'VERIFIED', 'COMPLIANT']), sha(raw)


@dataclass(frozen=True)
class Rule:
    code: str
    terms: tuple


@dataclass(frozen=True)
class Policy:
    namespace: str
    policy_id: str
    revision: int
    rules: tuple
    sha256: str
    vocabulary_sha256: str


def policy(raw):
    value = parse(raw)
    keys = {'format', 'namespace', 'policy_id', 'revision', 'claim', 'limits_visible',
            'receipts_optional', 'personal_checks_separate', 'rules'}
    require(isinstance(value, dict) and set(value) == keys and value['format'] == POLICY)
    for key in ('limits_visible', 'receipts_optional', 'personal_checks_separate'):
        require(value[key] is True)
    require(value['claim'] == 'literal_term_occurrence_only')
    namespace = value['namespace']
    require(isinstance(namespace, str) and re.fullmatch(r'[a-z][a-z0-9-]{2,47}', namespace))
    require(namespace not in {'aitrust', 'aitrust-id', 'public', 'standard', 'system'})
    require(isinstance(value['policy_id'], str) and re.fullmatch(r'[a-z][a-z0-9-]{0,47}', value['policy_id']))
    require(type(value['revision']) is int and 1 <= value['revision'] <= 1_000_000)
    rows = value['rules']; require(isinstance(rows, list) and 1 <= len(rows) <= 32)
    reserved, vocab_hash = vocabulary(); rules = []; seen = set()
    for row in rows:
        require(isinstance(row, dict) and set(row) == {'code', 'terms'})
        code = row['code']; terms = row['terms']
        require(isinstance(code, str) and re.fullmatch(r'[A-Z][A-Z0-9_]{1,23}', code)
                and code not in reserved and code not in seen)
        seen.add(code)
        require(isinstance(terms, list) and 1 <= len(terms) <= 8
                and all(isinstance(term, str) for term in terms) and len(set(terms)) == len(terms))
        for term in terms:
            require(isinstance(term, str) and 1 <= len(term) <= 128 and term == term.strip()
                    and all(32 <= ord(c) < 127 for c in term)
                    and re.match(r'[A-Za-z0-9]', term) and re.search(r'[A-Za-z0-9]$', term))
        rules.append(Rule(code, tuple(terms)))
    return Policy(namespace, value['policy_id'], value['revision'], tuple(rules), sha(raw), vocab_hash)


def observe(text, raw_policy, context, *, reviewed):
    require(reviewed is True and isinstance(text, str) and 0 < len(text) <= MAX_TEXT)
    subject = normalize_nfc(text); require(subject.strip() and len(subject) <= MAX_TEXT)
    selected = policy(raw_policy)
    require(isinstance(context, dict) and set(context) == {'format', 'namespace', 'policy_sha256', 'subject_sha256'})
    require(context['format'] == CONTEXT and context['namespace'] == selected.namespace
            and context['policy_sha256'] == selected.sha256
            and context['subject_sha256'] == sha(subject.encode('utf-8')))
    rows = []; total = 0
    for rule in selected.rules:
        hits = set()
        for term in rule.terms:
            # Literal matching only. ASCII word adjacency is declared explicitly,
            # independent of the host's changing Unicode character categories.
            for match in re.finditer(re.escape(term), subject):
                start, end = match.span()
                word = lambda c: c.isascii() and (c.isalnum() or c == '_')
                if (start and word(subject[start-1])) or (end < len(subject) and word(subject[end])):
                    continue
                hits.add((start, end))
        for start, end in sorted(hits):
            total += 1
            if len(rows) < MAX_RESULTS:
                rows.append({'qualified_code': selected.namespace + ':' + rule.code,
                             'span': [start, end],
                             'meaning': 'selected_case_sensitive_literal_with_ASCII_word_boundaries'})
    return {'profile': PROFILE, 'state': 'OBSERVATIONS' if total else 'NO_SUPPORTED_TERM',
            'namespace': selected.namespace, 'namespace_ownership': 'unverified_caller_selection',
            'policy_id': selected.policy_id, 'policy_revision': selected.revision,
            'policy_sha256': selected.sha256, 'subject_sha256': context['subject_sha256'],
            'method_sha256': sha(Path(__file__).read_bytes()),
            'vocabulary_sha256': selected.vocabulary_sha256, 'normalization_id': NORMALIZATION_ID,
            'observations': rows, 'total_observations': total, 'truncated': total > MAX_RESULTS,
            'maximum_returned_observations': MAX_RESULTS, 'span_units': 'NFC_unicode_codepoints',
            'policy_review_signal': 'explicit_local_invocation_not_employee_consent_proof',
            'public_assertions_processed': False, 'public_tag_asserted': False,
            'standard_namespace_adopted': False, 'limits_visible': True, 'receipts_required': False,
            'compliance_established': False, 'truth_established': False, 'release_approved': False}
