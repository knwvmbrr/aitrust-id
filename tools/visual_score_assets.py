"""Closed data/source boundary for an optional image-score research reference.

No model framework import, checkpoint pickle/JIT evaluation, network or tag issuance.
"""
import ast
from contextlib import contextmanager
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
COHORT=ROOT/'integrations/visual-score-reference/1.0.0'
BACKBONE_SHA='a2bf730a0c7debf160f7a6b50b3aaf3703e7e88ac73de7a314903141db026dcb'
BACKBONE_BYTES=1710540580
HEAD_GIT_BLOB='2a8efc8e238bf5a491e4fd5999655ed5eb3bbb72'
HEAD_BYTES=4083
MAX_IMAGE=10*1024*1024
MAX_PIXELS=4000000
METHOD='ufd-hf32bd-clip-vision-f32-centercrop224/raw-logit-v1'
# Fixed retained source digests. Model acquisition cannot update these assertions.
SOURCE_PINS={'ufd-license.txt': '923dbc0fe040cc826122491e98b20d6f401e510d50c8b666de908e59ebf2f2b2', 'ufd-clip-models.py': '57ce5898bf0bc7ff52b5922a0aefae8bc34a9237e4d59e4a1615ff5d8c6ff7a6', 'ufd-validate.py': '9ab4021cc6f85002a8b8cd0fc28baa9b4861b59bffcfbd98e10d02b08c42b2d6', 'ufd-head-metadata.json': 'db3ba20dbc85d13085aa60b997dbd1c760430d1128ce284e0be0625d2553690b', 'clip-license.txt': '987e63b32f6c89ff5160e429458a872ff048e6860b590a3912e938f9da8f14db', 'clip-model.py': '9902cbe5ee90a1da2aa3e6f043e8a23dc1f8831193b963785c9af03d5c7bef2c', 'clip-model-card.md': '7baf04f60c6234b301ec2c9ca39e67a3ca54b47c05e9509bddf732cbcbec8b7f', 'hf-config.json': '8a09b467700c58138c29d53c605b34ebc69beaadd13274a8a2af8ad2c2f4032a', 'hf-model-card-reference.json': '7ba894d89271710d574456154041d8dc98e0cb90af0929ce2ea77af782718621', 'hf-metadata.json': 'c89d81f20b6a35523af447f3d9f407607ccca85ee90eae18f6a90f2725e2e871', 'projection.json': '0ef209689edf086cad74c79df1c813aed2cae79811d313b238c9c90ca48f1260', 'source.json': 'f95f1008433c32216e0153c8ffd3d9cab4327abed047c19f28fd0c99d55253dc', 'torchvision-center-crop.py.txt': 'fc1e04cda9e231a1fb72036f6b3d6e9a3ae6dd494842b9036e70471fbf83ca0a', 'torchvision-license.txt': '6502f676851cfe25f8af75531dfb32375b7325b73c37e7b43741fa422893e71d', 'preprocess-reference.json': 'e7dabb28e8d7d074f89cd37d6f4ad735dcc80cb4e85d98f2e5701b5393ba03fe', 'runtime-candidates.json': '502a91a7a8e0d3a1331e5ff9f3ed14d3df7d8a0f0df5e55c0b1a9153be0837c0'}
NODE_PINS={'LayerNorm': 'bf13f581a4e61d51e45090c33d306de5e7a5c1251c53c98498f68e0c694582bf', 'QuickGELU': '23fb2dc3a596685eb389103d32769112901d321295374af1575a3d7daa0e8af4', 'ResidualAttentionBlock': '445b536b8a6109c6f8c70c08762d69db60f2579678b460863630eab97287b58f', 'Transformer': '58298fc06e86823406383e0f3abd666b42205e964edd6573460512d6b719be0e', 'VisionTransformer': '476926e19f83b50015cbbc8091f4d973e7ca64a9a232d44f2600f1e832b62a65'}
IMAGE_PINS={
 'png_metadata.py':'addd35028617f2d5c2cd01dc19106cec9946686cfe35139beb923af3973d6994',
 'jpeg_metadata.py':'c7e8fcb58acd2087a35c886a32b7df1fa390c74c52c023e9b137bdf1dd90872a'}
REASONS=frozenset(['invalid_request','input_limit','source_unavailable','source_changed','source_mismatch','model_missing','model_identity','model_format','head_format','head_numeric','image_unsupported','image_corrupt','image_limit','decoder_unavailable','decoder_failure','network_isolation_unavailable','resource_isolation_unavailable','runtime_unavailable','runtime_identity','inference_unavailable','worker_unavailable','deadline','output_limit','invalid_result','cleanup_uncertain','cancelled'])
class Refused(ValueError):
 def __init__(self,reason='runtime_unavailable'):
  self.reason=reason if reason in REASONS else 'runtime_unavailable';super().__init__(self.reason)
def need(value,reason):
 if not value:raise Refused(reason)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def identity(s):return s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns

class Source:
 """Owned regular no-follow descriptor; no close retry after ownership release."""
 def __init__(self,path,maximum):
  self.path=os.path.abspath(os.fspath(path));self.fd=None
  try:
   parent=Path(self.path).parent
   for ancestor in [parent,*parent.parents]:need(stat.S_ISDIR(os.lstat(ancestor).st_mode),'source_unavailable')
   self.fd=os.open(self.path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK)
   info=os.fstat(self.fd);need(stat.S_ISREG(info.st_mode),'source_unavailable');need(0<=info.st_size<=maximum,'input_limit')
   self.info=identity(info);self.size=info.st_size;self.check()
  except BaseException:
   if self.fd is not None:
    owned=self.fd;self.fd=None;os.close(owned)
   raise
 def check(self):
  need(self.fd is not None,'source_unavailable')
  need(identity(os.fstat(self.fd))==self.info and identity(os.lstat(self.path))==self.info,'source_changed')
 def read(self):
  self.check();parts=[];offset=0
  while offset<self.size:
   part=os.pread(self.fd,min(65536,self.size-offset),offset);need(bool(part),'source_changed');parts.append(part);offset+=len(part)
  need(not os.pread(self.fd,1,self.size),'source_changed');self.check();return b''.join(parts)
 def sha256(self):
  self.check();h=hashlib.sha256();offset=0
  while offset<self.size:
   data=os.pread(self.fd,min(1024*1024,self.size-offset),offset);need(bool(data),'source_changed');h.update(data);offset+=len(data)
  self.check();return h.hexdigest()
 def close(self):
  if self.fd is not None:
   owned=self.fd;self.fd=None;os.close(owned)
 def __enter__(self):return self
 def __exit__(self,kind,value,tb):
  try:
   if kind is None:self.check()
  finally:self.close()


class PrivateHome:
 """Parent-owned empty read-only cache; no recursive deletion or successor adoption."""
 def __init__(self):
  self.path=None;self.fd=None;self.origin=None;self.ready=False;self.removed=False
  try:
   self.path=tempfile.mkdtemp(prefix='aitrust-visual-score-home-',dir=os.path.realpath(tempfile.gettempdir()))
   self.fd=os.open(self.path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
   info=os.fstat(self.fd);self.origin=(info.st_dev,info.st_ino);need(stat.S_ISDIR(info.st_mode) and info.st_uid==os.geteuid(),'cleanup_uncertain')
   os.fchmod(self.fd,0o500);self.ready=True;self.check()
  except BaseException:
   self.close();raise
 def check(self):
  need(self.fd is not None and self.origin is not None,'cleanup_uncertain')
  info=os.fstat(self.fd);slot=os.lstat(self.path)
  need(stat.S_ISDIR(info.st_mode) and stat.S_ISDIR(slot.st_mode) and (info.st_dev,info.st_ino)==self.origin==(slot.st_dev,slot.st_ino) and info.st_uid==slot.st_uid==os.geteuid(),'cleanup_uncertain')
  need(stat.S_IMODE(info.st_mode)==stat.S_IMODE(slot.st_mode)==(0o500 if self.ready else 0o700),'cleanup_uncertain')
 def close(self):
  if self.fd is None:
   if self.path is not None and self.origin is None:raise Refused('cleanup_uncertain')
   return
  try:
   self.check();need(os.listdir(self.fd)==[],'cleanup_uncertain');os.rmdir(self.path);self.removed=True
  except (OSError,Refused):raise Refused('cleanup_uncertain') from None
  finally:
   fd=self.fd;self.fd=None
   try:os.close(fd)
   except OSError:raise Refused('cleanup_uncertain') from None
 def __enter__(self):return self
 def __exit__(self,kind,value,tb):self.close()

def fixed_source(name):
 need(name in SOURCE_PINS,'source_mismatch')
 with Source(COHORT/name,131072) as source:raw=source.read()
 need(digest(raw)==SOURCE_PINS[name],'source_mismatch');return raw

def projection():
 raw=fixed_source('clip-model.py');spec=json.loads(fixed_source('projection.json'));text=raw.decode('utf-8')
 need(spec['source_sha256']==digest(raw) and spec['nodes']==NODE_PINS,'source_mismatch')
 nodes={n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,ast.ClassDef) and n.name in NODE_PINS}
 need(list(nodes)==list(NODE_PINS),'source_mismatch')
 need(all(digest(value.encode())==NODE_PINS[name] for name,value in nodes.items()),'source_mismatch')
 return '\n\n'.join(nodes.values())+'\n'

def unique(pairs):
 out={}
 for key,value in pairs:
  need(key not in out,'model_format');out[key]=value
 return out

def safetensor_header(fd,size):
 """Bound framing and ALL tensors before asking an optional native reader to map."""
 need(type(size) is int and 8<=size<=BACKBONE_BYTES,'model_format')
 first=os.pread(fd,8,0);need(len(first)==8,'model_format');length=int.from_bytes(first,'little')
 need(2<=length<=262144 and 8+length<=size,'model_format')
 raw=os.pread(fd,length,8);need(len(raw)==length,'model_format')
 try:header=json.loads(raw,object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(Refused('model_format')))
 except (ValueError,UnicodeError,RecursionError):raise Refused('model_format') from None
 need(type(header)is dict and 1<=len(header)<=768,'model_format');ranges=[]
 for key,row in header.items():
  if key=='__metadata__':
   need(type(row)is dict and len(row)<=16 and all(type(k)is str and type(v)is str and len(k)<=128 and len(v)<=1024 for k,v in row.items()),'model_format');continue
  need(type(key)is str and re.fullmatch(r'[A-Za-z0-9_.]{1,180}',key) and type(row)is dict and set(row)=={'dtype','shape','data_offsets'},'model_format')
  dtype=row['dtype'];shape=row['shape'];span=row['data_offsets'];need(dtype in ('F32','I64') and type(shape)is list and len(shape)<=4,'model_format')
  count=1
  for n in shape:need(type(n)is int and 0<n<=50000,'model_format');count*=n;need(count<=50000000,'model_format')
  need(type(span)is list and len(span)==2 and all(type(x)is int for x in span),'model_format');start,end=span
  need(0<=start<end<=size-8-length and end-start==count*(4 if dtype=='F32' else 8),'model_format');ranges.append((start,end))
 ranges.sort();need(bool(ranges) and ranges[0][0]==0 and ranges[-1][1]==size-8-length,'model_format')
 need(all(a[1]==b[0] for a,b in zip(ranges,ranges[1:])),'model_format');return header

def vision_shapes():
 out={'vision_model.embeddings.class_embedding':('F32',[1024]),'vision_model.embeddings.patch_embedding.weight':('F32',[1024,3,14,14]),'vision_model.embeddings.position_embedding.weight':('F32',[257,1024]),'vision_model.embeddings.position_ids':('I64',[1,257]),'visual_projection.weight':('F32',[768,1024])}
 for norm in ['pre_layrnorm','post_layernorm']:
  for suffix in ['weight','bias']:out['vision_model.'+norm+'.'+suffix]=('F32',[1024])
 for n in range(24):
  p=f'vision_model.encoder.layers.{n}.'
  for name in ['q_proj','k_proj','v_proj','out_proj']:
   out[p+'self_attn.'+name+'.weight']=('F32',[1024,1024]);out[p+'self_attn.'+name+'.bias']=('F32',[1024])
  for name in ['layer_norm1','layer_norm2']:
   for suffix in ['weight','bias']:out[p+name+'.'+suffix]=('F32',[1024])
  for name,rows,cols in [('fc1',4096,1024),('fc2',1024,4096)]:
   out[p+'mlp.'+name+'.weight']=('F32',[rows,cols]);out[p+'mlp.'+name+'.bias']=('F32',[rows])
 return out

def validate_vision_header(header):
 expected=vision_shapes();actual={k:v for k,v in header.items() if k.startswith('vision_model.') or k.startswith('visual_projection.')}
 need(set(actual)==set(expected),'model_format')
 need(all(actual[k]['dtype']==dtype and actual[k]['shape']==shape for k,(dtype,shape) in expected.items()),'model_format')
 need(all(k in actual or k=='__metadata__' or k=='logit_scale' or k.startswith('text_model.') or k=='text_projection.weight' for k in header),'model_format')
 return expected

def head_layout(raw):
 """Tiny inert numeric ZIP profile; data.pkl is CRC-checked but NEVER evaluated."""
 need(type(raw)is bytes and 0<len(raw)<=8192,'head_format')
 try:
  with zipfile.ZipFile(io.BytesIO(raw)) as archive:
   rows=archive.infolist();need(4<=len(rows)<=6 and len(archive.comment)==0,'head_format');prefix=None;data={};total=0
   allowed={'data.pkl','version','data/0','data/1','byteorder','.data/serialization_id'}
   for row in rows:
    need(row.compress_type==zipfile.ZIP_STORED and row.flag_bits&1==0 and row.file_size==row.compress_size and row.file_size<=4096,'head_format')
    parts=row.filename.split('/',1);need(len(parts)==2 and re.fullmatch(r'[A-Za-z0-9_-]{1,64}',parts[0]) and parts[1] in allowed,'head_format')
    if prefix is None:prefix=parts[0]
    need(prefix==parts[0] and parts[1] not in data and (row.external_attr>>16)&0o170000 not in (stat.S_IFLNK,stat.S_IFDIR),'head_format')
    total+=row.file_size;need(total<=8192,'head_format');data[parts[1]]=archive.read(row)
   need({'data.pkl','version','data/0','data/1'}<=set(data) and data['version'] in (b'3\n',),'head_format')
   need('byteorder' not in data or data['byteorder']==b'little','head_format')
   need('.data/serialization_id' not in data or re.fullmatch(rb'[0-9]{1,64}',data['.data/serialization_id']),'head_format')
   weight,bias=data['data/0'],data['data/1'];need(len(weight)==3072 and len(bias)==4,'head_format')
 except (zipfile.BadZipFile,OSError,RuntimeError,NotImplementedError,EOFError):raise Refused('head_format') from None
 values=struct.unpack('<769f',weight+bias);need(all(math.isfinite(x) for x in values),'head_numeric')
 header={'bias':{'dtype':'F32','shape':[1],'data_offsets':[0,4]},'weight':{'dtype':'F32','shape':[1,768],'data_offsets':[4,3076]}}
 text=json.dumps(header,sort_keys=True,separators=(',',':')).encode();text+=b' '*((-len(text))%8)
 return len(text).to_bytes(8,'little')+text+bias+weight

def pinned_head(raw):
 need(type(raw)is bytes and len(raw)==HEAD_BYTES and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==HEAD_GIT_BLOB,'model_identity')
 return head_layout(raw)

def crop_geometry(width,height):
 need(type(width)is int and type(height)is int and width>0 and height>0 and width*height<=MAX_PIXELS,'image_limit')
 pad=(max(0,224-width)//2,max(0,224-height)//2,max(0,225-width)//2 if width<224 else 0,max(0,225-height)//2 if height<224 else 0)
 w,h=width+pad[0]+pad[2],height+pad[1]+pad[3]
 left,top=int(round((w-224)/2.0)),int(round((h-224)/2.0))
 return pad,(left,top,left+224,top+224)

def image_preflight(raw):
 need(type(raw)is bytes and 0<len(raw)<=MAX_IMAGE,'image_limit')
 name='png_metadata.py' if raw.startswith(b'\x89PNG\r\n\x1a\n') else 'jpeg_metadata.py' if raw.startswith(b'\xff\xd8') else None
 need(name is not None,'image_unsupported');path=ROOT/'integrations/image-metadata-reference/1.0.0/tools'/name
 with Source(path,65536) as source:code=source.read()
 need(digest(code)==IMAGE_PINS[name],'source_mismatch')
 scope={'__name__':'_visual_score_fixed_container','__file__':str(path)};exec(compile(code,'<fixed-image-container>','exec'),scope)
 try:record=scope['inspect_bytes'](raw)
 except scope['ImageError'] as error:
  reason=getattr(error,'reason','')
  raise Refused('image_unsupported' if reason in ('unsupported_variant','unsupported_format') else 'image_limit' if reason in ('input_limit','metadata_limit') else 'image_corrupt') from None
 image=record['image'];need(image['width']*image['height']<=MAX_PIXELS,'image_limit')
 if name=='png_metadata.py':need(image['color']=='RGB','image_unsupported')
 else:need(image['components']==3,'image_unsupported')
 return {'format':'PNG' if name=='png_metadata.py' else 'JPEG','width':image['width'],'height':image['height'],'pixel_profile':'stored_RGB8_no_orientation_or_ICC_transform'}

def crop_window(width,height):
 pad,box=crop_geometry(width,height);left,top,right,bottom=box
 # Equivalent to pad-then-center-crop, without ever allocating a huge padded strip.
 sx0,sy0=max(0,left-pad[0]),max(0,top-pad[1]);sx1,sy1=min(width,right-pad[0]),min(height,bottom-pad[1])
 need(0<=sx0<sx1<=width and 0<=sy0<sy1<=height,'image_limit')
 return {'logical_padding':list(pad),'crop_after_padding':list(box),'source_box':[sx0,sy0,sx1,sy1],'paste_at':[sx0+pad[0]-left,sy0+pad[1]-top],'output':[224,224]}

def implementation_identity():
 """Checkout byte observations, NOT execution attestation or numerical validation."""
 paths=['tools/visual_score_assets.py','tools/visual_score_runtime.py','tools/visual_score_process.py','tools/visual_score.py','scripts/inspect-visual-score.py']
 paths+=['integrations/visual-score-reference/1.0.0/'+name for name in SOURCE_PINS]
 paths+=['integrations/image-metadata-reference/1.0.0/tools/'+name for name in IMAGE_PINS]
 out={}
 for name in paths:
  with Source(ROOT/name,131072) as source:out[name]=digest(source.read())
 return out
