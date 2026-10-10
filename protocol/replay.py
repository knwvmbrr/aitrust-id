"""Repeat a current unsigned assertion through the explicitly selected local service."""
import hashlib
from pathlib import Path
import httpx
from protocol.assertions import validator
from protocol.replay_identity import PipelineIdentity
ROOT=Path(__file__).resolve().parents[1]
LOCAL_GATEWAY='http://127.0.0.1:8787/v1/evaluate'
MAX_RESPONSE=2_000_000


def outcome(status,reason,**extra):
    return {'status':status,'reason':reason,'input_scope':'owner_supplied_original_text',
            'local_service_only':True,'tool_retains_input':False,
            'signature_verified':False,'independent_accuracy_verified':False,**extra}


def inspect_record(record,root=ROOT):
    if record.get('spec_version')!='0.1.0':
        return outcome('unavailable','unsupported_wire_version')
    if not validator().is_valid(record):
        return outcome('invalid','invalid_assertion')
    if record.get('signature'):
        return outcome('unavailable','signature_trust_not_supported')
    if record['subject']['modality']!='text':
        return outcome('unavailable','unsupported_modality')
    raw=record['evaluator'].get('preprocessing')
    if raw is None:return outcome('unavailable','historical_preprocessing_identity_missing')
    try:identity=PipelineIdentity.model_validate(raw)
    except ValueError:return outcome('invalid','invalid_preprocessing_identity')
    config=identity.configuration
    hashes={
        root/'services/gateway/app.py':config.gateway_source_sha256,
        root/'protocol/normalization.py':config.normalization_source_sha256,
        root/'protocol/unicode15-data.json':config.normalization_data_sha256,
        root/'services/anonymizer/app.py':config.redactor.configuration.sources.app,
        root/'services/anonymizer/model_identity.py':config.redactor.configuration.sources.model_loader,
        root/'services/anonymizer/replay_metadata.py':config.redactor.configuration.sources.identity_builder,
        root/'protocol/replay_identity.py':config.redactor.configuration.sources.identity_contract,
        root/'services/anonymizer/requirements.lock':config.redactor.configuration.sources.requirements_lock,
    }
    if any(hashlib.sha256(file.read_bytes()).hexdigest()!=sha for file,sha in hashes.items()):
        return outcome('unavailable','historical_or_different_pipeline_sources')
    models=record['evaluator']['models']
    expected=[{'name':'presidio-redaction','revision':config.redactor.version,'sha256':config.redactor.sha256},
              {'name':'gateway-pipeline','revision':identity.version,'sha256':identity.sha256}]
    if len(models)!=3 or models[1:]!=expected:
        return outcome('invalid','inconsistent_pipeline_models')
    if (models[0].get('name')!='rules-only' or models[0].get('revision')!='context-v6'
            or models[0].get('sha256')!=hashlib.sha256((root/'services/evaluator/app.py').read_bytes()).hexdigest()):
        return outcome('unavailable','historical_or_different_detector')
    return None


def compare(expected,actual):
    if not validator().is_valid(actual):return outcome('unavailable','invalid_local_reply')
    try:PipelineIdentity.model_validate(actual['evaluator'].get('preprocessing'))
    except ValueError:return outcome('unavailable','invalid_local_identity')
    e,a=expected['evaluator'],actual['evaluator']
    if any(e.get(k)!=a.get(k) for k in ['models','preprocessing','calibration_id']):
        return outcome('unavailable','local_method_identity_differs',identity_matched=False)
    if any(expected['subject'][k]!=actual['subject'][k] for k in ['sha256','char_len']):
        return outcome('input_mismatch','redacted_subject_differs',identity_matched=True)
    if any(expected.get(k,[])!=actual.get(k,[]) for k in ['tags','abstentions']):
        return outcome('mismatch','findings_differ',identity_matched=True)
    return outcome('matched','same_versioned_pipeline_and_findings',identity_matched=True,
                   tags_checked=len(actual['tags']),abstentions_checked=len(actual.get('abstentions',[])))


def replay(record,text,token,*,root=ROOT,transport=None):
    refused=inspect_record(record,root)
    if refused:return refused
    if (not isinstance(text,str) or not 1<=len(text)<=200_000
            or any(0xD800<=ord(c)<=0xDFFF for c in text)):
        return outcome('invalid','invalid_source_text')
    if (not isinstance(token,str) or not 16<=len(token)<=256 or not token.isascii()
            or any(c.isspace() or ord(c)<33 or ord(c)>126 for c in token)):
        return outcome('unavailable','invalid_local_credential')
    # Neither an assertion nor an environment variable can choose a destination.
    # The optional transport is an in-process test seam, never a CLI option.
    try:
        with httpx.Client(timeout=20,trust_env=False,follow_redirects=False,transport=transport) as client:
            with client.stream('POST',LOCAL_GATEWAY,headers={'Authorization':'Bearer '+token},
                    json={'text':text,'origin_host':record['subject']['origin_host'],'modality':'text'}) as response:
                if response.status_code!=200:return outcome('unavailable','local_service_unavailable')
                raw=bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw)>MAX_RESPONSE:return outcome('unavailable','local_reply_limit')
        import json
        from protocol.evidence import unique,reject,finite
        actual=json.loads(bytes(raw).decode('utf-8',errors='strict'),object_pairs_hook=unique,parse_constant=reject)
        finite(actual)
        if not isinstance(actual,dict):return outcome('unavailable','invalid_local_reply')
        return compare(record,actual)
    except (httpx.HTTPError,UnicodeError,ValueError,KeyError,TypeError,RecursionError):
        return outcome('unavailable','local_service_unavailable')
