"""On-device literal quantitative observations; no HP assertion or text storage."""
import hashlib
import json
from pathlib import Path
from protocol.normalization import normalize_nfc, NORMALIZATION_ID
from tools import quantitative_observations as quantitative

ROOT=Path(__file__).resolve().parents[1]
PROFILE='hp-literal-detail-explorer/1.0.0'
METHOD='literal-quantitative-observations/1.0.1'
SOURCE_FILES=('tools/hp_device.py','tools/quantitative_observations.py','tools/language_observations.py',
              'protocol/normalization.py','protocol/unicode15-data.json','protocol/corpus.py')
MAX_RECORD_BYTES=262144


def inspect_hp_device(text):
    if not isinstance(text,str) or not text.strip() or len(text)>8000 or '\0' in text:
        raise ValueError('Unsupported literal-detail input.')
    raw=text.encode('utf-8','strict')
    if len(raw)>32000:raise ValueError('Unsupported literal-detail input.')
    normalized=normalize_nfc(text)
    if len(normalized)>8000:raise ValueError('Unsupported literal-detail input.')
    brief,original=quantitative.observe(text,'en')
    if original['method']!=METHOD:raise ValueError('Unexpected literal-detail method.')
    # Preserve the canonical private-record budget. Never clip its evidence rows.
    if len(json.dumps(original,ensure_ascii=True,allow_nan=False,indent=2).encode())>quantitative.MAX_REPORT_BYTES:
        raise ValueError('Literal-detail record exceeds the preview budget.')
    value={'format':PROFILE,'method':METHOD,'state':original['state'],
      'counts':{name:brief[name] for name in ('supported_detail_count','without_same_unit_marker','with_same_unit_marker','skipped_detail_count')},
      'original':original,'raw_sha256':hashlib.sha256(raw).hexdigest(),'raw_characters':len(text),'raw_bytes':len(raw),
      'subject_sha256':hashlib.sha256(normalized.encode()).hexdigest(),'subject_characters':len(normalized),
      'normalization_id':NORMALIZATION_ID,'offset_unit':'NFC_unicode_codepoint',
      'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCE_FILES},
      'tags':[],'tag_asserted':False,'truth_established':False,'source_support_established':False,
      'independent_accuracy_evidence':False,'subject_text_included':False}
    encoded=json.dumps(value,ensure_ascii=True,allow_nan=False,separators=(',',':'))
    if len(encoded.encode())>MAX_RECORD_BYTES:raise ValueError('Literal-detail record exceeds the preview budget.')
    return encoded
