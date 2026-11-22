"""Accepted offline assertion conversion; no detector, signature or trust claim."""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
from protocol.evidence import unique, reject

ROOT=Path(__file__).resolve().parents[1]
LIMIT=2*1024*1024
PROFILE='assertion-migration/v1'
SCHEMAS={
 '0.1.0':('spec/assertion.schema.json','d43c769a5ddc6a2f7cb4b5e6b81474403dbb2513d25f94fa7958035bfdd6ba1c'),
 '0.2.0':('spec/versions/0.2.0/assertion.schema.json','868509d90049ee839e050615bdc3256ef91fc1837d18767323f052ed24e2aa48'),
}
class Refusal(ValueError):
 def __init__(self,status,reason):self.status=status;self.reason=reason;super().__init__('Assertion migration refused.')
def need(ok,status='invalid',reason='invalid_record'):
 if not ok:raise Refusal(status,reason)
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def exact_float(token):
 # Reject decimal underflow/rounding before json.loads can erase the evidence.
 # Decimal comparison is on the JSON mathematical value, not binary float bits.
 need(len(token)<=128,reason='numeric_precision_loss')
 try:
  value=float(token)
  need(math.isfinite(value) and Decimal(token)==Decimal(repr(value)),reason='numeric_precision_loss')
  return value
 except (ValueError,InvalidOperation,OverflowError):raise Refusal('invalid','numeric_precision_loss')from None
def scalar(v,depth=0):
 need(depth<=64,reason='input_depth')
 if isinstance(v,float):need(math.isfinite(v),reason='invalid_json')
 if isinstance(v,str):need(not any(0xD800<=ord(c)<=0xDFFF for c in v),reason='invalid_json')
 if isinstance(v,dict):
  for k,item in v.items():need(type(k)is str,reason='invalid_json');scalar(k,depth+1);scalar(item,depth+1)
 elif isinstance(v,list):
  for item in v:scalar(item,depth+1)
def parse(raw):
 need(type(raw)is bytes and 0<len(raw)<=LIMIT,reason='input_limit')
 try:v=json.loads(raw.decode('utf-8','strict'),object_pairs_hook=unique,parse_constant=reject,parse_float=exact_float);scalar(v)
 except Refusal:raise
 except (ValueError,UnicodeError,RecursionError):raise Refusal('invalid','invalid_json')from None
 need(type(v)is dict);return v

def validator(version):
 try:
  path,digest=SCHEMAS[version];file=ROOT/path
  need(not file.is_symlink() and all(not p.is_symlink()for p in file.parents if p!=ROOT),'unavailable','schema_configuration')
  raw=file.read_bytes();need(len(raw)<=LIMIT and hashlib.sha256(raw).hexdigest()==digest,'unavailable','schema_configuration')
  from protocol.assertions import validator as make
  return make(json.loads(raw))
 except Refusal:raise
 except ImportError:raise Refusal('unavailable','missing_dependencies')from None
 except (ValueError,OSError,RuntimeError,RecursionError):raise Refusal('unavailable','schema_configuration')from None

def complete_identity(value):
 identity=value.get('evaluator',{}).get('preprocessing')
 need(type(identity)is dict,'unavailable','missing_preprocessing')
 # The stricter profile explicitly requires every existing identity/config key.
 try:
  schema=validator('0.2.0');probe=deepcopy(value);probe['spec_version']='0.2.0'
  need(schema.is_valid(probe),'unavailable','incomplete_identity')
  from protocol.replay_identity import PipelineIdentity
  validated=PipelineIdentity.model_validate(identity).model_dump()
  need(canonical(identity)==canonical(validated),'unavailable','identity_requires_normalization')
 except Refusal:raise
 except ImportError:raise Refusal('unavailable','missing_dependencies')from None
 except (ValueError,TypeError,RecursionError):raise Refusal('unavailable','invalid_identity')from None

def transform(raw,target):
 need(type(target)is str and target in SCHEMAS,'unsupported','unsupported_target')
 record=parse(raw);source=record.get('spec_version')
 need(type(source)is str and source in SCHEMAS,'unsupported','unsupported_version')
 need(source!=target,'unsupported','unsupported_route')
 need('signature'not in record,'unavailable','signed_record_requires_resigning')
 try:valid=validator(source).is_valid(record)
 except RecursionError:raise Refusal('invalid','input_depth')from None
 need(valid,reason='invalid_schema')
 complete_identity(record)
 result=deepcopy(record);result['spec_version']=target
 need(validator(target).is_valid(result),'unavailable','target_validation')
 # Semantic canonicalization preserves float/int representations and integer precision.
 roundtrip=deepcopy(result);roundtrip['spec_version']=source
 need(canonical(roundtrip)==canonical(record),'unavailable','roundtrip_failure')
 return result,{'format':PROFILE,'status':'transformed','source_version':source,'target_version':target,
   'field_changes':['spec_version'],'information_lost':False,'canonical_roundtrip_equal':True,
   'source_file_changed':False,'signature_verified':False,'identity_authenticated':False,
   'detector_rerun':False,'independent_accuracy_evidence':False,'runtime_replay_guaranteed':False}
