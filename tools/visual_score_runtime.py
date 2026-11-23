"""Optional actual CPU inference. Never imported by unrelated tags or absent-SDK CLI."""
from collections import OrderedDict
from contextlib import ExitStack
import builtins
import hashlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import platform
import socket
import sys
import warnings
from tools.visual_score_assets import (ROOT,COHORT,Source,Refused,need,digest,projection,fixed_source,
 BACKBONE_SHA,BACKBONE_BYTES,HEAD_BYTES,pinned_head,safetensor_header,validate_vision_header,
 image_preflight,crop_window,METHOD,implementation_identity)

VERSIONS={'torch':'2.15.0+cpu','safetensors':'0.8.0','pillow':'13.0.0'}
MEAN=(0.48145466,0.4578275,0.40821073)
STD=(0.26862954,0.26130258,0.27577711)

def isolation():
 need(sys.platform=='linux' and platform.machine()=='x86_64' and os.geteuid()!=0,'network_isolation_unavailable')
 try:
  text=Path('/proc/self/status').read_text();need(len(text)<=16384,'resource_isolation_unavailable')
  status=dict(line.split(':',1) for line in text.splitlines() if ':' in line)
  need(status.get('NoNewPrivs','').strip()=='1' and not status.get('Groups','').strip(),'resource_isolation_unavailable')
  for field in ['CapInh','CapPrm','CapEff','CapBnd','CapAmb']:need(int(status.get(field,'-1').strip(),16)==0,'resource_isolation_unavailable')
  interfaces=sorted(name for _,name in socket.if_nameindex());need(interfaces==['lo'],'network_isolation_unavailable')
  for name in ['route','ipv6_route']:
   with open('/proc/self/net/'+name) as stream:route=stream.read(16385)
   need(len(route)<=16384,'network_isolation_unavailable')
   for line in route.splitlines():
    if not line.strip() or line.startswith('Iface'):continue
    interface=line.split()[0 if name=='route' else -1];need(interface=='lo','network_isolation_unavailable')
 except (OSError,ValueError):raise Refused('network_isolation_unavailable') from None
 return {'loopback_only_observed':True,'capability_sets_zero':True,'no_new_privileges':True,'nonroot':True}

def sdk():
 records={}
 try:
  for name,version in VERSIONS.items():
   dist=importlib.metadata.distribution(name);need(dist.version==version,'runtime_identity')
   record=dist.read_text('RECORD');need(type(record)is str and len(record)<=4*1024*1024,'runtime_identity')
   records[name]={'version':version,'record_sha256':digest(record.encode())}
  import torch
  from safetensors import safe_open
  from safetensors.torch import load
  from PIL import Image,features
  need(torch.__version__==VERSIONS['torch'],'runtime_identity')
  torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
  Image.MAX_IMAGE_PIXELS=4000000
 except (ImportError,importlib.metadata.PackageNotFoundError):raise Refused('runtime_unavailable') from None
 return torch,safe_open,load,Image,features,records

def visual_state(read,torch):
 # Closed HF32bd vision-to-OpenAI visual mapping. No config-selected architecture.
 state={
 'conv1.weight':read('vision_model.embeddings.patch_embedding.weight'),
 'class_embedding':read('vision_model.embeddings.class_embedding'),
 'positional_embedding':read('vision_model.embeddings.position_embedding.weight'),
 'proj':read('visual_projection.weight').t()}
 for target,source in [('ln_pre','pre_layrnorm'),('ln_post','post_layernorm')]:
  for suffix in ['weight','bias']:state[target+'.'+suffix]=read('vision_model.'+source+'.'+suffix)
 for n in range(24):
  source=f'vision_model.encoder.layers.{n}.';target=f'transformer.resblocks.{n}.'
  for suffix in ['weight','bias']:
   state[target+'attn.in_proj_'+suffix]=torch.cat([read(source+'self_attn.'+part+'_proj.'+suffix) for part in ['q','k','v']],dim=0)
   state[target+'attn.out_proj.'+suffix]=read(source+'self_attn.out_proj.'+suffix)
   for to,fr in [('ln_1','layer_norm1'),('ln_2','layer_norm2'),('mlp.c_fc','mlp.fc1'),('mlp.c_proj','mlp.fc2')]:state[target+to+'.'+suffix]=read(source+fr+'.'+suffix)
 return state

def prepare_pixels(raw,geometry,torch,Image):
 try:
  with warnings.catch_warnings():
   warnings.simplefilter('error')
   with Image.open(io.BytesIO(raw),formats=[geometry['format']]) as image:
    need(image.size==(geometry['width'],geometry['height']) and image.mode=='RGB' and getattr(image,'n_frames',1)==1,'image_unsupported')
    image.load();window=crop_window(*image.size)
    # Fixed224-square allocation, including extremely narrow <=4MP inputs.
    with Image.new('RGB',(224,224),(0,0,0)) as canvas:
     with image.crop(tuple(window['source_box'])) as crop:canvas.paste(crop,tuple(window['paste_at']))
     pixels=canvas.tobytes()
  need(len(pixels)==224*224*3,'decoder_failure')
  tensor=torch.frombuffer(bytearray(pixels),dtype=torch.uint8).reshape(224,224,3).permute(2,0,1).to(dtype=torch.float32).div(255.)
  tensor=(tensor-torch.tensor(MEAN,dtype=torch.float32).view(3,1,1))/torch.tensor(STD,dtype=torch.float32).view(3,1,1)
  return tensor.unsqueeze(0),window,digest(pixels)
 except Refused:raise
 except (OSError,ValueError,Warning):raise Refused('decoder_failure') from None

def infer(raw,model_dir):
 implementation=implementation_identity();geometry=image_preflight(raw);environment=isolation()
 model_dir=Path(model_dir)
 with ExitStack() as stack:
  backbone=stack.enter_context(Source(model_dir/'model.safetensors',BACKBONE_BYTES))
  head=stack.enter_context(Source(model_dir/'fc_weights.pth',HEAD_BYTES))
  need(backbone.size==BACKBONE_BYTES and backbone.sha256()==BACKBONE_SHA,'model_identity')
  head_raw=head.read();head_safe=pinned_head(head_raw)
  header=safetensor_header(backbone.fd,backbone.size);shapes=validate_vision_header(header)
  projected=projection();torch,safe_open,load,Image,features,records=sdk()
  allowed={name:getattr(builtins,name) for name in ['__build_class__','super','range','int','float']}
  scope={'__builtins__':allowed,'__name__':'_visual_score_trusted_clip','torch':torch,'nn':torch.nn,'OrderedDict':OrderedDict}
  exec(compile(projected,'<fixed-CLIP-visual-projection>','exec'),scope)
  with safe_open('/proc/self/fd/'+str(backbone.fd),framework='pt',device='cpu') as reader:
   need(set(reader.keys())==set(header)-{'__metadata__'},'model_format')
   def tensor(name):
    need(name in shapes,'model_format');value=reader.get_tensor(name);dtype,shape=shapes[name]
    need(list(value.shape)==shape and str(value.dtype)==('torch.float32' if dtype=='F32' else 'torch.int64') and value.device.type=='cpu','model_format')
    need(bool(torch.isfinite(value).all().item()),'model_format');return value
   positions=tensor('vision_model.embeddings.position_ids')
   need(bool(torch.equal(positions,torch.arange(257,dtype=torch.int64).view(1,257))),'model_format')
   state=visual_state(tensor,torch)
   with torch.device('meta'):model=scope['VisionTransformer'](224,14,1024,24,16,768)
   model.load_state_dict(state,strict=True,assign=True);model.eval()
   prepared,window,pixel_sha=prepare_pixels(raw,geometry,torch,Image)
   linear=load(head_safe);need(set(linear)=={'weight','bias'},'head_format')
   with torch.inference_mode():
    feature=model(prepared);need(list(feature.shape)==[1,768] and bool(torch.isfinite(feature).all().item()),'inference_unavailable')
    value=torch.nn.functional.linear(feature,linear['weight'],linear['bias']);need(list(value.shape)==[1,1],'inference_unavailable');score=float(value.item())
   need(math.isfinite(score),'inference_unavailable')
  need(backbone.sha256()==BACKBONE_SHA and digest(head.read())==digest(head_raw),'source_changed')
  need(implementation==implementation_identity(),'source_changed')
  record={'format':'offline-image-score-observation/v1','state':'OBSERVED','subject':{'sha256':digest(raw),'bytes':len(raw),'image':geometry},'method':{'id':METHOD,'implementation_sha256':implementation,'implementation_identity_kind':'observed_checkout_file_sha256_not_execution_attestation','backbone_sha256':BACKBONE_SHA,'head_git_blob_sha1':'2a8efc8e238bf5a491e4fd5999655ed5eb3bbb72','head_sha256':digest(head_raw),'derived_head_safetensors_sha256':digest(head_safe),'projection_sha256':digest(projected.encode()),'preprocessing':'RGB8_center224_half-even_black-padding_no-resize_no-EXIF-ICC_no-feature-L2/v1','crop':window,'crop_rgb_sha256':pixel_sha,'runtime':records,'decoder_jpeg_version':str(features.version_codec('jpg')),'cpu_threads':1,'batch':1},'raw_logit':score,'score_type':'uncalibrated_linear_logit','threshold_applied':False,'AI_origin':'unknown','authorship_established':False,'content_truth_established':False,'independently_validated':False,'training_performed':False,'tags':[],'environment':environment,'text_or_metadata_values_returned':False,'hash_linkability_warning':'Explicit JSON fingerprints can link copies of the input image.'}
 return record
