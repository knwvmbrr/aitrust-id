"""Caller-declared browser practice using the unchanged choice-framing method."""
import hashlib
import json
from pathlib import Path
from protocol import corpus
from protocol.normalization import normalize_nfc, NORMALIZATION_ID
from tools import choice_framing

ROOT=Path(__file__).resolve().parents[1]
PROFILE='mt-selected-choice-device/1.0.0'
METHOD='caller-bound-choice-framing-observation/1.3.0'
SOURCE_FILES=('tools/mt_choice_device.py','tools/choice_framing.py',
              'tools/language_observations.py','protocol/corpus.py',
              'protocol/normalization.py','protocol/unicode15-data.json')
MAX_REQUEST_BYTES=24000
MAX_RESULT_BYTES=65536


def need(ok):
    if not ok:raise ValueError('Selected wording practice unavailable.')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def field(value,characters,bytes_limit):
    need(type(value)is str and bool(value.strip()) and '\0'not in value and len(value)<=characters)
    raw=value.encode('utf-8','strict');need(len(raw)<=bytes_limit)
    normalized=normalize_nfc(value);need(len(normalized)<=characters)
    return raw,normalized


def inspect_mt_choice(request):
    need(type(request)is str and len(request.encode('utf-8','strict'))<=MAX_REQUEST_BYTES)
    value=json.loads(request,object_pairs_hook=corpus.unique_pairs,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Selected wording practice unavailable.')))
    need(type(value)is dict and set(value)=={'subject','first','second','reference','whole_frame'}
         and value['whole_frame']is True)
    raw,text=field(value['subject'],2000,8000)
    ref_raw,reference=field(value['reference'],2000,8000)
    selected=[]
    for name in ('first','second'):
        item_raw,item=field(value[name],256,1024)
        at=text.find(item);need(at>=0 and text.find(item,at+1)==-1)
        selected.append([at,at+len(item)])
    need(selected[0][1]<=selected[1][0])
    source={'id':'practice-reference','text':value['reference'],'sha256':sha(ref_raw)}
    content={'format':corpus.VERSION,'documents':[source]}
    record={**content,'manifest_sha256':sha(corpus.encoded(content))}
    context={'format':'choice-frame-context/v1','language':'en','subject_sha256':sha(text.encode()),
        'manifest_sha256':record['manifest_sha256'],'frames':[{'span':[0,len(text)],'choices':selected,
        'additional_reference':{'document_id':'practice-reference','document_sha256':source['sha256'],
                                'source_span':[0,len(reference)]}}]}
    original=choice_framing.observe(value['subject'],record,context)
    need(original['profile']==METHOD)
    additive=sum(row['construction']=='not_only_but_also'for row in original['observations'])
    result={'format':PROFILE,'method':METHOD,'state':original['state'],
        'request_sha256':sha(request.encode()),'raw_subject_sha256':sha(raw),
        'raw_subject_characters':len(value['subject']),'raw_subject_bytes':len(raw),
        'subject_sha256':sha(text.encode()),'subject_characters':len(text),
        'reference':{'raw_sha256':sha(ref_raw),'normalized_sha256':sha(reference.encode()),
                     'raw_characters':len(value['reference']),'normalized_characters':len(reference)},
        'item_request_sha256':{name:sha(value[name].encode())for name in ('first','second')},
        'counts':{'matched_frames':len(original['observations']),'additive_frames':additive,
                  'other_paired_frames':len(original['observations'])-additive,
                  'unmatched_frames':len(original['unmatched_selected_frames'])},
        'normalization_id':NORMALIZATION_ID,'span_units':'NFC_unicode_codepoints',
        'selection':'caller_declared_whole_frame_and_unique_literal_items',
        'original':original,'source_sha256':{name:sha((ROOT/name).read_bytes())for name in SOURCE_FILES},
        'tags':[],'intent_established':False,'truth_established':False,'independent_accuracy_evidence':False,
        'additional_option_verified':False,'subject_or_reference_text_included':False}
    encoded=json.dumps(result,ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False)
    need(len(encoded.encode())<=MAX_RESULT_BYTES)
    return encoded
