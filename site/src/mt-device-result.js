import manifest from './mt-device-manifest.json' with {type:'json'};
import {normalizeNFC,NORMALIZATION_ID} from '../../protocol/normalization.mjs';
const fail=()=>{throw Error('MT observation unavailable');};
const contexts=new WeakMap(),validated=new WeakSet();
const PYTHON_SOURCES=['tools/mt_device.py','tools/language_observations.py','tools/authority_quotation.py','protocol/normalization.py','protocol/unicode15-data.json','protocol/corpus.py','tools/blind_review_io.py','scripts/authority-quotation.py'];
const AUTHORITY_SOURCES=['tools/authority_quotation.py','scripts/authority-quotation.py','tools/language_observations.py','protocol/normalization.py','protocol/unicode15-data.json','protocol/corpus.py','tools/blind_review_io.py'];
function object(value,keys){
 if(!value||typeof value!=='object'||Array.isArray(value)||![Object.prototype,null].includes(Object.getPrototypeOf(value)))fail();
 const own=Reflect.ownKeys(value);if(own.length!==keys.length||own.some(k=>typeof k!=='string')||own.toSorted().some((k,i)=>k!==keys.toSorted()[i]))fail();
 for(const key of own){const d=Object.getOwnPropertyDescriptor(value,key);if(!Object.hasOwn(d,'value')||!d.enumerable)fail();}
}
function list(value,max=8000){
 if(!Array.isArray(value)||value.length>max||Reflect.ownKeys(value).length!==value.length+1)fail();
 for(let i=0;i<value.length;i++){const d=Object.getOwnPropertyDescriptor(value,String(i));if(!d||!Object.hasOwn(d,'value')||!d.enumerable)fail();}
 return value;
}
const eq=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const count=(value,max=8000)=>{if(!Number.isSafeInteger(value)||value<0||value>max)fail();return value;};
function fieldsFalse(value,names){for(const key of names)if(value[key]!==false)fail();}
function sources(value,names){object(value,names);for(const name of names)if(value[name]!==manifest.sources[name])fail();}
function span(value,size){list(value,2);if(value.length!==2||!value.every(Number.isSafeInteger)||value[0]<0||value[0]>=value[1]||value[1]>size)fail();return value;}
const cmp=(a,b)=>a[0]-b[0]||a[1]-b[1];
const contains=(outer,inner)=>outer[0]<=inner[0]&&inner[1]<=outer[1];
const overlap=(a,b)=>Math.max(a[0],b[0])<Math.min(a[1],b[1]);
function spans(values,size,max=8000){list(values,max);let previous;for(const item of values){span(item,size);if(previous&&cmp(previous,item)>=0)fail();previous=item;}return values;}
const member=(values,item)=>values.some(value=>eq(value,item));
function freeze(record){const pending=[record],seen=new Set();while(pending.length){const value=pending.pop();if(!value||typeof value!=='object'||seen.has(value))continue;seen.add(value);pending.push(...Object.values(value));Object.freeze(value);}return record;}
export async function mtSubject(text){
 if(typeof text!=='string'||!text.trim()||text.includes('\0')||Array.from(text).length>8000||new TextEncoder().encode(text).length>32000)fail();
 const normalized=normalizeNFC(text),points=Array.from(normalized);if(!points.length||points.length>8000||NORMALIZATION_ID!==manifest.normalization_id)fail();
 const bytes=new TextEncoder().encode(normalized),digest=await crypto.subtle.digest('SHA-256',bytes);
 const context=Object.freeze({sha256:Array.from(new Uint8Array(digest),v=>v.toString(16).padStart(2,'0')).join(''),characters:points.length});
 contexts.set(context,points);return context;
}
function urgency(original,counts,size){
 object(original,['format','method','method_sha256','kind','language','subject_sha256','subject_characters','normalization_id','offset_unit','state','findings','measurements','context_inferred','quoted_or_recommended_context_classified','intent_established','truth_established','score_is_probability','independent_accuracy_evidence','network_used','tags']);
 if(original.format!=='language-observation/v1'||original.kind!=='urgency'||original.language!=='en'||original.method_sha256!==manifest.sources['tools/language_observations.py']||original.subject_characters!==size)fail();
 fieldsFalse(original,['context_inferred','quoted_or_recommended_context_classified','score_is_probability']);
 const m=original.measurements;object(m,['sentence_units','directive_units','directive_density','minimum_density','directive_spans','time_pressure_spans','association_scope','paired_units','unpaired_time_pressure_spans','grammatical_imperatives_verified']);
 count(m.sentence_units,size);count(m.directive_units,m.sentence_units);
 if(m.directive_density!==(m.sentence_units?m.directive_units/m.sentence_units:0)||m.minimum_density!==0.5||m.association_scope!=='same_sentence_unit'||m.grammatical_imperatives_verified!==false)fail();
 spans(m.directive_spans,size);spans(m.time_pressure_spans,size);spans(m.unpaired_time_pressure_spans,size);
 if(m.directive_units!==m.directive_spans.length)fail();
 list(m.paired_units,m.directive_units);let previous;const pairedPressure=[],evidence=[];
 for(const unit of m.paired_units){
  object(unit,['unit_span','directive_span','time_pressure_spans']);span(unit.unit_span,size);span(unit.directive_span,size);spans(unit.time_pressure_spans,size);
  if(previous&&previous[1]>unit.unit_span[0]||!contains(unit.unit_span,unit.directive_span)||!member(m.directive_spans,unit.directive_span)||!unit.time_pressure_spans.length)fail();previous=unit.unit_span;
  for(const p of unit.time_pressure_spans){if(!contains(unit.unit_span,p)||!member(m.time_pressure_spans,p))fail();pairedPressure.push(p);}
  evidence.push(unit.directive_span,...unit.time_pressure_spans);
 }
 if(!eq(m.unpaired_time_pressure_spans,m.time_pressure_spans.filter(p=>!member(pairedPressure,p))))fail();
 list(original.findings,1);const found=m.paired_units.length>0&&m.directive_density>=m.minimum_density;
 if(Boolean(original.findings.length)!==found||(original.state==='OBSERVATIONS')!==found)fail();
 if(found){const row=original.findings[0];object(row,['id','spans','meaning']);spans(row.spans,size);
  const unique=[...new Map(evidence.map(p=>[p.join(','),p])).values()].sort(cmp);
  if(row.id!=='sig.urgency_frame.v1'||row.meaning!=='same_unit_lexical_time_pressure_with_supported_directive_density'||!eq(row.spans,unique))fail();
 }
 object(counts,['finding_groups','paired_units']);if(counts.finding_groups!==original.findings.length||counts.paired_units!==m.paired_units.length)fail();
}
function authority(original,counts,points,contract=null){
 const size=points.length,names=['outside_supported_quotes_without_marker','outside_supported_quotes_with_marker','quoted_phrase_count','supported_quote_count'];
 object(original,['format','method','state',...names,'source_lookup_performed','quote_endorsement_interpreted','negation_interpreted','semantic_attribution_interpreted','intent_established','truth_established','independent_accuracy_evidence','network_used','tags','subject_sha256','normalization_id','offset_unit','source_sha256','quote_spans','outside_markerless_phrases','outside_marked_phrases','quoted_phrases','subject_text_included','parameters']);
 if(original.format!==(contract?.format||'authority-quotation-observation/v1'))fail();
 fieldsFalse(original,['source_lookup_performed','quote_endorsement_interpreted','negation_interpreted','semantic_attribution_interpreted','subject_text_included']);if(contract){object(original.source_sha256,Object.keys(contract.sources));for(const name of Object.keys(contract.sources))if(original.source_sha256[name]!==contract.sources[name])fail();}else sources(original.source_sha256,AUTHORITY_SOURCES);
 const p=original.parameters;object(p,contract?Object.keys(contract.parameters):['language','quote_grammar','citation_scope','max_quotes','max_phrases','max_units','max_markers']);
 const fixed=contract?.parameters||{language:'en',quote_grammar:'balanced_unescaped_ASCII_double_quotes',citation_scope:'same_literal_unit_and_supported_quote_context',max_quotes:64,max_phrases:128,max_units:512,max_markers:256};
 for(const key of Object.keys(fixed))if(p[key]!==fixed[key])fail();
 spans(original.quote_spans,size,64);
 if(contract){if(!eq(original.quote_spans,contract.quoteSpans))fail();}else{
const quotePoints=[];
 for(let i=0;i<size;i++){if(['“','”','«','»','`'].includes(points[i]))fail();if(points[i]==='"'){if(points[i-1]==='\\')fail();quotePoints.push(i);}}
 if(quotePoints.length!==original.quote_spans.length*2)fail();
 for(let i=0;i<original.quote_spans.length;i++)if(!eq(original.quote_spans[i],[quotePoints[i*2],quotePoints[i*2+1]+1]))fail();
 }
 const phraseSpans=[],allMarkers=[];
 for(const [name,mode] of [['outside_markerless_phrases','markerless'],['outside_marked_phrases','marked'],['quoted_phrases','quoted']]){
  list(original[name],128);let previous;
  for(const row of original[name]){
   object(row,['phrase_span','unit_span','quote_span','source_marker_spans']);span(row.phrase_span,size);span(row.unit_span,size);spans(row.source_marker_spans,size,256);
   if(!contains(row.unit_span,row.phrase_span)||previous&&cmp(previous,row.phrase_span)>=0||member(phraseSpans,row.phrase_span))fail();previous=row.phrase_span;phraseSpans.push(row.phrase_span);
   if(mode==='quoted'){
    span(row.quote_span,size);if(!member(original.quote_spans,row.quote_span)||!contains([row.quote_span[0]+1,row.quote_span[1]-1],row.phrase_span))fail();
   }else if(row.quote_span!==null||original.quote_spans.some(q=>overlap(q,row.phrase_span)))fail();
   if(mode==='markerless'&&row.source_marker_spans.length||mode==='marked'&&!row.source_marker_spans.length)fail();
   for(const marker of row.source_marker_spans){
    if(!contains(row.unit_span,marker))fail();
    if(mode==='quoted'){if(!contains([row.quote_span[0]+1,row.quote_span[1]-1],marker))fail();}
    else if(original.quote_spans.some(q=>overlap(q,marker)))fail();allMarkers.push(marker);
   }
  }
 }
 if(phraseSpans.length>128||new Set(allMarkers.map(s=>s.join(','))).size>256)fail();
 const wanted={outside_supported_quotes_without_marker:original.outside_markerless_phrases.length,outside_supported_quotes_with_marker:original.outside_marked_phrases.length,quoted_phrase_count:original.quoted_phrases.length,supported_quote_count:original.quote_spans.length};
 object(counts,names);for(const name of names)if(original[name]!==wanted[name]||counts[name]!==wanted[name])fail();
 if((original.state==='OBSERVATIONS')!==Boolean(wanted.outside_supported_quotes_without_marker))fail();
}
export function validMTRecord(record,kind,context){
 const points=contexts.get(context);if(!points||!['urgency','authority'].includes(kind))fail();
 object(record,['format','check','method','state','counts','original','subject_sha256','subject_characters','normalization_id','offset_unit','source_sha256','tags','intent_established','truth_established','independent_accuracy_evidence','subject_text_included']);
 if(record.format!=='mt-device-phrase-explorer/1.0.1'||record.check!==kind||record.method!==manifest.methods[kind]||!['OBSERVATIONS','NO_SUPPORTED_PATTERN'].includes(record.state)||record.subject_sha256!==context.sha256||record.subject_characters!==context.characters||record.normalization_id!==manifest.normalization_id||record.offset_unit!=='NFC_unicode_codepoint')fail();
 fieldsFalse(record,['intent_established','truth_established','independent_accuracy_evidence','subject_text_included']);list(record.tags,0);sources(record.source_sha256,PYTHON_SOURCES);
 const original=record.original;
 if(kind==='urgency')urgency(original,record.counts,context.characters);else if(kind==='authority')authority(original,record.counts,points);else fail();
 if(original.method!==record.method||original.state!==record.state||original.subject_sha256!==context.sha256||original.normalization_id!==manifest.normalization_id||original.offset_unit!=='NFC_unicode_codepoint')fail();
 fieldsFalse(original,['intent_established','truth_established','independent_accuracy_evidence','network_used']);list(original.tags,0);
 freeze(record);validated.add(record);return record;
}
export function explainMT(record){
 if(!validated.has(record))fail();
 if(record.check==='urgency')return record.state==='OBSERVATIONS'?
  {title:'Instruction + time wording found',body:'A request and a time phrase appear together. This could be ordinary advice.'}:
  record.counts.paired_units?{title:'Some time wording, no overall match',body:'A local pair appears, but the full supported pattern did not match. Other pressure may still be present.'}:
  {title:'No supported urgency pattern found',body:'This check did not find its instruction-and-time pattern. Other pressure may still be present.'};
 if(record.counts.outside_supported_quotes_without_marker)return {title:'Authority wording found',body:'An expertise or consensus phrase has no nearby outside-quote source marker. A source may appear elsewhere.'};
 if(record.counts.quoted_phrase_count)return {title:'Authority wording appears in a quote',body:'Quoted phrases are kept separate. This does not tell us whether anyone endorses them.'};
 if(record.counts.outside_supported_quotes_with_marker)return {title:'Authority wording has a source marker',body:'A marker appears nearby. This check has not verified the source.'};
 return {title:'No supported authority wording found',body:'This check did not find one of its supported phrases. Other wording may still be present.'};
}

// Structural foundation only; callers still own their closed profile/subject checks.
export {authority as validateAuthorityDetails};
