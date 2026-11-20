"""On-device wrapper for canonical static Python flow; never executes the subject."""
import hashlib
import json
from pathlib import Path
from protocol.normalization import normalize_nfc, NORMALIZATION_ID
from tools import credential_flow

ROOT=Path(__file__).resolve().parents[1]
PROFILE='credential-flow-device/1.0.0'
METHOD='python-credential-flow-observation/1.0.2'
SOURCE_FILES=('tools/credential_device.py','tools/credential_flow.py',
              'protocol/normalization.py','protocol/unicode15-data.json','protocol/corpus.py')
MAX_RECORD_BYTES=262144


def inspect_credential_device(text):
    if not isinstance(text,str) or not text.strip() or len(text)>8000 or '\0' in text:
        raise ValueError('Unsupported Python flow input.')
    raw=text.encode('utf-8','strict')
    if len(raw)>32000:raise ValueError('Unsupported Python flow input.')
    normalized=normalize_nfc(text)
    if len(normalized)>8000:raise ValueError('Unsupported Python flow input.')
    original=credential_flow.observe(text)
    if original['method']!=METHOD:raise ValueError('Unexpected Python flow method.')
    value={'format':PROFILE,'method':METHOD,'state':original['state'],
      'counts':{'recognized_reads':len(original['recognized_read_spans']),'static_flows':len(original['findings'])},
      'original':original,'raw_sha256':hashlib.sha256(raw).hexdigest(),'raw_characters':len(text),'raw_bytes':len(raw),
      'subject_sha256':hashlib.sha256(normalized.encode()).hexdigest(),'subject_characters':len(normalized),
      'normalization_id':NORMALIZATION_ID,'offset_unit':'NFC_unicode_codepoint',
      'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCE_FILES},
      'tags':[],'tag_asserted':False,'safety_established':False,'context_classified':False,
      'independent_accuracy_evidence':False,'subject_text_included':False}
    encoded=json.dumps(value,ensure_ascii=True,allow_nan=False,separators=(',',':'))
    if len(encoded.encode())>MAX_RECORD_BYTES:raise ValueError('Python flow record exceeds the preview budget.')
    return encoded
