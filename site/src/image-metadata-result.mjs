export const PARSERS=Object.freeze({"png":{"source_sha256":"addd35028617f2d5c2cd01dc19106cec9946686cfe35139beb923af3973d6994","projection_sha256":"59c5a09534b8ff7ff0e4598024a02a4a0e84447dfee408ce37b2b9c4df14c6f1","projection_bytes":12113,"profile":"png-metadata-preflight/1.0.0"},"jpeg":{"source_sha256":"c7e8fcb58acd2087a35c886a32b7df1fa390c74c52c023e9b137bdf1dd90872a","projection_sha256":"2670acac47e6cd567ed46643b905b202491d99bc12d4c490815044422597a7f2","projection_bytes":13607,"profile":"jpeg-metadata-observation/1.0.0"}});
export const MAX_INPUT=10485760;
for(const pin of Object.values(PARSERS))Object.freeze(pin);
const contexts=new WeakSet(),accepted=new WeakSet(),hex=/^[a-f0-9]{64}$/;
const need=(ok)=>{if(!ok)throw Error('Image result unavailable.');};
const keys=(v,allowed)=>{need(v&&typeof v==='object'&&!Array.isArray(v));need(Object.keys(v).sort().join()===allowed.slice().sort().join());};
const integer=(v,max,min=0)=>Number.isSafeInteger(v)&&v>=min&&v<=max;
function inert(value,depth=0,budget={nodes:0}){
 need(depth<=12&&++budget.nodes<=512);
 if(value===null||typeof value==='boolean'||typeof value==='number'){need(typeof value!=='number'||Number.isFinite(value));return;}
 if(typeof value==='string'){need(value.length<=8192);return;}
 need(typeof value==='object'&&[Object.prototype,Array.prototype,null].includes(Object.getPrototypeOf(value)));
 const descriptors=Object.getOwnPropertyDescriptors(value);need(Reflect.ownKeys(descriptors).every(k=>typeof k==='string')&&Object.keys(descriptors).length<=128);
 for(const descriptor of Object.values(descriptors)){need('value'in descriptor&&!descriptor.get&&!descriptor.set);inert(descriptor.value,depth+1,budget);}
}
const PNG_META=['plain_text','compressed_text','international_text','EXIF_section','ICC_section','C2PA_section','time_section','other_ancillary_sections'];
const PNG_CATEGORIES=['author','software','description','copyright','XMP','other'];
const JPEG_META=['Exif_labelled','XMP_labelled','ICC_labelled','JFIF_labelled','APP11_opaque','comment','other_APP'];
const REASONS={png:['unsupported_format','unsupported_variant','corrupt_container','corrupt_image_data','corrupt_text_metadata','input_limit','metadata_limit','source_unavailable','worker_unavailable','invalid_request'],jpeg:['unsupported_format','unsupported_variant','malformed_structure','trailing_data','input_limit','metadata_limit','source_unavailable','worker_unavailable','invalid_request']};
function counts(v,allowed,max){keys(v,allowed);need(Object.values(v).every(x=>integer(x,max)));}
function deepFreeze(v){if(v&&typeof v==='object'){for(const item of Object.values(v))deepFreeze(item);Object.freeze(v);}return v;}
function boundHeader(bytes,kind){
 const raw=new Uint8Array(bytes),view=new DataView(bytes);
 if(kind==='png')return raw.length>=33&&view.getUint32(8)===13&&[73,72,68,82].every((v,i)=>raw[12+i]===v)?{width:view.getUint32(16),height:view.getUint32(20),bit_depth:raw[24],color:({0:'grayscale',2:'RGB',4:'grayscale_alpha',6:'RGBA'})[raw[25]]||null}:null;
 let at=2;
 for(let count=0;count<4096&&at+1<raw.length;count++){
  if(raw[at++]!==255)return null;while(at<raw.length&&raw[at]===255)at++;if(at>=raw.length)return null;
  const code=raw[at++];if(code===0||code===0xD8||code===0xD9||code===0xDA||at+2>raw.length)return null;
  const length=view.getUint16(at);if(length<2||at+length>raw.length)return null;
  if(code===0xC0)return length>=8?{width:view.getUint16(at+5),height:view.getUint16(at+3),precision:raw[at+2],components:raw[at+7]}:null;
  at+=length;
 }
 return null;
}
export async function imageContext(bytes){
 need(bytes instanceof ArrayBuffer&&integer(bytes.byteLength,MAX_INPUT,1));const head=new Uint8Array(bytes,0,Math.min(bytes.byteLength,8));
 const kind=head.length===8&&[137,80,78,71,13,10,26,10].every((v,i)=>head[i]===v)?'png':head[0]===255&&head[1]===216?'jpeg':null;
 if(!kind){const error=Error('Choose a supported PNG or JPEG.');error.code='unsupported_format';throw error;}
 const header=boundHeader(bytes,kind);const digest=await crypto.subtle.digest('SHA-256',bytes),context=Object.freeze({kind,bytes:bytes.byteLength,header:deepFreeze(header),sha256:Array.from(new Uint8Array(digest),v=>v.toString(16).padStart(2,'0')).join('')});contexts.add(context);return context;
}
export function validateImageRecord(value,context){
 need(contexts.has(context));inert(value);keys(value,['format','kind','source_sha256','projection_sha256','record']);
 const kind=context.kind,pin=PARSERS[kind];need(value.format==='image-metadata-device-record/v1'&&value.kind===kind&&value.source_sha256===pin.source_sha256&&value.projection_sha256===pin.projection_sha256);
 const r=value.record;base(r,kind,context);
 const fixed=['profile','state','asset_sha256','asset_bytes','metadata_values_returned','watermark_verified','C2PA_inspected','AI_origin','content_truth_established','tags',...(kind==='jpeg'?['pixels_decoded']:[])];
 if(r.state==='UNAVAILABLE'){keys(r,[...fixed,'reason']);need(REASONS[kind].includes(r.reason));}
 else{
  need(r.state==='OBSERVED');keys(r,[...fixed,...(kind==='png'?['image','chunk_count','stored_metadata_bytes','expanded_text_bytes','metadata_sections','text_categories','image_data_check']:['image','marker_count','metadata_bytes','metadata_sections','entropy_framing'])]);
  if(kind==='png'){
   keys(r.image,['width','height','bit_depth','color']);need(r.image.bit_depth===8&&['grayscale','RGB','grayscale_alpha','RGBA'].includes(r.image.color));
   need(integer(r.chunk_count,4096)&&integer(r.stored_metadata_bytes,262144)&&integer(r.expanded_text_bytes,262144)&&r.image_data_check==='bounded_zlib_scanlines');
   counts(r.metadata_sections,PNG_META,4096);counts(r.text_categories,PNG_CATEGORIES,128);
   need(Object.values(r.text_categories).reduce((a,b)=>a+b,0)===['plain_text','compressed_text','international_text'].reduce((n,k)=>n+r.metadata_sections[k],0)&&Object.values(r.text_categories).reduce((a,b)=>a+b,0)<=128&&Object.values(r.metadata_sections).reduce((a,b)=>a+b,0)<=r.chunk_count);
  }else{
   keys(r.image,['width','height','precision','components']);need(r.image.precision===8&&[1,3].includes(r.image.components));
   need(integer(r.marker_count,4096,1)&&integer(r.metadata_bytes,262144));counts(r.metadata_sections,JPEG_META,128);need(Object.values(r.metadata_sections).reduce((a,b)=>a+b,0)<=128);
   keys(r.entropy_framing,['scan_count','data_bytes','restart_markers','decoded','MCU_intervals_verified']);const e=r.entropy_framing;need(e.scan_count===1&&integer(e.data_bytes,MAX_INPUT,1)&&integer(e.restart_markers,4096)&&e.decoded===false&&e.MCU_intervals_verified===false);
  }
  need(integer(r.image.width,4000000,1)&&integer(r.image.height,4000000,1)&&r.image.width*r.image.height<=4000000&&context.header&&Object.keys(r.image).every(k=>r.image[k]===context.header[k]));
 }
 need(new TextEncoder().encode(JSON.stringify(value)).length<=10000);deepFreeze(value);accepted.add(value);return value;
}
function base(r,kind,context){
 need(r&&r.profile===PARSERS[kind].profile&&r.asset_sha256===context.sha256&&hex.test(r.asset_sha256)&&r.asset_bytes===context.bytes&&r.metadata_values_returned===false&&r.watermark_verified===false&&r.C2PA_inspected===false&&r.AI_origin==='unknown'&&r.content_truth_established===false&&Array.isArray(r.tags)&&r.tags.length===0&&Object.keys(r.tags).length===0);
 if(kind==='jpeg')need(r.pixels_decoded===false);
}
export function explainImage(value){
 need(accepted.has(value));const r=value.record;
 if(r.state==='UNAVAILABLE'){
  const unsupported=r.reason.startsWith('unsupported_');return {title:unsupported?'Unsupported image profile':r.reason.endsWith('_limit')?'Image exceeds supported limits':'Image details unavailable',message:unsupported?'This reader does not support this format or coding variant. That says nothing about who made it.':r.reason.endsWith('_limit')?'The image or metadata exceeds this bounded preview. Your file is unchanged.':'The selected container checks could not complete. No empty or safe result is being reported.',observed:false};
 }
 return {title:'Image container details',message:`${value.kind==='png'?'PNG':'JPEG'} · ${r.image.width} × ${r.image.height} header dimensions.`,observed:true,sections:Object.values(r.metadata_sections).reduce((a,b)=>a+b,0)};
}
