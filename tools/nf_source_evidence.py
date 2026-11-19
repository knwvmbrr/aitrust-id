"""Caller-selected source passage observations. No NF/FI tag or factual verdict."""
import hashlib
import json
from pathlib import Path
import platform
import runpy
import subprocess
import sys

from protocol import corpus
from protocol.normalization import NORMALIZATION_ID, normalize_nfc
from tools import nf_private_io as io

ROOT = Path(__file__).absolute().parents[1]
PROFILE = 'nf-selected-source-evidence/v1'
MAX_PAIRS = 8
MAX_SUBJECT_BYTES = 32000
MAX_SUBJECT_CHARACTERS = 8000
MAX_PASSAGE_CHARACTERS = 2000
MAX_SIDECAR_BYTES = 65536
MAX_RESULT_BYTES = 262144
DEADLINE = 8
CHECKS = ('literal', 'cosine')
COMMON = ('tools/nf_source_evidence.py', 'tools/nf_private_io.py',
          'scripts/check-nf-source-evidence.py', 'scripts/nf-source-worker.py',
          'scripts/worker_process.py', 'protocol/corpus.py',
          'protocol/normalization.py', 'protocol/unicode15-data.json')
OPTIONAL = {'literal': (), 'cosine': ('protocol/corpus_support.py',)}
METHODS = {'literal': 'corpus-query-case-sensitive-nonoverlapping/v1',
           'cosine': 'corpus-support-ascii-cosine/1.0.0'}


def require(value):
    if not value:
        raise ValueError('Selected source evidence unavailable.')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def parse(raw, limit):
    require(type(raw) is bytes and 0 < len(raw) <= limit)
    def integer(value):
        require(len(value) <= 7)
        return int(value)
    def floating(value):
        import math
        result = float(value)
        require(math.isfinite(result))
        return result
    return json.loads(raw, object_pairs_hook=corpus.unique_pairs, parse_int=integer,
                      parse_float=floating, parse_constant=lambda _: require(False))


def source_identity(capture, names):
    # Reuse held source descriptors; repeated pre/post checks must not amplify FDs.
    cache = getattr(capture, '_nf_source_cache', {})
    for name in names:
        if name not in cache:
            cache[name] = sha(capture.read(ROOT / name, 1000000, private=False))
    capture._nf_source_cache = cache
    capture.check()
    return {name: cache[name] for name in names}


def method_identity(capture, check):
    try:
        # Optional method drift belongs only to this check, not common input I/O.
        with io.Capture() as optional:
            return source_identity(optional, OPTIONAL[check])
    except (OSError, ValueError):
        return None


def normalized_subject(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_SUBJECT_BYTES)
    value = raw.decode('utf-8', 'strict')
    require(bool(value.strip()) and '\0' not in value and len(value) <= MAX_SUBJECT_CHARACTERS)
    value = normalize_nfc(value)
    require(len(value) <= MAX_SUBJECT_CHARACTERS)
    return value


def span(value, size):
    require(type(value) is list and len(value) == 2 and all(type(n) is int for n in value))
    require(0 <= value[0] < value[1] <= size and value[1] - value[0] <= MAX_PASSAGE_CHARACTERS)
    return value


def bind(corpus_raw, subject_raw, selection, checks, capture):
    require(type(checks) is list and 1 <= len(checks) <= 2
            and all(type(k) is str and k in CHECKS for k in checks) and len(set(checks)) == len(checks))
    require(type(selection) is dict and set(selection) == {'format', 'pairs'}
            and selection['format'] == 'nf-pair-selections/v1')
    rows = selection['pairs']
    require(type(rows) is list and 1 <= len(rows) <= MAX_PAIRS)
    attached = corpus.parse(corpus_raw)
    text = normalized_subject(subject_raw)
    documents = {d['id']: d for d in attached['documents']}
    normalized = {}
    pairs = []
    seen = set()
    for row in rows:
        require(type(row) is dict and set(row) == {'claim_span', 'document_id', 'source_span'})
        identity = row['document_id']
        require(type(identity) is str and corpus.valid_id(identity) and identity in documents)
        document = documents[identity]
        if identity not in normalized:
            normalized[identity] = normalize_nfc(document['text'])
        source = normalized[identity]
        claim_span, source_span = span(row['claim_span'], len(text)), span(row['source_span'], len(source))
        claim, passage = text[slice(*claim_span)], source[slice(*source_span)]
        require(bool(claim.strip()) and bool(passage.strip()))
        key = (tuple(claim_span), identity, tuple(source_span))
        require(key not in seen)
        seen.add(key)
        pairs.append({'claim_span': list(claim_span), 'claim_sha256': sha(claim.encode()),
                      'document_id': identity, 'document_sha256': document['sha256'],
                      'normalized_document_sha256': sha(source.encode()),
                      'source_span': list(source_span), 'passage_sha256': sha(passage.encode())})
    value = {'format': 'nf-selected-pairs-sidecar/v1', 'normalization_id': NORMALIZATION_ID,
             'offset_unit': 'NFC_unicode_codepoint', 'raw_subject_sha256': sha(subject_raw),
             'subject_sha256': sha(text.encode()), 'subject_characters': len(text),
             'corpus_file_sha256': sha(corpus_raw), 'corpus_manifest_sha256': attached['manifest_sha256'],
             'pairs': pairs, 'checks': list(checks), 'source_sha256': source_identity(capture, COMMON),
             'method_sha256': {k: method_identity(capture, k) for k in checks}}
    require(len(io.encoded(value)) < MAX_SIDECAR_BYTES)
    return value


def validate_sidecar(corpus_raw, subject_raw, raw, capture):
    value = parse(raw, MAX_SIDECAR_BYTES)
    fields = {'format', 'normalization_id', 'offset_unit', 'raw_subject_sha256',
              'subject_sha256', 'subject_characters', 'corpus_file_sha256',
              'corpus_manifest_sha256', 'pairs', 'checks', 'source_sha256', 'method_sha256'}
    require(type(value) is dict and set(value) == fields)
    require(type(value['pairs']) is list and 1 <= len(value['pairs']) <= MAX_PAIRS)
    rows = []
    for row in value['pairs']:
        require(type(row) is dict and set(row) == {'claim_span', 'claim_sha256', 'document_id',
            'document_sha256', 'normalized_document_sha256', 'source_span', 'passage_sha256'})
        rows.append({k: row[k] for k in ('claim_span', 'document_id', 'source_span')})
    expected = bind(corpus_raw, subject_raw, {'format': 'nf-pair-selections/v1', 'pairs': rows}, value['checks'], capture)
    # Optional method changes affect only that check, never the sibling result.
    require(type(value['method_sha256']) is dict and set(value['method_sha256']) == set(value['checks']))
    for k in value['checks']:
        item = value['method_sha256'][k]
        require(k != 'literal' or item == {})
        require(item is None or (type(item) is dict and set(item) == set(OPTIONAL[k])
                and all(type(v) is str and len(v) == 64 and all(c in '0123456789abcdef' for c in v) for v in item.values())))
    require(io.encoded({k: v for k, v in value.items() if k != 'method_sha256'}) ==
            io.encoded({k: v for k, v in expected.items() if k != 'method_sha256'}))
    attached, text = corpus.parse(corpus_raw), normalized_subject(subject_raw)
    documents = {d['id']: normalize_nfc(d['text']) for d in attached['documents']}
    pairs = [{'claim': text[slice(*p['claim_span'])],
              'passage': documents[p['document_id']][slice(*p['source_span'])]} for p in value['pairs']]
    return value, expected['method_sha256'], pairs


def projection(passage):
    content = {'format': corpus.VERSION, 'documents': [
        {'id': 'selected', 'sha256': sha(passage.encode()), 'text': passage}]}
    return corpus.parse(corpus.encoded({**content, 'manifest_sha256': sha(corpus.encoded(content))}))


def evaluate(kind, pairs):
    """Canonical components run only in the bounded worker, never another tag."""
    rows = []
    for index, pair in enumerate(pairs):
        claim, passage = pair['claim'], pair['passage']
        record = projection(passage)
        if kind == 'literal':
            result = corpus.query(record, claim)
            matches = [{'claim_span': m['query_span'], 'source_span': m['source_span']} for m in result['matches']]
            row = {'pair_index': index, 'state': result['state'], 'matches': matches,
                   'match_limit': result['match_limit'], 'limit_reached': len(matches) == result['match_limit']}
        elif kind == 'cosine':
            from protocol import corpus_support
            require('\n' not in claim and '\r' not in claim)
            result = corpus_support.observe(record, claim, threshold=.75, maximum=10)
            matches = [{'claim_span': m['spans'][0], 'source_span': m['reference']['source_span'],
                        'cosine': m['score']} for m in result['findings']]
            row = {'pair_index': index, 'state': result['state'], 'matches': matches,
                   'threshold': .75, 'maximum_findings': 10, 'reference_passages': result['reference_passages'],
                   'unsupported_reference_passages': result['unsupported_reference_passages']}
        else:
            require(False)
        rows.append({**row, 'projection_manifest_sha256': record['manifest_sha256'],
                     'projection_document_sha256': record['documents'][0]['sha256']})
    return rows


def validate_output(value, kind, pairs, request_sha256, sources):
    require(type(value) is dict and set(value) == {'component', 'method', 'request_sha256',
        'source_sha256', 'network_control', 'ipv4_ipv6_denied', 'rows'})
    network = {'Darwin': 'macos_sandbox_deny_network', 'Linux': 'linux_seccomp_deny_network'}
    require(value['component'] == kind and value['method'] == METHODS[kind]
            and value['request_sha256'] == request_sha256 and value['source_sha256'] == sources
            and value['network_control'] == network.get(platform.system()) and value['ipv4_ipv6_denied'] is True)
    rows = value['rows']
    require(type(rows) is list and len(rows) == len(pairs))
    for index, (row, pair) in enumerate(zip(rows, pairs)):
        common = {'pair_index', 'state', 'matches', 'projection_manifest_sha256', 'projection_document_sha256'}
        fields = {'match_limit', 'limit_reached'} if kind == 'literal' else {
            'threshold', 'maximum_findings', 'reference_passages', 'unsupported_reference_passages'}
        require(type(row) is dict and set(row) == common | fields and type(row['pair_index']) is int and row['pair_index'] == index)
        record = projection(pair['passage'])
        require(row['projection_manifest_sha256'] == record['manifest_sha256']
                and row['projection_document_sha256'] == sha(pair['passage'].encode()))
        require(type(row['matches']) is list and len(row['matches']) <= 10)
        if kind == 'literal':
            # Cheap exact replay uses the same foundation; no optional import.
            require(io.encoded(row) == io.encoded(evaluate('literal', [pair])[0] | {'pair_index': index}))
        else:
            from protocol import corpus_support
            require('\n' not in pair['claim'] and '\r' not in pair['claim'])
            claim_lines = corpus_support.lines(pair['claim'])
            require(len(claim_lines) == 1)
            passages = corpus_support.lines(pair['passage'])
            usable = set()
            for left, right, phrase in passages:
                try:
                    corpus_support.vector(phrase)
                    usable.add((left, right))
                except corpus.CorpusError:
                    pass
            require(type(row['threshold']) is float and row['threshold'] == .75
                    and type(row['maximum_findings']) is int and row['maximum_findings'] == 10)
            for name in ('reference_passages', 'unsupported_reference_passages'):
                require(type(row[name]) is int and 0 <= row[name] <= 4096)
            require(row['reference_passages'] > 0 and row['reference_passages'] + row['unsupported_reference_passages'] <= len(pair['passage']))
            require(row['reference_passages'] == len(usable)
                    and row['unsupported_reference_passages'] == len(passages) - len(usable))
            require(row['state'] == ('SIMILAR_PASSAGE' if row['matches'] else 'NO_SIMILAR_PASSAGE'))
            previous = 2
            seen = set()
            for match in row['matches']:
                require(type(match) is dict and set(match) == {'claim_span', 'source_span', 'cosine'})
                span(match['claim_span'], len(pair['claim']))
                span(match['source_span'], len(pair['passage']))
                require(match['claim_span'] == list(claim_lines[0][:2])
                        and tuple(match['source_span']) in usable and tuple(match['source_span']) not in seen)
                seen.add(tuple(match['source_span']))
                score = match['cosine']
                require(type(score) in (int, float) and .75 <= score <= 1 and score <= previous)
                previous = score
    return value


LAUNCH = "import os,sys;os.execve(sys.argv[1],sys.argv[1:],{'PATH':'/usr/bin:/bin','LC_ALL':'C','PYTHONIOENCODING':'utf-8'})"


def run_check(kind, pairs, expected_sources, capture):
    unavailable = {'component': kind, 'state': 'UNAVAILABLE', 'reason': 'selected_check_unavailable'}
    try:
        if expected_sources is None or method_identity(capture, kind) != expected_sources:
            return unavailable
        sources = {**source_identity(capture, COMMON), **expected_sources}
        request = {'component': kind, 'pairs': pairs, 'source_sha256': sources}
        raw = io.encoded(request)
        require(len(raw) <= MAX_RESULT_BYTES)
        command = [sys.executable, '-I', '-S', '-B', str(ROOT / 'scripts/nf-source-worker.py')]
        if platform.system() == 'Darwin':
            require(Path('/usr/bin/sandbox-exec').is_file())
            command = ['/usr/bin/sandbox-exec', '-p', '(version 1) (allow default) (deny network*)', *command]
        else:
            require(platform.system() == 'Linux')
        supervise = runpy.run_path(str(ROOT / 'scripts/worker_process.py'))['run_worker']
        child = supervise([sys.executable, '-I', '-S', '-B', '-c', LAUNCH, *command],
                          input=raw, timeout=DEADLINE, output_limit=MAX_RESULT_BYTES)
        require(child.returncode == 0)
        value = validate_output(parse(child.stdout, MAX_RESULT_BYTES), kind, pairs, sha(raw), sources)
        require({**source_identity(capture, COMMON), **method_identity(capture, kind)} == sources)
        capture.check()
        return {'component': kind, 'state': 'COMPLETE', 'observation': value}
    except Exception:
        return unavailable


def check(corpus_raw, subject_raw, sidecar_raw, capture):
    bindings, current, pairs = validate_sidecar(corpus_raw, subject_raw, sidecar_raw, capture)
    checks = []
    for kind in bindings['checks']:
        row = (run_check(kind, pairs, bindings['method_sha256'][kind], capture)
               if current[kind] == bindings['method_sha256'][kind] else
               {'component': kind, 'state': 'UNAVAILABLE', 'reason': 'selected_check_unavailable'})
        if row['state'] == 'COMPLETE':
            for observed, selection in zip(row['observation']['rows'], bindings['pairs']):
                observed['selected_pair'] = selection
                observed['match_offset_origin'] = 'original_subject_and_document'
                for match in observed['matches']:
                    match['claim_span'] = [v + selection['claim_span'][0] for v in match['claim_span']]
                    match['source_span'] = [v + selection['source_span'][0] for v in match['source_span']]
        checks.append(row)
    failed = sum(r['state'] == 'UNAVAILABLE' for r in checks)
    state = 'UNAVAILABLE' if failed == len(checks) else 'PARTIAL' if failed else 'COMPLETE'
    result = {'format': PROFILE, 'state': state, 'bindings': bindings, 'checks': checks,
              'selection_source': 'explicit_caller_selected_NFC_spans',
              'subject_text_included': False, 'source_text_included': False, 'tags': [],
              'truth_established': False, 'semantic_support_established': False,
              'source_authenticity_or_freshness_established': False, 'independent_accuracy_evidence': False,
              'unselected_claims_or_sources_evaluated': False, 'score_is_probability': False}
    require(len(io.encoded(result)) <= MAX_RESULT_BYTES)
    return result


def summary(result, saved=False):
    return {'format': PROFILE, 'state': result['state'], 'selected_pairs': len(result['bindings']['pairs']),
            'checks': [{'component': r['component'], 'state': r['state'],
                        'pairs_with_observations': sum(bool(p['matches']) for p in r['observation']['rows'])
                        if r['state'] == 'COMPLETE' else 0} for r in result['checks']],
            'private_report_saved': saved, 'tags': [], 'truth_established': False,
            'semantic_support_established': False, 'independent_accuracy_evidence': False}
