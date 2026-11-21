"""Bound original input and complete mobile quote evidence; never a tag."""
import hashlib
import json
from pathlib import Path
from protocol.normalization import normalize_nfc,NORMALIZATION_ID
from tools import authority_mobile_quotation
ROOT=Path(__file__).resolve().parents[1]
PROFILE='mt-device-mobile-authority/1.0.0'
SOURCES=('tools/mt_mobile_device.py',*authority_mobile_quotation.SOURCES)
MAX_RECORD_BYTES=100000

def inspect_mt_mobile_device(text):
    if not isinstance(text,str) or not text.strip() or len(text)>8000 or '\x00' in text:raise ValueError('Unsupported double-quote input.')
    raw=text.encode('utf-8','strict');normalized=normalize_nfc(text)
    if len(raw)>32000 or len(normalized)>8000:raise ValueError('Unsupported double-quote input.')
    brief,original=authority_mobile_quotation.observe(text,'en')
    counts={k:brief[k] for k in ('outside_supported_quotes_without_marker','outside_supported_quotes_with_marker','quoted_phrase_count','supported_quote_count')}
    value={'format':PROFILE,'check':'authority-curly','method':authority_mobile_quotation.METHOD,'state':original['state'],
           'counts':counts,'original':original,'raw_sha256':hashlib.sha256(raw).hexdigest(),'raw_characters':len(text),'raw_bytes':len(raw),
           'subject_sha256':hashlib.sha256(normalized.encode()).hexdigest(),'subject_characters':len(normalized),
           'normalization_id':NORMALIZATION_ID,'offset_unit':'NFC_unicode_codepoint',
           'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
           'tags':[],'tag_asserted':False,'intent_established':False,'truth_established':False,
           'independent_accuracy_evidence':False,'subject_text_included':False}
    encoded=json.dumps(value,ensure_ascii=True,allow_nan=False,separators=(',',':'))
    if len(encoded.encode())>MAX_RECORD_BYTES:raise ValueError('Double-quote evidence exceeds the budget.')
    return encoded
