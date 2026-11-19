"""Candidate observations for authority phrases in balanced ASCII double quotes."""
import hashlib
from pathlib import Path

from protocol.corpus import CorpusError
from protocol.normalization import NORMALIZATION_ID
from tools.language_observations import AUTHORITY, SOURCE_MARKER, subject_text, units

ROOT = Path(__file__).resolve().parents[1]
METHOD = 'ascii-quoted-authority-observations/1.0.0'
MAX_QUOTES = 64
MAX_PHRASES = 128
MAX_UNITS = 512
MAX_MARKERS = 256
SOURCES = ('tools/authority_quotation.py', 'scripts/authority-quotation.py',
           'tools/language_observations.py', 'protocol/normalization.py',
           'protocol/unicode15-data.json', 'protocol/corpus.py', 'tools/blind_review_io.py')


def require(value):
    if not value:
        raise CorpusError('Supported authority quotation context is unavailable.')


def quoted_ranges(subject):
    quotes = []
    opening = None
    for index, character in enumerate(subject):
        require(character not in '\u201c\u201d\u00ab\u00bb`')
        if character != '"':
            continue
        require(index == 0 or subject[index - 1] != '\\')
        if opening is None:
            opening = index
        else:
            require(len(quotes) < MAX_QUOTES)
            quotes.append([opening, index + 1])
            opening = None
    require(opening is None)
    return quotes


def sources():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}


def observe(original, language):
    text = subject_text(original, language)
    require(len(text.encode('utf-8')) <= 32000)
    quotes = quoted_ranges(text)
    sentences = units(text)
    require(len(sentences) <= MAX_UNITS)
    observations = []
    quoted = []
    marked = []
    phrase_count = 0
    marker_count = 0
    for start, end in sentences:
        # Intersect the unit with each quoted/plain segment before scanning.
        # A URL match therefore cannot consume a closing quote or borrow text
        # from a different quotation context.
        segments = []
        position = start
        for quote_start, quote_end in quotes:
            if quote_end <= start or quote_start >= end:
                continue
            if position < quote_start:
                segments.append((position, quote_start, None))
            content_start = max(start, quote_start + 1)
            content_end = min(end, quote_end - 1)
            if content_start < content_end:
                segments.append((content_start, content_end, [quote_start, quote_end]))
            position = min(end, quote_end)
        if position < end:
            segments.append((position, end, None))

        local_markers = []
        phrase_segments = []
        for segment_start, segment_end, quote in segments:
            markers = [[match.start(), match.end()] for match in SOURCE_MARKER.finditer(text, segment_start, segment_end)]
            marker_count += len(markers)
            require(marker_count <= MAX_MARKERS)
            if quote is None:
                local_markers.extend(markers)
            phrase_segments.append((segment_start, segment_end, quote, markers))

        for segment_start, segment_end, quote, markers in phrase_segments:
            for match in AUTHORITY.finditer(text, segment_start, segment_end):
                phrase_count += 1
                require(phrase_count <= MAX_PHRASES)
                applicable = markers if quote is not None else local_markers
                row = {'phrase_span': [match.start(), match.end()], 'unit_span': [start, end],
                       'quote_span': quote, 'source_marker_spans': applicable}
                if quote is not None:
                    quoted.append(row)
                elif applicable:
                    marked.append(row)
                else:
                    observations.append(row)
    common = {
        'format': 'authority-quotation-observation/v1', 'method': METHOD,
        'state': 'OBSERVATIONS' if observations else 'NO_SUPPORTED_PATTERN',
        'outside_supported_quotes_without_marker': len(observations),
        'outside_supported_quotes_with_marker': len(marked), 'quoted_phrase_count': len(quoted),
        'supported_quote_count': len(quotes), 'source_lookup_performed': False,
        'quote_endorsement_interpreted': False, 'negation_interpreted': False,
        'semantic_attribution_interpreted': False, 'intent_established': False,
        'truth_established': False, 'independent_accuracy_evidence': False,
        'network_used': False, 'tags': [],
    }
    details = {
        **common, 'subject_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
        'normalization_id': NORMALIZATION_ID, 'offset_unit': 'NFC_unicode_codepoint',
        'source_sha256': sources(), 'quote_spans': quotes,
        'outside_markerless_phrases': observations, 'outside_marked_phrases': marked,
        'quoted_phrases': quoted, 'subject_text_included': False,
        'parameters': {'language': 'en', 'quote_grammar': 'balanced_unescaped_ASCII_double_quotes',
                       'citation_scope': 'same_literal_unit_and_supported_quote_context',
                       'max_quotes': MAX_QUOTES, 'max_phrases': MAX_PHRASES,
                       'max_units': MAX_UNITS, 'max_markers': MAX_MARKERS},
    }
    return common, details
