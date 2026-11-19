"""Local browser adapter around unchanged MT observation methods; never a tag."""
import hashlib
import json
from pathlib import Path
from protocol.normalization import normalize_nfc, NORMALIZATION_ID
from tools import language_observations

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'mt-device-phrase-explorer/1.0.0'
SOURCE_FILES = ('tools/mt_device.py', 'tools/language_observations.py', 'tools/authority_quotation.py',
                'protocol/normalization.py', 'protocol/unicode15-data.json', 'protocol/corpus.py',
                'tools/blind_review_io.py', 'scripts/authority-quotation.py')
METHODS = {'urgency':'english-context-observations/1.1.0',
           'authority':'ascii-quoted-authority-observations/1.0.0'}


def inspect_mt_device(kind, text):
    if (kind not in METHODS or not isinstance(text,str) or not text.strip() or
            len(text)>8000 or '\x00' in text or len(text.encode('utf-8','strict'))>32000):
        raise ValueError('Unsupported MT phrase input.')
    normalized = normalize_nfc(text)
    if len(normalized)>8000: raise ValueError('Unsupported MT phrase input.')
    if kind == 'urgency':
        original = language_observations.observe('urgency',text,language='en')
        counts = {'finding_groups':len(original['findings']),
                  'paired_units':len(original['measurements']['paired_units'])}
    else:
        from tools import authority_quotation
        brief,original = authority_quotation.observe(text,'en')
        counts = {name:brief[name] for name in ('outside_supported_quotes_without_marker',
                  'outside_supported_quotes_with_marker','quoted_phrase_count','supported_quote_count')}
    if original['method'] != METHODS[kind]: raise ValueError('Unexpected MT phrase method.')
    return json.dumps({'format':PROFILE,'check':kind,'method':METHODS[kind],
        'state':original['state'],'counts':counts,'original':original,
        'subject_sha256':hashlib.sha256(normalized.encode()).hexdigest(),
        'normalization_id':NORMALIZATION_ID,'offset_unit':'NFC_unicode_codepoint',
        'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCE_FILES},
        'tags':[],'intent_established':False,'truth_established':False,
        'independent_accuracy_evidence':False,'subject_text_included':False},
        ensure_ascii=True,allow_nan=False,separators=(',',':'))
