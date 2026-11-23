"""Qualification-only independent HF vision forward. No from_pretrained/network/pickle."""
import io
import math
import os
import struct
import zipfile
from pathlib import Path
from tools import visual_score_assets as a
from tools import visual_score_runtime as r

def infer(raw,model_dir):
 geometry=a.image_preflight(raw);environment=r.isolation()
 with a.Source(Path(model_dir)/'model.safetensors',a.BACKBONE_BYTES) as backbone,a.Source(Path(model_dir)/'fc_weights.pth',a.HEAD_BYTES) as head:
  a.need(backbone.size==a.BACKBONE_BYTES and backbone.sha256()==a.BACKBONE_SHA,'model_identity')
  rawhead=head.read();a.pinned_head(rawhead)
  header=a.safetensor_header(backbone.fd,backbone.size);shapes=a.validate_vision_header(header)
  torch,safe_open,_,Image,_,_=r.sdk()
  from transformers import CLIPVisionConfig,CLIPVisionModelWithProjection
  from PIL import ImageOps
  config=CLIPVisionConfig(hidden_size=1024,intermediate_size=4096,num_hidden_layers=24,num_attention_heads=16,image_size=224,patch_size=14,projection_dim=768,hidden_act='quick_gelu',layer_norm_eps=1e-5,attention_dropout=0.0)
  config._attn_implementation='eager'
  with torch.device('meta'):model=CLIPVisionModelWithProjection(config)
  with safe_open('/proc/self/fd/'+str(backbone.fd),framework='pt',device='cpu') as reader:
   state={}
   expected=set(model.state_dict())
   a.need(expected<=set(shapes) and set(shapes)-expected<={'vision_model.embeddings.position_ids'},'model_format')
   for name in sorted(expected):
    value=reader.get_tensor(name);dtype,shape=shapes[name]
    a.need(dtype=='F32' and list(value.shape)==shape and value.dtype==torch.float32 and bool(torch.isfinite(value).all().item()),'model_format');state[name]=value
   model.load_state_dict(state,strict=True,assign=True);model.eval()
   with Image.open(io.BytesIO(raw)) as source:
    a.need(source.mode=='RGB' and source.size==(geometry['width'],geometry['height']),'image_unsupported');source.load()
    width,height=source.size
    padding=(max(0,(224-width)//2),max(0,(224-height)//2),max(0,(224-width+1)//2),max(0,(224-height+1)//2))
    # Only bounded synthetic fixtures in this reference, not a public image decoder.
    a.need(width<=1024 and height<=1024,'image_limit')
    with ImageOps.expand(source,padding,fill=0) as padded:
     left=round((padded.width-224)/2.);top=round((padded.height-224)/2.)
     with padded.crop((left,top,left+224,top+224)) as cropped:pixels=cropped.tobytes()
   prepared=torch.tensor(list(pixels),dtype=torch.float32).reshape(224,224,3).permute(2,0,1).div(255.)
   for i,(mean,std) in enumerate(zip((.48145466,.4578275,.40821073),(.26862954,.26130258,.27577711))):prepared[i].sub_(mean).div_(std)
   with zipfile.ZipFile(io.BytesIO(rawhead)) as z:
    names=z.namelist();w=[x for x in names if x.endswith('/data/0')];b=[x for x in names if x.endswith('/data/1')];a.need(len(w)==len(b)==1,'head_format')
    weights=struct.unpack('<768f',z.read(w[0]));bias=struct.unpack('<f',z.read(b[0]))[0]
   with torch.inference_mode():
    feature=model(pixel_values=prepared.unsqueeze(0),return_dict=True).image_embeds
    a.need(list(feature.shape)==[1,768],'inference_unavailable')
    score=float((feature@torch.tensor(weights,dtype=torch.float32).reshape(768,1)+bias).item())
   a.need(math.isfinite(score),'inference_unavailable')
  a.need(backbone.sha256()==a.BACKBONE_SHA and head.read()==rawhead,'source_changed')
 return {'reference':'HF-CLIPVisionModelWithProjection5.22.2-eager/no-L2/v1','raw_logit':score,'crop_rgb_sha256':a.digest(pixels),'AI_origin':'unknown','tags':[],'environment':environment}
