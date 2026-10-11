"""Independent English lexical observations; no truth, intent or tag verdict."""
import hashlib
import math
from pathlib import Path
import re
from protocol.corpus import CorpusError
from protocol.normalization import NORMALIZATION_ID, normalize_nfc

METHOD = 'english-context-observations/1.0.0'
MAX_CHARACTERS = 8000
MAX_ANNOTATIONS = 32
HEDGE = re.compile(r'\b(?:may|might|could|possibly|perhaps|probably|likely|unlikely|uncertain|unclear|approximately|roughly|estimated|estimate)\b', re.I)
PRESSURE = re.compile(r'\b(?:now|today|immediately|right away|last chance|act fast|before it is too late|within [0-9]{1,4} (?:minutes?|hours?))\b', re.I)
DIRECTIVE = re.compile(r'\s*(?:please\s+)?(?P<verb>act|buy|click|send|pay|transfer|sign|choose|join|call|run|install|download|stop|leave|evacuate|check|verify|read|submit|respond|decide|take)\b', re.I)
AUTHORITY = re.compile(r'\b(?:experts agree|studies show|research proves|scientists agree|everyone knows|doctors recommend|authorities say|according to (?:experts|science|research))\b', re.I)
SOURCE_MARKER = re.compile(r'https?://[^\s<>]+|\[[0-9]{1,4}\]', re.I)


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def subject_text(subject, language):
    if language != 'en' or not isinstance(subject, str) or not subject.strip() or len(subject) > MAX_CHARACTERS or '\x00' in subject:
        raise CorpusError('Supply supported English text within the limit.')
    try:
        subject.encode('utf-8', errors='strict')
    except UnicodeError:
        raise CorpusError('Subject must use valid Unicode.') from None
    normalized = normalize_nfc(subject)
    if len(normalized) > MAX_CHARACTERS:
        raise CorpusError('Normalized subject exceeds the limit.')
    return normalized


def annotations(value, subject):
    if value is None:
        return {'uncertainty': [], 'sources': []}
    if not isinstance(value, dict) or set(value) != {'format', 'subject_sha256', 'uncertainty', 'sources'} or value['format'] != 'language-context-annotations/v1' or value['subject_sha256'] != digest(subject):
        raise CorpusError('Annotations do not bind the selected subject.')
    for name in ('uncertainty', 'sources'):
        spans = value[name]
        if not isinstance(spans, list) or len(spans) > MAX_ANNOTATIONS:
            raise CorpusError('Too many or invalid context annotations.')
        previous = -1
        for span in spans:
            if not isinstance(span, list) or len(span) != 2 or any(type(n) is not int for n in span) or not 0 <= span[0] < span[1] <= len(subject) or span[0] < previous or not subject[span[0]:span[1]].strip():
                raise CorpusError('Context annotations require ordered nonoverlapping subject spans.')
            previous = span[1]
    return value


def units(subject):
    result = []
    for match in re.finditer(r'[^\n]+?(?:[.!?]+(?=\s|$)|(?=\n|$))', subject):
        if match.group().strip():
            result.append((match.start(), match.end()))
    return result


def overlap(span, candidates):
    return [value for value in candidates if max(span[0], value[0]) < min(span[1], value[1])]


def observe(kind, original, language='en', context=None, minimum_density=.5):
    if kind not in ('hedge', 'urgency', 'authority'):
        raise CorpusError('Unsupported language observation.')
    if type(minimum_density) not in (int, float) or not math.isfinite(minimum_density) or not 0 < minimum_density <= 1:
        raise CorpusError('Invalid directive-density threshold.')
    subject = subject_text(original, language)
    context = annotations(context, subject)
    findings, measurements = [], {}
    if kind == 'hedge':
        if not context['uncertainty']:
            raise CorpusError('Select where uncertainty is expected before checking hedges.')
        measured = []
        for start, end in context['uncertainty']:
            hedges = []
            calendar = []
            for match in HEDGE.finditer(subject, start, end):
                span = [match.start(), match.end()]
                if match.group().lower() == 'may' and re.match(r'\s+[0-9]{1,2}\b', subject[match.end():end]):
                    calendar.append(span)
                else:
                    hedges.append(span)
            measured.append({'expected_uncertainty_span': [start, end], 'hedge_spans': hedges,
                             'excluded_calendar_spans': calendar})
            if not hedges:
                findings.append({'id': 'sig.hedge_collapse.v1', 'spans': [[start, end]],
                                 'meaning': 'no_supported_hedge_in_caller_selected_uncertainty_span',
                                 'expectation_source': 'explicit_caller_annotation'})
        measurements = {'contexts': measured, 'expected_uncertainty_inferred': False,
                        'calendar_exclusion': 'may_followed_by_day_number_only',
                        'negation_interpreted': False}
    elif kind == 'urgency':
        sentence_units = units(subject)
        directives = []
        for start, end in sentence_units:
            found = DIRECTIVE.match(subject, start, end)
            if found:
                directives.append([found.start('verb'), found.end('verb')])
        pressure = [[m.start(), m.end()] for m in PRESSURE.finditer(subject)]
        density = len(directives)/len(sentence_units) if sentence_units else 0
        measurements = {'sentence_units': len(sentence_units), 'directive_units': len(directives),
                        'directive_density': density, 'minimum_density': minimum_density,
                        'directive_spans': directives, 'time_pressure_spans': pressure,
                        'grammatical_imperatives_verified': False}
        if pressure and directives and density >= minimum_density:
            findings.append({'id': 'sig.urgency_frame.v1', 'spans': sorted(set(map(tuple, pressure+directives))),
                             'meaning': 'lexical_time_pressure_with_supported_directive_density'})
    else:
        attributed = []
        for start, end in units(subject):
            markers = [[m.start(), m.end()] for m in SOURCE_MARKER.finditer(subject, start, end)]
            selected = overlap([start, end], context['sources'])
            for match in AUTHORITY.finditer(subject, start, end):
                detail = {'spans': [[match.start(), match.end()]], 'context_span': [start, end],
                          'source_marker_spans': markers, 'selected_source_spans': selected}
                if markers or selected:
                    attributed.append(detail)
                else:
                    findings.append({'id': 'sig.authority_appeal.v1', **detail,
                                     'meaning': 'supported_authority_phrase_without_same_unit_source_marker'})
        measurements = {'marked_appeals': attributed, 'citation_resolution_performed': False,
                        'sources_elsewhere_checked': False}
    return {'format': 'language-observation/v1', 'method': METHOD,
            'method_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'kind': kind, 'language': language, 'subject_sha256': digest(subject),
            'subject_characters': len(subject), 'normalization_id': NORMALIZATION_ID,
            'offset_unit': 'NFC_unicode_codepoint', 'state': 'OBSERVATIONS' if findings else 'NO_SUPPORTED_PATTERN',
            'findings': findings, 'measurements': measurements,
            'context_inferred': False, 'quoted_or_recommended_context_classified': False,
            'intent_established': False, 'truth_established': False, 'score_is_probability': False,
            'independent_accuracy_evidence': False, 'network_used': False, 'tags': []}
