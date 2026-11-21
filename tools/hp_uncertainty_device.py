"""Caller-selected whole-passage hedge words. No HP/uncertainty/truth inference."""
import hashlib
import json
from pathlib import Path
import re
from protocol.normalization import normalize_nfc, NORMALIZATION_ID
from protocol.corpus import unique_pairs
from tools import language_observations as canonical

ROOT=Path(__file__).resolve().parents[1]
PROFILE='hp-explicit-uncertainty-device/1.0.0'
METHOD='english-context-observations/1.0.0'
BOUNDARY='hp-uncertainty-safe-boundaries/v1'
SOURCES=('tools/hp_uncertainty_device.py','tools/language_observations.py','protocol/corpus.py',
         'protocol/normalization.py','protocol/unicode15-data.json')
MAX_RECORD_BYTES=262144
# These assigned nonword punctuation points are stable, not a full Unicode table.
SAFE_PUNCTUATION='\u2018\u2019\u201c\u201d\u00ab\u00bb\u2013\u2014\u2026'
CANDIDATE=re.compile(canonical.HEDGE.pattern.removeprefix(r'\b').removesuffix(r'\b'),canonical.HEDGE.flags)


def need(value):
    if not value:raise ValueError('Uncertainty wording unavailable.')


def safe_boundary(char):return ord(char)<128 or char.isspace() or char in SAFE_PUNCTUATION


def supported_boundary(text):
    """Refuse ambiguous potential lexical/calendar edges, never silently omit them."""
    for match in CANDIDATE.finditer(text):
        left,right=match.span()
        need(match.group().isascii())
        for index in (left-1,right):
            if 0<=index<len(text):need(safe_boundary(text[index]))
        if match.group().lower()=='may':
            end=right
            while end<len(text) and text[end].isspace():end+=1
            digits=re.match(r'[0-9]{1,2}',text[end:])
            if digits:
                after=end+len(digits.group())
                if after<len(text):need(safe_boundary(text[after]))


def inspect_hp_uncertainty_device(text,annotation_json):
    need(type(text) is str and bool(text.strip()) and '\0' not in text and len(text)<=8000)
    raw=text.encode('utf-8','strict');normalized=normalize_nfc(text)
    need(len(raw)<=32000 and 0<len(normalized)<=8000)
    supported_boundary(normalized)
    need(type(annotation_json) is str and 0<len(annotation_json.encode('utf-8','strict'))<=1024)
    annotation=json.loads(annotation_json,object_pairs_hook=unique_pairs,parse_constant=lambda _:need(False))
    expected={'format':'language-context-annotations/v1','subject_sha256':canonical.digest(normalized),
              'uncertainty':[[0,len(normalized)]],'sources':[]}
    # Exact serialized types distinguish bool/int aliases and reject private extras.
    need(json.dumps(annotation,sort_keys=True,allow_nan=False,separators=(',',':'))==
         json.dumps(expected,sort_keys=True,separators=(',',':')))
    original=canonical.observe('hedge',text,'en',context=annotation)
    need(original['method']==METHOD)
    measured=original['measurements']['contexts'][0]
    result={'format':PROFILE,'method':METHOD,'boundary':BOUNDARY,'state':original['state'],
            'raw_sha256':hashlib.sha256(raw).hexdigest(),'raw_bytes':len(raw),'raw_characters':len(text),
            'subject_sha256':canonical.digest(normalized),'subject_characters':len(normalized),
            'normalization_id':NORMALIZATION_ID,'offset_unit':'NFC_unicode_codepoint',
            'annotation':expected,'annotation_source':'explicit_caller_whole_passage',
            'counts':{'hedge_words':len(measured['hedge_spans']),'calendar_candidates':len(measured['excluded_calendar_spans'])},
            'original':original,'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
            'tags':[],'tag_asserted':False,'uncertainty_needed_established':False,'truth_established':False,
            'independent_accuracy_evidence':False,'subject_text_included':False,'input_persisted':False}
    encoded=json.dumps(result,ensure_ascii=True,sort_keys=True,allow_nan=False,separators=(',',':'))
    need(len(encoded.encode())<=MAX_RECORD_BYTES)
    return encoded
