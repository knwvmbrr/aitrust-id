// Separate implementation of the bounded decoded-artifact subject contract.
const {createHash}=require('node:crypto');
const {normalizeNFC,NORMALIZATION_ID}=require('./normalization.cjs');
const VERSION='reserved-subject-v1', MAX_BINARY=1048576, MAX_VIDEO_BYTES=4194304;
function fields(value,expected){if(!value||Array.isArray(value)||typeof value!=='object'||Object.keys(value).length!==expected.length||expected.some(key=>!Object.hasOwn(value,key)))throw Error('Unexpected artifact fields');}
function integer(value,min,max){if(!Number.isSafeInteger(value)||value<min||value>max)throw Error('Invalid integer');return value;}
function binary(value,max=MAX_BINARY){if(typeof value!=='string'||value.length>4*Math.ceil(max/3))throw Error('Invalid base64');const raw=Buffer.from(value,'base64');if(raw.length>max||raw.toString('base64')!==value)throw Error('Noncanonical/oversized base64');return raw;}
function digest(kind,parts){const h=createHash('sha256');h.update(VERSION+'\0'+kind+'\0','ascii');for(const part of parts){const raw=Buffer.isBuffer(part)?part:Buffer.from(String(part),'utf8'),size=Buffer.alloc(4);size.writeUInt32BE(raw.length);h.update(size);h.update(raw);}return h.digest('hex');}
function image(value){
 fields(value,['modality','width','height','representation','pixels_base64']);
 if(value.modality!=='image'||value.representation!=='RGBA8-sRGB-straight-oriented')throw Error('Unsupported image representation');
 const width=integer(value.width,1,262144),height=integer(value.height,1,262144);if(width*height>262144)throw Error('Oversized pixel count');
 const raw=binary(value.pixels_base64);if(raw.length!==width*height*4)throw Error('Pixel buffer mismatch');
 return [{modality:'image',contract_version:VERSION,sha256:digest('image',[width,height,value.representation,raw]),width,height,offset_unit:'pixel_xy_half_open'},raw.length];
}
function audio(value){
 fields(value,['modality','sample_rate','channels','representation','samples_base64']);
 if(value.modality!=='audio'||value.representation!=='PCM16LE-interleaved')throw Error('Unsupported audio representation');
 const rate=integer(value.sample_rate,8000,192000),channels=integer(value.channels,1,8),raw=binary(value.samples_base64);
 if(!raw.length||raw.length%(2*channels))throw Error('Incomplete audio frame');
 return {modality:'audio',contract_version:VERSION,sha256:digest('audio',[rate,channels,value.representation,raw]),frames:raw.length/(2*channels),sample_rate:rate,channels,offset_unit:'sample_frame_half_open',time_base:{numerator:1,denominator:rate}};
}
function video(value){
 fields(value,['modality','representation','frames']);if(value.modality!=='video'||value.representation!=='decoded-frames-us-v1')throw Error('Unsupported video representation');
 if(!Array.isArray(value.frames)||value.frames.length<1||value.frames.length>64)throw Error('Invalid frame count');
 const leaves=[],manifest=[];let total=0,previousEnd=0;
 value.frames.forEach((frame,index)=>{
  fields(frame,['timestamp_us','duration_us','image']);const timestamp=integer(frame.timestamp_us,0,Number.MAX_SAFE_INTEGER),duration=integer(frame.duration_us,1,Number.MAX_SAFE_INTEGER);
  if(timestamp+duration>Number.MAX_SAFE_INTEGER||index&&timestamp<previousEnd)throw Error('Overlapping/unsafe video timing');
  const [subject,size]=image(frame.image);total+=size;if(total>MAX_VIDEO_BYTES)throw Error('Oversized video buffers');previousEnd=timestamp+duration;
  leaves.push(digest('video-leaf',[index,timestamp,duration,Buffer.from(subject.sha256,'hex')]));manifest.push({index,timestamp_us:timestamp,duration_us:duration,image:subject});
 });
 let nodes=leaves.slice();while(nodes.length>1){const next=[];for(let i=0;i<nodes.length;i+=2)next.push(i+1<nodes.length?digest('video-pair',[Buffer.from(nodes[i],'hex'),Buffer.from(nodes[i+1],'hex')]):nodes[i]);nodes=next;}
 return {modality:'video',contract_version:VERSION,sha256:digest('video',[value.frames.length,value.representation,Buffer.from(nodes[0],'hex')]),frames:manifest,merkle_rule:'ordered-domain-separated-pairs; odd node promoted',offset_unit:'frame_index_pixel_xy_half_open',time_unit:'microsecond'};
}
function document(value){
 fields(value,['modality','extraction_profile','pages']);if(value.modality!=='document'||value.extraction_profile!=='supplied-page-text-v1')throw Error('Unsupported extraction profile');
 if(!Array.isArray(value.pages)||value.pages.length<1||value.pages.length>100)throw Error('Invalid page count');
 const hashes=[],manifest=[];let characters=0,assetCount=0,assetBytes=0;
 value.pages.forEach((page,index)=>{
  fields(page,['text','assets']);if(typeof page.text!=='string')throw Error('Invalid page text');characters+=[...page.text].length;if(characters>200000)throw Error('Oversized document text');const normalized=normalizeNFC(page.text);
  if(!Array.isArray(page.assets))throw Error('Invalid assets');assetCount+=page.assets.length;if(assetCount>64)throw Error('Too many document assets');
  const parts=[index,NORMALIZATION_ID,Buffer.from(normalized,'utf8'),page.assets.length],assets=[];
  page.assets.forEach((asset,assetIndex)=>{fields(asset,['media_type','data_base64']);const media=asset.media_type;if(typeof media!=='string'||media.length<1||media.length>64||! /^[A-Za-z0-9.+\-]+\/[A-Za-z0-9.+\-]+$/.test(media))throw Error('Invalid asset media type');
   const raw=binary(asset.data_base64);assetBytes+=raw.length;if(assetBytes>MAX_BINARY)throw Error('Oversized document assets');const sha256=digest('document-asset',[assetIndex,media,raw]);parts.push(Buffer.from(sha256,'hex'));assets.push({index:assetIndex,media_type:media,bytes:raw.length,sha256});
  });
  const sha256=digest('document-page',parts);hashes.push(Buffer.from(sha256,'hex'));manifest.push({index,characters:[...normalized].length,sha256,assets});
 });
 return {modality:'document',contract_version:VERSION,sha256:digest('document',[value.extraction_profile,NORMALIZATION_ID,value.pages.length,...hashes]),extraction_profile:value.extraction_profile,normalization_id:NORMALIZATION_ID,pages:manifest,offset_unit:'page_index_unicode_codepoint_half_open'};
}
function subject(value){if(!value||Array.isArray(value)||typeof value!=='object')throw Error('Invalid artifact');switch(value.modality){case 'image':return image(value)[0];case 'audio':return audio(value);case 'video':return video(value);case 'document':return document(value);default:throw Error('Unsupported reserved subject modality');}}
function validateSpan(artifact,span){
 const result=subject(artifact);
 function interval(value,max){if(!Array.isArray(value)||value.length!==2)throw Error('Invalid interval');const start=integer(value[0],0,max),end=integer(value[1],0,max);if(start>=end)throw Error('Empty/reversed interval');return [start,end];}
 function box(value,width,height){if(!Array.isArray(value)||value.length!==4)throw Error('Invalid box');const [x0,x1]=interval([value[0],value[2]],width),[y0,y1]=interval([value[1],value[3]],height);return [x0,y0,x1,y1];}
 if(result.modality==='image')return box(span,result.width,result.height);
 if(result.modality==='audio')return interval(span,result.frames);
 if(result.modality==='video'){fields(span,['frame','box']);const frame=integer(span.frame,0,result.frames.length-1),image=result.frames[frame].image;return {frame,box:box(span.box,image.width,image.height)};}
 fields(span,['page','range']);const page=integer(span.page,0,result.pages.length-1);return {page,range:interval(span.range,result.pages[page].characters)};
}
module.exports={subject,validateSpan,VERSION};
