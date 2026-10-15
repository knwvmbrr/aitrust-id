"""Optional organization-owned metadata history; never an accuracy or identity claim."""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import uuid

from protocol.assertions import validator
from protocol.evidence import unique, reject, finite

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'organization-audit-metadata/v1'
SCHEMA = ROOT/'spec/organization-audit-metadata.schema.json'
HASH = re.compile(r'[a-f0-9]{64}')
CODES = {'NF','FI','HP','MT','PS','IV','FA','PA','UNK','PII_REDACTED'}
REASONS = {'below_floor','no_corpus','unsupported_modality','timeout','not_in_production_allowlist'}


def require(ok):
    if not ok:
        raise ValueError('Unsupported organization audit record')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False,separators=(',',':')).encode()


def parse(raw, limit=2_000_000):
    require(type(raw) is bytes and 0 < len(raw) <= limit)
    value=json.loads(raw.decode('utf-8','strict'),object_pairs_hook=unique,parse_constant=reject)
    finite(value); require(type(value) is dict)
    return value


def fixed(value, allowed, required=None):
    require(type(value) is dict and set(value)<=set(allowed)
            and set(required if required is not None else allowed)<=set(value))


def hash_value(value):
    require(type(value) is str and HASH.fullmatch(value))
    return value


def number(value, nullable=False):
    if value is None and nullable:return None
    require(type(value) in (int,float) and math.isfinite(value) and 0<=value<=1)
    return value


def uuid_value(value):
    if value is None:return None
    require(type(value) is str and str(uuid.UUID(value))==value)
    return value


def capture_time(value):
    if value is None:return None
    require(type(value) is str)
    stamp=datetime.fromisoformat(value.replace('Z','+00:00'));require(stamp.tzinfo is not None)
    return stamp.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')


def tags_metadata(tags, length):
    require(type(tags) is list and len(tags)<=10)
    result=[];seen=set();total=0
    for tag in tags:
        fixed(tag,{'code','confidence','floor','state','signals'}, {'code','confidence','signals'})
        code=tag['code'];require(code in CODES and code not in seen);seen.add(code)
        require('state' not in tag or tag['state']=='asserted')
        signals=tag['signals'];require(type(signals) is list and 1<=len(signals)<=64)
        output=[]
        for signal in signals:
            fixed(signal,{'id','score','spans','detail'},{'id','score'})
            require(type(signal['id']) is str and re.fullmatch(r'[a-z0-9_.]+[.]v[0-9]+',signal['id'])
                    and len(signal['id'])<=128)
            spans=signal.get('spans',[]);require(type(spans) is list and len(spans)<=256)
            for span in spans:
                require(type(span) is list and len(span)==2 and all(type(n) is int for n in span)
                        and 0<=span[0]<span[1]<=length)
            total+=len(spans);require(total<=4096)
            count=None
            if 'detail' in signal:
                require(code=='PII_REDACTED' and signal['id']=='presidio.entity.v1')
                detail=signal['detail'];fixed(detail,{'count','entities'})
                count=detail['count'];require(type(count) is int and 0<=count<=200000)
                require(type(detail['entities']) is list and len(detail['entities'])<=64
                        and all(type(v) is str and re.fullmatch(r'[A-Z][A-Z0-9_]{0,63}',v) for v in detail['entities']))
            output.append({'id':signal['id'],'score':number(signal['score']),'spans':spans,'redaction_count':count})
        result.append({'code':code,'confidence':number(tag['confidence']),
                       'floor':number(tag.get('floor'),True),'signals':output})
    return result


def validate_metadata(value):
    validator(json.loads(SCHEMA.read_text())).validate(value)
    # These cross-field constraints also execute in the PostgreSQL admission path.
    require(len(encoded(value))<=65536)
    require(len({v['code'] for v in value['tags']})==len(value['tags'])
            and len({v['code'] for v in value['abstentions']})==len(value['abstentions'])
            and not ({v['code'] for v in value['tags']}&{v['code'] for v in value['abstentions']}))
    expected='FINDING' if value['tags'] else 'UNCERTAIN' if value['abstentions'] else 'NO_FINDING'
    require(value['result_state']==expected)
    total=0
    for tag in value['tags']:
        for signal in tag['signals']:
            require(re.fullmatch(r'[a-z0-9_.]+[.]v[0-9]+',signal['id']))
            for a,b in signal['spans']:require(0<=a<b<=value['subject_char_len'])
            total+=len(signal['spans'])
    require(total<=4096)
    return value


def prepare(raw):
    source=parse(raw);profile=source.get('format');record_id=None;captured=None;preprocessing=None
    if source.get('spec_version')=='0.1.0':
        validator().validate(source)
        require(source['subject']['modality']=='text')
        subject=source['subject'];evaluator=source['evaluator'];models=evaluator['models']
        tags=source['tags'];abstentions=source['abstentions'];calibration=evaluator['calibration_id']
        record_id=source['assertion_id'];captured=subject['captured_at'];length=subject['char_len']
        normalization=subject.get('normalization');preprocessing=evaluator.get('preprocessing')
        profile='gateway-wire-0.1.0'
    elif profile=='ai-trust-id-device-preview/v1':
        allowed={'format','state','subject','candidates','models','calibration_id','redaction_performed',
                 'independently_validated','training_label','label_status','text_included',
                 'device_runtime','bundle_sha256','record_id'}
        fixed(source,allowed,allowed-{'device_runtime','bundle_sha256','record_id'})
        require(source['redaction_performed'] is False and source['independently_validated'] is False
                and source['text_included'] is False and source['training_label'] is None
                and source['label_status']=='unreviewed_prediction')
        if 'bundle_sha256' in source:hash_value(source['bundle_sha256'])
        if 'device_runtime' in source:require(type(source['device_runtime']) is str and re.fullmatch(r'[0-9]+[.][0-9]+[.][0-9]+',source['device_runtime']))
        subject=source['subject'];fixed(subject,{'sha256','codepoint_count','normalization'})
        length=subject['codepoint_count'];normalization=subject['normalization']
        models=source['models'];tags=source['candidates'];abstentions=[];calibration=source['calibration_id']
        require(type(length) is int and 1<=length<=20000)
        require(type(tags) is list and len(tags)<=1 and all(t.get('code')=='PS' for t in tags))
        require(source['state']==('FINDING' if tags else 'NO_FINDING'))
        record_id=source.get('record_id');profile='device-preview-v1'
    elif profile=='ai-trust-id-result-export/v1':
        fixed(source,{'format','exported_at','result_state','selected_tag','assertion_id','subject','evaluator',
                      'tags','redaction_summary','abstentions','training_label','review_status','delivery'})
        require(source['training_label'] is None and source['review_status']=='unreviewed_detector_output'
                and source['delivery']=='local_download_only')
        subject=source['subject'];fixed(subject,{'modality','sha256','char_len','origin_host','captured_at','normalization'},
                                      {'modality','sha256','char_len','origin_host','captured_at'})
        require(subject['modality']=='text')
        evaluator=source['evaluator'];fixed(evaluator,{'calibration_id','models'})
        models=evaluator['models'];tags=source['tags'];abstentions=source['abstentions']
        calibration=evaluator['calibration_id'];record_id=source['assertion_id'];captured=subject['captured_at']
        length=subject['char_len'];normalization=subject.get('normalization')
        capture_time(source['exported_at'])
        require(source['selected_tag'] is None or source['selected_tag'] in CODES)
        if source['selected_tag'] is not None:require(all(t.get('code')==source['selected_tag'] for t in tags))
        require(type(source['redaction_summary']) is list and len(source['redaction_summary'])<=10)
        for summary in source['redaction_summary']:
            fixed(summary,{'count','entities'})
            require(summary['count'] is None or type(summary['count']) is int and 0<=summary['count']<=200000)
            require(type(summary['entities']) is list and len(summary['entities'])<=64
                    and all(type(v) is str and re.fullmatch(r'[A-Z_]{1,64}',v) for v in summary['entities']))
        # Selected-tag exports are intentionally partial; preserve their claim without filling gaps.
        require(source['result_state']==('FINDING' if tags else 'UNCERTAIN' if abstentions else 'NO_FINDING'))
        profile='extension-export-v1'
    else:
        raise ValueError('Unsupported organization audit source')
    require(type(length) is int and 1<=length<=200000)
    hash_value(subject['sha256'])
    require(normalization is None or type(normalization) is str and 1<=len(normalization)<=256)
    require(type(calibration) is str and 1<=len(calibration)<=256)
    require(type(models) is list and 1<=len(models)<=16)
    method_hashes=[]
    for model in models:
        fixed(model,{'name','revision','sha256'})
        require(all(type(model[k]) is str and 0<len(model[k])<=256 for k in ('name','revision')))
        method_hashes.append(hash_value(model['sha256']))
    require(type(abstentions) is list and len(abstentions)<=10)
    withheld=[]
    for a in abstentions:
        fixed(a,{'code','confidence','floor','reason'},{'code','floor','reason'})
        require(a['code'] in CODES and a['reason'] in REASONS)
        withheld.append({'code':a['code'],'confidence':number(a.get('confidence'),True),
                         'floor':number(a['floor'],True),'reason':a['reason']})
    tags=tags_metadata(tags,length)
    value={'profile':PROFILE,'source_profile':profile,'source_record_sha256':digest(raw),
           'source_record_id':uuid_value(record_id),'subject_sha256':subject['sha256'],'subject_char_len':length,
           'reported_capture_at':capture_time(captured),'normalization_sha256':digest(normalization.encode()) if normalization else None,
           'preprocessing_sha256':digest(encoded(preprocessing)) if preprocessing is not None else None,
           'calibration_sha256':digest(calibration.encode()),'method_sha256':sorted(set(method_hashes)),
           'result_state':'FINDING' if tags else 'UNCERTAIN' if withheld else 'NO_FINDING',
           'tags':tags,'abstentions':withheld,
           'redaction_counts':([s['count'] for s in source['redaction_summary']] if profile=='extension-export-v1' else []),
           'source_authenticity_verified':False,
           'independent_accuracy_verified':False,'tag_release_approved':False,'text_included':False}
    return validate_metadata(value)
