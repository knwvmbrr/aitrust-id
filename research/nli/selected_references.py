"""One caller-selected, corpus-bound reference pair; no automatic retrieval or tag."""
import hashlib
import json
from pathlib import Path

from protocol import corpus
from protocol.normalization import normalize_nfc, NORMALIZATION_ID
from .pairs import analyze, require, scalar, validate

SELECTION_PROFILE = 'caller-selected-reference-pair/1.0.0'
RESULT_PROFILE = 'selected-reference-nli-observation/1.0.0'
MAX_SELECTION_BYTES = 8192


def subject_text(value):
    require(scalar(value) and bool(value.strip()) and len(value) <= 2000)
    text = normalize_nfc(value)
    require(len(text) <= 2000)
    return text


def selected_line(text, number):
    """Physical one-based LF/CRLF line; spans are trimmed NFC codepoints."""
    parts = text.split('\n')
    require(type(number) is int and 1 <= number <= len(parts))
    offset = sum(len(part) + 1 for part in parts[:number-1])
    body = parts[number-1]
    if number < len(parts) and body.endswith('\r'):
        body = body[:-1]
    require(body.isascii() and all(c == '\t' or 32 <= ord(c) <= 126 for c in body))
    left = len(body) - len(body.lstrip(' \t'))
    right = len(body.rstrip(' \t'))
    require(left < right and right-left <= 2000)
    selected = body[left:right]
    # Match the published ASCII lexical input ceiling without retrieving/ranking.
    from protocol.corpus_support import vector
    vector(selected)
    return [offset+left, offset+right]


def bind(record, subject, claim_line, document_id, reference_line):
    record = corpus.parse(corpus.encoded(record))
    normalized = subject_text(subject)
    require(corpus.valid_id(document_id))
    documents = {document['id']: document for document in record['documents']}
    require(document_id in documents)
    document = documents[document_id]
    reference = normalize_nfc(document['text'])
    content = {'profile': SELECTION_PROFILE, 'language': 'en',
        'normalization_id': NORMALIZATION_ID,
        'original_subject_sha256': corpus.sha(subject.encode('utf-8')),
        'subject_sha256': corpus.sha(normalized.encode('utf-8')),
        'manifest_sha256': record['manifest_sha256'],
        'claim': {'line': claim_line, 'span': selected_line(normalized, claim_line)},
        'reference': {'document_id': document_id, 'document_sha256': document['sha256'],
            'normalized_source_sha256': corpus.sha(reference.encode('utf-8')),
            'line': reference_line, 'source_span': selected_line(reference, reference_line)}}
    result = {**content, 'selection_sha256': corpus.sha(corpus.encoded(content))}
    require(len(corpus.encoded(result)) <= MAX_SELECTION_BYTES)
    return result


def capture(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_SELECTION_BYTES)
    value = json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=corpus.unique_pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Invalid selection number')))
    require(type(value) is dict)
    return value


def checked(record, subject, selection):
    require(type(selection) is dict and set(selection) == {'profile', 'language',
        'normalization_id', 'original_subject_sha256', 'subject_sha256',
        'manifest_sha256', 'claim', 'reference', 'selection_sha256'})
    require(type(selection['claim']) is dict and set(selection['claim']) == {'line', 'span'})
    require(type(selection['reference']) is dict and set(selection['reference']) == {
        'document_id', 'document_sha256', 'normalized_source_sha256', 'line', 'source_span'})
    expected = bind(record, subject, selection['claim']['line'],
                    selection['reference']['document_id'], selection['reference']['line'])
    # Canonical encoding retains exact JSON types; True is not line number 1.
    require(corpus.encoded(selection) == corpus.encoded(expected))
    return expected


def prepare(record, subject, selection):
    selected = checked(record, subject, selection)
    normalized = subject_text(subject)
    document = next(d for d in record['documents'] if d['id'] == selected['reference']['document_id'])
    source = normalize_nfc(document['text'])
    first = source[slice(*selected['reference']['source_span'])]
    second = normalized[slice(*selected['claim']['span'])]
    request = {'schema_version': 1, 'language': 'en', 'text': first+'\n'+second+'\n',
        'pairs': [{'id': 'selected-reference-000', 'first': [0, len(first)],
                   'second': [len(first)+1, len(first)+1+len(second)]}]}
    validate(request)
    return request


def observe(record, subject, selection, backend, identity):
    selected = checked(record, subject, selection)
    request = prepare(record, subject, selected)
    output = analyze(request, backend, identity)
    row = output['pairs'][0]
    observation = {key: row[key] for key in ['token_count', 'logits', 'normalized_model_scores',
                                             'top_model_labels', 'calibrated_probability']}
    observation.update({'proposed_signal': 'sig.corpus_contradiction.v1',
        'claim_span': selected['claim']['span'], 'reference': selected['reference'],
        'direction': 'reference_is_premise_claim_is_hypothesis'})
    return {'profile': RESULT_PROFILE, 'state': 'observed_model_outputs',
        'method_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'subject_sha256': selected['subject_sha256'], 'manifest_sha256': selected['manifest_sha256'],
        'normalization_id': NORMALIZATION_ID, 'span_units': 'NFC_unicode_codepoints',
        'selection': selected, 'selection_basis': 'explicit_caller_selected_physical_lines',
        'retrieval_evaluation_obtained': False, 'retrieval': None,
        'model_evaluation_obtained': True, 'model_identity': output['model_identity'],
        'observations': [observation], 'reference_freshness': 'unestablished',
        'absence_proves_false': False, 'truth_established': False,
        'independent_corroboration': False, 'tag_asserted': False, 'release_approved': False}
