"""Closed synthetic admission requests; no endpoint, credentials or telemetry."""
import base64
import hashlib
import json
import re

PROFILE = 'metadata-admission-development/v1'
MAX_BYTES = 4096
CHOICES = {
    'reported_result': ('pattern_found','no_pattern_found','unavailable','not_checked'),
    'failure_category': ('none_observed','unexpected_finding','possible_missed_pattern','could_not_check','unclear_result'),
    'feedback': ('easy_to_understand','needs_clearer_explanation','hard_to_use','could_not_complete'),
}
FIXED = {'schema_version': 1, 'purpose': 'PS_preview_usability_and_failure_review',
         'tag': 'PS', 'method_version': 'context-v6', 'sharing': 'local_file_not_submitted'}


class AdmissionError(ValueError):
    """Constant diagnostics never interpolate tokens, metadata or private paths."""


def require(condition):
    if not condition:
        raise AdmissionError('Synthetic admission refused')


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def digest_token(value):
    require(type(value) is str and re.fullmatch(r'[A-Za-z0-9_-]{43}',value) is not None)
    raw = base64.urlsafe_b64decode(value+'=')
    require(len(raw)==32 and base64.urlsafe_b64encode(raw).decode('ascii').rstrip('=')==value)
    return hashlib.sha256(raw).hexdigest()


def metadata(value):
    require(type(value) is dict and set(value)==set(FIXED)|set(CHOICES))
    for key, expected in FIXED.items():
        require(type(value[key]) is type(expected) and value[key]==expected)
    for key, allowed in CHOICES.items():
        require(type(value[key]) is str and value[key] in allowed)
    return value


def parse(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES)
    try:
        value=json.loads(raw.decode('utf-8','strict'),object_pairs_hook=unique,
                         parse_constant=lambda _: require(False))
        require(type(value) is dict)
        common={'format','synthetic','operation','withdrawal_token'}
        require(value.get('format')==PROFILE and value.get('synthetic') is True)
        operation=value.get('operation')
        require(type(operation) is str and operation in ('submit','withdraw'))
        require(set(value)==common|({'invitation_token','feedback'} if operation=='submit' else set()))
        withdrawal=digest_token(value['withdrawal_token'])
        if operation=='withdraw':
            return {'operation':operation,'withdrawal_digest':withdrawal}
        invitation=digest_token(value['invitation_token'])
        require(invitation!=withdrawal)
        envelope={'format':'metadata-storage-development/v1','synthetic':True,
                  'permission':'synthetic_test_only','feedback':metadata(value['feedback'])}
        return {'operation':operation,'withdrawal_digest':withdrawal,
                'invitation_digest':invitation,'envelope':envelope}
    except (UnicodeError,ValueError,TypeError,KeyError,RecursionError):
        raise AdmissionError('Synthetic admission refused') from None


def statement(raw):
    """Fixed SQL, hex-only data, no bearer plaintext or untrusted SQL syntax."""
    request=parse(raw)
    token="decode('"+request['withdrawal_digest']+"','hex')"
    if request['operation']=='withdraw':
        call='metadata_dev.withdraw_synthetic('+token+')'
        query="SELECT json_build_object('operation','withdraw','removed',"+call+");"
    else:
        encoded=json.dumps(request['envelope'],sort_keys=True,separators=(',',':'),
                           ensure_ascii=True,allow_nan=False).encode().hex()
        body="convert_from(decode('"+encoded+"','hex'),'UTF8')"
        invite="decode('"+request['invitation_digest']+"','hex')"
        call='metadata_dev.record_invited_synthetic('+body+','+token+','+invite+')'
        query="SELECT json_build_object('operation','submit','feedback_id',"+call+");"
    return "BEGIN; SET LOCAL ROLE ait_metadata_intake;\n"+query+"\nCOMMIT;\n"
