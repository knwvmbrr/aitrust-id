import manifest from './hp-uncertainty-manifest.json' with {type:'json'};
import {normalizeNFC,NORMALIZATION_ID} from '../../protocol/normalization.mjs';
const contexts=new WeakMap(),accepted=new WeakSet();
const NAMES=['tools/hp_uncertainty_device.py','tools/language_observations.py','protocol/corpus.py','protocol/normalization.py','protocol/unicode15-data.json'];
export const need=value=>{if(!value)throw Error('Uncertainty wording unavailable');};
const encode=text=>new TextEncoder().encode(text);
const sha=async raw=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw)),v=>v.toString(16).padStart(2,'0')).join('');
const punctuation=new Set(Array.from('‘’“”«»–—…'));
const whitespace=cp=>cp>=9&&cp<=13||cp>=28&&cp<=32||[133,160,5760,8232,8233,8239,8287,12288].includes(cp)||cp>=8192&&cp<=8202;
const safe=c=>c.codePointAt(0)<128||whitespace(c.codePointAt(0))||punctuation.has(c);
const word=c=>Boolean(c&&/^[A-Za-z0-9_]$/.test(c));
const pattern='may|might|could|possibly|perhaps|probably|likely|unlikely|uncertain|unclear|approximately|roughly|estimated|estimate';
function candidates(points){
 const projection=points.map(c=>({'İ':'i','ı':'i','ſ':'s','K':'k'})[c]||c).join('');
 const rows=[];
 for(const m of projection.matchAll(new RegExp(pattern,'gi'))){
  const start=Array.from(projection.slice(0,m.index)).length,end=start+Array.from(m[0]).length;
  need(points.slice(start,end).every(c=>c.codePointAt(0)<128));
  for(const index of [start-1,end])if(index>=0&&index<points.length)need(safe(points[index]));
  if(m[0].toLowerCase()==='may'){
   let i=end;while(i<points.length&&whitespace(points[i].codePointAt(0)))i++;
   let count=0;while(count<2&&i+count<points.length&&/^[0-9]$/.test(points[i+count]))count++;
   if(count&&i+count<points.length)need(safe(points[i+count]));
  }
  rows.push([start,end]);
 }
 return rows;
}
export function validUncertaintyInput(text){
 need(typeof text==='string'&&Array.from(text).some(c=>!whitespace(c.codePointAt(0)))&&!text.includes('\0')&&Array.from(text).length<=8000&&encode(text).length<=32000);
 need(!Array.from(text).some(c=>{const n=c.codePointAt(0);return n>=0xd800&&n<=0xdfff;}));
 const p=Array.from(normalizeNFC(text));need(p.length>0&&p.length<=8000&&NORMALIZATION_ID===manifest.normalization_id);candidates(p);
}
export async function uncertaintyContext(text,selection){
 need(selection===true);validUncertaintyInput(text);
 const normalized=normalizeNFC(text),points=Array.from(normalized),raw=encode(text);
 const identity={raw_sha256:await sha(raw),raw_bytes:raw.length,raw_characters:Array.from(text).length,subject_sha256:await sha(encode(normalized)),subject_characters:points.length};
 const annotation={format:'language-context-annotations/v1',subject_sha256:identity.subject_sha256,uncertainty:[[0,points.length]],sources:[]};
 Object.freeze(annotation.uncertainty[0]);Object.freeze(annotation.uncertainty);Object.freeze(annotation.sources);Object.freeze(annotation);
 const context=Object.freeze({identity:Object.freeze(identity),annotation});contexts.set(context,points);return context;
}
const canonical=v=>Array.isArray(v)?'['+v.map(canonical).join(',')+']':v&&typeof v==='object'?'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}':JSON.stringify(v);
function closed(value){
 let count=0,characters=0;const seen=new Set();
 function visit(v){
  need(++count<=20000);
  if(typeof v==='string'){characters+=v.length;need(v.length<=1000&&characters<=150000);return;}
  if(v===null||typeof v==='boolean')return;
  if(typeof v==='number'){need(Number.isFinite(v));return;}
  need(v&&typeof v==='object'&&!seen.has(v));seen.add(v);
  if(Array.isArray(v)){
   need(v.length<=8000&&Reflect.ownKeys(v).length===v.length+1);
   for(let i=0;i<v.length;i++){const d=Object.getOwnPropertyDescriptor(v,String(i));need(d&&Object.hasOwn(d,'value')&&d.enumerable);visit(d.value);}
  }else{
   need([Object.prototype,null].includes(Object.getPrototypeOf(v)));const keys=Reflect.ownKeys(v);need(keys.length<=40);
   for(const key of keys){need(typeof key==='string'&&key.length<=120);const d=Object.getOwnPropertyDescriptor(v,key);need(d&&Object.hasOwn(d,'value')&&d.enumerable);visit(d.value);}
  }
 }
 visit(value);
}
export function canonicalUncertainty(context){
 const points=contexts.get(context);need(points);const hedge=[],calendar=[];
 for(const [start,end] of candidates(points)){
  if(word(points[start-1])||word(points[end]))continue;
  let isCalendar=false;
  if(points.slice(start,end).join('').toLowerCase()==='may'){
   let i=end;while(i<points.length&&whitespace(points[i].codePointAt(0)))i++;
   if(i>end){let j=i;while(j<points.length&&j-i<2&&/^[0-9]$/.test(points[j]))j++;isCalendar=j>i&&!word(points[j]);}
  }
  (isCalendar?calendar:hedge).push([start,end]);
 }
 const n=points.length,state=hedge.length?'NO_SUPPORTED_PATTERN':'OBSERVATIONS';
 const original={format:'language-observation/v1',method:'english-context-observations/1.0.0',method_sha256:manifest.checks.hedge.sources['tools/language_observations.py'],kind:'hedge',language:'en',subject_sha256:context.identity.subject_sha256,subject_characters:n,normalization_id:manifest.normalization_id,offset_unit:'NFC_unicode_codepoint',state,
  findings:hedge.length?[]:[{id:'sig.hedge_collapse.v1',spans:[[0,n]],meaning:'no_supported_hedge_in_caller_selected_uncertainty_span',expectation_source:'explicit_caller_annotation'}],
  measurements:{contexts:[{expected_uncertainty_span:[0,n],hedge_spans:hedge,excluded_calendar_spans:calendar}],expected_uncertainty_inferred:false,calendar_exclusion:'may_followed_by_day_number_only',negation_interpreted:false},
  context_inferred:false,quoted_or_recommended_context_classified:false,intent_established:false,truth_established:false,score_is_probability:false,independent_accuracy_evidence:false,network_used:false,tags:[]};
 return {format:'hp-explicit-uncertainty-device/1.0.0',method:original.method,boundary:'hp-uncertainty-safe-boundaries/v1',state,...context.identity,normalization_id:manifest.normalization_id,offset_unit:'NFC_unicode_codepoint',annotation:context.annotation,annotation_source:'explicit_caller_whole_passage',counts:{hedge_words:hedge.length,calendar_candidates:calendar.length},original,source_sha256:Object.fromEntries(NAMES.map(p=>[p,manifest.checks.hedge.sources[p]])),tags:[],tag_asserted:false,uncertainty_needed_established:false,truth_established:false,independent_accuracy_evidence:false,subject_text_included:false,input_persisted:false};
}
export function validUncertaintyRecord(record,context){
 need(contexts.has(context));closed(record);need(canonical(record)===canonical(canonicalUncertainty(context))&&encode(JSON.stringify(record)).length<=262144);
 function freeze(v){if(v&&typeof v==='object'){Object.values(v).forEach(freeze);Object.freeze(v);}}freeze(record);accepted.add(record);return record;
}
export function explainUncertainty(record){
 need(accepted.has(record));return record.counts.hedge_words?{title:'Listed uncertainty words found',body:'Words such as “may” or “likely” appear in your selected passage. Their meaning still depends on context.'}:{title:'No listed uncertainty words found',body:'This word list is limited. It cannot tell whether uncertainty is needed, a statement is true, or different wording expresses uncertainty.'};
}
