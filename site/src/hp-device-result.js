import manifest from './hp-device-manifest.json' with {type:'json'};
import {normalizeNFC,NORMALIZATION_ID} from '../../protocol/normalization.mjs';
const fail=()=>{throw Error('Literal-detail observation unavailable');};
const contexts=new WeakMap(),validated=new WeakSet();
const SOURCES=['tools/hp_device.py','tools/quantitative_observations.py','tools/language_observations.py','protocol/normalization.py','protocol/unicode15-data.json','protocol/corpus.py'];
const METHOD_SOURCES=SOURCES.filter(p=>p!=='tools/hp_device.py');
const COUNTS=['supported_detail_count','without_same_unit_marker','with_same_unit_marker','skipped_detail_count'];
function object(value,keys){
 if(!value||typeof value!=='object'||Array.isArray(value)||![Object.prototype,null].includes(Object.getPrototypeOf(value)))fail();
 const own=Reflect.ownKeys(value),expected=keys.toSorted();
 if(own.length!==expected.length||own.some(k=>typeof k!=='string')||own.toSorted().some((k,i)=>k!==expected[i]))fail();
 for(const key of own){const d=Object.getOwnPropertyDescriptor(value,key);if(!Object.hasOwn(d,'value')||!d.enumerable)fail();}
}
function list(value,max){
 if(!Array.isArray(value)||value.length>max||Reflect.ownKeys(value).length!==value.length+1)fail();
 for(let i=0;i<value.length;i++){const d=Object.getOwnPropertyDescriptor(value,String(i));if(!d||!Object.hasOwn(d,'value')||!d.enumerable)fail();}
 return value;
}
const count=(n,max)=>{if(!Number.isSafeInteger(n)||n<0||n>max)fail();};
function sources(value,names){object(value,names);for(const name of names)if(value[name]!==manifest.sources[name])fail();}
function fieldsFalse(value,names){for(const key of names)if(value[key]!==false)fail();}
const contains=(a,b)=>a[0]<=b[0]&&b[1]<=a[1];
const overlap=(a,b)=>Math.max(a[0],b[0])<Math.min(a[1],b[1]);
const space=cp=>cp>=9&&cp<=13||cp>=28&&cp<=32||[133,160,5760,8232,8233,8239,8287,12288].includes(cp)||cp>=8192&&cp<=8202;
function markerShape(text){if(/^\[[0-9]{1,4}\]$/.test(text))return true;const prefix=text.toLowerCase().replaceAll('ſ','s').match(/^https?:\/\//);return Boolean(prefix&&text.length>prefix[0].length&&!Array.from(text.slice(prefix[0].length)).some(c=>space(c.codePointAt(0))||c==='<'||c==='>'));}
const cmp=(a,b)=>a[0]-b[0]||a[1]-b[1];
const eq=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const digest=async raw=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw)),n=>n.toString(16).padStart(2,'0')).join('');
export async function hpSubject(text){
 if(typeof text!=='string'||!text.trim()||text.includes('\0')||Array.from(text).length>8000)fail();
 const normalized=normalizeNFC(text),points=Array.from(normalized),raw=new TextEncoder().encode(text);
 if(raw.length>32000||!points.length||points.length>8000||NORMALIZATION_ID!==manifest.normalization_id)fail();
 const [rawHash,normalHash]=await Promise.all([digest(raw),digest(new TextEncoder().encode(normalized))]);
 const context=Object.freeze({raw_sha256:rawHash,raw_characters:Array.from(text).length,raw_bytes:raw.length,subject_sha256:normalHash,subject_characters:points.length});
 contexts.set(context,points);return context;
}
function freeze(record){const stack=[record],seen=new Set();while(stack.length){const v=stack.pop();if(!v||typeof v!=='object'||seen.has(v))continue;seen.add(v);stack.push(...Object.values(v));Object.freeze(v);}return record;}
export function validHPRecord(record,context){
 const points=contexts.get(context);if(!points)fail();const size=points.length;let spanBudget=0;
 function span(s){list(s,2);if(s.length!==2||!s.every(Number.isSafeInteger)||s[0]<0||s[0]>=s[1]||s[1]>size||++spanBudget>16384)fail();}
 function spans(items){list(items,2667);let previous;for(const s of items){span(s);if(previous&&cmp(previous,s)>=0)fail();previous=s;}}
 object(record,['format','method','state','counts','original','raw_sha256','raw_characters','raw_bytes','subject_sha256','subject_characters','normalization_id','offset_unit','source_sha256','tags','tag_asserted','truth_established','source_support_established','independent_accuracy_evidence','subject_text_included']);
 if(record.format!=='hp-literal-detail-explorer/1.0.0'||record.method!==manifest.method||!['OBSERVATIONS','NO_SUPPORTED_PATTERN'].includes(record.state)||record.normalization_id!==manifest.normalization_id||record.offset_unit!=='NFC_unicode_codepoint')fail();
 for(const k of ['raw_sha256','raw_characters','raw_bytes','subject_sha256','subject_characters'])if(record[k]!==context[k])fail();
 fieldsFalse(record,['tag_asserted','truth_established','source_support_established','independent_accuracy_evidence','subject_text_included']);list(record.tags,0);sources(record.source_sha256,SOURCES);object(record.counts,COUNTS);
 const o=record.original;
 object(o,['format','method','state',...COUNTS,'source_lookup_performed','source_support_established','calendar_validity_checked','truth_established','uncertainty_inferred','score_is_probability','independent_accuracy_evidence','network_used','tags','subject_sha256','normalization_id','offset_unit','method_sha256','source_file_sha256','parameters','details','subject_text_included','privacy']);
 if(o.format!=='quantitative-observation/v1'||o.method!==manifest.method||o.state!==record.state||o.subject_sha256!==context.subject_sha256||o.normalization_id!==manifest.normalization_id||o.offset_unit!=='NFC_unicode_codepoint'||o.method_sha256!==manifest.sources['tools/quantitative_observations.py']||o.privacy!=='Hashes and spans may reveal or link information. Share deliberately.')fail();
 fieldsFalse(o,['source_lookup_performed','source_support_established','calendar_validity_checked','truth_established','uncertainty_inferred','score_is_probability','independent_accuracy_evidence','network_used','subject_text_included']);list(o.tags,0);sources(o.source_file_sha256,METHOD_SOURCES);
 object(o.parameters,['declared_language','source_context','token_boundary','max_detail_characters','max_details']);
 const fixed={declared_language:'en',source_context:'same_literal_sentence_unit',token_boundary:'ASCII_only',max_detail_characters:48,max_details:256};
 for(const k of Object.keys(fixed))if(o.parameters[k]!==fixed[k])fail();
 list(o.details,256);let previous,without=0;
 for(const row of o.details){
  object(row,['id','signal_candidate','span','unit_span','source_marker_spans','kind','meaning']);span(row.span);span(row.unit_span);spans(row.source_marker_spans);
  if(!contains(row.unit_span,row.span)||row.span[1]-row.span[0]>48||previous&&previous[1]>row.span[0])fail();previous=row.span;
  const token=points.slice(...row.span).join('');
  if(!/^(?:[0-9]{4}-[0-9]{2}-[0-9]{2}|[+-]?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?%?)$/.test(token))fail();
  const date=/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(token);
  if(row.kind!==(date?'date_shaped':'numeric_literal'))fail();
  const marked=row.source_marker_spans.length>0;
  if(row.id!==(marked?null:'sig.unsourced_specificity.v1')||row.signal_candidate!==!marked||row.meaning!==(marked?'literal_detail_with_same_unit_marker':'literal_detail_without_same_unit_marker'))fail();
  for(const marker of row.source_marker_spans)if(!overlap(row.unit_span,marker)||overlap(row.span,marker)||!markerShape(points.slice(...marker).join('')))fail();
  if(!marked)without++;
 }
 for(const k of COUNTS){count(o[k],k==='skipped_detail_count'?8000:256);if(record.counts[k]!==o[k])fail();}
 if(o.supported_detail_count!==o.details.length||o.without_same_unit_marker!==without||o.with_same_unit_marker!==o.details.length-without||(record.state==='OBSERVATIONS')!==Boolean(without))fail();
 // Serialization follows closed typed validation: unknown raw fields are never
 // serialized/projected away. All method fields remain intact.
 if(new TextEncoder().encode(JSON.stringify(o,null,2)).length>131072||JSON.stringify(record).length>262144)fail();
 freeze(record);validated.add(record);return record;
}
export function explainHP(record){
 if(!validated.has(record))fail();const c=record.counts;
 return c.supported_detail_count?{title:`${c.supported_detail_count} literal ${c.supported_detail_count===1?'detail':'details'} found`,body:'Numbers and date-shaped text only. This does not tell us whether a claim is true.',marked:c.with_same_unit_marker,unmarked:c.without_same_unit_marker,skipped:c.skipped_detail_count}:
 {title:'No supported details found',body:'Other number formats may not be covered. This is not a fact check.',marked:0,unmarked:0,skipped:c.skipped_detail_count};
}
