"""Caller-declared source context around bounded static Python flow; no PS mapping."""
import hashlib
import json
from pathlib import Path
import platform
import runpy
import sys

from protocol.normalization import NORMALIZATION_ID, normalize_nfc
from tools import credential_context_io as io

ROOT = Path(__file__).absolute().parents[1]
PROFILE = 'caller-declared-credential-context/v1'
LABELS = ('recommended', 'quoted_example', 'unknown')
MAX_DOCUMENT_BYTES = 64000
MAX_DOCUMENT_CHARACTERS = 16000
MAX_CODE_CHARACTERS = 8000
MAX_PACKET_BYTES = 65536
MAX_REQUEST_BYTES = 131072
MAX_RESULT_BYTES = 262144
DEADLINE = 6
SOURCES = ('tools/credential_flow_context.py', 'tools/credential_context_io.py',
           'tools/credential_flow.py', 'scripts/credential-flow-context.py',
           'scripts/credential-context-worker.py', 'scripts/worker_process.py',
           'protocol/corpus.py', 'protocol/normalization.py', 'protocol/unicode15-data.json')


def require(value):
    if not value:
        raise ValueError('Selected credential context unavailable.')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def parse(raw, limit=MAX_PACKET_BYTES):
    require(type(raw) is bytes and 0 < len(raw) <= limit)
    def integer(value):
        require(len(value) <= 6)
        return int(value)
    return json.loads(raw, object_pairs_hook=io.corpus.unique_pairs, parse_int=integer,
                      parse_float=lambda _: require(False), parse_constant=lambda _: require(False))


def identity(capture):
    cache = getattr(capture, '_credential_sources', None)
    if cache is None:
        cache = {name: sha(capture.read(ROOT / name, 1000000, private=False)) for name in SOURCES}
        capture._credential_sources = cache
    capture.check()
    return dict(cache)


def document(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_DOCUMENT_BYTES)
    text = raw.decode('utf-8', 'strict')
    require(bool(text.strip()) and '\0' not in text and len(text) <= MAX_DOCUMENT_CHARACTERS)
    normalized = normalize_nfc(text)
    require(len(normalized) <= MAX_DOCUMENT_CHARACTERS)
    return text, normalized


def mapped_span(text, normalized, value, maximum):
    require(type(value) is list and len(value) == 2 and all(type(n) is int for n in value))
    left, right = value
    require(0 <= left < right <= len(text) and right-left <= maximum)
    prefix, selected, suffix = normalize_nfc(text[:left]), normalize_nfc(text[left:right]), normalize_nfc(text[right:])
    # Reject a boundary inside a combining/composition sequence instead of
    # guessing an offset or normalizing away neighboring context.
    require(prefix + selected + suffix == normalized and bool(selected.strip()) and len(selected) <= maximum)
    return {'raw_span': list(value), 'normalized_span': [len(prefix), len(prefix)+len(selected)],
            'raw_sha256': sha(text[left:right].encode()), 'normalized_sha256': sha(selected.encode())}


def bind(raw, selection, capture):
    require(type(selection) is dict and set(selection) == {'format', 'code_span', 'context_span', 'declared_context'}
            and selection['format'] == 'credential-context-selection/v1')
    require(type(selection['declared_context']) is str and selection['declared_context'] in LABELS)
    text, normalized = document(raw)
    code = mapped_span(text, normalized, selection['code_span'], MAX_CODE_CHARACTERS)
    context = mapped_span(text, normalized, selection['context_span'], MAX_DOCUMENT_CHARACTERS)
    require(context['raw_span'][0] <= code['raw_span'][0] < code['raw_span'][1] <= context['raw_span'][1])
    require(context['normalized_span'][0] <= code['normalized_span'][0] < code['normalized_span'][1] <= context['normalized_span'][1])
    result = {'format': 'credential-context-sidecar/v1', 'normalization_id': NORMALIZATION_ID,
              'offset_unit': 'unicode_codepoint', 'raw_document_sha256': sha(raw),
              'normalized_document_sha256': sha(normalized.encode()), 'raw_document_characters': len(text),
              'normalized_document_characters': len(normalized), 'code': code, 'context': context,
              'declared_context': selection['declared_context'], 'declaration_source': 'explicit_caller_selection',
              'declaration_verified': False, 'selection_sha256': sha(io.encoded(selection)), 'source_sha256': identity(capture)}
    require(len(io.encoded(result)) <= MAX_PACKET_BYTES)
    return result


def checked(raw, packet, capture):
    value = parse(packet)
    fields = {'format', 'normalization_id', 'offset_unit', 'raw_document_sha256',
              'normalized_document_sha256', 'raw_document_characters', 'normalized_document_characters',
              'code', 'context', 'declared_context', 'declaration_source', 'declaration_verified', 'selection_sha256', 'source_sha256'}
    require(type(value) is dict and set(value) == fields)
    for name in ('code', 'context'):
        require(type(value[name]) is dict and set(value[name]) == {'raw_span', 'normalized_span', 'raw_sha256', 'normalized_sha256'})
    expected = bind(raw, {'format': 'credential-context-selection/v1', 'code_span': value['code']['raw_span'],
                         'context_span': value['context']['raw_span'], 'declared_context': value['declared_context']}, capture)
    require(io.encoded(value) == io.encoded(expected))
    _, text = document(raw)
    return expected, text[slice(*expected['code']['normalized_span'])]


LAUNCH = "import os,sys;os.execve(sys.argv[1],sys.argv[1:],{'PATH':'/usr/bin:/bin','LC_ALL':'C','PYTHONIOENCODING':'utf-8'})"


def observe(code, sources, capture):
    try:
        request = {'code': code, 'source_sha256': sources}
        raw = io.encoded(request)
        require(len(raw) <= MAX_REQUEST_BYTES)
        command = [sys.executable, '-I', '-S', '-B', str(ROOT / 'scripts/credential-context-worker.py')]
        if platform.system() == 'Darwin':
            require(Path('/usr/bin/sandbox-exec').is_file())
            command = ['/usr/bin/sandbox-exec', '-p', '(version 1) (allow default) (deny network*)', *command]
        else:
            require(platform.system() == 'Linux')
        supervisor = runpy.run_path(str(ROOT / 'scripts/worker_process.py'))['run_worker']
        child = supervisor([sys.executable, '-I', '-S', '-B', '-c', LAUNCH, *command], input=raw,
                           timeout=DEADLINE, output_limit=MAX_RESULT_BYTES)
        require(child.returncode == 0)
        value = parse(child.stdout, MAX_RESULT_BYTES)
        require(type(value) is dict and set(value) == {'request_sha256', 'source_sha256', 'network_control', 'ipv4_ipv6_denied', 'observation'})
        require(value['request_sha256'] == sha(raw) and value['source_sha256'] == sources
                and value['network_control'] == {'Darwin':'macos_sandbox_deny_network','Linux':'linux_seccomp_deny_network'}.get(platform.system())
                and value['ipv4_ipv6_denied'] is True)
        # Same bounded canonical AST method, not a second heuristic/context vote.
        from tools import credential_flow
        expected = credential_flow.observe(code)
        require(io.encoded(value['observation']) == io.encoded(expected))
        require(identity(capture) == sources)
        return value
    except Exception:
        return None


def check(raw, packet, capture):
    binding, code = checked(raw, packet, capture)
    value = observe(code, binding['source_sha256'], capture)
    findings = []
    if value is not None:
        start = binding['code']['normalized_span'][0]
        for finding in value['observation']['findings']:
            findings.append({**finding, 'source_spans': [[a+start,b+start] for a,b in finding['source_spans']],
                             'sink_span': [n+start for n in finding['sink_span']]})
    return {'format': PROFILE, 'state': value['observation']['state'] if value else 'UNAVAILABLE',
            'bindings': binding, 'canonical_code_observation': value['observation'] if value else None,
            'network_control': value['network_control'] if value else None,
            'ipv4_ipv6_denied': value['ipv4_ipv6_denied'] if value else None,
            'document_findings': findings if value else None,
            'finding_offset_origin': 'normalized_whole_document', 'declared_context': binding['declared_context'],
            'declaration_verified': False, 'use_mention_inferred': False, 'authorization_or_intent_established': False,
            'PS_mapping_performed': False, 'subject_executed': False, 'secret_contents_read': False,
            'live_credential_verified': False, 'text_included': False, 'independent_accuracy_evidence': False, 'tags': []}


def summary(value, saved=False):
    return {'format': PROFILE, 'state': value['state'], 'declared_context': value['declared_context'],
            'declaration_verified': False, 'use_mention_inferred': False,
            'flow_count': len(value['document_findings']) if value['document_findings'] is not None else None,
            'private_report_saved': saved, 'subject_executed': False, 'secret_contents_read': False,
            'PS_mapping_performed': False, 'live_credential_verified': False,
            'authorization_or_intent_established': False, 'independent_accuracy_evidence': False, 'tags': []}
