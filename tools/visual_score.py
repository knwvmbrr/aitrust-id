"""Private optional image-score CLI boundary. No SDK/model import on missing assets."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import sys
import stat
from tools.visual_score_assets import (ROOT,Source,Refused,need,digest,MAX_IMAGE,METHOD,BACKBONE_SHA,BACKBONE_BYTES,HEAD_BYTES,HEAD_GIT_BLOB,REASONS,PrivateHome)
from tools.visual_score_process import run,MAX_REPORT
FORMAT='offline-image-score-observation/v1'
FALSES=['threshold_applied','authorship_established','content_truth_established','independently_validated','training_performed','text_or_metadata_values_returned']

def unavailable(reason):
 return {'format':FORMAT,'state':'UNAVAILABLE','reason':reason if reason in REASONS else 'worker_unavailable','AI_origin':'unknown','tags':[]}

def decode(raw):
 need(type(raw)is bytes and 0<len(raw)<=MAX_REPORT,'invalid_result')
 def unique(pairs):
  out={}
  for key,value in pairs:need(key not in out,'invalid_result');out[key]=value
  return out
 try:value=json.loads(raw,object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(Refused('invalid_result')))
 except (ValueError,UnicodeError,RecursionError):raise Refused('invalid_result') from None
 need(type(value)is dict and value.get('format')==FORMAT and value.get('tags')==[] and value.get('AI_origin')=='unknown','invalid_result')
 return value

def identical(value,expected):
 if type(value)is not type(expected):return False
 if type(expected)is dict:return set(value)==set(expected) and all(identical(value[k],v) for k,v in expected.items())
 if type(expected)is list:return len(value)==len(expected) and all(identical(a,b) for a,b in zip(value,expected))
 return value==expected

def validate(value,raw):
 need(type(value)is dict and value.get('format')==FORMAT and value.get('tags')==[] and value.get('AI_origin')=='unknown','invalid_result')
 need(value.get('state') in ('OBSERVED','UNAVAILABLE'),'invalid_result')
 if value['state']=='UNAVAILABLE':
  need(set(value)=={'format','state','reason','AI_origin','tags'} and value['reason'] in REASONS,'invalid_result');return value
 keys={'format','state','subject','method','raw_logit','score_type','AI_origin','tags','environment','hash_linkability_warning',*FALSES}
 need(set(value)==keys and all(value[k] is False for k in FALSES),'invalid_result')
 need(type(value['raw_logit']) in (int,float) and math.isfinite(value['raw_logit']) and value['score_type']=='uncalibrated_linear_logit','invalid_result')
 subject=value['subject'];need(type(subject)is dict and set(subject)=={'sha256','bytes','image'} and subject['sha256']==digest(raw) and type(subject['bytes'])is int and subject['bytes']==len(raw),'invalid_result')
 from tools.visual_score_assets import image_preflight,crop_window,projection,implementation_identity
 geometry=image_preflight(raw);need(identical(subject['image'],geometry),'invalid_result')
 method=value['method'];expected={'id','implementation_sha256','implementation_identity_kind','backbone_sha256','head_git_blob_sha1','head_sha256','derived_head_safetensors_sha256','projection_sha256','preprocessing','crop','crop_rgb_sha256','runtime','decoder_jpeg_version','cpu_threads','batch'}
 need(type(method)is dict and set(method)==expected and method['id']==METHOD and method['backbone_sha256']==BACKBONE_SHA and method['head_git_blob_sha1']==HEAD_GIT_BLOB and method['projection_sha256']==digest(projection().encode()),'invalid_result')
 need(method['implementation_identity_kind']=='observed_checkout_file_sha256_not_execution_attestation' and identical(method['implementation_sha256'],implementation_identity()),'invalid_result')
 for key in ['head_sha256','derived_head_safetensors_sha256','crop_rgb_sha256']:
  need(type(method[key])is str and len(method[key])==64 and all(x in '0123456789abcdef' for x in method[key]),'invalid_result')
 need(method['preprocessing']=='RGB8_center224_half-even_black-padding_no-resize_no-EXIF-ICC_no-feature-L2/v1' and identical(method['crop'],crop_window(geometry['width'],geometry['height'])) and type(method['cpu_threads'])is int and method['cpu_threads']==1 and type(method['batch'])is int and method['batch']==1,'invalid_result')
 need(type(method['decoder_jpeg_version'])is str and len(method['decoder_jpeg_version'])<=64,'invalid_result')
 from tools.visual_score_runtime import VERSIONS
 versions=method['runtime'];need(type(versions)is dict and set(versions)==set(VERSIONS),'invalid_result')
 for name,version in VERSIONS.items():
  row=versions[name];need(type(row)is dict and set(row)=={'version','record_sha256'} and row['version']==version and type(row['record_sha256'])is str and len(row['record_sha256'])==64 and all(x in '0123456789abcdef' for x in row['record_sha256']),'invalid_result')
 environment=value['environment'];need(type(environment)is dict and set(environment)=={'loopback_only_observed','capability_sets_zero','no_new_privileges','nonroot'} and all(v is True for v in environment.values()),'invalid_result')
 need(value['hash_linkability_warning']=='Explicit JSON fingerprints can link copies of the input image.','invalid_result');return value

def check(path,model_dir):
 try:
  model_dir=Path(os.path.abspath(os.fspath(model_dir)))
  # Missing optional assets cannot cause SDK import or disable PS/other tools.
  need(model_dir.is_dir() and (model_dir/'model.safetensors').is_file() and (model_dir/'fc_weights.pth').is_file(),'model_missing')
  with Source(path,MAX_IMAGE) as source:
   raw=source.read();need(bool(raw),'input_limit')
   with PrivateHome() as home:
    header=json.dumps({'model_dir':str(model_dir),'image_bytes':len(raw),'cache_dir':home.path,'cache_devino':list(home.origin)},separators=(',',':')).encode();need(len(header)<=4096,'invalid_request')
    request=len(header).to_bytes(4,'big')+header+raw
    output=run([sys.executable,'-I','-B',str(ROOT/'scripts/inspect-visual-score.py'),'--worker'],request)
    record=validate(decode(output),raw);source.check();home.check()
  return record
 except Refused as error:return unavailable(error.reason)
 except (OSError,ValueError,TypeError,KeyError,RuntimeError):return unavailable('worker_unavailable')

def worker():
 """Internal fixed protocol: model path is trusted CLI config, never image metadata."""
 size=sys.stdin.buffer.read(4);need(len(size)==4,'invalid_request');length=int.from_bytes(size,'big');need(0<length<=4096,'invalid_request')
 header=decode_request(sys.stdin.buffer.read(length));raw=sys.stdin.buffer.read(MAX_IMAGE+1)
 need(len(raw)==header['image_bytes'] and 0<len(raw)<=MAX_IMAGE,'input_limit')
 resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3));resource.setrlimit(resource.RLIMIT_NOFILE,(64,64));resource.setrlimit(resource.RLIMIT_FSIZE,(MAX_REPORT,MAX_REPORT))
 # Parent owns this directory before spawn and cleans it after ordinary kill/reap.
 cache_fd=os.open(header['cache_dir'],os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
 try:
  info=os.fstat(cache_fd);need((info.st_dev,info.st_ino)==tuple(header['cache_devino']) and info.st_uid==os.geteuid() and stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode)==0o500 and os.listdir(cache_fd)==[],'invalid_request')
  home='/proc/self/fd/'+str(cache_fd) if sys.platform=='linux' else header['cache_dir']
  for name in ['HOME','XDG_CACHE_HOME','HF_HOME','TORCH_HOME','TMPDIR']:os.environ[name]=home
  import tempfile
  tempfile.tempdir=home # no fallback into an existing user/system cache
  from tools.visual_score_runtime import infer
  record=infer(raw,header['model_dir'])
 finally:
  owned=cache_fd;cache_fd=None;os.close(owned)
 data=json.dumps(record,allow_nan=False,separators=(',',':')).encode();need(len(data)<=MAX_REPORT,'output_limit');sys.stdout.buffer.write(data)

def decode_request(raw):
 try:
  value=json.loads(raw,object_pairs_hook=lambda pairs:_request_unique(pairs))
 except (ValueError,UnicodeError,RecursionError):raise Refused('invalid_request') from None
 need(type(value)is dict and set(value)=={'model_dir','image_bytes','cache_dir','cache_devino'} and type(value['model_dir'])is str and value['model_dir'].startswith('/') and len(value['model_dir'])<=2048 and '\0' not in value['model_dir'] and type(value['image_bytes'])is int,'invalid_request');need(type(value['cache_dir'])is str and value['cache_dir'].startswith('/') and len(value['cache_dir'])<=2048 and '\0' not in value['cache_dir'] and type(value['cache_devino'])is list and len(value['cache_devino'])==2 and all(type(x)is int and x>=0 for x in value['cache_devino']),'invalid_request');return value

def _request_unique(pairs):
 out={}
 for key,value in pairs:need(key not in out,'invalid_request');out[key]=value
 return out

class PrivateParser(argparse.ArgumentParser):
 def error(self,message):
  print('IMAGE SCORE UNAVAILABLE: invalid_request. Check the documented command; no input was inspected.')
  raise SystemExit(2)

def main(argv=None):
 p=PrivateParser(description='Optional offline image reference logit. Not an AI-origin verdict or tag.')
 p.add_argument('image',help='Explicit PNG/JPEG file, at most10MiB/4MP; path is not printed')
 p.add_argument('--model-dir',required=True,help='Trusted offline directory containing exact publisher model.safetensors and fc_weights.pth; no download')
 p.add_argument('--json',action='store_true',help='Explicit identities/hashes can link copies of the private image')
 a=p.parse_args(argv);record=check(a.image,a.model_dir)
 if a.json:print(json.dumps(record,allow_nan=False,indent=2))
 elif record['state']=='OBSERVED':
  print('Reference raw logit: '+format(record['raw_logit'],'.17g'))
  print('Unvalidated research computation; not a probability, AI-origin claim, authorship verdict or FA/PA tag.')
  print('Center-cropped224px input can miss edits. No filenames, metadata, image hashes or embeddings printed.')
 else:
  print('IMAGE SCORE UNAVAILABLE: '+record['reason']+'. No origin conclusion or tag; unrelated checks remain separate.')
  if record['reason']=='cleanup_uncertain':print('Private cache bytes may remain. Do not use this attempt as accepted evidence.')
 return 0 if record['state']=='OBSERVED' else 2
