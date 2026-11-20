"""Closed optional framing component around unchanged authority quotation code."""
import hashlib
import json

from protocol.normalization import normalize_nfc, NORMALIZATION_ID

COMPONENT = 'authority-quotation'
PROFILE = 'framing-quotation-component/v1'
METHOD = 'ascii-quoted-authority-observations/1.0.0'
REPLAY_PROFILE = 'framing-quotation-canonical-replay/v1'
MAX_RECORD_BYTES = 100000
COUNTS = ('outside_supported_quotes_without_marker', 'outside_supported_quotes_with_marker',
          'quoted_phrase_count', 'supported_quote_count')
CANONICAL_SOURCES = ('tools/authority_quotation.py', 'scripts/authority-quotation.py',
    'tools/language_observations.py', 'protocol/normalization.py',
    'protocol/unicode15-data.json', 'protocol/corpus.py', 'tools/blind_review_io.py')
FALSE_FIELDS = ('source_lookup_performed', 'quote_endorsement_interpreted', 'negation_interpreted',
    'semantic_attribution_interpreted', 'intent_established', 'truth_established',
    'independent_accuracy_evidence', 'network_used', 'subject_text_included')


def require(value):
    if not value:
        raise ValueError('Quoted authority observation unavailable.')


def canonical_json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(',', ':'))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(text):
    require(isinstance(text, str) and text.strip() and len(text) <= 8000 and '\0' not in text)
    raw = text.encode('utf-8', 'strict')
    normalized = normalize_nfc(text)
    require(len(raw) <= 32000 and len(normalized) <= 8000)
    return {'raw_subject_sha256': digest(raw), 'raw_subject_characters': len(text),
            'raw_subject_bytes': len(raw), 'subject_sha256': digest(normalized.encode()),
            'subject_characters': len(normalized), 'normalization_id': NORMALIZATION_ID,
            'offset_unit': 'NFC_unicode_codepoint'}


def produce(text, sources, limitations):
    # Optional method import stays inside this selected worker, not the parent.
    from tools.authority_quotation import observe
    _, original = observe(text, 'en')
    record = {'format': PROFILE, 'component': COMPONENT, 'method': METHOD,
              'state': original['state'], 'counts': {k: original[k] for k in COUNTS},
              **identity(text), 'sources': sources, 'original': original,
              'limitations': dict(limitations), 'subject_text_included': False}
    require(len(canonical_json(record).encode()) <= MAX_RECORD_BYTES)
    return record


def object_fields(value, names):
    require(type(value) is dict and set(value) == set(names))


def span(value, length):
    require(type(value) is list and len(value) == 2 and all(type(x) is int for x in value)
            and 0 <= value[0] < value[1] <= length)


def spans(values, length, maximum):
    require(type(values) is list and len(values) <= maximum)
    previous = None
    for item in values:
        span(item, length)
        require(previous is None or tuple(previous) < tuple(item))
        previous = item


def validate_shape(record, text, sources, limitations):
    expected_identity = identity(text)
    object_fields(record, ['format', 'component', 'method', 'state', 'counts', *expected_identity,
                          'sources', 'original', 'limitations', 'subject_text_included'])
    require(record['format'] == PROFILE and record['component'] == COMPONENT
            and record['method'] == METHOD and record['state'] in ('OBSERVATIONS', 'NO_SUPPORTED_PATTERN')
            and record['subject_text_included'] is False)
    require(all(type(record[k]) is type(v) and record[k] == v for k, v in expected_identity.items()))
    require(canonical_json(record['sources']) == canonical_json(sources)
            and canonical_json(record['limitations']) == canonical_json(limitations))
    original = record['original']
    object_fields(original, ['format', 'method', 'state', *COUNTS, *FALSE_FIELDS[:-1], 'tags',
        'subject_sha256', 'normalization_id', 'offset_unit', 'source_sha256', 'quote_spans',
        'outside_markerless_phrases', 'outside_marked_phrases', 'quoted_phrases',
        'subject_text_included', 'parameters'])
    require(original['format'] == 'authority-quotation-observation/v1'
            and original['method'] == METHOD and original['state'] == record['state']
            and original['subject_sha256'] == expected_identity['subject_sha256']
            and original['normalization_id'] == NORMALIZATION_ID
            and original['offset_unit'] == 'NFC_unicode_codepoint'
            and type(original['tags']) is list and original['tags'] == [])
    require(all(original[k] is False for k in FALSE_FIELDS))
    require(canonical_json(original['source_sha256']) == canonical_json({k: sources[k] for k in CANONICAL_SOURCES}))
    parameters = {'language': 'en', 'quote_grammar': 'balanced_unescaped_ASCII_double_quotes',
        'citation_scope': 'same_literal_unit_and_supported_quote_context',
        'max_quotes': 64, 'max_phrases': 128, 'max_units': 512, 'max_markers': 256}
    require(canonical_json(original['parameters']) == canonical_json(parameters))
    size = expected_identity['subject_characters']
    spans(original['quote_spans'], size, 64)
    object_fields(record['counts'], COUNTS)
    for key in COUNTS:
        require(type(original[key]) is int and 0 <= original[key] <= 128
                and type(record['counts'][key]) is int and record['counts'][key] == original[key])
    names = ('outside_markerless_phrases', 'outside_marked_phrases', 'quoted_phrases')
    phrase_count = 0
    for name in names:
        rows = original[name]
        require(type(rows) is list and len(rows) <= 128)
        phrase_count += len(rows)
        for row in rows:
            object_fields(row, ['phrase_span', 'unit_span', 'quote_span', 'source_marker_spans'])
            span(row['phrase_span'], size)
            span(row['unit_span'], size)
            require(row['unit_span'][0] <= row['phrase_span'][0] < row['phrase_span'][1] <= row['unit_span'][1])
            if name == 'quoted_phrases':
                span(row['quote_span'], size)
            else:
                require(row['quote_span'] is None)
            spans(row['source_marker_spans'], size, 256)
    require(phrase_count <= 128 and record['counts']['supported_quote_count'] == len(original['quote_spans']))
    for key, name in zip(COUNTS[:3], names):
        require(record['counts'][key] == len(original[name]))
    require((record['state'] == 'OBSERVATIONS') is bool(original['outside_markerless_phrases']))
    # No unknown field is removed, projected, logged or treated as evidence.
    require(len(canonical_json(record).encode()) <= MAX_RECORD_BYTES)
    return record


def replay(text, claimed, sources, limitations):
    # Executed in a bounded child. Comparing complete strict JSON also refuses
    # forged omissions and semantically moved evidence that passes shape checks.
    expected = produce(text, sources, limitations)
    require(canonical_json(expected) == canonical_json(claimed))
    return {'format': REPLAY_PROFILE, 'matches': True, **identity(text), 'sources': sources}


def expected_replay(text, sources):
    return {'format': REPLAY_PROFILE, 'matches': True, **identity(text), 'sources': sources}
